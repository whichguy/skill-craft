# Spec changes after the plan: every route, what each does to the plan, the gaps (2026-11-22)

The owner's rule, 2026-11-22, verbatim: "We should also be clear that if we do update the spec, we would definitely
need to incrementally update the plan to accommodate the spec changes."

Consumer: the main session writing section 9 of `docs/shiploop-end-of-inner-loop-journal.md`, and anyone who later
designs a stage or gate that changes the living spec during a run.

Scope and method. A read-only study of ShipLoop's source at skill-craft `main`
4758480e40c646c0d09eaf394ec6b00feaaf82a1 (ShipLoop source identical to 2ddacc9ed7317a7576e2cfefd477bf63c3fa4862,
ShipLoop 2.6.1: `git diff --stat` of `skills/shiploop` between them is empty). Nothing in the repository was changed
outside this folder; nothing was committed. No ShipLoop command, E2E harness, model or test file was run. Three
read-only scans of the saved E2E deliveries under `~/e2e-runs*/` ran (`git log` and `git show` on each delivery's
`work/` checkout; one scan imports ShipLoop's own spec-entry parser, `shiploop_knowledge_home._entries`, to read
entries the way the gates do). Their scripts and outputs are in this folder (section 7).

Status. What the source does (sections 1 to 3 and 5) is firm: read from the code, each claim with its file and
symbol. The counts of saved deliveries, wherever they appear, are interim: they rest on a line classifier and a
boundary rule stated in section 7. Section 4 is a proposal, not built and not tested.

Terms. *Plan boundary*: the moment the `plan` stage's result is accepted; "after the plan" means every stage from
`prepare` on. *Changed requirement*: an R-n entry of `docs/shiploop/spec.md` that lost a line it held at the plan
boundary, or that is new or newly retired since then (a line added to an entry is no change). *Route*: a way the
spec, or what the run treats as its requirements, can change after the plan. *Re-planning* of a part of the plan
means the stage that wrote that part runs again (or a stage that owns it amends it) with the change as input.

## 0. The answer in five lines

1. After `prepare`, no script route re-enters planning (spec, test-strategy, plan) for a spec change. The only
   script route back into planning is the plan review's reconcile, and it is refused once `prepare` or any work item
   has run (`shiploop_navigator._reconciliation_permitted`).
