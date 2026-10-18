# U9 (u9-reruns): one run per recorded command

- **Date:** 2026-10-17. **Status:** firm for the offline tests and the replay of the chess step plan below; interim for
  the org time saved, which needs a live run (plan section 3, item 3).
- **Question:** F10 (reviewer D: DX-2, D-1, D-11(b)). Verify ran the same org suite three or four times: rows 7-9 of the
  step plan repeated rows 1-3 (a focused row and a regression row with the same command, IDs and minimum), so every run
  deployed and ran them twice, and the real `complete` after a passing `--check-only` reran all 10 commands on a tree
  that had not changed (about 104 s at verify). Can ShipLoop run each command once and take the check-only run (owner
  decision D5) without weakening a gate?
- **Change** (`skills/shiploop/scripts/shiploop_test_loop.py`; base 03c5edbc):
  - `normalise_commands` folds rows with the same command string until nothing folds (`_fold`), so the result is
    canonical (`validate` re-normalises every accepted result and requires equality). Rows fold when they share
    `host_dependent` and either a suite, or are focused plus a regression row whose IDs are all focused IDs. The one row
    keeps the first row's place, the union of IDs and criteria and the larger `min_tests`; a regression row folded into
    a focused one leaves `regression: true` (a new `COMMAND_KEYS` key, valid only on a focused row). A check and a
    counted row, a regression row with its own IDs (they would come under the base rule for new IDs), and rows that
    differ in `host_dependent` stay apart.
  - `default_suite_drift` also runs a focused row with `regression: true`, so the system-test drift check keeps seeing
    the default suite; `_listing` prints "(also recorded as regression)".
  - `verify`: a `count=False` run in the repository (every stage but release-verify) records `commands` and `trees`
    (the `lint.snapshot_tree` tree before and after its commands, `_tree`); a counted run takes a passed check-only
    record of the same stage, item and command list when the current tree is one of those (`_reused`), re-applies the
    current floors and writes the counted record with `reused: {path, created_at, tree}`. A reused run the current floor
    refuses is not taken: the commands run again. `loop_run` prints `candidate: reused ...`; `reuse_note` gives the
    check-only print its sentence (`shiploop_navigator.dispatch`, complete path).
  - References: `references/inner-loop.md` (check-only paragraph), `references/state-files.md` (`tests/` row).
- **Fail-first:** with the source reverted (`shiploop_test_loop.py`, `shiploop_navigator.py`) the new tests failed: 3 of
  6 in `shiploop-test-loop` (recorded twice runs once; complete takes the check-only run; test stage takes the candidate
  run) plus the command-list subtest erroring, and 3 of 3 in `shiploop-test-counts` (fold, apart and canonical, drift on
  a folded row). The guard tests pass on the old code (it always reran), so each was proved against a mutant of the new
  code: tree not compared (one-byte-edit test fails), command list not compared (command-list subtest fails), a reused
  run below the floor taken (below-the-floor test fails), drift skipping a folded row (drift test fails), one fold pass
  only (canonical test fails). Source restored byte-identical (`cmp`).
- **Replay of the chess step plan** (`pkt-review/in/17-step-plan.result.md`): 10 rows -> 7; the command listing the test
  and verify packets print, 5,360 -> 4,204 characters (-1,156; reviewer estimate 1,245); normalising again changes
  nothing. With D5, verify's `complete` after the passing check-only runs 0 commands instead of 10, so the org suite
  runs once (in the check-only) instead of twice per accepted verify.
- **Suites run** (once each, after the last edit; `SHIPLOOP_PROGRESS=off python3 -B`): test-loop 148 OK (339 s),
  test-counts 46 OK, confirmation 5 OK, callback-contract 72 OK (140 s), loops 51 OK, navigator-contract 110 OK,
  reference 8 OK, reference-routing 4 OK, packet-obligations 15 OK. A later tidy of the check-only print's
  concatenation (same output) was rechecked with the three test-loop tests that read that print, OK.
- **Suites skipped:** the other packet pin suites (head-order, packet-recut, packet-bounds, packet-completeness,
  step-packets, delegation): the offline render shows no packet line changed (the reference fixture records no
  command twice); the listing changes only for a folded row. handoff, lint, workspace, actual-improve-cli: their
  check-only calls are at intake, test-spec and Improve, which write no test record.
- **Render** (`packets.py --offline node-fix-bug --run-dir-length 83 --cli-path-length 96`, `render_diff.py --unit U9`):
  every stage +0 printed and +0 whole (step-plan 19,673 / 24,327; test 18,004 / 20,759; verify 18,393 / 21,137). The
  diff reports implement FAIL against its head-table value 16,022 at both renders (printed 16,040 on 03c5edbc before
  this change): an existing table gap for the integrator, not this unit's.
- **Key learning:** a fold is safe only when one row checks exactly what the two did, and the folded list must be a fixed
  point, because `validate` re-normalises every accepted result; a single pass is not one (regression A,B; focused A;
  focused B). Reusing evidence needs the floor applied again at reuse time: at the test stage the base run that sets the
  floor runs after the check-only.
