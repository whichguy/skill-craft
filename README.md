# skill-craft

Host-neutral **portable skills** monorepo. Skills live under `skills/<name>/` as [agentskills](https://github.com/agentskills/agentskills)-shaped packages. Marketplaces **pull from** this repo; this repo is **not** Claude-only.

## skill-craft vs claude-craft

| | **skill-craft** (this repo) | **claude-craft** |
|--|----------------------------|------------------|
| Role | Skills library (SoT) | Claude suite **plugin** marketplace |
| Layout | `skills/<name>/SKILL.md` | `plugins/<suite>/` (skills+agents+hooks+commands) |
| Install | `./install.sh` skill-dir shims | `claude plugin install name@claude-craft` |

## First skill

**skill-interop** — create/review portable multi-host skills; `marketplace-run.sh` facade for Claude/Grok/Codex plugin CLIs.

## Install (skill-dir shim)

```bash
./install.sh                          # all hosts, all skills under skills/
./install.sh --skill skill-interop
./install.sh --claude-only --agents
./install.sh --relink                 # repair dangling symlinks
./install.sh --dry-run
```

Destinations: `~/.claude/skills`, `~/.grok/skills`, `~/.codex/skills`, `~/.hermes/skills/software-development`.

## Marketplace face

Catalog pins live in sibling repo **[skill-craft-market](https://github.com/whichguy/skill-craft-market)** (host-specific faces only; no skill body SoT).

## Develop

```bash
bash test/run-all.sh
```

## License

MIT
