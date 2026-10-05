#!/usr/bin/env python3
"""Stage A message syntax and framing; no TLS, durable state or model execution.

Callers retain the original bytes, authenticate the connection, persist budgets,
and own duplicate detection and inbox/outbox transactions. A parsed sender is a
claim until peer_id is supplied from the authenticated certificate mapping.
Binary streams should have a caller-enforced I/O timeout. This module does not
implement a network service or establish that an exchange completed.
"""
import json
import re
import struct
from datetime import datetime, timezone

SCHEMA = "sandhi-exchange.v1"
MAX_ENVELOPE_BYTES = 16 * 1024
MAX_TURN = 7
_ID = re.compile(r"[0-9a-f]{32}\Z")
_INSTALLATION = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
_DEADLINE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_FIELDS = {"schema", "conversation_id", "message_id", "parent_id", "sender",
           "recipient", "turn", "deadline", "kind", "payload"}


class ProtocolError(ValueError):
    """A stable diagnostic code, safe to record without echoing message content."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ProtocolError(code)


def _text(value):
    if not isinstance(value, str):
        return False
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return False
    return True


def _id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _deadline(value):
    _require(isinstance(value, str) and _DEADLINE.fullmatch(value), "invalid-deadline")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ProtocolError("invalid-deadline") from None


def _decode(raw):
    _require(isinstance(raw, bytes), "bytes-required")
    _require(0 < len(raw) <= MAX_ENVELOPE_BYTES, "message-size")

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            _require(key not in obj, "duplicate-key")
            obj[key] = value
        return obj

    def invalid_constant(_):
        raise ProtocolError("nonfinite-json")

    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)
    except ProtocolError:
        raise
    except UnicodeDecodeError:
        raise ProtocolError("invalid-utf8") from None
    except (ValueError, RecursionError):
        raise ProtocolError("invalid-json") from None
    _require(isinstance(value, dict), "object-required")
    return value


def _shape(value):
    _require(isinstance(value, dict), "object-required")
    _require(value.get("schema") == SCHEMA, "unknown-schema")
    _require(value.get("kind") in ("message", "final"), "invalid-kind")
    fields = _FIELDS | ({"status", "reason"} if value["kind"] == "final" else set())
    _require(set(value) == fields, "envelope-fields")
    _require(_id(value["conversation_id"]) and _id(value["message_id"]), "invalid-id")
    _require(type(value["turn"]) is int and 0 <= value["turn"] <= MAX_TURN, "turn-limit")
    _require(value["parent_id"] is None if value["turn"] == 0 else _id(value["parent_id"]),
             "invalid-parent")
    _require(value["parent_id"] != value["message_id"], "self-parent")
    for key in ("sender", "recipient"):
        _require(isinstance(value[key], str) and _INSTALLATION.fullmatch(value[key]),
                 "invalid-installation")
    _require(value["sender"] != value["recipient"], "self-recipient")
    _require(_text(value["payload"]), "invalid-payload")
    expiry = _deadline(value["deadline"])
    if value["kind"] == "final":
        _require(value["status"] in ("complete", "failed"), "invalid-status")
        _require(_text(value["reason"]) and bool(value["reason"].strip()), "invalid-reason")
    return expiry


def decode_envelope(raw, *, local_id=None, peer_id=None, now=None, conversation_id=None):
    """Parse without rewriting bytes; optionally bind identities to trusted context.

    now is an aware datetime for deterministic tests; production defaults to UTC
    wall clock. Parent existence and conversation state require validate_parent
    plus the caller's durable ledger. No authentication is inferred if peer_id is
    omitted. Deadline enforcement here concerns admission, not real-time execution.
    """
    value = _decode(raw)
    expiry = _shape(value)
    if peer_id is not None:
        _require(value["sender"] == peer_id, "sender-mismatch")
    if local_id is not None:
        _require(value["recipient"] == local_id, "recipient-mismatch")
    if conversation_id is not None:
        _require(value["conversation_id"] == conversation_id, "conversation-mismatch")
    current = datetime.now(timezone.utc) if now is None else now
    _require(isinstance(current, datetime) and current.utcoffset() is not None, "invalid-clock")
    _require(expiry > current, "expired")
    return value


def validate_parent(message, parent):
    """Check a parsed message against its locally recorded parent.

    parent=None is valid only for an opening; the caller must also require that
    this conversation has no existing opener. Final-state policy belongs to the
    state machine (including any explicitly designed final confirmation).
    """
    expiry = _shape(message)
    if message["turn"] == 0:
        _require(parent is None, "unexpected-parent")
        return
    _require(parent is not None, "missing-parent")
    parent_expiry = _shape(parent)
    _require(message["parent_id"] == parent["message_id"], "parent-mismatch")
    _require(message["conversation_id"] == parent["conversation_id"], "conversation-mismatch")
    _require(message["sender"] == parent["recipient"]
             and message["recipient"] == parent["sender"], "parent-address-mismatch")
    _require(message["turn"] == parent["turn"] + 1, "parent-turn-mismatch")
    _require(expiry == parent_expiry, "deadline-changed")


def encode_ack(message_id, result, reason=""):
    value = {"ack": message_id, "result": result, "reason": reason}
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise ProtocolError("invalid-ack") from None
    decode_ack(raw, message_id=message_id)
    return raw


def decode_ack(raw, *, message_id):
    value = _decode(raw)
    _require(set(value) == {"ack", "result", "reason"}, "ack-fields")
    _require(_id(message_id) and value["ack"] == message_id, "ack-id-mismatch")
    _require(value["result"] in ("accepted", "duplicate", "rejected"), "ack-result")
    _require(_text(value["reason"]), "ack-reason")
    return value


def _limit(max_bytes):
    _require(type(max_bytes) is int and 0 < max_bytes <= MAX_ENVELOPE_BYTES, "invalid-frame-limit")


def _read_exact(stream, count):
    chunks = []
    remaining = count
    while remaining:
        piece = stream.read(remaining)
        _require(isinstance(piece, bytes) and 0 < len(piece) <= remaining, "truncated-frame")
        chunks.append(piece)
        remaining -= len(piece)
    return b"".join(chunks)


def read_frame(binary_stream, *, max_bytes=MAX_ENVELOPE_BYTES):
    _limit(max_bytes)
    length, = struct.unpack("!I", _read_exact(binary_stream, 4))
    _require(0 < length <= max_bytes, "frame-size")
    return _read_exact(binary_stream, length)


def write_frame(binary_stream, raw, *, max_bytes=MAX_ENVELOPE_BYTES):
    _limit(max_bytes)
    _require(isinstance(raw, bytes), "bytes-required")
    _require(0 < len(raw) <= max_bytes, "frame-size")
    data = struct.pack("!I", len(raw)) + raw
    offset = 0
    while offset < len(data):
        written = binary_stream.write(data[offset:])
        _require(type(written) is int and 0 < written <= len(data) - offset, "incomplete-write")
        offset += written
    binary_stream.flush()
