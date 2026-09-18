# Independent feature controls — proposed contract

Status: design only; the recovery prerequisite passed in run 35320318020. The
options below are not yet implemented or tested. This is Tessera's interpretation
of Sideband's review relayed by Mora, not a new response from Sideband.

`sandhi.enable` remains a compatibility default, not a bypass switch. Planned
explicit controls each default to its value:

| Proposed option | Responsibility when true | Behavior when false |
| --- | --- | --- |
| `sandhi.services.enable` | Compile contracts and legacy workers into restricted units | Emit no Sandhi-managed service units; never emit an unrestricted alternative |
| `sandhi.retention.enable` | Apply keep-derivations, selected recipe/output retention, and scheduled-GC policy | Leave host retention policy untouched; runnable services still need their normal package closure |
| `sandhi.registry.export` | Export public claims, gaps, and active contract snapshots | Emit no diagnostic snapshots; blocking gap assertions still apply |

These switches do not grant an option to run a contract with its declared network
restrictions silently removed. A workload needing different networking needs a
different, explicit contract. Nor does disabling retention imply deletion: other
system generations and roots may still retain the same objects.

All declared `blocksActivation` gaps must remain assertions independently of
export. The operator may resolve or explicitly remove a gap; hiding its JSON is
not resolution. Runtime dependencies are separate from archival retention.

The existing build-security settings in kosa (sandbox, signatures, no IFD) need
an explicit boundary during implementation: preserve them for the umbrella or
enabled execution/retention, without forcing them for a registry-only system.

## Acceptance matrix

Evaluate all eight combinations with the umbrella disabled. Check emitted units,
retention settings, exported snapshots, and blocking assertions separately. Also
retain the original umbrella-only compatibility test. A services-only guest must
pass the existing packet/write experiment without registry export; a retention-
only guest must pass recovery without generating service units.

The affected-path experiment should run the same unit first with a missing
required path and then with that path present. Require the first attempt to fail
before the workload writes its execution marker, and the second to execute.
Also inspect the namespace failure status; a generic nonzero return is not enough.

An export-schema change is separate from this toggle split. Preserve the current
gap-ID-keyed JSON shape unless a versioned migration is explicitly documented.
