# skill-craft

**Host-neutral portable skills monorepo.** Skills live under `skills/<leaf>/` and install into
Grok, Claude Code, Cursor, Codex, and Hermes skill directories via `install.sh`.

For setup and marketplace distribution across hosts, start with
[docs/distribution.md](docs/distribution.md).

Architecture (layers, binding, install honesty): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Loop-engineering compose (before / during / after DevLoop):
[docs/LOOP-ENGINEERING.md](docs/LOOP-ENGINEERING.md).

This is **not** [claude-craft](https://github.com/whichguy/claude-craft).

| Repo | Role |
|------|------|
| **skill-craft** (this repo) | Skill source of truth and the marketplace for Claude, Codex, Grok and Cursor; `install.sh` for every host including OpenCode |
| **claude-craft** | Claude Code plugin marketplace (GAS, wiki, review suites, …) |

## skill-craft vs claude-craft

- **skill-craft** is host-agnostic. There is no required root `.claude-plugin`. Skills follow an
  [agentskills.io](https://agentskills.io)-style unit: a directory with `SKILL.md` (and optional
  `prompts/`, `scripts/`, `references/`).
- **claude-craft** is a Claude Code **plugin marketplace** (plugins with commands, agents, hooks).
  Different packaging, different install path.

Use **skill-craft** for portable skill packages and their plugin distribution. Use
**claude-craft** for its separate product suites.

## Skills in this monorepo

<!-- skill-craft:inventory:start -->

**21 skills.** Generated from skill frontmatter by `scripts/sync-plugin-views.sh`.

| Skill | Version | Purpose |
|-------|---------|---------|
| [architect](skills/architect/SKILL.md) | 0.1.2 | Design system architecture and make technology decisions. Uses a structured inline design or an available independent reviewer for comprehensive work. |
| [ask-agent](skills/ask-agent/SKILL.md) | 0.7.10 | A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return.… |
| [backchain](skills/backchain/SKILL.md) | 0.6.0 | Use when an implementation task needs a dependency-aware plan before coding: backward planner / backchain / precondition-first planning, dependency DAGs, elaborating incomplete… |
| [c-plan](skills/c-plan/SKILL.md) | 0.1.2 | Resolve ambiguous user prompts by choosing whether to answer now, answer with assumptions, ask 1–2 high-value clarification questions, replan, or stop. Use when the best response… |
| [compare-prompts](skills/compare-prompts/SKILL.md) | 0.1.3 | Compare two prompt versions (A vs B) by running both against a directory of test input files, then evaluating results on three dimensions in priority order: quality > tokens >… |
| [devloop](skills/devloop/SKILL.md) | 0.7.0 | DevLoop (default): invoke the autonomous engine for a machine-verifiable build or debug goal. Use when the user says devloop, DevLoop, /devloop, or wants an isolated fail-closed… |
| [evidence-gates](skills/evidence-gates/SKILL.md) | 0.2.4 | Optional offline evidence gates (freeze/prove/stop with guard digests) for machine-checkable red→green contracts without the autonomous engine. Use when the user says… |
| [improve](skills/improve/SKILL.md) | 0.3.0-rc.5 | Use when a repository candidate needs a deliberate review-and-improvement loop: use recent Git history, make warranted changes, run meaningful checks, and require two consecutive… |
| [improve-agent](skills/improve-agent/SKILL.md) | 0.1.1 | Use when Improve should run in a fresh native agent instead of this conversation: start one agent that runs /improve in its own context, keep useful parent work going, then… |
| [improve-system-prompt](skills/improve-system-prompt/SKILL.md) | 0.1.2 | Benchmark and compare system prompt variants (V2/V2a/V2b/V2c) for Sheets Chat by running test scenarios through the real GAS-side ClaudeConversation pipeline. Tests both… |
| [plan-dispatcher](skills/plan-dispatcher/SKILL.md) | 0.3.0 | Use when executing or resuming an agreed dependency graph with one main dispatcher and parallel native workers: claim ready steps, preserve launch state, collect result evidence,… |
| [plan-test](skills/plan-test/SKILL.md) | 0.1.3 | Generate comprehensive tests for code. Uses an inline strategy or an available independent test specialist for complex components. |
| [prompt-align](skills/prompt-align/SKILL.md) | 0.1.2 | Compare an agent or skill prompt against its test harness skill for phase-model, skip-condition, and wiring consistency. Reports mismatches and identifies which file is… |
| [prompt-audit](skills/prompt-audit/SKILL.md) | 0.1.2 | Audit an agent or skill prompt file for internal inconsistencies (phase numbering, behavioral contracts, terminology, stale references). Produces a Q&A with info-gain scores, a… |
| [prompt-migrate](skills/prompt-migrate/SKILL.md) | 0.1.2 | TDD-based prompt migration — given a target agent/skill prompt and a remediation list, writes failing tests first, then updates the prompt to make them pass. Commits remain… |
| [prompt-refine](skills/prompt-refine/SKILL.md) | 0.1.2 | Full prompt-improvement workflow — runs prompt-audit to find inconsistencies, presents a remediation plan, then runs prompt-migrate to apply fixes and prompt-align to verify… |
| [review-coverage](skills/review-coverage/SKILL.md) | 0.3.1 | Add a post-ship improve-to-exhaustion directive to a plan, or run that directive after implementation. Invoke like any skill: /review-coverage, "review-coverage on this plan",… |
| [review-fix-bench](skills/review-fix-bench/SKILL.md) | 0.1.2 | Compare two code-review prompt versions against supplied fixture ground truth using an explicitly configured external benchmark runner. Reports an F1-based verdict only when the… |
| [shiploop](skills/shiploop/SKILL.md) | 0.32.2 | Markdown-authoritative delivery harness. Start or resume once, follow the script's current action packet, and submit its exact completion call until the script reports completion… |
| [shiploop-e2e-audit](skills/shiploop-e2e-audit/SKILL.md) | 0.4.6 | Run the ShipLoop test harness and audit its retained graph, review, test, product and incremental-change evidence. Use for ShipLoop mock checks, live one-shot E2E smoke/full… |
| [skill-interop](skills/skill-interop/SKILL.md) | 0.2.5 | Use when authoring or reviewing a portable multi-host agent skill (Grok, Claude Code, Codex, Hermes): scaffold a prompt-only skill, make a skill host-agnostic, create skill… |

<!-- skill-craft:inventory:end -->

Operator guides: [ShipLoop](skills/shiploop/README.md),
[current chain operator contract](skills/shiploop/references/parallel-chain.md#bind-the-selected-packages-and-reviewed-graph),
[historical planning-artifact handoff implementation/qualification record](docs/shiploop-planning-artifact-handoff-plan-2026-09-19.md)
(supporting references; dispatcher step contracts remain the worker assignment),
[Improve and release-candidate limits](skills/improve/README.md), and
[completed ShipLoop proposals](docs/shiploop-proposal-closeout.md).

**External compatibility:** Per-step ShipLoop chains require a selected compatible
Plan Dispatcher and an Ask-Agent helper declaring all five required
managed-worktree capabilities (no version floor). Both parallel and serial modes
use the current managed-worktree lifecycle and v6 binding. Every chain operation
refuses an earlier binding; preserve its worktrees and ledger and bind a new
chain. Follow
[the chain binding requirements](skills/shiploop/references/parallel-chain.md#bind-the-selected-packages-and-reviewed-graph).

**External (not in this monorepo):** [lennox-s40](https://github.com/whichguy/lennox-s40) — thermostat skill; install from that clone. Its catalog pin is in `catalog/external-plugins.json`.

Port inventory: [docs/PORT.md](docs/PORT.md). After editing a skill, add a
change note under `changes/<leaf>/` ([format](changes/README.md)) instead of
editing its version. `plugins/`, the catalogs and this inventory are release
output written by `python3 scripts/release.py`; see the
[release checklist](docs/skill-release-checklist.md).
## Install (`install.sh`)

Installs `skills/<leaf>` into local skill homes. Claude/Grok/Codex/Cursor get **symlinks**.
Hermes gets a **materialized copy** (refreshable managed install; foreign real trees skipped).
Never clobbers a foreign real file/directory. Wrong/dangling symlinks are only replaced with `--relink`.
Switching an existing symlink install to a managed copy needs `./install.sh --copy --relink`;
without `--relink` the symlink is skipped. `--relink` is the only spelling (no `--force`), and
`--skill all` the only all-skills value.
Source leaf `devloop` installs as dest `devloop` on Claude/Grok/Codex/Cursor.
Hermes card install is skipped (the engine owns `software-development/devloop`).

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
./install.sh --cursor-only
./install.sh --grok-only --claude-only --cursor-only --codex-only  # these four hosts
./install.sh --relink                # fix wrong/dangling symlinks
./install.sh --copy                  # force copy mode (all hosts)
./install.sh --symlink               # force symlink (overrides Hermes copy default)
./install.sh --status                # report state=… per host (no writes); Claude also reports plugin-track / double-install
./install.sh --uninstall             # remove only owned installs
./install.sh --dry-run               # print actions only
```

| Host | Destination | Mode |
|------|-------------|------|
| Claude Code | `~/.claude/skills/<dest>` | symlink |
| Grok | `~/.grok/skills/<dest>` | symlink |
| Codex | `~/.codex/skills/<dest>` | symlink |
| Cursor | `~/.cursor/skills/<dest>` | symlink (never `~/.cursor/skills-cursor`) |
| Hermes | `~/.hermes/skills/software-development/<dest>` | **copy** (+ `.skill-craft/<dest>.json` marker) |

`dest` is the source leaf. Leaf `devloop` skips Hermes so it cannot overwrite the engine.

`install.sh` never writes host hook config. A marketplace install carries a skill's hooks:
its `host-hooks.json` is generated into each host's plugin hook file, which Claude Code,
Grok, Codex and Cursor load with the plugin. For a skill-directory install, ShipLoop's
own `scripts/shiploop-hook install --host HOST` registers its
[keepalive](skills/shiploop/references/keepalive.md) hooks. Use one route per host.

With `--agents`: `~/.claude/agents/<leaf>.md` and `~/.grok/agents/<leaf>.md` when present.
Re-running install refreshes managed Hermes copies; foreign Hermes trees print `Skipped (foreign)`.

## Marketplace

This repository is the marketplace. Claude and Codex read the root catalogs
`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`; Grok
and Cursor read `.grok-plugin/` and `.cursor-plugin/`. OpenCode has no skill
marketplace and uses `install.sh`.

```sh
claude plugin marketplace add whichguy/skill-craft
claude plugin install skill-interop@skill-craft-market

codex plugin marketplace add whichguy/skill-craft
codex plugin list --marketplace skill-craft-market --available --json
codex plugin add skill-interop@skill-craft-market
```

The Claude and Codex catalogs keep the name `skill-craft-market`, so plugin
IDs are unchanged from the former `whichguy/skill-craft-market` repository; to
move an existing registration without uninstalling its plugins, follow
[distribution.md](docs/distribution.md#moving-from-the-former-whichguyskill-craft-market-repository).
Register a local checkout by passing its absolute root to `marketplace add`.
Install only skills not already exposed by skill-dir. Start a new Codex thread
after installing a plugin.

### Install lifecycle

| Mode | Action |
|------|--------|
| **Dev (skill-dir)** | `./install.sh --skill <name> [--agents] [--relink]` |
| **Claude, Codex or Grok plugin** | install from this marketplace (above) |
| **Upgrade skill-dir** | `git pull` + re-run install; use `--relink` if links point elsewhere |
| **Uninstall skill-dir** | `./install.sh --skill <name> --uninstall` (removes only owned installs, every host) |


### Grok and Cursor marketplaces

This repo also contains generated native catalogs at `.grok-plugin/marketplace.json`
and `.cursor-plugin/marketplace.json`. Both reference the same generated `plugins/<leaf>`
packages in this checkout. They omit
the external plugins listed in `catalog/external-plugins.json`. Only
`scripts/release.py` regenerates the catalogs. See
[distribution instructions](docs/distribution.md) for local use, updates, and publication.

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
bash test/run-all.sh                                  # full hermetic regression
bash test/run-all.sh --group quick --changed-from origin/main  # baseline + suites for your changes
bash test/run-all.sh --group ask-agent                # helper and consumer boundaries
bash test/run-all.sh --group shiploop-composition     # cross-skill integration
bash test/run-all.sh --group ask-agent --group shiploop-composition --list
```

Local and GitHub runs share one explicit catalog, and `test/run-all.sh` is the
only runner command. Code PRs and every `main` push run full regression;
allowlisted documentation-only PRs run smoke. Full includes the source E2E
apparatus, with balanced ShipLoop shards. CI uses latest stable runtimes and retains source/version/result receipts.
Component unions execute shared entries once. See [test/README.md](test/README.md)
for the exact policy, cleanup rules, current-Dispatcher qualification and the
separate installed/native/live evidence boundaries.

Hermes is an optional integration, not a prerequisite for repository CI.
Mocked host-binding tests remain in the hermetic suite; tests needing real engines,
installed skills, credentials or environment-specific projects are explicitly
opt-in through `bash test/run-integration.sh --help`.
See [test/README.md](test/README.md) for test groups, prerequisites and evidence boundaries.

## License

MIT — see [LICENSE](LICENSE).

## Shared plugin packages

Skill **SoT** is always `skills/<name>/`. Marketplace hosts share one generated **plugin view**:

```text
plugins/skill-interop/
  .claude-plugin/plugin.json
  .cursor-plugin/plugin.json
  skills/skill-interop/   # materialised copy of skills/skill-interop (not a symlink)
  agents/… (optional real files)
```

Claude `git-subdir` installs **do not follow** relative symlinks outside the pin path,
so the plugin view is a **materialised copy**. `plugins/` is release output:
`scripts/release.py` regenerates it with `scripts/sync-plugin-views.sh` and
commits it, so between releases it lags `skills/`. After editing a skill, add a
change note and check a build of the current source instead:

```sh
python3 scripts/build-packages.py "$(mktemp -d)/build"   # prints the build dir
```

Package tests build the same way (`test/package_build.py`). Never commit
`sync-plugin-views.sh` output by hand. Copy and `--check` ignore `__pycache__/`
and `*.pyc`; bytecode next to a leaf script is not view drift.

Catalog entries select `./plugins/skill-interop`, not the bare skill leaf.
