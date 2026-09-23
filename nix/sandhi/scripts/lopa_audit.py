#!/usr/bin/env python3
"""Validate a Lopa 1.0 snapshot and inventory declared evidence without fetching it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "lopa-v1.schema.json"


def decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value
    def invalid_constant(value):
        raise ValueError(f"Non-JSON constant: {value}")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def audit(raw, schema):
    snapshot = decode(raw)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(snapshot)
    gaps = snapshot["gaps"]
    return {
        "schema": "sandhi.lopa-audit", "schemaVersion": "1.0",
        "inputSha256": hashlib.sha256(raw).hexdigest(),
        "inputSchemaVersion": snapshot["schemaVersion"],
        "gapCount": len(gaps),
        "blockingGapIds": sorted(key for key, gap in gaps.items() if gap["blocksActivation"]),
        "unattributedGapIds": sorted(key for key, gap in gaps.items()
                                    if gap["provenance"]["assertedBy"] is None),
        "evidenceReferences": [
            {"gapId": key, "kind": entry["kind"], "reference": entry["reference"],
             "declaredProvenance": entry["provenance"], "verification": "not-performed"}
            for key, gap in sorted(gaps.items()) for entry in gap["recoveryEvidence"]],
        "canonical": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    args = parser.parse_args()
    try:
        result = audit(args.snapshot.read_bytes(), decode(args.schema.read_bytes()))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    # JSON Schema exceptions deliberately also cause a nonzero process exit.
    print(json.dumps(result, sort_keys=True, indent=2))
    return 2 if result["blockingGapIds"] else 0


if __name__ == "__main__":
    sys.exit(main())
