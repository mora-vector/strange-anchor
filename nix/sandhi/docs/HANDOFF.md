# Sandhi development handoff — 2026-09-17

Prepared by Tessera in the current Codex session. Sideband's review was supplied
by Mora; no new reply or endorsement from Sideband is implied. This document is
an engineering handoff, not an independent attestation or complete session export.

## Read first

1. `../VALIDATION.json` for measured status and evidence locations.
2. `DECISIONS.md` for accepted corrections and their boundaries.
3. `RECOVERY.md` and `../tests/recovery.nix` for the next experiment.

The last inspected remote head was
`70f5659d3655b3505d49379024c82897db1c5f95` on `tessera/sandhi-runtime`, PR #2.
This local continuation is not yet published. Automatic approval review rejected
the public GitHub upload, even after repository ownership/admin access was
verified. Publishing the prepared changes and evidence needs explicit approval
under that review. Do not route around the rejection through another transport.

## Next unresolved observation

Run 35271564455 passed evaluation and reachability, then ordinary realization
returned success without a visible fixture file. The proposed correction records
initial registration and file presence separately and uses repair mode to
establish the baseline. Controlled output deletion and the later ordinary rebuild
remain unchanged. A successful build or type check cannot establish this fix.

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
| `sandhi.enable` | Split accepted, intentionally deferred until recovery baseline passes | Cross-feature tests: export off cannot waive blockers; services off cannot emit unrestricted workloads |
| Resource budgets | Settings compiled; behavior under exhaustion not yet tested | Separate bounded experiments for timeout, retry, and memory/CPU behavior |
| Independent reports | `lib.saksya` compares declared derivation/output inventories and NAR hashes; no report is privileged as canonical | Authenticated reports with independently administered execution and explicit cache scope |

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
