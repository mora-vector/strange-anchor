{ pkgs }:
let
  payload = "Sandhi recovery fixture: the recipe needs its source.\n";
  source = builtins.toFile "sandhi-recovery-input" payload;
  # The builtin fetcher keeps this experiment small: no compiler toolchain is
  # smuggled in through a shell builder's derivation closure.
  recoverable = import ./fixtures/fixed-output.nix {
    name = "sandhi-recoverable";
    url = "file://${source}";
    sha256 = builtins.hashString "sha256" payload;
  };
  recipe = drv: builtins.unsafeDiscardOutputDependency drv.drvPath;
in pkgs.testers.runNixOSTest {
  name = "sandhi-offline-recovery";
  requiredFeatures.kvm = false;
  globalTimeout = 900;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules ];
    virtualisation = {
      memorySize = 1536;
      cores = 2;
      vlans = [];
      writableStore = true; # All collection/deletion happens in the disposable guest.
    };
    nix.settings = {
      experimental-features = [ "nix-command" ];
      substituters = lib.mkForce [];
      substitute = false;
    };
    nix.distributedBuilds = false;
    # Nix's exportReferencesGraph used by the VM image builder also walks
    # derivation outputs. Satisfy that packaging requirement explicitly, without
    # adding an output root. The missing-input case is instantiated after boot.
    system.checks = [ recoverable ];
    environment.etc."sandhi/recovery-fixture.nix".source = ./fixtures/fixed-output.nix;
    # All store mutations below explicitly select this daemon. A root client's
    # implicit local store would evade the network condition being tested.
    systemd.services.nix-daemon.serviceConfig.PrivateNetwork = true;
    sandhi = {
      retention.enable = true; # Recovery does not require execution or export.
      # Nonempty declarations make absence of generated units a useful control.
      workers.disabled.package = pkgs.hello;
      contracts.disabled = { karana = pkgs.hello; adhikarana = "backplane"; };
      chandas.disabled = { cpuPercent = 50; memoryMiB = 128; };
      retainedRecipes = [ recoverable ];
      gaps.unavailable-fixture = {
        status = "unknown";
        availability = "absent";
        recoveryEvidence = [];
        reason = "A deliberately missing fixture input; retaining its recipe is not recovery.";
      };
    };
  };
  testScript = ''
    import hashlib, json, os, shlex
    start_all()
    machine.wait_for_unit("multi-user.target")
    inventory = machine.succeed("systemctl list-unit-files --type=service --no-legend --no-pager")
    units = {line.split()[0] for line in inventory.splitlines() if line.strip()}
    # An unmatched pattern can return 1. Query the complete inventory and use a
    # known service as a positive control before asserting the managed set empty.
    assert "nix-daemon.service" in units, units
    assert not any(unit.startswith("sandhi-") for unit in units), units
    for snapshot in ["claims", "lopa", "contracts"]:
        machine.succeed(f"test ! -e /etc/sandhi/{snapshot}.json")
    store = "NIX_REMOTE=daemon nix-store"
    no_builders = shlex.quote("")
    good = "${recipe recoverable}"
    source = "${source}"
    expected = ${builtins.toJSON payload}

    def query(arguments):
        return machine.succeed(f"{store} {arguments}").strip()

    def nar_hash(path):
        return query(f"--query --hash {shlex.quote(path)}")

    out = query(f"--query --outputs {good}")
    machine.succeed(
        "NIX_REMOTE=daemon nix-instantiate /etc/sandhi/recovery-fixture.nix "
        "--add-root /nix/var/nix/gcroots/sandhi-test-unavailable "
        "--argstr name sandhi-unavailable "
        "--argstr url file:///sandhi-intentionally-missing-input "
        "--argstr sha256 ${builtins.hashString "sha256" payload}"
    )
    bad = machine.succeed("readlink -f /nix/var/nix/gcroots/sandhi-test-unavailable").strip()
    bad_out = query(f"--query --outputs {bad}")
    machine.succeed(f"test ! -e {bad_out}",
                    "test ! -e /sandhi-intentionally-missing-input")
    closure = query("--query --requisites /run/current-system").splitlines()
    assert good in closure and source in closure and out not in closure, closure
    machine.succeed("test -L /nix/var/nix/gcroots/sandhi-test-unavailable")

    # Establish the daemon's actual network namespace, not just its unit setting.
    pid = machine.succeed("systemctl show nix-daemon.service -p MainPID --value").strip()
    assert int(pid) > 0, pid
    host_net = machine.succeed("readlink /proc/1/ns/net").strip()
    daemon_net = machine.succeed(f"readlink /proc/{pid}/ns/net").strip()
    assert daemon_net != host_net, (host_net, daemon_net)
    links = json.loads(machine.succeed(f"nsenter -t {pid} -n ip -j link show"))
    assert [link["ifname"] for link in links] == ["lo"], links
    routes = json.loads(machine.succeed(f"nsenter -t {pid} -n ip -j route show"))
    assert routes == [], routes

    # A host build dependency need not be copied into the guest store. Establish
    # the baseline through the isolated daemon before testing GC and output loss.
    initially_present = machine.execute(f"test -f {out}")[0] == 0
    initially_registered = machine.execute(f"{store} --check-validity {out}")[0] == 0
    # Image registration can describe bytes absent from the guest's mounted
    # store. Normal realization trusts that registration. Repair checks bytes.
    realized = query(f"--realise {good} --repair --option substitute false --option builders {no_builders}")
    assert realized == out, (realized, out)
    machine.succeed(f"test -f {out}")

    machine.succeed("printf '%s' disposable-fixture > /tmp/sandhi-unrooted-control")
    orphan = query("--add /tmp/sandhi-unrooted-control")
    machine.succeed(f"test -f {orphan}")
    machine.succeed(f"{store} --gc")
    machine.succeed(f"test ! -e {orphan}", f"test -f {good}", f"test -f {bad}", f"test -f {source}")
    before = nar_hash(out)
    assert machine.succeed(f"cat {out}") == expected
    machine.succeed(f"test -f {out}") # Normal keep-outputs policy preserves the realized form.

    # Deliberately simulate loss of this one synthetic output. This scoped test
    # override is explicit; the module's retention policy remains enabled.
    machine.succeed(f"{store} --delete --option keep-outputs false {out}")
    machine.succeed(f"test ! -e {out}", f"test -f {good}", f"test -f {source}")
    query(f"--realise {good} --option substitute false --option builders {no_builders}")
    after = nar_hash(out)
    restored = machine.succeed(f"cat {out}")
    assert before == after and restored == expected, (before, after, restored)

    # Counterexample: a retained recipe whose source is unavailable cannot build.
    failure_code, failure_log = machine.execute(
        f"{store} --realise {bad} --option substitute false --option builders {no_builders} 2>&1"
    )
    assert failure_code != 0, failure_log
    assert "file:///sandhi-intentionally-missing-input" in failure_log, failure_log
    assert "Could not open file" in failure_log, failure_log
    machine.succeed(f"test -f {bad}", f"{store} --check-validity {out}")
    invalid_code, invalid_log = machine.execute(f"{store} --check-validity {bad_out} 2>&1")
    assert invalid_code != 0 and "is not valid" in invalid_log, invalid_log
    # A failed builtin fetch may leave an unregistered partial file. Measure it;
    # neither its presence nor a failed command alone establishes recovery.
    residual_present = machine.execute(f"test -e {bad_out} || test -L {bad_out}")[0] == 0
    residual_hash = None
    if residual_present:
        machine.succeed(f"test -f {bad_out}", f"test ! -L {bad_out}")
        residual_hash = machine.succeed(f"sha256sum {bad_out}").split()[0]
        assert residual_hash != hashlib.sha256(expected.encode()).hexdigest(), residual_hash
    evidence = {
        "schemaVersion": 2,
        "scope": "Synthetic fixed-output fixture in one disposable guest; no off-host or independent restoration claim",
        "canonical": False,
        "features": {"services": False, "retention": True, "registryExport": False,
                     "managedServiceUnitsAbsent": True, "diagnosticSnapshotsAbsent": True},
        "recipe": good, "source": source, "output": out,
        "retentionMechanism": "system closure recipe reference; baseline realized in isolated guest",
        "baseline": {"initiallyPresent": initially_present,
                     "initiallyRegistered": initially_registered,
                     "establishedWithRepair": True},
        "gc": {"unrootedControlCollected": True, "recipesAndInputRetained": True,
               "realizedOutputRetainedUnderNormalPolicy": True},
        "offline": {"daemonPrivateNetwork": True, "interfaces": ["lo"],
                    "routes": routes, "substitutionEnabled": False, "remoteBuilders": []},
        "recovery": {"outputRemovedWithScopedKeepOutputsOverride": True,
                     "narHashBefore": before, "narHashAfter": after,
                     "payloadSha256": hashlib.sha256(restored.encode()).hexdigest(),
                     "sameBytes": True},
        "missingInput": {"recipe": bad, "recipeRetained": True,
                         "retentionMechanism": "explicit guest test gcroot, created after boot",
                         "realizationFailed": True, "failureExitCode": failure_code,
                         "failureLog": failure_log,
                         "validOutputRegistered": False,
                         "residualFilePresent": residual_present,
                         "residualPayloadSha256": residual_hash,
                         "expectedPayloadPresent": False,
                         "recoveryStatus": "unresolved"},
    }
    with open(os.path.join(os.environ["out"], "recovery.json"), "w") as f:
        json.dump(evidence, f, indent=2)
  '';
}
