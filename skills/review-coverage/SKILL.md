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
version: 0.3.1
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

### Optional helper binding from an installed package

Use a CLI helper only after the host has identified the **selected, loaded**
`SKILL.md`. Let `SKILL_ROOT` be the absolute directory containing that file and
bind the bundled helper from it for the current tool call:

```sh
# Replace this illustrative path with the selected absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
CLI="$SKILL_ROOT/scripts/review-coverage"
python3 "$CLI" template --short
```

Do not infer `SKILL_ROOT` from the user's project cwd, a source checkout,
`PATH`, a same-named skill, or a guessed cache layout. If the host presents a
skill-root alias, expand the alias selected for this loaded card first. Claude
Code may render `${CLAUDE_SKILL_DIR}` in card text on versions that support that
substitution; it is not a portable shell environment variable. Rebind the
absolute `CLI` in each independent shell call, quote it, and keep plan/run
state under the target repository rather than this package. If the bundled file
or `python3` is unavailable, report that prerequisite instead of falling back
to a similarly named executable.

## Definitions

| Term | Meaning |
|------|---------|
| **Review Coverage** | Durable plan **H2 only** `## Review Coverage` + this skill (H1/H3+ are not recognized). After ship: prove code matches specs and **stop** when proof is stable. |
| **Status / Log / landed** | Driver ledger at repo-root `REVIEW_CONVERGE.md`. **Landed** = latest Log `Committed: yes` and `review-converge: round N —`. |
| **residual** | Forward (specs→code) + reverse (diff vs Base ref); material fixes only; pathspec commits. |
| **clean / residual×2** | Clean = **only trivial findings remaining this cycle** (not “fixed some material and left minors”). Review success = two consecutive cleans with second-pass verification as defined below. Fixing material resets the streak. After DevLoop COMPLETE, this is the overlay — not a nested `/devloop`. Practices: skill-craft `docs/LOOP-ENGINEERING.md`. |
| **`/goal` body** | Outer multi-turn objective: **static complete-when sentence** + plan bindings (see below). Do not paraphrase the static sentence. |
| **`/review-converge`** | Default Driver: **one** residual round per outer turn. |
| **complete** | residual×2 review success + landed Log. Delivery success additionally requires the current-candidate Finalization record below. |
| **stopped (...)** | Terminal halt without residual×2 success; still ends `/goal`. |

### Static complete-when (byte-exact — do not paraphrase)

```text
quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial findings remaining for 2 consecutive cycles
```

### Host `/goal` line (operator paste — not agent-executable on Grok)

On Grok, `/goal` is a **user-typed pager slash**. The agent must not type it
and wait. Prefer CLI when available (avoids compose drift) **for the optional
operator paste**:

```sh
python3 "$CLI" goal-body --plan <ABS_PLAN> --slash
```

Show that output to the operator labeled **user-typed slash — not
agent-executable on Grok**. Fallback only if the CLI is missing: STATIC + the
same trailer fields/order as `references/review_coverage.md` (Plan absolute, Base
ref, Target paths, Test command, Driver one round, Max review-converge rounds + halt rules,
Ledger clean = only trivial findings remaining this cycle + landed SUCCESS, and
the Finalization current-candidate evidence, pathspec). Include `Repo:` when
set. Default Max review-converge rounds **N** = 12. The CLI
fills those slots and prints; it does not author the sentence. The **executable**
driver is in-session **review-converge** (or `update_goal` when that tool exists).

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
   - **Test command** — exact suite command, or explicit N/A with reason and concrete manual verification
   - **Materiality bar** — material P0/P1 blocks clean; minors/P2 are trivial
   - **Driver** — default `review-converge under /goal`
   - **Max review-converge rounds** — default 12
   - **Repo** — optional absolute git root
   - **Plan contract** — absolute plan path (SHA-256 at campaign start)
   - **Specs** — anchors / intent questions for forward audit

   Use these labels exactly. The retired short labels `Base`, `Target path` and
   `Max rounds` fail validation; rename them to the labels above.
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

