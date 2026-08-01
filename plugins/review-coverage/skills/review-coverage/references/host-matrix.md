# review-coverage — host matrix

| Host | Install | Notes |
|------|---------|--------|
| **Claude Code** | `./install.sh --skill review-coverage` → `~/.claude/skills/review-coverage` | Plan mode: Edit plan to add `## Review Coverage`. Optional later: marketplace pin. |
| **Grok** | `./install.sh --skill review-coverage` → `~/.grok/skills/review-coverage` | Same skill body. Hooks not required. |
| **Codex** | `./install.sh --skill review-coverage` → `~/.codex/skills/review-coverage` | Same. No sticky exit gate for this skill. |
| **Hermes** | `./install.sh --skill review-coverage` (materialized copy) | Skill-dir only. |
| **c-thru** | skill-dir or Claude plugin as above | review-plan may call this skill; does not force ExitPlanMode. |

## Optional plan-oversight

If plan-oversight is installed, `PLAN_OVERSIGHT_REQUIRE_RESIDUAL_LOOP` and
`residual_exit_nudge` are **optional** ops tools. This skill works without them.
Product success = directive in the plan + residual×2 after implement.

## Marketplace (later)

```sh
claude plugin marketplace add whichguy/skill-craft-market
claude plugin install review-coverage@skill-craft-market
```

Pin path must be `plugins/review-coverage` (not bare `skills/`).
