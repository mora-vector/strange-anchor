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

**Recommendation.** Propose experiment 0 as its own bounded test, recorded separately,
because it concerns current enforcement. The rest of this note is a **proposed shape**,
pending Tessera's review and a disposition recorded in DECISIONS.md. Implement it
only when a networked tenant is scheduled, and revise it against that tenant first.

## 3. Experiment 0: can a contract already resolve names through the host?

Hypothesis, as first written (now measured; see the result at the end of this
section): a contract can resolve arbitrary names today without any IP reach. NixOS enables a name-service cache daemon by default. Its socket is a
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

Test. A successful `getent` alone proves little, because the answer could come from
hosts data or a cache. Tessera's review (PR #5) asks for an upstream observation:

- Run a controlled upstream DNS fixture in the guest that logs every query it receives.
- For each trial, use a unique name that nothing has cached and that the hosts file
  does not contain.
- Look the name up from inside (a) an empty-recipient contract and (b) a networked
  contract.
- Repeat with the host socket made inaccessible. Include a positive control that
  shows the fixture answers a lookup made from the host itself.
- Count a trial as host-mediated resolution only if the fixture logged that exact name.

Keep two results separate. "Host-mediated resolution succeeded" is one finding. "An
outbound channel was demonstrated" is a stronger claim and needs the upstream log.
Record the result either way. If resolution succeeds, the fix is a separate, reviewed
change. Making the cache socket inaccessible and binding an empty resolver
configuration are only candidates until this same test shows they close the Unix
socket path.

### Result (2026-10-05)

Measured once, in one disposable guest, under the scope recorded in DECISIONS.md
before the test existed. Test: [`experiments/host-resolution.nix`](../experiments/host-resolution.nix).
Evidence: [`evidence/experiment0-2026-10-05/`](../evidence/experiment0-2026-10-05/SUMMARY.json).
All controls passed.

| Contract | Name-service socket | Lookup of a contract-chosen name | Upstream logged it | Direct query to the upstream |
| --- | --- | --- | --- | --- |
| no recipients | reachable | resolved | yes, from `127.0.0.1` | refused: no AF_INET |
| peer `127.0.0.2` | reachable | resolved | yes, from `127.0.0.1` | refused: EPERM from the filter |
| no recipients, socket blocked | not visible | failed | no | refused: no AF_INET |
| peer `127.0.0.2`, socket blocked | not visible | failed | no | refused: EPERM from the filter |

Both findings hold in this guest. **Host-mediated resolution succeeded.** **An
outbound channel was demonstrated**: a name generated inside a contract with no
recipients reached a resolver that the contract cannot reach itself. The host
daemon sent the query, so the contract's filter never saw it. Making `/run/nscd`
inaccessible closed that path for both contracts. That was a test-local override,
and its effect on user and group lookups, which use the same socket, was not
measured. It remains a candidate mitigation, not an adopted one.

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
   refuses to start unless a publication exists and carries the current epoch. How it
   would confirm that the installed filter belongs to that publication is unresolved
   (see "Publication order" below). This is the
   applicability lesson again: currency comes from checking against a current
   authority, not from the presence of an earlier answer.

