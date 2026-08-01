---
name: review-coverage
description: >
  Add a post-ship improve-to-exhaustion directive to a plan, or run that
  directive after implementation. Use when: writing or reviewing a plan that
  needs residual×2 after implement; ensuring the plan carries a /goal-ready
  Review Coverage section; running coverage after ship against plan specs
  (forward + reverse). Not for pre-exit plan quality (use review-plan) or
  raw residual×2 engine mechanics alone (use review-converge under /goal).
allowed-tools: all
version: 0.2.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# Review Coverage

**Plan directive** for post-implementation improve-to-exhaustion — not an exit hook
and not a second review-plan. Residual campaigns are **finite** (residual×2 success
or stopped halt) — never open loops.

```text
review-plan      →  plan quality (pre-exit)
review-coverage  →  plan directive: residual×2 after implement   ← THIS SKILL
review-converge  →  default residual×2 engine (driver only)
review-fix      →  optional first-pass code review before coverage
improve-loop     →  optional broader improve campaign
```

Center of gravity: **the plan body**. Hooks are optional sugar; they are not
required for this skill to work.

## Definitions

| Term | Meaning |
|------|---------|
| **Review Coverage** | Durable plan H2 `## Review Coverage` + this skill. Answers: after ship, how do we prove code matches specs and **stop** when proof is stable? |
| **residual** | Post-ship forward (specs→code) + reverse (diff vs Base ref); material fixes only; pathspec commits. |
| **residual×2** | **Stop rule:** Status `complete` only after **two consecutive clean** residual rounds, with the **second** clean running Test command green. Not “run twice and quit.” Any non-clean resets the streak. |
| **`/goal`** | Outer multi-turn driver (must have host max-turns/budget). Pastes Objective; re-checks Status after every round. |
| **`/review-converge`** | Default Driver: **one** residual round per invocation. |
| **complete** | residual×2 success (objective-met) + Log landed. |
| **stopped(...)** | Terminal halt without residual×2 success; still ends `/goal` so the campaign cannot spin forever. |

### Nesting

```text
## Review Coverage (plan text)
  → paste Objective into /goal (capped outer loop)
    → each turn: exactly one /review-converge
      → residual×2 + same-error×3 + no-progress×3 + max-cycles (default 12)
```

## When to use

- Non-trivial **code** plans about to be approved — ensure `## Review Coverage` is in the plan.
- After implementation is green — run the section’s `/goal` residual×2 campaign.
- User asks for residual / improve-to-exhaustion / post-ship coverage of the plan.

Skip pure doc-only one-line plans unless the user asks.

## Phase A — Plan authoring / review (edit the plan)

1. Read the plan path (or most recent plan under `~/.claude/plans/` if in Claude plan mode).
2. If `## Review Coverage` already present and filled (or waived) → stop Phase A.
3. Otherwise **Edit the plan** to insert the section from
   `references/review_coverage.md` (or `scripts/review-coverage template`).
4. Fill when known:
   - **Base ref** — commit SHA before implement
   - **Target paths** — concrete pathspecs (no TBD)
   - **Test command** — exact suite command
   - **Driver** — default `review-converge under /goal`
   - **Max rounds** — default 12 (anti-loop hard wall)
5. Do **not** use heading `## Post-Implementation Residual Loop` (collides with
   review-plan Q-E2 “Post-Implementation Workflow or equivalent”).

Waiver (only if residual is intentionally out of scope):

```text
None — residual loop waived: <concrete reason>
```

Phase A success: the **approved plan file** contains the directive. No ExitPlanMode
gate, soft_exit, or REQUIRE env is required.

## Phase B — Post-implement (run residual×2)

1. Implementation landed; suite green; optional first-pass `/review-fix` done.
2. Read `## Review Coverage` from the plan (or `scripts/review-coverage goal-body --plan PATH`).
3. Paste Objective into **`/goal`** with host **max-turns** and **max-budget** set.
4. Each turn: **exactly one** `/review-converge` round (or the Driver named in the section).
5. After every round, re-read Status and apply Exit conditions:
   - `complete` + landed → **EXIT success** (residual×2 met)
   - `stopped(...)` + landed → **EXIT halt** (not success)
   - `active` and rounds ≥ Max → force `stopped (max-cycles)`, land, EXIT
   - else continue one more unit only
6. Every cycle does **both**:
   - **Forward:** specs / anchors / intent → code; pathspec commit material fixes.
   - **Reverse:** diff vs **Base ref**; regressions, violated anchors, side effects; fix or waive.
7. **Success** only when Status is **`complete`** after two consecutive clean rounds **and**
   the second clean ran Test command successfully **and** Log landed.  
   **`stopped(...)` is not success.** Never unlimited ralph. Never continue after complete/stopped.

## Helpers (optional)

```sh
# From skill package root (after install.sh or in skill-craft clone)
scripts/review-coverage template
scripts/review-coverage template --short
scripts/review-coverage goal-body --plan /path/to/plan.md
scripts/review-coverage validate /path/to/plan.md
```

Validate is advisory lint for agents/humans — not soft_exit dependency.
Unfilled templates (including example `None — residual loop waived: <reason>`)
**fail** `validate` — a placeholder waiver reason is not a real waiver.
`goal-body` emits a finite residual Objective (success/stop/max-cycles) for `/goal` paste.

## What this skill is not

- Not review-plan (pre-exit quality gates).
- Not a forced ExitPlanMode hook product.
- Not review-converge itself (that is the default **driver** named in the section).
- Not an infinite residual loop — always residual×2 success or stopped halt.

## Install

```sh
# skill-craft clone
./install.sh --skill review-coverage

# Claude plugin (after marketplace pin)
# claude plugin install review-coverage@skill-craft-market
```

See `references/host-matrix.md`.
