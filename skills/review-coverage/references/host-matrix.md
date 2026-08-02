# review-coverage — host matrix

## Install (skill-dir — all hosts)

```sh
# from skill-craft clone
./install.sh --skill review-coverage
```

| Host | Destination | Notes |
|------|-------------|--------|
| **Claude Code** | `~/.claude/skills/review-coverage` | Mid-session skill invoke after install |
| **Grok** | `~/.grok/skills/review-coverage` | Same body; mid-session if skill-dir present |
| **Codex** | `~/.codex/skills/review-coverage` | Same |
| **Hermes** | materialized under Hermes skills tree | Same |

## Marketplace (Claude plugin)

```sh
claude plugin marketplace add whichguy/skill-craft-market
claude plugin install review-coverage@skill-craft-market
```

Pin path: **`plugins/review-coverage`** (not bare `skills/`). Prefer a **release tag** that
includes current `main` product; skill-dir install tracks the skill-craft checkout instead.

## Phase support

| Phase | What | Supported where |
|-------|------|-----------------|
| **A — Plan authoring** | Skill invoke: agent edits plan to add filled `## Review Coverage` | **All hosts** with skill-dir or Claude plugin install |
| **B — Post-ship residual** | Skill invoke: agent composes `/goal` + one **`/review-converge`** per turn; residual×2 | **Claude** when review-converge is available. **Grok / Codex / Hermes**: if `/review-converge` (or equivalent) is installed; else residual manually from the composed `/goal` text |

### Mid-session invoke (primary)

Yes — invoke like any skill:

```text
/review-coverage
/review-coverage path/to/plan.md
add Review Coverage to this plan
run residual×2 / post-ship coverage for this plan
```

Requires skill on the host skill path (skill-dir or marketplace install). Not auto-run on
every message. **Do not** require the user to shell `scripts/review-coverage …` as the
entrypoint; CLI helpers are optional lint/print only.

### Phase B preflight (agent judgment)

Before residual×2, the skill agent confirms (no script required):

1. Plan has filled `## Review Coverage` (or run Phase A).
2. Residual driver available: skill **review-converge** (or host equivalent).
3. Host can run `/goal` with max-turns / max-budget (or manual multi-turn).

Optional CLI: `scripts/review-coverage preflight --plan <plan>` / `goal-body --slash`.

## Residual campaign hygiene

Before claiming a clean residual×2 streak:

1. **Pathspec commits only** under Target paths — never `git add -A` / `.` / `-u`.
2. After every package edit: `scripts/sync-plugin-views.sh review-coverage` (or full sync)
   so plugin drift cannot fail the suite mid-streak.
3. Do not start residual with unfinished WIP in Target paths (plugin/version drift).
4. Prefer skill Phase B preflight, or optional `run-card --preflight` for humans.

## Optional plan-oversight

If plan-oversight is installed, residual hooks are **optional adapters**. Product success =
directive in the plan + residual×2 after implement. Prefer hooks that recognize
`## Review Coverage` and/or call this skill’s CLI — legacy
`## Post-Implementation Residual Loop` only is incomplete. Do not claim Review Coverage
support if the nudge only matches the legacy H2.
