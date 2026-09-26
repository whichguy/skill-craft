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
| improve-system-prompt | review-bench | Wave 2 (Sheets Chat specific) |
| review-fix-bench | review-bench | Wave 2 |
| review-coverage | (native) | Post-ship residual×2 directive + CLI |

**Retired:** `derive-questions` and `question-bench` (review-bench, Wave 2) were
removed from skill-craft together with the question-ID review-plan contract they
served. `devloop` (the autonomous-engine shim) and its offline companion
`evidence-gates` were archived on 2026-09-26 (owner decision); their source,
engine and local projects are in `~/src-archive/2026-09-26/devloop/`.

**External (not monorepo):** [lennox-s40](https://github.com/whichguy/lennox-s40) — local LAN thermostat control; `catalog/external-plugins.json` pins the standalone repo.

## Stay in claude-craft (suite)

gas-suite/*, wiki-suite/*, async-suite/*, claudecraft/*, comms/*, form990/*, slides-suite/*

## Split / later

node-plan, schedule-plan-tasks, test-delivery-agent, test-prompt-harness,
test-schedule-plan-tasks, review-plan, improve-prompt, optimize-questions,
optimize-system-prompt, ablate-review-plan, validate-questions, compare-questions

## Process for next port

1. Copy `claude-craft/plugins/<suite>/skills/<leaf>/` → `skill-craft/skills/<leaf>/`
2. Neutralize `CLAUDE_PLUGIN_*` paths
3. Put the starting `version:` in `SKILL.md`. Add no `plugins/`, catalog,
   README inventory or `CHANGELOG.md` entry: those are release output.
4. Add `changes/<leaf>/<slug>.md` with `version: <the same version>`
   ([format](../changes/README.md)); a never-released skill may ship at its
   authored version.
5. The next `python3 scripts/release.py` ships it. A skill that stays in
   another repository is instead pinned by commit in
   `catalog/external-plugins.json`.
6. Optional claude-craft SoT note
