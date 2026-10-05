# Stage A: standalone transport between two separately configured Sandhi
# installations. Scope: DECISIONS.md, 2026-10-05 (Stage A adopted), and
# docs/SCOPE-STAGE-A-TRANSPORT.md. Deterministic responders: this is a transport
# test, not an AI conversation. Two guests on one builder are separate
# installations, not independent administration.
#
# A measurement, not a flake check. All eleven assertions are recorded whichever way
# they fall; the build fails only when provisioning or a harness control fails.
#
#   nix build --impure -L --expr \
#     'let f = builtins.getFlake "path:'"$PWD"'"; in import ./experiments/standalone-exchange.nix
#        { pkgs = import f.inputs.nixpkgs { system = "x86_64-linux"; }; }'
{ pkgs }:
let
  lib = pkgs.lib;
  exchange = import ../packages/sandhi-exchange.nix { inherit pkgs; };
  port = 7443;
  controlPort = 7444;
  addresses = { a = "192.168.1.10"; b = "192.168.1.20"; c = "192.168.1.30"; };
  ids = { a = "installation-a"; b = "installation-b"; };
  credentials = "/run/sandhi-exchange-credentials";
  trialDir = "/run/sandhi-exchange-trial";

  guest = self: { ... }: {
    virtualisation = { memorySize = 1024; cores = 1; vlans = [ 1 ]; };
    # The scope fixes these addresses; the framework's defaults would be .1 to .3.
    networking.interfaces.eth1.ipv4.addresses =
      lib.mkForce [ { address = addresses.${self}; prefixLength = 24; } ];
    environment.systemPackages = [ exchange pkgs.openssl pkgs.iproute2 ];
  };

  installation = self: peer: { lib, ... }: {
    imports = [ ../modules (guest self) ];
    networking.firewall.allowedTCPPorts = [ port controlPort ];
    sandhi = {
      services.enable = true;
      peers.${peer}.ipv4 = addresses.${peer};
      contracts.exchange = {
        kartr = "exchange";
        karman.state = "exchange";
        karana = exchange;
        arguments = [ "--config" "${pkgs.writeText "exchange-${self}.json" (builtins.toJSON {
          local_id = ids.${self}; peer_id = ids.${peer}; opener = self == "a";
          responder = [ "${exchange}/bin/sandhi-exchange-responder" ];
          listen_address = addresses.${self}; inherit port;
          peer_address = addresses.${peer}; peer_port = port;
        })}" ];
        sampradana = [ peer ];
        adhikarana = "backplane";
        startAtBoot = false;
      };
      # Adopted budgets: four starts per 600 s window, 600 s per attempt.
      chandas.exchange = { cpuPercent = 50; memoryMiB = 192; retries = 3; windowSec = 600;
                           runtimeMaxSec = 600; };
    };
    # Test-local override, not a module change: keys and driver inputs arrive as
    # systemd credentials, outside the Nix store.
    systemd.services.sandhi-contract-exchange.serviceConfig.LoadCredential = [
      "cert:${credentials}/cert.pem" "key:${credentials}/key.pem"
      "trust:${credentials}/trust.pem" "map:${credentials}/map.json"
      "input:${trialDir}/input" "trial:${trialDir}/trial.json"
    ];
    # Ephemeral installation key pair, generated in the guest at boot.
    systemd.services.sandhi-exchange-credentials = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig = { Type = "oneshot"; RemainAfterExit = true; UMask = "0077"; };
      path = [ pkgs.openssl ];
      script = ''
        install -d -m 0700 ${credentials}
        openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 2 \
          -subj "/CN=${ids.${self}}" -addext "basicConstraints=critical,CA:TRUE" \
          -addext "keyUsage=critical,digitalSignature,keyCertSign" \
          -keyout ${credentials}/key.pem -out ${credentials}/cert.pem
      '';
    };
    # Control listener outside any contract: shows the network path to this host
    # is open, so a refusal on the contract port is attributable to the contract.
    systemd.services.exchange-control-listener = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 -m http.server ${toString controlPort}"
        + " --bind ${addresses.${self}} --directory ${pkgs.writeTextDir "index.html" self}";
    };
  };