2. The spec can still change after the plan at most stages: outside a step, the script checks only that no R-n is
   dropped (`shiploop_knowledge_home.check`). Only implement and document (and the step's review) are held to
   add-only marked lines (`shiploop_knowledge_home.step_spec_refusal`, called from `shiploop_navigator._evaluate`
   and the Improve import in `shiploop_navigator.dispatch`).
3. When the spec changes, the script changes nothing in the plan: not the queue, not a completed item's step plan,
   test spec or tests, not the test strategy, not `primary` or `defaults`. The next item's step plan does not even
   receive the change (`shiploop_navigator.CONSUMES["step-plan"]` is `("assumptions",)`).
4. Two parts route the same finding differently: a changed requirement is a send-back to `step-plan` from
   implement and document, and a stop for the person (`blocked`) from carry-forward. The 2026-11-12 review asked
   for this to be aligned; it never was (section 3, G4).
5. The smallest change that makes the owner's rule true by script is one gate built like
   `shiploop_primary.check_queue`: every requirement changed since the plan must be routed to a work item still to
   run whose `follows` names it (its step plan then re-plans it), or marked `none` with a reason; plus one
   script-placed line in the affected item's step-plan packet. On the 58 unseeded released-engine deliveries of
   ShipLoop 2.4 and later it would have fired in 6 (section 4).

## 1. The map: every route after the plan

| # | Route | Spec edit the script allows | What the script does to the plan | Enforced by |
|---|---|---|---|---|
| R1 | plan's Improve review, `improve-reconcile` | any (the review can edit files) | restarts planning at the target (discovery, research, spec or test-strategy); every planning stage after it reruns | script, but only before `prepare` |
| R2 | `prepare` and its knowledge close | any that keeps every R-n | nothing | script (files present, IDs kept) |
| R3 | `step-plan` (and its first-item review) | any that keeps every R-n; the duty forbids spec edits | the item's own plan is written; nothing else | script for IDs; the rest is prompt |
| R4 | `test-spec`, `validate-existing` | any that keeps every R-n | nothing; a case that cannot be tested, or a wrong expectation, is a send-back | script for IDs |
| R5 | `implement`, `test`, `document`, and document's review (a step) | only new lines inside an R-n the committed spec holds, ending with the step's mark | nothing; any other spec edit is refused and the refusal names send-back | script |
| R6 | send-back from test-spec through document | none of its own (it goes to R3) | the item reruns from step-plan; done steps are kept (fix forward); test-spec reruns; no planning stage reruns | script |
| R7 | `carry-forward` | any that keeps every R-n; the duty tells it to write spec.md | may replace the whole future queue; primary requirements must stay followed | script for the queue's shape and primary coverage; the rest is prompt |
| R8 | the end-of-work Improve review (after the last carry-forward) | any that keeps every R-n, and a review's own commit is never checked | may add work items | script for IDs (uncommitted edits only) |
| R9 | outer stages and their reviews (system-test-author, release-plan) | any that keeps every R-n | `add-work`: new items run the inner loop, then the outer stages from system-test-author; system-test and release-verify may send back to the stage that wrote their plan | script |
| R10 | product-acceptance | any that keeps every R-n | gaps become add-work; a user correction can settle an unverified outcome without any spec change | script for the ledger; prompt for the judgment |
| R11 | an owner note (`shiploop note`) | whatever the current stage allows | nothing: notes "do not change the callback, the result template or ShipLoop's checks" | script delivers the text only |
| R12 | the requester's answer: a blocked stage resumed with `--answer` | whatever the resumed stage allows | the same stage reruns with the reply; nothing else | script |
| R13 | the spec's `defaults` (choices the spec made for the requester) | none (shown only) | nothing; a changed default is "a new run" | script shows them; no answer route on main |
| R14 | the knowledge closes at prepare, release-plan, release-verify | any that keeps every R-n | nothing; release-verify's lessons become the commit body | script (files present, IDs kept) |
| R15 | pause and resume; halt | n/a | none: a pause keeps the action pending | script |
| R16 | an open item a stage records in `assumptions` | n/a | settled by the due stage's later done result, by order alone | script (ordering only) |
| R17 | the opt-in delivery contract (`delivery_contract_version` runs) | its own typed requirement ledger | a material change after release planning sets a replanning barrier, cleared only by add-work, then fresh system-test and release-plan | script |
| R18 | the handoff's `follow_on` list | none | a recommended next run; ShipLoop starts nothing | script (shape) |

## 2. Each route in detail

Each entry gives the edit allowed, what happens to the four parts of the plan (the work-item queue; the item's step
plan; its test spec and criteria; the regression set), whether a script or only a prompt enforces it, and the tests
that pin it (file, then test name).

### R1. The plan's Improve review reconciles back into planning (before prepare only)

- Edit: the review child may edit any file, the spec included.
- Plan: `shiploop_navigator.reconcile` records a `reconcile` outcome and sets the stage to the target;
  `shiploop_planning_revision.current_actions` drops every planning result from the target on
  (`RECONCILIATION_TARGETS` = discovery, research, spec, test-strategy), so spec, test-strategy and plan rerun in
  order and the plan's queue may be replaced (`_replace_plan_work_items`).
- Enforced: script. `_reconciliation_permitted` refuses unless the stage is `plan`, `work_index` is 0, no item is
  completed or started, and every history row is a prelude stage before prepare; `planning_revision.validate`
  refuses a reconcile that "occurred after prepare or work execution".
- Tests: `test/shiploop-navigator-v4.test.py` `test_reconcile_is_rejected_by_normal_success_paths_and_after_prepare`,
  `test_cold_reconciled_v4_plan_packet_lists_current_sources_and_revalidates_queue`,
  `test_two_reconciliations_follow_history_order_even_when_clocks_reverse`.
- This is the one route that does what the owner's rule asks, and it closes at the plan boundary.

### R2. prepare

- Edit: any spec edit that keeps every R-n: `shiploop_knowledge_home.check` refuses only a missing close file
  (`CLOSES["prepare"]` requires spec.md, environment.md, architecture.md) and a dropped ID.
- Plan: nothing; on accept the run enters the inner loop (`_apply_result`, `_begin_inner_loop`).
- Enforced: script, for the files and the IDs only.
- Tests: `test/shiploop-knowledge.test.py` `test_a_close_needs_its_files_and_commits_only_the_home`,
  `test_the_living_spec_keeps_every_committed_requirement_id`.

### R3. step-plan

- Edit by script: any spec edit that keeps every R-n. `_step_spec_refusal` returns "" outside a step and is called
  only for implement and document (`_evaluate`) and for document's review (the Improve import in `dispatch`); the
  knowledge close commits step-plan's home edits (`_knowledge_close`).
- Edit by prompt: none. Duty 10 of `DUTIES["step-plan"]` (`shiploop_prompts.py`): "Keep every R-<n> and AD-<n>;
  write nothing else in KNOWLEDGE/." `STAGE_FILES["step-plan"]` is architecture.md and environment.md.
- But two script texts invite a spec addition here: the `follows` refusal in `_handoff_fault` says "drop each other
  ID, or add its entry to the living file", and `shiploop_primary.check_queue` says "cite only IDs with an entry, or
  write the entry first" (that one at plan and carry-forward).
- Plan: the item's `criteria`, `steps`, `test_commands` (focused, regression, check), `expectations`, `paths`,
  `follows`. Its packet lists spec.md by its table of contents only (`shiploop_knowledge_home.READS`,
  `shiploop_navigator.reads_lines`), quotes the item's plan-written `context` (`_work_item_block`) and the plan's open
  items due at this item; no spec diff (`CONSUMES["step-plan"]`).
- Tests: `test/shiploop-knowledge.test.py` `test_closes_and_stage_files_name_only_living_files`,
  `test_a_step_plan_that_adds_a_decision_is_committed_with_the_home_and_kept_afterwards`,
  `test_a_non_close_stage_that_changed_the_home_is_committed`. No test pins that step-plan may not change the spec.

### R4. test-spec and validate-existing

- Edit: any that keeps every R-n (no step yet, so `_step_spec_refusal` does not apply). Neither duty writes spec.md.
- Plan: test-spec's cases must name requirements that have an entry in the current spec
  (`shiploop_expectations.check_test_cases`); its packet lists the current R-n with the first line of each
  (`_requirement_lines`). "Untestable as written: report send-back naming it" (`DUTIES["test-spec"]` item 7).
  validate-existing sends a wrong check or a wrong step back with `failed_expectations` (route `check` or `steps`).
- Tests: `test/shiploop-navigator-contract.test.py` and `test/shiploop-callback-contract.test.py` cover the case
  checks; none covers a spec edit here.

### R5. A step: implement, test, document, and the step's review

- Edit: only new lines inside an R-n entry the committed spec holds, each ending `(<item>/<step>)`
  (`shiploop_knowledge_home.step_spec_refusal`). Changing or removing a committed line, or adding an R-n, is refused:
  "to change a requirement, report send-back naming it". Checked at implement's and document's complete and at the
  import of document's review; a refusal at a complete opens the action's send-back (`loops.open_send_back` in
  `_evaluate`). A test-stage edit is caught at document's complete, because the step's one commit comes after
  document and its review (`_knowledge_close` skips implement and test inside a step).
- Prompt: implement hands off "an acceptance detail as a line in its R-<n> entry ... ending (<item>/<step>)";
  document's duty 3 adds lines only, and "a requirement whose intent moved is no edit: report send-back naming the
  R-<n>" (`DUTIES["document"]`).
- Plan: nothing beyond the step's own commit.
- Enforced: script.
- Tests: `test/shiploop-navigator-contract.test.py`
  `test_a_steps_acceptance_line_in_the_spec_is_accepted_and_committed_with_the_step`,
  `test_a_changed_requirement_at_implement_is_refused_and_send_back_is_the_accepted_exit`,
  `test_a_requirement_a_step_adds_is_refused_and_send_back_is_the_exit`,
  `test_a_spec_line_document_adds_is_held_to_the_steps_mark_and_committed_with_the_step`;
  `test/shiploop-actual-improve-cli.test.py`
  `test_a_step_reviews_unmarked_spec_line_is_refused_at_its_import_and_a_marked_one_is_imported`;
  `test/shiploop-knowledge.test.py` `test_a_step_spec_line_may_end_in_sentence_punctuation_after_its_mark`.

### R6. Send-back to step-plan (fix forward)

- Edit: none of its own; the item goes to R3, whose duty forbids a spec edit.
- Plan: `_apply_result` counts the send-back in `revisions` and replaces the item's action with a fresh step-plan
  (`_replace_inner_action`). `current_actions` drops the item's results from step-plan on, except the done steps an
  amended plan keeps (`planning_revision._StepLists`). The amended plan must start with the done steps exactly, mark
  them `"done": true`, keep their criteria, and leave a step to run (`_fix_forward_refusal`); test-spec reruns and
  keeps the done steps' cases exactly (`_frozen_case_refusal`); both run in `_check_fix_forward`, at complete and at
  the Improve import (`finish_improve`). The redone packets print the four revisit lines (`_revisit_lines`).
  Regression: the amended plan's `test_commands` replace the old; earlier steps' cases still run at later steps.
- What does not rerun: spec, test-strategy, plan. The redone step-plan is told so in `_upstream_line`: "Changed
  upstream since your previous step plan: nothing (a send-back reruns no planning stage)".
- Enforced: script.
- Tests: `test/shiploop-send-back.test.py` `test_send_back_returns_the_item_to_step_plan_with_a_fresh_action`,
  `test_earlier_results_of_a_sent_back_item_are_no_longer_current`,
  `test_the_interrupted_step_names_its_own_previous_result_and_a_done_step_is_not_redone`;
  `test/shiploop-step-edges.test.py`
  `test_a_send_back_after_a_committed_step_keeps_it_done_and_the_amended_plan_resumes_at_the_next_step`,
  `test_an_amendment_that_reopens_a_done_step_is_refused`, `test_a_review_of_the_amendment_may_not_reopen_a_done_step`,
  `test_after_an_amendment_the_done_steps_counts_and_cases_still_bind`.

### R7. carry-forward (the coordinator's lead 1, verified)

- Edit by script: any spec edit that keeps every R-n. carry-forward's gates are `_check_skill_decision` (in
  `_inner_gates`), `shiploop_primary.check_queue` (only when it gives `work_items`), the open-item shape
  (`_handoff_gate`), the loop receipt and `_knowledge_gate`; `_step_spec_refusal` is not among them.
