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
version: 0.2.1
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
review-fix       →  optional first-pass code review before coverage
improve-loop     →  optional broader improve campaign
```

Center of gravity: **the plan body**. Hooks are optional sugar; they are not
required for this skill to work.

## Definitions

| Term | Meaning |
|------|---------|
| **Review Coverage** | Durable plan **H2 only** `## Review Coverage` + this skill (H1/H3+ headings are not recognized). It answers: after ship, how do we prove code matches specs and **stop** when proof is stable? |
| **Status / Log / landed** | When the Driver is `review-converge`, repo-root `REVIEW_CONVERGE.md` is the ledger: Status selects the next branch; Log records each round. **Landed** means latest Log `Committed: yes` and a `review-converge: round N —` commit subject (or legacy `grok-review-converge: round N —`). |
| **residual** | Post-ship forward (specs→code) + reverse (diff vs Base ref); material fixes only; pathspec commits. |
| **residual×2** | **Stop rule:** “only trivial changes remain for 2 consecutive cycles.” Material issues block the streak; minors/P2 are trivial. The second clean runs Test command PASS, and any material finding resets the streak. |
| **`/goal`** | The outer multi-turn driver. It is the **literal paste command** emitted by `scripts/review-coverage goal-body --plan … --slash`; do not paraphrase its body. |
| **`/review-converge`** | Default inner Driver: exactly **one** residual round per invocation. |
| **complete** | residual×2 success plus a landed Log. |
| **stopped (...)** | Terminal halt without residual×2 success; it still ends `/goal` so the campaign cannot spin forever. |

The static `/goal` logic is byte-exact:

```text
/goal quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial changes remain for 2 consecutive cycles
```

### Nesting

```text
## Review Coverage (plan text)
  → outer /goal: static complete-when sentence + plan bindings
    → each turn: one /review-converge
```

## When to use

- Non-trivial **code** plans about to be approved — ensure `## Review Coverage` is in the plan.
- After implementation is green — run the section’s `/goal` residual×2 campaign.
- User asks for residual / improve-to-exhaustion / post-ship coverage of the plan.

Skip pure doc-only one-line plans unless the user asks.

## Phase A — Plan authoring / review (edit the plan)

1. Read the host-neutral plan path supplied for the work (it need not live in a
   Claude-specific plans directory).
2. If `## Review Coverage` already present and filled (`scripts/review-coverage validate <PLAN_PATH>` exits 0) or truly waived → stop Phase A.
3. Otherwise **edit the plan** to insert the section from
   `references/review_coverage.md` (or `scripts/review-coverage template`).
4. Fill when known:
   - **Base ref** — commit SHA before implement
   - **Target paths** — concrete pathspecs (no TBD)
   - **Test command** — exact suite command
   - **Materiality bar** — material P0/P1 blocks a clean cycle; minors/P2 are trivial
   - **Driver** — default `review-converge under /goal`
   - **Max review-converge rounds** — default 12 (anti-loop hard wall)
   - **Repo** — optional absolute git root
   - **Plan contract** — absolute plan path bound with SHA-256 at campaign start
   - **Specs** — anchors and implementation-intent questions for the forward audit
5. Do **not** use heading `## Post-Implementation Residual Loop` (it collides with
   review-plan Q-E2 “Post-Implementation Workflow or equivalent”).

Waiver (only if residual is intentionally out of scope): **replace the entire
section body** with one unfenced line (a fenced example does not waive; a waiver
line outside `## Review Coverage` does not waive; waiver + filled fields is a
**conflict**):

```text
None — residual loop waived: <concrete reason>
```

Phase A success: the **approved plan file** contains a filled directive
(`scripts/review-coverage validate <PLAN_PATH>` exit 0) or a real unfenced
in-section waiver. An example waiver reason is not a waiver.
Heading must be level-2 `## Review Coverage` (not `#` / `###`).

## Phase B — Post-implement (run residual×2)

1. Implementation landed; suite green; optional first-pass `/review-fix` done.
2. Validate the approved plan: `scripts/review-coverage validate <PLAN_PATH>`.
3. Generate the command: `scripts/review-coverage goal-body --plan <PLAN_PATH> --slash`.
4. Paste the **exact** CLI output into the host goal, then set host max-turns and
   max-budget before unattended work. **Do not paraphrase** its static sentence:

   ```text
   /goal quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial changes remain for 2 consecutive cycles
   ```

5. Run exactly one inner `/review-converge` per outer turn. The section’s exit
   table remains the operator procedure for terminal or capped states; it is not
   the `/goal` body text.
6. The one inner round does both:
   - **Forward:** specs / anchors / intent → code; pathspec commit material fixes.
   - **Reverse:** diff vs **Base ref**; regressions, violated anchors, side effects;
     fix or record the result in the ledger.

Success is only Status **`complete`** after two consecutive clean rounds, the second
clean ran Test command successfully, and Log landed. **`stopped (...)` is not success.**
Never unlimited ralph. Never continue after complete or stopped (...).

## Helpers (optional)

```sh
# From skill package root (after install.sh or in a skill-craft clone)
scripts/review-coverage template
scripts/review-coverage template --short
scripts/review-coverage validate /path/to/plan.md
scripts/review-coverage goal-body --plan /path/to/plan.md
scripts/review-coverage goal-body --plan /path/to/plan.md --slash
```

`goal-body` emits the static sentence plus available plan bindings. `goal-body --slash`
prefixes it exactly with `/goal ` for direct paste. Validate is advisory lint for
agents/humans — not a soft_exit dependency. Unfilled templates (including example
`None — residual loop waived: <reason>`) **fail** `validate` — a placeholder waiver
reason is not a real waiver. `goal-body` runs the **same** validation path as
`validate` first, so the two commands never disagree on waived vs filled status.

### CLI exit codes

| Code | Meaning |
|------|---------|
| **exit 0** | Success: `validate` prints `ok`; `goal-body` prints the paste body |
| **exit 1** | Invalid plan / refused: missing section, placeholders, conflict, waived for `goal-body`, etc. |
| **exit 2** | Input unreadable: missing path, directory path, or OS read error — stderr is `error: cannot read <path>: <reason>` (never a Python traceback) |

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
