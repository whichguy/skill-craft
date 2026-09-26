---
name: skill-interop
description: >-
  Use when authoring or reviewing a portable multi-host agent skill (Grok,
  Claude Code, Codex, Hermes): scaffold a prompt-only skill, make a skill
  host-agnostic, create skill layout, review skill for interop, or install
  across hosts. Covers prompt-first design, host matrix, anti-patterns
  (divergent copies, silent mode fallback, abs symlinks), and script-backed
  CLI contracts.
version: 0.2.6
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
| **Create (prompt-only)** | New portable skill from scratch | Run the bound `SCAFFOLD` helper (templates under `references/create-template/`) |
| **Install** | Symlink this package into host skill homes (**skill-dir** side-load) | From **skill-craft** (or dual-home) repo root: `./install.sh --skill skill-interop` (or `--skill all` / any `skills/<name>` / `--from DIR`); optional `--agents` |
| **Marketplace** | List/add marketplaces or install/uninstall **plugins** on Claude / Grok / Codex | Bound `MARKETPLACE_RUN` helper (see **Marketplace procedure** below) |

Host skill-dir destinations: `references/host-paths.md`.  
Plugin marketplace matrix + id forms: `references/marketplace-hosts.md`, `references/marketplace-id-forms.md`.

## Installed package binding

For a script-backed mode, first obtain the absolute path of the **selected,
loaded** `SKILL.md` from the host's skill context. `SKILL_ROOT` is that file's
parent directory; it is not the user's project cwd, an author checkout, a
same-name skill found on `PATH`, or a guessed plugin-cache layout. Expand a
host-provided selected skill-root alias before binding it. Claude Code may
render `${CLAUDE_SKILL_DIR}` in this card where supported, but that substitution
is not a portable shell environment variable.

```sh
# Replace this illustrative path with the selected skill's absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
SCAFFOLD="$SKILL_ROOT/scripts/scaffold-skill.sh"
MARKETPLACE_RUN="$SKILL_ROOT/scripts/marketplace-run.sh"
```

Quote these absolute paths and bind them again for each independent tool call.
Keep the selected logical path for host identity; the bundled helpers may
resolve their own package-local resources physically. Do not replace either
helper with an ambient executable. If `bash`, `python3`, or a requested host
CLI is absent, surface that prerequisite and its scope rather than silently
changing modes.

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
bash "$SCAFFOLD" \
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

This is a **checkout-only** skill-dir side-load, not a marketplace-package
operation. From an explicitly chosen **skill-craft** monorepo root (or
dual-home checkout; never overwrite foreign trees):

```sh
./install.sh --skill skill-interop
# --skill all|skill-interop|<name>              # any skills/<name> with SKILL.md
# --from /abs/path/to/skill                     # leaf = basename; exclusive with --skill
# --agents                                      # thin agents/<leaf>.md for Claude + Grok only
# host filters: --claude-only | --grok-only | --codex-only | --hermes-only | --cursor-only | --opencode-only | --all
# preview: --dry-run
```

See `references/host-paths.md` for skill and agent destinations (Claude, Grok, Codex, Hermes).

This path is **not** the plugin marketplace. For host plugins use **Marketplace** below.
skill-craft itself is the marketplace (catalog name `whichguy`, after its publisher). Every skill ships in
its one `skill-craft` plugin (install `skill-craft@whichguy`; invoke `/skill-craft:<leaf>`).
Its catalogs and `plugins/` are release output written by `scripts/release.py`; plugins
from other repositories are pinned by commit in `catalog/external-plugins.json`.

## Marketplace procedure

Generic facade over Claude / Grok / Codex **plugin** marketplaces (not skill-dir symlinks):

```sh
bash "$MARKETPLACE_RUN" hosts --json
bash "$MARKETPLACE_RUN" marketplaces list --json
bash "$MARKETPLACE_RUN" plugins list --json [--q QUERY]
bash "$MARKETPLACE_RUN" plugins install name@marketplace --host claude
# Grok only: explicitly bypass its install confirmation for a qualified selector.
bash "$MARKETPLACE_RUN" plugins install review-coverage@local/local-marketplace --host grok --trust
bash "$MARKETPLACE_RUN" marketplaces add <src>
```

Global flags: `--host claude|grok|codex|all` (default `all`), `--json`, `--dry-run`.  
Bin overrides: `CLAUDE_BIN`, `CODEX_BIN`, `GROK_BIN`.

`--trust` is accepted only for `plugins install` with an explicit `--host grok`; it is never
added automatically and is rejected for the other host selections.

For Grok, a qualified catalog selector is install-only. Use the installed short name reported by
`plugins list` for removal or a per-plugin update, for example
`plugins uninstall review-coverage --host grok`; the facade does not rewrite selector forms.

`install-local` is intentionally **not** a marketplace fallback. It only runs
an installer the operator explicitly chooses from a local checkout:

```sh
MARKETPLACE_INSTALL_SH="/absolute/path/to/skill-craft/install.sh" \
  bash "$MARKETPLACE_RUN" install-local --skill skill-interop --dry-run
```

The facade never searches upward from an installed package for `install.sh`.
If `MARKETPLACE_INSTALL_SH` is missing, non-absolute, or unreadable, it exits
with a precondition error; install the plugin normally or select a checkout
deliberately.

**Keep distinct:** `./install.sh` → skill homes; `marketplace-run.sh plugins|marketplaces` → host plugin CLIs.  
Details: `references/marketplace-hosts.md`, `references/marketplace-id-forms.md`.

## Not for

Domain product implementation or ordinary code review.
