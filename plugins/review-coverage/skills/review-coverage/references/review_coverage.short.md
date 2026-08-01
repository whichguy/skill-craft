## Review Coverage

*Finite residual×2 after implement — never open loop.*

| Field | Value |
|-------|--------|
| Base ref | `<sha before implement>` |
| Target paths | `<pathspecs>` |
| Test command | `<cmd>` |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Max rounds | 12 → then `stopped (max-cycles)` |

**residual×2** = two consecutive clean rounds + suite PASS on second clean → Status `complete`.
**stopped(...)** ends `/goal` without success. Never unlimited ralph.

### Objective (paste into /goal)

```text
FINITE residual. After every turn: complete+landed → EXIT success; stopped+landed → EXIT halt;
active and rounds≥12 → stopped(max-cycles); else one /review-converge then re-check.
Base ref: <BASE_REF>. Paths: <PATHS>. Test: <CMD>.
Driver: review-converge under /goal — one round per turn.
Forward specs→code; reverse diff vs Base ref. Material only. Pathspec commits.
stopped(...) is not success. Never continue after complete or stopped.
```

### Waiver
Replace body with a real reason (not placeholder): `None — residual loop waived: <reason>`
