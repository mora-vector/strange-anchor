#!/usr/bin/env python3
"""Run Sandhi's checks and preserve one machine's evidence. No promotion occurs."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory for this run; existing paths are refused")
    parser.add_argument("--evaluation-only", action="store_true",
                        help="Build only the evaluation artifact; no VM claim")
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    if destination == ROOT or ROOT in destination.parents:
        parser.error("Place evidence outside the source tree so recording does not change the input.")
    if destination.exists():
        parser.error("Output directory already exists; choose a new run directory.")
    nix = shutil.which("nix")
    if nix is None:
        parser.error("Nix must be installed and available on PATH.")
    destination.mkdir(parents=True)
    sources = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and (path.suffix in {".nix", ".py"} or path.name == "flake.lock"):
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        "schemaVersion": 2,
        "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "sourceFilesSha256": sources,
        "evidenceScope": "one local run; no builder independence or canonical promotion asserted",
        "steps": [], "canonical": False, "status": "running",
    }
    command_base = [nix, "--extra-experimental-features", "nix-command flakes"]

    def save():
        temp = destination / "report.json.tmp"
        temp.write_text(json.dumps(report, indent=2) + "\n")
        temp.replace(destination / "report.json")

    def execute(name, command):
        with (destination / (name + ".stdout")).open("w") as out, \
             (destination / (name + ".stderr")).open("w") as err:
            result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err)
        report["steps"].append({"name": name, "command": command, "exitCode": result.returncode})
        save()
        if result.returncode:
            raise RuntimeError(f"{name} exited {result.returncode}")
        return (destination / (name + ".stdout")).read_text()

    save()
    try:
        if shutil.which("git"):
            revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True)
            if revision.returncode == 0:
                report["repositoryCommit"] = revision.stdout.strip()
                changes = subprocess.run(["git", "status", "--porcelain", "--", "."],
                                         cwd=ROOT, capture_output=True, text=True)
                report["sourceChanges"] = changes.stdout.splitlines() if changes.returncode == 0 else None
        report["nixVersion"] = execute("nix-version", [nix, "--version"]).strip()
        execute("evaluate", command_base + ["flake", "check", "--no-build", "path:" + str(ROOT)])
        targets = ["evaluation"] if args.evaluation_only else ["evaluation", "reachability"]
        for target in targets:
            ref = f"path:{ROOT}#checks.x86_64-linux.{target}"
            raw = execute("build-" + target, command_base + [
                "build", "--print-build-logs", "--json", "--out-link", str(destination / (target + "-result")), ref])
            records = json.loads(raw)
            outputs = [p for r in records for p in r["outputs"].values()]
            execute("paths-" + target, command_base + ["path-info", "--json"] + outputs)
            if target == "reachability":
                observation = Path(records[0]["outputs"]["out"]) / "reachability.json"
                shutil.copyfile(observation, destination / "reachability.json")
        report["status"] = "evaluation-only-passed" if args.evaluation_only else "vm-test-passed"
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        report["status"] = "failed"
        report["error"] = str(error)
    finally:
        report["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(destination / "report.json")
    return 0 if report["status"].endswith("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
