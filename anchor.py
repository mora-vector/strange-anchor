#!/usr/bin/env python3
"""An append-only, content-addressed archive. Python 3.10+, standard library only."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "strange-anchor.record.v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {"source", "message", "context", "note"}
RELATIONS = {"observed_in", "derived_from", "reply_to", "supersedes", "context", "cites"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value, nullable=False):
    if nullable and value is None:
        return
    require(isinstance(value, str), "timestamp must be an ISO 8601 string")
    require(datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None,
            "timestamp needs a timezone")


def put_once(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), f"refusing symlink: {path}")
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        require(path.read_bytes() == data, f"immutable object differs: {path}")


def message_header(body):
    """A declaration in a message is data, never authenticated model identity."""
    match = re.match(r"\A<!-- anchor-message:v1\r?\n(.*?)\r?\n-->", body, re.S)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


class Archive:
    def __init__(self, root="archive"):
        self.root = Path(root)

    def records(self):
        result = {}
        for path in sorted((self.root / "records").glob("*.json")):
            require(HEX.fullmatch(path.stem), f"invalid record filename: {path.name}")
            raw = path.read_bytes()
            require(digest(raw) == path.stem, f"record hash mismatch: {path.name}")
            result[path.stem] = json.loads(raw)
        return result

    def capture(self, data, *, title, uri, scope, recorder, kind="source",
                media_type="application/octet-stream", revision=None, created_at=None,
                captured_at=None, node=None, provider=None, model=None,
                attribution_basis="unknown", transport_author=None, missing=None,
                completeness="complete-as-received", relations=None, details=None):
        require(isinstance(data, bytes), "capture requires bytes")
        record = {
            "schema": SCHEMA, "kind": kind, "title": title,
            "captured_at": captured_at or now(), "recorded_by": recorder,
            "origin": {"uri": uri, "revision": revision, "created_at": created_at,
                       "transport_author": transport_author},
            "attribution": {"node": node, "provider": provider, "model": model,
                            "basis": attribution_basis},
            "capture": {"scope": scope, "completeness": completeness,
                        "missing": missing or [], "details": details or {}},
            "content": {"sha256": digest(data), "bytes": len(data), "media_type": media_type},
            "relations": relations or [],
        }
        self._shape(record)
        existing = self.records()
        self._links(record, existing)
        if kind == "context":
            self._context(data)
        put_once(self.root / "blobs" / record["content"]["sha256"], data)
        raw = encoded(record)
        record_id = digest(raw)
        put_once(self.root / "records" / (record_id + ".json"), raw)
        return record_id

    @staticmethod
    def _shape(record):
        require(record.get("schema") == SCHEMA, "unsupported record schema")
        require(record.get("kind") in KINDS, "unknown record kind")
        for key in ("title", "recorded_by"):
            require(isinstance(record.get(key), str) and record[key].strip(), f"missing {key}")
        timestamp(record.get("captured_at"))
        origin = record["origin"]
        require(isinstance(origin["uri"], str) and origin["uri"].strip(), "missing source URI")
        timestamp(origin["created_at"], nullable=True)
        for key in ("revision", "transport_author"):
            require(origin[key] is None or isinstance(origin[key], str), f"invalid origin {key}")
        attribution = record["attribution"]
        require(attribution["basis"] in {"unknown", "self-declared", "source-stated"},
                "invalid attribution basis")
        for key in ("node", "provider", "model"):
            require(attribution[key] is None or isinstance(attribution[key], str),
                    f"invalid attribution {key}")
        capture = record["capture"]
        require(isinstance(capture["scope"], str) and capture["scope"], "missing capture scope")
        require(capture["completeness"] in {"complete-as-received", "partial"},
                "invalid completeness")
        require(isinstance(capture["missing"], list) and
                all(isinstance(x, str) for x in capture["missing"]), "invalid missing list")
        require(capture["completeness"] != "partial" or capture["missing"],
                "partial captures must describe what is missing")
        content = record["content"]
        require(isinstance(content["sha256"], str) and HEX.fullmatch(content["sha256"]),
                "invalid blob hash")
        require(type(content["bytes"]) is int and content["bytes"] >= 0, "invalid byte length")
        require(isinstance(content["media_type"], str) and content["media_type"], "missing media type")
        require(isinstance(record["relations"], list), "relations must be a list")

    @staticmethod
    def _links(record, records):
        for relation in record["relations"]:
            require(relation.get("type") in RELATIONS, "unknown relation type")
            target = relation.get("target")
            require(isinstance(target, str), "missing relation target")
            if target.startswith("sha256:"):
                target_id = target[7:]
                require(target_id in records, f"missing referenced record: {target_id}")
                selection = relation.get("bytes")
                if selection is not None:
                    require(isinstance(selection, list) and len(selection) == 2 and
                            all(type(x) is int for x in selection), "invalid byte selection")
                    start, end = selection
                    require(0 <= start < end <= records[target_id]["content"]["bytes"],
                            "byte selection outside source")
            else:
                require(target.startswith(("https://", "http://", "urn:")), "invalid external reference")
                require("bytes" not in relation, "byte selection needs an archived record")
            if record["kind"] == "context":
                require(relation["type"] == "context" and target.startswith("sha256:"),
                        "context inputs must refer to archived records")
                require(isinstance(relation.get("reason"), str) and relation["reason"].strip(),
                        "context inputs need a selection reason")

    def verify(self):
        records = self.records()
        for blob in sorted((self.root / "blobs").glob("*")):
            require(blob.is_file() and not blob.is_symlink() and HEX.fullmatch(blob.name),
                    f"invalid blob object: {blob.name}")
            require(digest(blob.read_bytes()) == blob.name, f"blob hash mismatch: {blob.name}")
        for record_id, record in records.items():
            self._shape(record)
            self._links(record, records)
            path = self.root / "blobs" / record["content"]["sha256"]
            require(path.is_file() and not path.is_symlink(), f"missing blob for {record_id}")
            data = path.read_bytes()
            require(digest(data) == path.name, f"blob hash mismatch: {path.name}")
            require(len(data) == record["content"]["bytes"], f"blob length mismatch: {path.name}")
            if record["kind"] == "context":
                self._context(data)
        return records

    @staticmethod
    def _context(data):
        context = json.loads(data)
        require(context.get("schema") == "strange-anchor.context.v1", "invalid context schema")
        for field in ("purpose", "selection_policy", "context_scope"):
            require(isinstance(context.get(field), str) and context[field].strip(),
                    f"context missing {field}")
        require(isinstance(context.get("unavailable"), list) and
                all(isinstance(x, str) for x in context["unavailable"]),
                "context must declare unavailable inputs")

    def index(self):
        records = self.verify()
        result = {"schema": "strange-anchor.index.v1", "records": {},
                  "by_origin": {}, "by_node": {}, "backlinks": {}}
        for record_id, record in sorted(records.items()):
            result["records"][record_id] = {
                "title": record["title"], "kind": record["kind"],
                "origin": record["origin"], "attribution": record["attribution"],
                "captured_at": record["captured_at"], "content": record["content"],
                "relations": record["relations"],
            }
            result["by_origin"].setdefault(record["origin"]["uri"], []).append(record_id)
            result["by_node"].setdefault(record["attribution"]["node"] or "unknown", []).append(record_id)
            for relation in record["relations"]:
                result["backlinks"].setdefault(relation["target"], []).append({
                    "record": record_id, "type": relation["type"],
                    **({"bytes": relation["bytes"]} if "bytes" in relation else {}),
                })
        return result

    def write_index(self):
        data = encoded(self.index())
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / "index.json"
        temporary = self.root / "index.json.tmp"
        temporary.write_bytes(data)
        temporary.replace(path)

    def context(self, *, title, purpose, policy, inputs, unavailable, context_scope, recorder):
        body = encoded({"schema": "strange-anchor.context.v1", "purpose": purpose,
                        "selection_policy": policy, "unavailable": unavailable,
                        "context_scope": context_scope})
        return self.capture(body, title=title, uri="urn:sha256:" + digest(body),
                            kind="context", scope="declared-input-manifest",
                            media_type="application/json", recorder=recorder,
                            relations=[{"type": "context", **item} for item in inputs])

    def github_event(self, raw, *, uri, observed_at=None, recorder="github-actions"):
        """Preserve runner/connector JSON and exact body strings separately."""
        event = json.loads(raw)
        comment = event["comment"]
        action = event["action"]
        require(action in {"created", "edited", "deleted", "snapshot"}, "unsupported comment action")
        previous = next(((key, value) for key, value in self.records().items()
                         if value["origin"]["uri"] == uri and
                         value["content"]["sha256"] == digest(raw)), None)
        captured_at = previous[1]["captured_at"] if previous else (observed_at or now())
        common = {"recorder": recorder, "captured_at": captured_at}
        event_id = self.capture(raw, title=f"GitHub comment {comment['id']}: {action} payload",
                                uri=uri, revision=digest(raw), media_type="application/json",
                                scope="received-event-json",
                                missing=[] if isinstance(comment.get("body"), str) else
                                ["This received event does not contain a comment body."], **common)
        if not isinstance(comment.get("body"), str):
            return event_id, None
        links = [{"type": "observed_in", "target": "sha256:" + event_id}]

        def body_record(body, revision, scope, relations):
            header = message_header(body)
            node = header.get("sender") if isinstance(header.get("sender"), str) else None
            model = header.get("model") if isinstance(header.get("model"), str) else None
            reply = header.get("reply_to")
            links_for_body = list(relations)
            if isinstance(reply, str) and reply.startswith("https://"):
                links_for_body.append({"type": "reply_to", "target": reply})
            for context_id in header.get("context", []) if isinstance(header.get("context"), list) else []:
                if isinstance(context_id, str) and HEX.fullmatch(context_id):
                    prefix = "sha256:" if context_id in self.records() else "urn:sha256:"
                    links_for_body.append({"type": "context", "target": prefix + context_id})
            return self.capture(body.encode("utf-8"), title=f"GitHub comment {comment['id']}: {scope}",
                                kind="message", uri=comment["html_url"], revision=revision,
                                created_at=comment.get("created_at"), node=node, model=model,
                                attribution_basis="self-declared" if node else "unknown",
                                transport_author=comment.get("user", {}).get("login"),
                                media_type="text/markdown; charset=utf-8", scope=scope,
                                missing=["Uncaptured earlier edits and attachment bytes are unavailable."],
                                details={"event_action": action, "declared_header": header},
                                relations=links_for_body, **common)

        old_body = event.get("changes", {}).get("body", {}).get("from")
        if action == "edited" and isinstance(old_body, str):
            old_id = body_record(old_body, "before:" + str(comment.get("updated_at")),
                                 "previous-body-from-edit-event", links)
            links.append({"type": "supersedes", "target": "sha256:" + old_id})
        message_id = body_record(comment["body"], comment.get("updated_at"),
                                 "comment-body-at-" + action, links)
        return event_id, message_id


def check_append_only(base, root):
    root = Path(root).resolve()
    result = subprocess.run(["git", "diff", "--name-status", "--diff-filter=DMRT", base,
                             "--", str(root / "records"), str(root / "blobs")],
                            check=True, capture_output=True, text=True)
    require(not result.stdout.strip(), "existing archive objects changed or disappeared:\n" + result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="archive")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="capture exact file bytes with explicit provenance")
    capture.add_argument("file", type=Path)
    for field in ("title", "uri", "scope", "recorder"):
        capture.add_argument("--" + field, required=True)
    capture.add_argument("--kind", choices=sorted(KINDS - {"context"}), default="source")
    capture.add_argument("--media-type", default="application/octet-stream")
    capture.add_argument("--revision")
    capture.add_argument("--node")
    capture.add_argument("--provider")
    capture.add_argument("--model")
    capture.add_argument("--attribution-basis", choices=["unknown", "self-declared", "source-stated"], default="unknown")
    capture.add_argument("--completeness", choices=["complete-as-received", "partial"], default="complete-as-received")
    capture.add_argument("--missing", action="append", default=[])
    capture.add_argument("--relation", action="append", default=[], metavar="TYPE:RECORD_HASH")
    context = commands.add_parser("context", help="declare the particular archived inputs selected")
    for field in ("title", "purpose", "policy", "context-scope", "recorder"):
        context.add_argument("--" + field, required=True)
    context.add_argument("--input", action="append", default=[], metavar="HASH[:START:END]")
    context.add_argument("--unavailable", action="append", default=[])
    commands.add_parser("index", help="regenerate the derived cross-index")
    verify = commands.add_parser("verify", help="verify hashes, links, selections, and the derived index")
    verify.add_argument("--base", help="also reject changes/deletions to objects already in this Git ref")
    args = parser.parse_args()
    archive = Archive(args.root)
    if args.command == "capture":
        fields = vars(args).copy()
        for key in ("root", "command", "file", "relation"):
            fields.pop(key)
        relations = []
        for item in args.relation:
            kind, record_id = item.split(":", 1)
            relations.append({"type": kind, "target": "sha256:" + record_id})
        print(archive.capture(args.file.read_bytes(), relations=relations, **fields))
        archive.write_index()
    elif args.command == "context":
        inputs = []
        for item in args.input:
            parts = item.split(":")
            require(len(parts) in {1, 3}, "input must be HASH or HASH:START:END")
            inputs.append({"target": "sha256:" + parts[0], "reason": args.policy,
                           **({"bytes": [int(parts[1]), int(parts[2])]} if len(parts) == 3 else {})})
        print(archive.context(title=args.title, purpose=args.purpose, policy=args.policy,
                              inputs=inputs, unavailable=args.unavailable,
                              context_scope=args.context_scope, recorder=args.recorder))
        archive.write_index()
    elif args.command == "index":
        archive.write_index()
    else:
        require((archive.root / "index.json").read_bytes() == encoded(archive.index()),
                "derived index is stale; run: python3 anchor.py index")
        if args.base:
            check_append_only(args.base, args.root)
        print(f"Verified {len(archive.records())} records, their blobs, links, and index.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(f"archive error: {error}")
