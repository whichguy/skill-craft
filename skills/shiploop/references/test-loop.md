# Test loop and confirmation

Split from the ShipLoop skill card (`../SKILL.md`). Read at `step-plan`, `test-spec`, `test` and `verify`, and when a test gate refuses.

## Test loop

`step-plan` records the work item's test command list in its result:
`"test_commands": [{"command": "<shell command>", "suite": "focused" | "regression" | "check", "ids": ["TC-9"], "min_tests": 1}]`
(`ids` and `min_tests` optional, and never on a `check` row). It also records
`"paths"` (the repository-relative files or globs the item will change) and
`"steps": [{"id": "S1", "task": "...", "deps": []}]`: every implementation step in
order, each step's actual prerequisites as earlier step IDs in `deps` (`[]` for
an independent step; order alone does not imply dependency). ShipLoop refuses a
done `step-plan` without any of these; an empty command list needs
`test_commands_na` with the reason, and a list with no `check` row (lint, type or
build) needs `check_na`.

The `test` stage follows `implement`. Tests are written after the build phase
and must assert the behaviour the test spec's oracle states; ShipLoop mutates a
sample of the item's changed product lines and refuses tests that catch none of
them. Inside its [Until Loop](inner-loop.md#stage-until-loops) the stage writes a test for every
test-spec case (the case ID as its own word in the test's name), runs every
recorded command, the `red-check` command and the lint command, and fixes the
product code (a test only for an independent reason it records) until all pass.
On `done`, after the lint gate, ShipLoop runs two things itself
(`scripts/shiploop_test_loop.py`), each with `/bin/sh -c` from the repository
(at most 10 minutes per command, 30 per run):

1. **Base run** (`base_check`): every focused and regression command in a
   temporary detached worktree at the item's base (after any preparatory fix),
   with only this item's test files copied in. A new test ID (one a focused
   command lists) must not pass there: it must fail because the behaviour it
   asserts is missing, or fail to load the code this item adds. A line that is
   only a path is not a load failure, so a guard that checks or prints a file's
   path is not RED. A command a platform card lists under Remote tests is not
   run on the base. A characterisation test that already
   passes goes in the result's `red_na: [{"id", "reason"}]`, which may name only
   an ID a focused command lists (`tests/<action>-base<N>.md`).
2. **Candidate run** (`loop_run`): every recorded command (focused, regression,
   check) in the checkout. Each must exit 0, show every listed ID and run at
   least its floor (`tests/<action>-verify<N>.md`). The refusal prints each
   failing command, why it did not pass and the end of its output.

A focused or regression command's **floor** is the larger of its base count and
the most any earlier ShipLoop run of this action ran, less each test the
result's `retired_tests: [{"id", "reason"}]` names that the base run showed. A
test removed or newly skipped to pass is refused; a test this item deliberately
retires is declared in `retired_tests`. A command passes only when it exits 0
**and ran tests** that ShipLoop can count and that show every listed ID.

`shiploop red-check --run-dir <run> --action <test action> [--result <draft>]`
runs the base check without completing, so the loop sees what the gate will
refuse. A draft result's `red_na` and `retired_tests` apply. It never gates and
never counts toward the refused runs: exit 0 when no new test ID passes on the
base, 1 when one does or a test did not run, 3 when the check cannot run.

`verify` reruns every recorded command on `done` and may not run fewer tests
than ShipLoop already accepted for the item; the outer `system-test` and
`release-verify` rerun their own recorded commands. Each action allows 11
refused runs (at `test`, base and candidate runs share one tally); after that
ShipLoop no longer accepts `done`, so a failing command takes the stage's own
remedy — back to the step plan with `send-back` at an INNER stage, or corrective
work items with `add-work` at `system-test` and `release-verify` — instead of an
endless retry. A run that times out, cannot start or is skipped on budget
refuses the stage but does not spend one of the 11.

`test` is recorded as not applicable when the item has no test command and
touches only documentation or configuration paths, and `document` when the
item's real diff touches no code or test path. How a run is read (runners, IDs,
skips), the floors' known limits, these not-applicable rules, the outer reruns
and runs that reach no verdict:
[how ShipLoop runs the recorded commands](testing-and-documentation.md#how-shiploop-runs-the-recorded-commands).

These are commands the step plan recorded; ShipLoop runs them outside the host's
permission prompts, and ShipLoop's checks at `complete` and the step plan's Improve
review (a `stage` run; a `none` run has none) are their check. With an
empty list ShipLoop runs no command and accepts `done` with the recorded reason.

## Confirmation is a passing command

A passing test that ShipLoop runs is the only confirmation of a completion
criterion. `step-plan` lists the item's `criteria` and names, in each test
command's `criteria`, the ones that command confirms; ShipLoop refuses a step plan
with an uncovered criterion. Content with no test runner gets a `check` command
(suite `check`, judged by exit code), for example a `grep` that a README documents a
flag. A condition no command can confirm is not a criterion: the step plan records it
as an open item in its summary. `verify` reruns every recorded command.
`system-test-author` records `system_commands` and `release-plan` records
`consumer_checks`; ShipLoop runs them when `system-test` and `release-verify` report
done and refuses unless each passes. At `release-verify` of an isolated run they
run in a clean copy of the result the workspace return delivered (made fresh from the
return receipt into `consumer-check` under the workspace root, never in your
checkout); with no completed return yet they run in the work area, and the test
record (`observed`) and the handoff say so. An empty list needs its `_na` reason. The run records under `tests/` are the
evidence; a result's summary is not.

A request outcome no executed check observed is neither confirmed nor hidden: a
done `product-acceptance` lists it in `unverified` (outcome, reason, check, owner,
due stage), and `[]` says every outcome was observed. ShipLoop refuses a missing
list, an incomplete or placeholder entry and a due stage that is not a later
stage; it cannot judge that the list is complete. It prints each entry at its
due stage and the whole list at `handoff` and in the report.

## Tests pass or the step stops

Each inner stage's [Until Loop](inner-loop.md#stage-until-loops) prints its own repeat
condition (`REPEAT` in `scripts/shiploop_loops.py`). At `implement` and `test`
it is the same rule: run the checks; when one fails, diagnose it, fix the
product code and rerun; change a check only for an independent reason that the
check itself is wrong. Only a final full pass after the last edit counts. The
stage ends on exactly one of: every check passes (`done`); a check proven
unachievable (`send-back`); or, at `implement`, the same check still failing after
7 genuine fix attempts (`send-back`). A check that needs a tool, access or
authority that is absent ends `blocked`, awaiting the person or service that must act. The loop judges its
own iterations; ShipLoop's gates at `complete` (lint, the test runs, the
expectation checks) are the script-enforced part.
