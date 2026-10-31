# AGENTS.md — skill-craft

Host-neutral **portable skills** monorepo. Not Claude-first; not a product harness.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Layout

- **`skills/<leaf>/`** — skill source of truth (`SKILL.md`, optional `prompts/`, `scripts/`, `references/`)
- **`agents/<leaf>.md`** — thin agent cards that point at the skill (Claude/Grok only)
- **`install.sh`** — multi-host skill-dir install (symlink Claude/Grok/Codex/Cursor/OpenCode; **copy** Hermes)
- **`plugins/skill-craft/`** — release output: the one plugin package bundling every skill (`/skill-craft:<leaf>`), written only by `scripts/release.py`; never edit here
- **`.claude-plugin/`, `.agents/plugins/`, `.grok-plugin/`, `.cursor-plugin/`** — release output: the marketplace catalogs for Claude, Codex, Grok and Cursor
- **`catalog/external-plugins.json`** — plugins published from other repositories, pinned by commit
- **`changes/<leaf>/*.md`** — pending change notes; `scripts/release.py` turns them into a release
- **`test/`** — hermetic checks for skills and install

## Install

```sh
./install.sh                      # OpenCode (plugin hosts use skill-craft@whichguy), every skills/<leaf>
./install.sh --skill skill-interop
./install.sh --claude-only --skill all --agents
./install.sh --from /path/to/pkg
./install.sh --claude-only --dry-run
```

Hosts: Claude (`~/.claude/skills`), Grok (`~/.grok/skills`), Codex (`~/.codex/skills`), Cursor (`~/.cursor/skills`),
OpenCode (`${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills`), Hermes (`~/.hermes/skills/software-development`, materialized copy + `.skill-craft` marker).

## Conventions

- Skills are **prompt-first** and host-agnostic. Prefer one CLI contract for scripts.
- Layer 0/1/2 = contract / prompts / scripts (do not renumber). Binding + honesty in ARCHITECTURE.
- This repository is the marketplace for every host. `.claude-plugin/marketplace.json` (Claude; Codex legacy fallback), `.agents/plugins/marketplace.json` (Codex), `.grok-plugin/` and `.cursor-plugin/` are generated side by side from skill frontmatter; none is another source of skill metadata. Every catalog is named `whichguy` (the publisher) and lists one local plugin, `skill-craft` (install `skill-craft@whichguy`), whose version lives in `catalog/skill-craft-plugin.json`. Plugins published from other repositories are listed, with full commit pins, in `catalog/external-plugins.json`.
- **Source vs release output.** Edit `skills/`, `agents/`, `catalog/`. `plugins/`, the catalogs, the README inventory, `CHANGELOG.md`, every `version:` field and the `version` in `catalog/skill-craft-plugin.json` are release output: only `scripts/release.py` writes them, in a commit with a `Skill-Craft-Release:` trailer. CI (`scripts/check-release-boundary.py`) rejects ordinary commits that touch them, and checks out each release commit in a temporary worktree to verify its output matches its source. Never commit `sync-plugin-views.sh` output by hand.
- **Release preflight.** `scripts/release.py` (and its `--dry-run`) refuses a release that ships the `shiploop` skill unless every commit since the last release (all of history before the first) that changes `skills/shiploop/` or `changes/shiploop/` comes before the latest commit touching `test/shiploop_e2e/LEARNINGS.md`, or carries its own `No-E2E-Round: <reason>` trailer (final paragraph with `Co-Authored-By:`, non-empty reason). The refusal names the uncovered commits. Releases that do not ship `shiploop` are not asked. The ShipLoop E2E round and its journal entry come after the change they vouch for.
- **Every skill change adds a note** `changes/<leaf>/<slug>.md` (`bump: patch|minor|major`; see `changes/README.md`) instead of editing its version, or carries a `No-Change-Note: <reason>` trailer (per commit, in the final message paragraph with `Co-Authored-By:`). An `agents/<leaf>.md` edit needs a note too. Only `scripts/release.py` deletes a pending note. Merge verified work directly to `main`; do not create PRs. Preserve individual commits and their learning messages; never squash.
- Tests that need packages read `scripts/build-packages.py` output (via `test/package_build.py`), never the committed `plugins/`.
- Unit of a skill: agentskills.io-style package (`SKILL.md` + optional tree).
- Discovery ≠ execution for engine multi-host claims.

## Decisions

Owner, 2026-10-30: before each subsequent change and commit, read the full relevant Git commit messages, including
empty learning-only commits. Recent messages are a starting point; search older history for the affected behavior,
paths and referenced decisions. Use prior measurements, rejected approaches and known unknowns to decide what to do
or avoid. Preserve earlier decisions unless new evidence or an explicit owner decision warrants changing them.

Every completed unit of work gets a very verbose commit message describing what was learned, the actual measurements
and checks, the decision, contrary evidence, remaining unknowns and evidence locations. Cite the full hashes and specific
contents of earlier commits that materially influenced the decision. Distinguish a generic ShipLoop improvement from an
E2E apparatus improvement or retained learning. Unaccepted candidate code stays out of `main`.

Owner, 2026-10-28: a session makes routine decisions itself and records each one (what, why, the evidence) in the
commit message or journal where the work lands. Routine:

- publishing a release once `scripts/release.py`'s preflight and CI pass on a commit that fast-forwards `main`, and
  refreshing the hosts after it;
- choosing between equivalent fixes;
- launching verification runs.

Ask the owner first for anything one-way or that sets direction:

- deleting data, branches or runs that are not the session's own;
- deploying to the owner's orgs or other external services;
- changing a default that breaks comparability with earlier evidence (the E2E subject model, a baseline);
- a ShipLoop product behaviour trade-off, or any limit on ShipLoop's loops.

Another session's runs, branches and releases stay its own: message that session instead of acting on them.

## First skill

**skill-interop** — author/review portable multi-host skills (Grok, Claude Code, Codex, Hermes).
