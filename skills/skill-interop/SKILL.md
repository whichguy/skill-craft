---
name: skill-interop
description: >-
  Use when authoring or reviewing a portable multi-host agent skill (Grok,
  Claude Code, Codex, Hermes): scaffold a prompt-only skill, make a skill
  host-agnostic, create skill layout, review skill for interop, or install
  across hosts. Covers prompt-first design, host matrix, anti-patterns
  (divergent copies, silent mode fallback, abs symlinks), and script-backed
  CLI contracts.
version: 0.2.0
author: Backchain / interop
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - skill-authoring
      - interop
      - multi-host
      - portable-skill
      - prompt-first
    related_skills:
      - backchain
---

# skill-interop

Review or design **skills** so they work across hosts: **prompt-first**, optional
**scripts** with one CLI contract, no host-specific prompt forks.

## Modes

| Mode | When | How |
|------|------|-----|
| **Review** | Existing skill tree needs an interop audit | Follow **Review procedure** below; load `prompts/review-skill.prompt.md` |
| **Create (prompt-only)** | New portable skill from scratch | Run `scripts/scaffold-skill.sh` (templates under `references/create-template/`) |
| **Install** | Symlink this package into host skill homes (**skill-dir** side-load) | From **skill-craft** (or dual-home) repo root: `./install.sh --skill skill-interop` (or `--skill all` / any `skills/<name>` / `--from DIR`); optional `--agents` |
| **Marketplace** | List/add marketplaces or install/uninstall **plugins** on Claude / Grok / Codex | `scripts/marketplace-run.sh` (see **Marketplace procedure** below) |

Host skill-dir destinations: `references/host-paths.md`.  
Plugin marketplace matrix + id forms: `references/marketplace-hosts.md`, `references/marketplace-id-forms.md`.

## Triggers

- “Make this skill portable / host-agnostic”
- “Review skill for Grok + Claude + Codex + Hermes”
- “Scaffold / create a prompt-only skill”
- “Prompt-only or needs scripts?”
- “Design a skill that works without the harness”
- “Install skill-interop across hosts”
- “List / install plugins or marketplaces across Claude, Grok, Codex”
- “Which hosts have marketplace CLIs available?”

## Review procedure

1. **Classify** — reasoning/drafting → prompt-only; deterministic/IO/external API → scripts; mix → both. Engine claims are orthogonal honesty (runtime host matrix), not a silent rename of `mixed`.
2. **Layer 0 contract** — I/O shapes, artifacts, success/failure (no silent empty).
3. **Layer 1 prompts** — strip models, paths, “run script X”; placeholders only.
4. **Layer 2 scripts** — one CLI family, injectable seams, document checkout requirement.
5. **Skill card** — short router: native default vs script optional; honest claims.
6. **Runtime binding** — package root, write-safe/runtime home/transport bins as separate surfaces; Hermes install is materialize-copy (not abs-symlink to external checkout).
7. **Host matrix** — fill Grok / Claude Code / Codex / Hermes for prompt-only and scripts; engines: discovery ≠ execution.
8. **Anti-patterns** — fail review if present (see `references/anti-patterns.md`).
9. **Output** — material/minor findings, proposed tree, migration steps.

Load `prompts/review-skill.prompt.md` with the skill tree + goals for a structured review.
Checklist: `references/checklist.md`. Packaging model: monorepo `docs/ARCHITECTURE.md`.

## Create procedure (prompt-only)

Scaffold a new skill package from the host-agnostic templates:

```sh
bash skills/skill-interop/scripts/scaffold-skill.sh \
  --name my-skill \
  --out /path/to/skills \
  [--description "Use when …"] \
  [--goals "summary for Procedure"] \
  [--force]
```

Creates `/path/to/skills/my-skill/{SKILL.md,prompts/main.prompt.md,references/host-matrix.md}`.
Templates live in `references/create-template/`. After scaffold: fill host matrix, tighten
Triggers/Procedure, and keep prompts free of model pins and host-only sole procedures.

Name rules: `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`, length 2–64.

## Install procedure

From the **skill-craft** monorepo root (or dual-home checkout; never overwrite foreign trees):

```sh
./install.sh --skill skill-interop
# --skill all|skill-interop|<name>              # any skills/<name> with SKILL.md
# --from /abs/path/to/skill                     # leaf = basename; exclusive with --skill
# --agents                                      # thin agents/<leaf>.md for Claude + Grok only
# host filters: --claude-only | --grok-only | --codex-only | --hermes-only | --cursor-only | --all
# preview: --dry-run
```

See `references/host-paths.md` for skill and agent destinations (Claude, Grok, Codex, Hermes).

This path is **not** the plugin marketplace. For host plugins use **Marketplace** below.
Marketplace **pins** (no skill bodies) live in sibling **skill-craft-market**.

## Marketplace procedure

Generic facade over Claude / Grok / Codex **plugin** marketplaces (not skill-dir symlinks):

```sh
bash skills/skill-interop/scripts/marketplace-run.sh hosts --json
bash skills/skill-interop/scripts/marketplace-run.sh marketplaces list --json
bash skills/skill-interop/scripts/marketplace-run.sh plugins list --json [--q QUERY]
bash skills/skill-interop/scripts/marketplace-run.sh plugins install name@marketplace --host claude
bash skills/skill-interop/scripts/marketplace-run.sh marketplaces add <src>
# optional bridge back to skill-dir install:
bash skills/skill-interop/scripts/marketplace-run.sh install-local --skill skill-interop --dry-run
```

Global flags: `--host claude|grok|codex|all` (default `all`), `--json`, `--dry-run`.  
Bin overrides: `CLAUDE_BIN`, `CODEX_BIN`, `GROK_BIN`.

**Keep distinct:** `./install.sh` → skill homes; `marketplace-run.sh plugins|marketplaces` → host plugin CLIs.  
Details: `references/marketplace-hosts.md`, `references/marketplace-id-forms.md`.

## Not for

Domain product implementation or ordinary code review.
