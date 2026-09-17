{ pkgs }:
let
  payload = "Sandhi recovery fixture: the recipe needs its source.\n";
  source = builtins.toFile "sandhi-recovery-input" payload;
  # The builtin fetcher keeps this experiment small: no compiler toolchain is
  # smuggled in through a shell builder's derivation closure.
  fixture = name: url: builtins.derivation {
    inherit name url;
    system = "builtin";
    builder = "builtin:fetchurl";
    outputHashAlgo = "sha256";
    outputHashMode = "flat";
    outputHash = builtins.hashString "sha256" payload;
    executable = false;
    unpack = false;
    preferLocalBuild = true;
    allowSubstitutes = false;
  };
  recoverable = fixture "sandhi-recoverable" "file://${source}";
  unavailable = fixture "sandhi-unavailable" "file:///sandhi-intentionally-missing-input";
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
    # All store mutations below explicitly select this daemon. A root client's
    # implicit local store would evade the network condition being tested.
    systemd.services.nix-daemon.serviceConfig.PrivateNetwork = true;
    sandhi = {
      enable = true;
      retainedRecipes = [ recoverable unavailable ];
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
    store = "NIX_REMOTE=daemon nix-store"
    no_builders = shlex.quote("")
    good = "${recipe recoverable}"
    bad = "${recipe unavailable}"
    source = "${source}"
    expected = ${builtins.toJSON payload}

    def query(arguments):
        return machine.succeed(f"{store} {arguments}").strip()

    def nar_hash(path):
        return query(f"--query --hash {shlex.quote(path)}")

    out = query(f"--query --outputs {good}")
    bad_out = query(f"--query --outputs {bad}")
    machine.succeed(f"test ! -e {out}", f"test ! -e {bad_out}")
    closure = query("--query --requisites /run/current-system").splitlines()
    assert good in closure and bad in closure and source in closure, closure

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

    orphan = query("--add-text sandhi-unrooted-control disposable-fixture")
    machine.succeed(f"{store} --gc")
    machine.succeed(f"test ! -e {orphan}", f"test -f {good}", f"test -f {bad}", f"test -f {source}")
    query(f"--realise {good} --option substitute false --option builders {no_builders}")
    before = nar_hash(out)
    assert machine.succeed(f"cat {out}") == expected
    machine.succeed(f"{store} --gc")
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
    machine.fail(f"{store} --realise {bad} --option substitute false --option builders {no_builders}")
    machine.succeed(f"test -f {bad}", f"test ! -e {bad_out}")
    gap = json.loads(machine.succeed("cat /etc/sandhi/lopa.json"))["unavailable-fixture"]
    assert gap["recoveryEvidence"] == [] and gap["availability"] == "absent", gap
    evidence = {
        "schemaVersion": 1,
        "scope": "Synthetic fixed-output fixture in one disposable guest; no off-host or independent restoration claim",
        "canonical": False,
        "recipe": good, "source": source, "output": out,
        "gc": {"unrootedControlCollected": True, "recipesAndInputRetained": True,
               "realizedOutputRetainedUnderNormalPolicy": True},
        "offline": {"daemonPrivateNetwork": True, "interfaces": ["lo"],
                    "routes": routes, "substitutionEnabled": False, "remoteBuilders": []},
        "recovery": {"outputRemovedWithScopedKeepOutputsOverride": True,
                     "narHashBefore": before, "narHashAfter": after,
                     "payloadSha256": hashlib.sha256(restored.encode()).hexdigest(),
                     "sameBytes": True},
        "missingInput": {"recipe": bad, "recipeRetained": True,
                         "realizationFailed": True, "outputAbsent": True,
                         "recoveryStatus": "unresolved"},
    }
    with open(os.path.join(os.environ["out"], "recovery.json"), "w") as f:
        json.dump(evidence, f, indent=2)
  '';
}
