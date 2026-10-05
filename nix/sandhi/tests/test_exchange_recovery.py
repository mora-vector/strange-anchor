"""Review regressions: crash commit boundaries and fixed conversation deadlines.

These drive durable node state without claiming a NixOS isolation result.
"""
import datetime
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_exchange_node as helpers

node = helpers.node


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = helpers.StateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_committed_terminal_recovered_after_crash_even_after_expiry(self):
        n = self.fixture.node()
        fields = helpers.envelope()
        self.fixture.receive(n, fields)
        terminal = {"status": "complete", "reason": "synthetic-result", "digest": "expected"}
        with patch.object(n, "invoke", return_value={"reply": None, "terminal": terminal}), \
             patch.object(n, "finish", side_effect=RuntimeError("crash after response commit")):
            with self.assertRaises(RuntimeError):
                n.work()
        self.assertIsNone(n.status())
        later = node.utcnow() + datetime.timedelta(seconds=400)
        with patch.object(node, "utcnow", return_value=later):
            restarted = self.fixture.node()
            with patch.object(restarted, "invoke", side_effect=AssertionError("must not re-invoke")):
                restarted.check_deadline()
                restarted.work()
        self.assertEqual(restarted.status()["status"], "complete")
        self.assertEqual(restarted.status()["digest"], "expected")
        self.assertEqual(restarted.conversation["deadline"], n.conversation["deadline"])

    def test_accepted_opening_recovers_binding_before_ack_and_work(self):
        n = self.fixture.node()
        before = (n.state / "conversation.json").read_bytes()
        fields = helpers.envelope(deadline=node.stamp(node.utcnow() + datetime.timedelta(seconds=20)))
        self.fixture.receive(n, fields)
        # The inbox rename survived; the following metadata write did not.
        node.durable_write(n.state / "conversation.json", before)
        restarted = self.fixture.node()
        self.assertEqual(restarted.conversation["conversation_id"], fields["conversation_id"])
        self.assertEqual(restarted.conversation["deadline"], fields["deadline"])
        _, ack = self.fixture.receive(restarted, fields)
        self.assertEqual(ack["result"], "duplicate")
        restarted.work()
        replies = [json.loads(raw) for raw in restarted.stored("outbox").values()]
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["conversation_id"], fields["conversation_id"])

    def test_recovered_completion_keeps_final_reply_pending_for_delivery(self):
        n = self.fixture.node()
        self.fixture.receive(n, helpers.envelope())
        output = {"reply": {"kind": "final", "status": "complete",
                            "reason": "synthetic-result", "payload": "saved-final"},
                  "terminal": {"status": "complete", "reason": "synthetic-result"}}
        with patch.object(n, "invoke", return_value=output), \
             patch.object(n, "finish", side_effect=RuntimeError("crash after response commit")):
            with self.assertRaises(RuntimeError):
                n.work()
        saved = n.stored("outbox")
        self.assertEqual(len(saved), 1)
        restarted = self.fixture.node()
        with patch.object(restarted, "invoke", side_effect=AssertionError("must not re-invoke")), \
             patch.object(restarted, "deliver") as deliver:
            restarted.work()
            restarted.send_pending(None)
        self.assertEqual(restarted.status()["status"], "complete")
        self.assertEqual(restarted.stored("outbox"), saved)
        mid, raw = next(iter(saved.items()))
        deliver.assert_called_once_with(mid, raw, 1, None)
        self.assertFalse(restarted.settled())

    def test_expired_outbox_is_not_retried_inside_a_longer_local_budget(self):
        n = self.fixture.node()
        fields = helpers.envelope(deadline=node.stamp(node.utcnow() + datetime.timedelta(seconds=20)))
        self.fixture.receive(n, fields)
        n.work()
        # Also guard old-format ledgers whose local deadline predates this fix.
        n.conversation["deadline"] = node.stamp(node.utcnow() + datetime.timedelta(seconds=300))
        later = node.utcnow() + datetime.timedelta(seconds=40)
        with patch.object(node, "utcnow", return_value=later), patch.object(n, "deliver") as deliver:
            n.send_pending(None)
        deliver.assert_not_called()
        self.assertEqual(n.status()["status"], "failed")
        self.assertIn("deadline-exceeded:undelivered:", n.status()["reason"])
        self.assertEqual(n.stored("delivery"), {})

    def test_responder_timeout_uses_remaining_deadline(self):
        n = self.fixture.node()
        now = node.utcnow()
        fields = helpers.envelope(deadline=node.stamp(now + datetime.timedelta(seconds=3)))
        process = SimpleNamespace(returncode=0, stdout=b'{"reply":null,"terminal":null}', stderr=b"")
        with patch.object(node, "utcnow", return_value=now), \
             patch.object(node.subprocess, "run", return_value=process) as run:
            n.invoke(fields["message_id"], fields)
        self.assertGreater(run.call_args.kwargs["timeout"], 0)
        self.assertLessEqual(run.call_args.kwargs["timeout"], 3)

    def test_result_finishing_after_deadline_cannot_create_reply_or_success(self):
        n = self.fixture.node()
        fields = helpers.envelope()
        raw, _ = self.fixture.receive(n, fields)
        later = node.utcnow() + datetime.timedelta(seconds=400)
        def late_result(*_):
            clock.return_value = later
            return {"reply": {"kind": "message", "payload": "too late"},
                    "terminal": {"status": "complete", "reason": "synthetic"}}
        with patch.object(node, "utcnow", return_value=node.utcnow()) as clock, \
             patch.object(n, "invoke", side_effect=late_result):
            n.step(fields["message_id"], raw)
        self.assertEqual(n.stored("outbox"), {})
        self.assertEqual(n.status()["status"], "failed")
        self.assertEqual(n.status()["reason"], "deadline-exceeded:responder")

    def test_ambiguous_json_id_gets_no_ack_and_no_acceptance(self):
        n = self.fixture.node()
        raw = b'{"message_id":"' + b"a" * 32 + b'","message_id":"' + b"b" * 32 + b'"}'
        self.assertIsNone(n.receive(raw, helpers.A, {"direction": "in"}))
        self.assertEqual(n.stored("inbox"), {})
        attempt = json.loads((n.state / "attempts.log").read_text())
        self.assertEqual(attempt["reason"], "duplicate-key")
        self.assertIsNone(attempt["message_id"])

    def test_new_admission_cannot_extend_expired_local_budget(self):
        n = self.fixture.node({"conversation_seconds": 1})
        fields = helpers.envelope()
        later = node.utcnow() + datetime.timedelta(seconds=10)
        with patch.object(node, "utcnow", return_value=later):
            _, ack = self.fixture.receive(n, fields)
        self.assertEqual((ack["result"], ack["reason"]), ("rejected", "expired"))
        self.assertEqual(n.stored("inbox"), {})


if __name__ == "__main__":
    unittest.main()
