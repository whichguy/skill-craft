# Current improvement-plan code map

Current source: fetched main `e707b794de0a0bd802988ca68dac8e29ac0b3315`. Earlier map: main `17ddec369f49383f9436ea4f2c6fba7c0c54f643`. Exact excerpts carry snippet hashes; the JSON map also retains full source-file hashes.

Each status describes source implementation. Tests and live qualification are separate. Superseded means a later recorded owner decision replaced the earlier design; it does not mean the user-facing requirement disappeared.

## Recommendation status

### R01 — Step-specific executable checks

**implemented · retain**. Inline steps require proof; complete runs it and binds the receipt to the step, action, command and candidate tree. Step paths are optional. The whole-plan ask-agent route intentionally keeps item-wide checks.

Remaining: Retain the mechanism. Qualify whether each command actually proves its assigned behavior; do not add a per-step gate to the whole-plan route.

Code: [shiploop_prompts.py — DUTIES[step-plan]: proof and criterion confirmation](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1761); [shiploop_navigator.py — _check_step_sizing](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:13); [shiploop_stage_spec.py — Stage(implement): step-proof completion gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1817); [shiploop_test_loop.py — step_command](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:262); [shiploop_test_loop.py — step_proof](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:60); [shiploop_navigator.py — _step_proof_gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:141); [shiploop-test-loop.test.py — test_implement_done_is_refused_while_the_step_proof_fails_and_accepted_once_it_passes](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3090); [shiploop-test-loop.test.py — test_an_ask_agent_implement_action_runs_no_step_proof](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3193).

Qualification IDs: T1, T2, T5, T6, T27, T31, T36.

### R02 — One assignment on every surface

**implemented · retain**. Head, full packet and Improve use the shared Step block and the retained step-entry review base.

Remaining: Retain the shared assignment. Test emitted surfaces under current bounds; do not restore the older full printed loop argument.

Code: [shiploop_navigator.py — step_block](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:284); [shiploop_navigator.py — packet_head](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:333); [shiploop_navigator.py — _producer_blocks](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:354); [shiploop_navigator.py — improve_handoff_text](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:468); [shiploop_navigator.py — _review_base_line](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:530); [shiploop_loops.py — invoke_lines](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1580); [shiploop_navigator.py — PRINT_LIMIT, HEAD_LIMIT and HEAD_REQUIRED_END](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2664).

Qualification IDs: T8, T9, T10, T11, T12, T16, T18, T19.

### R03 — Criterion evidence and changed-candidate proof

**superseded · retain**. Candidate-bound step Proof and re-proof after Improve are implemented. The later owner-selected lean port explicitly omits per-step criterion_evidence fields and their gate.

Remaining: Keep re-proof and existing observations/notes. Retire the proposed evidence-row schema; acceptance correctness is still required without adding that form.

Code: [shiploop_navigator.py — _improve_change_gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:177); [shiploop_test_loop.py — step_proof](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:60); [shiploop-test-loop.test.py — test_a_review_that_breaks_the_proof_is_refused_at_import_and_an_unchanged_candidate_reuses_its_record](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3124); [shiploop-template-build-plan-2026-10-18.md — Owner-selected lean port and follow-up commits](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2477); [implement-guidance.md — Considerations and Evidence](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2595).

Qualification IDs: T7, T17, T26, T27, T33.

### R04 — Static method, cards, match and Code craft

**partial · retain / P3 wording review**. The eight considerations are a static referenced guide. CODE_CRAFT has fourteen rules, with compact producer guidance and full review focus; the lean port selected no extra per-step assessment fields.

Remaining: Preserve the lean guide and retire the superseded assessment forms/extraction. Earlier CC3 complex-unit, CC6 resource-release and CC9 composable-unit expansions remain absent. The lean-port decision does not explicitly resolve these three; retain them as low-priority wording proposals, not implemented changes.

Code: [implement-guidance.md — Considerations and Evidence](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2595); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649); [shiploop_prompts.py — CODE_CRAFT: fourteen rules](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1862); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926); [shiploop-template-build-plan-2026-10-18.md — Owner-selected lean port and follow-up commits](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2477).

Qualification IDs: T3, T4, T13, T15, T20, T21, T22, T23, T24.

### R05 — Valid procedures through final review and person ask

**partial · P1 qualification**. Shared procedure-walk guidance exists at planning/originating stages. The final code-review focus still has no explicit inherited-procedure walk.

