import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from anchor import Archive, encoded, message_header
from scripts.archive_event import publish

OBSERVED = "2026-09-07T00:00:00Z"


def event(number=1, body="A message", action="created", old_body=None):
    value = {"action": action, "comment": {
        "id": number, "html_url": f"https://github.com/test/archive/pull/1#issuecomment-{number}",
        "body": body, "created_at": "2026-09-06T12:00:00Z",
        "updated_at": "2026-09-06T12:01:00Z", "user": {"login": "transport-account"},
    }, "issue": {"number": 1, "body": "Thread opening"}}
    if old_body is not None:
        value["changes"] = {"body": {"from": old_body}}
    return encoded(value)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")

    def capture(self, data=b"original\r\n\x00\xff", **kwargs):
        options = dict(title="Source", uri="urn:test:source", scope="file-bytes",
                       recorder="test", captured_at=OBSERVED)
        options.update(kwargs)
        return self.archive.capture(data, **options)

    def test_exact_binary_and_idempotent_capture(self):
        record_id = self.capture()
        self.assertEqual(record_id, self.capture())
        record = self.archive.verify()[record_id]
        self.assertEqual((self.archive.root / "blobs" / record["content"]["sha256"]).read_bytes(),
                         b"original\r\n\x00\xff")
        self.assertEqual(len(self.archive.records()), 1)

    def test_modified_blob_is_detected(self):
        record_id = self.capture()
        record = self.archive.records()[record_id]
        (self.archive.root / "blobs" / record["content"]["sha256"]).write_bytes(b"rewritten")
        with self.assertRaisesRegex(ValueError, "blob hash mismatch"):
            self.archive.verify()

    def test_modified_envelope_is_detected(self):
        record_id = self.capture()
        path = self.archive.root / "records" / (record_id + ".json")
        path.write_bytes(path.read_bytes().replace(b"Source", b"Framed"))
        with self.assertRaisesRegex(ValueError, "record hash mismatch"):
            self.archive.verify()

    def test_dangling_reference_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, "missing referenced record"):
            self.capture(relations=[{"type": "reply_to", "target": "sha256:" + "a" * 64}])
        self.assertFalse((self.archive.root / "records").exists())

    def test_partial_capture_needs_explicit_gap(self):
        with self.assertRaisesRegex(ValueError, "describe what is missing"):
            self.capture(completeness="partial")

    def test_context_range_and_backlink(self):
        record_id = self.capture(b"prefix: fox\nsuffix")
        context_id = self.archive.context(
            title="Selected input", purpose="Read the word fox", policy="Exact excerpt",
            context_scope="Declared external inputs only", unavailable=["Earlier chat is unavailable"],
            recorder="test", inputs=[{"target": "sha256:" + record_id,
                                      "bytes": [8, 11], "reason": "Read only this word"}])
        index = self.archive.index()
        self.assertEqual(index["backlinks"]["sha256:" + record_id],
                         [{"record": context_id, "type": "context", "bytes": [8, 11]}])
        with self.assertRaisesRegex(ValueError, "outside source"):
            self.archive.context(title="Bad input", purpose="Test", policy="Test",
                                 context_scope="Declared", unavailable=[], recorder="test",
                                 inputs=[{"target": "sha256:" + record_id, "bytes": [0, 99], "reason": "Test"}])

    def test_invalid_context_does_not_pollute_archive(self):
        with self.assertRaisesRegex(ValueError, "missing purpose"):
            self.archive.context(title="Bad", purpose="", policy="Test", inputs=[],
                                 unavailable=[], context_scope="Declared", recorder="test")
        self.assertFalse((self.archive.root / "records").exists())

    def test_event_replay_and_edits_preserve_both_bodies(self):
        raw = event(body="corrected", action="edited", old_body="original")
        ids = self.archive.github_event(raw, uri="urn:test:event", observed_at=OBSERVED)
        self.assertEqual(ids, self.archive.github_event(raw, uri="urn:test:event"))
        records = self.archive.verify()
        self.assertEqual(len(records), 3)
        message = records[ids[1]]
        predecessor = next(x["target"][7:] for x in message["relations"] if x["type"] == "supersedes")
        old = records[predecessor]
        self.assertEqual((self.archive.root / "blobs" / old["content"]["sha256"]).read_bytes(), b"original")

    def test_deleted_event_preserves_body_and_action(self):
        ids = self.archive.github_event(event(body="removed", action="deleted"),
                                        uri="urn:test:deleted", observed_at=OBSERVED)
        self.assertEqual(self.archive.verify()[ids[1]]["capture"]["details"]["event_action"], "deleted")

    def test_unavailable_body_is_a_recorded_gap(self):
        event_id, message_id = self.archive.github_event(event(body=None), uri="urn:test:missing")
        self.assertIsNone(message_id)
        self.assertTrue(self.archive.verify()[event_id]["capture"]["missing"])

    def test_transport_and_claimed_identity_remain_distinct(self):
        body = '<!-- anchor-message:v1\n{"sender":"sideband","model":null}\n-->\nHello ♃🦊\r\n'
        ids = self.archive.github_event(event(body=body), uri="urn:test:identity", observed_at=OBSERVED)
        record = self.archive.verify()[ids[1]]
        self.assertEqual(record["attribution"]["node"], "sideband")
        self.assertEqual(record["attribution"]["basis"], "self-declared")
        self.assertEqual(record["origin"]["transport_author"], "transport-account")
        self.assertEqual((self.archive.root / "blobs" / record["content"]["sha256"]).read_bytes(), body.encode())

    def test_malformed_header_is_preserved_as_data(self):
        body = '<!-- anchor-message:v1\nnot json\n-->\n$(touch NEVER_EXECUTE)'
        self.assertEqual(message_header(body), {})
        _, record_id = self.archive.github_event(event(body=body), uri="urn:test:malformed")
        self.assertIsNone(self.archive.verify()[record_id]["attribution"]["node"])

    def test_index_can_be_rebuilt_identically(self):
        self.capture()
        self.archive.write_index()
        first = (self.archive.root / "index.json").read_bytes()
        (self.archive.root / "index.json").unlink()
        self.archive.write_index()
        self.assertEqual(first, (self.archive.root / "index.json").read_bytes())


