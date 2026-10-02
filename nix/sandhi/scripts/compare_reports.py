#!/usr/bin/env python3
"""Compare declared reports against an explicit subject/inventory. No authentication."""
import argparse
import json
from pathlib import Path
import re


def compare(spec, reports):
    pending = ["authenticate-reports", "verify-administrative-independence",
               "audit-cache-policy-and-evidence", "apply-release-policy"]

    def result(reasons):
        return dict(schemaVersion="1.0", status="held" if reasons else "reported-agreement",
                    reasons=sorted(set(reasons)), canonical=False,
                    independenceVerified=False, pending=pending)

    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())

    def digest(value):
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

    def valid_source(value):
        return isinstance(value, dict) and set(value) == {"filesSha256", "lockSha256", "system"} \
            and digest(value["filesSha256"]) and digest(value["lockSha256"]) and nonempty(value["system"])

    if not isinstance(spec, dict) or set(spec) != {
            "schemaVersion", "kind", "subject", "source", "requiredMembers"}:
        return result(["malformed-specification"])
    members = spec["requiredMembers"]
    if spec["schemaVersion"] != "1.0" or spec["kind"] not in ["artifact", "behavior"] \
            or not nonempty(spec["subject"]) or not valid_source(spec["source"]) \
            or not isinstance(members, list) or not members or not all(map(nonempty, members)) \
            or len(set(members)) != len(members):
        return result(["malformed-specification"])
    if spec["kind"] == "artifact" and re.fullmatch(
            r"/nix/store/[0-9a-z]{32}-[^/]+[.]drv", spec["subject"]) is None:
        return result(["malformed-specification"])
    if not isinstance(reports, list) or len(reports) < 2:
        return result(["fewer-than-two-reports"])
    reasons = []
    identities, administrations, runs, observations = [], [], [], []
    for report in reports:
        required = {"schemaVersion", "kind", "subject", "source", "builderId", "administration",
                    "runId", "cache", "evidence", "observations"}
        if not isinstance(report, dict) or set(report) != required:
            reasons.append("malformed-report")
            continue
        if report["schemaVersion"] != "1.0" or not valid_source(report["source"]):
            reasons.append("malformed-report")
        for key in ["kind", "subject", "source"]:
            if report[key] != spec[key]:
                reasons.append("subject-or-source-mismatch")
        if not all(nonempty(report[k]) for k in ["builderId", "administration", "runId"]):
            reasons.append("missing-execution-identity")
            continue
        identities.append(report["builderId"])
        administrations.append(report["administration"])
        runs.append(report["runId"])
        cache = report["cache"]
        if not isinstance(cache, dict) or set(cache) != {"subject", "dependencies"} \
                or cache.get("subject") != "rebuilt" \
                or cache.get("dependencies") not in ["rebuilt", "substituted", "mixed"]:
            reasons.append("unproven-subject-execution")
        evidence = report["evidence"]
        if not isinstance(evidence, dict) or set(evidence) != {"reference", "sha256"} \
                or not nonempty(evidence.get("reference")) or not digest(evidence.get("sha256")):
            reasons.append("missing-evidence-provenance")
        obs = report["observations"]
        if not isinstance(obs, dict) or set(obs) != set(members):
            reasons.append("incomplete-or-extra-inventory")
            continue
        if spec["kind"] == "behavior":
            if not all(value is True for value in obs.values()):
                reasons.append("behavior-not-passed")
        else:
            for value in obs.values():
                if not isinstance(value, dict) or set(value) != {"path", "narHash"} \
                        or not isinstance(value.get("path"), str) \
                        or re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^/]+", value["path"]) is None \
                        or not isinstance(value.get("narHash"), str) \
                        or re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", value["narHash"]) is None:
                    reasons.append("malformed-output")
            paths = [v["path"] for v in obs.values() if isinstance(v, dict) and isinstance(v.get("path"), str)]
            if len(paths) != len(set(paths)):
                reasons.append("duplicate-output-path")
        observations.append(obs)
    for values, label in [(identities, "duplicate-builder"), (administrations, "shared-administration"),
                          (runs, "duplicate-run")]:
        if len(values) != len(set(values)):
            reasons.append(label)
    if observations and any(value != observations[0] for value in observations[1:]):
        reasons.append("observation-mismatch")
    return result(reasons)


def read(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key: {key}")
            value[key] = item
        return value
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specification", type=Path)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    output = compare(read(args.specification), [read(p) for p in args.reports])
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0 if output["status"] == "reported-agreement" else 1


if __name__ == "__main__":
    raise SystemExit(main())
