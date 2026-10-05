# Sandhi handoff — 2026-10-05 (artifact verification)

Tessera, a new OpenAI session, inspected main `ff75d2a1d1ff41899818da33b957ef0d973bfa8e`.
PR #3 is merged at Mora's instruction. Its final head `bfd0e31` has the same tree
as that merge; Actions API reports Sandhi run 37076963957 and archive run
37076963889 successful. No implementation changed since the premise-separation handoff.

The requested artifact verification is complete: artifact 11216103657 from run
36983396017 was downloaded (183515 bytes), its SHA-256 matched GitHub's reported
digest, and ZIP CRC verification passed. The report identifies tested merge
`e03c1711af887a2a53436add70e76af9d9dd54ca`. All 40 recorded source hashes match
main at inspection; the recorder reports no endpoint source drift. Original report,
guest observations and path metadata are preserved alongside a new
[verification record](../evidence/ci-36983396017/VERIFICATION-2026-10-05.json).
Sideband's original API-only SUMMARY.json remains unchanged as a historical record.
This is evidence inspection, not a fresh build or independently administered reproduction.

PR #1's latest inspected contribution is Tessera's comment 5963429159. Mora's
comment 5963129962 assigns Tessera Independent Administration design and Sideband
DNS design. Synthetic alignment and its four evidence layers are discussion-stage
design, not implemented scope. Later F5 deferral conditions and these design
assignments still need an attributed DECISIONS.md entry before implementation.
F5 remains deferred; reopen before production activation or operational reliance
on declared-recoverable, with ordered fault-injection tests. No new implementation
scope is established by this evidence update.

---

# Sandhi handoff — 2026-10-02 (premise separation)

Start with [OPERATOR-VIEW.md](OPERATOR-VIEW.md).

## This checkpoint

PR #3 carries two commits after the PR #2 merge (`d602a4a`). The first is Sideband's post-merge
review, [SIDEBAND-REVIEW-2026-10-02.md](SIDEBAND-REVIEW-2026-10-02.md). The second, `ec08eff`,
implements the F1 and F2 dispositions agreed with Tessera in PR #1, without Mora relaying them
(see DECISIONS.md, 2026-10-02). Retention off with export on, and export off with retention on,
are now separate activation legs. Legacy and 1.0 export invariance under retention is pinned by
evaluation. v2 `recoveryPolicy.subjects` is documented as declared targets.

CI 36983396017 passed all six checks on `ec08eff` against `d602a4a`; archive validation passed in
36983396062. The conclusion comes from the Actions API, and Tessera confirmed it in PR #1. Its
artifact was not downloaded or digest-checked from Sideband's session, because the host is
blocked there. A second builder passed the evaluation (214 assertions), applicability and
workload checks under software emulation. The full PR #2 checkpoint record follows below,
unchanged.

## Open items

- F5, failed-activation hardening, is to be decided in a Sideband–Tessera exchange, and requires
  fault-injection tests before any stronger guarantee is claimed.
- Fetch and verify the 36983396017 artifact before it expires on 2026-11-01.
- Production activation, independent administration and authentication remain separate scopes.

---

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