class GitPublisherTests(unittest.TestCase):
    def test_competing_writers_and_replay_keep_every_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            def git(path, *args):
                return subprocess.run(["git", "-C", str(path), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)],
                           check=True, capture_output=True)
            first, second = root / "first", root / "second"
            subprocess.run(["git", "clone", str(remote), str(first)], check=True, capture_output=True)
            (first / "README.md").write_text("Test repository\n")
            git(first, "add", "README.md")
            git(first, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "Initialize test")
            git(first, "push", "origin", "main")
            subprocess.run(["git", "clone", str(remote), str(second)], check=True, capture_output=True)
            raw1, raw2 = event(1), event(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(publish, first, raw1, "urn:test:event1", OBSERVED),
                           pool.submit(publish, second, raw2, "urn:test:event2", OBSERVED)]
                for future in futures:
                    future.result()
            publish(first, raw1, "urn:test:event1", OBSERVED)
            git(first, "fetch", "origin", "anchor-archive")
            git(first, "checkout", "--detach", "FETCH_HEAD")
            self.assertEqual(len(Archive(first / "archive").verify()), 4)
            self.assertEqual(git(first, "rev-list", "--count", "HEAD"), "3")

    def test_deleting_an_old_object_fails_append_only_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            archive = Archive(root / "archive")
            record_id = archive.capture(b"preserve", title="Original", uri="urn:test:original",
                                        scope="file", recorder="test")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-m", "Original"],
                           check=True, capture_output=True)
            (archive.root / "records" / (record_id + ".json")).unlink()
            # The check takes a Git ref in the caller's repository.
            result = subprocess.run([sys.executable, str(Path(__file__).parents[1] / "anchor.py"),
                                     "--root", str(archive.root), "index"], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable, str(Path(__file__).parents[1] / "anchor.py"),
                                     "--root", str(archive.root), "verify", "--base", "HEAD"],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("disappeared", result.stderr)


if __name__ == "__main__":
    unittest.main()
