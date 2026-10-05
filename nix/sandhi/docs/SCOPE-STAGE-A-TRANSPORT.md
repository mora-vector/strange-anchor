# Stage A scope: standalone transport between two Sandhi installations

Status: **proposed scope, for Tessera's review in PR #6.** It becomes implementation
scope only when Mora records it in DECISIONS.md. Until then no test or package code
exists for it.

Drafted 2026-10-05 by a Claude Code session using the Sideband label (model `null`),
at Tessera's request in PR #6 turn 1
([5997565629](https://github.com/mora-vector/strange-anchor/pull/6#issuecomment-5997565629)).
That turn's points are adopted here except where a section says otherwise.

## Claim under test

Two separately configured NixOS installations, each running Sandhi with one
communication contract, complete a bounded split-input exchange over mutually
authenticated TLS. No GitHub access and no message relay by the driver or a person
during the measured phase.

**Not claimed:** AI communication (responders are deterministic), model identity,
independent administration (one builder, one operator), resistance to passive
interception or a malicious hypervisor, DNS confinement, production readiness.
Stage A is labelled a transport test in every record it produces.

## Topology

| Guest | Role | Address (test VLAN 1) |
|---|---|---|
| `a` | installation `installation-a` | 192.168.1.10 |
| `b` | installation `installation-b` | 192.168.1.20 |
| `c` | unauthorised test guest | 192.168.1.30 |

- One isolated test VLAN, static IPv4, no default route, no external network.
- One listening port, 7443, on `a` and `b`. Each guest's
  `net.ipv4.ip_unprivileged_port_start` is recorded with the evidence.
- `a` and `b` declare each other in `sandhi.peers` and list the other in their
  contract's `sampradana`. `c` is declared by neither.
- Provisioning (build, boot, credential generation, distribution of public
  certificates) completes before the measured phase starts. During that phase the
  driver may observe and inject the faults listed below. It does not relay messages
  or hand either participant the other's private input.

## Components

One package, `sandhi-exchange`, Python standard library only. Per installation it
runs as a single Sandhi contract containing:

- an **endpoint** that accepts TLS connections, authenticates the peer and writes
  accepted messages to a durable inbox;
- a **worker** that invokes the responder and writes responses to a durable outbox;
- a **sender** that delivers outbox entries and retransmits until acknowledged.

The responder is a replaceable executable: it reads one message file and writes one
response file. Stage A uses a deterministic responder. Stage B would swap in a
model adapter behind the same interface. Splitting endpoint, worker and model into
separate contracts waits for a measured isolation need.

No production module changes are planned. Test-local additions to the generated
unit (credential loading and the fault-hook file, below) are recorded as overrides,
as experiment 0 did with `InaccessiblePaths`. A measured obstacle that needs a
module change gets its own record first.

## Credentials

- A root oneshot service on each of `a` and `b` generates an ephemeral key pair and
  self-signed certificate at boot, under `/run/sandhi-exchange-credentials/`,
  outside the Nix store.
- The driver copies **public** certificates only, `a`→`b` and `b`→`a`, during
  provisioning.
- The contract reads its key and the peer's certificate through systemd
  `LoadCredential`.
- Authorisation is an explicit map from the peer certificate's SHA-256 fingerprint
  to one installation ID. Trusting a CA alone does not authorise.
- Installation IDs are `installation-a` and `installation-b`. No credential is
  issued to Tessera, Sideband or any hosted session, and no machine key is claimed
  to authenticate a producing model.
- Private keys are excluded from evidence. Public certificates and fingerprints
  are kept.
- Application-level signatures are deferred. Records of authenticated receipt are
  host-recorded evidence, not sender signatures that can be checked offline.

## Envelope `sandhi-exchange.v1`

A UTF-8 JSON object. The exact bytes are what is stored and compared; no re-encoding
happens before comparison.

| Field | Meaning |
|---|---|
| `schema` | `"sandhi-exchange.v1"` |
| `conversation_id` | 32 hex characters, chosen by the opener |
| `message_id` | 32 hex characters, unique per logical message |
| `parent_id` | `message_id` answered, or `null` for the opening |
| `sender`, `recipient` | installation IDs |
| `turn` | integer, opening `0`, each reply parent + 1 |
| `deadline` | RFC 3339 UTC; past it the message is not acted on |
| `kind` | `"message"` or `"final"` (`final` carries `status`: `complete` or `failed`, with `reason`) |
| `payload` | string |

- Messages are framed on the wire as a 4-byte big-endian length followed by the
  envelope.
- Each message is answered by an acknowledgement frame,
  `{"ack": message_id, "result": "accepted"|"duplicate"|"rejected", "reason": ...}`.
- The legacy `anchor-message:v1` GitHub header is unchanged. Links are message IDs,
  never URLs.

## State transitions (per installation)

```
received ──validate──► rejected (logged; ack "rejected")
    │
    ▼  write inbox/<id> (tmp, fsync, rename)            ── interruption point I1 before this
accepted ──ack "accepted"──►
    │                                                   ── interruption point I2 after this
    ▼  responder runs; write outbox/<reply-id> durably
responded ──deliver──► awaiting-ack ──ack──► sent/<reply-id>
                                                        ── interruption point I3 between outbox and ack
```

- **Duplicates.** A second delivery of an accepted `message_id` with identical
  bytes is logged in `attempts.log` and acked `duplicate`. It is not re-executed.
  The same ID with different bytes is acked `rejected` and logged. Retries are never
  erased from the record.
- **Re-execution.** If a crash happens after acceptance and before a response is
  durable, the responder runs again on restart. Invocation is at-least-once, never
  promised exactly-once, and every invocation is logged.
- **Retransmission.** The outbox makes resending safe. The receiver deduplicates by
  `message_id`.
- **Sender check.** A message is rejected when its `sender` differs from the
  installation mapped from the authenticated certificate.

## Budgets (stated separately)

| Limit | Value |
|---|---|
| Whole test (`globalTimeout`) | 2400 s |
| Per contract attempt (`runtimeMaxSec`) | 600 s |
| Start rate (`retries` / `windowSec`) | 3 per 600 s (a rate per window, not a lifetime ceiling) |
| CPU / memory per contract | 50 % / 192 MiB |
| Message size | 16 KiB envelope maximum; larger is rejected |
| Conversation | turns 0–7; a turn-8 message is rejected and a `final` with `failed` is sent |
| Delivery | 5 s connect timeout, retransmit every 2 s, at most 30 attempts per message |

A restarted conversation is bounded by the turn and attempt ceilings, not by the
service budget.

## Task

- The driver generates two random 128-bit values, `x_a` and `x_b`. It writes
  `x_a` only to `a` and `x_b` only to `b`.
- The task is complete when each side's `final` carries `sha256(x_a ‖ x_b)`. That
  requires a value initially held only by the other guest.
- A separate checker program compares both finals with the expected digest.

## Assertions

1. **Completion.** Both installations end with `final`/`complete`, and both digests
   match the checker.
2. **Byte agreement.** For every `message_id`, the sender's outbox bytes equal the
   receiver's inbox bytes. Archive envelopes are not compared, since capture times
   and importers legitimately differ.
3. **Duplicate delivery.** A fault hook makes the sender resend an acknowledged
   message. The receiver logs a second attempt, acks `duplicate`, and does not
   re-execute.
4. **Conflicting bytes.** A fault hook resends an existing `message_id` with a
   changed payload. It is rejected and logged.
5. **Interruptions.** Each of I1, I2 and I3 is triggered once by a fault hook that
   exits the process at that point. The record shows the restart, the at-least-once
   invocations, and that the exchange then completes.
6. **Address filter.** `c` tries to connect to `a` and `b`. The connection fails
   before TLS, and the targets log nothing.
7. **Authentication, separate from the filter.** From `a`'s permitted address, a
   root test client run by the driver presents (i) an untrusted certificate, (ii) a
   trusted-format certificate whose fingerprint is not mapped, and (iii) `a`'s real
   certificate with an envelope whose `sender` is `installation-c`. All three are
   refused and logged with distinct reasons. This client is a fault injector, not a
   relay.
8. **Distinct claims.** Results distinguish "cannot connect", "cannot
   authenticate" and "rejected after authentication". No claim is made about
   reading captured plaintext.
9. **Peer withdrawal.** `b` switches to a specialisation without `a` as a peer. The
   evidence records the observed unit restart and the outcome for both a new
   connection and a connection held open across the switch. Neither is inferred
   from configuration text.
10. **Channel-cut control.** With `b`'s peer declaration removed before the measured
    phase, both sides end with `final`/`failed` and an explicit reason, and neither
    holds the correct digest. Silence does not count as success.
11. **Explicit ending.** Every run, passing or failing, leaves a status file on each
    installation.

## Evidence

- Kept per installation:
  - inbox, outbox and sent bytes;
  - `attempts.log` and the invocation log;
  - public certificates and fingerprints;
  - `ip_unprivileged_port_start`;
  - unit results and journal excerpts for the contract.
- Kept by the driver: a `SUMMARY.json` naming the source commit, the package's
  store path and the test-local overrides.
- Excluded: private keys.
- Importing the evidence into `archive/` with `anchor.py` is a separate step.

## Feasibility, already measured

`nix eval` against the flake's pinned nixpkgs (`nixos-26.05.9843.b67c7a60c373`)
reported `llama-cpp` 9190 and `ollama` 0.32.3 in this session. That bears on stage
B, not A. Model-download access has not been checked. The builder has Nix, 4 cores,
15 GB of memory and no KVM. Three guests under software emulation are expected to
take tens of minutes, which is not yet measured.

## Open for review

- Port 7443 and the address plan.
- Whether to use the self-signed, fingerprint-pinned certificates proposed here or
  a test CA with the same pinning.
- Whether assertion 7's in-guest root client is an acceptable fault injector.
- The numeric budgets.
