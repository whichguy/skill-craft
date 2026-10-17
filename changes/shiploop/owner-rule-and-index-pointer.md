---
bump: minor
---
Every ShipLoop packet, the Improve packets included, now carries two lines directly under its first line: the owner rule
("concise and exact; no restating", keep every command, path, ID and expected value) and a pointer to the run's
`context-index.md` to read first after lost context or any doubt. The mid-packet "Run context index" line is gone; the
pass-log line keeps its own line.
- `context-index.md` is now the run's master index. It opens with a map of about 3 KB: the current stage with its packet
  file, the next and recovery commands, and one row per file or folder of the run, per knowledge file and for the skill's
  guides, each saying what it holds and when to read it. The run's record (request, accepted results, work items) follows.
  It stays a derived view that every save rewrites; `emit` writes it when a run lacks it.
- A model that lost its context used to have no single place to learn what the run's files are: in the last live run it
  never opened the index (0 reads across five compactions) although a mid-packet line named it.
- Reading pins moved with the lines: the callback is now the third line after the header, not the first, and the packet
  anatomy classifier knows both lines.
