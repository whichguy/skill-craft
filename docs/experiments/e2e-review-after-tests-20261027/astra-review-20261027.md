# Astra review of design T §8, 2026-10-27

Model `gpt-6-astra`, persona `codex-astra`, effort `max`, sandbox `read-only`, fallback `False`, exit `0`. Reviewed main at 10e4f21d (checkout HEAD c59c4809, a docs-only commit).

## The question as sent

```text
Use max effort. This is a deep design review; the owner wants the strongest reasoning.

Review a design for the ShipLoop skill in the repository /Users/dadleet/src/skill-craft (main at 10e4f21d). Read-only: do not edit, commit or run anything that writes.

DESIGN TO REVIEW: docs/shiploop-review-after-tests-design-2026-10-27.md, section 8 (the current proposal). Each work item is planned once (step-plan; a test-spec that assigns every case to a step; validate-existing). Then, for each planned step in order: build → test → document → Improve (review) → knowledge → commit. Carry-forward follows the last step. Within §8:
- §8.2: the gates of each stage;
- §8.2a: where the linters run;
- §8.2b: the knowledge stage, which updates spec, architecture and environment, and makes the reusable-skill decision for every step;
- §8.2c: skills in every stage packet;
- §8.3: what changes from today;
- §8.4: cost;
- §8.5: decisions F1 to F9.
Background:
- §7 dissolves the verify stage into tests and gates.
- §1 to §6 cover running Improve after the tests.
- docs/shiploop-measured-width-design-2026-10-27.md is superseded, but holds measured per-step changes.
- Evidence is in docs/experiments/e2e-review-after-tests-20261027/ and docs/experiments/e2e-measured-width-20261027/.

CODE THE DESIGN WOULD CHANGE (read it to check feasibility):
- skills/shiploop/scripts/shiploop_stage_spec.py: the INNER stage rows and IMPROVE_RULES.
- skills/shiploop/scripts/shiploop_navigator.py: _improve_checkpoint, apply, finish_improve, validate (the active_improve binding rules), _step_entry, _step_after, _step_commit, _item_commit, step_view.
- skills/shiploop/scripts/shiploop_test_loop.py: base_check, loop_run, floors.
- skills/shiploop/scripts/shiploop_mutation.py.
- skills/shiploop/scripts/shiploop_lint.py: the item base.
- skills/shiploop/scripts/shiploop_item_scope.py: commit_scope, commit_item.
- skills/shiploop/scripts/shiploop_prompts.py: the stage packet text.
- skills/improve/references/shiploop-route.md: Improve's commit rule.

OWNER INTENT (verbatim quotes are listed at the top of §8):
- one step at a time (build, test, document, review, record knowledge, commit), not one monolithic build of all the steps;
- script gates decide when each stage exits;
- optimistic: a stage passes once unless a gate refuses;
- linters run on the production code after build and on the test code after the test stage;
- mocks simulate the expected behaviour before the system tests;
- one commit per iteration, made by a stage named for committing, not "verify".

QUESTIONS:
1. Do the stage order and the gate placement hold together? Find contradictions between §8 and the code it must change. Examples to check:
   - one Improve child per producer action;
   - what triggers the item commit;
   - carry-forward reading item:verify;
   - the base, floor and RED semantics of the test loop, scoped per step;
   - mutation scope per step;
   - the lint base per step;
   - Improve's own commit rule.
2. What breaks or gets weaker compared with today? Cover:
   - send-back routes and reconciliation;
   - the ask-agent route;
   - the outer stages that read item results;
   - packet-count tests;
   - Run Review.
   Name the symbol for each.
3. Can a script check every gate? Look in particular at:
   - the entry-point map against the change inventory;
   - the knowledge-stage gates;
   - the skill decision rule;
   - the commit stage's tree match.
   Where is a gate really a model judgement in disguise?
4. Cost. Each step gets its own test, document, Improve and knowledge stage. Is the §8.4 forecast credible? What is the cheapest shape that keeps the owner's order?
5. What is missing? For example:
   - a test case that spans steps;
   - a step whose tests need a later step;
   - a step that changes no code;
   - a send-back or rerun in the middle of an iteration;
   - how the outer system-test stage interacts with the mocks.

OUTPUT:
- A verdict: sound, sound with changes, or unsound.
- Then findings ranked by severity. Give each:
  - the claim;
  - the evidence (file:symbol or doc section);
  - the consequence;
  - the smallest fix.
- Mark anything you could not verify.
- Keep it under about 1,500 words.
```

