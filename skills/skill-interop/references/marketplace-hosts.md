# Marketplace hosts (plugin layer)

This is the **plugin marketplace** surface, not skill-dir side-load.

| Layer | What it is | How (this repo) |
|-------|------------|-----------------|
| **Skill-dir install** | Symlink a `SKILL.md` package into host skill homes | `./install.sh` / `marketplace-run.sh install-local` |
| **Plugin marketplace** | Host CLI plugins + marketplaces (shared skills/hooks/tools as plugins) | `marketplace-run.sh` verbs under `marketplaces` / `plugins` |

Facade: `skills/skill-interop/scripts/marketplace-run.sh`.

Env bin overrides (testable): `CLAUDE_BIN`, `CODEX_BIN`, `GROK_BIN`.

## Capability matrix

| Capability | Claude | Grok | Codex |
|------------|--------|------|-------|
| list_marketplaces | yes (`--json` preferred) | yes | yes |
| add_marketplace | yes | yes | yes |
| list_plugins (installed) | yes (`--json` preferred) | yes (`--json` preferred) | yes (`--json`) |
| install_plugin | yes (`plugin install`) | **no** Claude-style `name@marketplace` (facade rejects; exit 4) | yes (`plugin add`) |
| install_git / path as id | mediated via marketplace | yes (git URL / GitHub shorthand / local path) | no — need `name@marketplace` |
| update plugins / marketplaces | yes | yes | marketplace `upgrade` |

Hermes is **not** in this marketplace facade (skill-dir only via `install.sh`).

## CLI map (verified)

### Claude

```text
claude plugin marketplace list [--json]     # facade prefers --json, falls back to human
claude plugin marketplace add <src>
claude plugin marketplace update [name]
claude plugin list [--json]                 # facade prefers --json; human: name@marketplace + Version/…
claude plugin install <plugin[@marketplace]>
claude plugin uninstall <plugin>
claude plugin update <plugin>
```

### Codex

```text
codex plugin marketplace list
codex plugin marketplace add …
codex plugin marketplace upgrade            # refresh snapshots (no "update")
codex plugin list [--json]                  # installed[] with pluginId, name, …
codex plugin add PLUGIN@MARKETPLACE         # install = add
codex plugin add PLUGIN --marketplace MP
codex plugin remove …
```

### Grok

```text
grok plugin marketplace list|add|remove|update
grok plugin list [--json]|install|uninstall|update
```

**Grok install-by-id (`name@marketplace`): no.** The facade does **not** pass Claude-style
`plugin@marketplace` ids to `grok plugin install`. Grok treats `@` as a **git ref**, not a
marketplace selector. Allowed install forms for Grok: git URL, GitHub shorthand
(`user/repo`, `user/repo@ref`), or a local path. Rejected Claude-style ids exit **4**
(precondition) and never invoke the CLI.

## Multi-host policy

- Default `--host all` runs Claude, Grok, Codex **sequentially**.
- Missing CLI → host `unavailable`, skipped (not by itself a failure).
- **Exit 1 if any selected available host fails** (partial success is still non-zero).
- Exit 3 if no selected host is available.
- Exit 4 for host preconditions (e.g. Codex install without `name@marketplace`; Grok install of Claude-style `name@marketplace`).
- `--dry-run` prints `would-run: …` and does **not** exec install/add/update (preconditions still fail before would-run).

## Parsing

Normalized JSON is **best-effort**. If a host's stdout cannot be structured, rows may include `raw` lines. CLI exit 0 still yields overall success for that host.
