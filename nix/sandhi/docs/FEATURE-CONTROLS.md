# Independent feature controls

Status: implemented; validation of the feature split is recorded in VALIDATION.json
and the associated CI evidence. The earlier recovery prerequisite passed in run
35320318020. This is Tessera's implementation of Sideband's review relayed by Mora,
not a new response from Sideband.

`sandhi.enable` remains a compatibility default. The explicit controls each
default to its value; any of them can override that default with true or false:

| Option | Responsibility when true | Behavior when false |
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
This also applies with all switches off, including `sandhi.enable`: an explicitly
declared blocker cannot be silently waived by disabling the subsystem.

Contract snapshots require both services and export. Registry-only systems export
claims and gaps without presenting dormant contract declarations as active units.
Dormant contracts still have typed declarations, but service-specific reference,
budget, locus, and ownership assertions apply only when service compilation is on.

The existing build-security settings in kosa (sandbox, signatures, no IFD) apply
when the umbrella, execution, or retention is enabled. Registry export alone
leaves the host build policy untouched. Retention's automatic-GC setting remains
a default an administrator can override; disabling retention emits no GC policy.

## Acceptance matrix

`tests/features.nix` evaluates all eight combinations with the umbrella disabled,
checking emitted units, runtime dependencies, retention settings, exported
snapshots, build policy, and blocking assertions separately. It also checks the
umbrella default, explicit overrides under the umbrella, and dormant versus
enabled contract validation. Host defaults deliberately differ from Sandhi's to
detect policy leakage. The services-only guest exercises the packet/write
experiment without registry export; the retention-only guest exercises recovery
and requires no Sandhi units despite nonempty worker/contract declarations.

The affected-path experiment in `tests/reachability.nix` runs the same unit first
with a missing required path and then with that path present. It requires namespace
exit status 226, a journal diagnostic naming the missing path, and no workload
execution marker. Once the path exists, the unchanged unit must execute, read the
reference payload, and receive EROFS when trying to write there. An unprivileged
host write control rules out ordinary directory ownership as the cause. This tests
the full generated sandbox, where ReadOnlyPaths and ProtectSystem overlap.

Type=simple start-job success is not accepted as evidence of execution: the test
waits for the actual process status. It explicitly stops the failed attempt and
resets the failure/start-limit state before the second run. Dedicated retry-budget
and timeout behavior remains a separate future experiment.

An export-schema change is separate from this toggle split. Preserve the current
gap-ID-keyed JSON shape unless a versioned migration is explicitly documented.
