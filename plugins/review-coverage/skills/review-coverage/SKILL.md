---
name: review-coverage
description: >
  Add a post-ship improve-to-exhaustion directive to a plan, or run that
  directive after implementation. Invoke like any skill: /review-coverage,
  "review-coverage on this plan", residual×2 after ship, or ensure the plan
  has a /goal-ready ## Review Coverage section. Not for pre-exit plan quality
  (use review-plan) or raw residual×2 engine mechanics alone (use
  review-converge under /goal).
allowed-tools: all
version: 0.2.4
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# Review Coverage

**Plan directive + post-ship residual campaign** — not an exit hook and not a
second review-plan. Residual campaigns are **finite** (residual×2 success or
stopped halt) — never open loops.

```text
review-plan      →  plan quality (pre-exit)
review-coverage  →  plan directive + residual×2 after implement   ← THIS SKILL
review-converge  →  default residual×2 engine (one round / turn)
review-fix       →  optional first-pass code review before coverage
improve-loop     →  optional broader improve campaign
```

**Primary interface:** invoke this skill like any other skill. The agent follows
Phase A or Phase B below. Optional CLI helpers exist for humans/CI lint; they
are **not** required to run the skill.

## Invocation

```text
/review-coverage
/review-coverage <path-to-plan.md>
review-coverage on this plan
add Review Coverage to the plan
run residual×2 / post-ship coverage for this plan
```

| Situation | Mode |
|-----------|------|
| Plan exists, no filled `## Review Coverage` (or user asks to add/waive it) | **Phase A** |
| Implementation landed / user asks to run residual / improve-to-exhaustion | **Phase B** |
| Section already filled and user only wants status | Report filled/waived; offer Phase B if shipped |

Resolve the plan path from the invocation, the current session plan, or ask once.
Do **not** require the user to run shell scripts to use this skill.

## Definitions

| Term | Meaning |
|------|---------|
| **Review Coverage** | Durable plan **H2 only** `## Review Coverage` + this skill (H1/H3+ are not recognized). After ship: prove code matches specs and **stop** when proof is stable. |
| **Status / Log / landed** | Driver ledger at repo-root `REVIEW_CONVERGE.md`. **Landed** = latest Log `Committed: yes` and `review-converge: round N —` (or legacy `grok-review-converge: round N —`). |
| **residual** | Forward (specs→code) + reverse (diff vs Base ref); material fixes only; pathspec commits. |
| **clean / residual×2** | Clean = **only trivial findings remaining this cycle** (not “fixed some material and left minors”). Success = two consecutive cleans; second clean runs Test command PASS. Fixing material resets the streak. After DevLoop COMPLETE, this is the overlay — not a nested `/devloop`. Practices: skill-craft `docs/LOOP-ENGINEERING.md`. |
| **`/goal` body** | Outer multi-turn objective: **static complete-when sentence** + plan bindings (see below). Do not paraphrase the static sentence. |
| **`/review-converge`** | Default Driver: **one** residual round per outer turn. |
| **complete** | residual×2 success + landed Log. |
| **stopped (...)** | Terminal halt without residual×2 success; still ends `/goal`. |

### Static complete-when (byte-exact — do not paraphrase)

```text
quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial findings remaining for 2 consecutive cycles
```

### Host `/goal` line the agent opens

**Prefer CLI when available** (avoids compose drift):

```sh
scripts/review-coverage goal-body --plan <ABS_PLAN> --slash
```

Paste that output byte-for-byte. Fallback only if the CLI is missing: STATIC + the
same trailer fields/order as `goal_body()` (Plan absolute, Base ref, Target paths,
Test command, Driver one round, Max rounds + halt rules, Ledger clean = only
trivial findings remaining this cycle + landed SUCCESS, pathspec). Include
`Repo:` when set. Default max rounds **N** = 12.

### Nesting

```text
/review-coverage (this skill)
  → Phase A: edit plan ## Review Coverage
  → Phase B: open host /goal with composed line
       → each turn: one /review-converge
```

## When to use

- Non-trivial **code** plans about to be approved — ensure `## Review Coverage` is in the plan.
- After implementation is green — run residual×2 under `/goal`.
- User asks for residual / improve-to-exhaustion / post-ship coverage.

Skip pure doc-only one-line plans unless the user asks.

## Phase A — Plan authoring / review (agent edits the plan)

1. Read the plan path (invocation, session plan, or ask once — host-neutral).
2. If `## Review Coverage` is already **filled** (required fields real, non-placeholder; or real waiver) → stop Phase A and say so.
3. Otherwise **edit the plan**: insert the section from `references/review_coverage.md` (or the short template). Prefer reading the reference file in this skill package over shelling out.
4. Fill when known:
   - **Base ref** — commit SHA before implement
   - **Target paths** — concrete pathspecs (no TBD)
   - **Test command** — exact suite command
   - **Materiality bar** — material P0/P1 blocks clean; minors/P2 are trivial
   - **Driver** — default `review-converge under /goal`
   - **Max review-converge rounds** — default 12
   - **Repo** — optional absolute git root
   - **Plan contract** — absolute plan path (SHA-256 at campaign start)
   - **Specs** — anchors / intent questions for forward audit
5. Heading must be level-2 `## Review Coverage` only — not `#` / `###`, and not
   `## Post-Implementation Residual Loop` (collides with review-plan Q-E2).
   **If the plan still has legacy `## Post-Implementation Residual Loop`:** rewrite
   it to `## Review Coverage` (same fields; Driver `review-converge under /goal`).
   Do not leave dual residual H2s.

