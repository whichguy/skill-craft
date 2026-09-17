## Review Coverage

*Improve to exhaustion after implement — finite residual, never an open loop.*

### What this section is

| Term | Meaning |
|------|---------|
| **Review Coverage** | This whole H2 block — durable post-ship instructions in the plan. Phase A writes it; Phase B runs it. |
| **residual** | Post-ship work: **forward** (specs → code) + **reverse** (diff vs Base ref); fix only **material** issues; pathspec commit. |
| **clean / residual×2** | A cycle is **clean** only when only trivial findings remain. Review success: Status `complete` only after **two consecutive clean** residual rounds, with second-pass verification as defined below. Fixing material resets the streak; not “run two rounds total.” |
| **Driver** | One residual **round** executor — default `/review-converge` under outer `/goal`. |
| **complete** | residual×2 **review success** (objective-met); delivery success also needs Finalization for the current candidate. |
| **stopped (...)** | Residual **failed closed** (not success; still ends the outer loop). |

**Run when:** implementation landed, applicable suite green (or concrete manual
verification for an explicitly N/A Test command), and any first-pass post-impl
review is done. Not before.
**Do not merge / declare product done** until residual Status is terminal
**complete** and Finalization records current-candidate evidence (or you
explicitly accept a **stopped** halt).

| Field | Value |
|-------|-------|
| Base ref | `<sha before implementation>` |
| Repo | `<absolute git root>` |
| Target paths | `<repo-relative pathspecs — no TBD>` |
| Test command | `<exact cmd — or N/A — no automated tests: reason>` |
| Materiality bar | material (P0/P1) only — minors never block exit |
| Driver | review-converge under /goal (default) |
| Plan contract | `<absolute plan path>` bound at campaign start (SHA-256) |
| Specs | Spec anchors + Implementation Intent Questions (READ-ONLY in cycles) |
| Max review-converge rounds | 12 hard cap; on exceed → `stopped (max-cycles)` |
| Same-error stop | 3 consecutive identical Error signature → `stopped (same-error ×3)` |
| No-progress stop | 3 consecutive blocked/no-progress → `stopped (no-progress ×3)` |
| Outer /goal caps | Host max-turns and max-budget required; never unattended without both |
| Ralph | Prefer `/goal` only; if used, `max_iterations` must be **positive** (never `0` / unlimited) |

**Preconditions:** pathspec-only commits under Target paths; never `git add -A`.

### Exit conditions (anti infinite loop)

After **every** outer `/goal` turn, re-read repo-root `REVIEW_CONVERGE.md` Status
and choose **exactly one**:

| Branch | Status after turn | Outer `/goal` action | residual×2 success? |
|--------|-------------------|----------------------|----------------------|
| S1 | `complete` AND Log **landed** | **Run Finalization**; EXIT SUCCESS only after current-candidate evidence is recorded | YES (review only) |
| S2 | `stopped (...)` AND Log **landed** | **EXIT HALT** | NO (halt) |
| S3 | `active` AND rounds **≥ Max** | Force `stopped (max-cycles)`, land Log, **EXIT HALT** | NO |
| S4 | Terminal but not landed | One ledger-flush only; then EXIT HALT if still not landed (never Finalization success) | n/a |
| S5 | Else | Run exactly **one** `/review-converge`, land Log; do not start another round this turn | n/a |

**Landed** means latest Log `Committed: yes` and a commit subject matching
`review-converge: round N —` (or legacy `grok-review-converge: round N —`).
**There is no “keep going forever while active.”** `active` = at most one more
unit of work, then re-evaluate.

**Residual review success (all required):** Status `complete`; two **consecutive**
Log rounds Outcome `clean` (only trivial findings remaining; non-clean resets
streak); second-pass verification; latest Log **landed**. Stop
iterating and apply remaining Deferred (minor/P2) in one pathspec wrap-up commit
(skip if Deferred is empty), then run Finalization before delivery success.

Second clean: automated Test command PASS when applicable; otherwise N/A requires concrete manual method and result (never an automated PASS).

**Delivery success (additional required):** Finalization records verification for
the exact final candidate. A wrap-up commit changes that candidate; the older
second-clean PASS cannot certify it by itself.

**Unsuccessful halt:** land `stopped (same-error ×3 | no-progress ×3 | max-cycles |
plan hash drift | no target paths | no test command | host quota | operator abort)`.
**`stopped (...)` is never success.**

**Non-exits:** suite green alone; one clean only; open material; minors/P2 listed
(must not block); unlanded Log; prose without Status complete/stopped.

