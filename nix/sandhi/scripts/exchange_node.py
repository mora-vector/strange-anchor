#!/usr/bin/env python3
"""Stage A exchange node: one Sandhi contract per installation.

Scope: DECISIONS.md, 2026-10-05 (Stage A adopted). A deterministic transport test,
not an AI conversation. The node accepts mutually authenticated TLS from one mapped
peer, keeps the exact bytes it receives and sends in durable state, invokes a
replaceable responder, retransmits until acknowledged, and always leaves an
explicit terminal status. Retries and faults are recorded, never erased.

Envelope decoding and framing belong to exchange_protocol.py (Tessera). This file
owns authentication, durable state transitions, delivery and fault injection.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exchange_protocol as protocol  # noqa: E402

SCHEMA = "sandhi-exchange.v1"
# Adopted budgets (DECISIONS.md 2026-10-05). A trial may set only the
# conversation length, the linger after a terminal status, and declared faults.
LIMITS = {"max_frame": 16384, "max_turn": 7, "connect_timeout": 5, "retransmit_interval": 2,
          "max_attempts": 30, "conversation_seconds": 300, "linger_seconds": 5,
          "idle_timeout": 120, "responder_timeout": 60}
TRIAL_KEYS = {"label", "faults", "conversation_seconds", "linger_seconds"}
# I1: before durable acceptance. I2: after acceptance, before its ack.
# I3: after sending an outbox frame, before reading its ack.
FAULTS = {"I1", "I2", "I3", "resend-acked", "conflict"}
FAULT_EXIT = 75


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def precise(moment=None):
    return (moment or utcnow()).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_stamp(text):
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def encode(fields):
    """Envelope bytes from the shared encoder, which checks syntax and size."""
    return protocol.encode_envelope(fields)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_id(value):
    return isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdef" for c in value)


def message_id_hint(raw):
    """Best-effort ID for acknowledging a rejected frame. Never used to accept one."""
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    candidate = value.get("message_id") if isinstance(value, dict) else None
    return candidate if is_id(candidate) else None


def code(error):
    return getattr(error, "code", None) or type(error).__name__


def valid_output(output):
    reply, terminal = output.get("reply"), output.get("terminal")
    if set(output) - {"reply", "terminal"}:
        return False
    if reply is not None and not (isinstance(reply, dict) and isinstance(reply.get("payload"), str)):
        return False
    return terminal is None or (isinstance(terminal, dict)
                                and terminal.get("status") in {"complete", "failed"})


def durable_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def tls_context(credentials, server):
    """Mutual TLS 1.3. Identity is the pinned certificate fingerprint, not a hostname."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    if not server:
        context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(credentials / "cert", credentials / "key")
    context.load_verify_locations(cafile=str(credentials / "trust"))
    return context


def fingerprint(tls):
    return sha(tls.getpeercert(binary_form=True))


