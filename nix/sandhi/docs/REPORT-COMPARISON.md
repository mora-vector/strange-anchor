# Explicit report comparison, version 1.0

`scripts/compare_reports.py SPEC REPORT_A REPORT_B ...` implements this opt-in
contract. The original `lib.saksya` remains compatible as a weaker reported
derivation/output comparison. Recorder reports (schema 5) are raw run records,
not automatically converted into comparison reports or independent attestations.

The specification supplies exactly:

* `schemaVersion`: `"1.0"`.
* `kind`: `"artifact"` or `"behavior"`.
* `subject`: an explicit derivation path for artifact comparison, or named,
  versioned assertion suite for behavioral comparison.
* `source`: `filesSha256`, `lockSha256`, and `system`.
* `requiredMembers`: the nonempty, unique output names or assertion IDs expected.

Define filesSha256 as SHA-256 of the UTF-8 encoding of the source-file digest map
serialized with sorted keys and JSON separators `(',', ':')`, without a newline.
Use paths relative to the Sandhi root. lockSha256 hashes exact flake.lock bytes.
The recorder supplies the map; inspect it before constructing a specification.
The tool compares these declarations; it does not independently reconstruct them.

Each report repeats schemaVersion, kind, subject, and source, then supplies:

* `builderId`, `administration`, and `runId`: nonempty declared identities.
* `cache`: `subject` must be `"rebuilt"`; `dependencies` is `"rebuilt"`,
  `"substituted"`, or `"mixed"`. Shared dependency binaries remain explicit.
* `evidence`: a nonempty `reference` and 64-character lowercase hex `sha256`.
* `observations`: exactly the required members. Artifact values contain `path`
  and SRI `narHash`; behavioral values must be boolean `true`.

Unknown fields/versions, invalid hashes, duplicate identities/runs, shared declared
administration, cached/unknown subject execution, missing provenance, incomplete
or extra inventories, source mismatches, changed bytes, or failed assertions hold
the comparison. Two equally incomplete reports cannot satisfy the specification.
Output order is irrelevant. Duplicate output paths are refused.
The specification itself is a review input: the comparator checks completeness
against its declared inventory, not against an independently inspected derivation
or test suite. Retain the specification and original reports with the result.

Behavioral agreement compares the selected assertion results, not timestamps,
raw logs, or the NAR hash of a VM evidence directory. Artifact agreement compares
the named build artifact and full expected output inventory. Never compare a
behavior report against an artifact report.

`reported-agreement` means only that the declarations agree and pass these gates.
Even differing administration strings do not prove independence. The result
always keeps `canonical = false` and `independenceVerified = false`. Authentication,
administrative independence, actual cache policy, evidence inspection, and release
policy remain pending. A signature feature is not implemented. No fabricated
second builder is supplied: tests use explicitly synthetic reports.
