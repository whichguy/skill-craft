# claude-craft → skill-craft port inventory

## Legend

| Class | Meaning |
|-------|---------|
| **ported** | Body lives in skill-craft `skills/<leaf>/` |
| **port-now** | Prompt-first candidate; not yet ported |
| **split/later** | Needs suite agents/hooks/scripts; port later or keep wrapper |
| **stay** | Suite-specific; remains only in claude-craft |

## Ported

| Leaf | From plugin | Notes |
|------|-------------|-------|
| skill-interop | (native) | First skill-craft skill |
| prompt-audit | planning-suite | Host paths neutralized |
| prompt-align | planning-suite | Host paths neutralized |
| prompt-migrate | planning-suite | Host paths neutralized |
| prompt-refine | planning-suite | Host paths neutralized |
| c-plan | planning-suite | Host paths neutralized |
| architect | planning-suite | Wave 2 |
| plan-test | planning-suite (`test`) | Renamed leaf to avoid generic `test` |
| compare-prompts | review-bench | Wave 2 |
| derive-questions | review-bench | Wave 2 |
| question-bench | review-bench | Wave 2 |
| improve-system-prompt | review-bench | Wave 2 (Sheets Chat specific) |
| review-fix-bench | review-bench | Wave 2 |
| review-coverage | (native) | Post-ship residual×2 directive + CLI |
| devloop-run | (native) | Hermes devloop engine discovery card |

**External (not monorepo):** [lennox-s40](https://github.com/whichguy/lennox-s40) — local LAN thermostat control; skill-craft-market pins the standalone repo.

## Stay in claude-craft (suite)

gas-suite/*, wiki-suite/*, async-suite/*, claudecraft/*, comms/*, form990/*, slides-suite/*

## Split / later

node-plan, schedule-plan-tasks, test-delivery-agent, test-prompt-harness,
test-schedule-plan-tasks, review-plan, improve-prompt, optimize-questions,
optimize-system-prompt, ablate-review-plan, validate-questions, compare-questions

## Process for next port

1. Copy `claude-craft/plugins/<suite>/skills/<leaf>/` → `skill-craft/skills/<leaf>/`
2. Neutralize `CLAUDE_PLUGIN_*` paths
3. Add `plugins/<leaf>/.claude-plugin/plugin.json` then `./scripts/sync-plugin-views.sh`
4. Pin in skill-craft-market root `.claude-plugin/marketplace.json` only (no faces/* catalog)
5. Tag skill-craft; flip market `ref` only when that leaf’s content/version changes
6. Optional claude-craft SoT note
