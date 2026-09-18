# Sandhi development handoff — 2026-09-18

Prepared by Tessera in the current Codex session. Sideband's review was supplied
by Mora; no new reply or endorsement from Sideband is implied. This document is
an engineering handoff, not an independent attestation or complete session export.

## Read first

1. `../VALIDATION.json` for measured status and evidence locations.
2. `DECISIONS.md` for accepted corrections and their boundaries.
3. `RECOVERY.md` and `../tests/recovery.nix` for the recovery experiment.
4. `FEATURE-CONTROLS.md` for the next bounded implementation and its test matrix.

The last inspected remote head was
`6deae6ebb28b800a335c42f6c2ce724775cf9377` on `tessera/sandhi-runtime`, draft PR #2.
Mora made the repository private and explicitly authorized publication; the
prepared continuation and CI-derived evidence have now been published through
the configured GitHub connection. No merge, production activation, or access
change was performed. Remote and local commits can have different metadata/SHAs
because publication used GitHub's commit API; compare trees, not just commit IDs.

## Completed baseline; next implementation

Run 35319510107 reached collection and offline restoration with matching bytes
and NAR hash, then failed an overly strong physical-absence assertion for the
unavailable-input counterexample. A failed fetch had left a residual file. The
correction measures the specific missing-input failure, store validity, and
payload identity separately, recording residual bytes rather than deleting or
ignoring them. Run 35320318020 passed all three checks; its saved observations
confirm the residual was an invalid empty file, not recovered payload. Original
report, guest observations, and output metadata are retained under
`../evidence/ci-35320318020/`, with the source head and synthetic merge revision
separate. All recorded source digests match the published implementation. Earlier
failed runs remain failed, with their original reports retained.

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
| `karman.affected` | Documented as required read-only constraints, distinct from owned writable state | Guest test: required path present permits startup; missing path prevents workload execution |
| Lopa/export naming | Documented typed registry versus generated per-generation JSON snapshot | Specify a versioned export/schema before external consumers depend on it |
| `sandhi.enable` | Split specified in FEATURE-CONTROLS.md; recovery prerequisite passed; implementation next | Eight cross-feature combinations plus umbrella compatibility; export off cannot waive blockers; services off cannot emit unrestricted workloads |
| Resource budgets | Settings compiled; behavior under exhaustion not yet tested | Separate bounded experiments for timeout, retry, and memory/CPU behavior |
| Independent reports | `lib.saksya` compares declared derivation/output inventories and NAR hashes; no report is privileged as canonical | Authenticated reports with independently administered execution and explicit cache scope |

Checkout and artifact upload now use full-SHA Node 24 action pins; ZIP uploads
remain explicit. Archive validation exercises checkout; Sandhi CI exercises both
checkout and upload. The comment archiver's checkout pin also changed, but that
workflow's event-specific behavior is not tested by this PR. Triggers and access
scopes were not expanded.

Next implementation order: split the three feature controls with
evaluation-matrix coverage; exercise services-only and
retention-only guests; add the required affected-path startup counterexample.
Do not treat the design document as an implemented option API. A versioned lopa
export and budget-exhaustion tests remain subsequent work.

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