## The answer, verbatim

**Verdict: sound with changes.** The order is coherent; the proposal needs stronger contracts for iteration identity, final verification, and evidence retention.

**1. Goal**

Complete each planned step through build → test → document → Improve → knowledge → one commit before starting the next step.

**2. Material issues**

1. **P1 — Knowledge breaks the final verification boundary.** §8.3 calls Improve the last edit, but §8.2b subsequently permits requirement changes and new skills, potentially including executable scripts. Commit’s tree comparison proves only that nothing changed after knowledge’s gate; that gate checks neither product correctness nor skill execution. Today, `knowledge_home.step_spec_refusal` requires send-back for requirement changes during implementation.  
   **Smallest fix:** distinguish record-only knowledge edits from changes requiring renewed verification. Changed intent must reopen affected planning/tests; executable additions must pass applicable checks/review before commit. Bind evidence to the final authorized candidate. [step_spec_refusal](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_knowledge_home.py:593)

2. **P1 — A step currently advances at build acceptance.** `implement_progress`, `_apply_result`, and `step_view` count accepted implement actions; after S1 build they identify S2. `_step_entry`/`_step_after` attach snapshots to the build action. Meanwhile, `validate`, `apply`, and `finish_improve` bind one child to one current producer. Moving an `IMPROVE_RULES` entry alone cannot implement §8. Ask-agent also still builds every step in one action.  
   **Smallest fix:** retain `(item, plan revision, step, base)` throughout the iteration and advance only after commit. Bind Improve to document’s producer; route an omitted document’s synthetic result through the same checkpoint. Give ask-agent the same step boundaries. [implement_progress](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2690), [_document_entry](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:4306)

3. **P1 — Commit must become a recoverable gate.** `_item_commit` fires on accepted `verify`; `_step_commit` and `_item_commit` run after state saving and tolerate failures. `_knowledge_close` and `_skill_commit` are additional commit owners omitted from §8.3’s list. `commit_scope` can leave undeclared skill scripts behind. Thus the next step could start without the promised commit—or after several commits.  
   **Smallest fix:** suppress auxiliary commits during an iteration; explicitly propagate Improve’s supported `--no-commit` through both pass and completion. Persist a pending commit operation, verify its parent and scoped tree, recover idempotently, and advance only on success. Include skill scripts while preserving exclusions. [_item_commit](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2901), [commit_scope](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_item_scope.py:220)

4. **P1 — Case-to-step assignment is insufficient for RED/GREEN.** `stage_commands` returns item-wide commands; `new_ids` treats every focused ID as new. S1 would require future cases, while S2’s base check would reject already-green S1 cases. `accepted_counts`/`floors` correctly retain earlier counts, but key them by command text and reset after replanning. Baseline callers still use the item/preparatory base.  
   **Smallest fix:** define command activation, cumulative GREEN obligations, and current-step RED obligations separately; thread the immutable iteration base through `base_check`, mutation, lint, and manual/check-only routes. Preserve justified `red_na`: characterization and test-only steps need not fail against their baseline. A spanning case becomes due at its last dependency; earlier steps need independently runnable proofs. Register review-added test identities too: `_test_rerun_gate` cannot detect a new test excluded by an old filter. [stage_commands/new_ids](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:329), [floors](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:930)

5. **P1 — Send-back and no-change semantics are underspecified.** `_apply_result` preserves dirty edits on send-back, while a new step-plan resets progress. Recapturing those edits as a new base can make unfinished work appear unchanged. P4 currently skips Improve, not every subsequent stage. `stage_spec._finish` also hardcodes `verify` as the send-back range endpoint; `_reconciliation_permitted` handles initial-plan recovery only.  
   **Smallest fix:** specify which base survives, which receipts become invalid, and how retained edits are revalidated. Preserve normal send-back independently of stopped-Improve reconciliation. Skip stages only when their obligations are already satisfied—not merely because build edited nothing. [_apply_result](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3785), [_finish](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_stage_spec.py:648)

