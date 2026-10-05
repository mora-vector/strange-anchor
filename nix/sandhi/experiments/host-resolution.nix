# Experiment 0: can a Sandhi contract resolve names through the host's
# name-service socket, and does a name chosen inside the contract reach an
# upstream its IP filter does not admit? Scope: DECISIONS.md, 2026-10-05.
#
# A measurement, not a flake check. It passes or fails only on its controls;
# each trial's outcome is recorded whichever way the hypothesis falls.
#
#   nix build --impure -L --expr \
#     'let f = builtins.getFlake "path:'"$PWD"'"; in import ./experiments/host-resolution.nix
#        { pkgs = import f.inputs.nixpkgs { system = "x86_64-linux"; }; }'
{ pkgs }:
let
  upstream = "127.0.0.4";
  zone = "exp0.sandhi.test";
  probe = pkgs.writeScriptBin "sandhi-exp0-probe" ''
    #!${pkgs.python3}/bin/python3
    import json, os, pathlib, secrets, socket, struct, sys, urllib.request

    token = secrets.token_hex(8)
    result = {"lookupName": f"c-{token}.${zone}", "directName": f"d-{token}.${zone}"}

    # 1. Resolution through glibc, which consults the nscd socket first.
    try:
        infos = socket.getaddrinfo(result["lookupName"], None, socket.AF_INET,
                                   socket.SOCK_STREAM)
        result["lookup"] = {"outcome": "resolved",
                            "addresses": sorted({i[4][0] for i in infos})}
    except socket.gaierror as error:
        result["lookup"] = {"outcome": "failed", "error": f"{error.errno}: {error.strerror}"}

    # 2. What the contract can see of the socket glibc uses.
    for path in ["/var/run/nscd/socket", "/run/nscd/socket"]:
        try:
            st = os.stat(path)
            result.setdefault("socketView", {})[path] = {"visible": True,
                                                         "mode": oct(st.st_mode)}
        except OSError as error:
            result.setdefault("socketView", {})[path] = {"visible": False,
                                                         "error": error.strerror}

    # 3. A direct query to the upstream, which the IP filter should stop.
    labels = result["directName"].split(".")
    question = b"".join(bytes([len(l)]) + l.encode() for l in labels) + b"\0"
    query = struct.pack(">HHHHHH", 0x5a5a, 0x0100, 1, 0, 0, 0) + question + struct.pack(">HH", 1, 1)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.sendto(query, ("${upstream}", 53))
        data, _ = s.recvfrom(512)
        result["direct"] = {"outcome": "answered", "bytes": len(data)}
    except socket.timeout:
        result["direct"] = {"outcome": "timeout"}
    except OSError as error:
        result["direct"] = {"outcome": "error", "error": f"{error.errno}: {error.strerror}"}

    # 4. Positive control for networked contracts: the declared peer is reachable.
    if len(sys.argv) > 1:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(f"http://{sys.argv[1]}:8080/", timeout=3) as response:
                result["peer"] = {"outcome": "reachable", "body": response.read().decode().strip()}
        except Exception as error:
            result["peer"] = {"outcome": "failed", "error": str(error)}

    pathlib.Path("result.json.tmp").write_text(json.dumps(result))
    pathlib.Path("result.json.tmp").replace("result.json")
  '';
  budget = { cpuPercent = 100; memoryMiB = 192; retries = 0; runtimeMaxSec = 90; };
  contract = peers: args: {
    karana = probe; sampradana = peers; arguments = args;
    adhikarana = "backplane"; startAtBoot = false;
  };
  trials = [ "empty" "networked" "empty-blocked" "networked-blocked" ];
