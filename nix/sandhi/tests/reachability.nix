{ pkgs }:
let
  probe = pkgs.writeScriptBin "sandhi-probe" ''
    #!${pkgs.python3}/bin/python3
    import errno, json, pathlib, sys, urllib.request, urllib.error
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    observations = []
    for spec in sys.argv[1:]:
        ip, expected, expected_body = spec.split("=")
        try:
            with opener.open("http://" + ip + ":8080/", timeout=3) as response:
                body = response.read().decode().strip()
            actual = "reachable" if body == expected_body else "wrong-body"
        except urllib.error.HTTPError as error:
            # An HTTP response demonstrates reachability; it is not a packet denial.
            actual, body = "http-error", str(error)
        except urllib.error.URLError as error:
            actual, body = "blocked", str(error)
        observations.append(dict(ip=ip, expected=expected, actual=actual, detail=body))
    pathlib.Path("owned-state").write_text("writable")
    # The host control proves this directory is writable by an ordinary user.
    # Require EROFS specifically: EACCES alone could merely be file ownership.
    try:
        pathlib.Path("/srv/sandhi-write-control/forbidden").write_text("bad")
        write_errno = None
    except OSError as error:
        write_errno = error.errno
    protected = write_errno == errno.EROFS
    result = dict(network=observations, owned_state=True,
                  system_write_blocked=protected, write_errno=write_errno)
    pathlib.Path("result.json.tmp").write_text(json.dumps(result))
    pathlib.Path("result.json.tmp").replace("result.json")
    sys.exit(0 if protected and all(x["expected"] == x["actual"] for x in observations) else 1)
  '';
  pathProbe = pkgs.writeScriptBin "sandhi-required-path-probe" ''
    #!${pkgs.python3}/bin/python3
    import errno, json, pathlib, sys
    # This is the first workload action: namespace failure must prevent it.
    pathlib.Path("executed").write_text("started")
    required = pathlib.Path("/srv/sandhi-required-path")
    readable = (required / "reference").read_text() == "required-reference"
    try:
        (required / "forbidden").write_text("bad")
        write_errno = None
    except OSError as error:
        write_errno = error.errno
    record = dict(requiredPathReadable=readable, writeErrno=write_errno,
                  requiredPathReadOnly=write_errno == errno.EROFS)
    pathlib.Path("result.json").write_text(json.dumps(record))
    sys.exit(0 if readable and write_errno == errno.EROFS else 1)
  '';
  budget = { cpuPercent = 100; memoryMiB = 192; retries = 0; runtimeMaxSec = 90; };
  contract = peers: args: {
    karana = probe; sampradana = peers; arguments = args;
    adhikarana = "backplane"; startAtBoot = false;
  };
