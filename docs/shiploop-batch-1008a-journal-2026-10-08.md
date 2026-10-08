# Batch 1008, worktree A: journal (REVISE, REGISTER, DOCCHECK, B6)

Living journal for the four items built in worktree A of `docs/shiploop-batch-1008-plan-2026-10-08.md`
(navigator and prompts). One section per item, written in the item's own commit. Each entry gives the
status of its findings (firm, interim, exploratory, superseded), the evidence, and what stays unmeasured.
Evidence for every design and audit: `docs/experiments/batch-1008-design-audit-20261008/design-audit.json`
(the entry whose key is the item name). Basis: origin/main 8a198cdd (skill-craft 1.23.0, ShipLoop 0.55.0).
REVISE is not one of the B1 to B12 items, so it has its own section here and not a row in the batch-1007
plan's audit table.

## REVISE: a redone step plan names the plan it amends (2026-10-08)

**Built (status: firm that the lines print and the route accepts an amended plan; the effect on cost is
unmeasured).** When a work item is sent back to `step-plan`, its packet now names the item's previous step
plan and the result that sent it back (both `results/<action>.md`, which `_new_result_records` writes for
every accepted action), asks for an amendment, and has the printed head's Done-when ask the summary to say
which rows are carried over. Code: `_sent_back_results`, `_revise_delta_lines` and the Done-when bullet in
`_goal_lines` (`skills/shiploop/scripts/shiploop_navigator.py`). Tests: `test/shiploop-revise.test.py`.
No state key, protocol version or gate changed.

**Why this much (firm for the numbers, interim for the conclusion).**
- On current defaults a revise redo is cheap: Sonnet 1.22.0 redid 10 stages in 1.18 min against 4.23 for
  the first pass; Grok 1.23.0 redid step-plan and test-spec in 2.28 min against 5.08 (28 and 45 percent).
- The one expensive redo of the current releases, Luna xhigh 1.21.0, rewrote the plan (all 4 criteria
  reworded, 1 step became 5, 2 test commands became 7, step-plan 38.7 to 120.1 min, its Improve child 26.7
  to 76.4 min). The Grok redo amended (all 8 criteria kept verbatim, C9 added). The packet never said
  "amend" and never named the previous plan, because `planning_revision.current_actions` drops the item's
  step plan from "Results this stage builds on" once it is sent back; it stayed only in `context-index.md`
  under "Superseded results".
- Luna has two expensive redos, not one: 123 min on 1.16.1 and 165.9 min on 1.21.0 (see the LEARNINGS
  entries "Luna max battleship on 1.16.1, final" and "Planning time: Luna xhigh and Grok medium on
  1.21.0, and where the minutes go"). Both followed the missing-module cause the test-author probe
  (`test-probe` in `stage_spec.complete_runs`) now guards. Whether the Luna growth was necessary is a
  reader's judgement: the revise reason required a new "real module seam" step.
- Every cheap redo (Sonnet 1.22.0, Grok 1.23.0) kept its context under inline delegation. No redo has
  been measured after a context clear, which is the case the tenet argument is about. So the time effect
  is unmeasured, not zero, and the tenet gain is designed, not demonstrated.

**Corrections from the audit that changed the build.**
- `_replan_delta_lines` is a shape precedent only. Its "result before the replan ... carried over" branch
  is presence-tested (`test_outer_stages_after_a_non_code_replan_are_scoped_to_the_delta`) and has never
  fired in a saved run; the one live packet with the replan delta took the no-prior-result branch. The
  amend wording is therefore not proven by it.
- The amend obligation needed a stated check, so it is also a Done-when bullet in the printed head
  (the full packet's mid-packet lines are about halfway into a 54 KB packet).
- Wording avoids "Revision 1 of 2" (it collides with the head's "revision N" and the budget text) and
  reuses the phrase `_in_progress_lines` uses, "has gone back to step-plan N of 2 times". Both results are
  marked as untrusted accepted host reports to revalidate, because after a clear or in an Ask Agent worker
  the reader is not the author.
- No silent "return nothing if a row is missing": a state that records a revision without its revise row,
  or a revise without an earlier accepted step plan, is refused at render (both refusals are reached by a
  test; the second needs `planning_review none`, because under `stage` the Improve bookkeeping refuses it
  earlier).
- The tautological "state keys unchanged" test was dropped; the guard asserts that the previous plan's
  path is absent from a first visit and from the next item, not that a common word is absent.

**Dropped, with the reasons and a re-open trigger.**
- Script-derived Improve opening (owner backlog item 7, improvement-backlog-2026-10-05). Of 23 Improve
  children across the four runs, 1 `improve-start` was refused: Grok 1.23.0, a 9,450-byte contract, 234
  bytes over the 9,216 budget, fixed in about 39 s. The expensive case is Luna xhigh (4 refusals, 3 of them
  the size guard, in the LEARNINGS entry "Luna max battleship, plan stage: the Backchain loop cannot
  persist its first callback (F3)" and the 1.21.0 planning-time entry). The "0.5 to 1.7 minutes per
  child" figure in the design has no derivation in its cited files: treat it as an estimate. **This drops
  an owner-listed item, so it is the owner's call.** Re-open when a current release shows more than one
  refusal per run recurring, or opening minutes comparable to the stage's own authoring minutes on a host
  the owner cares about. First remedy: raise the bound. `CONTRACT_BUDGET` derives from
  `until_loop_ephemeral.MAX_STATE_BYTES`, a constant in this repository (pinned to `STATE_LIMIT` by
  `test/shiploop-actual-improve-cli.test.py`); `docs/shiploop-fast-planning-plan-2026-10-04.md` (c8) names
  raising it. Second remedy: derive the opening from state.
- Engine "cheaper revise" (skipped stages, delta-only review, a prefilled template, fewer Improve passes):
  each trades S-10 rigour or saves seconds. The result record is about 1,200 tokens.
- Test-red guard against a missing module: already shipped as the `test-probe` run at `test-author`.

**Scope: step-plan only (interim).** `planning_revision.current_actions` also drops the item's test-spec
through integration-verify results after a revise, so those redone stages have the same "previous result
unnamed" gap. Their measured redo cost is lower on all three hosts (Luna test-spec 39.9 to 25.2 min, Grok
113 to 62 s, Sonnet 33 to 16 s), which supports the step-plan-only scope. Re-open on a measured expensive
redo of one of those stages.

**Unknowns left open.**
- Does the amend wording shrink a Luna-class redo? Settle by the next live run that contains a revise: read
  the Run Review export's per-visit minutes, and compare the redo's criteria carry-over and result bytes
  with the first plan.
- The Improve child that reviews the redone plan (76.4 of Luna's 120.1 min) is not told the plan is an
  amendment; whether that shortens its until-two-passes-change-nothing loop is unmeasured. S-10 is untouched.
- A revise after a bound parallel chain (`state['chain_bindings']`) was not examined.
- The could-not-run revise route fixed by 6a59012c is cited without a run; the commit exists.
- Whether a live refusal of the test-author probe on a real missing module ever happens: the probe has
  run at W1 and W2 in the Grok 1.23.0 run and was accepted first time. A failing test plus an unimportable
  module in one command with no ids reads as red (`PROBE_CASES`, "known limit"); adversarial-only, unchanged.

**For the Run Review session (skills/shiploop-run-review is not edited here).** The redo packet grows by
about 600 bytes. The change adds no export field; a stage card must not parse these lines.