- Edit by prompt: duty 1 of `DUTIES["carry-forward"]` writes spec.md: "KNOWLEDGE/spec.md: each R-<n> this item
  satisfied; an open gap under its R-<n>, an unresolved state or data change included ... Keep unaffected clauses,
  and never relax one to fit the code or tests. Test IDs live only in test code: write none here." But
  `STAGE_FILES["carry-forward"]` (`shiploop_knowledge_home.py`) names only architecture.md and environment.md, so
  the packet's own knowledge line ("This stage keeps these up to date", `stage_lines`) leaves spec.md out, and two
  tests pin that row: `test/shiploop-knowledge.test.py` `test_closes_and_stage_files_name_only_living_files` and
  `test_the_stages_that_discover_commands_facts_and_decisions_keep_the_files_up_to_date`. The journal's section 1
  line "`carry-forward` does not write spec.md (`STAGE_FILES`)" needs correcting: its duty does.
- Routing by prompt: a changed requirement is "incompatible with the approved work ... stop the loop and report
  blocked; it is no queue edit" (duty 2, full form; `shiploop_loops.REPEAT["carry-forward"]`; carry-forward.md "Map
  observations to the future queue"). The short duty a one-item, one-step run prints instead
  (`shiploop_prompts._CARRY_FORWARD_ONE_STEP`, chosen by `shiploop_loops.one_step_run`) has no such rule; only the
  loop's repeat rule keeps it.
- What happens to the plan when carry-forward rewords an R-n (lead 1):
  - the knowledge close commits it as `docs(shiploop): record <label> knowledge after carry-forward`;
  - the future queue is kept as it was unless the result gives `work_items`; nothing marks the items whose `follows`
    names the reworded R-n;
  - the next item's step-plan sees its plan-written `context`, the spec's table of contents (headings and IDs, not
    the reworded text) and no spec diff; from test-spec on, the item's packets quote the R-n it `follows` by value
    (`_followed_lines`, read at render), so a later item builds to the new text while its context may describe the old;
  - the completed item's step plan, test spec, code and tests stay as built against the old text; fix forward
    forbids reopening them, and nothing requires a corrective item; its tests stay wherever a later step plan's
    regression command runs them, and a later item that changes that behaviour must retire them in `retired_tests`
    (a reason naming an R-n or AD-n, not checked against the spec; `shiploop_test_loop.check_result_fields`);
  - `primary` and `defaults` stay as the spec result recorded them (`shiploop_primary.primary_ids`,
    `shiploop_defaults.recorded`); `shiploop_defaults.changed` marks a default whose requirement was rewritten in the
    done packet and report, which is the one place ShipLoop already detects a rewrite after the spec;
  - test-strategy's per-requirement map and the plan's concern rows are not revisited; system-test-author reads the
    spec afresh; product-acceptance and release-verify see the change in the spec diff since the run began
    (`CONSUMES`); if this was the last item, the end-of-work review and the outer stages follow and nothing re-plans
    the built work.
