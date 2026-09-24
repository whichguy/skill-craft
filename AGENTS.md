# AGENTS.md — skill-craft

Host-neutral **portable skills** monorepo. Not Claude-first; not a product harness.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Layout

- **`skills/<leaf>/`** — skill source of truth (`SKILL.md`, optional `prompts/`, `scripts/`, `references/`)
- **`agents/<leaf>.md`** — thin agent cards that point at the skill (Claude/Grok only)
- **`install.sh`** — multi-host skill-dir install (symlink Claude/Grok/Codex/Cursor/OpenCode; **copy** Hermes)
- **`bundles/<plugin>/`** — vendored multi-skill plugin sources (`bundle.json` + `PROVENANCE.json`); refresh only with `scripts/sync-vendored-bundles.py`, never hand-edit; `install.sh` never installs them
- **`plugins/<leaf>/`** — release output: plugin packages (also `plugins/<plugin>/` for a bundle) written only by `scripts/release.py`; never edit here
- **`.claude-plugin/`, `.agents/plugins/`, `.grok-plugin/`, `.cursor-plugin/`** — release output: the marketplace catalogs for Claude, Codex, Grok and Cursor
- **`catalog/external-plugins.json`** — plugins published from other repositories, pinned by commit
- **`changes/<leaf>/*.md`** — pending change notes; `scripts/release.py` turns them into a release
- **`test/`** — hermetic checks for skills and install

## Install

```sh
./install.sh                      # all hosts, every skills/<leaf>
./install.sh --skill skill-interop
./install.sh --skill all --agents
./install.sh --from /path/to/pkg
./install.sh --claude-only --dry-run
```

Hosts: Claude (`~/.claude/skills`), Grok (`~/.grok/skills`), Codex (`~/.codex/skills`), Cursor (`~/.cursor/skills`),
OpenCode (`${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills`), Hermes (`~/.hermes/skills/software-development`, materialized copy + `.skill-craft` marker).

## Conventions

- Skills are **prompt-first** and host-agnostic. Prefer one CLI contract for scripts.
- Layer 0/1/2 = contract / prompts / scripts (do not renumber). Binding + honesty in ARCHITECTURE.
- This repository is the marketplace for every host. `.claude-plugin/marketplace.json` (Claude; Codex legacy fallback), `.agents/plugins/marketplace.json` (Codex), `.grok-plugin/` and `.cursor-plugin/` are generated side by side from skill frontmatter; none is another source of skill metadata. Plugins published from other repositories are listed, with full commit pins, in `catalog/external-plugins.json`. `skill-craft-market` is retired.
- **Source vs release output.** Edit `skills/`, `agents/`, `bundles/`, `catalog/`. `plugins/`, the catalogs, the README inventory, `CHANGELOG.md` and every `version:` field are release output: only `scripts/release.py` writes them, in a commit with a `Skill-Craft-Release:` trailer. CI (`scripts/check-release-boundary.py`) rejects ordinary commits that touch them.
- **Every skill change adds a note** `changes/<leaf>/<slug>.md` (`bump: patch|minor|major`; see `changes/README.md`) instead of editing its version, or carries a `No-Change-Note: <reason>` trailer.
- Tests that need packages read `scripts/build-packages.py` output (via `test/package_build.py`), never the committed `plugins/`.
- Unit of a skill: agentskills.io-style package (`SKILL.md` + optional tree).
- Discovery ≠ execution for engine multi-host claims.

## First skill

**skill-interop** — author/review portable multi-host skills (Grok, Claude Code, Codex, Hermes).
