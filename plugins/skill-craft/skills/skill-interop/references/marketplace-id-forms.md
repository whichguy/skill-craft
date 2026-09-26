# Marketplace / plugin id forms

Four identifier forms appear in skill-interop. Do not mix them.

## 1. Plugin id: `name@marketplace` (Claude and Codex)

Primary install selector for **Claude** and **Codex** marketplaces. It is not the
unambiguous Grok selector form.

| Form | Example | Hosts |
|------|---------|-------|
| `plugin@marketplace` | `code-review@claude-plugins-official` | Claude, Codex |
| bare `plugin` | `code-review` | Claude may resolve; **Codex facade requires `@`** |

Facade rules (`marketplace-run.sh plugins install <id>`):

| Host | Behavior |
|------|----------|
| Claude | `claude plugin install <id>` (pass through; prefer `name@marketplace`) |
| Codex | if `id` contains `@` → `codex plugin add <id>`; else **fail** exit 4 (use `name@marketplace`) |
| Grok | rejects the **unqualified** form with exit 4; use its qualified `name@scope/marketplace` selector below when a marketplace inventory supplies one |

## 2. Grok qualified marketplace selector: `name@scope/marketplace`

Grok's current marketplace inventory can provide a qualified selector when a bare plugin name
would collide. Preserve it exactly rather than treating its slash as an invalid marketplace id:

| Form | Example | Host | Purpose |
|------|---------|------|---------|
| `plugin@scope/marketplace` | `review-coverage@local/local-marketplace` | Grok | Select the intended plugin when duplicate names exist |

The facade passes this form directly to `grok plugin install`. `--trust` is an optional,
explicit Grok-only confirmation bypass:

```sh
bash "$MARKETPLACE_RUN" plugins install review-coverage@local/local-marketplace \
  --host grok --trust
```

Do not add `--trust` by default. It is rejected for Claude, Codex, and `--host all` because
their confirmation options have different semantics.

This is an **install selector only**. Grok's uninstall and per-plugin update commands take the
installed short name shown by `grok plugin list`, not this qualified value. For the example
above, use `plugins uninstall review-coverage --host grok` (or `plugins update review-coverage
--host grok`). The facade intentionally forwards the provided lifecycle identifier rather than
trying to infer one from the other.

## 3. Git URL / local path (plugin source)

Used when **adding a marketplace** or when a host accepts git/path as a **plugin install** source.

| Form | Example | Typical use |
|------|---------|-------------|
| HTTPS git | `https://github.com/anthropics/claude-plugins-official.git` | `marketplaces add` |
| GitHub shorthand | `anthropics/claude-plugins-official` | host-dependent marketplace add |
| Local path | `/path/to/marketplace-or-plugin` | Grok plugin install / marketplace add |

- **Grok** `plugins install` takes git URL, GitHub shorthand, or local path (`install_git` capability). It also accepts the qualified marketplace selector in section 2 when its inventory emits one; the bare `name@marketplace` form is rejected as ambiguous.
- **Claude** usually installs plugins **from an already-added marketplace**, not from a raw git URL as plugin id.
- **Codex** installs from configured marketplace snapshots via `PLUGIN@MARKETPLACE`.

## 4. Local skill leaf (skill-dir side-load)

Not a marketplace id. This is a **checkout `./install.sh`** path:

| Form | Example | Effect |
|------|---------|--------|
| skill leaf name | `skill-interop`, other `skills/<leaf>` | symlink `skills/<leaf>` into host skill homes |
| `--from DIR` | `--from /path/to/my-skill` | leaf = basename of DIR |

```sh
# Skill-dir (not marketplace):
./install.sh --skill skill-interop

# From an installed skill only after selecting a real checkout installer:
MARKETPLACE_INSTALL_SH="/absolute/path/to/skill-craft/install.sh" \
  bash "$MARKETPLACE_RUN" install-local --skill skill-interop --dry-run
```

## Quick chooser

| Goal | Use |
|------|-----|
| Install official/curated **plugin** (Claude/Codex) | `plugins install name@marketplace --host claude` (or codex) |
| Install Grok plugin from its qualified marketplace inventory | `plugins install name@scope/marketplace --host grok` |
| Remove/update an installed Grok plugin | `plugins uninstall name --host grok` / `plugins update name --host grok` |
| Install plugin from git/path (Grok) | `plugins install user/repo` or URL/path `--host grok` |
| Register a **marketplace source** | `marketplaces add <git-or-path>` |
| Symlink this repo’s **skill package** | `install.sh` / `install-local` |
| Discover what is installed | `plugins list [--json] [--q substr]` |
