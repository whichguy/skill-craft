# Marketplace hosts (plugin layer)

This is the **plugin marketplace** surface, not skill-dir side-load.

| Layer | What it is | How (this repo) |
|-------|------------|-----------------|
| **Skill-dir install** | Symlink a `SKILL.md` package into host skill homes | Checkout `./install.sh`, or bound facade `install-local` with explicit `MARKETPLACE_INSTALL_SH` |
| **Plugin marketplace** | Host CLI plugins + marketplaces (shared skills/hooks/tools as plugins) | Bound `MARKETPLACE_RUN` verbs under `marketplaces` / `plugins` |

Facade: `"$SKILL_ROOT/scripts/marketplace-run.sh"`, where the parent card binds
`SKILL_ROOT` from the selected loaded `SKILL.md`.

Env bin overrides (testable): `CLAUDE_BIN`, `CODEX_BIN`, `GROK_BIN`.

## Capability matrix

| Capability | Claude | Grok | Codex |
|------------|--------|------|-------|
| list_marketplaces | yes (`--json` preferred) | yes | yes |
| add_marketplace | yes | yes | yes |
| list_plugins (installed) | yes (`--json` preferred) | yes (`--json` preferred) | yes (`--json`) |
| install_plugin | yes (`plugin install`) | yes (`plugin install`; git/path or qualified marketplace selector) | yes (`plugin add`) |
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
grok plugin install <source-or-qualified-selector> [--trust]
```

Installed `grok plugin install --help` documents Git URLs, GitHub shorthand, and local paths
as sources (including `@ref` and `#subdir` forms), and exposes `--trust` to skip its install
confirmation. Its current marketplace inventory can also emit a **qualified marketplace
selector** for a duplicate name, for example
`review-coverage@local/local-marketplace`. The facade deliberately passes that
`name@scope/marketplace` form to Grok unchanged; it does not misclassify the slash qualifier
as a Claude-only id or rewrite it as a git ref.

A bare `name@marketplace` remains ambiguous on Grok and the facade rejects it with exit **4**.
Use the qualified selector supplied by Grok's marketplace inventory, or a documented git/path
source. `--trust` is never added automatically: it is accepted only for
`plugins install ... --host grok`, forwarded only to Grok, and rejected for Claude, Codex, or
`--host all` rather than being silently dropped or translated.

**Grok uses different identifiers across its lifecycle.** `plugins install` may take the
qualified catalog selector above, but `grok plugin uninstall --help` and `grok plugin update
--help` require the installed plugin **name** shown by `grok plugin list`. After installing
`review-coverage@local/local-marketplace`, remove or update it as `review-coverage`:

```sh
bash "$MARKETPLACE_RUN" plugins uninstall review-coverage --host grok
bash "$MARKETPLACE_RUN" plugins update review-coverage --host grok
```

The facade forwards the supplied identifier; it deliberately does not guess or normalize an
install selector into an installed name. Claude and Codex retain their own selector semantics.

## Multi-host policy

- Default `--host all` runs Claude, Grok, Codex **sequentially**.
- Missing CLI → host `unavailable`, skipped (not by itself a failure).
- **Exit 1 if any selected available host fails** (partial success is still non-zero).
- Exit 3 if no selected host is available.
- Exit 4 for host preconditions (e.g. Codex install without `name@marketplace`; ambiguous Grok `name@marketplace`; `--trust` without explicit `--host grok`).
- `--dry-run` prints `would-run: …` and does **not** exec install/add/update (preconditions still fail before would-run).

## Parsing

Normalized JSON is **best-effort**. If a host's stdout cannot be structured, rows may include `raw` lines. CLI exit 0 still yields overall success for that host.
