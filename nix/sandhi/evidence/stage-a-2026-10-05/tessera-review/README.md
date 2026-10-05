# Tessera's offline reading of Stage A evidence

The JSON records here are new derived records. Sideband's original attempt
artifacts remain unchanged. Each review pins the experiment source, hashes the
checker, and hashes the 19 input files it checked. The declared producing model
is `null`; the node label is not model authentication.

Both attempts 3 and 4 passed these offline consistency checks: 15 endpoint state
archives, 18 successful sent/received message pairs, recomputed split-input
digests, acknowledgments, parent chains, endpoint outcomes, and journal restarts.
Attempt 3 describes superseded source `a5dbe45`; attempt 4 describes `a990b99`,
which includes the recovery/deadline fixes and the expired-outbox settling fix.

From the repository root:

```sh
python3 nix/sandhi/scripts/check_exchange_evidence.py \
  nix/sandhi/evidence/stage-a-2026-10-05/attempt-4 \
  --expected-source a990b9983166598ed6fd3e3c92414c231667173b

python3 -m unittest discover -s nix/sandhi/tests \
  -p 'test_exchange_evidence.py' -v
```

The six synthetic corruption tests exercise byte changes, missing messages or
acknowledgments, fabricated matching result strings, broken parent chains,
rejected delivery, exceeded attempt budgets, source/report mismatch, missing
trials despite a passing summary flag, and unsafe archive members. The full
Sandhi Python suite passed 65 tests in the reviewing container, including the
real TLS/process tests. No NixOS VM was run by this reviewer.

## What this establishes

The saved endpoint records agree with each other and with the selected driver's
report. Digest checking computes from the two values retained in messages; it
does not accept a pair of identical result strings as sufficient. All successful
outbox messages must have matching peer inbox bytes and accepted/duplicate
acknowledgments. Restart checking reads the journal timestamps between the node's
two process-start events. Archives are read in memory, never extracted or run.

The checker does not use `allAssertionsPassed` to establish these results. It
also does not independently re-establish all eleven VM assertions. The recorded
network probes, certificate outcomes and code were reviewed separately in
[PR #6 turn 13](https://github.com/mora-vector/strange-anchor/pull/6#issuecomment-5998946759).
The CI runs [37341156112](https://github.com/mora-vector/strange-anchor/actions/runs/37341156112)
and [37341155977](https://github.com/mora-vector/strange-anchor/actions/runs/37341155977)
were checked as successful on `a990b99`.

## Limits and context gaps

These are host-recorded artifacts from one builder and operator. An independent
reading is not an independently administered execution, a cryptographic attestation,
proof of model identity, or proof that a malicious host could not fabricate data.
Responders are deterministic; no AI-model exchange is established. The held
connection broke across a service restart, so it does not measure filter changes
on an uninterrupted connection. The guests retained their QEMU host-facing link.

At review time the artifact inventory contained certificate fingerprints but no
public PEM/DER files. Original certificate availability was queried in turn 13;
without those bytes, offline recomputation of their fingerprints is unavailable.
Later clarification should be appended as a new record, not silently substituted
into the reviewed inputs.

No archived context manifest was produced by this session. The JSON file hashes
identify the selected evidence inputs, not a complete session export.

## Certificate clarification, after Sideband's turn 14

Sideband recovered three original public certificates and both trust bundles/maps
from base64 provisioning commands already retained in attempt 4's `driver.log`.
The supplementary `certificates-attempt-4.json` records a separate verification:
the decoded bytes match the saved bundles and maps; the bundles decompose into
the supplied PEM files exactly; all three DER SHA-256 fingerprints match the
original report; both maps bind the expected installation. Nothing was regenerated.

The untrusted probe certificate remains unavailable, with its fingerprint only.
This is an explicit evidence gap, not a substitute certificate. The future-export
fix in `d48a439` is after the measured source `a990b99`; the existing run does not
validate that new export code.
