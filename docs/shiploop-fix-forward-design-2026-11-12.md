# ShipLoop fix-forward: done steps stay done (design, 2026-11-12)

Owner direction, 2026-11-12: "I want to avoid send back about redoing steps ... at the end of an inner loop, even if
there are things to change, we should add or augment existing or new steps in the step-plan not revisit old steps. This
is a fix forward motion." Owner answer after the review: "Build, replay after".

Evidence and reviews: `docs/experiments/step-boundary-replan-20261112/` (README E5 and E6; `fixforward.out`;
`astra-fix-forward.md`). In 300 runs, 81 inner send-backs were followed by an accepted step plan. The redone plan
changed a done step's row once. Every late send-back still re-ran implement, test and document for every done step,
because a send-back drops the item's results from the step plan on (`planning_revision.current_actions`,
`step_actions`).

## The rule

A **done step** is a step of the item's current step plan whose `document` result was accepted. Acceptance comes after
the step's review, and the step commit runs in that same call (`_apply_result` with the review's record,
`_commit_stage`). An automatic not-applicable document is accepted the same way.

1. **A send-back keeps the done steps.** An INNER send-back (test-spec through document) still returns the item to
   step-plan. Every step done under the plan in force stays done: its implement, test and document results, commit,
   review and test counts are kept, and none of them runs again. The interrupted step's results are dropped, and its
   uncommitted edits stay in the checkout for that step's next attempt.
2. **The amended plan carries the done steps as written.** The step plan after such a send-back starts `steps` with
   the done steps' rows, byte-identical to the previous plan's except for the added mark `"done": true`. The packet
   prints those rows to copy. Only rows marked done are kept, and the mark is valid only on exactly those rows.
   Retention is a property of the accepted plan, so a plan without marks (every plan written before this change)
   reads as it always did.
3. **Done steps' contracts are frozen.** The `criteria` entries a done step lists keep their definitions. No
   unfinished step may list them (`iteration.case_step` gives a criterion to the last step that lists it, so a new
   step re-listing C1 would move TC-1; Astra reproduced this). A defect in a done step's behaviour becomes a new step
   with new criterion and case IDs.
4. **Frozen cases.** The test spec after the amendment keeps every case of a done step's criteria byte-identical, with
   the same ID.
5. **At least one unfinished step.** An amendment with nothing left to run is refused. The item's last-step
   obligations (the full regression, checks due at the last step) always have a step to run at, so no closure
   transition is needed.
6. **Everything else is as today.** IDs stay unique. The interrupted step and later steps may change, be reordered
   among themselves, be removed or be added. Expectations describe the item's lint base, which ShipLoop moves to the
   tree the last done step left when the next step begins, and a send-back keeps it. So the amendment's expectations
   describe what the done steps left, and a done step's own expectation is restated (absent becomes works), as the
   replayed plans did. Every later step still runs the earlier cases and the minimum
   regression, and the last step runs the full regression (b385df5d7005de79e2522de308b3feb57b397716,
   b55909179b89bfc63bba67d4cdbb833c700df147). A changed requirement intent stays a block or a pause, never an
   amendment.

## Decisions (routine, recorded)

- **Mark in the data, not a version flag.** One-supported-version rule: no version flag and no legacy branch. The
  `done` mark carries the meaning, and only fix-forward writes it.
- **The planner copies the rows; the script checks them.** Astra preferred a mechanical copy. Changing a submitted
  result in the script would break the replay check (`_apply_result`: a resubmitted result must equal the accepted
  one). The packet prints the exact rows, and a refusal names the first differing row. A typing slip costs a refusal,
  never a silent change.
- **The amendment base already exists.** Astra's rule 5 asked for expectations judged at the last done commit. That
  is ShipLoop's behaviour today: the step-entry hook re-captures the item's lint base when a later step's implement
  begins after a document (`lint.capture_base`), a send-back keeps it, and step-plan's expectation gate and
  validate-existing read that base. Found by the first fix-forward test: "expectation E1 is absent, but notes.md exists
  on the item's lint base". Nothing changes for expectations.
- **No closure transition.** Rule 5 makes it unnecessary (Astra's rule 7, first half).
- **Deferred: a document that is done and asks for an amendment.** That is Astra's boundary route: commit this step,
  then amend later steps. It is the next unit, measured by the replay the owner chose to run after this. Until then a
  boundary finding is a send-back, and under rule 1 it no longer replays the done steps.

## Code

One projection: `planning_revision.step_actions` keeps the done steps' per-step actions across the send-back and the
plan that marks them, and `current_actions` keeps their latest. The cursors read it: `implement_progress`,
`test_loop.step_number` and `loops.current_step` count `step_actions(..., "implement")`; `step_view` pairs steps with
those actions; `_previous_step_results` skips done rows. Gates: the step plan after a send-back
(`planning_revision.amendment_refusal`) and the test spec after it (`frozen_case_refusal`). Packets: the step-plan and
test-spec revisit lines list the done rows and frozen cases.

## Tests (negative controls from Astra's list that apply here)

- An identical amendment after S1: S1's actions and commit stay, and the next packet, loop contract, Proof and test
  cursor all name S2.
- Two amendments in a row: S1 survives both; an edit to it is refused.
- A changed done row, a dropped done row, a mark on an unfinished row: each refused.
- A new step listing a done step's criterion: refused.
- A test spec that changes or drops a done step's case: refused.
- An amendment with no unfinished step: refused.
- S1's open items and test counts stay visible after the amendment, not double-counted.
- S2's uncommitted edits from before the send-back land in S2's commit, not S1's.
- A plan without marks after a send-back replays as before (the existing replay test now asks for the marks, so it
  becomes the fix-forward test; one plan without marks pins the old reading).