- Data (section 7): on ShipLoop 2.4 and later, carry-forward rewrote a requirement line that the plan boundary held
  in 2 of 58 unseeded released-engine deliveries (`~/e2e-runs-sdlc10/20261121-paired/sol-high-due-p2`, R-4 gained
  "The original executable compatibility check is due before local release", a due-stage change; and
  `~/e2e-runs-sdlc12/20261121/sonnet-medium-due`, R-4 and R-7 test-file names), and in 4 of 78 candidate-engine
  deliveries. In the other 7 released-engine deliveries where carry-forward rewrote spec lines, it rewrote only lines
  added after the plan boundary, mostly the steps' marked lines.
- Queue rules (script): `_replace_future_work_items` keeps the completed and current items and refuses a repeated ID;
  `check_queue` keeps every primary requirement in some item's `follows` and every `follows` ID an entry.
- Tests: `test/shiploop-navigator-contract.test.py` `test_carry_forward_replaces_only_future_queue_and_rejects_prior_ids`,
  `test_carry_forward_omission_retains_all_pending_items`; `test/shiploop-callback-contract.test.py`
  `test_a_carry_forward_whose_queue_drops_the_work_item_serving_a_primary_requirement_is_refused`;
  `test/shiploop-handoff.test.py` `test_a_carry_forward_that_replaces_the_queue_keeps_each_primary_requirement_followed`;
  `test/shiploop-test-loop.test.py` `test_a_one_step_one_item_carry_forward_prints_the_short_queue_and_skill_duties`.
  No test pins carry-forward's spec edits either way.

### R8. The end-of-work Improve review

- Edit: any. On import `_knowledge_gate(..., "improve")` refuses only a dropped ID in an edit still uncommitted, and
  every review pass commits its edits through `improve-commit` (`_improve_commit`, which runs no knowledge check). The
  docstring of `shiploop_knowledge_home.check` says so: "an edit a review already committed through improve-commit is
  the baseline". So a review can even drop an R-n.
