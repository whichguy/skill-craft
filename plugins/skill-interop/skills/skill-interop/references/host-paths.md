# Install destinations (skill-craft)

Repo root `./install.sh` (skill-craft monorepo) symlinks skill packages into local skill homes.
Optional `--agents` symlinks thin agent cards for Claude and Grok only.
Existing destinations are never overwritten.

When this package is dual-homed under **backchain**, use that repo’s `./install.sh`
(`--skill skill-interop` or product defaults). Destinations are the same.

## Skills

Per skill leaf (`skill-interop`, or any `skills/<name>` / `--from DIR`):

| Host | Destination |
|------|-------------|
| Claude Code | `~/.claude/skills/<leaf>` |
| Grok Build | `~/.grok/skills/<leaf>` |
| Codex | `~/.codex/skills/<leaf>` |
| Hermes (host) | `~/.hermes/skills/software-development/<leaf>` |
| Hermes (Docker bind) | `/opt/data/skills/software-development/<leaf>` when `~/.hermes` is mounted at `/opt/data` |

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

# Preview
./install.sh --skill skill-interop --agents --dry-run
```

Sources in this repo: every `skills/<name>` with `SKILL.md`. Agent cards: `agents/<leaf>.md`.
