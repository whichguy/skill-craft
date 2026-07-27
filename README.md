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

## Skills in this monorepo

| Skill | Purpose |
|-------|---------|
| **skill-interop** | Author/review portable multi-host skills; scaffold; install; marketplace facade |
| **c-plan** | Ambiguous-prompt clarifier (EVQ / FASTPATH) |
| **prompt-audit** | Audit agent/skill prompts for internal inconsistencies |
| **prompt-align** | Diff a prompt vs its test harness |
| **prompt-migrate** | TDD-style prompt migration |
| **prompt-refine** | Audit → remediate → migrate → align workflow |
| **architect** | Architecture / tech decisions (suite agent dispatch may be host-specific) |
| **plan-test** | Generate tests (ported from planning-suite `test`) |
| **compare-prompts** | A/B compare prompt versions |
| **derive-questions** | Research-derived planning questions library |
| **question-bench** | Benchmark review-plan question subsets |
| **improve-system-prompt** | Benchmark system prompt variants (Sheets Chat lineage) |
| **review-fix-bench** | A/B benchmark code reviewer agent prompts |

Port inventory: [docs/PORT.md](docs/PORT.md). After editing any skill body, run:

```sh
./scripts/sync-plugin-views.sh
./scripts/sync-plugin-views.sh --check
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

**skill-craft-market** holds host-facing marketplace adapters that **pin** skills in this repo.
Claude pins use the **plugin view** path (`plugins/<name>`), never the bare skill leaf.
Catalog only — skill prompt bodies stay here.

```sh
claude plugin marketplace add whichguy/skill-craft-market
claude plugin install skill-interop@skill-craft-market
```

### Install lifecycle

| Mode | Action |
|------|--------|
| **Dev (skill-dir)** | `./install.sh --skill <name> [--agents] [--relink]` |
| **Claude plugin** | install via skill-craft-market (above) |
| **Upgrade skill-dir** | `git pull` + re-run install; use `--relink` if links point elsewhere |
| **Uninstall skill-dir** | remove host symlink under `~/.{claude,grok,codex}/skills/<name>` (and Hermes path) |

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

## Claude plugin view (optional distribution)

Skill **SoT** is always `skills/<name>/`. For Claude marketplace installs we also ship a thin **plugin view**:

```text
plugins/skill-interop/
  .claude-plugin/plugin.json
  skills/skill-interop/   # materialised copy of skills/skill-interop (not a symlink)
  agents/… (optional real files)
```

Claude `git-subdir` installs **do not follow** relative symlinks outside the pin path,
so the plugin view is a **materialised copy**. Keep it in sync:

```sh
./scripts/sync-plugin-views.sh          # after editing skills/
./scripts/sync-plugin-views.sh --check  # CI / pre-commit
```

`skill-craft-market` pins `path: "plugins/skill-interop"`, not the bare skill leaf.
