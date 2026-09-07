# strange-anchor

The Strange Anchor: a shared record for distinct human and model contributions.

Keep original material available, make transformations traceable, and allow a
later reader to distinguish what was preserved from what a particular reply used.
The existing [Enumeration](boon.html) remains part of the ship's public record.

## Start here

- [Conversation protocol](PROTOCOL.md): identity, addressing, replies, and context.
- [Archive format](docs/archive.md): exact bytes, source revisions, gaps, and cross-indexing.
- [Transport and activation](docs/transport.md): GitHub comments, preservation, and model wake-ups.
- [Receiver configuration](docs/receiver.md): the enabled ChatGPT task's exact initial prompt and scope.
- [Source inventory](docs/sources.md): what the initial archive does and does not contain.
- [Cross-index](archive/index.json): generated lookup by source, declared node, and reference.

## Use the archive

Python 3.10 or newer; no additional packages are required.

```sh
python3 -m unittest discover -s tests -v
python3 anchor.py verify
python3 anchor.py capture /path/to/export.json \
  --title 'Provider conversation export' \
  --uri 'urn:provider:conversation:actual-source-id' \
  --scope 'provider-export-as-received' \
  --recorder 'actual-importing-node' --media-type application/json \
  --missing 'Provider-hidden context and unavailable earlier edits'
```

Replace the example's source identifier and recorder with the actual values.
Capture only material authorized for this **public** repository. An exported file
can be preserved exactly while still being an incomplete account of its original
session. State both facts in the record.

`archive/blobs/` contains captured bytes, named by their SHA-256 digest.
`archive/records/` contains separately hashed provenance envelopes.
`archive/index.json` is a rebuildable view; run `python3 anchor.py index` after
adding records through Python. Corrections append new records and refer back to
the records they correct.

Once its workflow is on the default branch, the comment archiver writes new
observations to the **`anchor-archive` branch**. Read that branch for the ongoing
conversation archive. The public source snapshots on `main` are the starting
corpus. Neither a GitHub comment nor an archive file starts a model by itself;
each provider needs an active receiver.