6. **P1 — Earlier steps’ evidence and obligations can disappear.** `planning_revision.current_actions` retains only the latest `(item, stage)` result. Consequently, `_ITEM_RECORDS` gives system-test-author only the last test result; `assumptions.open_items` can lose S1’s pending real-boundary obligation when S2 records none. Carry-forward still reads `item:verify`. Removing verify also requires relocating `SELECTED_CASE_RECONCILIATION`, including required surfaces and due phases.  
   **Smallest fix:** provide one authoritative, revision-aware aggregation of step receipts and unresolved obligations. Map each mock to a retained real system case and owner. Preserve the distinction between simulated and observed behavior; allow reuse/N/A instead of requiring a fresh mock for every internal call. [open_items](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_assumptions.py:183), [_ITEM_RECORDS](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:6595)

7. **P2 — Several “script gates” remain model judgments.** `lint.inventory_writes` inventories files, not public entry points. Scripts cannot infer complete entry-point coverage from that inventory, or establish that three named tests represent valid/boundary/invalid behavior. Likewise, file changes and source IDs cannot prove knowledge accuracy or distinguish clarification from changed intent. `_check_skill_decision` currently accepts nonempty evidence strings, without proving repetition.  
   **Smallest fix:** enforce structure, real references, distinct executed subcases, unique AD definitions, and actual referenced step counts. Explicitly assign completeness, relevance, intent classification, and procedural equivalence to Improve/model review. Avoid promising semantic proof from receipt validation. [inventory_writes](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_lint.py:2576), [_check_skill_decision](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:4384)

8. **P2 — Run Review needs more than a catalog refresh.** `export.stage_model` maps every version ≥5 to today’s model; `work_items` treats entering test before all builds finish as malformed. Only implement receives step attribution. Packet expectations also change: `SMALL_HOME_FINGERPRINTS` and e2e-efficiency’s 32-packet assertion.  
   **Smallest fix:** version the new lifecycle, preserve historical rendering, and attribute every iteration action to its step. Update exporter, template `stageFlow`, and `metrics.skipped_gates`; establish correct lifecycle fixtures before repinning packet counts. Explicitly choose fresh-run-only support or migration for existing navigator states. [stage_model](/Users/dadleet/src/skill-craft/skills/shiploop-run-review/scripts/export.py:145), [work_items](/Users/dadleet/src/skill-craft/skills/shiploop-run-review/scripts/export.py:2600)

9. **P2 — §8.4 supports review timings, not a total-cost forecast.** It omits per-step knowledge overhead and compares different realized plans. Against its one-review-per-item baseline, three fully applicable steps increase from **7 to 15 model actions**, excluding unchanged planning/carry-forward. Repeated cumulative suites add further cost. The stage table explicitly says Improve overlap is unknown.  
   **Smallest fix:** present this as a quality/feedback-speed pilot. The cheapest faithful shape keeps the order, shares harnesses, emits compact step-specific packets and knowledge deltas, reuses valid unchanged receipts, and makes commit entirely scripted. Measure nonoverlapping model/tool time and packet volume. [cost evidence](/Users/dadleet/src/skill-craft/docs/experiments/e2e-review-after-tests-20261027/stage-minutes.txt:1)

**3. Minor nits**

- State lint’s actual limits: `_lint_gate` permits `off`; `lint.gate` accepts unavailable tools/timeouts. Coverage reporting should expose these.
- `mutation_check` retains a hard zero-kill rule for local samples; dispositions do not override it. Distinguish accepted skips from successful mutation checks.
- F9 says every model stage but omits knowledge, which may author skills.

**4. Open unknowns**

Relevant inspected files match `10e4f21d`, despite checkout HEAD being `c59c4809`. This was source inspection only: no edits or tests. Checked-in timings were verified, not live reruns. Net cost, mock fidelity, and whether the relocated review catches verify’s historical defects remain unproven.

**5. If I were implementing tomorrow**

1. Specify iteration identity, producer ownership, retry invalidation, and final-tree commit invariants.
2. Implement one two-step lifecycle, including omitted document and ask-agent.
3. Add due-case projection, cumulative floors, shared baselines, and obligation aggregation.
4. Exercise send-back, commit failure/retry, test-only steps, cross-step cases, and review-added tests.
5. Update packets and historical Run Review compatibility; then run the two proposed pilots with stage-level defect and cost attribution.
