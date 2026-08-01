# Host matrix — devloop-run

| Host | Skill card install | Scripts | Runtime |
|------|-------------------|---------|---------|
| Grok | `./install.sh --skill devloop-run --grok-only` → `~/.grok/skills/devloop-run` | `scripts/devloop-run` | After resolve or `--setup` bootstrap to host-local engine |
| Claude Code | skill-dir and/or marketplace `plugins/devloop-run` | same | same |
| Codex | `./install.sh --skill devloop-run --codex-only` | same | same |
| Hermes | optional card leaf `devloop-run` (copy); engine remains `devloop` | same | Hermes engine path still accepted |

## Binding surfaces (do not collapse)

| Surface | Env / default |
|---------|----------------|
| Preferred engine | `DEVLOOP_HOME` |
| Host-local engine | `$XDG_DATA_HOME/devloop` or `~/.local/share/devloop` |
| Bootstrap | `DEVLOOP_ENGINE_URL` / `DEVLOOP_BOOTSTRAP_CMD` / seed from Hermes |
| Hermes engine (foreign) | `~/.hermes/skills/software-development/devloop` — **never** overwritten by this card |

## Honesty

- Card install ≠ engine install.
- First `--setup` (or first real run without `--no-bootstrap`) may materialize a **host-local** engine.
- Claude marketplace git-subdir cannot hold the full engine; bootstrap writes **outside** the plugin tree.
