{ pkgs }:
pkgs.testers.runNixOSTest {
  name = "sandhi-lopa-audit-workload";
  requiredFeatures.kvm = false;
  globalTimeout = 600;
  nodes.machine = { ... }: {
    imports = [ ../examples/lopa-audit.nix ];
    virtualisation = { memorySize = 1024; cores = 2; vlans = []; };
    sandhi.gaps.independent-builder = {
      status = "unknown"; reason = "No independent execution report supplied.";
      recoveryEvidence = [{ kind = "verified-restoration"; reference = "fixture:unverified-claim"; }];
    };
  };
  testScript = ''
    import hashlib, json, os
    start_all()
    machine.wait_for_unit("multi-user.target")
    unit = "sandhi-contract-lopa-audit.service"
    machine.succeed(f"systemctl start {unit}")
    machine.wait_until_succeeds(
        f"test $(systemctl show {unit} -p ActiveState --value) = inactive", timeout=60)
    machine.succeed(f"test $(systemctl show {unit} -p Result --value) = success")
    raw = machine.succeed("cat /etc/sandhi/lopa-v1.json")
    report = json.loads(machine.succeed("cat /var/lib/sandhi-contract-lopa-audit/report.json"))
    assert report["inputSha256"] == hashlib.sha256(raw.encode()).hexdigest(), report
    assert report["gapCount"] == 1 and report["blockingGapIds"] == [], report
    assert report["unattributedGapIds"] == ["independent-builder"], report
    assert report["evidenceReferences"][0]["verification"] == "not-performed", report
    assert report["canonical"] is False, report
    machine.succeed(f"test $(systemctl show {unit} -p PrivateNetwork --value) = yes",
                    f"test $(systemctl show {unit} -p ProtectSystem --value) = strict")
    with open(os.path.join(os.environ["out"], "workload.json"), "w") as f:
        json.dump({"scope": "local snapshot audit in generated contract", "report": report}, f, indent=2)
  '';
}
