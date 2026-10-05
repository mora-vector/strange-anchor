"""Stage A node: durable state transitions, and real TLS exchanges between processes.

State tests need only Python. Exchange tests also need the openssl command to make
ephemeral certificates; without it they are skipped with that reason. The
three-guest VM experiment covers the same transitions under Sandhi contracts.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("exchange_node", SCRIPTS / "exchange_node.py")
node = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node)
protocol = node.protocol
RESPONDER = [sys.executable, str(SCRIPTS / "exchange_responder.py")]
A, B = "installation-a", "installation-b"
OPENSSL = shutil.which("openssl")


def config(local, peer, port, peer_port, opener):
    return {"local_id": local, "peer_id": peer, "opener": opener, "responder": RESPONDER,
            "listen_address": "127.0.0.1", "port": port,
            "peer_address": "127.0.0.1", "peer_port": peer_port}


def envelope(**fields):
    value = {"schema": node.SCHEMA, "conversation_id": "c" * 32, "message_id": secrets.token_hex(16),
             "parent_id": None, "sender": A, "recipient": B, "turn": 0, "kind": "message",
             "deadline": node.stamp(node.utcnow() + datetime.timedelta(seconds=300)),
             "payload": json.dumps({"x": "11" * 16})}
    value.update(fields)
    return value


class StateTests(unittest.TestCase):
    """Node transitions driven directly; no sockets or certificates."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.credentials = self.root / "credentials"
        self.credentials.mkdir()
        (self.credentials / "map").write_text("{}")
        (self.credentials / "input").write_text("22" * 16)

    def node(self, trial=None):
        if trial is not None:
            (self.credentials / "trial").write_text(json.dumps(trial))
        state = self.root / "state"
        state.mkdir(exist_ok=True)
        return node.Node(config(B, A, 1, 2, opener=False), self.credentials, state)

    def receive(self, n, fields):
        raw = protocol.encode_envelope(fields) if fields["turn"] <= 7 else node.canonical(fields)
        return raw, json.loads(n.receive(raw, A, {"direction": "in"}))

    def test_duplicate_is_acknowledged_once_and_conflict_rejected(self):
        n = self.node()
        fields = envelope()
        raw, ack = self.receive(n, fields)
        self.assertEqual(ack["result"], "accepted")
        self.assertEqual((n.state / "inbox" / fields["message_id"]).read_bytes(), raw)
        _, again = self.receive(n, fields)
        self.assertEqual(again["result"], "duplicate")
        changed = dict(fields, payload=fields["payload"] + " ")
        _, conflict = self.receive(n, changed)
        self.assertEqual((conflict["result"], conflict["reason"]), ("rejected", "conflicting-bytes"))
        self.assertEqual((n.state / "inbox" / fields["message_id"]).read_bytes(), raw)
        results = [json.loads(line)["result"] for line in
                   (n.state / "attempts.log").read_text().splitlines()]
        self.assertEqual(results, ["accepted", "duplicate", "rejected"])

    def test_expired_duplicate_is_still_a_duplicate_but_expired_new_is_refused(self):
        n = self.node()
        fields = envelope()
        self.receive(n, fields)
        past = node.utcnow() + datetime.timedelta(seconds=400)
        original = node.utcnow
        node.utcnow = lambda: past
        try:
            _, again = self.receive(n, fields)
            _, late = self.receive(n, envelope(turn=1, parent_id="d" * 32,
                                               deadline=fields["deadline"]))
        finally:
            node.utcnow = original
        self.assertEqual(again["result"], "duplicate")
        self.assertEqual((late["result"], late["reason"]), ("rejected", "expired"))

    def test_identity_turn_and_parent_checks(self):
        n = self.node()
        _, wrong = self.receive(n, envelope(sender="installation-c"))
        self.assertEqual((wrong["result"], wrong["reason"]), ("rejected", "sender-mismatch"))
        _, over = self.receive(n, envelope(turn=8, parent_id="d" * 32))
        self.assertEqual((over["result"], over["reason"]), ("rejected", "turn-limit"))
        _, orphan = self.receive(n, envelope(turn=1, parent_id="d" * 32))
        self.assertEqual(orphan["reason"], "unknown-parent")
        self.receive(n, envelope())
        _, second = self.receive(n, envelope())
        self.assertEqual(second["reason"], "unexpected-opening")
        _, other = self.receive(n, envelope(conversation_id="e" * 32))
        self.assertEqual(other["reason"], "conversation-mismatch")
        self.assertFalse((n.state / "outbox").exists())

    def test_reinvocation_after_crash_keeps_one_reply(self):
        n = self.node()
        fields = envelope()
        self.receive(n, fields)
        n.work()
        replies = n.stored("outbox")
        self.assertEqual(len(replies), 1)
        reply_id, reply = next(iter(replies.items()))
        # Crash after the durable reply, before the step's commit record.
        (n.state / "responses" / f"{fields['message_id']}.json").unlink()
        restarted = self.node()
        restarted.work()
        self.assertEqual(restarted.stored("outbox"), {reply_id: reply})
        invocations = [json.loads(line) for line in
                       (n.state / "invocations.log").read_text().splitlines()]
        self.assertEqual([i["event"] for i in invocations], ["invoke", "result"] * 2)
        message = json.loads(reply)
        self.assertEqual((message["turn"], message["parent_id"], message["deadline"]),
                         (1, fields["message_id"], fields["deadline"]))

    def test_deadline_and_fault_markers_survive_restart(self):
        first = self.node({"label": "t", "faults": ["I1"], "conversation_seconds": 30})
        self.assertTrue(first.fault("I1"))
        second = self.node()
        self.assertEqual(second.conversation, first.conversation)
        self.assertFalse(second.fault("I1"))

    def test_deadline_without_messages_is_an_explicit_failure(self):
        n = self.node({"conversation_seconds": 1})
        original = node.utcnow
        node.utcnow = lambda: original() + datetime.timedelta(seconds=5)
        try:
            n.check_deadline()
        finally:
            node.utcnow = original
        self.assertEqual((n.status()["status"], n.status()["reason"]),
                         ("failed", "deadline-exceeded:no-message-received"))

    def test_no_new_work_after_the_persisted_deadline(self):
        n = self.node({"conversation_seconds": 30})
        fields = envelope()
        self.receive(n, fields)
        original = node.utcnow
        node.utcnow = lambda: original() + datetime.timedelta(seconds=60)
        try:
            n.work()
            self.assertFalse((n.state / "invocations.log").exists())
            n.check_deadline()
        finally:
            node.utcnow = original
        self.assertEqual(n.status()["reason"], "deadline-exceeded:incomplete")

    def test_expired_message_is_not_worked_inside_the_conversation(self):
        n = self.node()
        fields = envelope(deadline=node.stamp(node.utcnow() + datetime.timedelta(seconds=2)))
        self.receive(n, fields)
        original = node.utcnow
        node.utcnow = lambda: original() + datetime.timedelta(seconds=10)
        try:
            n.work()
            n.check_deadline()
        finally:
            node.utcnow = original
        self.assertFalse((n.state / "invocations.log").exists())
        # Accepting the opening now persists the earlier deadline as the
        # conversation deadline, so the whole conversation expires together.
        self.assertEqual(n.conversation["deadline"], fields["deadline"])
        self.assertEqual(n.status()["reason"], "deadline-exceeded:incomplete")

    def test_expired_outbox_message_is_settled_once(self):
        n = self.node()
        expired = envelope(sender=B, recipient=A,
                           deadline=node.stamp(node.utcnow() - datetime.timedelta(seconds=1)))
        node.durable_write(n.state / "outbox" / expired["message_id"],
                           protocol.encode_envelope(expired))
        n.send_pending(client_context=None)
        n.send_pending(client_context=None)
        events = [json.loads(line)["event"] for line in
                  (n.state / "events.log").read_text().splitlines()]
        self.assertEqual(events.count("undeliverable"), 1)
        self.assertNotIn("later-outcome-ignored", events)
        self.assertTrue(n.settled())
        self.assertFalse((n.state / "delivery").exists())
        self.assertEqual(n.status()["reason"],
                         f"deadline-exceeded:undelivered:{expired['message_id']}")

    def test_unknown_trial_keys_and_faults_are_refused(self):
        with self.assertRaises(ValueError):
            self.node({"max_attempts": 1})
        with self.assertRaises(ValueError):
            self.node({"faults": ["I4"]})


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def certificate(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run([OPENSSL, "req", "-x509", "-newkey", "ec",
                    "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-days", "1",
                    "-subj", f"/CN={name}", "-addext", "basicConstraints=critical,CA:TRUE",
                    "-addext", "keyUsage=critical,digitalSignature,keyCertSign",
                    "-keyout", str(directory / "key"), "-out", str(directory / "cert")],
                   check=True, capture_output=True)
    pem = (directory / "cert").read_text()
    return pem, hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()


@unittest.skipUnless(OPENSSL, "openssl is unavailable; the VM experiment covers TLS")
class ExchangeTests(unittest.TestCase):
    """Two node processes over loopback TLS; faults exit as they would under systemd."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        ports = {A: free_port(), B: free_port()}
        self.inputs = {A: secrets.token_hex(16), B: secrets.token_hex(16)}
        pems, prints = {}, {}
        for name in (A, B):
            pems[name], prints[name] = certificate(self.root / name / "credentials", name)
        self.paths = {}
        for local, peer in ((A, B), (B, A)):
            credentials = self.root / local / "credentials"
            (credentials / "trust").write_text(pems[peer])
            (credentials / "map").write_text(json.dumps({prints[peer]: peer}))
            (credentials / "input").write_text(self.inputs[local])
            value = config(local, peer, ports[local], ports[peer], opener=local == A)
            (self.root / local / "config.json").write_text(json.dumps(value))
            (self.root / local / "state").mkdir()
            self.paths[local] = (self.root / local / "config.json", credentials,
                                 self.root / local / "state")

    def trial(self, local, **value):
        (self.paths[local][1] / "trial").write_text(json.dumps(value))

    def start(self, local):
        config_path, credentials, state = self.paths[local]
        with open(self.root / local / "stderr.log", "ab") as log:
            return subprocess.Popen([sys.executable, str(SCRIPTS / "exchange_node.py"),
                                     "--config", str(config_path), "--credentials",
                                     str(credentials), "--state", str(state)], stderr=log)

    def run_pair(self, timeout=90):
        """Restart a node that exits with the fault code, as Restart=on-failure would."""
        processes = {name: self.start(name) for name in (B, A)}
        restarts = {A: 0, B: 0}
        limit = time.monotonic() + timeout
        while processes and time.monotonic() < limit:
            for name, process in list(processes.items()):
                code = process.poll()
                if code is None:
                    continue
                if code == node.FAULT_EXIT:
                    restarts[name] += 1
                    time.sleep(0.5)
                    processes[name] = self.start(name)
                else:
                    self.assertEqual(code, 0, (self.root / name / "stderr.log").read_text())
                    del processes[name]
            time.sleep(0.1)
        for process in processes.values():
            process.kill()
        self.assertFalse(processes, "nodes did not finish")
        return restarts

    def state(self, local, *parts):
        return self.paths[local][2].joinpath(*parts)

    def expected(self):
        return hashlib.sha256(bytes.fromhex(self.inputs[A]) + bytes.fromhex(self.inputs[B])).hexdigest()

    def assert_complete(self):
        for name in (A, B):
            status = json.loads(self.state(name, "status.json").read_text())
            self.assertEqual((status["status"], status["digest"]), ("complete", self.expected()),
                             status)
        # Byte agreement: every acknowledged sent message equals the peer's stored bytes.
        for sender, receiver in ((A, B), (B, A)):
            for path in self.state(sender, "outbox").iterdir():
                self.assertEqual(path.read_bytes(),
                                 self.state(receiver, "inbox", path.name).read_bytes())

    def attempts(self, local):
        return [json.loads(line) for line in self.state(local, "attempts.log").read_text().splitlines()]

    def test_split_input_exchange_completes_with_matching_bytes(self):
        restarts = self.run_pair()
        self.assertEqual(restarts, {A: 0, B: 0})
        self.assert_complete()
        self.assertEqual(sorted(json.loads(p.read_bytes())["turn"] for p in
                                self.state(A, "outbox").iterdir()), [0, 2])

    def test_duplicate_and_conflicting_resends_are_recorded(self):
        self.trial(A, faults=["resend-acked", "conflict"])
        self.run_pair()
        self.assert_complete()
        faults = {r["fault"]: (r["result"], r["reason"]) for r in self.attempts(A) if "fault" in r}
        self.assertEqual(faults, {"resend-acked": ("ack-duplicate", ""),
                                  "conflict": ("ack-rejected", "conflicting-bytes")})
        received = [(r["result"], r.get("reason")) for r in self.attempts(B)
                    if r["direction"] == "in"]
        self.assertIn(("duplicate", None), received)
        self.assertIn(("rejected", "conflicting-bytes"), received)
        invoked = [json.loads(line)["incoming"] for line in
                   self.state(B, "invocations.log").read_text().splitlines()]
        self.assertEqual(len(invoked), len(set(invoked)) * 2)  # One invocation per message.

    def test_interruption_points_restart_and_complete(self):
        for local, point in ((B, "I1"), (B, "I2"), (A, "I3")):
            with self.subTest(point=point):
                self.setUp()
                self.trial(local, faults=[point])
                restarts = self.run_pair()
                self.assertEqual(restarts[local], 1, point)
                self.assertTrue(self.state(local, "faults-fired", point).exists())
                self.assert_complete()


if __name__ == "__main__":
    unittest.main()