Remaining: Extend only the missing inherited review/person boundary after a fixture shows where an invalid carried procedure survives. Keep valid setup and actual observation separate.

Code: [shiploop_prompts.py — PROCEDURE_WALK and planning review focus](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1987); [shiploop_prompts.py — END_REVIEW_FOCUS_HEAD](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2011); [shiploop_prompts.py — DUTIES[release-verify]: unresolved consumer observations](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2056); [shiploop_expectations.py — normalise_test_cases](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1036); [shiploop_expectations.py — check_test_cases](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1078).

Qualification IDs: T25, T26, T29, T34.

### R06 — Early actor/access prerequisites

**implemented · retain**. Prepare names the intended account/role, entry route and prerequisites, probes read-only, and records unresolved owners. Test layers and target/harness contracts add early setup gates.

Remaining: Retain early checks and qualify actor/entry evidence on the actual target. No new permission mechanism is needed.

Code: [shiploop_prompts.py — DUTIES[prepare]: consumer access and tool state](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2030); [shiploop_test_layers.py — test_layers, targets and criterion confirm contract](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2246); [shiploop_navigator.py — _check_submitted_layers](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:975).

Qualification IDs: T28, T29, T44.

### R07 — Required acceptance and partial/declined replies

**partial · P1 qualification**. Person-reply guidance and required delivery gates exist. Primary unverified outcomes now require a passed lower-layer case through an actual validator; this does not certify the user-visible outcome.

Remaining: Prove requirement-to-case-to-obligation continuity across partial replies, stage changes and omitted obligations. A required consumer observation must remain open; add enforcement only for a reproduced omission.

Code: [shiploop_prompts.py — DUTIES[release-verify]: unresolved consumer observations](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2056); [shiploop_consumer_delivery.py — validate_transition](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1140); [shiploop_consumer_delivery.py — validate_terminal](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1177); [shiploop_primary.py — check_unverified](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1269); [shiploop_primary.py — _passed_ids](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1310); [shiploop_expectations.py — normalise_test_cases](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1036); [shiploop-consumer-delivery.test.py — test_a_partial_person_reply_closes_no_required_behavior_and_the_ask_again_it_names_is_accepted](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3212).

Qualification IDs: T26, T44.

### R08 — Observe the intended copy and reporter outcomes

**outstanding · P1 fix**. Per-command targets, remote exclusions and reporter guidance have improved. Candidate judge still accepts exit zero despite a recognized failed test tally and failed named outcome; the direct helper probe reproduces this.

Remaining: Reject recognized failed/error/cancelled outcomes when a wrapper masks the exit. Add real callback and primary passed-ID fixtures, positive controls for titles containing FAILED, and a deliberate policy for negated checks. Invalidate or rejudge receipts created under changed judging semantics; do not match failure words indiscriminately.

Code: [shiploop_test_loop.py — judge](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:556); [shiploop_test_counts.py — outcomes](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:599); [shiploop_test_counts.py — _pytest: error count omitted from failed tally](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2808); [shiploop_primary.py — _passed_ids](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1310); [shiploop_test_loop.py — _judge_base](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:671); [salesforce.md — Testing and remote test boundary](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2179); [shiploop_test_layers.py — test_layers, targets and criterion confirm contract](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2246).

Qualification IDs: T37, T43, T45.

### R09 — Mutation restoration and interrupted recovery

**conditional · conditional**. Local mutation uses a disposable candidate and restores local source. Remote commands are excluded per card/target, so that local run does not prove a remote mutant was killed.

Remaining: Do not build remote restoration machinery for the excluded route. If an authorized remote mutation path is introduced, require effect tracking, accepted-candidate restoration and interrupted recovery before enabling it.

Code: [shiploop_mutation.py — _check](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:820); [shiploop_mutation.py — split_remote](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:922); [shiploop_mutation.py — _remote_reason](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:939); [shiploop_test_loop.py — _judge_base](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:671).

Qualification IDs: T37, T38.

### R10 — Mutation check-only reuse

**deferred · defer**. Candidate check-only and step-Proof reuse exist. Base and mutation verdict reuse do not; a later measured review explicitly deferred them.

Remaining: Keep the measured deferral. Reopen only when representative command cost justifies the identity/invalidation risk; do not remove mutation from check-only merely to shorten it.

