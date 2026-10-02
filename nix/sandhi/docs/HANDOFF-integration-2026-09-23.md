# Sandhi integration handoff — 2026-09-23

Prepared by Tessera from the inspected repository and Mora's instruction to
continue. The later Sideband relay is recorded under Next decisions; no independent
builder is implied.
The previous feature-control handoff is preserved in
HANDOFF-feature-controls-2026-09-23.md; its future-work statements describe that
historical checkpoint.

## Read first

1. `../VALIDATION.json` and the specific CI report it names for measured status.
2. `REVIEW-2026-09-23.md` for the review packet and attribution.
3. `LOPA-EXPORT.md`, `BUDGETS.md`, and `REPORT-COMPARISON.md` for the new contracts.
4. `CONTEXT-2026-09-23.json` for selected inputs and unavailable sources.

## Implemented continuation

* Both Lopa snapshots are gated by registry.export. The original gap-ID-keyed
  lopa.json retains its shape; lopa-v1.json uses a 1.0 envelope, standalone schema,
  and explicit nullable provenance for gaps and evidence. Unknown versions and
  malformed/duplicate-key inputs are refused by the bundled reader.
* The budget experiment covers per-attempt timeout, start-window exhaustion,
  touched resident-memory allocation, and CPU throttling, each with a control.
  Retries are additional starts inside windowSec, not a lifetime counter. Memory
  behavior is measured with swap absent and panic_on_oom=0; host policy remains
  outside these service declarations.
* compare_reports.py requires a declared subject/source and expected inventory.
  Artifact and behavior modes stay distinct; incomplete matching reports are
  held. Identity, administration, cache scope, and evidence declarations are
  required but not authenticated. lib.saksya remains compatible.
* The first workload is a manual local Lopa audit under a generated Sandhi unit.
  It validates a snapshot, hashes its exact bytes, inventories gaps and references,
  and writes report.json in owned state. Evidence references remain unverified.
  The workload has no declared network peers and no automatic schedule.

## Execution record

Local evaluation at implementation commit dd8d228 (published as 2dc832e with
identical tree) passed 199 Nix assertions and 17 Python tests, including legacy
export compatibility and schema validation. Its original report and evaluation
artifact are retained in evidence/local-integration-evaluation-001.

CI run 35807515761 was superseded after evaluation and reachability completed.
Review required touching every memory page rather than relying on zero-filled
virtual allocations. The original partial report remains running as captured;
its derived summary records GitHub's cancellation, not a completed pass.

Run 35807690591 passed evaluation, reachability, and recovery, then panicked the
budget guest at its 64 MiB cgroup limit. The test harness default panic_on_oom=2
caused a whole-guest panic. The next revision explicitly sets and verifies policy
0 for this expected OOM experiment; the workload limit and outcome assertions
stay unchanged. Original selected members, the contiguous failure excerpt, and
the artifact digest are retained beside the summary.

The corrected source is c69e209287720c378722fb49f5743d4250e1b904 (local f9d5127),
shared tree 18743cd48d0cbdae511025fbc05a840617394b64. Run 35864282761 is the
completed verification for that correction: all five checks passed, with 199
Nix assertions and 17 Python tests. Archive validation also passed. The original
artifact digest matched GitHub's metadata, every recorded source digest matches
the local implementation, and the recorder reported stable source at the end.
Selected original observations are retained in evidence/ci-35864282761, including
budget stop results/kernel counters and the actual workload report. The synthetic
merge tested by CI was ff1c422063d05cc5f32bca8fcbe583ab38a4811b.

The memory probe recorded one kernel OOM kill at 64 MiB; the same 96 MiB touched
allocation succeeded under 192 MiB. Zero/two retries produced one/three attempts,
with a further manual start denied. The timeout and its short positive control
behaved as expected. The 10% CPU unit used about 10% of one CPU over the measured
six seconds and accumulated throttle events; the 100% control did more work.
The audit's report matched the snapshot's exact input hash and retained explicit
unverified evidence references. These are bounded observations on one builder.

## Reproduce and review

Use a fixed checkout and a new output directory outside the source tree:

```sh
cd nix/sandhi
python3 scripts/realize.py --output-dir /path/outside/checkout/sandhi-integration-001
```

The default now requires all five checks: evaluation, reachability, recovery,
budgets, workload. Recorder schema 5 includes schema-file digests. Selecting only
the old three checks cannot produce a full-suite pass. A bounded follow-up may
use `--check budgets --check workload`, with its narrower scope explicit.
Do not repeat the known local EPERM guest-launch failure without changed launch
capability. CI is the measured runtime builder for this checkpoint.

Import examples/lopa-audit.nix into a chosen NixOS configuration to obtain the
manual service; the repository itself has no production host activation. Start
sandhi-contract-lopa-audit.service only on that configured host and inspect its
owned report and input hash. An older completed report is not overwritten when a
later invocation fails validation.

## Next decisions

Sideband's subsequent note, relayed by Mora, is captured verbatim as supplied in
SIDEBAND-RELAY-2026-09-23.md. See the final September 23 entry in DECISIONS.md and
CONTEXT-SIDEBAND-2026-09-23.json for its disposition and source limits. It identifies
two distinct recorded publication refusals and the later private-publication
authorization; no unresolved public-upload refusal is a draft-review gate.

The next implementation checkpoint is retention-evidence applicability: turning
retention off must withdraw any current affirmative assessment relying on it,
while preserving historical observations. Re-enabling it must not automatically
revive a stale assessment. This invariant is not yet implemented or tested and
is now the explicit technical condition for ready-for-review. Keep the current
bounded recovery test; separate image-transport and absent-before-repair tests
are deferred, and neither is claimed to pass. Follow the Lopa compatibility rules.

A later checkpoint is a separately administered execution with explicit
cache scope and retained original evidence. Construct the comparison specification
from the exact source and expected artifact/assertion inventory; do not count
shared discussion, a local rebuild, or two labels on one host as independence.
Authentication/signing and release policy are not implemented. No canonical
promotion, merge, fleet database, or production activation follows from this work.

Sideband can review the packet without a fabricated reply. Mora retains the
choice of production workload/host, storage costs, and the independent operator.
Routine review and fixture work can continue without repeated mediation.
