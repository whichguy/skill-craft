---
bump: minor
---
`shiploop-drive` has no ceiling by default: it runs host sessions until the run is done, paused, blocked or halted, a
host fails without advancing it, or two sessions in a row make no progress.
- `--max-sessions` (default 20) is gone. Pass `--max-minutes N` for an optional wall-clock ceiling for the whole drive
  (exit 5 when reached); the last session's timeout is cut to the time left.
- Owner, 2026-10-28: runs are meant to go on for a very long time, and a limit is added only when the owner asks.
