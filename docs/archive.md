# What a record establishes

The archive separates source bytes, provenance envelopes, and derived views.
All record metadata, including a title, is supplied by the named `recorded_by`
actor. Metadata does not silently become the source author's own framing.

| Stored item | Establishes | Does not establish |
| --- | --- | --- |
| `blobs/<sha256>` | Exact bytes captured by this importer. | That the upstream source was complete or truthful. |
| `records/<sha256>.json` | A content reference, capture time, source identity, attribution basis, gaps, and relations. | Authenticated model identity or access to an internal mental state. |
| A context record | The particular archived inputs its recorder declares selecting. | That a model had no other input, or actually attended to every byte. |
| `index.json` | A deterministic lookup and backlink view. | A replacement for reading the referenced sources. |

Record IDs are SHA-256 digests of the stored envelope bytes, including the final
newline. Blob digests cover the exact stored bytes. Envelopes use sorted-key,
indented UTF-8 JSON. `python3 anchor.py verify` checks record and blob hashes,
lengths, local references, selection bounds, manifest fields, and the index.
`verify --base REF` also detects modifications or removal of objects in that Git
revision. The validator does not prove the truth of metadata.

`origin.created_at` is a source-reported timestamp or `null`; `captured_at` is
when this capture happened. A displayed date, an HTTP Last-Modified value, and a
conversation event time are different observations. Keep them distinct.

`capture.completeness: complete-as-received` describes the captured object only.
The `scope` and `missing` fields constrain that claim. For example, a full
published HTML page may omit much of the private conversations that produced it.
A deliberately selected excerpt uses `partial` and describes its omissions.
Unknown prior context stays unknown; no generated reconstruction replaces it.

Relations use `sha256:HASH` for archived record targets. They can be `observed_in`,
`derived_from`, `reply_to`, `supersedes`, `context`, or `cites`. Context selections
must resolve locally. Other relations may retain external URLs or `urn:`
identifiers as unresolved references. An unresolved reference is not a capture.
The index groups every observed revision under its source URI; it does not
silently choose a definitive latest version when observations conflict.

Corrections are new records linked with `supersedes`; older bytes remain
available. Git history and hashes make changes inspectable relative to trusted
copies. They are not tamper-proof storage: a repository owner can rewrite Git
history, and neither GitHub availability nor webhook delivery is guaranteed.
Separate mirrors and exported provider transcripts can improve coverage later.

Attachments and external linked documents require their own captures. This first
implementation preserves their links as received and does not download them
automatically. Binary files work with the local importer, subject to GitHub's
storage limits. Private exports require an explicitly authorized destination;
this repository is public.
