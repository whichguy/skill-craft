# ShipLoop host matrix

**Status:** session dispatcher — **not** DevLoop.

Default DevLoop: package **`devloop`** → engine.

**Honesty:** discovery (skill installed) ≠ a live `.shiploop/` run.

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/shiploop` | `/shiploop` (not bare “devloop”) | pending |
| Claude Code | symlink + plugin view | `~/.claude/skills/shiploop` | `/shiploop` | pending |
| Hermes | materialize-copy | `…/software-development/shiploop` | `/shiploop` | pending |
| Codex | symlink | `~/.codex/skills/shiploop` | `/shiploop` | pending |
| Cursor | symlink | `~/.cursor/skills/shiploop` | `/shiploop` | pending |

Package leaf: **shiploop**. Reprint and closer are `/shiploop next` and
`/shiploop complete` on this leaf.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | a live `init`/`next`/`complete` run on H |
| Default DevLoop | **never** this package — use skill `devloop` |