1. Preconditions: implementation landed; applicable suite green or concrete manual
   verification for an explicitly N/A Test command; optional first-pass `/review-fix` done.
2. **Preflight (hard stops — do not open `/goal` if any fail):**
   - The selected `review-converge` driver is an external skill, not bundled
     here. Resolve it through the host's advertised skill inventory and read its
     loaded card before starting Phase B. If it is unavailable, stop with that
     missing prerequisite; do not invent a slash command or substitute a different
     review lifecycle. Phase A and this package's CLI helpers remain usable.
   - Plan has filled `## Review Coverage` (or run Phase A first).
   - Not waived (if waived, stop — no residual campaign).
   - Base ref looks real; if git repo available, prefer resolvable.
   - If repo-root `REVIEW_CONVERGE.md` is **terminal** (`complete` / `stopped`)
     for a **different** plan contract, plan hash, or campaign scope → **hard
     stop**: archive/rename the ledger
     first (do not auto-delete). Same plan + re-run only if operator explicitly
     requests re-open residual. Resuming Finalization alone is not a residual reopen;
     for the same completed/landed campaign, reconcile its Finalization record
     and perform only the missing verification/receipt work without another round.
   - If `git status --porcelain -- <Target paths>` shows foreign dirt under
     Target paths (excluding the ledger), **warn**; refuse unattended start
     until paths are clean or dirt is confirmed in-scope.
   - Optional: after the installed-package binding above, run
     `python3 "$CLI" preflight --plan ABS` (use `--strict` in CI).
3. **Outer driver (host-aware — Grok cannot agent-execute `/goal`):**
   - **Executable (Grok default, and any host without an agent-callable `/goal`
     or `update_goal` tool):** invoke skill **review-converge** in **this
     session**. One round, then if `REVIEW_CONVERGE.md` Status is still
     `active`, immediately run another round. Do not stop for the user. Do
     **not** type a `/goal` slash and wait — on Grok that is a user-typed
     pager command and a `/goal` line in a plan does not execute.
   - **If the host advertises an objective-creation tool:** use its actual schema
     and authorization rules to set the composed complete-when sentence + trailer;
     one review-converge per outer turn. A status-only `update_goal` tool cannot
     create an objective. Never infer authorization to create a persistent goal
     merely from the presence of that tool.
   - **Optional operator paste:** if the bound `CLI` exists, run
     `python3 "$CLI" goal-body --plan <ABS> --slash` and show that line labeled
     **user-typed slash — not agent-executable on Grok**. The operator may
     paste it for host max-turns/budget. **Do not paraphrase** the static
     sentence. CLI missing → compose from Definitions (STATIC + trailer).
4. Set host **max-turns** / **max-budget** only when the operator actually
   opened `/goal`. Prefer in-session review-converge over unlimited ralph.
5. **Each outer turn:** run exactly **one** `/review-converge` for the plan’s
   target paths and test command (forward + reverse). Then re-read
   `REVIEW_CONVERGE.md` Status:
   - `complete` + landed → **enter Finalization** below. EXIT SUCCESS only
     after it records current-candidate verification.
   - `stopped (...)` + landed → **EXIT HALT** (not success)
   - `active` and rounds ≥ Max → force `stopped (max-cycles)`, land, EXIT HALT
   - terminal but not landed → one ledger-flush; then EXIT HALT if still not
     landed
   - else → next turn, one more converge only
6. Every converge round does both:
   - **Forward:** specs / anchors / intent → code; pathspec commit material fixes.
   - **Reverse:** diff vs Base ref; regressions / violated anchors; fix or ledger.
   - Per static sentence: review last 10 commit messages for learnings; verbose
     pathspec commits with key learnings between iterations.
7. **Wrap-up trivials (after residual×2 success only):** when Status is
   `complete` and the latest Log **landed**, stop iterating. Apply remaining
   Deferred (minor/P2) trivial improvements in **one** pathspec wrap-up commit
   (no new `/review-converge` round). If it changes the candidate, it must be
   verified in Finalization below before delivery success. Do not start another
   residual cycle for those trivials. Skip the wrap-up when Deferred is empty,
   then enter Finalization below.

