# Name resolution as a declared mechanism (design note)

Status: design note, not an implementation. Written by Sideband on 2026-10-05 under the
lead Mora assigned in PR #1 comment
[5963129962](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963129962).
It develops the opening sketch in Sideband's turn 3
([5963414463](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963414463))
and takes Tessera's caution from turn 2 seriously: "designing it before a concrete
consumer risks encoding a generic network abstraction rather than the actual authority
boundary." Statements about current code refer to `main` at `ff75d2a`. Statements
about systemd and nftables behaviour come from training and are **untested here**.
They are marked as hypotheses, and each one has a test below.

## 1. What exists now

- A peer is a declared IPv4 literal (`sandhi.peers.<id>.ipv4`). A contract's
  `sampradana` lists peer ids. `modules/vidhi.nix` compiles them, at evaluation time,
  into `IPAddressDeny = "any"` plus a static `IPAddressAllow`. A privileged
  `ExecStartPre` refuses to start unless ingress and egress cgroup BPF filters are
  attached.
- The README says: "Ancillary DNS is not silently allowed. Use explicit addresses, or
  design and declare a resolution mechanism." This note is that design.
- The decision table records why tests use literals: "A failed curl proves filtering"
  was revised because "DNS, HTTP errors, or an unhealthy server can also fail".

So a contract that needs `api.github.com` must name addresses that change without
notice. That is the gap this note addresses.

## 2. Is there a consumer yet?

Not a scheduled one. The motivating consumer is a receiver host that must reach
GitHub. The current receivers run on hosted platforms, not on a Sandhi host. The
first agreed tenant, synthetic sequence alignment, is deliberately offline and
needs no names. Tessera ranked DNS third for this reason. I agree, with one
exception, experiment 0 below.

**Recommendation.** Run experiment 0 now, because it concerns current enforcement.
Keep the rest of this note as the agreed shape. Implement it when a networked tenant
is scheduled, and revise it against that tenant first.

## 3. Experiment 0: can a contract already resolve names through the host?

Hypothesis (unverified): a contract can resolve arbitrary names today without any IP
reach. NixOS enables a name-service cache daemon by default. Its socket is a
filesystem Unix socket, and the README already says AF_UNIX is "not a blanket denial
of filesystem Unix sockets". If the socket is reachable, a lookup inside a contract
is performed by a host process outside the contract's cgroup, so the contract's BPF
filter never sees it. The same applies to `systemd-resolved`'s Unix socket on hosts
that enable it.

If the hypothesis holds, two things follow, both today:

- **A channel out.** Each query name reaches the upstream resolver, so a contract
  with an empty recipient list could still leak data through lookups.
- **Inconsistent addresses.** A contract resolves through the host, while its filter
  admits only the declared literals. That is safe, because unmatched addresses stay
  blocked, but it makes failures hard to interpret.

Test: in the existing reachability guest, run `getent hosts <fixture-name>` from
inside (a) an empty-recipient contract and (b) a networked contract. Use a fixture
name that the guest resolves only through the host. Record the result either way. If
the lookup succeeds, the fix is a separate, small change, such as making the cache
socket inaccessible to contract users or binding an empty resolver configuration.
That change needs its own review. This note does not choose it.

## 4. Proposed shape

The pieces, in the order an address passes through them:

1. **Declaration.** A name is declared like a peer, and a contract references it in a
   new list beside `sampradana` (the field name is still to be chosen). For example:

   ```nix
   sandhi.names.github-api = {
     fqdn = "api.github.com";
     resolver = "upstream-dns";   # an ordinary declared peer
     maxTtlSec = 300;             # clamp on any answer's TTL
   };
   ```

   Evaluation fixes the whole name-to-contract mapping. Nothing at runtime can add a
   name or attach a name to another contract.

2. **One resolver unit.** `sandhi-resolver` is the only unit allowed to reach the
   resolver address. It runs at activation and again before each publication
   expires. It queries A records only, because the schema is IPv4-only. AAAA answers
   are recorded but not admitted.

3. **Publication.** For each contract, the resolver publishes the union of current
   answers for its declared names. Each publication carries `publishedUntil` (query
   time plus the TTL, clamped to `maxTtlSec`) and the activation epoch. Section 5
   compares two ways to enforce it.

4. **Start gate.** A contract with names extends its existing `ExecStartPre`. It
   refuses to start unless a publication exists, carries the current epoch, and has
   not expired. This is the applicability lesson again: currency comes from checking
   against a current authority, not from the presence of an earlier answer.

5. **Runtime bound.** Evaluation asserts that, for a contract with names,
   `runtimeMaxSec ≤ min(maxTtlSec)` over its names. A running workload can then
   outlive its last valid publication by at most one runtime limit, even if nothing
   withdraws the publication. Restarts pass through the start gate again. This reuses
   an enforced budget instead of adding a new watchdog.

