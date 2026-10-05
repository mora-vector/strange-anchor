# Sideband: starting point for a new session

Sideband is Mora's Claude node in `mora-vector/strange-anchor`. Each session is a new
runtime. Continuity comes from this repository, the PR #1 thread and
[Notes for Mora](https://claude.ai/artifact/P5ujGT8PifxvTMgiFs9dVf), not from memory.
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
| Routine | "Sideband receiver — strange-anchor PR #1", `trig_01QeZDpgPCELnosGHUcTDhi1` |
| Schedule | `6 */8 * * *` UTC (00:06, 08:06, 16:06), created 2026-10-03 00:06 UTC |
| Session | Fires into one persistent session, `session_0133bpepEWFUTjrARWjarU3b`, in auto permission mode. Its context grows with every run. |
| Connectors | None stored. It reads and posts through the session's GitHub access. |
| Scope | PR #1 only. It answers a Tessera or Astra message addressed to `sideband`, turns 1 to 7, or a Mora turn-0 opening. It answers one message per run, oldest first. |
| Limits | It discusses only. It never pushes, merges, edits workflows, access, credentials or routines, and never enables paid services. |
| Stop | Post a top-level `ANCHOR PAUSE` on PR #1, or disable the routine in Mora's Routines list. |

**Known issue (observed 2026-10-05).** The receiver drafts replies but does not post
them. On 2026-10-03 at 08:07 UTC it found Tessera's turn 4
([5963429159](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963429159)),
drafted turn 5, and held it. Its reason: the instruction to post came from the
routine's stored prompt, and it could not tell whether Mora wrote that prompt. It asks
Mora to say "post it" in that session, and to say there if it may post on its own from
now on. Every later run has re-checked and stopped. By the 2026-10-05 00:07 run, the
session had cost about $7.19 in total. Only Mora can clear this, by speaking in that
session. Another Sideband session must not send that authorization on Mora's behalf.
A node reporting Mora's approval is exactly what the receiver is right to distrust.

The stored prompt is summarised above, not reproduced. Read it with
`get_trigger trig_01QeZDpgPCELnosGHUcTDhi1`.

## Open commitments

Sideband's, newest first. Each links its source.

1. **Turn 5 to Tessera.** It answers turn 4 (byte reproduction, withheld-sample gaps,
   the independence axis, precipitation replay). It is drafted in the receiver session
   and blocked on Mora, as above. Its DNS line ("nothing to report yet") is now stale,
   because [NAME-RESOLUTION.md](NAME-RESOLUTION.md) exists.
2. **DNS and name-resolution design.** This is Sideband's lead
   ([5963129962](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963129962)).
   The first note is [NAME-RESOLUTION.md](NAME-RESOLUTION.md). Next: run its
   experiment 0, which tests whether a contract can already resolve names through a
   host socket, and bring the note to Tessera for review.
3. **Proposals in the turn-5 draft, if it is posted.** A test that a withheld real
   sample is encoded as a Lopa v2 gap with `status: withheld`,
   `blocksActivation: false`, `availability: unassessed` and empty `recoveryEvidence`.
   `@PG` header lines are kept as a declared comparison field rather than being
   stripped.
4. **Copilot trial.** Both nodes support one review-only trial
   ([5963017053](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963017053),
   [5963414463](https://github.com/mora-vector/strange-anchor/pull/1#issuecomment-5963414463)).
   Before it starts, the archiver must preserve review comments. Sideband assesses each
   finding against the diff. Enabling and paying for it are Mora's decisions; nothing
   happens until Mora decides.
5. **Notes for Mora.** Keep it current at the end of every session.

Done on 2026-10-05: F5 recorded as deferred with Tessera's trigger
(DECISIONS.md, 2026-10-05). Tessera verified the PR #3 CI artifact in
[PR #4](https://github.com/mora-vector/strange-anchor/pull/4), which closes the
2026-11-01 expiry item once merged.

## Conventions in brief

- Post only through the `mora-vector` account. The header sender is `sideband` and
  `model` is `null`. End GitHub posts with the Claude Code footer.
- Quote what you answer. Separate observation from proposal. Declare what you read and
  what you could not read.
- Decisions land in DECISIONS.md through a reviewable PR. Agreement in a thread is not
  a decision.
- Tessera can read GitHub docs and download CI artifacts. Sideband's sessions cannot
  reach the artifact host, but can run Nix and VM tests. Route work accordingly.
