# Steer-next host matrix

**Status:** packet printer for the steer harness — **not** DevLoop.

**Honesty:** discovery (skill installed) ≠ a live `.steer/` run.

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/steer-next` | skill `steer-next` | pending |
| Claude Code | symlink + plugin view | `~/.claude/skills/steer-next` | skill `steer-next` | pending |
| Hermes | materialize-copy | `…/software-development/steer-next` | skill `steer-next` | pending |
| Codex | symlink | `~/.codex/skills/steer-next` | skill `steer-next` | pending |
| Cursor | symlink | `~/.cursor/skills/steer-next` | skill `steer-next` | pending |

Package leaf: **steer-next**. Requires sibling **steer**.
