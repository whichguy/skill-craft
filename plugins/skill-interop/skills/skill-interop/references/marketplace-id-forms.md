# Marketplace / plugin id forms

Three different identifiers appear in skill-interop. Do not mix them.

## 1. Plugin id: `name@marketplace`

Primary install selector for **Claude** and **Codex** marketplaces.

| Form | Example | Hosts |
|------|---------|-------|
| `plugin@marketplace` | `code-review@claude-plugins-official` | Claude, Codex |
| bare `plugin` | `code-review` | Claude may resolve; **Codex facade requires `@`** |

Facade rules (`marketplace-run.sh plugins install <id>`):

| Host | Behavior |
|------|----------|
| Claude | `claude plugin install <id>` (pass through; prefer `name@marketplace`) |
| Codex | if `id` contains `@` → `codex plugin add <id>`; else **fail** exit 4 (use `name@marketplace`) |
| Grok | **rejects** Claude-style `name@marketplace` (exit 4; `@` is a git ref on Grok). Accepts git URL, `user/repo`, `user/repo@ref`, or local path only |

## 2. Git URL / local path (plugin source)

Used when **adding a marketplace** or when a host accepts git/path as a **plugin install** source.

| Form | Example | Typical use |
|------|---------|-------------|
| HTTPS git | `https://github.com/anthropics/claude-plugins-official.git` | `marketplaces add` |
| GitHub shorthand | `anthropics/claude-plugins-official` | host-dependent marketplace add |
| Local path | `/path/to/marketplace-or-plugin` | Grok plugin install / marketplace add |

- **Grok** `plugins install` takes git URL, GitHub shorthand, or local path (`install_git` capability). Claude-style `name@marketplace` is **rejected by the facade** (not passed through).
- **Claude** usually installs plugins **from an already-added marketplace**, not from a raw git URL as plugin id.
- **Codex** installs from configured marketplace snapshots via `PLUGIN@MARKETPLACE`.

## 3. Local skill leaf (skill-dir side-load)

Not a marketplace id. This is the **`./install.sh`** path:

| Form | Example | Effect |
|------|---------|--------|
| skill leaf name | `skill-interop`, other `skills/<leaf>` | symlink `skills/<leaf>` into host skill homes |
| `--from DIR` | `--from /path/to/my-skill` | leaf = basename of DIR |

```sh
# Skill-dir (not marketplace):
./install.sh --skill skill-interop
bash skills/skill-interop/scripts/marketplace-run.sh install-local --skill skill-interop --dry-run
```

## Quick chooser

| Goal | Use |
|------|-----|
| Install official/curated **plugin** (Claude/Codex) | `plugins install name@marketplace --host claude` (or codex) |
| Install plugin from git/path (Grok) | `plugins install user/repo` or URL/path `--host grok` |
| Register a **marketplace source** | `marketplaces add <git-or-path>` |
| Symlink this repo’s **skill package** | `install.sh` / `install-local` |
| Discover what is installed | `plugins list [--json] [--q substr]` |
