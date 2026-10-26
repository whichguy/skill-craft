# Review brief: do the run-5 changes implement their intents?

## Context
ShipLoop is a script-driven SDLC harness for coding agents: a Python navigator prints one stage packet at a time
(intake, spec, test-strategy, plan, prepare, then per work item step-plan, test-spec, validate-existing, implement,
test, document, verify, carry-forward, then system-test, product-acceptance and the release stages); the model does the
stage and submits a JSON result; CLI gates refuse a result that breaks a rule, and the refusal names the fix. A live
run (run 4: Grok 4.7 building a chess app on a hosted platform, 4 h cap) reached release-plan. Two reviews of that run
found the code graded B- and named generic failure modes: (a) a deferral, not-applicable or "inspection suffices" exit
was too easy; (b) a rule only the Improve reviewer held; (c) a fact stranded in prose that later packets do not quote;
(d) refusal text that taught a workaround. The owner's spec for the run-5 batch (one batch, one release) is below.

## The intents
Earlier run-5 prep (owner-approved):
- I1 the inline implement packet's look-back (the last two commits' lessons) must reach the printed head: in run 4 it
  sat in an optional tier and reached 0 of 9 printed heads.
- I2 a test command that runs against a deployed target (listed by a platform card under Remote tests) must not be run
  on the item's base, because the target already holds the change (run 4's W2 send-back) and running it deployed base
  files; record why, like the mutation gate's existing skip.
- I3 context-usage measurement per window between compactions (harness only). Result: ShipLoop's own skill files are
  30-34% of context; the Improve route card (47 KB) is read whole at every Improve stage.
- I4 a lean Improve route card (being built separately; not in this diff).

The owner's F1-F6 spec ("structure, not prose": a required result field per decision, a placeholder stating the bar, a
CLI gate on the field, downstream packets quoting it by value):
- F1 test-strategy `surfaces: [{surface, layer: unit|component|e2e, harness, status: available|prerequisite|unverified,
  reason}]`; gate: no `unverified` on unit/component for code the run writes (that is prerequisite work for prepare);
  step-plan criteria gain `confirm: executed|inspected`, `inspected` must name the surfaces row showing no runner;
  Improve focus: "a code surface whose only check is a source grep".
- F2 RED must come from missing behaviour: test-spec `red` placeholder states it; gate: refuse a focused command whose
  IDs all passed on an earlier item; rewrite the refusal that taught `test -f` + printf; a route test of the named exit.
- F4 test-spec `entry_points: [{name, throws, rows}]` with at least one error-oracle row per declared throw; every
  test_cases row gains a required `stand_in_rejected` (the weaker implementation the oracle fails); verify 4: "not a
  quoted case" is no reason to leave a path untested; spec NFRs state numeric thresholds below hard platform limits.
- F3 test-strategy `targets: [{target, keeps_state, base_state_route}]`, quoted into step-plan and test-spec; a
  test-spec row on a keeps_state target says in `red` how the base state is produced.
- F5 an Improve code fix ships with a regression test (`Regression test: <ID> | none: <reason>` in the improve-commit
  message, gated); three Improve focus lines (cross-field validity of parsed input; a language pitfall applied to every
  instance; each failure state names the user's next action).
- F6 `unverified` rows gain `lower_layer_check`; a primary request outcome is accepted only with an executed
  lower-layer check, else add-work.

## What is built so far (files in this folder)
- `commits.txt`: the five local commits with their messages (I1, I2, I3, F2's gate and RED wording as "Q2", and a
  stage-text commit "Q1, Q3-Q7" written before the F-spec arrived, which added duty prose).
- `diff.patch`: the full diff against main, including F1 in progress (uncommitted): new module
  `skills/shiploop/scripts/shiploop_test_layers.py`, navigator wiring (`_check_submitted_layers`, the criteria
  `confirm`/`surface` fields, a required "test-layers" packet block at prepare, step-plan and test-spec), duty text.

## Design choices the builder made that depart from or interpret the spec (please judge each)
- D1 F2's "rewrite the send-back": the phrase that taught the workaround ("fails when the added class files are absent,
  and names an added path") was the MODEL's own send-back summary, which ShipLoop quoted into the redo packet; the
  ShipLoop-side cause was the base-run refusal ("fail to load only because a file this item adds is missing"), reworded
  in Q2. Also the base-run detector now ignores a line that is only a path. Is that the right fix, and is anything left?
- D2 F2's gate is "a focused command whose IDs are ALL focused IDs of another item's step plan" (from step-plan
  results), not "IDs that all passed on an earlier accepted item" (from test runs). Equivalent enough? Loopholes?
- D3 I2 skips remote commands on the base entirely, so remote-only items get no automated RED check (and the mutation
  check already skips them). Combined with F3's base_state_route, is RED for stateful remote targets now only a text
  obligation? Should a gate enforce it?
- D4 F3: test_cases rows will gain an optional `target` naming a `targets` row, so the gate can tell which rows run on a
  keeps_state target (the spec does not say how rows map to targets).
- D5 F6: "primary request outcome" will be an explicit `primary: yes|no` on unverified rows (the script cannot infer
  primacy).
- D6 the earlier stage-text commit (Q1, Q3-Q7) added prose that overlaps F1/F3/F4/F6; the builder is replacing the
  overlapping prose with field references as each field lands. Keep, trim, or revert that commit?
- D7 F1's `surfaces_na` (a reason) stands in for an empty surfaces list when the run writes no code; is that another
  too-easy exit (failure mode a)?

## Questions
1. For each intent (I1, I2, F1 so far, F2): does the change implement it? Name any mismatch, with file and function.
2. Judge D1-D7: agree, or what instead.
3. Which of the failure modes (a)-(d) does the plan still leave open, and what is the smallest structural fix?
4. Risks: refusal load (run 4 had 13 refusals, all fixed in stage), head budget (the printed packet is cut at 20,000
   characters; step-plan is closest), fixture churn, and any rule that could block a legitimate run with no exit.
5. Anything you would add, drop or reorder before the release and run 5? Keep advice generic: ShipLoop must not be
   tuned to the chess app or one platform.
Answer concisely, ranked by effect on the code ShipLoop produces.
