# Row: W2-A (the per-step Proof) and W2-B (one step block on every surface), branch feat/pr-w2-proof-75e8ad

- Date: 2026-10-17. Base: e6a86587, rebased onto b0bacf5f (the integration fixes; the coordinator's instruction), so the
  branch carries that commit unchanged. Status: **interim** (offline renders and suites only; no live run yet).
- Spec: `/Users/dadleet/src/skill-craft/docs/shiploop-implement-step-fix-plan-2026-10-17.md` sections 2.1, 2.2, 3.1, 3.3,
  3.4, 4.1, 5 and 6 (T1, T2, T5, T6, T8-T12, T17, T27, T31, T33), with the dispositions in section 5 of
  `docs/shiploop-packet-review-plan-2026-10-17.md` (knowledge stays a table of contents; Code craft text kept; static
  guidance from files and `criterion_evidence` are W2-D, not here).
- Questions. W2-A: can each step be proven by its own command, run by ShipLoop at the step's done and again before a
  changed Improve review is imported, so that no step is asked to pass a check on a later step's work (finding F1, the
  chess run's S1 that got S3's board grep and merged three steps)? W2-B: do the packet file, its printed head and the
  step's Improve hand-off carry the same step block, with the loop last and no path fence (F15, F3, F5)?

## Change

- Step plan (`shiploop_navigator._normalise_steps`, `_check_step_sizing`, `_result_template`; `shiploop_prompts` step-plan
  duty items 4 and 5; `shiploop_stage_spec` step-plan condition 3): every step records `check`, one command line, refused by
  name without it ("step S1 must record its check"); per-step `paths` optional (the inline template asks none, the
  ask-agent template keeps them for the chain); `shiploop_expectations.check_step_plan` covers the item's non-test paths
  when a step names none. The step-plan Improve focus (`_REVIEW_FOCUS_STEPS`, one line) flags "a check that needs a later
  step's work or passes by skipping a missing artifact".
- The Proof (`shiploop_test_loop.step_command`, `step_proof`, `step_proof_path`, `step_proof_check_only_path`,
  `STEP_PROOF_STAGES`; stage table complete run `step-proof`): `_run_command` + `judge` (suite check: exit 0, and a runner
  summary that ran no test is refused) with the test loop's timeout and budget; record `RUN/tests/<action>-step-proof<n>.md`
  in the test-loop schema with `kind: step-proof`, action, step, command, phase and the working trees the run started on
  and left. A passed record of the same step and command whose trees hold today's tree is taken instead of a run.
  Dispatch: `_step_proof_gate` after the lint gate at an inline step's done (check-only writes the uncounted record);
  `_improve_change_gate` reruns it at the step's Improve import (phase `improve-import`, no write when reused). The
  ask-agent whole-plan action is not gated (`step_view` is None there).
