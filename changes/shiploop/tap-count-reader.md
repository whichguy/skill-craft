---
bump: minor
---
The test counter now reads a plain TAP stream, such as `--result-format tap` output or mocha's tap reporter, when no
runner's own summary matches. It reads one `1..N` plan, before the test points or after them, and exactly N top-level
points numbered 1..N in order. So `min_tests` and the count floor now hold for such a command, and `1..0` reads as zero
tests (`no-tests`) instead of `uncounted`.

Before this, a regression row with `min_tests` whose command printed native TAP was refused as uncounted. A focused
row whose ids showed passed with no count, so its `min_tests` was never applied.

SKIP and TODO directives follow TAP 14: `# skipped` is a skip, and an escaped `\#` is part of the title. The IDs a
TAP point shows now follow the same rule. A stream with numberless or out-of-order points, nested subtests, a second
plan or a `Bail out!` is still not read. pytest's exit-status-5 guess now comes after TAP, so `1..1` / `ok 1` at
status 5 reads one test instead of zero.