**Filled** means: Base ref, Target paths, Test command, Driver are present and not
placeholders; Materiality or material+residual×2 language present; positive Forward
and Reverse instructions present; residual×2 / two consecutive clean language present.

**Waiver** (only if residual intentionally out of scope): replace the **entire
section body** with one unfenced line (fenced examples do not waive; outside the
H2 does not waive; waiver + filled fields = **conflict**):

```text
None — residual loop waived: <concrete reason>
```

Phase A success: plan file contains a filled directive or a real unfenced in-section
waiver. Report what you wrote; do not require the user to run a CLI.

## Phase B — Post-implement residual (agent runs the campaign)

1. Preconditions: implementation landed; suite green; optional first-pass
   `/review-fix` done.
2. **Preflight (hard stops — do not open `/goal` if any fail):**
   - Plan has filled `## Review Coverage` (or run Phase A first).
   - Not waived (if waived, stop — no residual campaign).
   - Base ref looks real; if git repo available, prefer resolvable.
   - If repo-root `REVIEW_CONVERGE.md` (or legacy `GROK_CONVERGE.md`) is
     **terminal** (`complete` / `stopped`) for a **different** plan contract,
     plan hash, or campaign scope → **hard stop**: archive/rename the ledger
     first (do not auto-delete). Same plan + re-run only if operator explicitly
     requests re-open residual.
   - If `git status --porcelain -- <Target paths>` shows foreign dirt under
     Target paths (excluding the ledger), **warn**; refuse unattended start
     until paths are clean or dirt is confirmed in-scope.
   - Optional: `scripts/review-coverage preflight --plan ABS` (use `--strict`
     in CI). Prefer when the CLI is on PATH.
3. **Emit host `/goal` line:** if `scripts/review-coverage` exists, run
   `goal-body --plan <ABS> --slash` and paste the **exact** stdout. **Do not
   paraphrase.** Only if CLI is missing, compose from Definitions (STATIC +
   trailer rules matching CLI).
4. Open that line in the host goal facility. Set host **max-turns** and
   **max-budget** before unattended work. Prefer `/goal` over unlimited ralph.
5. **Each outer turn:** run exactly **one** `/review-converge` for the plan’s
   target paths and test command (forward + reverse). Then re-read
   `REVIEW_CONVERGE.md` Status:
   - `complete` + landed → **EXIT SUCCESS** (residual×2 met)
   - `stopped (...)` + landed → **EXIT HALT** (not success)
   - `active` and rounds ≥ Max → force `stopped (max-cycles)`, land, EXIT HALT
   - terminal but not landed → one ledger-flush; then EXIT per Status
   - else → next turn, one more converge only
6. Every converge round does both:
   - **Forward:** specs / anchors / intent → code; pathspec commit material fixes.
   - **Reverse:** diff vs Base ref; regressions / violated anchors; fix or ledger.
   - Per static sentence: review last 10 commit messages for learnings; verbose
     pathspec commits with key learnings between iterations.

Success is only Status **`complete`** after two consecutive clean rounds, second
clean Test PASS, Log landed. **`stopped (...)` is not success.** Never unlimited
ralph. Never continue after complete or stopped (...).

## Optional CLI helpers (not the primary invoke)

Humans or CI may lint/print without loading the agent skill. Agents may use these
when convenient; **skill Phase A/B above is authoritative**.

```sh
# From skill package root (install.sh or skill-craft clone)
scripts/review-coverage template
scripts/review-coverage template --short
scripts/review-coverage validate /path/to/plan.md
scripts/review-coverage preflight --plan /path/to/plan.md
scripts/review-coverage preflight --plan /path/to/plan.md --strict
scripts/review-coverage run-card --plan /path/to/plan.md --preflight
scripts/review-coverage goal-body --plan /path/to/plan.md
scripts/review-coverage goal-body --plan /path/to/plan.md --slash
```

| Helper | Role |
|--------|------|
| `validate` | Lint filled vs waived vs broken (same rules Phase A “filled”) |
| `goal-body` / `--slash` | Emit the composed `/goal` line (same contract as Phase B compose) |
| `preflight` | Extra checks (base ref resolve, terminal ledger) |
| `run-card` | Print operator card (goal line + each-turn converge reminder) |
| `template` | Print section markdown for paste |

When the agent composes the `/goal` line natively, it must match the CLI contract
(static sentence + required trailer fields and halt/ledger clauses).

### CLI exit codes (helpers only)

| Code | Meaning |
|------|---------|
| **exit 0** | Success: `validate` prints `ok`; `goal-body` prints the paste body |
| **exit 1** | Invalid plan / refused: missing section, placeholders, conflict, waived for `goal-body`, etc. |
| **exit 2** | Input unreadable: missing path, directory path, or OS read error — stderr is `error: cannot read <path>: <reason>` (never a Python traceback) |

Unfilled templates (including example `None — residual loop waived: <reason>`)
**fail** `validate`. `goal-body` uses the same validation path as `validate`.

## What this skill is not

- Not review-plan (pre-exit quality gates).
- Not a forced ExitPlanMode hook product.
- Not review-converge itself (default **driver** for each residual round).
- Not a script-first workflow — invoke the **skill**; CLI is optional lint/print.
- Not an infinite residual loop — residual×2 success or stopped halt.

## Install

```sh
./install.sh --skill review-coverage
# → host skill dir (symlink). Then: /review-coverage …
```

See `references/host-matrix.md`.
