# Host matrix — devloop-run

| Host | Prompt-only card | Scripts | Install | Runtime |
|------|------------------|---------|---------|---------|
| Grok | yes | preflight may refuse | skill-dir symlink | **execution unsupported** unless `DEVLOOP_HOME` / Hermes engine present |
| Claude Code | yes | same | skill-dir and/or plugin | same |
| Codex | yes | same | skill-dir | same |
| Hermes | yes | run engine CLI | materialize **this card** as copy; engine is separate foreign/live tree | **supported** when engine resolves |

**Honesty:** Installing `devloop-run` on four hosts is not multi-host **runtime**. The
engine leaf name `devloop` under Hermes skillhub must not be overwritten by this card
(different leaf: `devloop-run`).
