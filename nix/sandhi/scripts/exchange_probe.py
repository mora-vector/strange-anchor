#!/usr/bin/env python3
"""Stage A fault-injection client, run by the test driver as root. Never a participant.

It never carries a participant's message. It probes the address filter (assertion 6),
authentication and sender binding from a permitted address (assertions 7 and 8),
the turn and size limits, and a connection held across peer withdrawal
(assertion 9). Each run prints one JSON observation and exits 0.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import socket
import ssl
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exchange_node  # noqa: E402
import exchange_protocol as protocol  # noqa: E402


def observe(**fields):
    print(json.dumps(fields, sort_keys=True))


def connect(args):
    started = time.monotonic()
    try:
        socket.create_connection((args.host, args.port), timeout=args.timeout).close()
        outcome, detail = "connected", ""
    except (socket.timeout, TimeoutError) as error:
        outcome, detail = "timeout", str(error)
    except ConnectionRefusedError as error:
        outcome, detail = "refused", str(error)
    except OSError as error:
        outcome, detail = "error", f"{type(error).__name__}: {error}"
    observe(probe="connect", host=args.host, port=args.port, outcome=outcome, detail=detail,
            seconds=round(time.monotonic() - started, 3))


def envelope(args):
    fields = json.loads(args.envelope)
    fields.setdefault("schema", exchange_node.SCHEMA)
    fields.setdefault("message_id", secrets.token_hex(16))
    fields.setdefault("deadline", exchange_node.stamp(
        exchange_node.utcnow() + exchange_node.datetime.timedelta(seconds=300)))
    # Deliberately not the shared encoder: probes may author envelopes it refuses.
    return exchange_node.canonical(fields)


def tls(args):
    record = {"probe": "tls", "host": args.host, "port": args.port, "label": args.label}
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(args.cert, args.key)
    context.load_verify_locations(cafile=str(args.trust))
    record["client_fingerprint"] = hashlib.sha256(
        ssl.PEM_cert_to_DER_cert(Path(args.cert).read_text())).hexdigest()
    try:
        connection = socket.create_connection((args.host, args.port), timeout=args.timeout)
    except OSError as error:
        return observe(**record, outcome="connect-failed", detail=f"{type(error).__name__}: {error}")
    try:
        channel = context.wrap_socket(connection)
    except (ssl.SSLError, OSError) as error:
        connection.close()
        return observe(**record, outcome="tls-failed", detail=f"{type(error).__name__}: {error}")
    with channel:
        record["server_fingerprint"] = exchange_node.fingerprint(channel)
        stream = channel.makefile("rwb")
        if args.hold_until:
            # Hold the authenticated connection open until the driver releases it.
            release = Path(args.hold_until)
            deadline = time.monotonic() + args.hold_timeout
            while not release.exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            record["held_seconds"] = round(args.hold_timeout - (deadline - time.monotonic()), 3)
            record["released"] = release.exists()
        if args.oversize:
            # Bypass the shared writer deliberately: the receiver must refuse this length.
            data = struct.pack(">I", args.oversize) + b"x" * args.oversize
            record["sent_bytes"] = len(data)
        elif args.envelope:
            raw = envelope(args)
            record["message_id"] = json.loads(raw)["message_id"]
            record["sha256"] = hashlib.sha256(raw).hexdigest()
            data = None
        else:
            return observe(**record, outcome="handshake-only")
        try:
            if data is None:
                protocol.write_frame(stream, raw, max_bytes=16384)
            else:
                stream.write(data)
            stream.flush()
            ack = protocol.read_frame(stream, max_bytes=16384)
        except (OSError, ssl.SSLError, protocol.ProtocolError) as error:
            return observe(**record, outcome="no-ack", detail=f"{type(error).__name__}: "
                                                              f"{exchange_node.code(error)}")
        if not ack:
            return observe(**record, outcome="closed-without-ack")
        return observe(**record, outcome="acked", ack=json.loads(ack))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("connect", "tls"):
        command = commands.add_parser(name)
        command.add_argument("--host", required=True)
        command.add_argument("--port", type=int, default=7443)
        command.add_argument("--timeout", type=float, default=5)
    tls_command = commands.choices["tls"]
    tls_command.add_argument("--label", default="")
    for name in ("cert", "key", "trust"):
        tls_command.add_argument("--" + name, type=Path, required=True)
    tls_command.add_argument("--envelope", help="JSON fields; schema, ID and deadline default")
    tls_command.add_argument("--oversize", type=int)
    tls_command.add_argument("--hold-until")
    tls_command.add_argument("--hold-timeout", type=float, default=300)
    args = parser.parse_args()
    (connect if args.command == "connect" else tls)(args)


if __name__ == "__main__":
    main()
