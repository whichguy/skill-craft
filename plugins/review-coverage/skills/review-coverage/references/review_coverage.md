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
| **stopped(...)** | residual **failed closed** (not success; still ends the outer loop). |

**Run when:** implementation landed, suite green, and any first-pass post-impl
review is done. Not before.
**Do not merge / declare product done** until residual Status is terminal **complete**
(or you explicitly accept a **stopped** halt).

| Field | Value |
|-------|--------|
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

After **every** `/review-converge` turn, read `REVIEW_CONVERGE.md` Status and choose **exactly one**:

| Status after round | Outer `/goal` | residual×2 success? |
|--------------------|---------------|----------------------|
| `complete` + Log **landed** | **EXIT** | YES |
| `stopped (...)` + Log **landed** | **EXIT** | NO (halt) |
| `active` and rounds **&lt; Max** | CONTINUE — at most **one** more round, then re-check | n/a |
| `active` and rounds **≥ Max** | Force `stopped (max-cycles)`, land, **EXIT** | NO |
| Terminal but not landed | One ledger-flush only; then EXIT if still not landed | NO |
| Prior campaign already terminal | Do **not** re-open unless user says re-run residual | n/a |

**There is no “keep going forever while active.”** `active` = at most one more unit of work, then re-evaluate.

**Success (all required):** Status `complete`; two **consecutive** Log rounds Outcome `clean` (zero material; non-clean resets streak); second clean runs Test command PASS; latest Log **landed** (`Committed: yes` + `review-converge: round N —` commit).

**Unsuccessful halt:** land `stopped (same-error ×3 | no-progress ×3 | max-cycles | plan hash drift | no target paths | no test command | host quota | operator abort)`. **`stopped(...)` is never success.**

**Non-exits:** suite green alone; one clean only; open material; minors/P2 listed (must not block); unlanded Log; prose without Status complete/stopped.

**Loop-safety MUST:** one `/review-converge` per outer turn; never unlimited ralph; never continue after complete or stopped; max rounds hard wall; pathspec only.

### Objective (paste into /goal)

```text
FINITE residual — never infinite. After every turn re-read REVIEW_CONVERGE.md Status and apply Exit conditions in plan ## Review Coverage.

Post-ship review coverage for plan <plan_path> (hash <sha256>).
Base ref: <BASE_REF>. Repo: <REPO>. Target paths: <PATHS>.
Test command: <CMD>.
Driver: review-converge under /goal — exactly ONE review-converge round per turn.
Plan contract: bind absolute path + SHA-256 at start; hash drift → blocked → stop path.
Max rounds: 12. Same-error×3 and no-progress×3 → stopped. Host max-turns and max-budget required.

Each turn:
1) If Status complete+landed → EXIT residual success (residual×2 met).
2) If Status stopped(...)+landed → EXIT residual unsuccessful halt.
3) If Status active and rounds ≥ 12 → stopped (max-cycles), land, EXIT.
4) Else run exactly one /review-converge (forward + reverse), land Log, goto 1.

1. Forward (specs → code): re-read bound plan; fix material drift vs anchors/intent; pathspec commit; evidence in ledger.
2. Reverse (code → specs): diff vs Base ref; violated anchors, regressions, blast radius; fix or waive with reason.

Do not edit the plan file during cycles. Anchor writeback uses status verified (never proven).
Minors → Deferred (P2); only material blocks clean.
stopped(...) is not success. Never unlimited ralph. Never continue after complete or stopped.
Pathspec commits only; never git add -A.
Do not auto-start if the user is not ready to implement residual coverage.
```

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
