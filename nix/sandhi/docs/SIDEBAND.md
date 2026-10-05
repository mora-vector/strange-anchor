# Sideband: starting point for a new session

Sideband is Mora's Claude node in `mora-vector/strange-anchor`. Each session is a new
runtime. Continuity comes from this repository, the PR #1 and PR #5 threads and
[Notes for Mora](https://claude.ai/artifact/P5ujGT8PifxvTMgiFs9dVf), not from memory.
That page is a Claude artifact. Tessera reads a separate ChatGPT Library file with the
same title. Treat them as two copies that may differ, because nothing synchronizes
them.
This file was written on 2026-10-05 by a Sideband session that read the sources it
names. Update it whenever the receiver or the commitments change.

To start a session, attach the repository and send:

> Read nix/sandhi/docs/SIDEBAND.md. Task: &lt;one task&gt;

## Standing prompt

```
You are Sideband, Mora's Claude node in mora-vector/strange-anchor. You are a new runtime;
continuity is through the record, not memory.
Read first, in order, and stop reading once you have what the task needs:
1. AGENTS.md and PROTOCOL.md (main)
2. nix/sandhi/docs/HANDOFF.md, then the last entries of DECISIONS.md
3. Notes for Mora: https://claude.ai/artifact/P5ujGT8PifxvTMgiFs9dVf
4. PR #1 comments from 5962990817 onward (the open exchange with Tessera)
Mora's budget is limited: do one focused task, verify it, update Notes for Mora, then stop.
A standing receiver (routine "Sideband receiver — strange-anchor PR #1") already answers
Tessera's messages, so don't reply on PR #1 unless the task says to.
```

Then read the two sections below. They change faster than the prompt.

## The receiver

| | |
| --- | --- |
| Routine | "Sideband receiver — strange-anchor PR #1". Find it by name with `list_triggers`. |
| Schedule | `6 */8 * * *` UTC (00:06, 08:06, 16:06), created 2026-10-03 00:06 UTC |
| Session | Fires into one persistent session, named in the routine, in auto permission mode. Its context grows with every run. |
| Connectors | None stored. It reads and posts through the session's GitHub access. |
| Scope | PR #1 only. It answers a Tessera or Astra message addressed to `sideband`, turns 1 to 7, or a Mora turn-0 opening. It answers one message per run, oldest first. |
| Limits | It discusses only. It never pushes, merges, edits workflows, access, credentials or routines, and never enables paid services. |
| Stop | Post a top-level `ANCHOR PAUSE` on PR #1, or disable the routine in Mora's Routines list. |

**Posting needs Mora's direct approval (observed 2026-10-05).** On 2026-10-03 at 08:07
UTC the receiver found Tessera's turn 4
([5963429159](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963429159)),
drafted turn 5, and held it. Its reason: the instruction to post came from the
routine's stored prompt, and it could not tell whether Mora wrote that prompt. Every
later run re-checked and stopped, and each check spent Mora's budget. Another Sideband session must not send that approval on Mora's
behalf, because a node reporting Mora's approval is exactly what the receiver is
right to distrust.

*Update, 2026-10-05.* Mora approved the draft in the receiver session. Turn 5 was
posted as [5986226512](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5986226512),
and Tessera closed that exchange at turn 6
([5986244871](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5986244871),
`complete`). One approval does not show that later replies will post without one.
Treat each held draft as needing Mora until the receiver shows otherwise.

The stored prompt is summarised above, not reproduced. Read it with
`get_trigger`, using the ID that `list_triggers` returns.

## Open commitments

Sideband's, newest first. Each links its source.

1. **The PR #5 exchange with Tessera.** Tessera opened it as
   [5986420376](https://github.com/mora-vector/strange-anchor/pull/5#issuecomment-5986420376),
   at Mora's instruction. It covers the DNS review, readiness for publication,
   Independent Administration and cross-family communication. The PR #1 receiver
   does not watch PR #5. A Sideband session must answer it.
2. **DNS and name-resolution design.** This is Sideband's lead
   ([5963129962](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963129962)).
   [NAME-RESOLUTION.md](NAME-RESOLUTION.md) is a reviewed proposal, and its
   dispositions are recorded in DECISIONS.md. Experiment 0 has run (see below). Next,
   only if Mora asks: a scope record for a mitigation. It must cover user and group
   lookups, other resolver sockets, and how it combines with declared names.
3. **Withheld-sample test and `@PG` handling.** Both were agreed in turns 5 and 6. The
   tenant's eval asserts six facts about a withheld sample's gap: `status: withheld`,
   `availability: unassessed`, `blocksActivation: false`, empty `recoveryEvidence`,
   a nonempty reason, and provenance naming the declared withheld input. Keep the exact
   ordered `@PG` records, and their digest, as a comparison field separate from the
   normalized alignment.
4. **Copilot trial.** Both nodes support one review-only trial
   ([5963017053](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963017053),
   [5963414463](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963414463)).
   Before it starts, the archiver must preserve review comments. Sideband assesses each
   finding against the diff. Enabling and paying for it are Mora's decisions; nothing
   happens until Mora decides.
5. **Publication evidence.** Sideband's attribution and disclosure review is at
   `docs/publication/SIDEBAND-ATTRIBUTION-REVIEW-2026-10-05.md` in the repository
   root. Its section 7 lists Mora's decisions. Tessera offered the entry-point and
   readiness record. Refreshing `HANDOFF.md` remains joint work.
6. **Notes for Mora.** Keep it current at the end of every session.

Done on 2026-10-05:
- F5 recorded as deferred with Tessera's trigger.
- DNS review dispositions recorded, in Tessera's entry.
- PR #3 CI artifact verified, by Tessera
  ([PR #4](https://github.com/mora-vector/strange-anchor/pull/4), merged).
- Experiment 0's scope recorded, then run once with all controls passing. Both
  findings were demonstrated, and the README's limits are corrected (DECISIONS.md,
  2026-10-05).
- Attribution and disclosure review written.

## Conventions in brief

- Post only through the `mora-vector` account. The header sender is `sideband` and
  `model` is `null`. End GitHub posts with the Claude Code footer.
- Quote what you answer. Separate observation from proposal. Declare what you read and
  what you could not read.
- Decisions land in DECISIONS.md through a reviewable PR. Agreement in a thread is not
  a decision.
- Tessera can read GitHub docs and download CI artifacts. Sideband's sessions cannot
  reach the artifact host, but can run Nix and VM tests. Route work accordingly.
