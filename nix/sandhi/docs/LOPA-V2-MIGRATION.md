# Lopa 2.0 and current recovery assessments

Lopa 2.0 adds `/etc/sandhi/lopa-v2.json` with an explicit
`evidenceSemantics: historical-declarations` and a `recoveryPolicy` inventory:
`retentionEnabled`, and subjects identified by output/recipe kind plus store path.
The legacy and 1.0 files remain byte-shape compatible. All three exported files
follow `sandhi.registry.export`. Their evidence references do not assert current
recoverability. The 2.0 schema is bundled as `schemas/lopa-v2.schema.json`.

`recoveryPolicy.subjects` lists **declared targets**, not an observed rooted
inventory. They remain listed when retention is disabled, so a reader can tell
"configured but disabled" from "nothing configured". `retentionEnabled` records
this snapshot's configured premise, not proof of its current activation or of
recoverability. A consumer that needs the effective configured targets derives an
empty set when the flag is false. Neither form establishes that the bytes exist.
Legacy and 1.0 exports are byte-identical whether retention is on or off; an
evaluation fixture pins this, and the activation test observes it with export on.
These clarifications change no schema constraint.

Readers must explicitly select 2.0. The bundled audit's default remains 1.0;
pass `--schema schemas/lopa-v2.schema.json` for a 2.0 snapshot. The example service
now selects the bundled 2.0 schema and required snapshot. It always reports
`currentRecovery: unassessed`: an immutable snapshot cannot certify a live state.
Legacy/1.0 consumers must not infer a present recovery pass from a historical
`verified-restoration` reference. No automatic migration of those consumers or
historical claims to current assessments occurs.

## Local lifecycle

Importing the Sandhi module installs `sandhi-recovery-state` and an activation
hook even when services, retention and registry export are disabled. This small
bookkeeping footprint is required to withdraw assessments when retention is off.
It starts no service, changes no GC policy, and grants no workload access. The
private policy snapshot is a store file whether public export is enabled or not.
Its subject strings discard Nix reference context: naming a subject must not
itself retain that output or realize a selected recipe.

Every successful activation of a configuration containing this module creates a
fresh random epoch and withdraws all current assessments. That includes boot,
switching to retention off, switching back on, and activating the identical
configuration again. Revalidation after harmless changes is a deliberate
conservative cost. The ledger at `/var/lib/sandhi-recovery/state.json` preserves
historical records with subject, epoch, configuration snapshot digest, evidence
reference and digest, and the administrator's declared identity. A file lock and
atomic replace cover each update; the ledger is private to root (0600 in a 0700
directory). This is an operational record, not an append-only signed archive.

`sudo sandhi-recovery-state status` reads current applicability. It returns
`unassessed` if state is absent or there are no current declarations. It returns
`declared-recoverable` only for the **listed subjects**, never for the whole store.
Malformed state or a mismatch with the installed command's policy returns a
nonzero exit; consumers must treat this as no usable current assessment.

After conducting a fresh recovery validation for the current activation, an
administrator can explicitly record its result:

```sh
sudo sandhi-recovery-state status
sudo sandhi-recovery-state record \
  --epoch CURRENT_EPOCH --kind output --subject /nix/store/ACTUAL_SUBJECT \
  --reference ACTUAL_REPORT_REFERENCE --evidence /path/to/report.json \
  --asserted-by ADMINISTRATOR_ID
```

The subject must occur in the activated retained inventory, retention must be
on, and the epoch must still match. The command hashes the supplied local file.
It **does not inspect whether that file proves successful recovery**, authenticate
its author, fetch a reference, execute a repair, or certify independent execution.
Every entry says `verification: not-performed`. This is deliberate declaration
and applicability tracking; an automatic verifier is a separate future feature.
Old epoch replay is refused. An administrator can still knowingly redeclare old
or false evidence under a new epoch; this tool cannot make that truthful.

## Limits and failure handling

Always use the installed generation's command and query it afresh. Saved status
output is a dated observation and must never be reused as a live guarantee.
Arbitrary archived command/store paths are not authorities for the running
system. The ledger tracks successful module activations, not continuous changes
to bytes, external GC roots, filesystem corruption, off-host backups, or network
reachability. A hash does not make a report an authenticated attestation.

Do not rely on a current claim after a failed system activation; resolve the
activation error and activate successfully before revalidating. Removing the
module entirely, booting a pre-lifecycle system, restoring an old whole-machine
backup, or root tampering with the ledger lies outside this invariant. Those
systems have no supported live assessment API. Preserve the ledger before
manual repair; do not silently overwrite malformed history. Recreating missing
state starts unassessed and cannot revive a saved old epoch.

## Acceptance evidence

`tests/test_recovery_state.py` exercises positive declarations, off/on, replay,
reactivation, wrong subjects, malformed state, policy mismatch, and schema rules.
`tests/applicability.nix` performs real NixOS switches to a specialization with
retention and export disabled, then back to the exact original snapshot. It
checks withdrawal, retained history, old-token refusal, explicit new declaration,
and another withdrawal on same-configuration activation. The declaration fixture
hashes actual local fixture bytes; it is not a claim of independent restoration.

Read `VALIDATION.json` and the named run for measured status. Test source alone
is not a runtime pass.
