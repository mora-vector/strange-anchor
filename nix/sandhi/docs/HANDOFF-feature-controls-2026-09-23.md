# Sandhi development handoff — 2026-09-23

Prepared by Tessera in the current Codex session. Sideband's review was supplied
by Mora; no new reply or endorsement from Sideband is implied. This document is
an engineering handoff, not an independent attestation or complete session export.

## Read first

1. `../VALIDATION.json` for measured status and evidence locations.
2. `DECISIONS.md` for accepted corrections and their boundaries.
3. `RECOVERY.md` and `../tests/recovery.nix` for the recovery experiment.
4. `FEATURE-CONTROLS.md` for implemented options and their test matrix.

The tested implementation head is
`fcdaece7c8d13560dbc48d075a238ac7109853de` on `tessera/sandhi-runtime`, draft PR #2.
Its pending evidence commit was published on 2026-09-23 as
`2eb9138d6f03dd81404ca003873eaacff44baa18`, with tree
`e95666389cac37aae1fafd77b77e3331a83cf822`, identical to local commit
`cb79166ac79c66bcf153745633721365592fd799`.
Mora made the repository private and explicitly authorized publication; the
prepared continuation and CI-derived evidence have now been published through
the configured GitHub connection. No merge, production activation, or access
change was performed. Remote and local commits can have different metadata/SHAs
because publication used GitHub's commit API; compare trees, not just commit IDs.

## Completed baseline and current continuation

Run 35319510107 reached collection and offline restoration with matching bytes
and NAR hash, then failed an overly strong physical-absence assertion for the
unavailable-input counterexample. A failed fetch had left a residual file. The
correction measures the specific missing-input failure, store validity, and
payload identity separately, recording residual bytes rather than deleting or
ignoring them. Run 35320318020 passed all three checks; its saved observations
confirm the residual was an invalid empty file, not recovered payload. Original
report, guest observations, and output metadata are retained under
`../evidence/ci-35320318020/`, with the source head and synthetic merge revision
separate. Those source digests identify that baseline revision; later changes
require their own results. Earlier failed runs remain failed, with their original
reports retained.

The three feature controls are now implemented, with 143 new evaluation assertions
(182 total including the required-bind assertion). Run 35397280379 passed
evaluation and services-only packet/write
checks with registry snapshots absent. Its retention guest stopped at an unmatched
systemctl inventory-pattern query. The corrected query positively identifies
nix-daemon.service in the complete inventory and requires no Sandhi units.

Run 35399320533 passed the complete suite. It verifies the independent controls,
retention-only recovery, services-only boundaries, and required-path enforcement.
The missing path failed at `226/NAMESPACE` before the execution marker; the same
unit later read the present path and received `EROFS` on write. Its artifact digest
and selected original members are retained under `../evidence/ci-35399320533/`.
Run 35397906109 caught a driver type-inference error before boot; the evidence
container now has an explicit heterogeneous type, with type checking still on.
Run 35398323774 then found a real compiler gap: ReadOnlyPaths with ProtectSystem
did not reject the missing path, and the workload executed. Vidhi now also emits
required read-only bind mounts; run 35399320533 verified this fix with the
unchanged negative test and the same-unit positive control.

Local recovery attempt 006 built the image and driver but could not launch the
guest (EPERM). Do not repeat that environment-only failure without evidence of
changed launch capability. Run on a capable builder from a fixed checkout:

```sh
cd nix/sandhi
python3 scripts/realize.py --check recovery --output-dir /path/outside/checkout/sandhi-recovery-001
```

Use a new output directory. Inspect the exact source digests, requested/completed
checks, baseline presence/registration, GC control, before/after hashes, and the
missing-input counterexample. If it fails, keep the failure and diagnose the named
step; do not weaken the assertion to obtain a pass.

## Sideband review disposition

| Concern | Current disposition | Next evidence |
| --- | --- | --- |
| `karman.affected` | Required-path enforcement passed in CI | Namespace exit 226, missing-path journal, absent marker; unchanged unit later executes with read-only access |
| Lopa/export naming | Documented typed registry versus generated per-generation JSON snapshot | Specify a versioned export/schema before external consumers depend on it |
| `sandhi.enable` | Three controls and both isolated runtime modes passed | Versioned export and budget-exhaustion experiments remain future work |
| Resource budgets | Settings compiled; behavior under exhaustion not yet tested | Separate bounded experiments for timeout, retry, and memory/CPU behavior |
| Independent reports | `lib.saksya` compares declared derivation/output inventories and NAR hashes; no report is privileged as canonical | Authenticated reports with independently administered execution and explicit cache scope |

Checkout and artifact upload now use full-SHA Node 24 action pins; ZIP uploads
remain explicit. Archive validation exercises checkout; Sandhi CI exercises both
checkout and upload. The comment archiver's checkout pin also changed, but that
workflow's event-specific behavior is not tested by this PR. Triggers and access
scopes were not expanded.

Next implementation order after this runtime verification: specify a versioned
lopa export and migration policy before adding external consumers, then exercise
budget exhaustion with bounded timeout/retry and memory/CPU experiments. Keep
registry references distinct from independently verified evidence. The new
feature options are implemented; the export is still the existing unversioned
gap-ID-keyed snapshot, with no new fleet database or signing protocol.

## Collaboration contract

Contributors may share designs without claiming independent rediscovery. Keep
original evidence separate from interpretations. Name the object a result tests.
Use separate fixed checkouts when working concurrently. The recorder detects
start/end source drift, not transient edits or malicious changes.

Selected checks reduce repeated work; their success does not imply unrequested
checks passed. A collaborator can finish or pause with a precise unresolved
question. No invented reply, automatic conversation expansion, production
activation, or release promotion is part of this handoff.

Mora sets purpose and acceptable operational costs. The next product choice is
one useful first workload, followed by host, storage budget, and an independent
builder when needed. Routine source review and fixture testing can proceed
without requiring Mora to mediate every engineering choice.
