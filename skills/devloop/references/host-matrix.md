# Host matrix — skill `devloop` (package leaf `devloop`)

User-facing skill / slash is **`devloop`**. Source package is `skills/devloop`.
Hermes card install is skipped — the engine owns `software-development/devloop`.

| Host | Skill card install | Scripts | Runtime |
|------|-------------------|---------|---------|
| Grok | `./install.sh --skill devloop --grok-only` → `~/.grok/skills/devloop` (symlink; detect host from **logical** path). Slash `/devloop` is `skills/devloop/commands/devloop.md` → `~/.grok/commands/devloop.md` | `scripts/devloop-run --host grok` | host-local engine + **Grok transport** (no Hermes required). Pin 0.2.0 declares `grok`. |
| Claude Code | skill-dir `~/.claude/skills/devloop` and/or marketplace `plugins/devloop` | same | resolve/bootstrap; transport TBD |
| Codex | `./install.sh --skill devloop --codex-only` → `~/.codex/skills/devloop` | same | resolve/bootstrap; transport TBD |
| Cursor | `./install.sh --skill devloop --cursor-only` → `~/.cursor/skills/devloop` (never `~/.cursor/skills-cursor`) | same | resolve/bootstrap; transport TBD |
| Hermes | **skip** card install (engine leaf is foreign) | same | Hermes transport; engine leaf accepted as seed |

## Binding surfaces (do not collapse)

| Surface | Env / default |
|---------|----------------|
| Preferred engine | `DEVLOOP_HOME` |
| Host-local engine | `$XDG_DATA_HOME/devloop` or `~/.local/share/devloop` |
| Bootstrap | `DEVLOOP_ENGINE_URL` / `DEVLOOP_BOOTSTRAP_CMD` / pin / Hermes seed |
| Hermes engine (foreign) | `~/.hermes/skills/software-development/devloop` — **never** overwritten by this card |
| Model transport | Engine-owned (`DEVLOOP_TRANSPORT`, `GROK_BIN`, `HERMES_BIN`) |

## Honesty

- Card install ≠ engine install ≠ COMPLETE.
- First `--setup` (or first real run without `--no-bootstrap`) may materialize a **host-local** engine.
- Claude marketplace git-subdir cannot hold the full engine; bootstrap writes **outside** the plugin tree.
- Demoted offline gates live in **`evidence-gates`** — not this matrix’s default path.
