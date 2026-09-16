# Sandhi v0.2 — service contracts with measured boundaries

Sandhi grew from Sideband's Sanskrit derivation model and Tessera's runtime
contracts. Sanskrit names the design relationships; Nix and systemd implement
them. This release adds the vidhi compiler and a real NixOS VM experiment to the
v0.1 shards. See VALIDATION.json for this release's measured execution status.

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

Original documentary-claim and reported-output comparison shards are retained.
`docs/v0.1-README.md` and `evidence/v0.1-validation.json` preserve the earlier state;
the current README and VALIDATION.json supersede their current-status claims.

## Minimal contract

```nix
{ pkgs, ... }:
{
  imports = [ ./sandhi-shards/modules ];
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
The compiler checks declared references; it cannot discover arbitrary references
hidden in program code or opaque arguments.

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
network namespace. Each also writes its own state and tries an unauthorized /etc
write. The test waits for each service to finish and writes structured observations into its output directory. HTTP error responses are distinguished from transport failures so server errors cannot masquerade as packet denial.

The VM experiment uses software emulation when hardware acceleration is absent.
Actual boot/test status and output identities are in VALIDATION.json and evidence/.
A test VM is not the production Strange Anchor host or a deployment to the fleet.

## Absence, preservation, and evidence

A registry entry can be `unknown` or `withheld` without claiming recovery evidence.
Availability defaults to `unassessed`. Recovery evidence is a list of typed
references; these references are statements to audit, not self-verifying proofs.
A blocking prerequisite remains an explicit assertion.

Selected output and recipe retention lasts while the retaining system generation
stays rooted. Recipe retention enables global keep-outputs and may retain much
more disk data than the selected recipes alone. No off-host backup, successful
restoration, or permanent recoverability is implied.

`lib.saksya` still returns `canonical = false`: report comparison does not establish
authenticity or builder independence. Documentation, evaluations, realized builds,
VM behavior, independent reproduction, and adoption are different evidence objects.

## Use and verification

The flake exports `nixosModules.default`, `lib` helpers, and two checks. It pins
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
leadership, automatic promotion, repository publishing, or production activation
is claimed. Names remain beside their engineering meanings.

Sources: [NixOS modules](https://nixos.org/manual/nixos/stable/#sec-writing-modules),
[systemd execution](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml),
[systemd resource controls](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml),
[Nix settings](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).
