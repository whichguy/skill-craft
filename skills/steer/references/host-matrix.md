# Steer host matrix

**Status:** session dispatcher — **not** DevLoop.

Default DevLoop: package **`devloop`** → engine.

**Honesty:** discovery (skill installed) ≠ a live `.steer/` run.

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/steer` | `/steer` (not bare “devloop”) | pending |
| Claude Code | symlink + plugin view | `~/.claude/skills/steer` | `/steer` | pending |
| Hermes | materialize-copy | `…/software-development/steer` | `/steer` | pending |
| Codex | symlink | `~/.codex/skills/steer` | `/steer` | pending |
| Cursor | symlink | `~/.cursor/skills/steer` | `/steer` | pending |

Package leaf: **steer**.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | a live `init`/`next`/`update` run on H |
| Default DevLoop | **never** this package — use skill `devloop` |