Residual review success is Status **`complete`** after two consecutive clean
rounds, second-pass verification, and Log landed. Delivery success additionally
requires Finalization to establish evidence for the final candidate after any
wrap-up commit. **`stopped (...)` is not success.** Never unlimited ralph.
Never run another residual round after complete or stopped (...); a completed/landed review enters Finalization.

Second clean: automated Test command PASS when applicable; otherwise N/A requires concrete manual method and result (never an automated PASS).

## Finalization (after completed/landed review)

Run this after the residual review is `complete` and landed, before declaring
delivery success. It is a record and verification step, not another
`/review-converge` round or a new execution engine.

1. Re-read the existing repo-root `REVIEW_CONVERGE.md`; preserve terminal review-round history.
   Add or update an ordinary Markdown `### Finalization` subsection with no new state enum or engine. Record all of:
   - **Candidate SHA** — the tested product/policy/configuration revision, not a later receipt commit.
   - **Verification command or manual method** — what checks that candidate.
   - **Result / exit** — PASS, manual result, or the failure/interruption.
   - **Log reference** — durable path or receipt for the actual output.
2. Bind evidence to that candidate. With no remaining edits and an unchanged
   candidate, current second-pass evidence may be reused; record that binding.
   A changed candidate, including a trivial wrap-up, requires verification after
   its final edit: Test command PASS when applicable, or the manual alternative.
   N/A is not an automated PASS: record a concrete manual method and result instead.
3. Missing, stale, failed, or interrupted evidence means no delivery success;
   HALT and retain the evidence. Never reinterpret an interrupted Finalization
   as a successful review.
4. Keep the record durable and read it on resume before acting. Reconcile any existing wrap-up
   commit and evidence; make no duplicate commit. Retest is not a review round,
   and must not erase or rewrite terminal review-round history.
5. If Finalization discovers a material repair, it requires the existing
   operator-authorized reopen path for the residual campaign; otherwise HALT.
   Do not label material repair as a trivial wrap-up.

A bookkeeping-only receipt commit may follow verification and does not invalidate proof. It must name the prior tested product/policy/configuration Candidate SHA and must not pretend to test the receipt commit. Any later in-scope product/policy/configuration change invalidates affected evidence.

Static/prompt tests prove this instruction contract; they do not prove actual model compliance.
They also do not attest a candidate that was not actually
verified and recorded.

## Optional CLI helpers (not the primary invoke)

Humans or CI may lint/print without loading the agent skill. Agents may use these
when convenient; **skill Phase A/B above is authoritative**.

```sh
# CLI is bound from the selected loaded SKILL.md above; cwd is irrelevant.
python3 "$CLI" template
python3 "$CLI" template --short
python3 "$CLI" validate /path/to/plan.md
python3 "$CLI" preflight --plan /path/to/plan.md
python3 "$CLI" preflight --plan /path/to/plan.md --strict
python3 "$CLI" run-card --plan /path/to/plan.md --preflight
python3 "$CLI" goal-body --plan /path/to/plan.md
python3 "$CLI" goal-body --plan /path/to/plan.md --slash
```

| Helper | Role |
|--------|------|
| `validate` | Lint filled vs waived vs broken (same rules Phase A “filled”) |
| `goal-body` / `--slash` | Emit the composed `/goal` line (same contract as Phase B compose) |
| `preflight` | Extra checks (base ref resolve, terminal ledger) |
| `run-card` | Print operator card (goal line + each-turn converge reminder) |
| `template` | Print section markdown for paste |

When the agent composes the `/goal` line natively, it must match
`references/review_coverage.md` (static sentence + printer trailer). The CLI
only fills slots and prints.

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
# Checkout-only skill-dir side-load; this installer is not part of a marketplace package.
./install.sh --skill review-coverage
# → host skill dir (symlink). Then: /review-coverage …
```

See `references/host-matrix.md`.