Code: [shiploop_test_loop.py — _reused](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:629); [shiploop_test_loop.py — step_proof](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:60); [shiploop_test_loop.py — _base_run](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:717); [shiploop_mutation.py — _check](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:820); [README.md — Measured reuse deferral and built genericity fixes](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2503); [shiploop-test-loop.test.py — test_complete_after_a_passing_check_only_on_an_unchanged_tree_takes_that_run_and_says_so](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3169).

Qualification IDs: T39.

### R11 — Narrow revisions and unchanged prefix reuse

**deferred · defer**. Per-step revisit now points at its own prior result/commit; same-action step receipts can be reused. Cross-plan unchanged-prefix reuse is absent.

Remaining: Treat prefix reuse as a separate optimization pilot. Preserve exact definitions and reopen actual product repair; no empty-diff shortcut.

Code: [shiploop_navigator.py — _step_revisit_line](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1337); [shiploop_navigator.py — implement_progress](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1358); [shiploop_test_loop.py — step_proof](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:60).

Qualification IDs: T40, T41.

### R12 — Compact, valid result and callback contracts

**implemented · retain**. Notes are read from --notes FILE. Callbacks, receipts and settling templates exist; current terms are KNOWLEDGE, proof, settle, due_stage/due_item and send-back/add-work.

Remaining: Update examples to the current contracts and keep their validator checks. The old inline-notes and two-review policies are obsolete.

Code: [shiploop_protocol.py — complete --notes FILE](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2148); [shiploop_navigator.py — Improve import reads notes file](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2161); [shiploop_consumer_delivery.py — template_assessment](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1203); [glossary.md — Current terminology and separate schemas](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2546); [shiploop_loops.py — invoke_lines](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1580); [shiploop_navigator.py — IMPROVE_TRIVIAL_REVIEWS = 1](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2377).

Qualification IDs: T42.

### R13 — Resolvable references and essential facts

**partial · P2 qualification**. Shared block rendering and locators exist. Mandatory blocks and bounded producer fields support the current 19,500 required-end/20,000 head limits; PRINT_LIMIT is still a separate 16,000 switch.

Remaining: Qualify locator resolution and essential command/target facts at the actual emitted head and installed path lengths. No demonstrated need for a second packet format or new symbol DSL.

Code: [shiploop_navigator.py — packet_head](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:333); [shiploop_navigator.py — PRINT_LIMIT, HEAD_LIMIT and HEAD_REQUIRED_END](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2664); [shiploop_navigator.py — _producer_blocks](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:354); [shiploop_navigator.py — _cited_guides](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1730); [salesforce.md — Testing and remote test boundary](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2179).

Qualification IDs: T18, T19, T43.

### R14 — Evidence-based Improve and relevant history

**implemented · retain**. Steps are committed with learnings; inline implement has a two-commit look-back. Improve has the step-entry base and import re-proof.

Remaining: Retain current history selection and first-trivial review policy; qualify relevant evidence instead of adding a review quota.

Code: [shiploop_navigator.py — look_back_lines](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1381); [shiploop_navigator.py — _step_commit](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1410); [shiploop_navigator.py — _review_base_line](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:530); [shiploop_navigator.py — _improve_change_gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:177); [shiploop_navigator.py — IMPROVE_TRIVIAL_REVIEWS = 1](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2377).

Qualification IDs: T14, T24, T33, T41.

### R15 — Same scoped probe authority for implement and Improve

**partial · P2 fix**. Producer/test instructions allow recorded test commands, while the Improve opening still says no deploy/install/credential access. Re-proof already shares the exact accepted command.

Remaining: For a genuinely authorized test route, make the opening and review permissions consistent with that route and its target/limits. Do not infer a release grant or introduce new authority.

Code: [shiploop_navigator.py — Improve opening authority](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2126); [shiploop_navigator.py — improve_start_contract](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1653); [shiploop_test_loop.py — step_command](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:262); [shiploop_prompts.py — DUTIES[prepare]: consumer access and tool state](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2030).

Qualification IDs: T28, T35, T44.

### R16 — Actual release state, not invented absence

**outstanding · P2 fix**. Release-check observes the current target but still asks to save its not-there-yet output, assuming absence after an earlier authorized stage may already have installed the candidate.

Remaining: Repair release-plan, release-check and both reference copies to record observed current state and the remaining delta. One observation cannot prove present/absent discrimination; do not manufacture absence.

