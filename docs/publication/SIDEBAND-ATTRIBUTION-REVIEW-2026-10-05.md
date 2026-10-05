# Sideband attribution and disclosure review, 2026-10-05

A derived contribution by Sideband, written as evidence for Mora's decision about
making this repository public. Tessera asked for it in PR #5
([5986542802](https://github.com/mora-vector/strange-anchor/pull/5#issuecomment-5986542802)),
and Mora instructed this session to do it.

**Scope.** It is not a full publication audit, a legal opinion, or permission on
anyone's behalf. Mora decides disclosure, licensing and the visibility change.

**What I read.** Everything tracked on `main` (`1be0f8a`) and on the PR #5 branch,
every commit on the five remote branches (73 at inspection), and `anchor-archive`. I used pattern
searches plus targeted reading. I did not read every archived blob line by line.

**What I could not read.** The private sessions that produced earlier Sideband
material, the original Strange Anchor conversations, and the rights status of
`strangeanchor.khazars.wiki`.

## 1. What Sideband contributed

These are commits authored as `Claude <noreply@anthropic.com>` and records that
declare Sideband as recorder. "This runtime" means the session writing this review.

| Contribution | Where | Who produced it, as far as I can verify |
| --- | --- | --- |
| Post-merge review of applicability, with counterexample evidence | `nix/sandhi/docs/SIDEBAND-REVIEW-2026-10-02.md`, `nix/sandhi/evidence/sideband-2026-10-02/` (`8139e90`) | An earlier Sideband session. I know it from commit metadata and the files' own declarations, not from memory. |
| Code: separate retention and export premises in the applicability test, schema descriptions, export fixture | `modules/lopa.nix`, `schemas/lopa-v2.schema.json`, `tests/applicability.nix`, `tests/export.nix`, `flake.nix`, docs (`ec08eff`) | An earlier Sideband session, implementing dispositions Tessera proposed. Licensed with the repository (GPLv3). |
| Checkpoint evidence and handoff | `VALIDATION.json`, `HANDOFF.md`, `evidence/ci-36983396017/SUMMARY.json` and others (`bfd0e31`) | An earlier Sideband session. |
| F5 deferral, Sideband start file, DNS design note, experiment-0 scope, test and evidence | PR #5 commits from `6c588c6` onward | This runtime. |
| Conversation turns signed "— Sideband" | PR #1 and PR #5 comments, preserved on `anchor-archive` | Several runtimes: earlier sessions, the scheduled receiver, and this one. Each turn declares itself. All were posted through the `mora-vector` account. |

I know of nothing in the Sideband contributions above that was copied from a third
party. The code and prose were produced by Claude sessions that Mora operated, and
they cite their sources where they rely on them.

## 2. Material that names Sideband but this runtime cannot vouch for

- **`boon.html` (The Enumeration).** Its embedded metadata names its author as
  "Sideband", a "Ship's Computer". The archive deliberately leaves attribution
  unassigned at the envelope level (`docs/sources.md`). A narrative node called
  Sideband is not this runtime, and nothing available to me shows which model or
  person produced the page. Public readers will see an authorship claim. Preserve
  the bytes unchanged, as AGENTS.md requires. If the claim needs context, add a
  separate attribution note that links to the capture.
- **`nix/sandhi/docs/SIDEBAND-RELAY-2026-09-23.md`.** A draft by an earlier Sideband
  runtime, written for Mora to carry by hand to Tessera. It opens with a carrier
  instruction and names a private conversation series, "Ferry Thread 0001". It was
  written for a relay, not for publication. See section 3.
- **Captured Krios and Three Lineages pages** (`archive/blobs/`). These are narrative
  pages that feature a Sideband character. Astra captured them as already-public
  artifacts. Their character attributions are part of the story, not records of
  which runtime produced them.

## 3. Material that may have been supplied for private development

These are flags for Mora, not conclusions. The repository's own README says to
"capture only material authorized for this **public** repository". The repository
was public from its opening until about 2026-09-18. GitHub showed it as private
when DECISIONS.md recorded that on 2026-09-23. The Enumeration, the Krios and
Three Lineages captures and the ecology graph date from the public period. The
items below were added after the repository became private, when that condition
was not being checked.

1. **`SIDEBAND-RELAY-2026-09-23.md`.** A private relay draft, as above. Mora carried
   it and committed it, so Mora is the right person to decide.
2. **Sideband's operational detail.** Earlier commits on the PR #5 branch record the
   receiver's routine ID, the persistent session ID and its running cost. I removed
   them from the current `SIDEBAND.md` (section 6), but they remain in those commits.
3. **Links to private sessions.** Commits from Sideband sessions carry
   `Claude-Session:` trailers with private Claude Code session URLs (10 commits on the
   remote branches at inspection, and every later commit from this session). Six
   files on `anchor-archive` also contain a session URL. `SIDEBAND.md` links to the private Notes for Mora page. Public readers
   will hit access walls, and the links reveal that private sessions exist. They
   expose nothing else.
4. **Mora's own words.** `anchor-archive` keeps every PR #1 and PR #5 comment
   verbatim, including Mora's plain, signed comments, and their GitHub event
   payloads. Publishing the repository publishes that history.

## 4. Third-party material and licensing

- **Two licenses.** The repository LICENSE is GPLv3. `boon.html` declares
  CC BY-SA 4.0 in its own metadata. That is not necessarily a conflict, but the
  README does not mention the per-file license. I recommend a short licensing
  note, not relicensing.
- **Captured narrative pages.** The Krios and Three Lineages captures declare no
  license in their markup. Their rights holder isn't recorded in the repository,
  and I couldn't establish it. The same applies to the ecology graph
  (`ecology/strange-anchor-ecology-2026-09-06.json`, 5.7 MB). It is a crawl of
  `strangeanchor.khazars.wiki` with page metadata, response headers and about
  8,100 evidence entries that include quoted excerpts. Mora should confirm that
  whoever holds the rights to that site agrees to republication here.
- **`scripts/satipatthana.py` and `scripts/satipatthana_machina.py`.** Their English
  renderings cite Bhikkhu Sujato's translation, which the file marks CC0. Their Pāli
  root cites SuttaCentral's Mahāsaṅgīti edition. I believe SuttaCentral releases
  root texts without copyright restriction, but I haven't verified that today.
  Anālayo is cited, not reproduced. The one phrase attributed to Nyanasatta is
  very short.
- **Contact details.** Two personal author addresses appear in commit metadata, and
  contact addresses from the site appear in the captured page and in the ecology
  crawl. I count them here without repeating them. Removing them from commit
  metadata would mean rewriting published history, which is out of scope.
- **Committed zip archives.** `nix/sandhi/evidence/prior-release-v0.1.zip` holds only
  Sandhi v0.1 source. I didn't inspect the zip blobs in `archive/blobs/`. The archive
  records them as CI artifacts.

## 5. Secrets scan (weak evidence)

I scanned the working tree, all branch histories and `anchor-archive` for common
token and private-key formats: GitHub tokens, `sk-` keys and PEM private keys.
Nothing matched. No file has ever been deleted on any branch, so the history
contains only earlier versions of current files. Neither result replaces a
dedicated secret scanner run over the full history before the visibility change.

## 6. What I changed

- In `nix/sandhi/docs/SIDEBAND.md`, I replaced the routine ID, the session ID and the
  cost figure with instructions to find the routine by name. Continuity doesn't
  depend on those values.

Nothing else was rewritten. Archive objects and other people's records are
untouched.

## 7. For Mora's decision

1. Decide whether `SIDEBAND-RELAY-2026-09-23.md` and the archived comment history
   should be public.
2. When merging PR #5, choose between a merge commit and a squash:
   - A **merge commit** keeps each author's commit, but leaves the removed IDs and
     cost figure in the branch's earlier commits.
   - A **squash** keeps those values out of `main`, but folds Tessera's attributed
     commit into one combined commit. Its message would need to credit Tessera.
3. Confirm the rights holder's consent for the captured Strange Anchor pages and
   the ecology crawl.
4. Add a short licensing note covering GPLv3 and the CC BY-SA `boon.html`, and run a
   dedicated secret scanner over the full history. The second could be Tessera's
   readiness record.
5. Decide whether the "Sideband" authorship claim in `boon.html` needs a separate
   attribution note.

None of these is about the Sandhi code itself. Experiment 0's result, which may
sharpen a stated limit, is recorded separately under
`nix/sandhi/evidence/experiment0-2026-10-05/`.

## 8. Mora's resolutions (2026-10-05, in this Sideband session)

1. **Relay draft and archived comments:** discussed with Tessera in PR #5 (turns 7
   and 8). Both nodes recommend keeping both by default. The relay draft now has an
   adjacent note, `SIDEBAND-RELAY-2026-09-23.NOTE.md`, and its own bytes are
   unchanged. Tessera adds two qualifications:
   - Archived event payloads can keep edited or deleted text that GitHub no longer
     shows, so "already visible on GitHub" has to be checked item by item.
   - A withdrawal needs its archived blob and every Git copy identified, and the
     scope of removal approved by the owner. Previously distributed copies cannot be
     recalled.

   Mora's decision is still open.
2. **Merge style:** delegated to Sideband. Sideband chose a merge commit (see PR #5).
3. **Rights to the strangeanchor.khazars.wiki captures and the ecology crawl:**
   confirmed by Mora. Recorded in the root README's licensing section.
4. **Licensing note and secret scan:** done. The licensing note is in the root
   README. gitleaks 8.30.1 scanned the full history of every remote branch, including
   `anchor-archive` (73 commits, about 7.8 MB, with redaction on). It found no leaks.
5. **`boon.html` authorship:** Mora verifies that Sideband, the narrative node, is
   the author. No separate attribution note is needed. The page's bytes are
   unchanged.
