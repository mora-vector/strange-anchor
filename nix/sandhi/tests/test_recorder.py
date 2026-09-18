"""Exercise recorder scope/failure handling without claiming any Nix build."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "realize", Path(__file__).resolve().parents[1] / "scripts" / "realize.py")
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class RecorderTests(unittest.TestCase):
    def run_recorder(self, selection, fail=None, missing_observation=False, mutate_source=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "evidence"
            source = root / "source"
            source.mkdir()
            (source / "flake.nix").write_text("# Initial test fixture\n")
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                if command[0] == "git":
                    return SimpleNamespace(returncode=1, stdout="")
                code, output = 0, ""
                if "--version" in command:
                    output = "nix (test double)\n"
                elif "build" in command:
                    if mutate_source:
                        (source / "flake.nix").write_text("# Changed test fixture\n")
                    target = command[-1].rsplit(".", 1)[-1]
                    if target == fail:
                        kwargs["stderr"].write("fixture failed: diagnostic preserved\n")
                        code = 1
                    else:
                        artifact = root / target
                        artifact.mkdir()
                        if not missing_observation:
                            (artifact / (target + ".json")).write_text('{"testDouble": true}')
                        output = json.dumps([{"outputs": {"out": str(artifact)}}])
                elif "path-info" in command:
                    output = "{}"
                kwargs["stdout"].write(output)
                return SimpleNamespace(returncode=code)

            out, err = io.StringIO(), io.StringIO()
            with patch.object(recorder.shutil, "which", return_value="/test/nix"), \
                    patch.object(recorder, "ROOT", source), \
                    patch.object(recorder.platform, "platform", return_value="recorder-test-double"), \
                    patch.object(recorder.subprocess, "run", side_effect=run), \
                    patch.object(recorder.sys, "argv", ["realize", "--output-dir", str(destination)] + selection), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = recorder.main()
            return code, json.loads((destination / "report.json").read_text()), calls, out.getvalue(), err.getvalue()

    def test_single_vm_success_never_claims_full_suite(self):
        code, report, calls, _, _ = self.run_recorder(["--check", "recovery", "--check", "recovery"])
        self.assertEqual(code, 0)
        self.assertEqual(report["requestedChecks"], ["recovery"])
        self.assertEqual(report["completedChecks"], ["recovery"])
        self.assertEqual(report["status"], "selected-checks-passed")
        self.assertEqual(sum("build" in command for command in calls), 1)
        self.assertFalse(report["canonical"])

    def test_default_failure_keeps_completed_checks_and_diagnostic(self):
        code, report, _, out, err = self.run_recorder([], fail="recovery")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["completedChecks"], ["evaluation", "reachability"])
        self.assertIn("fixture failed: diagnostic preserved", err)
        self.assertIn('"status": "failed"', out)

    def test_missing_observation_is_not_a_runtime_pass(self):
        code, report, _, _, _ = self.run_recorder(["--check", "recovery"], missing_observation=True)
        self.assertEqual(code, 1)
        self.assertEqual(report["completedChecks"], [])

    def test_default_success_names_all_checks(self):
        code, report, _, _, _ = self.run_recorder([])
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "runtime-tests-passed")
        self.assertEqual(report["completedChecks"], ["evaluation", "reachability", "recovery"])

    def test_evaluation_only_compatibility(self):
        code, report, _, _, _ = self.run_recorder(["--evaluation-only"])
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "evaluation-only-passed")

    def test_concurrent_source_edit_prevents_combined_success(self):
        code, report, _, _, _ = self.run_recorder(["--evaluation-only"], mutate_source=True)
        self.assertEqual(code, 1)
        self.assertEqual(report["completedChecks"], ["evaluation"])
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["sourceStableAtEnd"])
        self.assertIn("changed during this run", report["sourceError"])


if __name__ == "__main__":
    unittest.main()
