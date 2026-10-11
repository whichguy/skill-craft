---
bump: major
---
The inner loop runs 8 stages in 5 phases instead of 17 stages.

| Phase | Stages |
|---|---|
| Plan | step-plan, test-spec |
| Validate existing | validate-existing |
| Build | implement per step, test, document |
| Verify | verify |
| Carry forward | carry-forward |

A run saved by the 17-stage loop (state version 4) is refused, with a reason.

- **Every inner stage is an Until Loop.**
  - The packet says `INVOKE /until-loop NOW`, then the work, the exit conditions (the same words as Done when) and
    the repeat condition.
  - ShipLoop writes the stage's contract to `loops/<action>-contract.json` and, at complete, checks the receipt
    `loops/<action>-terminal.json` against the contract rebuilt from state.
  - `repeat` is no longer an inner outcome.
- **step-plan** also records:
  - check commands (lint, type, build), or `check_na`;
  - an `expectations` list: works, absent or broken, each with a read-only check command;
  - per-step helper `skills`, which the implement packet prints.
- **validate-existing** replaces baseline.
  - ShipLoop runs every expectation's check on the unchanged checkout. When all match, the stage is recorded without
    a packet.
  - A known small fix to a works expectation found broken is made here. ShipLoop commits it on accept, as its own
    commit.
- **implement** is gated by lint on every step, and an Improve child reviews every accepted step.
  - The review uses `IMPLEMENT_STEP_REVIEW_FOCUS` with the Code craft rubric.
  - It runs even under `--planning-review none`.
- **test** follows implement. It writes the test spec's cases, runs every recorded command and fixes until all pass.
  At done, ShipLoop:
  - runs the item's tests on its base (after any preparatory fix) and refuses a new test ID that passes there,
    unless `red_na: [{id, reason}]` names it;
  - runs every command on the candidate, holding the floor (base count and earlier runs);
  - accepts a deliberate removal declared in `retired_tests`.

  `shiploop red-check` runs the base check without completing.
- **document** is recorded as not applicable when the item's diff touches no code or test path.
- **verify** takes over:
  - from static-checks: the change inventory, the first-entry lint auto-fix and the review loop;
  - from integrate: the item commit.
- **carry-forward** records a skill decision: `none | reuse | update | create`.
  - A created or updated skill must name an existing `SKILL.md` with name and description, and list its repeat
    evidence.
  - ShipLoop commits it.
- **`complete --check-only`** runs a stage's script gates on a result without completing the action.
