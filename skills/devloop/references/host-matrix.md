# Host matrix — skill `devloop` (package leaf `devloop`)

User-facing skill / slash is **`devloop`**. Source package is `skills/devloop`.
Hermes card install is skipped — the engine owns `software-development/devloop`.

| Host | Skill card install | Scripts | Runtime |
|------|-------------------|---------|---------|
| Grok | `./install.sh --skill devloop --grok-only` → `~/.grok/skills/devloop` (symlink; detect host from **logical** path). Slash `/devloop` is `skills/devloop/commands/devloop.md` → `~/.grok/commands/devloop.md` | `scripts/devloop-run --host grok` | preinstalled host-local engine + **Grok transport** (no Hermes required). |
| Claude Code | skill-dir `~/.claude/skills/devloop` and/or marketplace `plugins/devloop` | same | no native port; explicit external `DEVLOOP_TRANSPORT=grok\|hermes` only (no auto-Hermes) |
| Codex | `./install.sh --skill devloop --codex-only` → `~/.codex/skills/devloop`; marketplace/cache paths under `~/.codex/plugins/` are also Codex-affine | same | no native port; explicit external `DEVLOOP_TRANSPORT=grok\|hermes` only (no auto-Hermes) |
| Cursor | `./install.sh --skill devloop --cursor-only` → `~/.cursor/skills/devloop` (never `~/.cursor/skills-cursor`) | same | no native port; explicit external `DEVLOOP_TRANSPORT=grok\|hermes` only (no auto-Hermes) |
| Hermes | **skip** card install (engine leaf is foreign) | same | preinstalled Hermes transport; foreign engine may be resolved explicitly |

## Binding surfaces (do not collapse)

| Surface | Env / default |
|---------|----------------|
| Preferred engine | `DEVLOOP_HOME` |
| Host-local engine | `$XDG_DATA_HOME/devloop` or `~/.local/share/devloop` |
| Operator provisioning | trusted checkout `scripts/devloop-setup.sh` (outside distributed package) |
| Hermes engine (foreign) | `~/.hermes/skills/software-development/devloop` — **never** overwritten by this card |
| Model transport | Engine-owned (`DEVLOOP_TRANSPORT`, `GROK_BIN`, `HERMES_BIN`) |
| Engine interpreter | `ENGINE/.venv/bin/python3` when executable, otherwise `python3` on `PATH`; operator setup verifies the same selection |

## Honesty

- Card install ≠ engine install ≠ COMPLETE.
- Marketplace invocation never materializes an engine. An operator provisions a **host-local** engine before invocation.
- Unknown `host=auto` has no native transport and fails closed until an explicit external transport is supplied.
- Claude marketplace git-subdir cannot hold the full engine; external transport remains explicit and separate from package installation.
- Demoted offline gates live in **`evidence-gates`** — not this matrix’s default path.
