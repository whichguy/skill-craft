---
bump: patch
---
Preserve per-host warm-`--resume` session IDs across `SessionEnd` hook binding cleanup on Claude, Codex, Grok, and Cursor during routed `shiploop-drive` runs, and read Claude Code's `effort` / `perTurnEffort` field from `assistant` transcript rows in passive `hook=model` telemetry.
