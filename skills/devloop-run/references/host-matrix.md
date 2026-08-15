# Host matrix — devloop-run (default DevLoop)

| Host | Skill card install | Scripts | Runtime |
|------|-------------------|---------|---------|
| Grok | `./install.sh --skill devloop-run --grok-only` → `~/.grok/skills/devloop-run` (symlink; detect host from **logical** path) | `scripts/devloop-run --host grok` | host-local engine + **Grok transport** (no Hermes required). Pin 0.2.0 declares `grok`. |
| Claude Code | skill-dir and/or marketplace `plugins/devloop-run` | same | resolve/bootstrap; transport TBD |
| Codex | `./install.sh --skill devloop-run --codex-only` | same | resolve/bootstrap; transport TBD |
| Hermes | optional card leaf `devloop-run` (copy); engine remains `devloop` | same | Hermes transport; engine leaf accepted as seed |

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
- Demoted offline gates live in **`devloop-native`** — not this matrix’s default path.