Code: [shiploop_prompts.py — DUTIES[release-check]: current target and not-there-yet wording](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2100); [shiploop_prompts.py — DUTIES[release-plan]: one observation claimed to discriminate states](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2682); [testing-and-documentation.md — Release-check absence wording](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2698); [salesforce.md — Release-check absence wording](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2714); [shiploop_consumer_delivery.py — validate_transition](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1140).

Qualification IDs: T35, T46.

### R17 — Product/test/tool-state classification and source return

**partial · P2 wording/qualification**. Prepare teaches ignored tool state. commit_leftovers commits eligible residual paths, then plan_return requires keep/exclude review. The message says no action needed before that decision; the committed state itself is not yet a reviewed return.

Remaining: Fix the misleading no-action-needed message and qualify one unignored-tool-state fixture through review/return. Preserve required keep/exclude decisions and product configuration; do not add a classification taxonomy without demonstrating a bypass.

Code: [shiploop_prompts.py — DUTIES[prepare]: consumer access and tool state](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2030); [shiploop_item_scope.py — classify](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1440); [shiploop_workspace.py — commit_leftovers](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1454); [shiploop_protocol.py — plan-return: no-action-needed message before review](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2731); [shiploop_workspace.py — plan_return](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2760).

Qualification IDs: T30, T47.

### R18 — Harness keep, terminal state and reporting

**implemented · retain**. The harness has explicit finished/unfinished keep decisions, blocking conditions and cleanup ownership. Kept unfinished work remains a non-passing run.

Remaining: Retain these distinctions. Qualify done-but-uncommitted, host exit and cleanup with harness integration fixtures; do not claim a fresh live platform outcome from this refresh.

Code: [run.py — keep_decision](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1486); [run.py — keep_refusal](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1512); [run.py — finish](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1539).

Qualification IDs: T30, T48.

### R19 — Run-owned loop state and recovery

**outstanding · P2 fix**. Stage start passes --receipt without --directory. That explicit receipt selects the isolated runtime path, which defaults backing state to the temporary directory; the durable receipt alone cannot recreate a lost backing state.

Remaining: Use a run-owned backing-state directory and preserve active receipt next_argv recovery. Validate fresh-context resume and missing-state failure without inferring success or overwriting receipts.

Code: [shiploop_loops.py — start_command](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1568); [until_loop_ephemeral.py — main: receipt chooses isolated path](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2437); [until_loop_ephemeral.py — start](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2385); [until_loop_ephemeral.py — _check_start_receipt: occupied active receipt is refused](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2829); [shiploop_loops.py — invoke_lines](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1580).

Qualification IDs: T12, T42, T49.

### R20 — Applicable guidance across software packages

**implemented · retain**. Runtime/module advice is conditional, the eight considerations are domain neutral, and dependency directories/reporters are sourced through platform cards.

Remaining: Preserve applicability across library, CLI, service, UI, data/config/docs and empty-repository cases. Card tests are not proof of every package type.

Code: [shiploop_prompts.py — DUTIES[plan]: conditional module format](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2279); [implement-guidance.md — Considerations and Evidence](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2595); [shiploop_mutation.py — dependency_directories](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:961); [salesforce.md — Testing and remote test boundary](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2179); [README.md — Measured reuse deferral and built genericity fixes](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2503).

Qualification IDs: T15, T43, T50.

### R21 — Avoid redundant system-stage executions

**partial · P1 qualification**. Candidate reuse compares action-local receipt, stage/item, exact command records, tree and current floors. It does not compare the actual remote target state, fixture state or authority freshness beyond what those records encode.

Remaining: Qualify reuse on stateful/remote commands before broadening it. A changed relevant external state must invalidate or bypass reuse; keep the broader system-stage optimization a measured pilot.

Code: [shiploop_test_loop.py — _reused](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:629); [shiploop_test_layers.py — test_layers, targets and criterion confirm contract](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2246); [shiploop_test_loop.py — stage_commands](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:230); [shiploop-test-loop.test.py — test_complete_after_a_passing_check_only_on_an_unchanged_tree_takes_that_run_and_says_so](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3169).

Qualification IDs: T45, T51.

### R22 — One directive with distinct production and Improve phases

**optional · optional proposal**. Producer and Improve remain distinct Until Loop consumers. Conditions live in contracts and implement no longer prints the whole argument; frozen C/R/AD identity exists. Improve now stops after one trivial review, while production has no clean-review quota.

