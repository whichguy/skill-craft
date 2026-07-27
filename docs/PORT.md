# claude-craft → skill-craft port inventory

Generated as part of skill-craft Phase 6. Update when porting.

## Legend

| Class | Meaning |
|-------|---------|
| **ported** | Body lives in skill-craft `skills/<leaf>/` |
| **port-now** | Prompt-first candidate; not yet ported |
| **split/later** | Needs suite agents/hooks/scripts; port later or keep wrapper |
| **stay** | Suite-specific; remains only in claude-craft |

## Ported (this wave)

| Leaf | From plugin | Notes |
|------|-------------|-------|
| skill-interop | (new) | First skill-craft native |
| prompt-audit | planning-suite | Host paths neutralized |
| prompt-align | planning-suite | Host paths neutralized |
| prompt-migrate | planning-suite | Host paths neutralized |
| prompt-refine | planning-suite | Host paths neutralized |
| c-plan | planning-suite | Host paths neutralized; agent names still descriptive |

## Stay in claude-craft (suite)

gas-suite/*, wiki-suite/*, async-suite/*, claudecraft/*, comms/*, form990/*, slides-suite/*

## Split / later

node-plan, schedule-plan-tasks, test-delivery-agent, test-prompt-harness,
test-schedule-plan-tasks, review-plan, improve-prompt, optimize-questions,
optimize-system-prompt, ablate-review-plan, validate-questions, compare-questions

## Port-now backlog

architect (Claude AskUserQuestion + system-architect dispatch),
compare-prompts, derive-questions, improve-system-prompt, question-bench,
review-fix-bench, test (planning-suite)

## Process for next port

1. Copy `claude-craft/plugins/<suite>/skills/<leaf>/` → `skill-craft/skills/<leaf>/`
2. Neutralize `CLAUDE_PLUGIN_*` paths; remove suite-only hard deps where possible
3. Add `plugins/<leaf>/.claude-plugin/plugin.json` then `./scripts/sync-plugin-views.sh`
4. Add pin in skill-craft-market root + faces/claude marketplace.json
5. Optionally thin claude-craft skill to note “install from skill-craft”
