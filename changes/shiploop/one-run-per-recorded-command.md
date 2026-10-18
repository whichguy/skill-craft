---
bump: minor
---
ShipLoop runs each recorded test command once per run, and `complete` no longer reruns a passing `--check-only` run.
- A step plan, system-test-author or release-plan result that records the same command string twice keeps one row: rows
  in one suite fold together, and a regression row that repeats a focused row (its IDs all IDs of the focused one) folds
  into the focused row, which then says `regression: true` and lists as "(also recorded as regression)". The one row
  checks the union of the IDs and criteria and the larger `min_tests`; the system-test drift check still runs it as the
  default suite. A check and a test-runner row, a regression row with IDs of its own, or rows that differ in
  `host_dependent` stay apart. In the packet review's run the step plan's 10 rows became 7 and the command listing
  5,360 characters 4,204.
- `complete` takes the action's passed `complete --check-only` test run instead of running every recorded command
  again when the command list and the working tree (tracked and untracked files, not ignored ones; the tree the
  check-only run started on or the one it left) are unchanged (owner decision D5). The counted `verify<N>` record says
  `reused` with the check-only record's path, time and tree; the test stage prints a `Gates: candidate: reused ...`
  line, and the check-only output says the next complete takes the run while nothing changes. A reused run is held to
  today's floor, and one the floor would refuse is run again. The test stage's base run and mutation check, and
  release-verify's consumer checks, still run at complete.