class Node:
    def __init__(self, config, credentials, state):
        self.config = config
        self.local_id, self.peer_id = config["local_id"], config["peer_id"]
        self.peer = (config["peer_address"], config["peer_port"])
        self.credentials = Path(credentials)
        self.authorized = json.loads((self.credentials / "map").read_text())
        self.private_input = (self.credentials / "input").read_text().strip()
        trial_path = self.credentials / "trial"
        self.trial = json.loads(trial_path.read_text()) if trial_path.exists() else {}
        unknown = set(self.trial) - TRIAL_KEYS
        if unknown:
            raise ValueError(f"unsupported trial keys: {sorted(unknown)}")
        self.faults = set(self.trial.get("faults", []))
        if self.faults - FAULTS:
            raise ValueError(f"unknown faults: {sorted(self.faults - FAULTS)}")
        self.limits = dict(LIMITS)
        for key in ("conversation_seconds", "linger_seconds"):
            if key in self.trial:
                self.limits[key] = int(self.trial[key])
        self.state = Path(state)
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.next_try = {}
        self.exhausted = set()
        self.conversation = self._conversation()

    # Durable state ----------------------------------------------------------
    def _conversation(self):
        path = self.state / "conversation.json"
        if path.exists():
            return json.loads(path.read_bytes())
        started = utcnow()
        value = {"local_id": self.local_id, "peer_id": self.peer_id,
                 "opener": bool(self.config["opener"]), "trial": self.trial.get("label"),
                 "conversation_id": secrets.token_hex(16) if self.config["opener"] else None,
                 "started_at": precise(started),
                 # Fixed at first start; a restart never renews it.
                 "deadline": stamp(started + datetime.timedelta(
                     seconds=self.limits["conversation_seconds"]))}
        durable_write(path, canonical(value))
        return value

    def log(self, name, record):
        line = canonical({"at": precise(), **record}) + b"\n"
        with self.lock, open(self.state / name, "ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())

    def stored(self, folder):
        directory = self.state / folder
        if not directory.is_dir():
            return {}
        return {path.name: path.read_bytes() for path in directory.iterdir()
                if not path.name.endswith(".tmp")}

    def status(self):
        path = self.state / "status.json"
        return json.loads(path.read_bytes()) if path.exists() else None

    def finish(self, status, reason, **extra):
        """Record the first terminal outcome; later outcomes are logged, not applied."""
        with self.lock:
            if self.status() is not None:
                self.log("events.log", {"event": "later-outcome-ignored", "status": status,
                                        "reason": reason})
                return
            value = {"status": status, "reason": reason, "decided_at": precise(),
                     "local_id": self.local_id,
                     "conversation_id": self.conversation["conversation_id"], **extra}
            durable_write(self.state / "status.json", canonical(value))
            self.log("events.log", {"event": "terminal", "status": status, "reason": reason})

    def fault(self, point):
        """A declared fault fires once per trial; the marker survives restarts."""
        if point not in self.faults:
            return False
        marker = self.state / "faults-fired" / point
        with self.lock:
            if marker.exists():
                return False
            durable_write(marker, precise().encode())
            self.log("events.log", {"event": "fault", "point": point})
        return True

    # Inbound ----------------------------------------------------------------
    def receive(self, raw, peer, context):
        """Return the ack bytes for one frame, or None when no ack can be addressed."""
        try:
            message = protocol.decode_envelope(raw, local_id=self.local_id, peer_id=peer,
                                               check_deadline=False)
        except protocol.ProtocolError as error:
            return self.reject(getattr(error, "message_id", None) or message_id_hint(raw),
                               code(error), context, raw)
        mid = message["message_id"]
        with self.lock:
            path = self.state / "inbox" / mid
            if path.exists():
                # An exact retransmission is acknowledged, never executed again.
                if path.read_bytes() == raw:
                    self.log("attempts.log", {**context, "message_id": mid,
                                              "result": "duplicate", "sha256": sha(raw)})
                    return protocol.encode_ack(mid, "duplicate")
                return self.reject(mid, "conflicting-bytes", context, raw)
            problem = self.admit(raw, peer, message)
            if problem:
                return self.reject(mid, problem, context, raw)
            if self.fault("I1"):
                os._exit(FAULT_EXIT)
            durable_write(path, raw)
            if self.conversation["conversation_id"] is None:
                self.conversation["conversation_id"] = message["conversation_id"]
                durable_write(self.state / "conversation.json", canonical(self.conversation))
            self.log("attempts.log", {**context, "message_id": mid, "turn": message["turn"],
                                      "result": "accepted", "sha256": sha(raw)})
        if self.fault("I2"):
            os._exit(FAULT_EXIT)
        return protocol.encode_ack(mid, "accepted")

    def admit(self, raw, peer, message):
        """Checks that apply only to a message not yet durably accepted."""
        try:
            protocol.decode_envelope(raw, local_id=self.local_id, peer_id=peer, now=utcnow(),
                                     conversation_id=self.conversation["conversation_id"])
        except protocol.ProtocolError as error:
            return code(error)
        if self.status() is not None:
            return "conversation-closed"
        inbox = {mid: json.loads(raw) for mid, raw in self.stored("inbox").items()}
        if message["parent_id"] is None:
            if self.config["opener"] or inbox:
                return "unexpected-opening"
            return None
        if any(m["parent_id"] == message["parent_id"] for m in inbox.values()):
            return "parent-already-answered"
        parent = self.stored("outbox").get(message["parent_id"])
        if parent is None:
            return "unknown-parent"
        try:
            protocol.validate_parent(message, json.loads(parent))
        except protocol.ProtocolError as error:
            return code(error)
        return None

    def reject(self, mid, reason, context, raw):
        self.log("attempts.log", {**context, "message_id": mid, "result": "rejected",
                                  "reason": reason, "bytes": len(raw), "sha256": sha(raw)})
        return protocol.encode_ack(mid, "rejected", reason) if mid else None

    def serve(self, connection, address, server_context):
        context = {"direction": "in", "from": address[0]}
        connection.settimeout(self.limits["idle_timeout"])
        try:
            tls = server_context.wrap_socket(connection, server_side=True)
        except (ssl.SSLError, OSError) as error:
            self.log("attempts.log", {**context, "result": "tls-failed",
                                      "reason": f"{type(error).__name__}: {error}"})
            connection.close()
            return
        with tls:
            context["fingerprint"] = fingerprint(tls)
            peer = self.authorized.get(context["fingerprint"])
            if peer != self.peer_id:
                # TLS trust passed but this certificate authorises no installation.
                self.log("attempts.log", {**context, "result": "unauthenticated",
                                          "reason": "unmapped-certificate" if peer is None
                                          else f"unexpected-installation:{peer}"})
                return
            context["peer"] = peer
            stream = tls.makefile("rwb")
            while not self.stopping.is_set():
                try:
                    if not stream.peek(1):
                        return  # Clean close at a frame boundary.
                    raw = protocol.read_frame(stream, max_bytes=self.limits["max_frame"])
                except protocol.ProtocolError as error:
                    self.log("attempts.log", {**context, "result": "rejected",
                                              "reason": code(error), "stage": "frame"})
                    return
                except (OSError, ssl.SSLError):
                    return
                ack = self.receive(raw, peer, context)
                if ack is None:
                    return
                try:
                    protocol.write_frame(stream, ack, max_bytes=self.limits["max_frame"])
                    stream.flush()
                except (OSError, ssl.SSLError):
                    return

    def listen(self, server):
        server_context = tls_context(self.credentials, server=True)
        server.settimeout(0.5)
        while not self.stopping.is_set():
            try:
                connection, address = server.accept()
            except (socket.timeout, TimeoutError):
                continue
            threading.Thread(target=self.serve, args=(connection, address, server_context),
                             daemon=True).start()

    # Worker -----------------------------------------------------------------
    def history(self, exclude=None):
        entries = [("in", json.loads(raw)) for mid, raw in self.stored("inbox").items()
                   if mid != exclude]
        entries += [("out", json.loads(raw)) for raw in self.stored("outbox").values()]
        return [{"direction": d, "envelope": e}
                for d, e in sorted(entries, key=lambda item: item[1]["turn"])]

    def expired(self):
        return utcnow() > parse_stamp(self.conversation["deadline"])

    def work(self):
        """New work stays inside the persisted deadline and the message's own deadline."""
        if self.status() is not None or self.expired():
            return
        if self.config["opener"] and not (self.state / "responses" / "open.json").exists():
            self.step(None, None)
        inbox = sorted(((json.loads(raw)["turn"], mid, raw)
                        for mid, raw in self.stored("inbox").items()))
        for _, mid, raw in inbox:
            if self.status() is not None or self.expired():
                return
            if (self.state / "responses" / f"{mid}.json").exists():
                continue
            try:
                protocol.validate_deadline(json.loads(raw), now=utcnow())
            except protocol.ProtocolError as error:
                self.finish("failed", f"deadline-exceeded:before-work:{mid}:{code(error)}")
                return
            self.step(mid, raw)

    def invoke(self, incoming_id, incoming):
        request = {"local_id": self.local_id, "peer_id": self.peer_id,
                   "private_input": self.private_input, "incoming": incoming,
                   "history": self.history(exclude=incoming_id)}
        self.log("invocations.log", {"event": "invoke", "incoming": incoming_id})
        started = time.monotonic()
        try:
            run = subprocess.run(self.config["responder"], input=canonical(request),
                                 capture_output=True, check=False,
                                 timeout=self.limits["responder_timeout"])
        except subprocess.TimeoutExpired:
            self.log("invocations.log", {"event": "timeout", "incoming": incoming_id})
            return None
        self.log("invocations.log", {
            "event": "result", "incoming": incoming_id, "exit": run.returncode,
            "seconds": round(time.monotonic() - started, 3), "stdout_sha256": sha(run.stdout),
            "stderr": run.stderr.decode(errors="replace")[-400:]})
        if run.returncode != 0:
            return None
        try:
            output = json.loads(run.stdout)
        except ValueError:
            return None
        return output if isinstance(output, dict) else None

    def step(self, incoming_id, raw):
        key = incoming_id or "open"
        incoming = json.loads(raw) if raw else None
        output = self.invoke(incoming_id, incoming)
        reply, terminal = None, {"status": "failed", "reason": "responder-error"}
        if output is not None and valid_output(output):
            reply, terminal = output.get("reply"), output.get("terminal")
        reply_id = None
        if reply:
            turn = incoming["turn"] + 1 if incoming else 0
            if turn > self.limits["max_turn"]:
                terminal = terminal or {"status": "failed", "reason": "turn-limit-reached"}
            else:
                deadline = incoming["deadline"] if incoming else self.conversation["deadline"]
                reply_id, problem = self.write_reply(key, incoming_id, turn, deadline, reply)
                if problem:
                    reply_id, terminal = None, {"status": "failed", "reason": problem}
        # Commit point of this step: written only after the reply is durable.
        durable_write(self.state / "responses" / f"{key}.json",
                      canonical({"incoming": incoming_id, "reply": reply_id,
                                 "terminal": terminal}))
        if terminal:
            extra = {k: v for k, v in terminal.items() if k not in {"status", "reason"}}
            self.finish(terminal["status"], terminal.get("reason", ""), **extra)

    def write_reply(self, key, incoming_id, turn, deadline, reply):
        # Derived from the incoming message, so re-invocation cannot add a second reply.
        reply_id = sha(f"{self.conversation['conversation_id']}/{key}/{self.local_id}".encode())[:32]
        fields = {"schema": SCHEMA, "conversation_id": self.conversation["conversation_id"],
                  "message_id": reply_id, "parent_id": incoming_id, "sender": self.local_id,
                  "recipient": self.peer_id, "turn": turn,
                  # An opening sets the conversation's deadline; replies keep the parent's.
                  "deadline": deadline, "kind": reply.get("kind"),
                  "payload": reply.get("payload")}
        if reply.get("kind") == "final":
            fields["status"], fields["reason"] = reply.get("status"), reply.get("reason", "")
        try:
            raw = encode(fields)
            # Round-trip through the shared decoder before anything is stored.
            protocol.decode_envelope(raw, local_id=self.peer_id, peer_id=self.local_id,
                                     check_deadline=False)
        except protocol.ProtocolError as error:
            return None, f"reply-invalid:{code(error)}"
        if len(raw) > self.limits["max_frame"]:
            return None, "reply-too-large"
        path = self.state / "outbox" / reply_id
        with self.lock:
            if path.exists():
                if path.read_bytes() != raw:
                    self.log("events.log", {"event": "reinvocation-differs", "message_id": reply_id,
                                            "kept_sha256": sha(path.read_bytes()),
                                            "discarded_sha256": sha(raw)})
            else:
                durable_write(path, raw)
        return reply_id, None

    # Outbound ---------------------------------------------------------------
    def send_pending(self, client_context):
        if self.expired():
            return
        acks = self.stored("acks")
        outbox = sorted(self.stored("outbox").items(), key=lambda item: json.loads(item[1])["turn"])
        for mid, raw in outbox:
            if mid in acks or mid in self.exhausted or time.monotonic() < self.next_try.get(mid, 0):
                continue
            counter = self.state / "delivery" / mid
            attempts = int(counter.read_text()) if counter.exists() else 0
            if attempts >= self.limits["max_attempts"]:
                self.exhausted.add(mid)
                self.log("events.log", {"event": "undeliverable", "message_id": mid,
                                        "attempts": attempts})
                self.finish("failed", f"delivery-exhausted:{mid}")
                continue
            # Counted before the attempt, so a crash mid-attempt still counts.
            durable_write(counter, str(attempts + 1).encode())
            self.deliver(mid, raw, attempts + 1, client_context)
            self.next_try[mid] = time.monotonic() + self.limits["retransmit_interval"]

    def transfer(self, stream, mid, raw):
        protocol.write_frame(stream, raw, max_bytes=self.limits["max_frame"])
        if self.fault("I3"):
            os._exit(FAULT_EXIT)
        ack_raw = protocol.read_frame(stream, max_bytes=self.limits["max_frame"])
        return ack_raw, protocol.decode_ack(ack_raw, message_id=mid)

    def deliver(self, mid, raw, attempt, client_context):
        context = {"direction": "out", "message_id": mid, "attempt": attempt,
                   "to": self.peer[0]}
        try:
            connection = socket.create_connection(self.peer, timeout=self.limits["connect_timeout"])
        except OSError as error:
            self.log("attempts.log", {**context, "result": "connect-failed",
                                      "reason": f"{type(error).__name__}: {error}"})
            return
        try:
            tls = client_context.wrap_socket(connection)
        except (ssl.SSLError, OSError) as error:
            connection.close()
            self.log("attempts.log", {**context, "result": "tls-failed",
                                      "reason": f"{type(error).__name__}: {error}"})
            return
        with tls:
            context["fingerprint"] = fingerprint(tls)
            if self.authorized.get(context["fingerprint"]) != self.peer_id:
                self.log("attempts.log", {**context, "result": "peer-unauthenticated"})
                return
            stream = tls.makefile("rwb")
            try:
                ack_raw, ack = self.transfer(stream, mid, raw)
            except (OSError, ssl.SSLError, protocol.ProtocolError) as error:
                self.log("attempts.log", {**context, "result": "transfer-failed",
                                          "reason": code(error)})
                return
            result = ack.get("result")
            self.log("attempts.log", {**context, "result": f"ack-{result}",
                                      "reason": ack.get("reason", "")})
            durable_write(self.state / "acks" / mid, ack_raw)
            if result == "rejected":
                self.finish("failed", f"peer-rejected:{mid}:{ack.get('reason', '')}")
                return
            self.inject(stream, mid, raw, context)

    def inject(self, stream, mid, raw, context):
        """Declared transport faults after an acknowledged delivery; never a relay."""
        variants = []
        if self.fault("resend-acked"):
            variants.append(("resend-acked", raw))
        if self.fault("conflict"):
            fields = json.loads(raw)
            fields["payload"] = fields["payload"] + " "
            variants.append(("conflict", encode(fields)))
        for name, data in variants:
            try:
                _, ack = self.transfer(stream, mid, data)
                outcome = {"result": f"ack-{ack.get('result')}", "reason": ack.get("reason", "")}
            except (OSError, ssl.SSLError, protocol.ProtocolError) as error:
                outcome = {"result": "transfer-failed", "reason": code(error)}
            self.log("attempts.log", {**context, "fault": name, "sha256": sha(data), **outcome})

    # Lifecycle --------------------------------------------------------------
    def check_deadline(self):
        if self.status() is not None or not self.expired():
            return
        acks, outbox = self.stored("acks"), self.stored("outbox")
        undelivered = sorted(set(outbox) - set(acks))
        if undelivered:
            reason = "deadline-exceeded:undelivered:" + ",".join(undelivered)
        elif not self.stored("inbox"):
            reason = "deadline-exceeded:no-message-received"
        else:
            reason = "deadline-exceeded:incomplete"
        self.finish("failed", reason)

    def settled(self):
        acks = self.stored("acks")
        return all(mid in acks or mid in self.exhausted for mid in self.stored("outbox"))

    def done(self):
        status = self.status()
        now = utcnow()
        linger = datetime.timedelta(seconds=self.limits["linger_seconds"])
        if now > parse_stamp(self.conversation["deadline"]) + linger:
            return True
        if status is None:
            return False
        decided = datetime.datetime.fromisoformat(status["decided_at"].replace("Z", "+00:00"))
        return self.settled() and now >= decided + linger

    def ending(self):
        acks = {mid: json.loads(raw) for mid, raw in self.stored("acks").items()}
        outbox = {}
        for mid, raw in self.stored("outbox").items():
            counter = self.state / "delivery" / mid
            outbox[mid] = {"turn": json.loads(raw)["turn"], "sha256": sha(raw),
                           "attempts": int(counter.read_text()) if counter.exists() else 0,
                           "ack": acks.get(mid, {}).get("result")}
        inbox = {mid: {"turn": json.loads(raw)["turn"], "sha256": sha(raw)}
                 for mid, raw in self.stored("inbox").items()}
        durable_write(self.state / "ending.json", canonical({
            "local_id": self.local_id, "conversation": self.conversation,
            "status": self.status(), "outbox": outbox, "inbox": inbox,
            "ended_at": precise()}))

    def run(self):
        server = socket.create_server((self.config["listen_address"], self.config["port"]))
        signal.signal(signal.SIGTERM, lambda *_: self.stopping.set())
        self.log("events.log", {"event": "start", "pid": os.getpid(),
                                "invocation": os.environ.get("INVOCATION_ID"),
                                "faults": sorted(self.faults), "limits": self.limits})
        client_context = tls_context(self.credentials, server=False)
        threading.Thread(target=self.listen, args=(server,), daemon=True).start()
        while not self.stopping.is_set():
            self.check_deadline()
            self.work()
            self.send_pending(client_context)
            if self.done():
                break
            self.stopping.wait(0.25)
        if self.status() is None:
            self.finish("failed", "stopped-before-completion")
        self.stopping.set()
        self.ending()
        self.log("events.log", {"event": "exit"})


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--credentials", type=Path,
                        default=os.environ.get("CREDENTIALS_DIRECTORY"))
    parser.add_argument("--state", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.credentials is None:
        parser.error("--credentials or CREDENTIALS_DIRECTORY is required")
    Node(json.loads(args.config.read_text()), args.credentials, args.state).run()


if __name__ == "__main__":
    main()