- Plan: the review may add work items ("If it adds work items, the review moves to the new last item's
  carry-forward", carry-forward.md); a commit that changes code owes a `Regression test:` line
  (`_regression_refusal`).
- Data: of the 6 released-engine deliveries where a plan-boundary requirement line changed, 3 changed it in a commit
  that is no ShipLoop knowledge commit: `~/e2e-runs-sdlc9/20261120/sonnet-high-due-L-2` ("docs(shiploop): spec A8.2
  describes the rollback test that exists", made between the last step commit and the carry-forward knowledge
  commit, so by the end-of-work review), `~/e2e-runs-sdlc10/20261120/grok-46-xhigh-due-1` ("fix(store): treat overdue
  as exact true...", after the last step commit and before the outer stages' commits, so by the same review) and
  `~/e2e-runs-sdlc14/r15c/20261121/sonnet-C-due-2` (a test-fixture commit between system-test-author and
  release-check). The stage of each is read from where the commit sits; no state was read for it.
- Tests: `test/shiploop-actual-improve-cli.test.py`
  `test_a_reviewed_step_plan_that_drops_a_decision_id_is_refused_at_complete_and_the_named_sequence_is_accepted`
  (the uncommitted case); none pins the committed case.

### R9. Outer stages: add-work and the outer send-back

- Edit: any that keeps every R-n (outer `STAGE_FILES` rows name environment.md only).
- add-work: `_apply_result` appends the corrective items (new IDs only), enters the inner loop, and after their
  carry-forward the outer stages run again from system-test-author (`_next_stage`). The items' rows may carry
  `follows` (`_normalise_work_items`), but `ADD_WORK_SHAPE` shows none. When the corrective items changed only
  non-code paths, `_replan_delta_lines` scopes each outer stage to the delta. The spec, test-strategy and the plan's
  concern rows are not touched: an item added after the plan gets no concern rows, and its step plan may map none
  (`shiploop_concerns.owned_rows`, `check_step_plan`).
- Outer send-back: system-test to system-test-author, release-verify to release-plan
  (`shiploop_stage_spec.OUTER_SEND_BACK_TO`); the target reruns with the result as evidence, then every stage after it
  (`_outer_revisit_lines`).
- Enforced: script.
- Tests: `test/shiploop-navigator-contract.test.py`
  `test_outer_add_work_adds_corrective_work_without_rewinding_completed_work`; `test/shiploop-test-loop.test.py`
  `test_outer_stages_after_a_non_code_add_work_are_scoped_to_the_delta`,
  `test_an_inner_stage_never_offers_add_work_and_an_outer_one_still_does`; `test/shiploop-send-back.test.py`
  `test_an_outer_send_back_reruns_the_stage_that_wrote_the_plan_with_a_fresh_action`.

### R10. product-acceptance

- Prompt: "Assess the product against the original outcome, not only the spec" and route missing product work as
  add-work (`DUTIES["product-acceptance"]` items 2 and 6). A missing requirement can only hang off an existing R-n:
  every test case's `requirement` must name an entry the spec holds (`check_test_cases`), and no stage after the
  plan is told to add one.
- Script: an unverified primary outcome needs a passed lower-layer test, else add-work (`check_unverified`); a row
  removed on a revisit needs one `settled` entry with basis `observed` or `user-correction`
  (`shiploop_unverified`, release dbd2a47f3dd52fc939620e6481cc64f486630075 "require explicit settlements before
  recorded outcomes disappear"). A user correction thus changes what the run treats as accepted without touching
  the spec.
- Tests: `test/shiploop-callback-contract.test.py`
  `test_an_unverified_primary_outcome_with_no_passed_test_is_refused_and_the_add_work_it_names_is_accepted`,
  `test_r07_settlement_rejection_table`.

### R11. Owner notes

- Script: `shiploop_owner_notes` shows each undelivered note in the current action's packet, holds a callback once
  for a note not yet shown, and records the note delivered when a step that showed it is accepted (`deliver`). The
  packet footer: "Notes do not change the callback, the result template or ShipLoop's checks" (`FOOTER`). A note
  written while the run is paused or blocked is quoted after resume (`main`).
- Plan: nothing. A note that changes a requirement can be applied only where the current stage's script rules allow a
  spec edit: not in a step (R5), freely at step-plan or carry-forward (R3, R7), and nothing re-plans.
- Candidates, not on main: branch `shiploop-notes-85299a` (f429c90a90b09b85021c91289576aa9103e06f90,
  7516a7ca58c14b6f2697a3b72ccbce6f7de8716c) settles each note by a row in a stage's result, and changes the duties so
  document "carries" a requirement-changing note and carry-forward rewrites the requirement in place and queues the
  work. Its deliveries `~/e2e-runs/r-20261122-5d2cbc/{k1,g2,g3}` (engine 053732c219ae2dbd528ffb6d21428f50ff9b5e31)
  rewrote the requirement at step-plan after a send-back in k1 (Sonnet: R-4, R-5, R-6) and g3 (Sol: R-3), and at
  carry-forward in g2 (Sol: R-2, R-3, a one-item run, so no later item re-planned it).
- Tests: `test/shiploop-owner-notes.test.py`
  `test_a_note_is_quoted_by_the_next_packet_and_delivered_by_the_accepted_step`,
  `test_a_note_written_during_a_step_holds_its_callback_once_and_the_next_packet_quotes_it_again`,
  `test_a_paused_run_takes_a_note_for_the_packet_after_resume`.

### R12. The requester's answer to an open question

- Blocked and resumed: a `blocked` result replaces the action with a fresh one of the same stage (`_apply_result`);
  `control(..., "resume", answer=...)` refuses a bare "continue" (`_NOT_AN_ANSWER`); the rerun's packet quotes the
  reply: "Act on this reply; it is the user's decision, recorded verbatim" (`_answered_lines`). The reply reaches
  only that stage; its own spec rules apply (R3, R5, R7); nothing re-plans.
- Intake's question ledger (`_check_intake_questions`, routes `inspect`, `research`, `experiment`, `default`,
  `person`) is settled in the prelude, before the plan.
- Tests: `test/shiploop-navigator-contract.test.py` `test_incomplete_child_and_blocked_producer_do_not_advance_parent`
  (it resumes at the same stage once its wait is answered).

### R13. The spec's defaults

- Script: the spec result's `defaults` are shown at the test-strategy packet, the done packet and the report
  (`shiploop_defaults.SHOWN_AT`, `done_lines`, `html_section`); nothing asks or waits. The module docstring says what
  this study finds in general: "it gives the requester no way to change a default inside the run. An owner note
  reaches the next packet, but no script route replaces an accepted specification and what was planned from it, so
  the surfaces promise only what holds: a new run on the delivered project." The glossary: "changing one is a new
  run" (`references/glossary.md`, "default").
- Candidate, not on main: branch `shiploop-answers-603aa8` (529b40d97e621834dee2700a48ca136ba0fab0ee) applies an
  answer recorded with `note --default` at the stage after the spec, checked by script, and holds a later answer for a
  new run. Its own record (5841b77ca5d9c513499c8d95efba439543c9d8fe): "seven deliveries whose answer arrived during
  the build all carried on with it held; the one whose plan it contradicted delivered what the requester did not
  want and said so".
- Tests: `test/shiploop-defaults.test.py`
  `test_a_row_is_marked_when_a_later_stage_rewrote_its_requirement_and_not_when_it_added_a_line`,
  `test_the_stage_after_the_spec_prints_the_rows_and_no_other_stage_does`.

### R14. The knowledge closes

- Script: `CLOSES` (prepare: the three files; release-plan and release-verify: environment.md), the dropped-ID refusal
  (`check`), and the commit (`commit`; release-verify's `lessons` become its body, `lessons_body`). Section and
  placement notices are counted, never refusals (`section_notices`, `placement_notices`). No close compares the spec
  with the plan; the spec diff is shown, never gated (`spec_diff`, `_source_lines`).
- Tests: `test/shiploop-knowledge.test.py` `test_a_close_needs_its_files_and_commits_only_the_home`,
  `test_release_verify_commits_the_results_lessons_as_its_message_and_needs_no_outcome_file`,
  `test_a_non_close_stage_that_drops_an_id_is_refused`.

### R15. Pause and resume, halt

`control`: a pause keeps the action pending and refuses housekeeping reasons; resume reactivates the same action;
halt is terminal. Nothing re-plans.

### R16. Open items (the coordinator's lead 2, verified)

- Script: `shiploop_assumptions.open_items` lists open rows of the current results; for any stage but `plan`,
  `_settled` drops a row once the current done result of its due stage (for carry-forward, the same item's) was
  accepted after the row's result, by history order alone. Nothing checks that the due stage resolved the row, mapped
  it to a queue item or even named it; "A due stage with no assumptions field settles by its done result" (the
  docstring). The plan's own open rows never settle ("the ledger never updates a disposition").
- Relevance here: document's duty sends "work outside this item" to an open item due at the item's carry-forward, and
  carry-forward is told to give every observation an owner (prompt). The script lets such a finding, a
  requirement-affecting one included, disappear at carry-forward's done even with `"assumptions": []`.
- Tests that pin it: `test/shiploop-handoff.test.py`
  `test_each_steps_document_keeps_its_open_items_until_its_items_carry_forward` ("The item's carry-forward settles
  both", with `{"assumptions": []}`) and
  `test_open_items_are_filtered_by_consumer_and_settled_by_the_consumers_later_done_result`.

### R17. The opt-in delivery contract: the one script-enforced re-planning after the plan

`shiploop_consumer_delivery.project` sets `replan_required` (`_REPLAN_MESSAGE`) when a contract correction accepted
after release-plan is material (`_material_post_plan_change`); `validate_transition` then refuses done at the
release-gated stages, and the barrier clears only after an add-work, a fresh system-test and a fresh release-plan. A
correction that narrows the user's scope needs a user-approved correction source (`_requires_user_correction`).
Tests: `test/shiploop-consumer-delivery.test.py`
`test_v3_add_work_clears_post_plan_requirement_only_after_fresh_tests_and_plan`,
`test_v3_add_work_without_immediate_contract_change_starts_a_fresh_plan_cycle`,
`test_v3_operations_contract_change_requires_add_work_after_release_plan`. It covers the delivery ledger, not the
living spec, and only runs that opt in.

### R18. follow_on

The handoff's recommend-only list (`shiploop_follow_on`): a `gap` or `decision` makes ShipLoop write
`RUN/follow-on-request.md` and print the command for a new run (`references/navigator.md`). This is the documented
route for a requirement change after delivery.

## 3. The gaps

G1. **No script route re-enters planning after prepare.** A send-back reruns no planning stage (`_upstream_line`);
reconcile is refused after prepare (`_reconciliation_permitted`); the plan's queue cannot be replaced after work
starts (`_replace_plan_work_items`: "plan work items can only be replaced before execution"); add-work only appends.
`shiploop_defaults` states the consequence in its docstring (R13). Every route R2 to R16 that can change the spec
leaves the plan as it was.

G2. **carry-forward can rewrite any requirement and nothing re-plans what it affects** (R7). Its duty tells it to
write spec.md, its `STAGE_FILES` row and packet line say it does not, and no script rule limits the edit beyond the
ID check. Released-engine data: 2 of 58 deliveries changed a plan-boundary requirement line there, one of them the due
stage of a check.

G3. **The send-back route for a changed requirement ends at a stage forbidden to change it.** `step_spec_refusal`'s
docstring says a requirement change "is the step plan's to decide: the refusal names send-back", and the refusal
says "to change a requirement, report send-back naming it". The step plan that receives it is told "write nothing
else in KNOWLEDGE/" (duty 10) and that "a send-back reruns no planning stage" (`_upstream_line`), while the script
lets it edit the spec (R3) and its `follows` refusal invites a new entry. The model follows the script, not the
duty: on the notes candidate, step-plan rewrote R-n in 2 of 3 deliveries (R11).

G4. **The same finding is routed two ways, and the 2026-11-12 alignment never happened.** A requirement whose intent
moved:

| Where | Route | Source |
|---|---|---|
| document | send-back to step-plan (no person) | `DUTIES["document"]` item 3 |
| implement | send-back when the step contradicts a requirement | `shiploop_loops.REPEAT_STEP`, `DUTIES["implement"]` item 6 |
| any step's spec edit | send-back | `step_spec_refusal` |
| carry-forward (full duty), its loop rule | blocked (the person) | `DUTIES["carry-forward"]` item 2, `REPEAT["carry-forward"]` |
| carry-forward (one item, one step) | no rule in the duty | `_CARRY_FORWARD_ONE_STEP` |
| carry-forward.md | blocked or pause; also lists a changed "completed-work assumption" | "Map observations to the future queue" |
| research-loop.md | pause or blocked, "completed-work assumption" included | the discovery-location table |
| behavioral-requirements.md | "stop and seek direction, not a silent spec edit" | the stage table and the paragraph after it |

A changed completed-work assumption is likewise split: blocked in carry-forward.md's incompatible findings and in
research-loop.md, but a corrective item in carry-forward's duty 2 ("a completed prerequisite new evidence
invalidates: a corrective item with revalidation") and in carry-forward.md's own later paragraph. The review of
2026-11-12 (`docs/experiments/step-boundary-replan-20261112/README.md` E6; `astra-fix-forward.md`, after rule 6) asked
to "Distinguish a defect violating an unchanged requirement, which can be corrected, from a change to the requirement
or authority itself." It was never done on main: carry-forward.md last changed 2026-10-29
(9147dcca8e260a8fcf03712b5594f16ea702025a); `git log -S` finds document's sentence only at its introduction
(7bba525ed74ad436ddbbe526db029714fdec47cb, 2026-10-28), carry-forward's "incompatible with the approved work" only
at 153139f173e57fe8838899dc534b8ca3cc2f2c2d (2026-10-11), and "completed-work assumption" only at
0591ce027906a5a84e76d007e8a178d638844ebf (2026-09-11). Only the notes candidate (7516a7ca, not on main) edits these
sentences, and it adds an owner-note exception to each while leaving the two base routes different.

G5. **Reviews can change the spec unchecked** (R8). Any Improve review edits with only the ID check, and its own
commits are the baseline for that check. 3 of the 6 released-engine deliveries in which a plan-boundary requirement
line changed made the change in such a commit, and at least one made the spec describe what was built ("spec A8.2
describes the rollback test that exists"), the opposite of carry-forward's "never relax one to fit the code or tests".

G6. **Outer stages add work but never requirements** (R9, R10). A missing requirement found at product-acceptance
becomes a corrective item whose cases must cite an existing R-n; the spec, the test strategy and the concern map are
not revisited, and the corrective item gets no concern rows.

G7. **Notes and answers have no route** (R11, R12, R13). A note or reply that changes a requirement reaches only the
stage that is current; the stage's own rules then decide whether the spec can change (no in a step, yes at step-plan
and carry-forward) and nothing re-plans.

G8. **A finding can be settled by order alone** (R16). The unverified ledger was fixed to need explicit settlement
rows on 2026-11-15 (dbd2a47f); the open-item ledger was not, so a requirement-affecting finding recorded as an open
item due at carry-forward needs no queue entry.

G9. **The next item cannot see the change.** step-plan gets the spec by table of contents only and no spec diff
(`READS`, `CONSUMES`); its `context` was written by the plan. The platform-knowledge study found that a page only
named reached 0 of 3 products while an entry the script hands over by value reached 6 of 6
(`docs/platform-knowledge-journal.md`, cited in the journal's section 2).

## 4. The smallest change that makes the rule true by script

The rule, made checkable: every requirement changed after the plan is routed, by script, to the planning step that
owns what it affects, and that step receives the change by value.

### 4.1 What to build (a gate, a line, and one wording)

1. **The plan baseline (script).** When the plan is accepted (`_apply_result` at `stage == "plan"`, beside
   `_planning_sources_current`), write `RUN/plan-spec.json`: the R-n entries `knowledge.entries(repo, "spec.md")`
   returns, as text and retired flag. This is the pattern of `knowledge.record_baseline` (`RUN_BASELINE`,
   `RUN_STARTING_KNOWLEDGE`). A reconcile that reruns the plan writes it again. (`knowledge.entries_after(state,
   "plan", ...)` would need no file but returns None when the plan changed nothing in the home.)
2. **The changed set (script).** An R-n is changed when a line its baseline entry held is no longer in its entry,
   or it is new, or newly retired: the rule `shiploop_defaults.changed` already applies against the spec stage's
   commit, rebased onto the plan baseline. Lines added after the plan, the steps' marked lines included, may be
   rewritten or removed without counting. On the saved deliveries the rule fires at carry-forward in only 2 of the 9
   released-engine runs whose carry-forward rewrote spec lines (section 7).
3. **The gate (script).** In `_evaluate` beside `_check_submitted_primary`, and on the Improve import beside
   `_knowledge_gate`: a done result after the plan that leaves a changed R-n no earlier accepted result routed with
   the same entry text must carry one row per such R-n,
   `requirement_changes: [{"requirement": "R-<n>", "route": "<work item id>" | "none", "reason": "..."}]`:
   - `route` names a work item that is not completed in the queue the result leaves (`primary.queue_after`) and whose
     `follows` names the R-n (`primary.followers`): that item's step plan re-plans it. At step-plan the current item
     qualifies when the step plan's own `follows` names it; at carry-forward a new corrective item qualifies; at an
     outer stage the result's add-work item; at test-spec through document only a send-back (the current item's step
     plan reruns);
   - `route: "none"` with a reason when no planned or built work depends on the change (a wording or file-name
     correction).
   The refusal names both exits, as `check_queue`'s does. This is `check_queue` with "changed" in place of
   "primary".
4. **The hand-over (script-placed).** The step-plan packet of a routed item, and of any pending item whose `follows`
   names a changed R-n, prints the entry's change since the plan by value, one line per R-n ("Changed since the
   plan: R-3, at W1 carry-forward: ..."): a new `CONSUMES["step-plan"]` source next to `assumptions`.
5. **One wording (prompt), written once.** One sentence for a changed requirement, kept as one constant (as
   `shiploop_stage_spec.STUCK_FIX` is) and printed by document, both carry-forward duties,
   `REPEAT["carry-forward"]`, step-plan's duty 10 and `step_spec_refusal`'s refusal, with carry-forward.md,
   research-loop.md and behavioral-requirements.md saying the same. Its content is the 2026-11-12 distinction: a
   defect against an unchanged requirement is fixed in the item or by a corrective item; a change to the requirement
   itself needs the person's word (an owner note or a blocked answer), and the stage that holds it rewrites the R-n
   in place and routes it (item 3). `STAGE_FILES["carry-forward"]` gains spec.md, since the duty writes it. This
   closes G3 and G4.

Unchanged: `_step_spec_refusal` (a step still never rewrites a requirement), fix forward (a change to done work is a
new step with new criterion IDs), the queue rules, and the outer graph.

### 4.2 What it costs a normal delivery

- **How often it fires** (`gate_firing_estimate.txt`): in 6 of 58 unseeded released-engine deliveries of ShipLoop 2.4
  and later (cases ticket-due-times 37, shared-expenses 14, hello 5, ticket-assignment 2; Codex 39, Claude 18, Grok
  1). First change by stage: carry-forward 2, a review or other commit 3, handoff 1. In 52 of 58 it costs only a file
  read and a parse at each done. In the 78 candidate-engine deliveries it fires in 9, 5 of them deliveries built to
  send a late owner note or answer (the notes and answers branches).
- **Per firing**: one route row, or one refused callback when the row is missing. Reading the six diffs, four are
  cosmetic and would get `none` (test-file names in sonnet-medium-due, a fixture path in sonnet-C-due-2, status lines
  rewritten as "Satisfied:" in grok-46-xhigh-due-1, evidence wording in sonnet-high-due-S-1); two touch the plan (a
  check's due stage in sol-high-due-p2; a check's method in sonnet-high-due-L-2).
- **Packet**: one line, only in an affected item's step-plan packet.
- **Code**: one small module (the baseline, the changed set, the gate), the result key, a `CONSUMES` source, the
  wording constant, and tests (a fail-first test for each route of section 1 that can change the spec).

### 4.3 What could break

- **Spec growth from hindsight.** A gate that accepts a routed change makes mid-run spec edits legitimate, and the
  owner's end-of-loop stage would make more of them. The Ratchet pilot measured where model-written requirements
  lead: blind judges accepted 10 of 59 closing-look additions, 6 of 9 tested additions failed on a correct
  reference, and one invented requirement rewrote 21 earlier tests (`docs/ratchet-pilot-journal.md` section 0). Here
  3 of 6 firings were model-made review edits. The guard on offer: a route row also names its authority (an owner
  note `N<k>` or the action of a blocked answer), and a requirement rewrite without one is refused (restore the line
  or report blocked). It would have cost a refusal, and sometimes a question to the person, in all 6 of the 58
  released-engine firings, 4 of them cosmetic: offer it as the option, not the default (KISS rule of 2026-11-21).
- **More send-backs.** None by itself: the inner exits already exist and fire today through `step_spec_refusal`; the
  gate adds a row only where a requirement changed.
- **A rubber-stamped `none`.** The script can enforce that every change is routed, not that the route is right.
- **`follows` granularity.** An item affected by a requirement it does not list escapes, as it does for
  `check_queue` today.
- **Fix forward friction.** A change that invalidates a done step's case cannot edit that case
  (`_frozen_case_refusal`); the routed plan adds a step with new criterion IDs, and a superseded test is retired
  through `retired_tests`, whose reason is not checked against the change.
- **The test strategy is still not rerun.** The routed item's step plan and test spec re-plan the changed
  requirement's checks, and system-test-author reads the spec afresh after the inner loop; a change accepted after
  system-test-author routes through add-work, which reruns the outer stages from there, the same shape as R17's
  barrier.
- **Two candidates touch the same texts** (the notes and answers branches). The wording of item 5 must be written once
  with them; the notes candidate's own lesson (7516a7ca): "A new rule for a stage has to be written into every
  standing text that states the stage's duty, or the older sentence stands beside it."

### 4.4 The simpler alternative, and the recommendation

The alternative is to freeze the contract after the plan: apply the add-only rule of `step_spec_refusal` to every
stage after the plan, measured against the plan baseline (so a step's and carry-forward's own added lines stay
editable), and send every requirement change to `blocked` and a follow-on run. The rule then holds because the spec
never changes in a run. It needs the same baseline and no routing field, matches the defaults module's "a new run on
the delivered project", and would refuse the 6 of 58 firings above instead of asking for a row. It contradicts the
owner's proposed stage, whose point is to update the spec in the run.

Recommendation: decide the owner's stage first. If the run may update its spec (the owner's stage, or owner notes
that change requirements), build 4.1 items 1 to 5 with the authority guard as an option; if not, build the freeze.
Either way align the wording now (item 5's distinction, ending in whichever route the chosen variant takes) and fix
`STAGE_FILES["carry-forward"]`: G3 and G4 exist on main today, whatever is decided about the stage.

The deciding evidence, cheapest first. The offline replay of the changed-set rule is done here
(`gate_firing_estimate.txt`): it fires in 6 of 58 released-engine deliveries, 4 of them cosmetic, so its cost is
known. What is not known is whether routing changes what gets delivered. The cheapest look at that is already on disk:
the notes candidate's late-note deliveries (`~/e2e-runs/r-20261122-5d2cbc/`; each has a `result.json`, owned by the
session running that candidate; this study read only their spec commits). If the deliveries whose requirement
changed at the last carry-forward (the g2 shape: no item left to re-plan) delivered the new requirement anyway, the
gate buys little; if they did not, that is the measured case for it. Only then one live rung on the latest Sonnet and
Sol: a late owner note that changes a requirement at the last item, with the gate. The decision it informs: build the
gate or not.

## 5. Learnings and what was unexpected

1. The spec is already mutable after the plan almost everywhere; only a step is held to add-only lines. "A step may
   add only marked lines" is true; "the spec is fixed after the plan" is not.
2. carry-forward's duty writes spec.md while its `STAGE_FILES` row, its packet line, two tests and the journal's
   section 1 say it does not.
3. The script's own refusal texts invite a new R-n at step-plan and carry-forward ("or add its entry to the living
   file", "or write the entry first"), against step-plan's duty.
4. The model applies a requirement change at the first stage the script lets edit the spec: on the notes candidate
   that was step-plan after a send-back (k1, g3), not the stage the duties name.
5. Post-plan spec edits are common, but nearly all are traceability: carry-forward rewrote spec lines in 9 of 58
   released-engine deliveries, mostly lines a step had added; in the samples read it reworded "Met by" lines and took
   test IDs out, as its "Test IDs live only in test code: write none here" asks of lines document had written with
   IDs. A plan-boundary line changed in 6 of 58; no requirement was added after the plan in any of the 136
   deliveries of 2.4 and later (10 of 506 of every version).
6. The "a consolidated spec that drops an earlier R-n is refused" rule holds only for uncommitted edits: a review's
   `improve-commit` makes its edit the baseline (`shiploop_knowledge_home.check` docstring).
7. Two ledgers, two settlement rules: unverified outcomes need an explicit settled row (2026-11-15); open items settle
   by order. Plan rows go the other way and never settle.
8. `primary` and `defaults` are frozen at the spec result, so a requirement added after the plan can never become
   primary and is never covered by `check_queue`; `shiploop_defaults.changed` is the one existing detector of a
   rewrite and is the building block for 4.1 item 2.
9. ShipLoop already has the pattern the owner asks for, in the opt-in delivery contract (R17): a material change
   after planning raises a barrier that only a fresh add-work, system-test and release-plan clear.
10. A run of one item and one step (one step is the default since ShipLoop 2.4.0) prints the carry-forward duty
    without its changed-requirement rule; only the loop's repeat rule keeps it.

## 6. Unknowns

- Whether the six released-engine rewrites changed what the product should do: read from the diffs, two touch a
  check's due stage or method and four are wording, paths or status lines; no product was re-graded.
- How the candidates' deliveries ended (k1, g2, g3, m1): this study read only their spec commits.
- Whether an Improve review that commits a dropped R-n has happened in a saved run: the scans looked at changed lines,
  not dropped IDs in review commits.
- How often a requirement-affecting finding was recorded as an open item due at carry-forward and then settled by
  order alone: not counted.
- Whether every delivery read as released-engine ran exactly main's code: a checkout run counts as main when its
  recorded `local_head` is on main; uncommitted local edits at launch would not show.

## 7. Evidence in this folder

| File | What it is |
|---|---|
| `scan_spec_after_plan.py`, `.json`, `.txt` | every saved delivery with a `work/` checkout (1,358; 506 with a plan or prepare knowledge commit); each spec.md commit after the plan boundary, its stage (from the commit subject), lines added and removed, new R-n |
| `classify_removed_lines.py`, `.txt` | ShipLoop 2.4 and later: each removed spec line sorted as traceability (starts with Met, Observed, Implemented, Pending and the like, or ends with a step mark), heading or other, with every non-traceability line printed |
| `engine_split.py`, `.txt` | the same runs split by engine: released (a plugin install, or a checkout whose `local_head` is on main) or candidate |
| `gate_firing_estimate.py`, `.json`, `.txt` | the 4.1 rule replayed per delivery: for each R-n, the first post-plan commit and stage at which a plan-boundary line left its entry |

Limits of the scans: the boundary is the last `knowledge (at|after) plan` commit, else the prepare commit; a stage is
read from ShipLoop's commit subject, so a review's or an outer stage's own commit reads as `other`; the traceability
classifier is a heuristic; the delivery set is the owner's E2E corpus, mostly the ticket-due-times case.
