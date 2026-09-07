#!/usr/bin/env python3
"""Archive a GitHub issue_comment payload using trusted default-branch code."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anchor import Archive, now, put_once  # noqa: E402

BRANCH = "anchor-archive"


def git(repository, *args, check=True):
    return subprocess.run(["git", "-C", str(repository), *args], check=check,
                          capture_output=True, text=True)


def publish(repository, raw, uri, observed_at=None):
    repository = Path(repository).resolve()
    observed_at = observed_at or now()
    for attempt in range(8):
        remote = git(repository, "ls-remote", "--heads", "origin", "refs/heads/" + BRANCH).stdout.strip()
        if remote:
            git(repository, "fetch", "--no-tags", "origin", "refs/heads/" + BRANCH)
            base = git(repository, "rev-parse", "FETCH_HEAD").stdout.strip()
        else:
            base = git(repository, "rev-parse", "HEAD").stdout.strip()
        with tempfile.TemporaryDirectory(prefix="anchor-event-") as directory:
            checkout = Path(directory) / "checkout"
            git(repository, "worktree", "add", "--detach", str(checkout), base)
            try:
                # New approved source records can join the archive as main advances.
                for folder in ("records", "blobs"):
                    for source in sorted((repository / "archive" / folder).glob("*")):
                        if source.is_file():
                            put_once(checkout / "archive" / folder / source.name, source.read_bytes())
                archive = Archive(checkout / "archive")
                record_ids = archive.github_event(raw, uri=uri, observed_at=observed_at)
                archive.write_index()
                git(checkout, "add", "--", "archive")
                if not git(checkout, "diff", "--cached", "--name-only").stdout.strip():
                    return record_ids
                git(checkout, "-c", "user.name=Strange Anchor archive",
                    "-c", "user.email=strange-anchor-archive@users.noreply.github.com",
                    "commit", "-m", "Preserve received comment event " + record_ids[0][:12])
                pushed = git(checkout, "push", "origin", "HEAD:refs/heads/" + BRANCH, check=False)
                if pushed.returncode == 0:
                    return record_ids
                # A competing fast-forward is retried against its complete archive.
                # Permission/network failures also fail visibly after bounded retries.
            finally:
                git(repository, "worktree", "remove", "--force", str(checkout))
    raise RuntimeError("Archive push failed after 8 attempts; event was not confirmed preserved.")


if __name__ == "__main__":
    if os.environ.get("GITHUB_EVENT_NAME") != "issue_comment":
        sys.exit("Only issue_comment payloads are supported.")
    raw_event = Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes()
    run_url = (os.environ["GITHUB_SERVER_URL"] + "/" + os.environ["GITHUB_REPOSITORY"]
               + "/actions/runs/" + os.environ["GITHUB_RUN_ID"])
    print("Preserved records:", *publish(Path.cwd(), raw_event, run_url + "#issue_comment"))
