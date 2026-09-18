# Sandhi — service contracts with measured boundaries

Sandhi grew from Sideband's Sanskrit derivation model and Tessera's runtime
contracts. Sanskrit names the design relationships; Nix and systemd implement
them. The v0.2 checkpoint added the vidhi compiler and a NixOS VM experiment.
Repository development now adds CI and stronger filesystem controls. See
VALIDATION.json for measured execution status and docs/CONTEXT.json for input scope.

## What changed

- `karaka.nix`: typed contracts for agent, affected resources/state, executable,
  peer recipients, named package inputs, and execution locus.
- `chandas.nix`: required CPU, memory, runtime, and restart budgets.
- `vidhi.nix`: compiles those declarations into systemd units, with separate
  dynamic users/state, write restrictions, peer-address filters, and limits.
- `lopa.nix`: independent knowledge, availability, and recovery-evidence fields.
- `kosa.nix`: optional retention of selected `.drv` paths through the system
  closure, alongside existing output retention.
- `tests/reachability.nix`: boots one guest and runs probes inside generated
  units against two healthy loopback-address HTTP fixtures.
- `tests/recovery.nix`: collects an unrooted control, retains recipes/input,
  restores a deliberately deleted fixture offline, and measures an unavailable-
  input counterexample. The complete baseline passed in CI; see
  [RECOVERY.md](docs/RECOVERY.md) for scope and original evidence.

Original documentary-claim and reported-output comparison shards are retained.
`docs/v0.1-README.md` and `evidence/v0.1-validation.json` preserve the earlier state;
the current README and VALIDATION.json supersede their current-status claims.

## Minimal contract

```nix
{ pkgs, ... }:
{
  imports = [ ./nix/sandhi/modules ]; # Relative to the repository root.
  sandhi = {
    enable = true;
    locus = "backplane";
    peers.sideband.ipv4 = "192.0.2.10"; # Documentation address: replace for deployment.
    contracts.worker = {
      kartr = "worker";
      karman = { state = "worker"; affected = [ "/srv/public-reference" ]; };
      karana = pkgs.curl;
      arguments = [ "--max-time" "5" "http://192.0.2.10:8080/" ];
      sampradana = [ "sideband" ];
      apadana = [];
      adhikarana = "backplane";
      startAtBoot = false;
    };
    chandas.worker = {
      cpuPercent = 50; memoryMiB = 128; retries = 2;
      windowSec = 300; runtimeMaxSec = 60;
    };
  };
}
```

This generates `sandhi-contract-worker.service`. The package must have a valid
main executable (or use a wrapper package). Arguments receive systemd-aware
escaping. No shell interpolation of contract values is used.

Named peers and inputs must exist; each contract needs a budget and the local
locus. Duplicate runtime agents or state-directory ownership are rejected.
Unknown references produce evaluation assertions rather than permissive defaults.
Legacy `sandhi.workers` names beginning with `contract-` are rejected: that
namespace belongs to compiled contract units and their state directories.
The compiler checks declared references; it cannot discover arbitrary references
hidden in program code or opaque arguments.

## Independent controls

`sandhi.services.enable`, `sandhi.retention.enable`, and `sandhi.registry.export`
each default to `sandhi.enable`, and can be explicitly overridden. Enable services
alone for restricted workloads, retention alone for store policy, or export alone
for claims and gap snapshots. Disabled services emit no managed workloads; disabled
retention deletes nothing and leaves host retention policy alone. Disabled export
does not waive declared blocking gaps—even when all features are disabled.

Contract snapshots require services and export together. Build-security settings
apply when the umbrella, services, or retention is enabled. See
[FEATURE-CONTROLS.md](docs/FEATURE-CONTROLS.md) for the precise boundaries and tests.

## Precisely what is enforced

- Nonempty recipient lists permit IPv4 traffic to the listed addresses. Both
  ingress and egress are filtered. This is address authorization, not peer identity,
  port authorization, TLS authentication, or a network route generator.
- Before a networked workload starts, a privileged preflight inspects effective
  cgroup BPF attachments and requires ingress and egress filters. Failure to inspect
  or missing filters prevents workload startup. Attachment presence is narrower
  than proof of rule correctness; the VM test checks actual behavior.
- Empty-recipient workloads get a private network namespace and AF_UNIX-only socket
  creation. This is not a blanket denial of filesystem Unix sockets or inherited
  descriptors. The compiler creates no socket-activation units.
- `ProtectSystem=strict` restricts writes. `ReadOnlyPaths` does not hide every
  unlisted readable file. This is not a full confidentiality sandbox or a VM-strength
  boundary against hostile workloads.
- `karman.affected` lists required host paths bound read-only. It grants no
  writes and does not override ordinary read permissions. Missing required paths
  prevent service startup through required `BindReadOnlyPaths` sources;
  `ReadOnlyPaths` alone did not establish this under `ProtectSystem=strict`.
  Nix evaluation cannot check a
  different machine's filesystem. `karman.state` separately declares owned writable
  state; the private temporary directory is also writable. The required-path
  experiment checks namespace failure before workload execution, then successful
  reading and EROFS on writes once that path exists. See VALIDATION.json for its
  observed status; the older packet-only results do not establish this behavior.