Remaining: Optional wording-only cleanup: remove the repeated completion clause from WORK_STEP while preserving scope, all acceptance/continuation conditions and recovery. Do not restore the two-pass rule, extra nested loops or the old printed argument.

Code: [shiploop_loops.py — WORK_STEP](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2298); [shiploop_loops.py — step_anchors](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1633); [shiploop_loops.py — REPEAT_STEP](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2314); [shiploop_loops.py — TRIVIAL_REVIEWS: implement gate zero](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2333); [shiploop_loops.py — Conditions remain in contract/runtime instructions](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2351); [shiploop_navigator.py — improve_start_contract](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1653); [shiploop_navigator.py — IMPROVE_TRIVIAL_REVIEWS = 1](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2377).

Qualification IDs: T10, T11, T12, T25, T31, T33, T52.

## Eight considerations

The C1–C8 labels here identify audit considerations, not a product’s criterion IDs.

| Consideration | Current source | Disposition |
|---|---|---|
| C1 — Whole step | [implement-guidance.md — Consideration 1](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3008); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C2 — Interactions | [implement-guidance.md — Consideration 2](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3019); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C3 — Building | [implement-guidance.md — Consideration 3](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3029); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C4 — Deploying | [implement-guidance.md — Consideration 4](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3038); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C5 — State | [implement-guidance.md — Consideration 5](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3049); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C6 — Operating | [implement-guidance.md — Consideration 6](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3060); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C7 — What exists | [implement-guidance.md — Consideration 7](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3070); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |
| C8 — Proof | [implement-guidance.md — Consideration 8](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3080); [shiploop_prompts.py — Implement considerations locator](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2649) | Referenced static guidance; no additional form. |

## Fourteen Code craft rules

All fourteen current rules exist. The three older expansions called out below remain proposals; their absence is not evidence of an explicit rejection.

| Rule | Current source | Disposition |
|---|---|---|
| CC1 — Match the house | [shiploop_prompts.py — CODE_CRAFT rule 1](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2857); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC2 — Fail at the door | [shiploop_prompts.py — CODE_CRAFT rule 2](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2868); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC3 — State the contract where it lives | [shiploop_prompts.py — CODE_CRAFT rule 3](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2883); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Earlier proposal to document the complex unit and its removed alternative is not implemented; no explicit decision rejecting that expansion was found in the lean-port record. Review separately after acceptance correctness; preserve the current rule until then. |
| CC4 — Spend tokens on information | [shiploop_prompts.py — CODE_CRAFT rule 4](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2895); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC5 — Small, not thin | [shiploop_prompts.py — CODE_CRAFT rule 5](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2905); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC6 — Make failure diagnosable | [shiploop_prompts.py — CODE_CRAFT rule 6](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2915); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Earlier proposal to release acquired resources on every success/failure path is not implemented; no explicit decision rejecting that expansion was found in the lean-port record. Review separately after acceptance correctness; preserve the current rule until then. |
| CC7 — Write text that can be translated | [shiploop_prompts.py — CODE_CRAFT rule 7](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2928); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC8 — Put it where it belongs | [shiploop_prompts.py — CODE_CRAFT rule 8](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2941); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC9 — Compose before you build | [shiploop_prompts.py — CODE_CRAFT rule 9](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2954); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Earlier proposal for narrow interfaces, a pure core and side-effect edges is not implemented; no explicit decision rejecting that expansion was found in the lean-port record. Review separately after acceptance correctness; preserve the current rule until then. |
| CC10 — Concurrency only for a shown gain | [shiploop_prompts.py — CODE_CRAFT rule 10](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2968); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC11 — Platform services before hand-written infrastructure | [shiploop_prompts.py — CODE_CRAFT rule 11](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2976); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC12 — Bound remote calls | [shiploop_prompts.py — CODE_CRAFT rule 12](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2984); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC13 — No hard-coded environment values | [shiploop_prompts.py — CODE_CRAFT rule 13](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2992); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
| CC14 — Inject the clock, randomness and I/O | [shiploop_prompts.py — CODE_CRAFT rule 14](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:3000); [shiploop_prompts.py — END_REVIEW_FOCUS and IMPLEMENT_STEP_REVIEW_FOCUS](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1926) | Current rule and shared review consumer implemented. |
