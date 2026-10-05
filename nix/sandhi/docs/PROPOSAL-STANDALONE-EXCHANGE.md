# Proposal: a standalone agent exchange between Sandhi installations

Status: **proposed, for discussion in this branch's pull request.** Nothing here is
a decision. Accepted scope goes into DECISIONS.md before any test or code exists,
as experiment 0's scope did.

Recorded on 2026-10-05 by a Claude Code session started by a repository user. The
session is a new runtime, not the PR #1 receiver. Model: `null`.

## The question

Can two independently installed copies of Sandhi carry a conversation between AI
agents from different model families, with no GitHub dependency and no person
relaying messages during execution?

Tessera's answer and this session's answer agree: **not with the current package.**
Sandhi restricts services and records gaps. It has no communication endpoint, model
adapter, peer authentication, conversation state or message-evidence integration.
`examples/mesh.nix` is an inventory with `host = null`, not a network.

Tessera's proposed acceptance criterion, relayed by the user in this session (not
posted on GitHub):

> Two separately installed Sandhi nodes, using different model families, complete a
> bounded information-exchange task over an authenticated direct connection, with
> matching message records and no GitHub access or human relay during execution.

## Constraints read from the current code

- `IPAddressAllow` filters ingress as well as egress (`modules/vidhi.nix`). A
  listening contract with one peer accepts only that peer's address. Routing and
  the host firewall are not created by Sandhi.
- `CapabilityBoundingSet = ""`, so a contract cannot bind a privileged port. The
  threshold is the kernel's per-namespace `net.ipv4.ip_unprivileged_port_start`
  (usually 1024), so a test records the guest's value rather than assuming it
  (Tessera, PR #6 turn 1).
- `runtimeMaxSec` is required and finite (`modules/chandas.nix`). A listener is
  stopped at that limit and restarted only within the start budget, which is a rate
  per window, not a lifetime ceiling. For a bounded experiment this is useful. A
  standing service would need a schema change.
- Contract values are public configuration (`modules/karaka.nix`). Keys and
  certificates must reach the process at runtime, outside the Nix store.
- Peers are IPv4 literals. Experiment 0 showed host-mediated DNS escapes the filter;
  explicit addresses avoid depending on the unfinished name-resolution design but
  do not close that path.
- CPU and memory budgets limit the local process, not remote inference spending.

## Proposed stages

| Stage | Setup | Establishes | Needs |
|---|---|---|---|
| A. Transport | One NixOS test, two guests on a private VLAN, each importing Sandhi with its own configuration; deterministic responders; a third guest as an unauthorised sender | Delivery, authentication, restriction, duplicates, restart, permission withdrawal | Nothing beyond this repository |
| B. Local models | Stage A with two small open-weight models from different publishers, run offline through llama.cpp, weights pinned by SHA-256 | Real cross-family exchange with the exact model bytes identified; no keys or spending | Licence review per model; weight download; CPU time |
| C. Hosted adapters | Adapters for hosted providers | Exchange between hosted models | Mora's decision on keys, spending limits and egress |
| D. Separate operators | Stage B or C on hosts run by different people | Independent administration | A second operator |

Stage A must be labelled a transport test, not AI communication. Two guests on one
builder are separate installations, not independent administration.

## Message and record

Each message carries: protocol version, conversation ID, message ID, parent ID,
sender, recipient, turn, deadline and payload. The existing `anchor-message:v1`
header covers sender, recipient, model, parent and turn; the rest would be a
version 2 or a transport envelope around it. Each node preserves exact sent and
received bytes with `anchor.py`, so the two archives can be compared afterwards.

## Tests proposed for stage A

- A full bounded exchange completes, and both archives hold identical message bytes.
- A duplicate delivery is recorded once and answered once.
- The receiver restarts mid-exchange and the exchange resumes or fails visibly.
- An unauthorised sender is refused, at the address filter and at authentication.
- Withdrawing a peer in the next activation stops delivery.
- The information-exchange task: each side holds part of a synthetic problem, and a
  separate checker verifies the joint result. It must fail when the channel is cut.

## Open questions

1. Authentication: mutual TLS between installations (Tessera's suggestion), signed
   messages, or both? Signed messages survive a relay and can be checked from the
   archive alone; mutual TLS authenticates the connection only.
2. Who holds the private keys, and does assigning them to node names conflict with
   the README's statement that no keys are assigned to crew identities?
3. Should stage B be the first AI stage, ahead of hosted adapters?
4. Which environment can run stage A for each node? This session has Nix, 4 cores
   and no KVM. Tessera's environment reports no Nix, QEMU or KVM.
