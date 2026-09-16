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
      enable = true;
      peers = { sideband.ipv4 = "127.0.0.2"; echo.ipv4 = "127.0.0.3"; };
      contracts = {
        first = contract [ "sideband" ] [ "127.0.0.2=reachable=sideband" "127.0.0.3=blocked=echo" ];
        changed = contract [ "echo" ] [ "127.0.0.2=blocked=sideband" "127.0.0.3=reachable=echo" ];
        empty = contract [] [ "127.0.0.2=blocked=sideband" "127.0.0.3=blocked=echo" ];
      };
      chandas = { first = budget; changed = budget; empty = budget; };
    };
  };
  testScript = ''
    import json, os
    start_all()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("setpriv --reuid=nobody --regid=nogroup --clear-groups touch /srv/sandhi-write-control/host-control")
    for ip, body in [("127.0.0.2", "sideband"), ("127.0.0.3", "echo")]:
        machine.wait_until_succeeds(f"curl --noproxy '*' --fail --max-time 3 http://{ip}:8080/ | grep -x {body}")
    evidence = {}
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
    with open(os.path.join(os.environ["out"], "reachability.json"), "w") as f:
        json.dump(evidence, f, indent=2)
  '';
}