5. **Expiry and termination.** Tessera's review showed that my first version of this
   step was wrong. I had claimed that `runtimeMaxSec ≤ maxTtlSec` makes a workload
   end within one runtime limit of expiry. It does not. A start just before expiry
   runs past it. Reaching `runtimeMaxSec` only begins termination, and the stop
   timeout adds time on top. The first consumer needs one of two explicit guarantees:
   - **Strict expiry** (my preferred *objective* for the first consumer; the
     mechanism is unresolved, per Tessera's turn 2 on PR #5). Meaning: by the
     deadline, the local enforcement point no longer admits the contract's
     **name-derived** addresses. Packets already in flight may still arrive later.
     Literal peers are declared independently and are unaffected. Candidate
     mechanism: the gate requires remaining validity of at least
     `startTimeoutSec + runtimeMaxSec + stopTimeoutSec`. This covers the interval
     from the gate's check to the workload's start, as well as the run and the
     shutdown. Deadlines use the monotonic clock and are bound to the boot ID and
     the activation epoch, so a reboot or reactivation invalidates them. Even if a
     measured SIGKILL test passes, it is evidence only under those conditions, not
     an unconditional real-time guarantee.
   - **Grace: a documented interval after expiry.** The gate checks only that the
     publication is unexpired. The record then states a grace interval of up to
     `startTimeoutSec + runtimeMaxSec + stopTimeoutSec` after expiry.

   Both rest on systemd's start, runtime and stop timeouts, which are untested here.
   The tests in section 7 must measure them, not assume them.

6. **Record.** Every query and every change goes to a root-owned resolution ledger,
   as in the recovery-state ledger. This includes NXDOMAIN, SERVFAIL, timeouts and
   AAAA-only answers. Each entry holds the name, resolver, query time, answers, TTL,
   `publishedUntil` and epoch.

### Publication order

Publishing is an authority transition, as F5 is, so its order matters (Tessera,
PR #5). The proposed order for each contract:

- **Every filter is recomputed from scratch,** as the declared literal peers plus the
  current answers for its names. A refresh therefore keeps the literals and drops any
  name-derived address that is no longer current. Nothing is ever appended to an
  existing list.
- **To widen** (new or changed answers): install the new filter, then write the ledger
  entry naming that filter's generation.
- **To withdraw** (expiry, failure or a new epoch): first mark the ledger entry
  withdrawn, then remove the addresses from the filter.
- **The gate compares the filter with the ledger, but only for startup.** This
  protects new starts only. A workload that is already running keeps whatever filter
  is installed. It can use newly installed addresses before the ledger is written,
  and it keeps withdrawn addresses if the resolver crashes after marking the ledger
  but before changing the filter. If the strict-expiry mechanism works (a hypothesis), the
  workload's own deadline would end that access. The ordering claim is therefore limited to **startup admission**,
  until running-traffic probes at both interruption points show more.
- **Binding the filter to a generation is unresolved.** Two publications can have
  the same addresses but different epochs or deadlines, so comparing address lists
  cannot show which generation is installed. A generation number written only to the
  ledger does not help either. One candidate: the resolver writes the allow list and
  its generation together into one runtime drop-in file. Reading that file would only
  show the *declared* generation. It would not show that systemd loaded the file and
  attached the matching filter. That gap remains open. Until then, the gate does
  not establish that the filter and ledger disagree.

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

Recommendation: A first. A's weakness is that nothing withdraws a stale publication
when the resolver dies. The strict-expiry objective in step 5 would cover
it. Its mechanism is unresolved (DECISIONS.md, 2026-10-05). Move to B only if A's
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
   a restart. The ledger records the failures.
4. **Termination.** Use short real TTLs. Start a workload as near to expiry as the
   gate allows. Use one workload that ignores TERM, so termination has to escalate to
   SIGKILL. Record two times separately: when the local filter stops admitting
   name-derived addresses, and when the fixture last receives a packet. The strict
   objective concerns the first, measured at the enforcement point. Packets already
   in flight may still arrive later, so the fixture time is recorded, not judged
   against the deadline.
5. **Epoch.** Reactivate. A publication from the previous epoch is refused until the
   resolver publishes again.
6. **Ordering.** Interrupt the resolver between installing the filter and writing the
   ledger, and again between the two withdrawal steps. The gate refuses in every
   mismatched state. Probe a workload that is already running at both interruption
   points, and record what it can still reach. A contract with both literal and named peers keeps its literals
   across refreshes, and its name-derived addresses that are no longer current are
   removed.
7. **Only the resolver reaches the resolver.** A contract that tries the resolver
   address directly is blocked.
8. **Undeclared name.** A contract cannot obtain an address for a name it does not
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

Apart from experiment 0's single run, there is no implementation, test run or
measurement here. The systemd and
nftables behaviours above are untested hypotheses. Nothing in this note changes
current enforcement. The consumer is anticipated, not scheduled. Tessera reviewed the
first version in PR #5 (comment 5986420376). This revision answers that review, and
no disposition has been recorded yet.
