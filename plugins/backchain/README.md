# Backchain

Plan Orchestrator portable skills: Backchain builds and repeatedly reviews evidence-backed dependency plans; Plan Dispatcher coordinates their execution with native agents. Existing backchain skill and plugin identities remain stable.

## Skills

This plugin packages 2 skills. Agent cards: [agents/backchain.md](agents/backchain.md).

| Skill | Version | Kind | Codex | Claude | Card |
|-------|---------|------|-------|--------|------|
| `backchain` | 0.4.0 | portable | `$backchain:backchain` | `/backchain:backchain` | [SKILL.md](skills/backchain/SKILL.md) |
| `plan-dispatcher` | 0.2.0 | script-backed | `$backchain:plan-dispatcher` | `/backchain:plan-dispatcher` | [SKILL.md](skills/plan-dispatcher/SKILL.md) |

## Install

Install the `backchain` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skills. Keep one track per host: use either this plugin or a skill-directory install of the same skills, not both. Skill Craft's `install.sh` never installs these skills.

## Use

Use the installed plugin skills by their qualified names: in Codex, ask for `$backchain:<skill>`; in Claude, invoke `/backchain:<skill>`; in other hosts, select the installed plugin skill. Read the skill's SKILL.md before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

Each skill declares its own kind and requirements; the primary skill targets linux, macos. When a card invokes a bundled helper, resolve it from that loaded skill directory (for example, `skills/<skill>/scripts/...`), never from the consumer project's current directory.

## Package scope

This package contains only the skills and agent cards listed above. Files that a card mentions outside its own skill directory, such as repository-level harnesses, installers or make targets, are not part of this package.

## Provenance

The skills and agent cards are a verbatim, hash-verified copy of upstream commit `8671b5c45f889e2eb82a4aca4b94a0af53f61869` (upstream package version 0.4.0). Skill Craft records every file's sha256 in [bundles/backchain/PROVENANCE.json](https://github.com/whichguy/skill-craft/blob/main/bundles/backchain/PROVENANCE.json).

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