- State directories are separately owned; resource limits and bounded retries
  are emitted as service settings. `retries` excludes the initial attempt.
- Ancillary DNS is not silently allowed. Use explicit addresses, or design and
  declare a resolution mechanism. IPv6 peers are intentionally outside this first
  compiler's schema; networked units can create AF_INET and AF_UNIX sockets.

Host administrators can override modules and privileges. The policy assumes a
trusted NixOS configuration and kernel; it is not unbypassable governance.

## Runtime experiment

All HTTP probes are executed by the generated units, not by the driver's root
shell. The root-shell controls independently establish fixture health before
and after the probes. Fixtures use distinct loopback IPs in one guest; this tests
per-service filtering without an external network or identity service.

| Contract | Allowed peers | Sideband address | Echo address |
| --- | --- | --- | --- |
| first | sideband | reachable | blocked |
| changed | echo | blocked | reachable |
| empty | none | blocked | blocked |

The first two contracts use the same probe program and have PrivateNetwork=false.
Thus their difference exercises the allow-list, rather than merely an absent
network namespace. Each also writes its own state and tries a write to a world-writable host
directory. An unprivileged host control succeeds there; the sandbox must return
EROFS. This distinguishes the read-only mount from ordinary ownership denial. The test waits for each service to finish and writes structured observations into its output directory. HTTP error responses are distinguished from transport failures so server errors cannot masquerade as packet denial.

The VM experiment uses software emulation when hardware acceleration is absent.
Actual boot/test status and output identities are in VALIDATION.json and evidence/.
A test VM is not the production Strange Anchor host or a deployment to the fleet.

## Absence, preservation, and evidence

A registry entry can be `unknown` or `withheld` without claiming recovery evidence.
Availability defaults to `unassessed`. Recovery evidence is a list of typed
references; these references are statements to audit, not self-verifying proofs.
A blocking prerequisite remains an explicit assertion.

Lopa names the concept. `sandhi.gaps` is its typed registry and
`/etc/sandhi/lopa.json` is a generated snapshot for one system generation: a plain
JSON object keyed by gap ID. It is not a writable database, a fleet-wide canonical
record, or an independently authenticated evidence archive. Nix option types
validate declarations; no standalone JSON Schema or stable versioned export API
exists yet. External consumers should wait for that contract to be specified.

Selected output and recipe retention lasts while the retaining system generation
stays rooted. Recipe retention enables global keep-outputs and may retain much
more disk data than the selected recipes alone. No off-host backup, successful
restoration, or permanent recoverability is implied.

`lib.saksya` still returns `canonical = false`: report comparison does not establish
authenticity or builder independence. Documentation, evaluations, realized builds,
VM behavior, independent reproduction, and adoption are different evidence objects.

## Use and verification

The flake exports `nixosModules.default`, `lib` helpers, and three checks. It pins
Nixpkgs through flake.lock. It does not export a production host: supply actual
hardware, storage, secrets, backup destinations, and host assignments separately.
Keep the established `system.stateVersion` on existing hosts.

Run `python3 scripts/realize.py --output-dir ../sandhi-run-001` to capture one host's evidence automatically. See [BUILD-PROTOCOL.md](docs/BUILD-PROTOCOL.md) for realization, repeatability,
second-builder scope, retention, and archival instructions.

## Attribution and limits

Sideband supplied the eight-adhyaya model, Sanskrit vocabulary, and the proposed
vidhi junction. Tessera implemented and tested these shards; Mora relayed and
steered the exchange. The six-karaka question carried forward Sandhivela's plate;
it was not an independent rediscovery. Different model lineages reading a shared
corpus are not independent build attestations.

No cryptographic keys have been assigned to fictional crew identities. No fleet
leadership, automatic promotion, or production activation is claimed. Names remain beside their engineering meanings.

Sources: [NixOS modules](https://nixos.org/manual/nixos/stable/#sec-writing-modules),
[systemd execution](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml),
[systemd resource controls](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml),
[Nix settings](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).

## Repository validation

The `Validate Sandhi` workflow runs for relevant pull requests and main-branch
changes. It evaluates the flake, builds the evaluation artifact, boots the VM test,
and uploads per-run JSON and logs for 30 days, including on failure. It has read-only
repository permissions and no deployment step. It also runs the offline recovery
experiment described in [RECOVERY.md](docs/RECOVERY.md), including an unavailable
input that must fail to build. Archive evidence elsewhere before
the CI artifact expires. A CI pass is one runtime observation, not count-two
reproducibility.

The original v0.2 manifest and validation summary are preserved in `evidence/`
with a `v0.2-` prefix. Their hashes describe the checkpoint commit, not later
revisions. Raw checkpoint evidence remains unchanged.
