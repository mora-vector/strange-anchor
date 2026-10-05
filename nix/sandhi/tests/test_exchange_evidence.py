"""Synthetic corruption tests for the offline evidence checker; no VM claim."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_exchange_evidence as checker


def raw(value):
    return json.dumps(value).encode()


def pair():
    expected = hashlib.sha256(bytes.fromhex("11" * 16 + "22" * 16)).hexdigest()
    envelopes = []
    for turn, sender, receiver, body in (
            (0, "a", "b", {"x": "11" * 16}),
            (1, "b", "a", {"x": "22" * 16, "digest": expected}),
            (2, "a", "b", {"digest": expected})):
        value = dict(schema="sandhi-exchange.v1", conversation_id="f" * 32,
                     message_id=str(turn + 1) * 32,
                     parent_id=str(turn) * 32 if turn else None,
                     sender="installation-" + sender, recipient="installation-" + receiver,
                     turn=turn, deadline="2000-01-01T00:00:00Z",
                     kind="final" if turn == 2 else "message", payload=json.dumps(body))
        if turn == 2:
            value.update(status="complete", reason="synthetic")
        envelopes.append((sender, receiver, value))
    states = {n: {"status.json": raw({"status": "complete", "digest": expected})} for n in ("a", "b")}
    for sender, receiver, value in envelopes:
        mid = value["message_id"]
        states[sender]["outbox/" + mid] = raw(value)
        states[receiver]["inbox/" + mid] = raw(value)
        states[sender]["acks/" + mid] = raw({"ack": mid, "result": "accepted", "reason": ""})
        states[sender]["delivery/" + mid] = b"1"
    return states, {"expectedDigest": expected, "complete": True}


class EvidenceTests(unittest.TestCase):
    def test_recomputes_historical_results_without_live_expiry(self):
        states, report = pair()
        self.assertEqual(checker.check_pair(states, report), 3)

    def test_altered_or_missing_bytes_and_acks_fail_despite_success_flag(self):
        states, report = pair()
        for kind in ("bytes", "missing", "ack"):
            changed = copy.deepcopy(states)
            if kind == "bytes":
                changed["b"]["inbox/" + "1" * 32] += b" "
            elif kind == "missing":
                del changed["a"]["outbox/" + "3" * 32]
            else:
                del changed["a"]["acks/" + "3" * 32]
            with self.subTest(kind=kind), self.assertRaises(checker.EvidenceError):
                checker.check_pair(changed, report)

    def test_matching_falsified_status_digests_do_not_replace_computation(self):
        states, report = pair()
        report["expectedDigest"] = "0" * 64
        for files in states.values():
            files["status.json"] = raw({"status": "complete", "digest": "0" * 64})
        with self.assertRaisesRegex(checker.EvidenceError, "driver digest mismatch"):
            checker.check_pair(states, report)

    def test_changed_parent_chain_and_rejected_delivery_are_not_success(self):
        states, report = pair()
        for kind in ("parent", "ack", "budget"):
            changed = copy.deepcopy(states)
            if kind == "parent":
                message = json.loads(changed["a"]["outbox/" + "3" * 32])
                message["parent_id"] = "7" * 32
                changed["a"]["outbox/" + "3" * 32] = raw(message)
                changed["b"]["inbox/" + "3" * 32] = raw(message)
            elif kind == "ack":
                changed["a"]["acks/" + "3" * 32] = raw({"ack": "3" * 32, "result": "rejected", "reason": "x"})
            else:
                changed["a"]["delivery/" + "3" * 32] = b"31"
            with self.subTest(kind=kind), self.assertRaises((checker.EvidenceError, checker.protocol.ProtocolError)):
                checker.check_pair(changed, report)

    def test_wrong_source_or_missing_trials_cannot_be_hidden_by_pass_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            report = raw({"allAssertionsPassed": True, "errors": [], "trials": {}})
            (path / "stage-a.json").write_bytes(report)
            summary = {"source": {"commit": "a" * 40}, "output": {"stageASha256": checker.digest(report)}}
            (path / "SUMMARY.json").write_bytes(raw(summary))
            with self.assertRaisesRegex(checker.EvidenceError, "source commit mismatch"):
                checker.verify(path, "b" * 40)
            with self.assertRaisesRegex(checker.EvidenceError, "missing or unexpected trials"):
                checker.verify(path, "a" * 40)
            (path / "stage-a.json").write_bytes(report + b" ")
            with self.assertRaisesRegex(checker.EvidenceError, "report hash mismatch"):
                checker.verify(path, "a" * 40)

    def test_archive_links_traversal_and_duplicate_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.tar"
            for kind in ("link", "traversal", "duplicate"):
                with tarfile.open(path, "w") as archive:
                    member = tarfile.TarInfo("../outside" if kind == "traversal" else "./status.json")
                    if kind == "link":
                        member.type, member.linkname = tarfile.SYMTYPE, "/outside"
                    archive.addfile(member, io.BytesIO())
                    if kind == "duplicate":
                        archive.addfile(member, io.BytesIO())
                with self.subTest(kind=kind), self.assertRaises(checker.EvidenceError):
                    checker.read_state(path)


if __name__ == "__main__":
    unittest.main()