in pkgs.testers.runNixOSTest {
  name = "sandhi-declared-reach";
  requiredFeatures.kvm = false;
  globalTimeout = 900;
  nodes.machine = { ... }: {
    imports = [ ../modules ];
    virtualisation.memorySize = 1536;
    virtualisation.cores = 2;
    virtualisation.vlans = []; # Single guest, loopback fixtures; no host-side switch needed.
    environment.systemPackages = [ pkgs.curl pkgs.bpftools ];
    systemd.tmpfiles.rules = [ "d /srv/sandhi-write-control 1777 root root -" ];
    systemd.services.sideband-fixture = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 -m http.server 8080 --bind 127.0.0.2 --directory ${pkgs.writeTextDir "index.html" "sideband"}";
    };
    systemd.services.echo-fixture = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 -m http.server 8080 --bind 127.0.0.3 --directory ${pkgs.writeTextDir "index.html" "echo"}";
    };
    sandhi = {
      services.enable = true; # Exercise execution without retention or export.
      peers = { sideband.ipv4 = "127.0.0.2"; echo.ipv4 = "127.0.0.3"; };
      contracts = {
        first = contract [ "sideband" ] [ "127.0.0.2=reachable=sideband" "127.0.0.3=blocked=echo" ];
        changed = contract [ "echo" ] [ "127.0.0.2=blocked=sideband" "127.0.0.3=reachable=echo" ];
        empty = contract [] [ "127.0.0.2=blocked=sideband" "127.0.0.3=blocked=echo" ];
        required-path = {
          karana = pathProbe; adhikarana = "backplane"; startAtBoot = false;
          karman.affected = [ "/srv/sandhi-required-path" ];
        };
      };
      chandas = { first = budget; changed = budget; empty = budget; required-path = budget; };
    };
  };
  testScript = ''
    import hashlib, json, os
    start_all()
    machine.wait_for_unit("multi-user.target")
    for snapshot in ["claims", "lopa", "contracts"]:
        machine.succeed(f"test ! -e /etc/sandhi/{snapshot}.json")
    machine.succeed("setpriv --reuid=nobody --regid=nogroup --clear-groups touch /srv/sandhi-write-control/host-control")
    for ip, body in [("127.0.0.2", "sideband"), ("127.0.0.3", "echo")]:
        machine.wait_until_succeeds(f"curl --noproxy '*' --fail --max-time 3 http://{ip}:8080/ | grep -x {body}")
    evidence = {"features": {"services": True, "retention": False, "registryExport": False,
                             "diagnosticSnapshotsAbsent": True}}
    for name in ["first", "changed", "empty"]:
        unit = f"sandhi-contract-{name}.service"
        machine.succeed(f"systemctl start {unit}")
        machine.wait_until_succeeds(
            f"systemctl show {unit} -p ActiveState --value | grep -Ex 'inactive|failed'", timeout=120)
        machine.succeed(f"test $(systemctl show {unit} -p Result --value) = success")
        machine.succeed(f"test $(systemctl show {unit} -p ExecMainStatus --value) = 0")
        path = f"/var/lib/sandhi-contract-{name}/result.json"
        machine.succeed(f"test -f {path}")
        record = json.loads(machine.succeed(f"cat {path}"))
        assert all(r["actual"] == r["expected"] for r in record["network"]), record
        assert record["system_write_blocked"] and record["owned_state"], record
        evidence[name] = record
    # Confirm controls remain healthy after the negative probes.
    for ip, body in [("127.0.0.2", "sideband"), ("127.0.0.3", "echo")]:
        machine.succeed(f"curl --noproxy '*' --fail --max-time 3 http://{ip}:8080/ | grep -x {body}")
    machine.succeed("test ! -e /srv/sandhi-write-control/forbidden")

    # Same generated unit, first missing its required path, then with it present.
    unit = "sandhi-contract-required-path.service"
    state = "/var/lib/sandhi-contract-required-path"
    definition = machine.succeed(f"systemctl cat {unit}")
    machine.succeed("test ! -e /srv/sandhi-required-path", f"test ! -e {state}/executed")
    # Type=simple may report a successful start job before namespace setup fails.
    start_code, _ = machine.execute(f"systemctl start {unit}")
    machine.wait_until_succeeds(
        f"test $(systemctl show {unit} -p ExecMainStatus --value) = 226", timeout=30)
    failure_result = machine.succeed(f"systemctl show {unit} -p Result --value").strip()
    machine.succeed(f"systemctl stop {unit}") # Cancel any pending automatic retry.
    journal = machine.succeed(f"journalctl -b -u {unit} --no-pager -o cat")
    assert "/srv/sandhi-required-path" in journal and "No such file or directory" in journal, journal
    assert "NAMESPACE" in journal, journal
    machine.succeed(f"test ! -e {state}/executed", f"test ! -e {state}/result.json")

    machine.succeed("install -d -m 1777 /srv/sandhi-required-path",
                    "printf '%s' required-reference > /srv/sandhi-required-path/reference",
                    "chmod 644 /srv/sandhi-required-path/reference",
                    "setpriv --reuid=nobody --regid=nogroup --clear-groups touch /srv/sandhi-required-path/host-control")
    machine.succeed(f"systemctl reset-failed {unit}", f"systemctl start {unit}")
    machine.wait_until_succeeds(
        f"systemctl show {unit} -p ActiveState --value | grep -Ex 'inactive|failed'", timeout=30)
    machine.succeed(f"test $(systemctl show {unit} -p Result --value) = success",
                    f"test $(systemctl show {unit} -p ExecMainStatus --value) = 0",
                    f"test -f {state}/executed",
                    "test ! -e /srv/sandhi-required-path/forbidden")
    assert machine.succeed(f"systemctl cat {unit}") == definition
    record = json.loads(machine.succeed(f"cat {state}/result.json"))
    assert record["requiredPathReadable"] and record["requiredPathReadOnly"], record
    evidence["requiredPath"] = {
        "path": "/srv/sandhi-required-path", "sameUnitDefinition": True,
        "unitDefinitionSha256": hashlib.sha256(definition.encode()).hexdigest(),
        "missing": {"startJobExitCode": start_code, "execMainStatus": 226,
                    "result": failure_result, "workloadMarkerAbsent": True,
                    "journal": journal},
        "present": {"hostUnprivilegedWriteSucceeded": True, "workloadExecuted": True,
                    **record},
    }
    with open(os.path.join(os.environ["out"], "reachability.json"), "w") as f:
        json.dump(evidence, f, indent=2)
  '';
}