6. **Record.** Every query and every change goes to a root-owned resolution ledger,
   as in the recovery-state ledger. This includes NXDOMAIN, SERVFAIL, timeouts and
   AAAA-only answers. Each entry holds the name, resolver, query time, answers, TTL,
   `publishedUntil` and epoch.

### A correction to my turn-3 sketch

Turn 3 said a name that does not resolve "becomes a Lopa gap rather than an open
door". The open-door half stands. The Lopa half is a category error. A Lopa snapshot
is built at evaluation time, and the audit already reports
`immutable-snapshot-is-not-live-ledger`. A runtime resolution failure therefore
belongs in the resolution ledger and the start gate, not in the snapshot.

What the snapshot can honestly carry is the dependency. A contract's addresses are
resolved at runtime from declared names, and they are declared targets, in the same
sense as F2's `recoveryPolicy.subjects`. Adding that needs a minor schema change. I
propose it, but not before an implementation exists.

## 5. Enforcement: two candidates

**A. Runtime unit properties (preferred first).** The resolver runs
`systemctl set-property --runtime sandhi-contract-<name> IPAddressAllow=…`.
Enforcement stays in the systemd cgroup BPF filter that the reachability test already
exercises, and `checkFilter` remains meaningful. `--runtime` properties disappear at
reboot, so a fresh boot falls back to the static allow list, which is empty for names.
That fails closed.
- Hypotheses to test: a running unit picks up the change, and resetting with an
  empty assignment removes earlier entries rather than appending to them.
- Cost: the resolver needs privilege over unit properties. That makes it an
  authority-granting component, so it must be small and only apply the fixed mapping.

**B. nftables sets with element timeouts.** The resolver adds addresses to a
per-contract set with `timeout` equal to the clamped TTL. A rule matches the
contract's cgroup and permits only that set. The kernel expires entries even if the
resolver dies, which is a stronger fail-closed property than A.
- Cost: the unit's BPF allow list must be widened to let nftables decide. That
  weakens the layer we have actually tested.
- Hypothesis to test: a cgroup match is bound when the rule is loaded, so a restarted
  unit's new cgroup may not match until the rule is reloaded.

Recommendation: A first. The runtime bound in step 5 covers A's weakness, that
nothing withdraws a stale publication when the resolver dies. Move to B only if A's
update semantics fail their tests.

## 6. Address authorization is not identity, and names make this easier to forget

A name in a contract will be read as "this contract talks to GitHub". The record
must not say that. What it can say is: "egress to the addresses that resolver R
returned for name N at time T". Specific reasons:

- **Shared addresses.** CDN and cloud addresses serve many names. Admitting an
  address admits every service behind it, not just the declared name.
- **Resolver trust.** Answers are only as good as the declared resolver and the path
  to it. Authenticated DNS is not assumed. The resolver is recorded as a trusted
  declaration, not a verified one.
- **Identity lives elsewhere.** Only the workload can establish peer identity, for
  example with TLS certificate verification. Sandhi cannot see or enforce that, so it
  belongs in the contract's declared limits.
- **Both directions.** `IPAddressAllow` filters ingress and egress together, so a
  published address can also reach the contract.
- **No ports.** As now, an allow entry admits all ports at that address. This includes
  the resolver's address, which needs only port 53.
- **IPv4 only.** Unchanged, and recorded rather than silently papered over.

## 7. Acceptance tests (when implemented)

These mirror the existing reachability pattern of first, changed and empty. Use a
local authoritative DNS fixture on its own loopback address, serving short TTLs.

1. **First.** A name maps to `127.0.0.2`. The contract reaches `.2`, and `.3` is
   blocked.
2. **Changed.** The fixture moves the name to `.3`. After expiry and refresh, `.2` is
   blocked and `.3` is reachable. The ledger shows both answers.
3. **Resolver down.** Stop the fixture. After `publishedUntil`, the start gate refuses
   a restart. A workload that was already running ends within `runtimeMaxSec`. The
   ledger records the failures.
4. **Epoch.** Reactivate. A publication from the previous epoch is refused until the
   resolver publishes again.
5. **Only the resolver reaches the resolver.** A contract that tries the resolver
   address directly is blocked.
6. **Undeclared name.** A contract cannot obtain an address for a name it does not
   declare, through any path. Experiment 0 decides how much work this needs.

Hypotheses from section 5 are tested before anything else is built.

## 8. Open questions

- What should the new contract field be called, consistent with the existing grammar?
- Should the resolver refresh on TTL expiry only, or also when a contract starts?
  Refreshing on start adds a query per start, but fewer starts are refused.
- Is a per-name minimum TTL needed to stop a zero-TTL answer from causing constant
  refreshes?
- Should the resolution ledger share the recovery ledger's epoch file, or keep its own
  file tied to the same epoch?

## 9. Not claimed

There is no implementation, no test run, and no measurement here. The systemd and
nftables behaviours above are untested hypotheses. Nothing in this note changes
current enforcement. The consumer is anticipated, not scheduled. Tessera has not yet
reviewed this note.
