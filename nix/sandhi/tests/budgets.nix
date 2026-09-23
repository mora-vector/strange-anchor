{ pkgs }:
let
  probe = pkgs.writeScriptBin "sandhi-budget-probe" ''
    #!${pkgs.python3}/bin/python3
    import pathlib, sys, time
    mode = sys.argv[1]
    with open("attempts", "a") as f:
        f.write("started\n")
    pathlib.Path("ready").touch()
    if mode == "retry":
        sys.exit(42)
    elif mode == "timeout":
        time.sleep(float(sys.argv[2]))
    elif mode == "memory":
        # Let the driver establish a live process before allocation.
        while not pathlib.Path("go").exists():
            time.sleep(0.05)
        chunks = [bytearray(1024 * 1024) for _ in range(96)]
    elif mode == "cpu":
        until = time.monotonic() + 60
        while time.monotonic() < until:
            pass
    pathlib.Path("completed").touch()
  '';
  capture = pkgs.writeScript "sandhi-budget-stop-observation" ''
    #!${pkgs.python3}/bin/python3
    import json, os, pathlib
    group = next(line.split(":", 2)[2] for line in
                 pathlib.Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
    directory = pathlib.Path("/sys/fs/cgroup" + group)
    record = {"serviceResult": os.environ.get("SERVICE_RESULT"),
              "exitCode": os.environ.get("EXIT_CODE"), "exitStatus": os.environ.get("EXIT_STATUS")}
    for name in ["memory.events", "memory.max", "cpu.stat", "cpu.max"]:
        record[name] = (directory / name).read_text()
    pathlib.Path("stop.json").write_text(json.dumps(record))
  '';
  names = [ "timeout" "timeout-ok" "retry-zero" "retry-two" "memory" "memory-ok" "cpu" "cpu-control" ];
  contract = args: { karana = probe; arguments = args; adhikarana = "backplane"; startAtBoot = false; };
  budget = { cpuPercent = 100; memoryMiB = 192; retries = 0; windowSec = 300; runtimeMaxSec = 90; };
in pkgs.testers.runNixOSTest {
  name = "sandhi-budget-behavior";
  requiredFeatures.kvm = false;
  globalTimeout = 600;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules ];
    virtualisation = { memorySize = 1536; cores = 2; vlans = []; };
    swapDevices = []; # Explicit test condition, not a compiler swap guarantee.
    sandhi = {
      services.enable = true;
      contracts = {
        timeout = contract [ "timeout" "60" ];
        timeout-ok = contract [ "timeout" "0.1" ];
        retry-zero = contract [ "retry" ];
        retry-two = contract [ "retry" ];
        memory = contract [ "memory" ];
        memory-ok = contract [ "memory" ];
        cpu = contract [ "cpu" ];
        cpu-control = contract [ "cpu" ];
      };
      chandas = {
        timeout = budget // { runtimeMaxSec = 3; };
        timeout-ok = budget // { runtimeMaxSec = 3; };
        retry-zero = budget;
        retry-two = budget // { retries = 2; };
        memory = budget // { memoryMiB = 64; };
        memory-ok = budget;
        cpu = budget // { cpuPercent = 10; };
        cpu-control = budget;
      };
    };
    # Observation only: the compiler's ExecStart and budget controls are intact.
    systemd.services = lib.genAttrs (map (n: "sandhi-contract-${n}") names)
      (_: { serviceConfig.ExecStopPost = "${capture}"; });
  };
  testScript = ''
    import json, os, time
    start_all()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("test $(wc -l < /proc/swaps) = 1")
    evidence: dict[str, object] = {"swapEnabled": False, "scope": "one disposable guest"}

    def unit(name):
        return f"sandhi-contract-{name}.service"

    def state(name):
        return f"/var/lib/sandhi-contract-{name}"

    def start(name):
        machine.succeed(f"systemctl start {unit(name)}")
        machine.wait_until_succeeds(f"test -e {state(name)}/ready", timeout=30)

    def stopped(name, failed):
        wanted = "failed" if failed else "inactive"
        machine.wait_until_succeeds(
            f"test $(systemctl show {unit(name)} -p ActiveState --value) = {wanted}", timeout=60)
        return json.loads(machine.succeed(f"cat {state(name)}/stop.json"))

    for name in ["timeout", "timeout-ok"]:
        start(name)
        record = stopped(name, name == "timeout")
        journal = machine.succeed(f"journalctl -b -u {unit(name)} --no-pager -o cat")
        expected = "timeout" if name == "timeout" else "success"
        assert record["serviceResult"] == expected, record
        check = "test ! -e" if name == "timeout" else "test -e"
        machine.succeed(f"{check} {state(name)}/completed")
        assert int(machine.succeed(f"wc -l < {state(name)}/attempts")) == 1
        evidence[name] = {"stop": record, "journal": journal}

    for name, count in [("retry-zero", 1), ("retry-two", 3)]:
        start(name)
        record = stopped(name, True)
        assert record["serviceResult"] == "exit-code" and record["exitStatus"] == "42", record
        assert int(machine.succeed(f"wc -l < {state(name)}/attempts")) == count
        machine.succeed(f"test $(systemctl show {unit(name)} -p Result --value) = start-limit-hit")
        # An additional manual start inside the window must also be denied.
        machine.fail(f"systemctl start {unit(name)}")
        time.sleep(3)
        assert int(machine.succeed(f"wc -l < {state(name)}/attempts")) == count
        evidence[name] = {"attempts": count, "windowSec": 300, "extraStartDenied": True,
                          "stop": record, "journal": machine.succeed(f"journalctl -b -u {unit(name)} --no-pager -o cat")}

    for name in ["memory", "memory-ok"]:
        start(name)
        machine.succeed(f"touch {state(name)}/go")
        record = stopped(name, name == "memory")
        events = dict(line.split() for line in record["memory.events"].splitlines())
        if name == "memory":
            assert record["serviceResult"] == "oom-kill", record
            assert int(events["oom_kill"]) > 0, record
            assert int(record["memory.max"]) == 64 * 1024 * 1024, record
            machine.succeed(f"test ! -e {state(name)}/completed")
        else:
            assert record["serviceResult"] == "success" and int(events["oom_kill"]) == 0, record
            machine.succeed(f"test -e {state(name)}/completed")
        evidence[name] = {"allocationMiB": 96, "stop": record,
                          "journal": machine.succeed(f"journalctl -b -u {unit(name)} --no-pager -o cat")}

    for name in ["cpu", "cpu-control"]:
        start(name)
    # Measure kernel counters and elapsed time in the guest's clock domain.
    sample = machine.succeed("${pkgs.python3}/bin/python3 - <<'PY'\n"
        "import json, pathlib, time\n"
        "def read(name):\n"
        "    p = pathlib.Path('/sys/fs/cgroup/system.slice/sandhi-contract-' + name + '.service')\n"
        "    return {'quota': (p / 'cpu.max').read_text(), 'stats': dict((k, int(v)) for k, v in (line.split() for line in (p / 'cpu.stat').read_text().splitlines()))}\n"
        "names = ['cpu', 'cpu-control']\n"
        "before = {n: read(n) for n in names}\n"
        "t = time.monotonic()\n"
        "time.sleep(6)\n"
        "after = {n: read(n) for n in names}\n"
        "print(json.dumps({'before': before, 'after': after, 'elapsedSec': time.monotonic() - t}))\nPY")
    cpu = json.loads(sample)
    limited = cpu["after"]["cpu"]["stats"]
    initial = cpu["before"]["cpu"]["stats"]
    quota, period = map(int, cpu["after"]["cpu"]["quota"].split())
    assert quota / period == 0.1, cpu
    assert limited["nr_throttled"] > initial["nr_throttled"], cpu
    assert limited["throttled_usec"] > initial["throttled_usec"], cpu
    usage = limited["usage_usec"] - initial["usage_usec"]
    control = cpu["after"]["cpu-control"]["stats"]["usage_usec"] - cpu["before"]["cpu-control"]["stats"]["usage_usec"]
    assert 0 < usage / (cpu["elapsedSec"] * 1000000) < 0.3, cpu
    assert control > usage, cpu
    evidence["cpu"] = cpu
    for name in ["cpu", "cpu-control"]:
        machine.succeed(f"systemctl is-active {unit(name)}", f"systemctl stop {unit(name)}")
    with open(os.path.join(os.environ["out"], "budgets.json"), "w") as f:
        json.dump(evidence, f, indent=2)
  '';
}
