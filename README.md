# skill-craft

**Host-neutral portable skills monorepo.** Skills live under `skills/<leaf>/` and install into
Claude, Grok, Codex, and Hermes skill directories via `install.sh`.

This is **not** [claude-craft](https://github.com/whichguy/claude-craft).

| Repo | Role |
|------|------|
| **skill-craft** (this repo) | Skill source of truth — prompt packages, scripts, tests |
| **skill-craft-market** | Marketplace *adapters* only — pins/docs, **no** skill prompt bodies |
| **claude-craft** | Claude Code plugin marketplace (GAS, wiki, review suites, …) |

## skill-craft vs claude-craft

- **skill-craft** is host-agnostic. There is no required root `.claude-plugin`. Skills follow an
  [agentskills.io](https://agentskills.io)-style unit: a directory with `SKILL.md` (and optional
  `prompts/`, `scripts/`, `references/`).
- **claude-craft** is a Claude Code **plugin marketplace** (plugins with commands, agents, hooks).
  Different packaging, different install path.

If you want portable skills that work across hosts, use **skill-craft**. If you want Claude Code
plugins, use **claude-craft**.

## First skill: skill-interop

Author or review skills so they work across **Grok, Claude Code, Codex, and Hermes**:

- prompt-first design, optional scripts with one CLI contract
- scaffold a new skill package
- multi-host install and marketplace facade helpers

```sh
# Install skill-interop into all four host skill homes
./install.sh --skill skill-interop

# Also symlink thin agent cards (Claude + Grok)
./install.sh --skill skill-interop --agents
```

## Install (`install.sh`)

Symlinks `skills/<leaf>` into local skill homes. Never overwrites a real file/directory.
Wrong/dangling symlinks are only replaced with `--relink`.

```sh
./install.sh                         # all hosts, every skills/<leaf>
./install.sh --skill skill-interop   # one skill
./install.sh --skill all             # explicit: all skills under skills/
./install.sh --from /path/to/pkg     # external package (leaf = basename)
./install.sh --agents                # also agents/<leaf>.md → Claude/Grok
./install.sh --claude-only           # single host
./install.sh --grok-only
./install.sh --codex-only
./install.sh --hermes-only
./install.sh --relink                # fix wrong/dangling symlinks
./install.sh --dry-run               # print actions only
```

| Host | Destination |
|------|-------------|
| Claude Code | `~/.claude/skills/<leaf>` |
| Grok | `~/.grok/skills/<leaf>` |
| Codex | `~/.codex/skills/<leaf>` |
| Hermes | `~/.hermes/skills/software-development/<leaf>` |

With `--agents`: `~/.claude/agents/<leaf>.md` and `~/.grok/agents/<leaf>.md` when present.

## Marketplace pins (sibling repo)

**skill-craft-market** holds host-facing marketplace adapters that **pin** skills in this repo
(e.g. Claude `marketplace.json` with `git-subdir` → `whichguy/skill-craft` path
`skills/skill-interop`). Catalog only — skill prompt bodies stay here.

```sh
# Example (after skill-craft-market is published)
# claude plugin marketplace add whichguy/skill-craft-market  # path faces/claude
```

See the skill-craft-market README for per-host faces.

## Unit of a skill (agentskills.io)

A skill is a directory containing at least:

```text
skills/<name>/
  SKILL.md                 # frontmatter + card
  prompts/                 # optional prompt bodies
  scripts/                 # optional CLI tools
  references/              # optional docs/checklists
```

## Tests

```sh
bash test/run-all.sh
```

## License

MIT — see [LICENSE](LICENSE).