in pkgs.testers.runNixOSTest {
  name = "sandhi-experiment0-host-resolution";
  requiredFeatures.kvm = false;
  globalTimeout = 900;
  nodes.machine = { ... }: {
    imports = [ ../modules ];
    virtualisation.memorySize = 1536;
    virtualisation.cores = 2;
    virtualisation.vlans = [];
    environment.systemPackages = [ pkgs.curl ];
    # The guest's only resolver is the logging fixture.
    networking.nameservers = [ upstream ];
    systemd.services.exp0-upstream = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.dnsmasq}/bin/dnsmasq --keep-in-foreground"
        + " --no-resolv --no-hosts --no-poll --bind-interfaces --listen-address=${upstream}"
        + " --port=53 --address=/${zone}/127.0.0.9 --log-queries --log-facility=-"
        + " --user=nobody --group=nogroup --pid-file=/run/exp0-upstream.pid";
    };
    systemd.services.sideband-fixture = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 -m http.server 8080 --bind 127.0.0.2 --directory ${pkgs.writeTextDir "index.html" "sideband"}";
    };
    sandhi = {
      services.enable = true;
      peers.sideband.ipv4 = "127.0.0.2";
      contracts = {
        empty = contract [] [];
        networked = contract [ "sideband" ] [ "127.0.0.2" ];
        empty-blocked = contract [] [];
        networked-blocked = contract [ "sideband" ] [ "127.0.0.2" ];
      };
      chandas = pkgs.lib.genAttrs trials (_: budget);
    };
    # Socket-blocked comparison: a test-local override, not a module change.
    systemd.services."sandhi-contract-empty-blocked".serviceConfig.InaccessiblePaths = [ "/run/nscd" ];
    systemd.services."sandhi-contract-networked-blocked".serviceConfig.InaccessiblePaths = [ "/run/nscd" ];
  };
  testScript = ''
    import json, os, re, uuid
    start_all()
    machine.wait_for_unit("multi-user.target")
    for unit in ["nscd.service", "exp0-upstream.service", "sideband-fixture.service"]:
        machine.wait_for_unit(unit)
    machine.wait_until_succeeds("curl --noproxy '*' --fail --max-time 3 http://127.0.0.2:8080/ | grep -x sideband")

    def upstream_lines(name):
        machine.succeed("journalctl --sync")
        log = machine.succeed("journalctl -b -u exp0-upstream.service --no-pager -o cat")
        return [line for line in log.splitlines() if name in line]

    def host_control(label):
        name = f"h-{uuid.uuid4().hex[:16]}.${zone}"
        status, out = machine.execute(f"getent ahostsv4 {name}")
        machine.sleep(2)
        lines = upstream_lines(name)
        record = {"name": name, "getentExit": status, "getentOutput": out.strip(),
                  "upstreamLines": lines}
        assert status == 0 and "127.0.0.9" in out, (label, record)
        assert lines, (label, record)
        return record

    env = {
        "resolvConf": machine.succeed("cat /etc/resolv.conf"),
        "nsswitchHosts": machine.succeed("grep -E '^hosts:' /etc/nsswitch.conf").strip(),
        "socketLs": machine.succeed("ls -la /run/nscd/; readlink -f /var/run/nscd/socket || true"),
        "nscdExecStart": machine.succeed("systemctl show nscd.service -p ExecStart --value").strip(),
        "upstreamVersion": machine.succeed("${pkgs.dnsmasq}/bin/dnsmasq --version | head -1").strip(),
        "kernel": machine.succeed("uname -r").strip(),
    }
    controls: dict[str, object] = {"hostBefore": host_control("before")}

    trials: dict[str, object] = {}
    for name in ${builtins.toJSON trials}:
        unit = f"sandhi-contract-{name}.service"
        machine.succeed(f"systemctl start {unit}")
        machine.wait_until_succeeds(
            f"systemctl show {unit} -p ActiveState --value | grep -Ex 'inactive|failed'", timeout=150)
        result_code = machine.succeed(f"systemctl show {unit} -p Result --value").strip()
        props = machine.succeed(f"systemctl show {unit} -p InaccessiblePaths -p PrivateNetwork -p IPAddressAllow -p RestrictAddressFamilies")
        machine.sleep(3)  # A negative must survive a settling interval.
        record = json.loads(machine.succeed(f"cat /var/lib/sandhi-contract-{name}/result.json"))
        record["unitResult"] = result_code
        record["unitProperties"] = props.strip().splitlines()
        record["upstreamLookupLines"] = upstream_lines(record["lookupName"])
        record["upstreamDirectLines"] = upstream_lines(record["directName"])
        record["upstreamSources"] = sorted({m.group(1) for l in record["upstreamLookupLines"] + record["upstreamDirectLines"]
                                            for m in [re.search(r" from (\S+)$", l)] if m})
        assert result_code == "success", (name, record)
        if name.startswith("networked"):
            assert record.get("peer", {}).get("body") == "sideband", (name, record)
        trials[name] = record

    controls["hostAfter"] = host_control("after")
    machine.succeed("curl --noproxy '*' --fail --max-time 3 http://127.0.0.2:8080/ | grep -x sideband")
    evidence = {
        "scope": "Experiment 0 (DECISIONS.md 2026-10-05); one disposable guest; controls gate the run, trials are recorded either way",
        "canonical": False, "environment": env, "controls": controls, "trials": trials,
    }
    with open(os.path.join(os.environ["out"], "experiment0.json"), "w") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)
  '';
}