in pkgs.testers.runNixOSTest {
  name = "sandhi-stage-a-standalone-exchange";
  requiredFeatures.kvm = false;
  globalTimeout = 2400;
  nodes = {
    a = installation "a" "b";
    b = { lib, ... }: {
      imports = [ (installation "b" "a") ];
      # Peer withdrawal: the next activation no longer admits installation-a.
      specialisation.withdrawn.configuration = {
        sandhi.peers = lib.mkForce { elsewhere.ipv4 = "192.168.1.40"; };
        sandhi.contracts.exchange.sampradana = lib.mkForce [ "elsewhere" ];
      };
    };
    c = guest "c";
  };
  testScript = ''
    import base64, hashlib, io, json, os, secrets, shlex, tarfile, time, traceback
    from typing import Any

    UNIT = "sandhi-contract-exchange.service"
    STATE = "/var/lib/sandhi-contract-exchange"
    CRED, TRIAL = "${credentials}", "${trialDir}"
    ADDR = ${builtins.toJSON addresses}
    IDS = ${builtins.toJSON ids}
    M = {"a": a, "b": b, "c": c}
    OUT = os.environ["out"]
    started = time.monotonic()
    evidence: dict[str, Any] = {"scope": "Stage A transport test (DECISIONS.md 2026-10-05); deterministic responders;"
                         " one builder, three guests; not AI communication or independent administration",
                "canonical": False, "trials": {}, "probes": {}, "errors": []}

    def put(machine, path, data):
        encoded = base64.b64encode(data).decode()
        machine.succeed(f"install -d -m 0700 {os.path.dirname(path)} && "
                        f"echo {encoded} | base64 -d > {path} && chmod 0600 {path}")

    def fingerprint(machine, path):
        return machine.succeed(f"openssl x509 -in {path} -outform DER | sha256sum | cut -d' ' -f1").strip()

    def probe(machine, *args):
        return json.loads(machine.succeed("sandhi-exchange-probe " + " ".join(shlex.quote(a) for a in args)))

    def unit(machine):
        keys = ["ActiveState", "Result", "NRestarts", "InvocationID", "ExecMainStatus"]
        raw = machine.succeed(f"systemctl show {UNIT} " + " ".join(f"-p {k}" for k in keys))
        return dict(line.split("=", 1) for line in raw.strip().splitlines())

    # Provisioning: before any measured phase -------------------------------
    start_all()
    for name in ("a", "b", "c"):
        M[name].wait_for_unit("multi-user.target")
    for name in ("a", "b"):
        M[name].wait_for_unit("sandhi-exchange-credentials.service")
        M[name].wait_for_unit("exchange-control-listener.service")
    pem = {n: M[n].succeed(f"cat {CRED}/cert.pem") for n in ("a", "b")}
    prints = {n: fingerprint(M[n], f"{CRED}/cert.pem") for n in ("a", "b")}
    # Probe certificates, root-only on a: "extra" is trusted by b but unmapped;
    # "untrusted" is in no trust set.
    for name in ("extra", "untrusted"):
        a.succeed("install -d -m 0700 /root/probe && openssl req -x509 -newkey ec "
                  "-pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 2 "
                  f"-subj /CN=probe-{name} -addext basicConstraints=critical,CA:TRUE "
                  "-addext keyUsage=critical,digitalSignature,keyCertSign "
                  f"-keyout /root/probe/{name}.key -out /root/probe/{name}.pem 2>/dev/null")
    extra_pem = a.succeed("cat /root/probe/extra.pem")
    # Only public certificates cross between guests.
    put(a, f"{CRED}/trust.pem", pem["b"].encode())
    put(a, f"{CRED}/map.json", json.dumps({prints["b"]: IDS["b"]}).encode())
    put(b, f"{CRED}/trust.pem", (pem["a"] + extra_pem).encode())
    put(b, f"{CRED}/map.json", json.dumps({prints["a"]: IDS["a"]}).encode())
    environment: dict[str, Any] = {"fingerprints": {**{IDS[n]: prints[n] for n in ("a", "b")},
                                    "probe-extra": fingerprint(a, "/root/probe/extra.pem"),
                                    "probe-untrusted": fingerprint(a, "/root/probe/untrusted.pem")}}
    for name in ("a", "b", "c"):
        machine = M[name]
        machine.succeed("ip route del default || true")  # No route out during measurement.
        environment[name] = {
            "addresses": machine.succeed("ip -4 -o addr show").strip().splitlines(),
            "routes": machine.succeed("ip route").strip().splitlines(),
            "kernel": machine.succeed("uname -r").strip(),
            "unprivilegedPortStart": machine.succeed("sysctl -n net.ipv4.ip_unprivileged_port_start").strip(),
        }
        assert f"{ADDR[name]}/24" in " ".join(environment[name]["addresses"]), environment[name]
    for name in ("a", "b"):
        environment[name]["unit"] = M[name].succeed(
            f"systemctl show {UNIT} -p IPAddressAllow -p IPAddressDeny -p RestrictAddressFamilies "
            "-p PrivateNetwork -p DynamicUser -p ProtectSystem -p CapabilityBoundingSet -p CPUQuotaPerSecUSec "
            "-p MemoryMax -p RuntimeMaxUSec -p StartLimitBurst -p StartLimitIntervalUSec "
            "-p LoadCredential -p Restart -p RestartUSec").strip().splitlines()
    environment["package"] = "${exchange}"
    evidence["environment"] = environment

    # Harness controls: the network path is open outside the contracts.
    controls = {f"{src}->{dst}:control": probe(M[src], "connect", "--host", ADDR[dst], "--port", "${toString controlPort}")
                for src, dst in (("c", "a"), ("c", "b"), ("a", "b"), ("b", "a"))}
    evidence["controls"] = controls
    assert all(v["outcome"] == "connected" for v in controls.values()), controls

    # Trials ----------------------------------------------------------------
    def prepare(name, label, trial, value):
        machine = M[name]
        machine.succeed(f"systemctl stop {UNIT}; systemctl reset-failed {UNIT} || true; "
                        "rm -rf /var/lib/private/sandhi-contract-exchange")
        put(machine, f"{TRIAL}/trial.json", json.dumps({"label": label, **trial}).encode())
        put(machine, f"{TRIAL}/input", value.encode())

    def collect(name, label):
        data = base64.b64decode(M[name].succeed(f"tar -C {STATE}/ -cf - . | base64 -w0"))
        directory = os.path.join(OUT, "trials", label)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"{name}-state.tar"), "wb") as stream:
            stream.write(data)
        files: dict[str, bytes] = {}
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            for member in archive.getmembers():
                handle = archive.extractfile(member) if member.isfile() else None
                if handle is not None:
                    files[os.path.normpath(member.name)] = handle.read()
        return files

    def lines(files, name):
        return [json.loads(l) for l in files.get(name, b"").decode().splitlines() if l]

    def folder(files, name):
        return {k.split("/", 1)[1]: v for k, v in files.items()
                if k.startswith(name + "/") and not k.endswith(".tmp")}

    def agreement(sender, receiver):
        acks, inbox = folder(sender, "acks"), folder(receiver, "inbox")
        return {mid: inbox.get(mid) == raw for mid, raw in folder(sender, "outbox").items()
                if mid in acks and json.loads(acks[mid])["result"] in ("accepted", "duplicate")}

    def summary(files, label) -> dict[str, Any]:
        status = json.loads(files["status.json"]) if "status.json" in files else None
        return {"status": status,
                "processStarts": sum(1 for e in lines(files, "events.log") if e["event"] == "start"),
                "faultsFired": sorted(k.split("/", 1)[1] for k in files if k.startswith("faults-fired/")),
                "invocations": [e for e in lines(files, "invocations.log") if e["event"] == "invoke"],
                "attempts": lines(files, "attempts.log"),
                "events": lines(files, "events.log"),
                "ending": json.loads(files["ending.json"]) if "ending.json" in files else None}

    def run(label, faults=None, seconds=240, linger=5, keep=False, order=("b", "a")) -> dict[str, Any]:
        faults = faults or {}
        inputs = {n: secrets.token_hex(16) for n in ("a", "b")}
        expected = hashlib.sha256(bytes.fromhex(inputs["a"]) + bytes.fromhex(inputs["b"])).hexdigest()
        for name in ("a", "b"):
            prepare(name, label, {"faults": faults.get(name, []), "conversation_seconds": seconds,
                                  "linger_seconds": linger}, inputs[name])
        began = time.monotonic()
        for name in order:
            M[name].succeed(f"systemctl start {UNIT}")
        for name in order:
            M[name].wait_until_succeeds(f"test -e {STATE}/status.json", timeout=seconds + 180)
        if not keep:
            for name in order:
                M[name].wait_until_succeeds(
                    f"systemctl show {UNIT} -p ActiveState --value | grep -Ex 'inactive|failed'",
                    timeout=seconds + 180)
        return {"label": label, "faults": faults, "expectedDigest": expected,
                "secondsToStatus": round(time.monotonic() - began, 1), "seconds": seconds}

    def finish(record: dict[str, Any], keep=False):
        files: dict[str, Any] = {}
        for name in ("a", "b"):
            if keep:
                M[name].succeed(f"systemctl stop {UNIT}")
            record[name] = {"unit": unit(M[name])}
            files[name] = collect(name, record["label"])
            record[name].update(summary(files[name], record["label"]))
        record["byteAgreement"] = {"a->b": agreement(files["a"], files["b"]),
                                   "b->a": agreement(files["b"], files["a"])}
        record["complete"] = all((record[n]["status"] or {}).get("status") == "complete" and
                                 record[n]["status"].get("digest") == record["expectedDigest"]
                                 for n in ("a", "b"))
        evidence["trials"][record["label"]] = record
        return files

    def attempt(label, function):
        try:
            function()
        except Exception:
            evidence["errors"].append({"step": label, "error": traceback.format_exc()[-2000:]})

    def baseline_with_probes():
        record = run("t1-baseline", seconds=240, linger=300, keep=True)
        cert, key = f"{CRED}/cert.pem", f"{CRED}/key.pem"
        conversation = json.loads(b.succeed(f"cat {STATE}/conversation.json"))["conversation_id"]
        outbox_before = b.succeed(f"ls {STATE}/outbox").split()
        probes: dict[str, Any] = {
            # Assertion 6: the unauthorised guest, at the address filter.
            "c->a:contract": probe(c, "connect", "--host", ADDR["a"]),
            "c->b:contract": probe(c, "connect", "--host", ADDR["b"]),
            # Assertion 7, from installation-a's permitted address, as root.
            "untrusted-certificate": probe(a, "tls", "--label", "untrusted", "--host", ADDR["b"],
                "--cert", "/root/probe/untrusted.pem", "--key", "/root/probe/untrusted.key",
                "--trust", f"{CRED}/trust.pem",
                "--envelope", json.dumps({"conversation_id": conversation, "parent_id": None,
                    "sender": IDS["a"], "recipient": IDS["b"], "turn": 0, "kind": "message",
                    "payload": "probe"})),
            "trusted-unmapped-certificate": probe(a, "tls", "--label", "unmapped", "--host", ADDR["b"],
                "--cert", "/root/probe/extra.pem", "--key", "/root/probe/extra.key",
                "--trust", f"{CRED}/trust.pem",
                "--envelope", json.dumps({"conversation_id": conversation, "parent_id": None,
                    "sender": IDS["a"], "recipient": IDS["b"], "turn": 0, "kind": "message",
                    "payload": "probe"})),
            "wrong-sender": probe(a, "tls", "--label", "wrong-sender", "--host", ADDR["b"],
                "--cert", cert, "--key", key, "--trust", f"{CRED}/trust.pem",
                "--envelope", json.dumps({"conversation_id": conversation, "parent_id": None,
                    "sender": "installation-c", "recipient": IDS["b"], "turn": 0,
                    "kind": "message", "payload": "probe"})),
            "turn-8": probe(a, "tls", "--label", "turn-8", "--host", ADDR["b"],
                "--cert", cert, "--key", key, "--trust", f"{CRED}/trust.pem",
                "--envelope", json.dumps({"conversation_id": conversation, "parent_id": "0" * 32,
                    "sender": IDS["a"], "recipient": IDS["b"], "turn": 8, "kind": "message",
                    "payload": "probe"})),
            "oversize-frame": probe(a, "tls", "--label", "oversize", "--host", ADDR["b"],
                "--cert", cert, "--key", key, "--trust", f"{CRED}/trust.pem",
                "--oversize", "16385"),
        }
        time.sleep(2)
        probes["b-outbox-unchanged"] = b.succeed(f"ls {STATE}/outbox").split() == outbox_before
        evidence["probes"] = probes
        finish(record, keep=True)

    attempt("t1-baseline", baseline_with_probes)
    for label, faults in (("t2-duplicate", {"a": ["resend-acked"]}),
                          ("t3-conflict", {"a": ["conflict"]}),
                          ("t4-I1", {"b": ["I1"]}),
                          ("t5-I2", {"b": ["I2"]}),
                          ("t6-I3", {"a": ["I3"]})):
        attempt(label, lambda label=label, faults=faults: finish(run(label, faults)))

    def withdrawal():
        # Assertion 9. b listens alone; a held connection and a new one are observed
        # across an actual activation that removes installation-a's address.
        label = "t7-withdrawal"
        for name in ("a", "b"):
            prepare(name, label, {"conversation_seconds": 240, "linger_seconds": 300},
                    secrets.token_hex(16))
        b.succeed(f"systemctl start {UNIT}")
        b.wait_until_succeeds(f"ss -ltn | grep -q '{ADDR['b']}:${toString port}'", timeout=120)
        before: dict[str, Any] = {"unit": unit(b), "allow": b.succeed(f"systemctl show {UNIT} -p IPAddressAllow").strip()}
        held = json.dumps({"conversation_id": "0" * 32, "parent_id": None, "sender": "installation-c",
                           "recipient": IDS["b"], "turn": 0, "kind": "message", "payload": "held"})
        a.succeed("rm -f /tmp/release /tmp/held.json && systemd-run --unit=exchange-held "
                  "--property=StandardOutput=file:/tmp/held.json sandhi-exchange-probe tls "
                  f"--label held --host {ADDR['b']} --cert {CRED}/cert.pem --key {CRED}/key.pem "
                  f"--trust {CRED}/trust.pem --hold-until /tmp/release --hold-timeout 900 "
                  f"--envelope {shlex.quote(held)}")
        b.wait_until_succeeds(f"ss -tn state established '( sport = :${toString port} )' | grep -q {ADDR['a']}", timeout=60)
        switched = time.monotonic()
        b.succeed("/run/current-system/specialisation/withdrawn/bin/switch-to-configuration test")
        after: dict[str, Any] = {"unit": unit(b), "allow": b.succeed(f"systemctl show {UNIT} -p IPAddressAllow").strip(),
                 "switchSeconds": round(time.monotonic() - switched, 1)}
        b.wait_until_succeeds(f"systemctl is-active {UNIT}", timeout=60)
        b.wait_until_succeeds(f"ss -ltn | grep -q '{ADDR['b']}:${toString port}'", timeout=120)
        after["listening"] = True
        a.succeed("touch /tmp/release")
        a.wait_until_succeeds("systemctl show exchange-held -p ActiveState --value | grep -Ex 'inactive|failed'", timeout=60)
        result: dict[str, Any] = {"before": before, "after": after,
                  "existingConnection": json.loads(a.succeed("cat /tmp/held.json")),
                  "newConnection": probe(a, "tls", "--label", "new-after-withdrawal", "--host", ADDR["b"],
                                         "--cert", f"{CRED}/cert.pem", "--key", f"{CRED}/key.pem",
                                         "--trust", f"{CRED}/trust.pem"),
                  "controlStillOpen": probe(a, "connect", "--host", ADDR["b"], "--port", "${toString controlPort}")}
        b.succeed(f"systemctl stop {UNIT}")
        result["b"] = summary(collect("b", label), label)
        evidence["trials"][label] = result

    attempt("t7-withdrawal", withdrawal)
    # Assertion 10, in the withdrawn configuration: the channel is cut before the
    # measured phase, so both sides must end with an explicit failure.
    attempt("t8-channel-cut", lambda: finish(run("t8-channel-cut", seconds=60, linger=2)))

    # Assertions -------------------------------------------------------------
    T: dict[str, Any] = evidence["trials"]
    P: dict[str, Any] = evidence.get("probes", {})

    def get(path, default=None) -> Any:
        try:
            value: Any = evidence
            for part in path:
                value = value[part]
            return value
        except (KeyError, IndexError, TypeError):
            return default

    def b_attempts(label):
        return get(["trials", label, "b", "attempts"], [])

    def from_address(label, guest, address):
        return [r for r in get(["trials", label, guest, "attempts"], []) if r.get("from") == address]

    t1_b = b_attempts("t1-baseline")
    restarted = {label: get(["trials", label, guest, "processStarts"], 0) - 1
                 for label, guest in (("t4-I1", "b"), ("t5-I2", "b"), ("t6-I3", "a"))}
    fault_result = {label: [r for r in get(["trials", label, "a", "attempts"], []) if "fault" in r]
                    for label in ("t2-duplicate", "t3-conflict")}
    all_agreement = [ok for record in T.values() if "byteAgreement" in record
                     for direction in record["byteAgreement"].values() for ok in direction.values()]
    endings: dict[str, Any] = {label: [get(["trials", label, n, "status", "status"]) for n in ("a", "b") if n in T[label]]
               for label in T}
    endings["t7-withdrawal"] = [get(["trials", "t7-withdrawal", "b", "status", "status"])]
    distinct: dict[str, Any] = {
        "cannot-connect": [k for k in ("c->a:contract", "c->b:contract") if P.get(k, {}).get("outcome") != "connected"],
        "cannot-authenticate": [r.get("reason", r["result"]) for r in t1_b if r["result"] in ("tls-failed", "unauthenticated")],
        "rejected-after-authentication": [r.get("reason") for r in t1_b if r["result"] == "rejected"],
        "passive-interception": "not tested; no claim"}
    distinct["passed"] = all(distinct[k] for k in ("cannot-connect", "cannot-authenticate",
                                                   "rejected-after-authentication"))
    withdrawn: dict[str, Any] = {
        "observed": {k: get(["trials", "t7-withdrawal", k]) for k in ("existingConnection", "newConnection")},
        "restartObserved": get(["trials", "t7-withdrawal", "before", "unit", "InvocationID"])
                           != get(["trials", "t7-withdrawal", "after", "unit", "InvocationID"]),
        "newConnectionRefusedBeforeTls": get(["trials", "t7-withdrawal", "newConnection", "outcome"]) == "connect-failed",
        "existingConnectionCarriedData": get(["trials", "t7-withdrawal", "existingConnection", "outcome"]) == "acked"}
    withdrawn["passed"] = withdrawn["newConnectionRefusedBeforeTls"] and withdrawn["restartObserved"]
    assertions: dict[str, Any] = {
        "1-completion": get(["trials", "t1-baseline", "complete"]) is True,
        "2-byte-agreement": bool(all_agreement) and all(all_agreement)
            and all(get(["trials", "t1-baseline", "byteAgreement", d], {}) for d in ("a->b", "b->a")),
        "3-duplicate-delivery": get(["trials", "t2-duplicate", "complete"]) is True
            and [(r["fault"], r["result"]) for r in fault_result["t2-duplicate"]] == [("resend-acked", "ack-duplicate")]
            and any(r["result"] == "duplicate" for r in b_attempts("t2-duplicate"))
            and len({i["incoming"] for i in get(["trials", "t2-duplicate", "b", "invocations"], [])})
                == len(get(["trials", "t2-duplicate", "b", "invocations"], [None])),
        "4-conflicting-bytes": get(["trials", "t3-conflict", "complete"]) is True
            and [(r["fault"], r["result"], r["reason"]) for r in fault_result["t3-conflict"]]
                == [("conflict", "ack-rejected", "conflicting-bytes")]
            and any(r.get("reason") == "conflicting-bytes" for r in b_attempts("t3-conflict")),
        "5-interruptions": all(get(["trials", label, "complete"]) is True and restarted[label] == 1
                               for label in restarted),
        "6-address-filter": all(P.get(k, {}).get("outcome") in ("timeout", "error") for k in ("c->a:contract", "c->b:contract"))
            and not from_address("t1-baseline", "a", ADDR["c"]) and not from_address("t1-baseline", "b", ADDR["c"]),
        "7-authentication": any(r.get("result") == "tls-failed" and r.get("from") == ADDR["a"] for r in t1_b)
            and any(r.get("reason") == "unmapped-certificate" for r in t1_b)
            and get(["probes", "wrong-sender", "ack", "reason"]) == "sender-mismatch"
            and get(["probes", "turn-8", "ack", "reason"]) == "turn-limit"
            and any(r.get("stage") == "frame" and r.get("reason") == "frame-size" for r in t1_b)
            and P.get("b-outbox-unchanged") is True,
        "8-distinct-claims": distinct,
        "9-peer-withdrawal": withdrawn,
        "10-channel-cut": all(get(["trials", "t8-channel-cut", n, "status", "status"]) == "failed"
                              and "digest" not in (get(["trials", "t8-channel-cut", n, "status"]) or {"digest": 1})
                              for n in ("a", "b")),
        "11-explicit-ending": all(e and all(s in ("complete", "failed") for s in e) for e in endings.values()),
    }
    evidence["assertions"] = assertions
    evidence["allAssertionsPassed"] = all(v if isinstance(v, bool) else v["passed"] for v in assertions.values())
    evidence["testScriptSeconds"] = round(time.monotonic() - started, 1)
    for name in ("a", "b"):
        with open(os.path.join(OUT, f"{name}-journal.txt"), "w") as stream:
            stream.write(M[name].succeed(f"journalctl -b -u {UNIT} -u sandhi-exchange-credentials "
                                         "--no-pager -o short-iso-precise"))
    with open(os.path.join(OUT, "stage-a.json"), "w") as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
  '';
}