- The six item-check consumers (fix plan section 5): implement duty 3 (inline paragraph swapped in,
  `_IMPLEMENT_CHECK_INLINE`; the ask-agent duty names each step's Proof instead of "Step lines" it never had); implement
  `done_when` (condition 1 `STEP_CRITERIA_CONDITION`, the D4/D7 words, the step's criterion IDs appended by
  `loops.worded_stage`; condition 2 `STEP_PROOF_CONDITION`, shared word for word by both wordings, as the stage-spec pair
  test requires); the stage's test text; the repeat rule (`loops.REPEAT_STEP`, the section 3.4 wording, for the inline
  step; `REPEAT["implement"]` stays the whole-plan route's); the step Improve focus's rerun sentence and its check bullet
  (the ask-agent focus is byte-identical to base through `_STEPS_WORDING`); `test_loop.stage_commands` (the step's Proof
  row at an inline step). `shiploop_navigator.step_checks` (603a709c's interim rule) is removed.
- One step block (`step_view`, `step_block`, `_step_lines`, `_review_base_line`): task; "Serves" with the criteria by
  value; the test case IDs of those criteria; "Depends on" with each accepted dependency's result locator; the Proof; the
  skills; the accepted steps; the later steps by id and first sentence; the item-paths commit line. The producer packet
  prints it right after Done when (P1 `step` block, with the line that says the stage runs inside the /until-loop at the
  end); the inline step packet ends with its loop in the file and the head (`_select_head` fills optional blocks only
  while a trailing required block still ends before `HEAD_REQUIRED_END`, 19,500); the step's Improve hand-off prints the
  same lines, its quoted criteria by ID, and the review base. Path fence gone (fix plan D3): goal, duty 1 (inline), loop
  scope (the item's declared paths), Improve focus.
- Review base: `_step_entry` (in `_transition`) records the working tree, untracked files included
  (`improve_changes.snapshot_tree`), in the implement action record (`base`, validated by `_validate_action`); the
  hand-off prints `git -C <repo> diff <base> <bind tree>`.
- Loop Work (`loops.WORK_STEP`, `step_anchors`): "Implement all of step S2 of this item's plan, anchored in the
  requirements that have been stated (C2, serving R-2 in docs/shiploop/spec.md) and the design directions that have been
  applied (AD-1 in docs/shiploop/architecture.md), until each requirement assigned to this step is satisfied and none of
  the others is broken." R-n from the step's criterion texts (`knowledge_home.requirement_ids`, renamed from `_ids`), else
  the item's follows; AD-n from follows; read from state only, so the contract rebuilds identically. The ask-agent Work is
  unchanged (T31).
- State version 6 -> 7 (`V6_REASON`, in `validate` and the CLI's saved-run reason).
- Docs: SKILL.md (version paragraph), references/navigator.md, references/state-files.md, context index (`RUN/tests/`
  row, in-progress Proof line). Run Review: `defaults/stages.json` regenerated (`export.py --stages`).
- Ledger: two new rows, `step-proof` and `step-plan-check` (`test/shiploop_e2e/packet_obligations.json`); none removed.

## Fail-first

- At e6a86587, the new tests only: callback-contract T1/T2/T5 FAILED (3; the template has no `check`, a step's `check` is
  refused, steps without paths are refused); delegation StepBlockTests and the converted proof test ERROR (5; no
  `_step_entry`, step `check` refused); loops T12 FAILED (Work names no criterion), T31 Work guard passed (it pins
  today's text); revise T17 FAILED (version 6 accepted), handoff T17 FAILED (6 != 7).
- StepBlockTests at base with a no-op entry hook and the `check` key dropped: T8 KeyError 'base'; T9 the hand-off has no
  TC-1; T10 the loop is not the last block (both head limits); T11 the Work lacks the D4 words.
- test-loop T6/T27/T31/T33 at b0bacf5f with today's test files: ERROR (5) at step-plan (the `check` key is refused);
  with the key dropped before validation: T6 implement's commands are the item's, not the Proof; T27 zero-test Proof
  accepted ("NavigatorError not raised"); T27 binding: no step-proof run in check-only; T33 KeyError 'base'; T31 gate
  passed (it is a guard: the base has no step gate to leak).

## Suites (once after the last edit)

All OK, 42 suites, 2328 tests: packet-bounds 10, step-packets 9, packet-recut 30, head-order 36, reference 8, packet-
obligations 15, reference-routing 4, packet-completeness 62, revise 15, delegation 63, loops 53, stage-spec 14,
improve-route 17, improve-changes 4, handoff 98, navigator-contract 110, lint 85, e2e-render-diff 43, e2e-packet-
anatomy 30, improve-schedule 33, confirmation 5, run-review 658, e2e-fidelity 136, quality 11, navigator-v4 18,
consumer-delivery 32, discovery 8, guidance 64, navigator-dry-run 34, rehydration 17, planning-handoff 7, knowledge
135, assumptions 9, full-runtime 2, callback-contract 81, domain-words 5, package-integrity 11, keepalive 60, skill-
calls 34, actual-improve-cli 84, return-review 25, test-loop 153.

Not run (and why): the e2e harness suites that only import knowledge_home (e2e-commit-counters, e2e-efficiency,
e2e-slice, e2e) and progress-data/workspace: they read no symbol this unit changed (`_ids` had no caller outside the
module); no run-all, no live E2E.

## Renders (packets.py --offline, text-dir; before = b0bacf5f, after = this branch)

| render | packet | printed before -> after | whole before -> after |
|---|---|--:|--:|
| node-fix-bug inline 83/96 | step-plan | 19,989 -> 19,961 | 23,466 -> 24,047 |
| node-fix-bug inline 83/96 | implement | 15,892 -> 16,104 | 18,303 -> 18,515 |
| node-fix-bug inline 163/96 | step-plan | 19,343 -> 19,924 | 24,986 -> 25,567 |
| node-fix-bug inline 163/96 | implement | 16,772 -> 16,984 | 19,263 -> 19,475 |
| node-fix-bug ask-agent 83/96 | step-plan | 19,224 -> 19,923 | 26,857 -> 27,556 |
| node-fix-bug ask-agent 83/96 | implement | 17,424 -> 17,544 | 21,403 -> 21,523 |
| node-fix-bug ask-agent 163/96 | step-plan | 19,647 -> 19,528 | 28,377 -> 29,076 |
| node-fix-bug ask-agent 163/96 | implement | 18,304 -> 18,424 | 22,363 -> 22,483 |
| two-item walk inline 83/96 | step-plan (W1) | 19,850 -> 19,631 | 23,545 -> 24,126 |
| two-item walk inline 83/96 | implement S1 | 19,959 -> 19,062 | 22,401 -> 23,574 |
| two-item walk inline 83/96 | implement S2 | 19,474 -> 19,398 | 21,908 -> 23,158 |
| two-item walk inline 83/96 | implement W2 S1 | 19,439 -> 19,475 | 21,881 -> 22,962 |
| two-item walk ask-agent 83/96 | step-plan (W1) | 19,272 -> 19,971 | 26,936 -> 27,635 |
| two-item walk ask-agent 83/96 | implement | 19,775 -> 19,820 | 25,050 -> 25,095 |

node-fix-bug's synthetic step plan has no steps, so its implement packet has no Step block (its growth is the new exit
conditions and duty text); the two-item walk (`test/shiploop_head_plans.full_walk`) is the step case. Every printed text
stays under 20,000 at 83 and 163; the inline step heads end with the loop before 19,500 (their required text is about
17,000-17,300, so the head now gives up the pause line and the quoted hand-offs to the file). Against the fix plan's
16,000-character target (measured, not a gate): every step-plan and inline implement head is above it, by about
1,000-1,300 characters of required text for implement. Both head tables re-measured with the reason in `_comment`/`_doc`.
The Improve hand-off's improve-commit line ends at 4,470 for the inline implement step (bound 4,500; 4,449 at base) and
4,494 for ask-agent (unchanged).

## Key learnings

- The interim rule (603a709c) placed an item check at the step that finishes its criteria; it still needed the item's
  check commands to be step-shaped. The Proof makes each step name its own command, and the item's checks go back to
  the test stage and verify, where they ran before the 8-stage loop.
- A trailing required block changes the head contract: "required first, optional after" no longer holds, so the head
  budget for optional blocks has to stop at the required-text bound, not the host cut (19,500, not 20,000).
- The ask-agent route shares the implement duty and the stage row: a route-specific paragraph swap (as the chain duty
  already does) keeps the whole-plan text intact; byte-compare the ask-agent focus, prompt and Work against base.
- `git diff <tree>` against a working-tree snapshot shows untracked earlier steps as deleted; the review base must be a
  tree-to-tree diff (entry snapshot to bind snapshot).
