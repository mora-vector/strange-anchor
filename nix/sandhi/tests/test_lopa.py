"""Compatibility, malformed input, and evidence-claim boundaries."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lopa_audit", ROOT / "scripts/lopa_audit.py")
lopa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lopa)
SCHEMA = json.loads((ROOT / "schemas/lopa-v1.schema.json").read_text())


def fixture():
    origin = dict(sourceReference=None, assertedBy=None, recordedAt=None, sha256=None)
    return dict(schema="sandhi.lopa", schemaVersion="1.0",
                provenance=dict(sourceRevision=None, recorder=None), gaps={
        "builder": dict(status="unknown", availability="unassessed", reason="No report",
                        blocksActivation=False, provenance=origin, recoveryEvidence=[
                            dict(kind="verified-restoration", reference="https://invalid.example/evidence",
                                 provenance=copy.deepcopy(origin))])})


class LopaTests(unittest.TestCase):
    def test_claim_is_not_verified(self):
        result = lopa.audit(json.dumps(fixture()).encode(), SCHEMA)
        self.assertEqual(result["evidenceReferences"][0]["verification"], "not-performed")
        self.assertFalse(result["canonical"])
        self.assertEqual(result["unattributedGapIds"], ["builder"])

    def test_incompatible_version_and_unknown_fields_rejected(self):
        for version in ["1.1", "2.0", 1]:
            value = fixture()
            value["schemaVersion"] = version
            with self.assertRaises(ValidationError):
                lopa.audit(json.dumps(value).encode(), SCHEMA)
        value = fixture()
        value["verified"] = True
        with self.assertRaises(ValidationError):
            lopa.audit(json.dumps(value).encode(), SCHEMA)

    def test_missing_provenance_and_malformed_digest_rejected(self):
        value = fixture()
        del value["gaps"]["builder"]["provenance"]
        with self.assertRaises(ValidationError):
            lopa.audit(json.dumps(value).encode(), SCHEMA)
        value = fixture()
        value["gaps"]["builder"]["provenance"]["sha256"] = "not-a-hash"
        with self.assertRaises(ValidationError):
            lopa.audit(json.dumps(value).encode(), SCHEMA)

    def test_blocking_gap_is_reported(self):
        value = fixture()
        value["gaps"]["builder"]["blocksActivation"] = True
        self.assertEqual(lopa.audit(json.dumps(value).encode(), SCHEMA)["blockingGapIds"], ["builder"])

    def test_duplicate_json_keys_and_nan_rejected(self):
        for raw in [b'{"gaps": {}, "gaps": {}}', b'{"value": NaN}']:
            with self.assertRaises(ValueError):
                lopa.decode(raw)


if __name__ == "__main__":
    unittest.main()
