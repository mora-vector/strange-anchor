import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "comparison", Path(__file__).resolve().parents[1] / "scripts/compare_reports.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def fixtures(kind="behavior"):
    subject = "/nix/store/" + "1" * 32 + "-fixture.drv" if kind == "artifact" else "fixture-test-v1"
    specification = dict(schemaVersion="1.0", kind=kind, subject=subject,
                         source=dict(filesSha256="a" * 64, lockSha256="b" * 64, system="x86_64-linux"),
                         requiredMembers=["out"])
    observations = {"out": True} if kind == "behavior" else {
        "out": dict(path="/nix/store/" + "0" * 32 + "-fixture",
                    narHash="sha256-" + "A" * 43 + "=")}
    reports = [dict({k: copy.deepcopy(v) for k, v in specification.items() if k != "requiredMembers"},
                    builderId=name, administration=name, runId=name,
                    cache=dict(subject="rebuilt", dependencies="substituted"),
                    evidence=dict(reference="fixture:" + name, sha256="c" * 64),
                    observations=copy.deepcopy(observations)) for name in ["one", "two"]]
    return specification, reports


class ComparisonTests(unittest.TestCase):
    def test_agreement_never_authenticates(self):
        for kind in ["artifact", "behavior"]:
            spec, reports = fixtures(kind)
            result = comparison.compare(spec, reports)
            self.assertEqual(result["status"], "reported-agreement")
            self.assertFalse(result["canonical"])
            self.assertFalse(result["independenceVerified"])

    def test_identical_omissions_are_held(self):
        spec, reports = fixtures()
        for report in reports:
            report["observations"] = {}
        self.assertIn("incomplete-or-extra-inventory", comparison.compare(spec, reports)["reasons"])

    def test_shared_administration_cache_and_identity_hold(self):
        for key in ["builderId", "administration", "runId"]:
            spec, reports = fixtures()
            reports[1][key] = reports[0][key]
            self.assertEqual(comparison.compare(spec, reports)["status"], "held")
        spec, reports = fixtures()
        reports[1]["cache"]["subject"] = "substituted"
        self.assertIn("unproven-subject-execution", comparison.compare(spec, reports)["reasons"])

    def test_changed_source_or_artifact_or_failed_behavior_held(self):
        spec, reports = fixtures("artifact")
        reports[1]["observations"]["out"]["narHash"] = "sha256-B" + "A" * 42 + "="
        self.assertIn("observation-mismatch", comparison.compare(spec, reports)["reasons"])
        spec, reports = fixtures()
        reports[1]["source"]["lockSha256"] = "d" * 64
        self.assertIn("subject-or-source-mismatch", comparison.compare(spec, reports)["reasons"])
        spec, reports = fixtures()
        for report in reports:
            report["observations"]["out"] = False
        self.assertIn("behavior-not-passed", comparison.compare(spec, reports)["reasons"])

    def test_malformed_unknown_and_missing_evidence_held(self):
        for value in [None, [], {}, {"schemaVersion": "2.0"}]:
            self.assertEqual(comparison.compare(value, [None, None])["status"], "held")
        spec, reports = fixtures()
        reports[1]["evidence"]["sha256"] = None
        self.assertIn("missing-evidence-provenance", comparison.compare(spec, reports)["reasons"])
        spec, reports = fixtures()
        reports[1]["claimedCanonical"] = True
        self.assertIn("malformed-report", comparison.compare(spec, reports)["reasons"])


if __name__ == "__main__":
    unittest.main()
