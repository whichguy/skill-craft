---
bump: minor
---
Improve reviews converge. Each pass records its size, `lines` (lines removed plus added in the tree and in the reviewed
result), in `pass-<n>.json`, in `passes.md` and in the pass's printed facts. After three passes that each changed 1-10
lines, `improve-pass` prints the trend. A further pass is recorded as non-trivial only when its review has the line
`Later-stage defect: <stage>: <what would fail there without this change>`, naming the reviewed stage or a later one.
Otherwise the pass is classified trivial, which ends the review. A pass of unknown size never starts the trend.
