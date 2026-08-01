# Install destinations (skill-craft)

Repo root `./install.sh` (skill-craft monorepo) installs skill packages into local skill homes:

- **Claude / Grok / Codex:** symlink into skill homes  
- **Hermes:** **materialized copy** (default), not an abs-symlink to an external checkout  

Optional `--agents` symlinks thin agent cards for Claude and Grok only.
Foreign real destinations are never overwritten.

When this package is dual-homed under **backchain**, use that repo’s `./install.sh`
(`--skill skill-interop` or product defaults). Destinations are the same.

## Skills

Per skill leaf (`skill-interop`, or any `skills/<name>` / `--from DIR`):

| Host | Destination | Mode |
|------|-------------|------|
| Claude Code | `~/.claude/skills/<leaf>` | symlink |
| Grok Build | `~/.grok/skills/<leaf>` | symlink |
| Codex | `~/.codex/skills/<leaf>` | symlink |
| Hermes (host) | `~/.hermes/skills/software-development/<leaf>` | **copy** |
| Hermes (Docker bind) | `/opt/data/skills/software-development/<leaf>` when `~/.hermes` is mounted at `/opt/data` | same tree as host |

Hermes provenance marker (outside the leaf):

`~/.hermes/skills/software-development/.skill-craft/<leaf>.json`

### Hermes materialization ≠ synced content

The Hermes leaf is a **local materialization** of skill-craft (or `--from`) source.
It is not the git SoT and should not be edited in place. Re-run `./install.sh` to refresh
a **managed** copy (marker present). Foreign real trees (no marker) are skipped forever.

If `~/.hermes` is a git work tree, prefer gitignoring skill-craft materializations so the
hermes home repo does not track divergent copies. `install.sh` may print a gitignore hint;
it does not write `~/.hermes/.gitignore`.

## Agents (optional, `--agents`)

Only when `agents/<leaf>.md` exists in the repo. **Claude + Grok only** — Codex and Hermes are skipped.

| Host | Destination |
|------|-------------|
| Claude Code | `~/.claude/agents/<leaf>.md` |
| Grok Build | `~/.grok/agents/<leaf>.md` |
| Codex | *(not installed)* |
| Hermes | *(not installed)* |

## Examples

```sh
# All skills under skills/, all four hosts (skill-craft default)
./install.sh

# skill-interop only
./install.sh --skill skill-interop

# Explicit all skills
./install.sh --skill all

# Arbitrary leaf under skills/
./install.sh --skill my-skill

# External package (leaf = basename)
./install.sh --from /path/to/sample-skill

# Skills + thin agent cards (Claude/Grok)
./install.sh --skill all --agents

# One host
./install.sh --skill skill-interop --claude-only
./install.sh --skill skill-interop --grok-only
./install.sh --skill skill-interop --codex-only
./install.sh --skill skill-interop --hermes-only

# Force modes
./install.sh --skill skill-interop --symlink   # all hosts symlink (overrides Hermes copy)
./install.sh --skill skill-interop --copy      # all hosts materialize

# Preview
./install.sh --skill skill-interop --agents --dry-run
```

Sources in this repo: every `skills/<name>` with `SKILL.md`. Agent cards: `agents/<leaf>.md`.

Architecture: [docs/ARCHITECTURE.md](../../../../docs/ARCHITECTURE.md).
