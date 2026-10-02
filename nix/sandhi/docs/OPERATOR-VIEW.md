# Sandhi — operator's view

Sandhi is a tested NixOS prototype that turns a workload's declared needs into
operating-system restrictions and keeps a record of what is known and unknown.
This branch is under review. It has not been deployed to a production vessel.

| Question | Current answer |
|---|---|
| What exists? | A service compiler, separate retention/export controls, an evidence registry, budget experiments, report comparison, and a manual local audit workload. |
| What can it affect? | On a host that explicitly imports and activates it: generated processes, their file/network access and resource budgets; selected Nix store retention; exported metadata; and a local recovery-assessment ledger. |
| What changed at this checkpoint? | Old recovery declarations lose current applicability whenever the system is activated. Switching retention off and back on cannot automatically restore their validity. Historical records remain inspectable. |
| What has been demonstrated? | All six checks passed: evaluation, service/file/network boundaries, bounded offline restoration, resource budgets, the audit workload, and actual activation transitions. This includes 211 Nix assertions and 23 Python tests; source-linked evidence is in VALIDATION.json. |
| What remains uncertain? | Independent reproduction and authenticated reports; separate image-transport proof; production behavior and off-host recovery. A local administrator's recovery declaration is still a claim, even when its referenced bytes have been hashed. |
| What needs Mora's decision? | Purpose, wider access, expenditure, production activation and acceptable loss. The current implementation/testing scope needs no new decision. Merge follows technical verification and review; deployment is a separate choice. |
| How do we stop it? | Stop a generated workload with systemctl; disable service generation in the next activated configuration. Keep retention separately if its ingredients should remain. Pause the dialogue receiver through PR #1 with the existing operator-only ANCHOR PAUSE control. |

## One concrete demonstration

The Lopa audit reads a required registry snapshot, validates it, hashes it, and
writes a report in its own state directory. It has no declared network peers.
Its report lists evidence references with verification explicitly not performed.
The boundary tests separately try undeclared connections and forbidden writes;
those attempts must fail. They also remove a required path: the workload must not
start until that path is present. This turns a promise into an observable test.

The new recovery demonstration starts with a positive administrator declaration.
It activates retention off, then on again. The same historical evidence and exact
same exported snapshot may return, but the old declaration must stay unassessed.
Only an explicit fresh declaration for the new activation can appear as current.
This guards against stale confidence; it does not manufacture recovery proof.

## Inspect and stop on an explicitly activated test host

```sh
systemctl status sandhi-contract-lopa-audit.service
sudo systemctl stop sandhi-contract-lopa-audit.service
sudo sandhi-recovery-state status
```

For a lasting service stop, set `sandhi.services.enable = false` and activate the
revised host configuration. Decide retention separately: `sandhi.retention.enable
= false` withdraws policy support and current assessments, but deletes no bytes
by itself. Existing rooted generations and external roots may still retain them.
Do not use forced store deletion as a stop button.

The ledger's history is in `/var/lib/sandhi-recovery/state.json`. The command's
current result is scoped to the listed subjects and activated policy. A saved
report, a successful CI run, or agreement between model contributors cannot
stand in for current host verification.

Technical detail: [handoff](HANDOFF.md), [validation](../VALIDATION.json),
[lifecycle contract](LOPA-V2-MIGRATION.md), [recorded decisions](DECISIONS.md).
