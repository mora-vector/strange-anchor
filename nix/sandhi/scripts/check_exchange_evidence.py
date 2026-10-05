#!/usr/bin/env python3
"""Offline consistency checks for saved Stage A evidence, not a VM rerun.

Checks source selection, the report hash, all 15 endpoint archives, exact message
bytes, acknowledgments, recomputed split-input results and journal restarts.
Does not independently attest the builder, TLS identity, network isolation,
absence of relaying, or model identity. Host-produced evidence remains a claim.
Archive members are read in memory, never extracted or executed.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

import exchange_protocol as protocol

SUCCESS = ("t1-baseline", "t2-duplicate", "t3-conflict", "t4-I1", "t5-I2", "t6-I3")
TRIALS = SUCCESS + ("t7-withdrawal", "t8-channel-cut")
LIMIT = 4 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    def nonfinite(_):
        raise EvidenceError("nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def read_state(path):
    require(path.stat().st_size <= LIMIT, f"archive too large: {path.name}")
    files, total = {}, 0
    with tarfile.open(path, mode="r:") as archive:
        for index, member in enumerate(archive):
            require(index < 1024, "too many archive members")
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and ".." not in name.parts, "unsafe archive member")
            if member.isdir():
                continue
            require(member.isfile(), "non-regular archive member")
            require(str(name) not in files, "duplicate archive member")
            total += member.size
            require(0 <= member.size <= LIMIT and total <= LIMIT, "archive content too large")
            stream = archive.extractfile(member)
            require(stream is not None, "unreadable archive member")
            files[str(name)] = stream.read()
    return files


def folder(files, name):
    return {key.split("/", 1)[1]: raw for key, raw in files.items()
            if key.startswith(name + "/") and not key.endswith(".tmp")}


def lines(files, name):
    return [decode(line) for line in files.get(name, b"").splitlines() if line]


def moment(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_endpoint(files, report, local, label):
    status, ending = decode(files["status.json"]), decode(files["ending.json"])
    conversation = decode(files["conversation.json"])
    require(status == report["status"] == ending["status"], f"{label}/{local}: status mismatch")
    require(ending == report["ending"], f"{label}/{local}: ending mismatch")
    require(conversation == ending["conversation"], f"{label}/{local}: conversation mismatch")
    require(conversation["trial"] == label, "wrong trial in archive")
    require(status["status"] in ("complete", "failed"), "missing terminal outcome")
    require(status["local_id"] == ending["local_id"] == "installation-" + local, "wrong installation")
    require(lines(files, "attempts.log") == report["attempts"], "attempt log mismatch")
    events = lines(files, "events.log")
    require(events == report["events"], "event log mismatch")
    starts = [e for e in events if e["event"] == "start"]
    require(len(starts) == report["processStarts"], "process count mismatch")
    invocations = [e for e in lines(files, "invocations.log") if e["event"] == "invoke"]
    require(invocations == report["invocations"], "invocation log mismatch")
    require(sorted(folder(files, "faults-fired")) == report["faultsFired"], "fault marker mismatch")
    for name in ("inbox", "outbox"):
        messages = folder(files, name)
        require(set(messages) == set(ending[name]), "ending message inventory mismatch")
        for mid, raw in messages.items():
            message = protocol.decode_envelope(raw, check_deadline=False)
            require(message["message_id"] == mid, "message filename mismatch")
            require(message["conversation_id"] == conversation["conversation_id"], "message conversation mismatch")
            require(ending[name][mid]["sha256"] == digest(raw), "ending message hash mismatch")
            require(ending[name][mid]["turn"] == message["turn"], "ending message turn mismatch")
    return starts


def check_pair(states, report):
    """Recompute successful task outcomes without trusting summary pass flags."""
    values, combined, count = {}, {}, 0
    for sender, receiver in (("a", "b"), ("b", "a")):
        outbox = folder(states[sender], "outbox")
        require(bool(outbox), "empty successful outbox")
        require(outbox == folder(states[receiver], "inbox"), "outbox/inbox byte mismatch")
        acks = folder(states[sender], "acks")
        require(set(acks) == set(outbox), "unacknowledged successful message")
        for mid, raw in outbox.items():
            message = protocol.decode_envelope(raw, peer_id="installation-" + sender,
                                               local_id="installation-" + receiver, check_deadline=False)
            require(mid == message["message_id"] and mid not in combined, "message ID collision")
            combined[mid] = message
            ack = protocol.decode_ack(acks[mid], message_id=mid)
            require(ack["result"] in ("accepted", "duplicate"), "rejected successful message")
            attempts = int(states[sender]["delivery/" + mid])
            require(1 <= attempts <= 30, "delivery budget exceeded")
            body = decode(message["payload"])
            if "x" in body:
                require(re.fullmatch(r"[0-9a-f]{32}", body["x"]) is not None, "invalid split input")
                require(sender not in values or values[sender] == body["x"], "split input changed")
                values[sender] = body["x"]
            count += 1
    require(set(values) == {"a", "b"}, "missing split input")
    expected = digest(bytes.fromhex(values["a"]) + bytes.fromhex(values["b"]))
    require(expected == report["expectedDigest"], "driver digest mismatch")
    require(sum(m["turn"] == 0 for m in combined.values()) == 1, "missing or multiple openings")
    finals = []
    for message in combined.values():
        protocol.validate_parent(message, combined.get(message["parent_id"]))
        if message["kind"] == "final":
            finals.append(message)
            require(message["status"] == "complete" and decode(message["payload"])["digest"] == expected,
                    "final digest mismatch")
    require(bool(finals), "missing final message")
    for local in ("a", "b"):
        status = decode(states[local]["status.json"])
        require(status["status"] == "complete" and status.get("digest") == expected,
                "endpoint digest mismatch")
    return count


def verify(directory, expected_source):
    directory = Path(directory)
    require(re.fullmatch(r"[0-9a-f]{40}", expected_source) is not None, "expected source must be full commit SHA")
    summary = decode((directory / "SUMMARY.json").read_bytes())
    require(summary["source"]["commit"] == expected_source, "source commit mismatch")
    raw_report = (directory / "stage-a.json").read_bytes()
    require(digest(raw_report) == summary["output"]["stageASha256"], "report hash mismatch")
    report = decode(raw_report)
    require(report["errors"] == [], "driver reported errors")
    require(set(report["trials"]) == set(TRIALS), "missing or unexpected trials")
    count, endpoints, restarts = 0, 0, {}
    reviewed = {"SUMMARY.json", "stage-a.json", "a-journal.txt", "b-journal.txt"}
    for label in TRIALS:
        trial = report["trials"][label]
        states, starts = {}, {}
        for local in (("b",) if label == "t7-withdrawal" else ("a", "b")):
            archive_path = f"trials/{label}/{local}-state.tar"
            reviewed.add(archive_path)
            states[local] = read_state(directory / archive_path)
            starts[local] = check_endpoint(states[local], trial[local], local, label)
            endpoints += 1
        if label in SUCCESS:
            count += check_pair(states, trial)
        if label == "t8-channel-cut":
            for files in states.values():
                status = decode(files["status.json"])
                require(status["status"] == "failed" and bool(status.get("reason")), "channel cut lacks explicit failure")
                require("digest" not in status and not folder(files, "inbox"), "channel cut received data or result")
        if label in ("t4-I1", "t5-I2", "t6-I3"):
            local = "a" if label == "t6-I3" else "b"
            events = starts[local]
            require(len(events) == 2 and events[0]["invocation"] != events[1]["invocation"], "restart absent")
            journal = (directory / f"{local}-journal.txt").read_text().splitlines()
            observed = sum("Scheduled restart job" in line and
                           moment(events[0]["at"]) < moment(line.split()[0]) <= moment(events[1]["at"])
                           for line in journal)
            require(observed == 1, "journal restart absent or ambiguous")
            if "systemdRestarts" in trial[local]:
                require(trial[local]["systemdRestarts"] == observed, "reported restart mismatch")
            restarts[label] = observed
    return {"ok": True, "source": expected_source, "endpointsChecked": endpoints,
            "successfulMessagesChecked": count, "journalRestarts": restarts,
            "reviewedFileSha256": {p: digest((directory / p).read_bytes()) for p in sorted(reviewed)},
            "scope": "offline artifact consistency; not an independent VM run or attestation of all eleven assertions"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-source", required=True)
    args = parser.parse_args()
    try:
        result = verify(args.directory, args.expected_source)
    except (EvidenceError, protocol.ProtocolError, OSError, ValueError, KeyError,
            TypeError, RecursionError, tarfile.TarError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
