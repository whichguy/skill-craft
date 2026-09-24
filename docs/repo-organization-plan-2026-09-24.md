---
Execute: inline
Status: in progress (worktree refactor/repo-layout-26fa71)
Date: 2026-09-24
---

# Repository organization plan

## Purpose

`skill-craft` is the one place to install these skills from, for **Claude Code,
Codex, Grok and OpenCode** (Cursor comes along at no extra cost).

## Recommendation

1. **One repository.** Separate repositories per skill would not make installs
   or releases more repeatable (idempotent). That comes from pinned versions,
   deterministic generation, and an installer that records what it owns,
   which `install.sh` already does.
2. **Skill source lives inside its plugin:** `plugins/<leaf>/skills/<leaf>/`,
   one plugin per skill, the way `anthropics/claude-plugins-official` lays out
   its plugins. The committed `skills/` → `plugins/` copy (131k lines)
   disappears; plugin and skill names do not change.
3. **Only small metadata is generated** (host manifests, catalogs, README
   inventory), and only at release.
4. **This repository is the marketplace** for Claude, Codex and Grok; OpenCode
   (and any host) installs skill directories with `install.sh`.
   `skill-craft-market` is retired.

## Research

### How each host gets skills

| Host | Skill directories it reads | Plugin marketplace | Catalog file in a repo |
|---|---|---|---|
| Claude Code | `~/.claude/skills`, `.claude/skills` | Yes | `.claude-plugin/marketplace.json` |
| Codex | `~/.agents/skills`, `.agents/skills` | Yes | `.agents/plugins/marketplace.json` (legacy fallback: `.claude-plugin/marketplace.json`) |
| Grok Build | `~/.grok/skills`, `.grok/skills`, `~/.agents/skills` | Yes; also reads Claude Code marketplaces | `.grok-plugin/…` |
| OpenCode | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | **No.** Plugins are JavaScript/npm modules | none |