**Loop-safety MUST:** one `/review-converge` per outer turn; never unlimited ralph;
max rounds hard wall; pathspec only.
Never run another residual round after complete or stopped (...); a completed/landed review enters Finalization.

### Finalization

After completed/landed review, before delivery success, re-read the existing
`REVIEW_CONVERGE.md`; preserve terminal review-round history. Add or update an
ordinary Markdown `### Finalization` subsection with no new state enum or engine. Record:

- **Candidate SHA** — tested product/policy/configuration revision, not a later receipt commit.
- **Verification command or manual method** — what checks that revision.
- **Result / exit** — PASS, manual result, or failure/interruption.
- **Log reference** — durable path or receipt for the actual output.

With no remaining edits and an unchanged candidate, current second-pass evidence
may be reused and bound in that record. A changed candidate, including a trivial
wrap-up, requires verification after its final edit: Test command PASS when
applicable, or the manual alternative.
N/A is not an automated PASS: record a concrete manual method and result instead. Missing,
stale, failed, or interrupted evidence means no delivery success; HALT and retain
it.

Keep the record durable and read it on resume before acting. Reconcile an existing wrap-up commit
and evidence; make no duplicate commit. Retest is not a review round and must not
erase or rewrite terminal review-round history. If Finalization discovers a
material repair, use the existing operator-authorized reopen path; otherwise HALT.

A bookkeeping-only receipt commit may follow verification and does not invalidate proof. It must name the prior tested product/policy/configuration Candidate SHA and must not pretend to test the receipt commit. Any later in-scope product/policy/configuration change invalidates affected evidence.

Static/prompt tests prove this instruction contract; they do not prove actual model compliance.
They are not evidence that a host/model performed the stated
verification.

### /goal command (Phase B — skill compose / paste literally)

Static complete-when (do not paraphrase):

```text
quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial findings remaining for 2 consecutive cycles
```

Printer trailer (CLI fills slots only):

```text
Plan: {plan}. Base ref: {base_ref}. Target paths: {target_paths}. Test command: {test_command}. Driver: one /review-converge per turn. Max review-converge rounds: {max_n} — on exceed, land stopped (max-cycles) in REVIEW_CONVERGE.md and EXIT HALT. Also EXIT HALT on stopped (same-error ×3) or stopped (no-progress ×3) when landed. Ledger: REVIEW_CONVERGE.md — a cycle counts clean only if Log Outcome is clean (only trivial findings remaining this cycle; fixing material resets the streak); review success only when Status complete AND Log landed. Second clean: automated Test command PASS when applicable; otherwise N/A requires concrete manual method and result (never an automated PASS). Finalization: after complete AND landed, before delivery success append/update ordinary ### Finalization in REVIEW_CONVERGE.md; preserve terminal review-round history; record Candidate SHA, verification command or manual method, Result / exit, and log reference; read it on resume. No remaining edits + unchanged candidate may reuse current second-pass evidence. Changed candidate (including wrap-up) requires verification after final edit: Test command PASS when applicable, or the manual alternative. N/A is not an automated PASS: record concrete manual method and result. Missing, stale, failed, or interrupted evidence means no delivery success; HALT. A bookkeeping-only receipt commit may follow verification and does not invalidate proof. It must name the prior tested product/policy/configuration Candidate SHA and must not pretend to test the receipt commit. Any later in-scope product/policy/configuration change invalidates affected evidence. Resume existing commit/evidence; no duplicate commit. Retest is not a review round. Material repair requires operator-authorized reopen; otherwise HALT. Never unlimited outer loop. Pathspec commits only under Target paths; never git add -A{repo_clause}.
```

**Primary (Grok-executable):** invoke the **review-coverage skill**
(`/review-coverage` on this plan) or **review-converge**. Loop rounds **in this
session** until residual×2 or halt. On Grok, `/goal` is a **user-typed** pager
slash — putting `/goal …` in a plan does not execute it.

**Optional operator paste:** after the Review Coverage card binds its installed
`CLI`, run `python3 "$CLI" goal-body --plan <ABS_PLAN> --slash`
(user types that line). The agent must not type `/goal` and wait.

Optional human/CI helper only: `python3 "$CLI" goal-body --plan <ABS_PLAN> --slash`
(or `run-card --preflight`). Do not treat the CLI as the skill entrypoint.

### Cycle log

| # | Date | Forward | Reverse | Material? | Suite | Commit |
|---|------|---------|---------|-----------|-------|--------|
|   |      |         |         |           |       |        |

### Waiver

Only when residual is intentionally out of scope: **replace the entire section body**
with one line and a real reason (not the `<reason>` placeholder — that fails
`validate`):

```text
None — residual loop waived: <one-line reason>
```
