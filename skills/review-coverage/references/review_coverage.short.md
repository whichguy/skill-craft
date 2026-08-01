## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | `<sha before implement>` |
| Target paths | `<pathspecs>` |
| Test command | `<cmd>` |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

### Objective (paste into /goal)

Post-ship review coverage. Base ref: <BASE_REF>. Paths: <PATHS>. Test: <CMD>.
Each turn: one /review-converge. Forward specs→code; reverse diff vs Base ref.
Complete after two consecutive clean rounds with green suite on second clean.
stopped(...) is not success. Pathspec commits only; never git add -A.

### Waiver
Replace body with a real reason (not placeholder): `None — residual loop waived: <reason>`
