{ pkgs }:
let
  subject = pkgs.writeText "sandhi-recovery-subject" "bounded fixture\n";
in pkgs.testers.runNixOSTest {
  name = "sandhi-retention-evidence-applicability";
  requiredFeatures.kvm = false;
  globalTimeout = 600;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules ];
    virtualisation = { memorySize = 1024; cores = 2; vlans = []; };
    sandhi = {
      retention.enable = true;
      registry.export = true;
      retainedPackages = [ subject ];
      gaps.recovery = {
        status = "unknown"; reason = "Fixture declarations are not independent evidence.";
        recoveryEvidence = [{ kind = "verified-restoration"; reference = "fixture:historical-restoration"; }];
      };
    };
    specialisation.without-retention.configuration = {
      sandhi.retention.enable = lib.mkForce false;
      sandhi.registry.export = lib.mkForce false;
    };
  };
  testScript = ''
    import json, os, shlex
    start_all()
    machine.wait_for_unit("multi-user.target")
    base = machine.succeed("readlink -f /run/current-system").strip()
    manager = "sandhi-recovery-state"
    def status():
        return json.loads(machine.succeed(manager + " status"))
    def declare(epoch):
        return (manager + " record --epoch " + shlex.quote(epoch)
            + " --kind output --subject ${subject} --reference fixture:local-bytes"
            + " --evidence ${subject} --asserted-by vm-fixture")
    def history():
        return json.loads(machine.succeed("cat /var/lib/sandhi-recovery/state.json"))["history"]
    snapshot = machine.succeed("cat /etc/sandhi/lopa-v2.json")
    first = status()
    assert first["status"] == "unassessed", first
    machine.succeed(declare(first["epoch"]))
    positive = status()
    assert positive["status"] == "declared-recoverable", positive
    original_history = history()
    machine.succeed(base + "/specialisation/without-retention/bin/switch-to-configuration test")
    disabled = status()
    assert disabled["status"] == "unassessed" and not disabled["retentionEnabled"], disabled
    assert history() == original_history
    machine.fail("test -e /etc/sandhi/lopa-v2.json")
    machine.fail(declare(disabled["epoch"]))
    machine.succeed(base + "/bin/switch-to-configuration test")
    enabled = status()
    assert enabled["status"] == "unassessed" and enabled["retentionEnabled"], enabled
    assert enabled["epoch"] not in [first["epoch"], disabled["epoch"]]
    assert machine.succeed("cat /etc/sandhi/lopa-v2.json") == snapshot
    assert history() == original_history
    machine.fail(declare(first["epoch"]))
    machine.succeed(declare(enabled["epoch"]))
    revalidated = status()
    assert revalidated["status"] == "declared-recoverable", revalidated
    assert revalidated["historicalAssessmentCount"] == 2
    assert revalidated["assessments"][0]["verification"] == "not-performed"
    machine.succeed(base + "/bin/switch-to-configuration test")
    assert status()["status"] == "unassessed"
    assert len(history()) == 2
    with open(os.path.join(os.environ["out"], "applicability.json"), "w") as f:
        json.dump({"scope": "administrator declarations across actual NixOS activations; not recovery verification",
                   "positive": positive, "disabled": disabled, "reenabled": enabled,
                   "revalidated": revalidated, "sameConfigurationReactivation": status(),
                   "historicalEvidencePreserved": True, "staleEpochRejected": True}, f, indent=2)
  '';
}
