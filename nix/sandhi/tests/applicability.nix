{ pkgs }:
let
  subject = pkgs.writeText "sandhi-recovery-subject" "bounded fixture\n";
in pkgs.testers.runNixOSTest {
  name = "sandhi-retention-evidence-applicability";
  requiredFeatures.kvm = false;
  globalTimeout = 900;
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
    # Separate premises: retention off with exports still visible, and exports
    # hidden with retention still on. Neither may stand in for the other.
    specialisation.without-retention.configuration = {
      sandhi.retention.enable = lib.mkForce false;
    };
    specialisation.without-export.configuration = {
      sandhi.registry.export = lib.mkForce false;
    };
  };
  testScript = ''
    import json, os, shlex
    start_all()
    machine.wait_for_unit("multi-user.target")
    base = machine.succeed("readlink -f /run/current-system").strip()
    manager = "sandhi-recovery-state"
    exports = ["/etc/sandhi/lopa.json", "/etc/sandhi/lopa-v1.json", "/etc/sandhi/lopa-v2.json"]
    def status():
        return json.loads(machine.succeed(manager + " status"))
    def declare(epoch):
        return (manager + " record --epoch " + shlex.quote(epoch)
            + " --kind output --subject ${subject} --reference fixture:local-bytes"
            + " --evidence ${subject} --asserted-by vm-fixture")
    def history():
        return json.loads(machine.succeed("cat /var/lib/sandhi-recovery/state.json"))["history"]
    def read_exports():
        return {path: machine.succeed("cat " + path) for path in exports}
    def switch(name=None):
        target = base if name is None else base + "/specialisation/" + name
        machine.succeed(target + "/bin/switch-to-configuration test")
    original_exports = read_exports()
    snapshot = original_exports["/etc/sandhi/lopa-v2.json"]
    first = status()
    assert first["status"] == "unassessed", first
    machine.succeed(declare(first["epoch"]))
    positive = status()
    assert positive["status"] == "declared-recoverable", positive
    original_history = history()

    # Retention off, export on: the snapshot stays readable and records the
    # disabled premise; it cannot carry or permit a current assessment.
    switch("without-retention")
    disabled = status()
    assert disabled["status"] == "unassessed" and not disabled["retentionEnabled"], disabled
    assert history() == original_history
    disabled_exports = read_exports()
    for path in ["/etc/sandhi/lopa.json", "/etc/sandhi/lopa-v1.json"]:
        assert disabled_exports[path] == original_exports[path], path
    disabled_v2 = json.loads(disabled_exports["/etc/sandhi/lopa-v2.json"])
    original_v2 = json.loads(snapshot)
    assert disabled_v2["evidenceSemantics"] == "historical-declarations", disabled_v2
    assert disabled_v2["recoveryPolicy"]["retentionEnabled"] is False, disabled_v2
    assert original_v2["recoveryPolicy"]["retentionEnabled"] is True, original_v2
    # Declared targets remain listed: configured-but-disabled is not "nothing configured".
    assert disabled_v2["recoveryPolicy"]["subjects"] == original_v2["recoveryPolicy"]["subjects"]
    assert disabled_v2["gaps"] == original_v2["gaps"]
    machine.fail(declare(disabled["epoch"]))

    # Returning restores identical snapshot bytes but not the old assessment.
    switch()
    enabled = status()
    assert enabled["status"] == "unassessed" and enabled["retentionEnabled"], enabled
    assert enabled["epoch"] not in [first["epoch"], disabled["epoch"]]
    assert read_exports() == original_exports
    assert history() == original_history
    machine.fail(declare(first["epoch"]))
    machine.succeed(declare(enabled["epoch"]))
    revalidated = status()
    assert revalidated["status"] == "declared-recoverable", revalidated
    assert revalidated["historicalAssessmentCount"] == 2
    assert revalidated["assessments"][0]["verification"] == "not-performed"

    # Export off, retention on: hiding the snapshots neither withdraws the
    # lifecycle nor blocks a fresh declaration for the new epoch.
    switch("without-export")
    hidden = status()
    assert hidden["status"] == "unassessed" and hidden["retentionEnabled"], hidden
    assert hidden["epoch"] not in [first["epoch"], disabled["epoch"], enabled["epoch"]]
    for path in exports:
        machine.fail("test -e " + path)
    machine.fail(declare(enabled["epoch"]))
    machine.succeed(declare(hidden["epoch"]))
    hidden_declared = status()
    assert hidden_declared["status"] == "declared-recoverable", hidden_declared
    assert hidden_declared["historicalAssessmentCount"] == 3

    switch()
    returned = status()
    assert returned["status"] == "unassessed", returned
    assert len(history()) == 3
    switch()
    same = status()
    assert same["status"] == "unassessed" and same["epoch"] != returned["epoch"], same
    assert len(history()) == 3
    with open(os.path.join(os.environ["out"], "applicability.json"), "w") as f:
        json.dump({"scope": "administrator declarations across actual NixOS activations; not recovery verification",
                   "positive": positive, "disabled": disabled,
                   "disabledExportPolicy": disabled_v2["recoveryPolicy"],
                   "reenabled": enabled, "revalidated": revalidated,
                   "exportHidden": hidden, "exportHiddenDeclared": hidden_declared,
                   "returned": returned, "sameConfigurationReactivation": same,
                   "legacyAndV1UnchangedByRetention": True,
                   "historicalEvidencePreserved": True, "staleEpochRejected": True}, f, indent=2)
  '';
}
