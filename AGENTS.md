# AGENTS.md — skill-craft

Host-neutral **portable skills** monorepo. Not Claude-first; not a product harness.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Layout

- **`skills/<leaf>/`** — skill source of truth (`SKILL.md`, optional `prompts/`, `scripts/`, `references/`)
- **`agents/<leaf>.md`** — thin agent cards that point at the skill (Claude/Grok only)
- **`install.sh`** — multi-host skill-dir install (symlink Claude/Grok/Codex; **copy** Hermes)
- **`test/`** — hermetic checks for skills and install

## Install

```sh
./install.sh                      # all hosts, every skills/<leaf>
./install.sh --skill skill-interop
./install.sh --skill all --agents
./install.sh --from /path/to/pkg
./install.sh --claude-only --dry-run
```

Hosts: Claude (`~/.claude/skills`), Grok (`~/.grok/skills`), Codex (`~/.codex/skills`),
Hermes (`~/.hermes/skills/software-development`, materialized copy + `.skill-craft` marker).

## Conventions

- Skills are **prompt-first** and host-agnostic. Prefer one CLI contract for scripts.
- Layer 0/1/2 = contract / prompts / scripts (do not renumber). Binding + honesty in ARCHITECTURE.
- Do not put Claude-only marketplace plugin packaging in this repo root (no required `.claude-plugin`).
- Marketplace **pins** live in the sibling repo **skill-craft-market** — catalog only, no skill bodies.
- Unit of a skill: agentskills.io-style package (`SKILL.md` + optional tree).
- Discovery ≠ execution for engine multi-host claims.

## First skill

**skill-interop** — author/review portable multi-host skills (Grok, Claude Code, Codex, Hermes).
