---
bump: minor
---
The test counter now reads a plain TAP stream, such as `--result-format tap` output or mocha's tap reporter, when no
runner's own summary matches. It reads one `1..N` plan, before the test points or after them, and exactly N top-level
points numbered 1..N in order. So `min_tests` and the count floor now hold for such a command.

What can now be refused that passed before, for output read this way:

- a `not ok` point at exit 0 fails the run, for every kind of row: a regression row without `min_tests`, a failing
  point that no listed ID names, and a `check` such as a linter that marks warnings `not ok` while it exits 0;
- `1..0` reads as zero tests and is refused as `no-tests` (with `min_tests` it was `uncounted`; without, it passed);
- a focused row with ids and `min_tests` is held to that minimum, and a later run of the same command to the count it
  reached.

SKIP and TODO directives follow TAP 14: `# skipped` is a skip, and an escaped `\#` is part of the title. The IDs a
TAP point shows now follow the same rule. A stream with numberless or out-of-order points, an indented point or plan
(nested subtests included), a second plan or a `Bail out!` is still not read. pytest's exit-status-5 guess now comes
after TAP, so `1..1` / `ok 1` at status 5 reads one test instead of zero. A check that passed under an earlier release
and is completed after this one on an unchanged tree keeps its recorded result.
