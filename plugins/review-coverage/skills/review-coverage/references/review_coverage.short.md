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

**clean** = zero material findings this cycle; fixing material resets the streak.
**residual×2** = two consecutive clean rounds + suite PASS on second clean + landed Log → Status `complete`.
**`stopped (...)`** ends `/goal` without success. Never unlimited ralph.

### Exit conditions

After every outer `/goal` turn, re-read `REVIEW_CONVERGE.md` Status and choose exactly one:

| Branch | Action |
|--------|--------|
| S1 | `complete` AND landed → **EXIT SUCCESS** (residual×2 met) |
| S2 | `stopped (...)` AND landed → **EXIT HALT** (not success) |
| S3 | `active` AND rounds ≥ Max → force `stopped (max-cycles)`, land Log, **EXIT HALT** |
| S4 | Terminal but not landed → one ledger-flush only; then EXIT if still not landed (HALT or SUCCESS per Status) |
| S5 | Else → run exactly one `/review-converge`, land Log; do not start another round this turn |

Forward: specs/anchors → code. Reverse: diff vs Base ref. Pathspec commits only.

### /goal command (Phase B — paste literally)

```text
/goal quality review changes and consider improvements, review the last 10 git commit messages for learnings, anchoring each spec item in code changes and verify use cases/corner cases, git commit between each iteration with a verbose message with key learnings, complete when only trivial changes remain for 2 consecutive cycles
```

After the fields are filled:

```sh
scripts/review-coverage run-card --plan <ABS_PLAN> --preflight
```

Use `run-card` as the operator entrypoint; its first command contains the exact
host goal. `goal-body --plan <ABS_PLAN> --slash` remains valid for direct paste.

### Waiver

Replace body with a real reason (not placeholder): `None — residual loop waived: <reason>`
