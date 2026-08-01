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
| **A — Plan authoring** | Edit plan to add filled `## Review Coverage`; `validate` / `template` / `goal-body` | **All hosts** with skill-dir or Claude plugin install |
| **B — Post-ship residual** | Paste `/goal` from `goal-body --slash`; each turn one **`/review-converge`**; residual×2 | **Claude** when review-converge is available. **Grok / Codex / Hermes**: only if `/review-converge` (or equivalent skill) is installed on that host; otherwise run residual manually using the `/goal` text |

### Mid-session invoke

Yes — name **review-coverage** in the prompt (e.g. “add Review Coverage to this plan”,
“run review-coverage residual after ship”). Requires skill on the host skill path
(skill-dir or marketplace install). Not auto-run on every message.

### Phase B preflight

Before residual×2, confirm:

1. `scripts/review-coverage validate <plan>` exits 0 (or skill path under `~/*/.skills/review-coverage/scripts/review-coverage`).
2. A residual driver is available: skill **review-converge** (or host equivalent).
3. Host can run `/goal` with max-turns / max-budget (or manual multi-turn).

If (2) is missing: still paste the goal-body objective and run residual **manually**
(review → fix material → pathspec commit with verbose learnings → repeat until two
trivial-only cycles).

## Optional plan-oversight

If plan-oversight is installed, residual hooks are **optional adapters**. Product success =
directive in the plan + residual×2 after implement. Prefer hooks that recognize
`## Review Coverage` and/or call this skill’s CLI — legacy
`## Post-Implementation Residual Loop` only is incomplete.
