#!/usr/bin/env python3
"""Local, administrator-declared recovery applicability; never evidence verification."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"Invalid JSON constant: {value}")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def policy(snapshot):
    if snapshot.get("schema") != "sandhi.lopa" or snapshot.get("schemaVersion") != "2.0":
        raise ValueError("Expected Lopa 2.0")
    value = snapshot["recoveryPolicy"]
    if set(value) != {"retentionEnabled", "subjects"} or type(value["retentionEnabled"]) is not bool:
        raise ValueError("Invalid retention policy")
    if not isinstance(value["subjects"], list):
        raise ValueError("Invalid subjects")
    for subject in value["subjects"]:
        if (not isinstance(subject, dict) or set(subject) != {"kind", "path"}
                or subject["kind"] not in {"output", "recipe"}
                or not isinstance(subject["path"], str) or not subject["path"].startswith("/nix/store/")):
            raise ValueError("Invalid retained subject")
    return value


def validate(state):
    if (not isinstance(state, dict) or set(state) != {"schema", "epoch", "snapshotSha256", "policy", "history", "current"}
            or state["schema"] != "sandhi.recovery-state.v1"
            or not isinstance(state["epoch"], str) or not state["epoch"]
            or not isinstance(state["snapshotSha256"], str) or len(state["snapshotSha256"]) != 64
            or not isinstance(state["history"], list) or not isinstance(state["current"], list)):
        raise ValueError("Invalid recovery state; refusing to infer a current assessment")
    policy({"schema": "sandhi.lopa", "schemaVersion": "2.0", "recoveryPolicy": state["policy"]})
    for item in state["history"]:
        if (not isinstance(item, dict) or set(item) != {"epoch", "snapshotSha256", "subject", "reference", "sha256", "assertedBy", "verification"}
                or not all(isinstance(item[k], str) and item[k] for k in ["epoch", "snapshotSha256", "reference", "sha256", "assertedBy"])
                or len(item["snapshotSha256"]) != 64
                or len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"])
                or item["verification"] != "not-performed"):
            raise ValueError("Invalid historical assessment")
        policy({"schema": "sandhi.lopa", "schemaVersion": "2.0", "recoveryPolicy": {"retentionEnabled": True, "subjects": [item["subject"]]}})
    for index in state["current"]:
        if (type(index) is not int or not 0 <= index < len(state["history"])
                or state["history"][index]["epoch"] != state["epoch"]
                or state["history"][index]["snapshotSha256"] != state["snapshotSha256"]
                or state["history"][index]["subject"] not in state["policy"]["subjects"]
                or not state["policy"]["retentionEnabled"]):
            raise ValueError("Invalid current assessment")
    return state


def activate(previous, raw, epoch=None):
    snapshot = decode(raw)
    current_policy = policy(snapshot)
    if previous is not None:
        validate(previous)
    return {"schema": "sandhi.recovery-state.v1", "epoch": epoch or uuid.uuid4().hex,
            "snapshotSha256": hashlib.sha256(raw).hexdigest(), "policy": current_policy,
            "history": copy.deepcopy(previous["history"]) if previous else [], "current": []}


def record(state, epoch, subject, reference, evidence, asserted_by):
    validate(state)
    if epoch != state["epoch"]:
        raise ValueError("Stale epoch; perform and declare a new validation for this activation")
    if not state["policy"]["retentionEnabled"] or subject not in state["policy"]["subjects"]:
        raise ValueError("Retention premise disabled or subject not retained by current policy")
    if not reference.strip() or not asserted_by.strip():
        raise ValueError("Reference and asserting administrator are required")
    result = copy.deepcopy(state)
    result["history"].append({"epoch": epoch, "snapshotSha256": state["snapshotSha256"], "subject": subject, "reference": reference,
                              "sha256": hashlib.sha256(evidence).hexdigest(),
                              "assertedBy": asserted_by, "verification": "not-performed"})
    result["current"] = [i for i in result["current"] if result["history"][i]["subject"] != subject]
    result["current"].append(len(result["history"]) - 1)
    return result


def status(state):
    if state is None:
        return {"status": "unassessed", "reason": "no-local-state", "assessments": [], "canonical": False}
    validate(state)
    return {"status": "declared-recoverable" if state["current"] else "unassessed",
            "epoch": state["epoch"], "snapshotSha256": state["snapshotSha256"],
            "retentionEnabled": state["policy"]["retentionEnabled"],
            "assessments": [state["history"][i] for i in state["current"]],
            "historicalAssessmentCount": len(state["history"]), "canonical": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("/var/lib/sandhi-recovery/state.json"))
    parser.add_argument("--policy", type=Path, help="Expected policy from the installed system generation")
    commands = parser.add_subparsers(dest="command", required=True)
    activation = commands.add_parser("activate")
    activation.add_argument("snapshot", type=Path)
    commands.add_parser("status")
    declaration = commands.add_parser("record", help="Declare a new administrator-assessed recovery result, without authenticating it")
    declaration.add_argument("--epoch", required=True)
    declaration.add_argument("--kind", choices=["output", "recipe"], required=True)
    declaration.add_argument("--subject", required=True)
    declaration.add_argument("--reference", required=True)
    declaration.add_argument("--evidence", type=Path, required=True)
    declaration.add_argument("--asserted-by", required=True)
    args = parser.parse_args()
    try:
        args.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(str(args.state) + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            previous = decode(args.state.read_bytes()) if args.state.exists() else None
            if args.command != "activate" and args.policy is not None and previous is not None:
                validate(previous)
                if hashlib.sha256(args.policy.read_bytes()).hexdigest() != previous["snapshotSha256"]:
                    raise ValueError("Installed policy and ledger disagree; no current assessment is applicable")
            if args.command == "activate":
                result = activate(previous, args.snapshot.read_bytes())
            elif args.command == "record":
                if previous is None:
                    raise ValueError("No activated policy")
                result = record(previous, args.epoch, {"kind": args.kind, "path": args.subject},
                                args.reference, args.evidence.read_bytes(), args.asserted_by)
            else:
                print(json.dumps(status(previous), sort_keys=True, indent=2))
                return 0
            # One atomic ledger transaction: history and applicability cannot diverge.
            with tempfile.NamedTemporaryFile(mode="w", dir=args.state.parent, delete=False) as tmp:
                temporary = Path(tmp.name)
                json.dump(result, tmp, sort_keys=True, indent=2)
                tmp.write("\n")
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(temporary, args.state)
            directory = os.open(args.state.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            print(json.dumps(status(result), sort_keys=True, indent=2))
            return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