Sources: [Claude Code marketplaces](https://code.claude.com/docs/en/plugin-marketplaces),
[Codex plugins](https://developers.openai.com/codex/plugins/build),
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Grok Build](https://docs.x.ai/build/features/skills-plugins-marketplaces),
[OpenCode skills](https://opencode.ai/docs/skills/),
[OpenCode plugins](https://opencode.ai/docs/plugins/),
[Agent Skills specification](https://agentskills.io/specification),
[`npx skills`](https://github.com/vercel-labs/skills).

Consequences:

- **Two channels from one source.** Skill directories reach all four hosts;
  plugins reach Claude, Codex and Grok.
- **Plugin installs are cached copies**, so a plugin cannot use files outside
  its own directory. Each plugin directory must be self-contained.
- **Same-repository catalogs** with `./plugins/<name>` sources are the
  documented default for Claude and Codex.
- **Version conflicts** have a standard fix (Changesets, release-please):
  branches add a change note; one release step bumps versions.

### Evidence from this repository (2026-08-24 to 2026-09-24)

| Measure | Value |
|---|---|
| Merges | 92, and **50 had files changed on both sides** |
| Committed copies | `plugins/` holds 131k lines copied from `skills/`; 247 of 379 commits touched it |
| Top collisions | README inventory (29), ShipLoop `SKILL.md` mostly on `version` (29), its `plugins/` copy (29), Grok catalog (27), three plugin manifests (17–22) |
| Real file sharing between skills | **Only ShipLoop → Improve** (managed controller, consumer contract, review policy), already a deliberate, hash-verified copy of three files. Every other link is a name mention: skills call each other through the host, which works across plugins |

Because only one pair shares files, grouping skills into multi-skill plugins
is unnecessary. One plugin per skill stays.

## Target layout

```text
skill-craft/
  plugins/<leaf>/                    SOURCE, edited directly
    skills/<leaf>/                   SKILL.md, scripts/, references/, …
    agents/<leaf>.md                 agent card, when the skill has one
    .claude-plugin/plugin.json       ┐
    .codex-plugin/plugin.json        │ generated from SKILL.md front-matter
    .cursor-plugin/plugin.json       ┘
  plugins/backchain/                 vendored two-skill bundle (unchanged until Phase 4)
  .claude-plugin/marketplace.json    ┐
  .agents/plugins/marketplace.json   │ generated catalogs
  .grok-plugin/marketplace.json      │
  .cursor-plugin/marketplace.json    ┘
  install.sh                         skill channel for every host, incl. OpenCode
```

## Execution sequence

Work happens in the worktree `.claude/worktrees/repo-layout-26fa71` on branch
`refactor/repo-layout-26fa71`, one commit per phase. Nothing is pushed or
merged until you approve.

### Phase 1: source moves into plugin directories

1. Delete each copied `plugins/<leaf>/skills/<leaf>` and `git mv
   skills/<leaf>` into its place; move `agents/<leaf>.md` to
   `plugins/<leaf>/agents/`.
2. `sync-plugin-views.sh` and `skill-frontmatter-to-plugin-json.js` stop
   copying trees; they only generate manifests, catalogs and the README
   inventory from `plugins/*/skills/*/SKILL.md`.
3. `install.sh` enumerates `plugins/*/skills/*` (bundle members stay excluded,
   as today).
4. Update test, script and CI paths; update `AGENTS.md`,
   `docs/ARCHITECTURE.md`, `docs/distribution.md`.
5. Verify: full hermetic suite matches the pre-change baseline; `install.sh`
   dry run on every host; a real plugin install of ShipLoop on Claude, Codex
   and Grok from the worktree; OpenCode discovers an installed skill.

### Phase 2: versions and generated files change only at release

1. Pull requests add `changes/<leaf>/<slug>.md` (bump level plus one line).
2. `scripts/release.py`: bump versions from pending notes, regenerate metadata,
   qualify, commit, push without force (reusing `release-push.py` guards).
3. CI fails pull requests that edit generated files or `version` fields, or
   change a skill without a change note (docs-only exempt).

### Phase 3: skill-craft becomes the marketplace

1. Generate `.claude-plugin/marketplace.json` and
   `.agents/plugins/marketplace.json` with `./plugins/<leaf>` sources; keep
   the marketplace name `skill-craft-market` so plugin IDs do not change.
2. Move catalog checks worth keeping into `test/`.
3. Replace the `AGENTS.md` rule against a root `.claude-plugin`.
4. Verify `claude plugin validate .` and installs on Claude, Codex and Grok.
5. **Needs your go-ahead (outward-facing):** push, archive
   `skill-craft-market`, re-add marketplaces on your machines.

### Phase 4: Backchain source moves in (separate, later)

Requires a review of what in the private `plan-orchestrator` repository is not
already public. Not part of this worktree run.

### Merge checklist (after approval)

1. Rebase onto current `main` (other branches will have landed; git follows
   renames, but new files added under `skills/` must be moved by hand).
2. Rerun the full hermetic suite.
3. Merge, then run `./install.sh --relink` so installed links point at
   `plugins/<leaf>/skills/<leaf>` instead of `skills/<leaf>`.
4. Tell other in-flight branches to rebase; their `skills/…` edits follow the
   rename automatically in most cases.

## Alternatives considered

| Option | Why not |
|---|---|
| One repository per skill | No gain in repeatability; turns the one real file dependency into a cross-repository pin |
| Group skills into multi-skill plugins | Only one pair shares files; grouping would rename plugin skills for little gain |
| Keep `skills/` as source, generate `plugins/` copies at release | Keeps a 131k-line generated tree and a release-time copy step |
| Symlink `plugins/<leaf>/skills/<leaf>` to `skills/<leaf>` | Depends on each host dereferencing symlinks that leave the plugin directory; not documented for Codex, Grok or Cursor |
| Whole repository as one Claude plugin | Claude-only; Codex would expose every skill in every plugin |

## Verification policy

Hermes is excluded from every phase. Because Phase 1 moves every skill, it
runs the full hermetic suite rather than a footprint subset.
