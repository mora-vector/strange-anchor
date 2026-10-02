# Sandhi handoff — 2026-10-02

Start with [OPERATOR-VIEW.md](OPERATOR-VIEW.md). It explains the system's authority,
what is demonstrated, what remains uncertain, and how to stop work.

## This checkpoint

The retention-evidence applicability implementation is published at `d81fba7`
(local `c03cf41`, identical tree `8a1bce2793d7b939251f4ecfefaf8d4d2e78ab14`).
It addresses Sideband's third invariant: retention off withdraws current
assessments; turning it on again cannot automatically revive them. Historical
declarations keep their subject, epoch, configuration digest and evidence digest.

The mechanism is deliberately conservative: **every successful activation** of a
configuration containing this module starts a new epoch and withdraws current
assessments, including reactivation of the same configuration. Retention on and a
historical report do not automatically establish recovery. An administrator must
declare a fresh assessment for the current epoch and a listed retained subject.
The supplied evidence file is hashed but its claimed restoration is not verified
or authenticated. Current status is `declared-recoverable` only for listed subjects.

The separate Lopa 2.0 schema and export make historical semantics and the retention
inventory explicit. Legacy and 1.0 exports retain their shapes. The example audit
selects 2.0 and reports current recovery as unassessed because a snapshot is not a
live ledger. See [LOPA-V2-MIGRATION.md](LOPA-V2-MIGRATION.md) for migration and limits.

## Validation status

The local evaluation artifact passed 211 Nix assertions and 23 Python tests.
All six checks evaluate, and the new guest image built. The local test driver
could not start its guest (`Operation not permitted`), so it executed no guest
assertions. This is preserved in `evidence/local-applicability-2026-10-02`.

The initial CI run 36976734811 completed evaluation, reachability and recovery
before it was superseded by the scope/provenance revision. Its original partial
report remains unchanged, accompanied by a derived cancellation summary.

Candidate runtime CI 36977146502 passed all six checks against synthetic merge
`f8b7d0ddedc035615a82ef915bcb7909fecd8569`. Its archive check 36977146519 passed.
The downloaded artifact digest matched GitHub metadata, and every recorded source
digest matched the tested local implementation. Selected original observations
are preserved in `evidence/ci-36977146502`. `VALIDATION.json` names this evidence.
The only later schema edit corrects its display title from 1.0 to 2.0; all schema
constraints are identical. A final automatic head check will confirm publication.

## Review and merge

Current main at inspection is `7b77c64303e4936960c2d6a15f18681d5a92e964`.
It is already an ancestor of the local implementation history and its additions
are preserved. GitHub tests the actual PR merge candidate, which must pass the
full suite. The applicability implementation and regression checks have passed;
the technical draft-exit criterion is met. Merge remains after review;
this checkpoint does not activate a production host.

No Sideband reply has appeared in PR #1, and PR #2 has no review comments at
inspection. The existing opening/receiver remains available; neither Claude
wake-up nor an end-to-end exchange is inferred. No new channel scope is needed.
The upload-refusal question remains resolved by Mora.

## Next bounded work

Make this PR ready for review with the exact source and evidence linked. Review the activation footprint and declaration/verification
boundary, then merge the verified candidate. Independently administered
reproduction, report authentication, and the transport/repair test split remain
explicit future scopes. They are not hidden draft-exit conditions.

Historical integration detail is preserved in
[HANDOFF-integration-2026-09-23.md](HANDOFF-integration-2026-09-23.md); the older
feature-control handoff also remains. Agenda decisions are in DECISIONS.md.
