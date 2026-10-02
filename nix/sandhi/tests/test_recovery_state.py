"""Applicability transitions with positive claims; fixtures are not recovery proof."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/recovery_state.py'
spec = importlib.util.spec_from_file_location('recovery_state', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
SUBJECT = {'kind': 'output', 'path': '/nix/store/fixture-output'}


def snapshot(enabled=True):
    return json.dumps({'schema': 'sandhi.lopa', 'schemaVersion': '2.0',
                      'recoveryPolicy': {'retentionEnabled': enabled, 'subjects': [SUBJECT]}}).encode()


def declared():
    return r.record(r.activate(None, snapshot(), 'first'), 'first', SUBJECT,
                    'fixture:recovery', b'actual evidence fixture bytes', 'test-administrator')


class RecoveryStateTests(unittest.TestCase):
    def test_on_off_on_requires_new_declaration_and_preserves_history(self):
        first = declared()
        self.assertEqual(r.status(first)['status'], 'declared-recoverable')
        off = r.activate(first, snapshot(False), 'off')
        self.assertEqual(r.status(off)['status'], 'unassessed')
        self.assertEqual(off['history'], first['history'])
        self.assertEqual(off['history'][0]['snapshotSha256'], first['snapshotSha256'])
        with self.assertRaises(ValueError):
            r.record(off, 'off', SUBJECT, 'fixture:new', b'new', 'operator')
        again = r.activate(off, snapshot(), 'again')
        self.assertEqual(r.status(again)['status'], 'unassessed')
        with self.assertRaises(ValueError):
            r.record(again, 'first', SUBJECT, 'fixture:replay', b'old', 'operator')
        final = r.record(again, 'again', SUBJECT, 'fixture:revalidated', b'new', 'operator')
        self.assertEqual(r.status(final)['status'], 'declared-recoverable')
        self.assertEqual(len(final['history']), 2)
        self.assertEqual(r.status(final)['assessments'][0]['verification'], 'not-performed')

    def test_same_configuration_reactivation_also_invalidates(self):
        previous = declared()
        result = r.activate(previous, snapshot())
        self.assertNotEqual(result['epoch'], previous['epoch'])
        self.assertEqual(r.status(result)['status'], 'unassessed')
        self.assertEqual(result['history'], previous['history'])

    def test_unretained_subject_and_missing_identity_rejected(self):
        state = r.activate(None, snapshot(), 'epoch')
        for subject, identity in [({'kind': 'output', 'path': '/nix/store/other'}, 'operator'), (SUBJECT, '')]:
            with self.assertRaises(ValueError):
                r.record(state, 'epoch', subject, 'fixture', b'data', identity)

    def test_malformed_or_disabled_current_state_fails_closed(self):
        for state in [[], {}, {'schema': 'other'}]:
            with self.assertRaises(ValueError):
                r.status(state)
        for field, value in [('current', [True]), ('current', [30]), ('epoch', 'wrong')]:
            state = declared()
            state[field] = value
            with self.assertRaises(ValueError):
                r.status(state)
        state = declared()
        state['policy']['retentionEnabled'] = False
        with self.assertRaises(ValueError):
            r.status(state)
        self.assertEqual(r.status(None)['status'], 'unassessed')

    def test_cli_atomic_ledger_and_malformed_state_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / 'snapshot.json'; policy.write_bytes(snapshot())
            ledger = root / 'state.json'
            command = [sys.executable, str(SCRIPT), '--state', str(ledger)]
            result = subprocess.run(command + ['activate', str(policy)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(result.stdout)['status'], 'unassessed')
            policy.write_bytes(snapshot(False))
            mismatch = subprocess.run(command + ['--policy', str(policy), 'status'], capture_output=True)
            self.assertNotEqual(mismatch.returncode, 0)
            ledger.write_text('malformed')
            result = subprocess.run(command + ['activate', str(policy)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(ledger.read_text(), 'malformed')

    def test_v2_schema_requires_history_semantics_and_no_current_snapshot_claim(self):
        from test_lopa import fixture, lopa
        value = fixture()
        value.update(schemaVersion='2.0', evidenceSemantics='historical-declarations',
                     recoveryPolicy={'retentionEnabled': True, 'subjects': [SUBJECT]})
        schema = json.loads((ROOT / 'schemas/lopa-v2.schema.json').read_text())
        result = lopa.audit(json.dumps(value).encode(), schema)
        self.assertEqual(result['currentRecovery'], 'unassessed')
        self.assertEqual(result['evidenceReferences'][0]['verification'], 'not-performed')
        value['currentRecovery'] = 'recoverable'
        with self.assertRaises(ValidationError):
            lopa.audit(json.dumps(value).encode(), schema)
