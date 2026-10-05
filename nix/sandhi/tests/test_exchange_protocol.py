"""Portable syntax/framing checks. These are not TLS or Sandhi VM results."""
import io
import json
from pathlib import Path
import struct
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from exchange_protocol import (MAX_ENVELOPE_BYTES, ProtocolError, decode_envelope,
                               encode_envelope, validate_deadline,
                               validate_parent, encode_ack, decode_ack, read_frame, write_frame)

NOW = datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc)


def message(**changes):
    result = dict(schema="sandhi-exchange.v1", conversation_id="a" * 32,
                  message_id="b" * 32, parent_id=None, sender="installation-a",
                  recipient="installation-b", turn=0, deadline="2026-10-05T16:05:00Z",
                  kind="message", payload="A synthetic input: λ\n")
    result.update(changes)
    return result


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class ProtocolTests(unittest.TestCase):
    def refused(self, code, fn, *args, **kwargs):
        with self.assertRaises(ProtocolError) as result:
            fn(*args, **kwargs)
        self.assertEqual(result.exception.code, code)

    def test_exact_bytes_survive_framing_and_parsing_does_not_normalize(self):
        original = json.dumps(message(), ensure_ascii=False, indent=3).encode()
        stream = io.BytesIO()
        write_frame(stream, original)
        stream.seek(0)
        received = read_frame(stream)
        self.assertEqual(received, original)
        self.assertEqual(decode_envelope(received, local_id="installation-b",
                                        peer_id="installation-a", now=NOW), message())

    def test_identity_and_conversation_must_match_trusted_context(self):
        for kwargs, code in [({"local_id": "installation-c"}, "recipient-mismatch"),
                             ({"peer_id": "installation-c"}, "sender-mismatch"),
                             ({"conversation_id": "c" * 32}, "conversation-mismatch")]:
            with self.subTest(code=code):
                self.refused(code, decode_envelope, raw(message()), now=NOW, **kwargs)

    def test_shared_encoder_validates_without_rewriting_received_bytes(self):
        value = message(payload='UTF-8 λ and "quotes"')
        encoded = encode_envelope(value)
        self.assertEqual(decode_envelope(encoded, now=NOW), value)
        self.assertEqual(encoded, encode_envelope(dict(reversed(list(value.items())))))
        self.refused("message-size", encode_envelope, message(payload="λ" * MAX_ENVELOPE_BYTES))
        self.refused("turn-limit", encode_envelope, message(turn=8))
        self.refused("invalid-payload", encode_envelope, message(payload="\ud800"))
        # Authoring or replaying a test fixture must not renew its deadline.
        expired = message(deadline="2000-01-01T00:00:00Z")
        self.refused("expired", decode_envelope, encode_envelope(expired), now=NOW)

    def test_explicit_syntax_only_pass_keeps_identity_checks(self):
        expired = message(deadline="2000-01-01T00:00:00Z")
        parsed = decode_envelope(raw(expired), peer_id="installation-a", check_deadline=False)
        self.assertEqual(parsed, expired)
        self.refused("expired", validate_deadline, parsed, now=NOW)
        self.refused("expired", decode_envelope, raw(expired))
        self.refused("sender-mismatch", decode_envelope, raw(expired),
                     peer_id="installation-c", check_deadline=False)
        self.refused("invalid-deadline-policy", decode_envelope, raw(message()), check_deadline=0)

    def test_rejected_ack_id_requires_an_unambiguous_valid_id(self):
        cases = [(raw(message()), {"peer_id": "installation-c"}, "b" * 32),
                 (raw(message(turn=8)), {}, "b" * 32),
                 (raw(message(message_id="untrusted")), {}, None),
                 (b'{"message_id":"' + b"b" * 32 + b'","message_id":"' + b"c" * 32 + b'"}', {}, None),
                 (b'{"message_id":"' + b"b" * 32 + b'"} trailing', {}, None)]
        for data, kwargs, expected in cases:
            with self.subTest(data=data), self.assertRaises(ProtocolError) as result:
                decode_envelope(data, now=NOW, **kwargs)
            self.assertEqual(result.exception.message_id, expected)

    def test_deadline_boundary_and_invalid_clocks(self):
        self.refused("expired", decode_envelope, raw(message(deadline="2026-10-05T16:00:00Z")), now=NOW)
        self.refused("expired", decode_envelope, raw(message(deadline="2026-10-05T15:59:59Z")), now=NOW)
        self.refused("invalid-clock", decode_envelope, raw(message()), now=datetime(2026, 10, 5))
        for deadline in ["2026-10-05", "2026-10-05T16:05:00+01:00", "2026-02-30T00:00:00Z", 0]:
            with self.subTest(deadline=deadline):
                self.refused("invalid-deadline", decode_envelope, raw(message(deadline=deadline)), now=NOW)

    def test_turn_types_and_limit_are_strict(self):
        for turn in [True, False, 1.0, "1", -1, 8]:
            with self.subTest(turn=turn):
                self.refused("turn-limit", decode_envelope, raw(message(turn=turn)), now=NOW)
        self.assertEqual(decode_envelope(raw(message(turn=7, parent_id="c" * 32)), now=NOW)["turn"], 7)

    def test_parent_structure_and_cross_conversation_reply(self):
        opening = message()
        reply = message(message_id="c" * 32, parent_id="b" * 32, turn=1,
                        sender="installation-b", recipient="installation-a")
        validate_parent(opening, None)
        validate_parent(reply, opening)
        for changes, code in [({"conversation_id": "d" * 32}, "conversation-mismatch"),
                              ({"parent_id": "d" * 32}, "parent-mismatch"),
                              ({"turn": 2}, "parent-turn-mismatch"),
                              ({"sender": "installation-c"}, "parent-address-mismatch"),
                              ({"deadline": "2026-10-05T16:05:01Z"}, "deadline-changed"),
                              ({"deadline": "2026-10-05T16:04:59Z"}, "deadline-changed")]:
            with self.subTest(changes=changes):
                self.refused(code, validate_parent, reply | changes, opening)
        self.refused("missing-parent", validate_parent, reply, None)
        self.refused("unexpected-parent", validate_parent, opening, reply)
        self.refused("invalid-parent", decode_envelope, raw(message(parent_id="c" * 32)), now=NOW)
        self.refused("self-parent", decode_envelope, raw(message(turn=1, parent_id="b" * 32)), now=NOW)

    def test_final_requires_explicit_status_reason(self):
        for status in ["complete", "failed"]:
            value = message(kind="final", status=status, reason="synthetic outcome")
            self.assertEqual(decode_envelope(raw(value), now=NOW), value)
        self.refused("envelope-fields", decode_envelope, raw(message(kind="final")), now=NOW)
        self.refused("invalid-status", decode_envelope,
                     raw(message(kind="final", status="running", reason="x")), now=NOW)
        self.refused("invalid-reason", decode_envelope,
                     raw(message(kind="final", status="failed", reason=" ")), now=NOW)
        self.refused("envelope-fields", decode_envelope, raw(message(status="complete")), now=NOW)

    def test_strict_json_and_unicode(self):
        for value, code in [(b'{"schema":"a","schema":"b"}', "duplicate-key"),
                            (b'{"x":NaN}', "nonfinite-json"),
                            (b'{"x":Infinity}', "nonfinite-json"),
                            (b"\xff", "invalid-utf8"),
                            (b"{} trailing", "invalid-json"),
                            (b"[]", "object-required")]:
            with self.subTest(code=code):
                self.refused(code, decode_envelope, value, now=NOW)
        # The parser's recursion limit varies by Python runtime; either parsing
        # rejection or the root-object check must refuse this input safely.
        with self.assertRaises(ProtocolError):
            decode_envelope(b"[" * 2000 + b"]" * 2000, now=NOW)
        escaped = json.dumps(message(payload="\ud800")).encode()
        self.refused("invalid-payload", decode_envelope, escaped, now=NOW)

    def test_unknown_fields_schema_and_malformed_ids(self):
        self.refused("unknown-schema", decode_envelope, raw(message(schema="sandhi-exchange.v2")), now=NOW)
        self.refused("envelope-fields", decode_envelope, raw(message(extra="ignored?")), now=NOW)
        for ident in [None, "x" * 32, "A" * 32, "b" * 31, 12]:
            self.refused("invalid-id", decode_envelope, raw(message(message_id=ident)), now=NOW)
        self.refused("self-recipient", decode_envelope, raw(message(recipient="installation-a")), now=NOW)

    def test_ack_binds_exact_message_id_and_result(self):
        for result in ["accepted", "duplicate", "rejected"]:
            encoded = encode_ack("b" * 32, result, "synthetic")
            self.assertEqual(decode_ack(encoded, message_id="b" * 32)["result"], result)
            self.refused("ack-id-mismatch", decode_ack, encoded, message_id="c" * 32)
        self.refused("ack-result", encode_ack, "b" * 32, "success")
        self.refused("ack-reason", encode_ack, "b" * 32, "rejected", None)
        self.refused("ack-fields", decode_ack, b'{"ack":"x"}', message_id="b" * 32)

    def test_oversized_frame_rejected_before_body_read(self):
        class HeaderOnly:
            def __init__(self, size): self.size, self.calls = size, 0
            def read(self, count):
                self.calls += 1
                if self.calls > 1: raise AssertionError("body read after oversized header")
                return struct.pack("!I", self.size)
        for size in [0, MAX_ENVELOPE_BYTES + 1, 2**32 - 1]:
            self.refused("frame-size", read_frame, HeaderOnly(size))
        self.refused("message-size", decode_envelope, b" " * (MAX_ENVELOPE_BYTES + 1), now=NOW)

    def test_fragmented_and_consecutive_frames(self):
        class Fragmented(io.BytesIO):
            def read(self, n): return super().read(min(n, 1))
            def write(self, data): return super().write(data[:2])
        stream = Fragmented()
        for data in [b"first", b"second", b"x" * MAX_ENVELOPE_BYTES]: write_frame(stream, data)
        stream.seek(0)
        for data in [b"first", b"second", b"x" * MAX_ENVELOPE_BYTES]:
            self.assertEqual(read_frame(stream), data)
        self.refused("truncated-frame", read_frame, stream)

    def test_truncated_frames_and_invalid_limits_fail(self):
        for data in [b"", b"\x00\x00", struct.pack("!I", 4) + b"abc"]:
            self.refused("truncated-frame", read_frame, io.BytesIO(data))
        for limit in [0, True, MAX_ENVELOPE_BYTES + 1]:
            self.refused("invalid-frame-limit", read_frame, io.BytesIO(), max_bytes=limit)
        self.refused("frame-size", write_frame, io.BytesIO(), b"")
        self.refused("frame-size", write_frame, io.BytesIO(), b"xx", max_bytes=1)
        class NoProgress(io.BytesIO):
            def write(self, data): return 0
        self.refused("incomplete-write", write_frame, NoProgress(), b"x")


if __name__ == "__main__":
    unittest.main()
