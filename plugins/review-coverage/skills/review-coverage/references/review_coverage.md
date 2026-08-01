## Review Coverage

*Improve to exhaustion after implement — finite residual, never an open loop.*

### What this section is

| Term | Meaning |
|------|---------|
| **Review Coverage** | This whole H2 block — durable post-ship instructions in the plan. Phase A writes it; Phase B runs it. |
| **residual** | Post-ship work: **forward** (specs → code) + **reverse** (diff vs Base ref); fix only **material** issues; pathspec commit. |
| **residual×2** | Success stop rule: Status `complete` only after **two consecutive clean** residual rounds, with the **second** clean running Test command green. Not “run two rounds total.” |
| **Driver** | One residual **round** executor — default `/review-converge` under outer `/goal`. |
| **complete** | residual×2 **success** (objective-met). |
| **stopped (...)** | Residual **failed closed** (not success; still ends the outer loop). |

**Run when:** implementation landed, suite green, and any first-pass post-impl
review is done. Not before.
**Do not merge / declare product done** until residual Status is terminal **complete**
(or you explicitly accept a **stopped** halt).

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
| S1 | `complete` AND Log **landed** | **EXIT SUCCESS** | YES |
| S2 | `stopped (...)` AND Log **landed** | **EXIT HALT** | NO (halt) |
| S3 | `active` AND rounds **≥ Max** | Force `stopped (max-cycles)`, land Log, **EXIT HALT** | NO |
| S4 | Terminal but not landed | One ledger-flush only; then EXIT if still not landed (**HALT** or **SUCCESS** per Status) | n/a |
| S5 | Else | Run exactly **one** `/review-converge`, land Log; do not start another round this turn | n/a |

**Landed** means latest Log `Committed: yes` and a commit subject matching
`review-converge: round N —` (or legacy `grok-review-converge: round N —`).
**There is no “keep going forever while active.”** `active` = at most one more
unit of work, then re-evaluate.

**Success (all required):** Status `complete`; two **consecutive** Log rounds Outcome
`clean` (zero material; non-clean resets streak); second clean runs Test command PASS;
latest Log **landed**.

**Unsuccessful halt:** land `stopped (same-error ×3 | no-progress ×3 | max-cycles |
plan hash drift | no target paths | no test command | host quota | operator abort)`.
**`stopped (...)` is never success.**

**Non-exits:** suite green alone; one clean only; open material; minors/P2 listed
(must not block); unlanded Log; prose without Status complete/stopped.

**Loop-safety MUST:** one `/review-converge` per outer turn; never unlimited ralph;
never continue after complete or stopped (...); max rounds hard wall; pathspec only.

### /goal command (Phase B — paste literally)

```text
/goal quality review changes and consider improvements, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration, complete when only trivial changes remain for 2 consecutive cycles
```

After the fields are filled:

```sh
scripts/review-coverage goal-body --plan <ABS_PLAN> --slash
```

Paste the entire CLI output. Do not paraphrase the static sentence; the CLI adds
the plan bindings after it.

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
