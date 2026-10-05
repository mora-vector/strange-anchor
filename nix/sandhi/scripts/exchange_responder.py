#!/usr/bin/env python3
"""Deterministic Stage A responder for the split-input task. Not a model.

Each installation holds one private 128-bit value. The task is complete when both
sides hold sha256(x of installation-a || x of installation-b), concatenated in
installation-ID order. That requires a value initially held only by the peer.

Reads one request (JSON) on stdin from exchange_node.py and writes
{"reply": {...} | null, "terminal": {...} | null} to stdout.
"""
import hashlib
import json
import sys


def payload(envelope):
    value = json.loads(envelope["payload"])
    if not isinstance(value, dict):
        raise ValueError("payload is not an object")
    return value


def hex128(value):
    if not (isinstance(value, str) and len(value) == 32 and bytes.fromhex(value)):
        raise ValueError("expected 32 hex characters")
    return value


def respond(request):
    own = hex128(request["private_input"])
    incoming = request["incoming"]
    received = [entry["envelope"] for entry in request["history"] if entry["direction"] == "in"]
    received += [incoming] if incoming else []
    peer = next((payload(e)["x"] for e in received if "x" in payload(e)), None)

    def digest():
        ordered = sorted([(request["local_id"], own), (request["peer_id"], hex128(peer))])
        return hashlib.sha256(b"".join(bytes.fromhex(x) for _, x in ordered)).hexdigest()

    if incoming is None:
        return {"reply": {"kind": "message", "payload": json.dumps({"x": own})}, "terminal": None}
    body = payload(incoming)
    if incoming["kind"] == "message" and "digest" not in body:
        reply = json.dumps({"x": own, "digest": digest()}, sort_keys=True)
        return {"reply": {"kind": "message", "payload": reply}, "terminal": None}
    if incoming["kind"] == "message":
        expected = digest()
        if body["digest"] == expected:
            final = {"kind": "final", "status": "complete", "reason": "digests-agree",
                     "payload": json.dumps({"digest": expected})}
            return {"reply": final, "terminal": {"status": "complete", "reason": "",
                                                 "digest": expected}}
        final = {"kind": "final", "status": "failed", "reason": "digest-mismatch",
                 "payload": json.dumps({"digest": expected})}
        return {"reply": final, "terminal": {"status": "failed", "reason": "digest-mismatch"}}
    expected = digest()
    if incoming.get("status") == "complete" and body.get("digest") == expected:
        return {"reply": None, "terminal": {"status": "complete", "reason": "", "digest": expected}}
    return {"reply": None, "terminal": {
        "status": "failed",
        "reason": f"peer-final:{incoming.get('status')}:{incoming.get('reason', '')}"
                  if incoming.get("status") != "complete" else "digest-mismatch"}}


def main():
    try:
        output = respond(json.loads(sys.stdin.buffer.read()))
    except (KeyError, TypeError, ValueError, StopIteration) as error:
        output = {"reply": None, "terminal": {"status": "failed",
                                              "reason": f"responder-input:{type(error).__name__}"}}
    sys.stdout.write(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
