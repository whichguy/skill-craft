## Review Coverage

*Finite residual×2 after implement — never open loop.*

| Field | Value |
|-------|-------|
| Base ref | `<sha before implement>` |
| Target paths | `<pathspecs>` |
| Test command | `<cmd>` |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Max review-converge rounds | 12 → then `stopped (max-cycles)` |

**clean** = only trivial findings remaining this cycle; fixing material resets the streak.
**residual×2** = two consecutive clean rounds + second-pass verification + landed Log → Status `complete` review success.
Second clean: automated Test command PASS when applicable; otherwise N/A requires concrete manual method and result (never an automated PASS).
Then stop iterating; apply remaining Deferred (minor/P2) in one wrap-up commit and
run Finalization before delivery success.
**`stopped (...)`** ends `/goal` without success. Never unlimited ralph.

### Exit conditions

After every outer `/goal` turn, re-read `REVIEW_CONVERGE.md` Status and choose exactly one:

| Branch | Action |
|--------|--------|
| S1 | `complete` AND landed → **Run Finalization**; EXIT SUCCESS only after current-candidate evidence is recorded |
| S2 | `stopped (...)` AND landed → **EXIT HALT** (not success) |
| S3 | `active` AND rounds ≥ Max → force `stopped (max-cycles)`, land Log, **EXIT HALT** |
| S4 | Terminal but not landed → one ledger-flush only; then EXIT HALT if still not landed |
| S5 | Else → run exactly one `/review-converge`, land Log; do not start another round this turn |

Forward: specs/anchors → code. Reverse: diff vs Base ref. Pathspec commits only.

### Finalization

After completed/landed review, before delivery success, add/update ordinary
Markdown `### Finalization` in `REVIEW_CONVERGE.md` without changing terminal
review-round history or adding a state enum/engine. Record Candidate SHA,
verification command or manual method, Result / exit, and log reference; read it
on resume. With no remaining edits and an unchanged candidate, current second-pass evidence
may be reused. A changed candidate (including wrap-up) needs verification
after its final edit: Test command PASS when applicable, or the manual alternative.
N/A is not an automated PASS: record concrete manual method and result.
Missing, stale, failed, or interrupted evidence means no delivery success; HALT.
Resume existing evidence with no duplicate commit. Retest is not a review round.
Material repair requires operator-authorized reopen;
otherwise HALT.

A bookkeeping-only receipt commit may follow verification and does not invalidate proof. It must name the prior tested product/policy/configuration Candidate SHA and must not pretend to test the receipt commit. Any later in-scope product/policy/configuration change invalidates affected evidence.

### /goal command (Phase B — skill compose / paste literally)

Static complete-when (do not paraphrase):

```text
quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial findings remaining for 2 consecutive cycles
```

**Primary (Grok-executable):** invoke skill `/review-coverage` or `/review-converge`
and loop rounds in this session. On Grok, `/goal` is user-typed only — a `/goal`
line in a plan does not execute.

Optional operator paste: `scripts/review-coverage goal-body --plan <ABS_PLAN> --slash`

Printer trailer (halt/ledger/finalization slots) lives in `review_coverage.md` — do not paraphrase it here.

Optional human/CI helper (not required): `scripts/review-coverage goal-body --plan <ABS_PLAN> --slash`

### Waiver

Replace body with a real reason (not placeholder): `None — residual loop waived: <reason>`
