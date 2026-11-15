Execute: ask

# Implement-step improvement plan — re-anchored 2026-11-15

**The newer code resolves or supersedes several old proposals. Keep the remaining work centered on truthful acceptance and fresh evidence; preserve the simpler lifecycle already implemented.**

Source baseline: `065dfadd1221ba43a3976e959e1acac50d7b770c` (local `main`), containing fetched `origin/main` `065dfadd1221ba43a3976e959e1acac50d7b770c`. The first rebase was already up to date. The second replayed three local scenario/experiment commits without conflicts and preserved existing untracked experiment files. A third refresh rebased this audit branch onto the newer main, including E14 and its registration-hash correction. All tracked `skills/` and `test/` bytes are identical to the initial review/test revision `64d5e3c1df1a69676996ae0489b138fe16f723a4`; intervening changes are documentation and experiment tools. Tests and probes retain their actual original revision.

This restores the existing plan filename from the archived audit while replacing obsolete conclusions. All 22 recommendation IDs, eight considerations, fourteen Code craft rules and T1–T52 references remain accounted for. The October 25 plan and Chess/Battleship analyses remain historical in archive commit `a8537de752bf925244f22c1dfed98097fc8180f2`; that archive is not a branch to merge wholesale. The unrelated September `shiploop-remaining-recommendations-plan.md` is a completed historical plan with different IDs.

“Present” below means verified in this source, not universal package or live-host certification. “Qualification” means a focused acceptance experiment is still needed before deciding on a repair. Proposed prompts below are not applied. Runtime implementation still follows the plan’s `Execute: ask` boundary.

## What changed since the earlier audit

| Change | Consequence for this plan | Current source / decision |
|---|---|---|
| One step on both execution routes | Retire whole-plan ask-agent and implementation-chain recommendations. | [shiploop_navigator.py:7741 — step_block and _step_block_shown](../skills/shiploop/scripts/shiploop_navigator.py#L7741); [shiploop_navigator.py:2130 — printed_text](../skills/shiploop/scripts/shiploop_navigator.py#L2130); [shiploop_prompts.py:670 — _IMPLEMENT_WORKER and _IMPLEMENT_INLINE](../skills/shiploop/scripts/shiploop_prompts.py#L670); [`146bd7f8`](https://github.com/whichguy/skill-craft/commit/146bd7f81ed3f03194655df6f9ed8a5a0a2ca021) |
| Implement → test → document → review → commit for each applicable step | Retarget acceptance and review checks to the current step boundary; `verify` is retired. | [shiploop_navigator.py:5009 — _step_proof_gate](../skills/shiploop/scripts/shiploop_navigator.py#L5009); [shiploop_navigator.py:5184 — _improve_change_gate](../skills/shiploop/scripts/shiploop_navigator.py#L5184); [shiploop_prompts.py:2604 — IMPLEMENT_STEP_REVIEW_FOCUS_HEAD](../skills/shiploop/scripts/shiploop_prompts.py#L2604); [`ddaf9076`](https://github.com/whichguy/skill-craft/commit/ddaf90760fd0035aae46d2c1591fa61dbb9dbd8b) |
| Full normal packet emission; per-field spills remain | Remove the old normal-head cutoff and text-size refusal recommendations. Test real emission plus locator recovery. | [shiploop_navigator.py:2130 — printed_text](../skills/shiploop/scripts/shiploop_navigator.py#L2130); [shiploop_navigator.py:3789 — write_field_files](../skills/shiploop/scripts/shiploop_navigator.py#L3789); [shiploop_fields.py:39 — component and inline](../skills/shiploop/scripts/shiploop_fields.py#L39); [`6116b91e`](https://github.com/whichguy/skill-craft/commit/6116b91ee95143e8d8b387e8be84df338289c053) |
| Stronger Proof planning and narrower criterion attribution | Preserve real consumers of per-step paths; do not simplify them away. | [shiploop_navigator.py:3108 — _check_step_sizing](../skills/shiploop/scripts/shiploop_navigator.py#L3108); [shiploop_navigator.py:2708 — _normalise_steps](../skills/shiploop/scripts/shiploop_navigator.py#L2708); [shiploop_item_scope.py:178 — proof_order_refusal](../skills/shiploop/scripts/shiploop_item_scope.py#L178); [`66ca4525`](https://github.com/whichguy/skill-craft/commit/66ca45252b5990d6d34503c15d5b2abe607ffc86) |
| Check/complete sharing and mutation reuse | R10 is implemented. R08/R21 must cover the whole-answer shortcut as well as lower-level receipts. | [shiploop_mutation.py:429 — _reusable](../skills/shiploop/scripts/shiploop_mutation.py#L429); [shiploop_mutation.py:483 — mutation_check](../skills/shiploop/scripts/shiploop_mutation.py#L483); [shiploop_test_loop.py:1370 — take_check](../skills/shiploop/scripts/shiploop_test_loop.py#L1370) |
| Completed steps survive send-back | R11 is superseded by fix-forward: repair through a new step, preserve old criteria/cases/floors. | [shiploop_planning_revision.py:119 — _StepLists.send_back / _StepLists.plan](../skills/shiploop/scripts/shiploop_planning_revision.py#L119); [shiploop_navigator.py:3022 — _fix_forward_refusal](../skills/shiploop/scripts/shiploop_navigator.py#L3022) |
| Criterion-based stuck rule and conditional single-command close | Remove the seven-attempt rule and old closing examples. The shell chain is not an atomic API. | [shiploop_loops.py:67 — WORK_STEP](../skills/shiploop/scripts/shiploop_loops.py#L67); [shiploop_loops.py:100 — REPEAT_STEP](../skills/shiploop/scripts/shiploop_loops.py#L100); [shiploop_stage_spec.py:85 — STEP_CRITERIA_CONDITION and STUCK_FIX](../skills/shiploop/scripts/shiploop_stage_spec.py#L85); [shiploop_loops.py:531 — _RESULT_HEAD](../skills/shiploop/scripts/shiploop_loops.py#L531) |
| Improve panel changes landed, then scheduling evolved | Replace “nothing built / awaiting approval” with the per-proposal dispositions below. | [shiploop-run5-followups-journal-2026-10-25.md:19 — Panel batch: what was built](../docs/shiploop-run5-followups-journal-2026-10-25.md#L19) |

The second fetch also brought a [Grok headless-refusal diagnosis](experiments/grok-headless-refusals-20261115/README.md#L143). It narrows the historical Battleship F10 shell-shape hypothesis to observed host/build behavior. Its hook and resume-prompt options remain apparatus proposals with only small probe evidence; they do not justify a rule in every package’s inner-loop prompt. R18 links the actual classifier prototype and current resume-prompt edit target.

The third refresh added the [E14 one-context control](experiments/parallel-plan-execution-20261114/skill-layer-contract.md#L78). It supports the existing simplicity constraint: compare worker fan-out against batching independent commands and overlapping their waits in one context. These short-task cells do not establish gains for production steps. R04 anchors both CC10 and the study arithmetic; no new scheduling policy is proposed.

## Remaining work in priority order

| Priority | IDs | Smallest warranted next action |
|---|---|---|
| P1 | R08 | Repair mixed pytest errors and qualify obsolete verdicts through candidate, Proof and whole-answer callback routes. Fresh helper probes still reproduce these defects. |
| P1 | R21, R10 | Hold code/command constant while a controlled external fixture changes. Qualify all reuse layers; conservatively rerun uncertain stateful checks if the callback demonstrates false acceptance. |
| P1 | R07, R05 | Exercise partial reply → revision → attempted completion and an inherited procedure made invalid by setup changes. Add enforcement or wording only for a reproduced miss. |
| P2 | R19 | Create a run-owned backing-state directory and pass the existing option at ordinary stage start; retain current receipt recovery. |
| P2 | R15, R16 | Align already-authorized test scope and replace forced-absence language with actual current-state observations plus independent observer controls. |
| P2 | R17 | Delete the misleading “no action needed” parenthetical; preserve the existing keep/exclude review. |
| P3 | R01, R13 | Correct stale path-reader documentation and qualify cold-host locator use. Retain paths and full emission. |
| Optional / conditional | R04, R09, R22 | Defer broad rubric expansion, keep remote mutation excluded, and pilot Work shortening only if quality holds. |

## Each recommendation, its code and acceptance

The linked source is the implementation or exact edit target. The adjacent acceptance checks are requirements for closing the remaining work, not claims that all those checks ran today. The [source map](shiploop-implement-prompt-audit-evidence/reanchor-20261115/source-map.json) retains every supporting span, excerpt hash and relevant decision commit.

### R01 — Step-specific executable checks

**present with clarification.** Every route has a step-bound Proof. The planner now rejects known unwritten-test and later-step inputs; inline test paths and generic-suite/criterion mismatches are also checked. Per-step paths remain optional in parsing but now feed proof-order validation; the comment saying nothing reads them is stale. Four criteria/three product files remains planning guidance, not a numeric CLI gate.

**Next:** Retain per-step paths on both routes and correct the stale parser comment. Clarify prompt expectations versus compatibility parsing without adding a new path schema or arbitrary gate.

**Acceptance:** Reject a Proof that needs an absent test or a file produced only by a later step; accept an existing test or an earlier producer, and the documented all-tests-item exception. Verify both routes bind one step and its due criteria; omission-compatible legacy input must not be described as providing path-order evidence.

**Code:** [shiploop_navigator.py:3108 — _check_step_sizing](../skills/shiploop/scripts/shiploop_navigator.py#L3108); [shiploop_navigator.py:2708 — _normalise_steps](../skills/shiploop/scripts/shiploop_navigator.py#L2708); [shiploop_item_scope.py:178 — proof_order_refusal](../skills/shiploop/scripts/shiploop_item_scope.py#L178); [shiploop_prompts.py:1326 — DUTIES[step-plan]](../skills/shiploop/scripts/shiploop_prompts.py#L1326)

### R02 — One assignment on every surface

**present; emission policy superseded.** A shared Step block supplies task, criteria, cases, dependencies, Proof and skills. Both routes execute one step. Normal printed_text emits the saved body in full; packet_head remains a diagnostic helper.

**Next:** Retain the shared block and whole-packet policy. Test actual emitted output and any host-side truncation recovery, not a proposed new size cutoff.

**Acceptance:** For inline and ask-agent, compare saved packet, actual printed output and applicable review context for the same step and criterion identities. With long/multibyte fields, retain the full emitted body and resolvable field files; a host-cut view must lead back to the whole saved material.

**Code:** [shiploop_navigator.py:7741 — step_block and _step_block_shown](../skills/shiploop/scripts/shiploop_navigator.py#L7741); [shiploop_navigator.py:2130 — printed_text](../skills/shiploop/scripts/shiploop_navigator.py#L2130); [shiploop_prompts.py:670 — _IMPLEMENT_WORKER and _IMPLEMENT_INLINE](../skills/shiploop/scripts/shiploop_prompts.py#L670)

### R03 — Criterion evidence and changed-candidate proof

**superseded form; gates retained.** The earlier mandatory evidence-row form remains retired. Implement acceptance runs its Proof; the current document-stage review import lints changed lines and reruns the step test commands after edits. This is not the former implement-review Proof call.

**Next:** Use current receipts, result notes and post-edit test gates. Add no second evidence form. Validate that the checks used after review still observe the affected criterion.

**Acceptance:** A failing implement Proof must refuse completion; a review edit breaking a recorded step test must refuse import. An unchanged review may retain valid current evidence; later-stage observations remain open, and source inspection cannot replace a required execution.

**Code:** [shiploop_navigator.py:5009 — _step_proof_gate](../skills/shiploop/scripts/shiploop_navigator.py#L5009); [shiploop_navigator.py:5184 — _improve_change_gate](../skills/shiploop/scripts/shiploop_navigator.py#L5184); [shiploop_prompts.py:2604 — IMPLEMENT_STEP_REVIEW_FOCUS_HEAD](../skills/shiploop/scripts/shiploop_prompts.py#L2604); [implement-guidance.md:43 — Evidence](../skills/shiploop/references/implement-guidance.md#L43)

### R04 — Static guidance and Code craft

**present; expansions deferred.** The eight applicable considerations and fourteen shared Code craft rules remain. The historical CC3 complex-unit expansion, CC6 all-exit resource release and CC9 pure-core/interface expansion are not all stated by the current rules. That absence alone is not a demonstrated defect. The latest E14 experiment supports retaining CC10's measured-gain condition: its one-context control overlaps command waits, and the reported short-task results do not qualify production step fan-out. The study changes no skill or default.

**Next:** Keep the lean guide and shared rubric. Reopen one missing clause only when a concrete defect survives the current wording; do not restore the rejected symbolic grammar.

**Acceptance:** An applicable review receives the authoritative rule wording and a step reads only selected decision guidance. Challenge any proposed added clause with a failing example and a good control; untouched considerations need no new result row.

**Code:** [shiploop_prompts.py:606 — CODE_CRAFT](../skills/shiploop/scripts/shiploop_prompts.py#L606); [implement-guidance.md:7 — Considerations](../skills/shiploop/references/implement-guidance.md#L7); [shiploop_prompts.py:2490 — _prompt_parts](../skills/shiploop/scripts/shiploop_prompts.py#L2490); [skill-layer-contract.md:78 — section 6, revised experimental predicate](../docs/experiments/parallel-plan-execution-20261114/skill-layer-contract.md#L78); [a0p_table.py:1 — registered A0p comparison arithmetic](../docs/experiments/parallel-plan-execution-20261114/a0p_table.py#L1)

**Decisions:** [`ed2c1834`](https://github.com/whichguy/skill-craft/commit/ed2c1834ba562d35540a32311e31d975a9df574d) — Retained six small-fixture control trials; no skill, agent or default change, and no production step-level result; [`065dfadd`](https://github.com/whichguy/skill-craft/commit/065dfadd1221ba43a3976e959e1acac50d7b770c) — Corrected registration references after the shared checkout rebase; preserve published hashes and original historical messages.

### R05 — Valid inherited procedures

**partial.** The shared walk now explicitly checks deciding transitions against spec rules, recomputes derived results, rejects unchecked helpers, and includes reviewer-added cases. Carry-forward still selects a separate code-review focus without that walk. Release-verify requires valid plans, current observations and scoped person replies, but does not explicitly apply the shared transition walk before the person ask. This establishes a remaining qualification boundary, not a demonstrated reviewer failure.

**Next:** Run the narrow behavioral qualification before editing prompts. Add the shared walk at a later boundary only if that fixture demonstrates a miss; add no procedure schema.

**Acceptance:** Accept: An unchanged valid library/API/CLI procedure remains accepted and its observation stays attributable to the intended candidate. Reject/challenge: Change setup so an inherited procedure's next action becomes impossible; final review/person preparation must identify the first invalid transition and retain the observation as open. Include an unchecked helper and a reviewer-added case.

**Code:** [shiploop_prompts.py:691 — PROCEDURE_WALK and _PROCEDURE_ITEM](../skills/shiploop/scripts/shiploop_prompts.py#L691); [shiploop_navigator.py:8202 — _improve_focus](../skills/shiploop/scripts/shiploop_navigator.py#L8202); [shiploop_prompts.py:2567 — END_REVIEW_FOCUS_HEAD](../skills/shiploop/scripts/shiploop_prompts.py#L2567); [shiploop_prompts.py:1840 — DUTIES['release-verify']](../skills/shiploop/scripts/shiploop_prompts.py#L1840); [shiploop-guidance.test.py:3047 — ProcedureFixtureTests](../test/shiploop-guidance.test.py#L3047)

**Decisions:** [`7d372c5a`](https://github.com/whichguy/skill-craft/commit/7d372c5a98cba6ec0272301d2af6b2cb6d38ca7c) — Put one shared procedure-validity condition at planning producers/reviews; retain existing case fields and distinguish deterministic fixtures from reviewer qualification; [`abdb0fdd`](https://github.com/whichguy/skill-craft/commit/abdb0fdd8b3206e3458603c2cefc87c6326ac556) — Require checked deciding transitions, recomputed expectations and review-added-case coverage; explicitly leave model effectiveness unmeasured; [`c376fe52`](https://github.com/whichguy/skill-craft/commit/c376fe521521ef7e6cee22f9b34a3aacc10ef3c4) — Carry required surfaces and completion conditions without new lifecycle gates; retained guidance is not prospective model-obedience proof.

### R06 — Early actor/access prerequisites

**present.** The mechanism remains present. Test-strategy discovers tools, probes capability or reuses a current same-setup probe, tries an existing UI before authentication, and distinguishes runtime/session/target readiness. Prepare reads saved runner output and requires at least one test ran. That gate neither executes the saved command nor proves actor permissions or consumer behavior.

**Next:** Retain implementation. Qualify actual actor, entry and permission behavior for the package under test; do not add fields merely to restate readiness.

**Acceptance:** Accept: A supported tool performs the fixture's first real action under the intended actor; a current same-capability/setup probe can be reused. A saved readable run showing one test satisfies the harness-content gate. Reject/challenge: A version print, probe page or zero-test summary fails the harness-content gate. Successful authentication with denied feature access remains a prerequisite; a stand-in does not satisfy the product observation.

**Code:** [shiploop_prompts.py:1116 — DUTIES['test-strategy'], item 11](../skills/shiploop/scripts/shiploop_prompts.py#L1116); [shiploop_prompts.py:1138 — DUTIES['test-strategy'], item 12](../skills/shiploop/scripts/shiploop_prompts.py#L1138); [shiploop_test_layers.py:212 — check_harness_output](../skills/shiploop/scripts/shiploop_test_layers.py#L212); [shiploop-handoff.test.py:1263 — TestLayerGateTests.test_prepare_harness_evidence_must_show_a_test_ran](../test/shiploop-handoff.test.py#L1263)

**Decisions:** [`dc83bc19`](https://github.com/whichguy/skill-craft/commit/dc83bc1960ade498048bb30680565a50a7db2247) — Reuse existing runner readers to reject probe pages; acknowledge that saved summaries can be fabricated and do not independently prove execution; [`c12c23b7`](https://github.com/whichguy/skill-craft/commit/c12c23b7bdde1da9f36bca66983dd540790b622f) — Discover tools, attempt the UI before scoped authentication, return to the same feature check, and retain existing fields rather than introduce speculative readiness schemas.

### R07 — Required acceptance continuity

**partial.** Declared required delivery-contract obligations cannot silently disappear: omitted assessments retain the contract, removing or changing required rows requires an explicit correction source, and unanswered/non-passed observations remain pending. New fix-forward gates also preserve completed-step criteria/cases and reject an omitted frozen case list. This is not universal semantic continuity: the separate unverified list allows deletion at the due stage without mechanically checking the claimed observation; primary validation checks listed unverified rows, not completeness of every required outcome. Correction references remain host claims.

**Next:** Compose the existing partial-reply, scope-weakening and amendment fixtures into the archived two-outcome continuity scenario. Reproduce any false closure through the actual callback before adding enforcement. Preserve existing correction and person-only continuation routes.

**Acceptance:** Accept: After a two-outcome requirement receives one valid observation, retain the unanswered outcome through amendment; a later current observation closes it. A legitimately authorized scope correction follows the existing correction route. Reject/challenge: Reject completion after partial/declined replies, omitted assessments, removed required contract rows, omitted frozen cases or lower-layer-only evidence for required consumer behavior. Accept: A genuinely observed unverified outcome can be removed at its due stage; outcomes due elsewhere remain unchanged. Reject/challenge: Probe a due-stage deletion with no observation and a revised product-acceptance empty list. Determine whether another real callback gate prevents false closure; the inspected unverified/primary functions alone do not.

**Code:** [shiploop_consumer_delivery.py:352 — _requires_user_correction](../skills/shiploop/scripts/shiploop_consumer_delivery.py#L352); [shiploop_consumer_delivery.py:483 — project](../skills/shiploop/scripts/shiploop_consumer_delivery.py#L483); [shiploop_consumer_delivery.py:594 — _pending and validate_transition](../skills/shiploop/scripts/shiploop_consumer_delivery.py#L594); [shiploop_unverified.py:122 — check_restated](../skills/shiploop/scripts/shiploop_unverified.py#L122); [shiploop_primary.py:179 — check_queue and check_unverified](../skills/shiploop/scripts/shiploop_primary.py#L179); [shiploop_navigator.py:3061 — _frozen_case_refusal](../skills/shiploop/scripts/shiploop_navigator.py#L3061); [shiploop-consumer-delivery.test.py:1319 — ConsumerDeliveryTests.test_a_partial_person_reply_closes_no_required_behavior_and_the_ask_again_it_names_is_accepted](../test/shiploop-consumer-delivery.test.py#L1319); [shiploop-step-edges.test.py:440 — CrossStepCaseTests.test_after_an_amendment_the_done_steps_counts_and_cases_still_bind](../test/shiploop-step-edges.test.py#L440)

**Decisions:** [`d84d30a9`](https://github.com/whichguy/skill-craft/commit/d84d30a977aa584ecc748fb34982f2bd7add21df) — Require later stages to restate unverified outcomes; due observations are recorded as drops, while later-due outcomes must carry forward; [`fdec0f6e`](https://github.com/whichguy/skill-craft/commit/fdec0f6ed642165effd33be640974c9ee25c1561) — Replace global test-spec primary coverage with plan/carry-forward follows coverage; keep tests relative to the current step and retire suite_requirements; [`636a02e2`](https://github.com/whichguy/skill-craft/commit/636a02e22965aa2a6e0de3cf6fb9ea761b2e0516) — Fix forward after send-back: preserve completed steps, criterion definitions and cases; retain a step still to run; [`41f0b5ce`](https://github.com/whichguy/skill-craft/commit/41f0b5ce999057352bd1f1f0ef5c5b196189ee6b) — Close Improve-import reopening, omitted-case-list and cumulative-floor gaps; [`300ae9b0`](https://github.com/whichguy/skill-craft/commit/300ae9b0c5db8fcdded102d0ad7622f31be509bd) — Empty terminal learning commit: DROP the unqualified broad intent-continuity candidate and retain accepted runtime; deferred follow-ups require a future owner decision.

### R08 — Truthful verdicts and receipt reuse

**partial.** Mixed pytest pass/error remains falsely accepted at the inspected judge boundary when exit is zero and the listed ID passes: the parser recognizes error tokens but omits them from failed and ran counts. Thus '1 passed, 1 error' yields ran=1, failed=0 and passes focused/check judging. Step Proof uses the same judge. Candidate and Proof receipt reuse trust saved passed verdicts without rejudging output or checking judge semantics. A newer whole-answer cache includes package version, but a version mismatch only reruns evaluation, where lower-level stale reuse remains possible. The base no-ID masked-failure defect was fixed separately. Fresh committed-helper probes reproduce the mixed-error false pass and both candidate/step-Proof stale-verdict reuse. These are not full callback upgrade trials.

**Next:** Prioritize the narrow pytest parser/callback regression and stale-receipt replay. Reuse existing receipts and invalidation mechanisms; introduce a semantics discriminator only if needed by the reproduced route. Do not repeat the landed failed-tally fix.

**Acceptance:** Accept: Genuine passes, passing titles containing FAILED and ordinary successful non-runner checks remain accepted; preserve zero-tests, missing-ID and floor precedence. Reject/challenge: Exit-zero mixed passed/error output must refuse focused, check and step-Proof completion and must not contribute a passed ID to primary acceptance. Accept: An unchanged local receipt produced under current semantics remains reusable. Reject/challenge: Seed an obsolete false-pass candidate or Proof receipt, including a package-version mismatch at the whole-answer layer; completion must rerun or safely rejudge rather than inherit the pass. Accept: A returned-copy check observes the delivered candidate and reports that identity. Reject/challenge: Wrong revision, unknown return identity, cancelled-only and skipped-only outcomes cannot masquerade as the required successful observation. Define deliberate negated-runner-check semantics explicitly before changing that behavior.

**Code:** [shiploop_test_counts.py:55 — _PYTEST_SUMMARY and _pytest](../skills/shiploop/scripts/shiploop_test_counts.py#L55); [shiploop_test_loop.py:836 — judge](../skills/shiploop/scripts/shiploop_test_loop.py#L836); [shiploop_test_loop.py:1389 — _reused](../skills/shiploop/scripts/shiploop_test_loop.py#L1389); [shiploop_test_loop.py:1662 — step_proof](../skills/shiploop/scripts/shiploop_test_loop.py#L1662); [shiploop_check.py:42 — answer_key and matching_yes](../skills/shiploop/scripts/shiploop_check.py#L42); [shiploop_navigator.py:10329 — dispatch check/complete branch](../skills/shiploop/scripts/shiploop_navigator.py#L10329); [shiploop_test_loop.py:1901 — _judge_base](../skills/shiploop/scripts/shiploop_test_loop.py#L1901); [shiploop_primary.py:108 — _passed_ids](../skills/shiploop/scripts/shiploop_primary.py#L108); [shiploop_test_loop.py:702 — observation and verify](../skills/shiploop/scripts/shiploop_test_loop.py#L702); [shiploop-test-loop.test.py:4177 — MaskedZeroExitFailureTests](../test/shiploop-test-loop.test.py#L4177)

**Decisions:** [`5fb29784`](https://github.com/whichguy/skill-craft/commit/5fb2978401b12278839670a9e1024a478989518e) — Reporter-recognized failures override exit zero; retain missing-ID behavior and note unresolved retry-to-pass aggregation; [`b446994c`](https://github.com/whichguy/skill-craft/commit/b446994cfbf3ad40c08cfa4ed6b926213175623e) — Apply masked-failure handling to the base judge's no-ID path; shared reporter retry semantics remain separate; [`5086baf6`](https://github.com/whichguy/skill-craft/commit/5086baf688a611172003e0fac4417dba06bb4e0c) — Introduce version-bearing whole-answer reuse while explicitly retaining _reused for draft-only changes; [`be98fb8e`](https://github.com/whichguy/skill-craft/commit/be98fb8e94c1d0310e3ee39953090620acb6fb07) — Add a repeat-safety explanation on Proof failure; explicitly decline running every Proof twice and acknowledge unchanged-tree Proof reuse; [`68985caf`](https://github.com/whichguy/skill-craft/commit/68985caf4ee4eab732e0df725e88aca40817f2d4) — Revert the unqualified A2b wording change; retain A2a repeat-safety guidance. Do not revive the reverted wording as an accepted remedy.

### R09 — Mutation restoration

**conditional.** The exclusion remains. Known remote commands and commands naming stateful targets are omitted. Local mutants execute in a temporary candidate worktree, restore each mutated file in finally, and remove/prune the worktree on normal context exit. This does not provide crash-proof external-state restoration or sandbox arbitrary commands.

**Next:** Keep remote mutation excluded. Do not build remote restoration machinery without an authorized route. Qualify local interruption behavior separately if a concrete failure warrants it.

**Acceptance:** Accept: Local accepted and refused mutation checks leave candidate bytes unchanged; declared remote/stateful commands never execute against local mutants. Reject/challenge: Injected command failure or interruption must not alter the source checkout. An unclassified command with external effects must not be assumed safe merely because it runs from a temporary directory. Accept: If remote mutation is separately authorized, prove restoration to the accepted target after success, failure and recovery. Reject/challenge: Interrupted or partially applied remote mutation must prevent acceptance until restoration is observed; absent that capability, retain exclusion.

**Code:** [shiploop_mutation.py:100 — split_remote](../skills/shiploop/scripts/shiploop_mutation.py#L100); [shiploop_mutation.py:349 — _check](../skills/shiploop/scripts/shiploop_mutation.py#L349); [shiploop_test_loop.py:1768 — _BaseTree](../skills/shiploop/scripts/shiploop_test_loop.py#L1768); [shiploop_mutation.py:281 — _run_focused and _check](../skills/shiploop/scripts/shiploop_mutation.py#L281); [shiploop-test-loop.test.py:2071 — TestLoopTests.test_the_checkout_is_byte_identical_after_the_check](../test/shiploop-test-loop.test.py#L2071)

**Decisions:** [`2403ee29`](https://github.com/whichguy/skill-craft/commit/2403ee29d98626812d0646400b1525df4a71d55c) — Use sampled local mutations to challenge assertions after build, with temporary-worktree isolation and a zero-kill refusal; [`7a194ae4`](https://github.com/whichguy/skill-craft/commit/7a194ae4fffbe34ee605e9e12075354a30f46420) — Skip deployed-copy test commands because local mutants cannot reach the deployed product; [`145aefbb`](https://github.com/whichguy/skill-craft/commit/145aefbb76500a1e986d5850858d7e5d3090d945) — Generalize exclusion to declared stateful targets and split local/remote commands per command; [`3f8a0a7b`](https://github.com/whichguy/skill-craft/commit/3f8a0a7b1f9e0d022cf20946664ae4b4b009d19b) — Require evidenced dispositions for mixed-item survivors without pretending excluded remote commands killed them.

### R10 — Mutation/check reuse

**present; freshness qualification remains.** Mutation reuse has landed. On a normal runner path, mutation_check consults the latest eligible same-action record from either check or counted runs. It compares local focused command strings and candidate tree, then re-evaluates survivor dispositions from the new result. Whole-answer reuse can additionally copy base, candidate, mutation and Proof check records without executing them again. The old blanket deferral is obsolete.

**Next:** Retain the landed reuse rather than reimplement or remove it. Qualify the omitted-input boundaries with minimal same-action probes; repair only a reproduced reachable gap.

**Acceptance:** Accept: A disposition-only resubmission reuses the same mutant observations while recomputing whether every survivor is explained. Reject/challenge: Changed product/test content or focused command strings rerun mutations; removing required dispositions refuses even when the observations are reused. Accept: A matching whole-answer check promotes all recorded evidence with provenance. Reject/challenge: Probe changes to the base, target classification, ignored dependencies or mutation semantics with an unchanged candidate/command. Determine reachable stale reuse before adding cache fields.

**Code:** [shiploop_mutation.py:429 — _reusable](../skills/shiploop/scripts/shiploop_mutation.py#L429); [shiploop_mutation.py:483 — mutation_check](../skills/shiploop/scripts/shiploop_mutation.py#L483); [shiploop_test_loop.py:1370 — take_check](../skills/shiploop/scripts/shiploop_test_loop.py#L1370); [shiploop-test-loop.test.py:2041 — TestLoopTests.test_each_surviving_mutant_needs_a_disposition_and_a_resubmission_with_them_reuses_the_run](../test/shiploop-test-loop.test.py#L2041); [shiploop-test-loop.test.py:2783 — TestLoopTests.test_complete_takes_the_checks_matching_yes_and_runs_nothing_again](../test/shiploop-test-loop.test.py#L2783)

**Decisions:** [`3f8a0a7b`](https://github.com/whichguy/skill-craft/commit/3f8a0a7b1f9e0d022cf20946664ae4b4b009d19b) — Adopt cheap disposition-only mutation retries while retaining survivor review and zero-kill rules; [`5086baf6`](https://github.com/whichguy/skill-craft/commit/5086baf688a611172003e0fac4417dba06bb4e0c) — Complete takes a matching check answer and promotes its base/candidate/mutation/Proof records without rerunning gates; [`8bf10c64`](https://github.com/whichguy/skill-craft/commit/8bf10c649711635fdcacd0bfad48ff5a39d1fc89) — Replace complete --check-only with shiploop check; current acceptance commands must use the new verb.

### R11 — Narrow revisions and completed steps

**superseded by implemented fix-forward.** The later owner-approved fix-forward rule preserves every completed step after an INNER send-back. Completed means document accepted, with review and commit completed. The amendment must copy those step rows exactly, adding done:true, preserve their criterion definitions and frozen cases, and leave at least one step to execute. Repairing completed behavior requires a new step and new criterion IDs. This supersedes reopening completed steps or treating preservation as merely a deferred cache optimization.

**Next:** Retire the old deferred-prefix wording and use the fix-forward contract. Qualify preservation and regression behavior across representative library, CLI, service and configuration packages before claiming generic behavioral coverage.

**Acceptance:** Accept: Complete S1, interrupt S2, amend the plan with unchanged S1 marked done, then complete S2. Verify S1 has one implementation/review/commit history, all cursors resume at S2, and S1 cases and test floors remain binding. Repeat through a second amendment. Reject/challenge: Reject changed or omitted S1 rows, false done marks, changed criterion definitions, omitted frozen cases, cases moved onto completed steps and amendments with no remaining step. Exercise both direct submission and Improve final-result import. Accept: Repair an earlier implementation through a new step with new criterion IDs while preserving existing regression obligations. Reject/challenge: A new step that breaks earlier required behavior must fail its applicable regression checks; preserved history alone must not certify the changed candidate.

**Code:** [shiploop_planning_revision.py:119 — _StepLists.send_back / _StepLists.plan](../skills/shiploop/scripts/shiploop_planning_revision.py#L119); [shiploop_navigator.py:3022 — _fix_forward_refusal](../skills/shiploop/scripts/shiploop_navigator.py#L3022); [shiploop_navigator.py:3074 — _frozen_case_refusal](../skills/shiploop/scripts/shiploop_navigator.py#L3074); [shiploop_navigator.py:4492 — finish_improve](../skills/shiploop/scripts/shiploop_navigator.py#L4492); [shiploop_test_loop.py:1088 — accepted_counts](../skills/shiploop/scripts/shiploop_test_loop.py#L1088)

**Decisions:** [`636a02e2`](https://github.com/whichguy/skill-craft/commit/636a02e22965aa2a6e0de3cf6fb9ea761b2e0516) — Owner approved building fix-forward before replay; completed steps remain fixed and later steps carry repairs; [`41f0b5ce`](https://github.com/whichguy/skill-craft/commit/41f0b5ce999057352bd1f1f0ef5c5b196189ee6b) — Closed Improve-import, omitted-case, cumulative-floor and criterion-free completed-step defects; [`601f4913`](https://github.com/whichguy/skill-craft/commit/601f49130247fdb1ce4edfae421ed844e89a057c) — Preserved interrupted-step provenance and excluded the done marker from substantive row differences.

### R12 — Compact valid result and callback contracts

**present; examples updated.** check and complete share evaluation; the check now applies canonical shape validation too. For done, current loop text asks one shell command chaining check, the satisfied loop report and complete, stopping on failure.

**Next:** Use the exact generated callback and done_argv. Do not invent a new completion verb or bypass receipt checks.

**Acceptance:** Malformed results must be refused by check as by complete; a refused check must prevent the satisfied report and callback. An unchanged valid check may be consumed once with the current key; changed result, candidate, package or floors must re-evaluate as applicable.

**Code:** [shiploop_check.py:42 — answer_key](../skills/shiploop/scripts/shiploop_check.py#L42); [shiploop_loops.py:531 — _RESULT_HEAD](../skills/shiploop/scripts/shiploop_loops.py#L531); [shiploop_navigator.py:10313 — dispatch check and matching yes](../skills/shiploop/scripts/shiploop_navigator.py#L10313)

### R13 — Resolvable references and essential facts

**partly addressed; host behavior unqualified.** Normal packet clipping is removed. Long individual fields still spill to durable RUN/fields files with safe names, written before emit/context. A complete closing marker does not establish that a host showed the middle or that a model read a locator.

**Next:** Qualify actual locator use in a cold host if claiming comprehension or efficiency. Preserve full facts and safe paths; no second packet format or opaque symbol DSL.

**Acceptance:** Whole long/multibyte emitted body retains its suffix; hostile/long field identifiers stay within RUN/fields, with complete original field contents. A simulated host middle cut still exposes the recovery pointer; a live reading claim needs a fresh-context trial, not only render equality.

**Code:** [shiploop_navigator.py:2130 — printed_text](../skills/shiploop/scripts/shiploop_navigator.py#L2130); [shiploop_navigator.py:3789 — write_field_files](../skills/shiploop/scripts/shiploop_navigator.py#L3789); [shiploop_fields.py:39 — component and inline](../skills/shiploop/scripts/shiploop_fields.py#L39)

### R14 — Evidence-based Improve and relevant history

**present; schedule changed.** Review retains relevant history and archived passes; the current per-step review happens after document and uses the step base. Historical schedule proposals need their own current disposition, not an awaiting-approval blanket.

**Next:** Retain evidence-based review at its current owner, its first-trivial convergence and recorded decisions. Propose another cadence change only from measured outcomes.

**Acceptance:** A behavior-changing review edit must add a failing-before case and pass the step commands/lint before import. Inspect relevant archived passes and history without adding a fixed review quota; a no-finding review does not prove unavailable consumer behavior.

**Code:** [shiploop_navigator.py:3468 — look_back_lines](../skills/shiploop/scripts/shiploop_navigator.py#L3468); [shiploop_prompts.py:2585 — IMPLEMENT_STEP_REVIEW_FOCUS_HEAD](../skills/shiploop/scripts/shiploop_prompts.py#L2585); [shiploop_stage_spec.py:90 — STUCK_FIX](../skills/shiploop/scripts/shiploop_stage_spec.py#L90)

### R15 — Consistent scoped test authority

**partial.** The conflict remains. Producer guidance permits authorized prerequisite setup and remote test routes, while the script-generated Improve opening still says 'No push, deploy, install or credential access.' The contract incorporates that Authority section. A separate release-effect prohibition remains and must stay separate from any bounded test-route correction.

**Next:** Retain the narrow correction as open work for a concrete authorized test route. Preserve the independent release-effect guard.

**Acceptance:** Accept: Render producer, Improve opening and frozen contract for one explicit test grant. Verify all preserve its target, allowed operations, identity and limits; then exercise the permitted route against an isolated controlled target. Reject/challenge: With identical command text but no grant, expired authority, a narrower target or a release operation, verify no authority is inferred and no prohibited operation occurs.

**Code:** [shiploop_prompts.py:1268 — DUTIES[prepare]](../skills/shiploop/scripts/shiploop_prompts.py#L1268); [shiploop_prompts.py:1307 — DUTIES[step-plan]](../skills/shiploop/scripts/shiploop_prompts.py#L1307); [shiploop_navigator.py:9861 — improve_opening_text](../skills/shiploop/scripts/shiploop_navigator.py#L9861); [shiploop_navigator.py:9245 — improve_start_contract](../skills/shiploop/scripts/shiploop_navigator.py#L9245); [shiploop_prompts.py:2859 — release_guard construction](../skills/shiploop/scripts/shiploop_prompts.py#L2859)

**Decisions:** [`df520e51`](https://github.com/whichguy/skill-craft/commit/df520e512dac96f363563aa8195a4d6d02f0a19b) — Moved Improve setup into the script-generated stage, opening and frozen contract; [`c12c23b7`](https://github.com/whichguy/skill-craft/commit/c12c23b7bdde1da9f36bca66983dd540790b622f) — Required trying the existing UI before scoped authentication; preserved denied-route and authority boundaries, without claiming authenticated product qualification.

### R16 — Actual release state

**open.** All four identified copies still contain the problematic wording. Release-plan says one predeploy run proves discrimination; release-check and both references demand 'not there yet' output. Other current guidance records candidate identity and authority, but does not remove this contradiction. This is an instructional requirement, not an identified script gate that mechanically demands absence.

**Next:** Correct all four copies together. Separate observing current state from qualifying the observer. Keep source return and remote release authority independent.

**Acceptance:** Accept: Use isolated targets with the candidate absent, already present and present at the wrong revision. Record actual state, candidate identity and remaining delta; establish discrimination with independently controlled positive and negative observations. Reject/challenge: Reject an observer that accepts both correct and wrong revisions. Never delete or alter a target to manufacture absence, and do not repeat a release operation solely because the candidate was already present.

**Code:** [shiploop_prompts.py:1772 — DUTIES[release-plan]](../skills/shiploop/scripts/shiploop_prompts.py#L1772); [shiploop_prompts.py:1797 — DUTIES[release-check]](../skills/shiploop/scripts/shiploop_prompts.py#L1797); [testing-and-documentation.md:249 — Release entry and release-check](../skills/shiploop/references/testing-and-documentation.md#L249); [salesforce.md:55 — Release-check confirm guidance](../skills/shiploop/references/platforms/salesforce.md#L55); [shiploop_prompts.py:1758 — DUTIES[release-plan]](../skills/shiploop/scripts/shiploop_prompts.py#L1758)

**Decisions:** [`153139f1`](https://github.com/whichguy/skill-craft/commit/153139f173e57fe8838899dc534b8ca3cc2f2c2d) — Introduced the inspected packet wording; its message explicitly described unfinished work and is not qualification evidence; [`c2da4604`](https://github.com/whichguy/skill-craft/commit/c2da4604a0916a21280f3a25aa4c7572f0694ea1) — Made rollback commands reflect decided return paths and strengthened release-check comparison, without changing the absence requirement.

### R17 — Source-return decisions and messages

**partial.** The misleading phrase remains and can print before pending decisions are evaluated. The underlying review gate remains: pending paths refuse return, protected or caller-excluded paths cannot be kept, and required knowledge cannot be excluded without a caller exclusion. Leftover commits do not mean return review is complete.

**Next:** Delete the parenthetical and qualify the unignored-tool-state fixture. Preserve the current decision mechanism rather than adding a classification taxonomy.

**Acceptance:** Accept: In a disposable workspace, leave product configuration and an unignored tool-state file. Confirm both reach review after the leftover commit; keep the configuration, exclude tool state, and verify only the reviewed delta returns. Reject/challenge: While either decision remains pending, return must refuse and output must not imply all action is complete. Protected/caller-excluded keep attempts must fail without changing the source. Accept: After all decisions are recorded, output reports the actual expected return route. Reject/challenge: Do not replace the misleading phrase with an unconditional warning that review remains pending after it is complete.

**Code:** [shiploop_protocol.py:323 — workspace plan-return dispatch](../skills/shiploop/scripts/shiploop_protocol.py#L323); [shiploop_workspace.py:1330 — commit_leftovers](../skills/shiploop/scripts/shiploop_workspace.py#L1330); [shiploop_workspace.py:1442 — _validate_plan](../skills/shiploop/scripts/shiploop_workspace.py#L1442); [shiploop_workspace.py:1358 — plan_return](../skills/shiploop/scripts/shiploop_workspace.py#L1358)

**Decisions:** [`e39160ae`](https://github.com/whichguy/skill-craft/commit/e39160ae498e64c178426909abbd21d431f26362) — Added script-owned review-return and the phrase to distinguish an already-made commit from an instruction. Explicitly rejected automatic keep-by-declared-path; [`f1f38850`](https://github.com/whichguy/skill-craft/commit/f1f3885062ef53a561933f502ac10d983e1bfce3) — Removed the credential-pattern commit skip because false positives stranded authorized files; retained runtime and caller exclusions; [`c2da4604`](https://github.com/whichguy/skill-craft/commit/c2da4604a0916a21280f3a25aa4c7572f0694ea1) — Derived runnable rollback recipes from reviewed keep paths.

### R18 — Harness retention and terminal evidence

**present.** These distinctions remain implemented. An unfinished platform can be retained only under the explicit keep policy and successful case-defined keep checks, and is still not a pass. Aggregate grading separately includes committed-product status. A done-but-uncommitted run can therefore fail aggregate grading even if retention keeps the platform. Regrading preserves observed termination instead of inventing an exit. New recovery inspection resolves ownership and returned content without rewriting the historical campaign result. The second fetch added a Grok 1.0.77 headless-refusal diagnosis that narrows the historical Battleship F10 shell-shape hypothesis. Its classifier-preserving hook is a probe prototype, not installed harness behavior or a cross-host prompt requirement.

**Next:** Retain the mechanisms and rerun focused harness integration fixtures when changing them. Keep package behavior, recovery ownership, retention and remote release acceptance as separate claims.

**Acceptance:** Accept: Exercise finished, committed delivery with observed host exit and passing checks; separately retain a timed-out but working platform under declared keep checks. Reject/challenge: Done-but-uncommitted and kept-unfinished cases must remain aggregate failures. A regrade with no observed terminal event must not manufacture a successful host exit. Accept: Inspect a valid final returned checkout without changing state, Git objects, selection or result.json; recover review metrics from archives after removing only the fixture worktree. Reject/challenge: Reject ambiguous ownership, pending transactions, changed returned content and missing binding evidence. Preserve the original failed campaign verdict. Accept: Readers see a complete cleanup record before and after replacement. Reject/challenge: Injected write/fsync/replace failure must not expose partial JSON or certify cleanup freshness from an older retained record.

**Code:** [run.py:2432 — keep_refusal / keep_decision](../test/shiploop_e2e/run.py#L2432); [run.py:1544 — committed_facts](../test/shiploop_e2e/run.py#L1544); [run.py:4700 — aggregate verdict construction](../test/shiploop_e2e/run.py#L4700); [run.py:3523 — termination_facts](../test/shiploop_e2e/run.py#L3523); [run.py:2349 — write_cleanup_record](../test/shiploop_e2e/run.py#L2349); [recovery.py:53 — inspect_context](../test/shiploop_e2e/recovery.py#L53); [shiploop_navigator.py:9738 — _review_pass_archives](../skills/shiploop/scripts/shiploop_navigator.py#L9738); [metrics.py:1142 — improve_reviews](../test/shiploop_e2e/metrics.py#L1142); [README.md:143 — Options and unknowns](../docs/experiments/grok-headless-refusals-20261115/README.md#L143); [analyze.py:236 — floor_shapes](../docs/experiments/grok-headless-refusals-20261115/analyze.py#L236); [preempt_hook.py:1 — prototype PreToolUse hook](../docs/experiments/grok-headless-refusals-20261115/preempt_hook.py#L1); [run.py:1086 — resume_prompt](../test/shiploop_e2e/run.py#L1086)

**Decisions:** [`dcd91d4a`](https://github.com/whichguy/skill-craft/commit/dcd91d4a9f75b50c90cf337f4d63734ee15f48cc) — Allowed explicitly requested retention of a working unfinished platform while keeping pass=false; [`3c604304`](https://github.com/whichguy/skill-craft/commit/3c60430499e64902821f253522c94fa136ae31dd) — Separated process termination from engine refusals and retained unknown observations; [`c2652034`](https://github.com/whichguy/skill-craft/commit/c265203473fa252401cc4bf76d974b81db41f2ea) — Made cleanup-record publication atomic; explicitly denied that atomicity proves freshness or cleanup success; [`17f5e10f`](https://github.com/whichguy/skill-craft/commit/17f5e10f34c6af9ff5054a7842c09e56d81f750e) — Added nonmutating recovery inspection and scoped assessment without converting historical failures into campaign PASS; [`6b422e09`](https://github.com/whichguy/skill-craft/commit/6b422e09c6c47dc4cc3f6a72919c4ba1ca2923a8) — Preserved non-final Improve findings in the run archive; [`a3facda8`](https://github.com/whichguy/skill-craft/commit/a3facda80649736f07b86c607e35284ebb0820db) — Added archive fallback and retained pass telemetry without overriding existing worktree measurements; [`ded34597`](https://github.com/whichguy/skill-craft/commit/ded345978767587e07c6fffe60aa3f7e785c668b) — New retained apparatus diagnosis narrows Battleship F10 to observed Grok build behavior; no hook, default or product prompt change was adopted.

### R19 — Run-owned loop state and recovery

**partial.** The stage-loop launcher still omits --directory. Because --receipt selects isolated operation and start passes directory=None to tempfile.mkstemp, backing state defaults to temporary storage. Improve child startup already supplies RUN/until-loop, so the missing option is specific to ordinary stage-loop launches. Receipt recovery and terminal validation exist, but a receipt cannot reconstruct missing live state.

**Next:** Add the existing --directory option to ordinary stage startup, creating the run-owned directory first; reuse the Improve startup pattern. Preserve exact next_argv recovery, active-receipt protection and intentional terminal backing-state deletion.

**Acceptance:** Accept: Start an ordinary stage in a disposable run and verify state_file is beneath that run's until-loop directory. In a fresh process, execute the receipt's exact next_argv to recover the same action, then submit its exact done_argv once. Reject/challenge: Delete only the fixture backing state: recovery must remain unverified, must not overwrite the active receipt and must not create replacement success. A concurrent run must retain separate state and receipt identity. Accept: Write the result and evidence-grounded report, then execute check && done_argv < report && complete. Verify one accepted stage transition and matching terminal receipt. Reject/challenge: Make check fail: neither the satisfied report nor complete may execute. Change a gate input after check: complete must not blindly reuse the old yes. Missing, copied or still-active receipts must not satisfy completion.

**Code:** [shiploop_loops.py:481 — start_command](../skills/shiploop/scripts/shiploop_loops.py#L481); [until_loop_ephemeral.py:949 — start](../skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py#L949); [until_loop_ephemeral.py:1283 — main](../skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py#L1283); [shiploop_navigator.py:9934 — _start_improve](../skills/shiploop/scripts/shiploop_navigator.py#L9934); [until_loop_ephemeral.py:406 — _check_start_receipt / _error_packet](../skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py#L406); [until_loop_ephemeral.py:1189 — _error_packet](../skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py#L1189); [shiploop_loops.py:531 — _RESULT_HEAD / RESULT_LINE / RESUME_RESULT_LINE](../skills/shiploop/scripts/shiploop_loops.py#L531); [shiploop_navigator.py:7982 — callback rendering](../skills/shiploop/scripts/shiploop_navigator.py#L7982); [shiploop_navigator.py:10306 — dispatch check/complete](../skills/shiploop/scripts/shiploop_navigator.py#L10306); [shiploop_loops.py:670 — check_terminal](../skills/shiploop/scripts/shiploop_loops.py#L670)

**Decisions:** [`d42ef53d`](https://github.com/whichguy/skill-craft/commit/d42ef53d869e38ddf6d365c589accd34837ddde9) — Made the runtime write receipts before terminal state deletion; explicitly did not claim protection against determined full-packet forgery; [`ad29f1d4`](https://github.com/whichguy/skill-craft/commit/ad29f1d41de41598a9525c1ac5098d6eecb90e0b) — Refreshed the vendored runtime while preserving owner-bound Contract/Receipt behavior; [`db725d10`](https://github.com/whichguy/skill-craft/commit/db725d10e31f869442f8ba0ec3b0401c4886b165) — Introduced the conditional one-command close as a measured candidate; explicitly changed no script behavior; [`79457c08`](https://github.com/whichguy/skill-craft/commit/79457c082eefdbf0d41626f16529d265efc173ef) — Recorded four successful historical deliveries and the adoption decision; one observed refused check stopped the chain before reporting done; [`892ae1f4`](https://github.com/whichguy/skill-craft/commit/892ae1f4a2d70efbf44d84ccd433c9d50a0278f8) — Limited the measured benefit to a small close-out gain on Codex Sol medium; rejected further changes without material benefit; [`706b0a26`](https://github.com/whichguy/skill-craft/commit/706b0a262e7a2f786e29f1e9bfacb549303208de) — Recorded the later Codex refresh and corrected a failed background-waiter claim; this is historical installed-host evidence only.

### R20 — Applicability across software packages

**present; breadth remains bounded.** One lifecycle consumes declared criteria, targets, commands, skills and selected platform cards. The considerations explicitly distinguish people, systems, deployment, state and operations only when touched.

**Next:** Keep generic records and applicability selection. Qualify distinct package boundaries only when the claim needs that breadth.

**Acceptance:** Use library API, CLI exit/filesystem, service persistent-state, UI interaction, and data/config/docs consumer checks with package-specific oracles. An irrelevant deployment/UI obligation must not become mandatory; an applicable remote or consumer observation cannot be replaced by a local mock.

**Code:** [implement-guidance.md:7 — Considerations](../skills/shiploop/references/implement-guidance.md#L7); [shiploop_navigator.py:6203 — platform_cards and _platform_testing_lines](../skills/shiploop/scripts/shiploop_navigator.py#L6203)

### R21 — Freshness at external boundaries

**partial.** Local deduplication and check-to-complete reuse are present. Mutable external state is not bound: target identity is declaration data, keeps_state controls base/mutation exclusion, and reuse keys omit live target contents, external fixture generation, environment and authority expiry. System-test can take the lower-level cached pass. Release-verify avoids that helper reuse, but the newer whole-answer shortcut has no equivalent stage or external-state freshness exclusion.

**Next:** Use a local controllable external-state fixture to reproduce the callback boundary. If confirmed, prefer bypassing reuse for uncertain stateful checks using existing declarations. Do not introduce per-command caching or distributed fingerprints without measured need.

**Acceptance:** Accept: An unchanged demonstrably local check reuses its current receipt and records provenance. Reject/challenge: Keep action, draft, repository and command constant; change an external fixture or target result after check. System-test complete must rerun/refuse rather than inherit the old pass. Repeat through the whole-answer release-verify shortcut. Accept: A still-valid scoped authority allows its authorized check. Reject/challenge: Expired or narrowed authority cannot be refreshed by command equality or a prior successful check; exercise this separately from fixture freshness.

**Code:** [shiploop_test_loop.py:377 — stateful_targets and stage_commands](../skills/shiploop/scripts/shiploop_test_loop.py#L377); [shiploop_test_loop.py:1343 — _tree](../skills/shiploop/scripts/shiploop_test_loop.py#L1343); [shiploop_test_loop.py:1460 — verify reuse selection](../skills/shiploop/scripts/shiploop_test_loop.py#L1460); [shiploop_check.py:42 — answer_key](../skills/shiploop/scripts/shiploop_check.py#L42); [shiploop_navigator.py:10333 — dispatch complete branch](../skills/shiploop/scripts/shiploop_navigator.py#L10333); [shiploop-test-loop.test.py:2819 — TestLoopTests.test_each_change_to_what_the_gates_read_makes_complete_run_them_again](../test/shiploop-test-loop.test.py#L2819)

**Decisions:** [`a3b2f975`](https://github.com/whichguy/skill-craft/commit/a3b2f975487ebb7ede6987628c4a931941f9b057) — Fold equivalent command rows and reuse a passed check on unchanged local inputs under D5; release-verify originally remained outside that reuse; [`f04cbdde`](https://github.com/whichguy/skill-craft/commit/f04cbdde94b118f9bc9f4810024afd714928a57f) — Preserve target when folding; require matching targets, while allowing checkout commands to omit target; [`5086baf6`](https://github.com/whichguy/skill-craft/commit/5086baf688a611172003e0fac4417dba06bb4e0c) — Add whole-answer reuse; no external-state freshness input was introduced; [`1e4e04c2`](https://github.com/whichguy/skill-craft/commit/1e4e04c2f72670e5d8395945f5249aec709ff608) — Retained run measurements did not support changing whole-record reuse; expensive first/failed checks dominated that case; [`33843698`](https://github.com/whichguy/skill-craft/commit/33843698f0731cb637dea281491fe35e6c3eeaa7) — Keep broader evidence-reuse semantics deferred and separate retained learning from implementation.

### R22 — One directive with production and review phases

**optional simplification.** The Work template remains 364 characters. Stage Until Loop owns producing the stage result, and Improve reviews the completed step after test/document. Existing completion and recovery contracts already carry the stopping conditions.

**Next:** Pilot shortening only the duplicated Work sentence. Do not add a loop per consideration or claim code anchors alone establish completion.

**Acceptance:** Compare emitted Work plus Exit/Repeat and callback on both routes, preserving scope, after-edit evidence, regression protection and recovery. Paired representative tasks must preserve acceptance quality before reporting token or time gains; 364 to 161 characters is only a template measurement.

**Code:** [shiploop_loops.py:67 — WORK_STEP](../skills/shiploop/scripts/shiploop_loops.py#L67); [shiploop_loops.py:100 — REPEAT_STEP](../skills/shiploop/scripts/shiploop_loops.py#L100); [shiploop_stage_spec.py:85 — STEP_CRITERIA_CONDITION and STUCK_FIX](../skills/shiploop/scripts/shiploop_stage_spec.py#L85); [shiploop_loops.py:531 — _RESULT_HEAD](../skills/shiploop/scripts/shiploop_loops.py#L531)

## Concrete before and after

These examples distinguish wording now in source from a proposed edit. Before excerpts preserve the current wording; release excerpts normalize line wrapping. Commands with uppercase placeholders are illustrative; runtime execution must use generated argv and callbacks.

### Work directive: optional shortening, current lifecycle retained

**Before — current `WORK_STEP`, 364 characters:**
```text
Implement all of step {step} of this item's plan, anchored in the criteria that have been stated ({criteria}{serving}) and the design directions that have been applied ({decisions}), until each criterion assigned to this step is satisfied and none of the others is broken. Do duty items {items} of {run}/packets/{action}.md. Write no tests and start no later step.
```

**After — proposed, 161 characters:**
```text
Implement step {step}: satisfy {criteria}{serving} under {decisions}.
Do duty items {items} of {run}/packets/{action}.md.
Write no tests and start no later step.
```

Keep the existing Exit/Repeat clauses: every assigned criterion shown after the last edit, other requirements preserved, no later work, Proof/lint, criterion-based send-back and honest blocked/pause recovery. Keep the current review after the step’s test/document work. The character reduction is 55.8%; no token, speed or quality improvement is established. R22 anchors and checks govern this pilot.

### Closing a stage: already changed in code

**Before — historical interaction sequence:** write result → run check → separately submit the loop report → separately complete.

**Now — current instruction, schematic:**
```sh
EXACT_CHECK_CALLBACK && EXACT_LOOP_DONE_ARGV < SATISFIED_REPORT && EXACT_COMPLETE_CALLBACK
```

Prepare the result and evidence-grounded five-field report first. A failed check prevents later commands. For blocked/send-back, report the loop blocked and use the callback; never substitute a satisfied report. This shortens orchestration without removing the stage’s Until contract. R12/R19 cite the current implementation; no new command is proposed.

### Inherited acceptance: qualify before adding text

**Before — current final-review opening:**
```text
Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input
```

**After — only if the R05 behavioral fixture demonstrates a miss:**
```text
For an inherited procedure affected by this change, apply the shared procedure
walk to its current setup, state, authority and observer, including review-added
cases. Repair an invalid transition or send it back before requesting its observation.
```

The deciding-transition and unchecked-helper clauses already exist in the shared walk. Do not add them a second time or infer that the missing final-review sentence proves an observed model failure.

### Scoped test authority: conditional repair

**Before — literal Improve opening excerpt:**
```text
No push, deploy, install or credential access.
```

**After — proposed for a recorded authorized test route:**
```text
No push or release effect. Use an already-authorized test route only within its
recorded target, setup and access limits. A recorded command grants no authority;
otherwise no deploy, install or credential access.
```

R15 requires matching producer, opening and frozen-contract scope, with a separate release-effect guard and denied/narrower/expired-authority controls.

### Release state: observe what is there

**Before — excerpts from the stage duties, line wrapping normalized:**
```text
release-check runs it once before the real deploy to prove it tells them apart
save its "not there yet" output
```

**After — proposed common rule:**
```text
Record the current target state, candidate identity and remaining delta.
Define expected present and absent results. Validate discrimination with
authorized fixtures or independent controls. Do not alter the target to obtain absence.
```

Apply to both stage duties and both reference copies listed under R16. Already-present and wrong-revision cases must be distinct.

### Source return: delete one contradictory phrase

**Before — literal message prefix:** `ShipLoop committed these files that were left uncommitted (no action needed): `

**After — proposed prefix:** `ShipLoop committed these files that were left uncommitted: `

Retain the generated file list and commit suffix. Existing pending keep/exclude decisions remain authoritative. R17’s fixture must show both pending and completed review.

### Script repairs: no extra model instruction

| Boundary | Before, observed or source-derived | Required after |
|---|---|---|
| Reporter and obsolete receipts (R08) | Exit zero plus `1 passed, 1 error` passes; saved false passes can be reused. | Recognized errors refuse; obsolete verdicts are invalidated or safely rejudged at every reachable reuse path. |
| Ordinary loop startup (R19) | `start --receipt RECEIPT < CONTRACT` defaults its backing state to temporary storage. | Create the run-owned directory, then `start --directory RUN/until-loop --receipt RECEIPT < CONTRACT`; preserve generated recovery commands. |
| Path metadata (R01) | Parser comment says optional paths have no reader. | Correct the comment: Proof-order checks consume paths; keep the field on both routes. No new prompt/schema machinery. |

## Improve scheduling proposal: current disposition

| Proposal | Re-anchored disposition |
|---|---|
| P1 | Present: tree/result edit telemetry, pass records and metrics include result-only changes; review duration uses the bind-to-last-note interval. Later archival work preserves these records. Caveat: per-pass edited is unknown only when both tree and result comparisons are unknown; one known-false plus one unknown is recorded false. |
| P2 | Present as shared instructions: validate deciding transitions under specification rules, recompute outcomes, reject unchecked appliers and cover review-added cases. Behavioral effectiveness is unverified here. |
| P3 | Superseded. Narrowed test-spec re-review landed, then the owner-approved Oct 26 schedule removed test-spec Improve entirely and deleted the narrowing helper. |
| P4 | Superseded in its original placement and shadow mechanism. No-change review skipping survives at document; changed or unknown steps are reviewed after their code, tests and documentation. IMP-4 shadow logging and the later wide-item heuristic were removed by subsequent scheduling decisions. |
| P5 | Present: surviving mutants require dispositions at the test stage after the zero-kill rule, unchanged mutation records may be reused, and end-of-work review asks whether later edits invalidated dispositions. |
| P6 | Conditional. Default planning_review=stage retains spec, test-strategy and plan reviews, plus first-item/revisited step-plan review. Explicit planning_review=none removes those planning reviews; it does not remove document reviews, system-test-author, release-plan or the final carry-forward review. |
| panel_additions | Result-only check preservation and the one-trivial-pass wording landed with P1. Automated counting of review-introduced defects was deliberately not built because the tested row-ID approach missed the motivating case. Current later-item 'would review' telemetry was not established by this audit. |

**Code:** [shiploop-run5-followups-journal-2026-10-25.md:19 — Panel batch: what was built](../docs/shiploop-run5-followups-journal-2026-10-25.md#L19); [shiploop_navigator.py:9664 — _improve_pass](../skills/shiploop/scripts/shiploop_navigator.py#L9664); [metrics.py:1211 — _improve_review_records](../test/shiploop_e2e/metrics.py#L1211); [shiploop_prompts.py:691 — PROCEDURE_WALK / _PROCEDURE_ITEM](../skills/shiploop/scripts/shiploop_prompts.py#L691); [shiploop_stage_spec.py:372 — test-spec Stage](../skills/shiploop/scripts/shiploop_stage_spec.py#L372); [shiploop_stage_spec.py:457 — document Stage / carry-forward Stage](../skills/shiploop/scripts/shiploop_stage_spec.py#L457); [shiploop_navigator.py:489 — _improve_checkpoint / _first_item_review](../skills/shiploop/scripts/shiploop_navigator.py#L489); [shiploop_stage_spec.py:696 — PLANNING_REVIEW_MODES / reviewed_stages](../skills/shiploop/scripts/shiploop_stage_spec.py#L696); [shiploop_mutation.py:486 — mutation_check](../skills/shiploop/scripts/shiploop_mutation.py#L486); [shiploop_prompts.py:2571 — END_REVIEW_FOCUS_HEAD](../skills/shiploop/scripts/shiploop_prompts.py#L2571)

**Acceptance:** Accept: Run a two-step fixture in each planning-review mode. Verify changed document stages receive reviews, step-plan review follows first-item/send-back rules, and final carry-forward review follows the resulting queue. Reject/challenge: Test-spec must not launch Improve; explicitly unchanged document must not launch it; unknown change state must still review. Neither item width nor IMP-4 position may silently suppress a changed step's review. Accept: A result-only edit counts as edited and retains fresh reviewer-owned check evidence; archived metrics preserve the result when worktree notes disappear. Reject/challenge: Missing records must not become an observed zero. Explicitly test partial-unknown tree/result telemetry and label its current semantics before using it for scheduling decisions. Accept: Validate a legal multi-action expected result and a review-added case using an independent rule-aware checker. Reject/challenge: An illegal transition accepted by an unchecked helper must remain unresolved or be corrected; wording presence and replay alone do not qualify it. Accept: A surviving mutant is killed by an observed test or receives an evidenced permitted disposition; disposition-only resubmission may reuse matching mutation evidence. Reject/challenge: Undisposed survivors refuse completion; changed relevant inputs invalidate reuse; later edits that invalidate a disposition are detected during reconciliation.

The old proposal file is retained as historical evidence. Its “nothing built yet” heading must not be used as the active backlog. This plan does not restore removed reviews, the old shadow heuristic or any iteration count.

## Eight considerations and fourteen rules

All remain individually anchored. Apply a consideration only when the step touches it. Retain the current rule text; the three historical expansion proposals remain deferred under R04.

| ID | Current consideration or rule | Disposition | Exact source |
|---|---|---|---|
| C1 | Whole step | present; applicable only | [implement-guidance.md:15 — Consideration 1](../skills/shiploop/references/implement-guidance.md#L15) |
| C2 | Interactions | present; applicable only | [implement-guidance.md:19 — Consideration 2](../skills/shiploop/references/implement-guidance.md#L19) |
| C3 | Building | present; applicable only | [implement-guidance.md:24 — Consideration 3](../skills/shiploop/references/implement-guidance.md#L24) |
| C4 | Deploying | present; applicable only | [implement-guidance.md:26 — Consideration 4](../skills/shiploop/references/implement-guidance.md#L26) |
| C5 | State | present; applicable only | [implement-guidance.md:30 — Consideration 5](../skills/shiploop/references/implement-guidance.md#L30) |
| C6 | Operating | present; applicable only | [implement-guidance.md:34 — Consideration 6](../skills/shiploop/references/implement-guidance.md#L34) |
| C7 | What exists | present; applicable only | [implement-guidance.md:37 — Consideration 7](../skills/shiploop/references/implement-guidance.md#L37) |
| C8 | Proof | present; applicable only | [implement-guidance.md:40 — Consideration 8](../skills/shiploop/references/implement-guidance.md#L40) |
| CC1 | Match the house | present | [shiploop_prompts.py:609 — CODE_CRAFT rule 1](../skills/shiploop/scripts/shiploop_prompts.py#L609) |
| CC2 | Fail at the door | present | [shiploop_prompts.py:613 — CODE_CRAFT rule 2](../skills/shiploop/scripts/shiploop_prompts.py#L613) |
| CC3 | State the contract where it lives | present; proposed expansion deferred | [shiploop_prompts.py:621 — CODE_CRAFT rule 3](../skills/shiploop/scripts/shiploop_prompts.py#L621) |
| CC4 | Spend tokens on information | present | [shiploop_prompts.py:626 — CODE_CRAFT rule 4](../skills/shiploop/scripts/shiploop_prompts.py#L626) |
| CC5 | Small, not thin | present | [shiploop_prompts.py:629 — CODE_CRAFT rule 5](../skills/shiploop/scripts/shiploop_prompts.py#L629) |
| CC6 | Make failure diagnosable | present; proposed expansion deferred | [shiploop_prompts.py:632 — CODE_CRAFT rule 6](../skills/shiploop/scripts/shiploop_prompts.py#L632) |
| CC7 | Write text that can be translated | present | [shiploop_prompts.py:638 — CODE_CRAFT rule 7](../skills/shiploop/scripts/shiploop_prompts.py#L638) |
| CC8 | Put it where it belongs | present | [shiploop_prompts.py:644 — CODE_CRAFT rule 8](../skills/shiploop/scripts/shiploop_prompts.py#L644) |
| CC9 | Compose before you build | present; proposed expansion deferred | [shiploop_prompts.py:650 — CODE_CRAFT rule 9](../skills/shiploop/scripts/shiploop_prompts.py#L650) |
| CC10 | Concurrency only for a shown gain: bounded, ordered, each error surfaced | present | [shiploop_prompts.py:657 — CODE_CRAFT rule 10](../skills/shiploop/scripts/shiploop_prompts.py#L657) |
| CC11 | Platform services before hand-written infrastructure | present | [shiploop_prompts.py:658 — CODE_CRAFT rule 11](../skills/shiploop/scripts/shiploop_prompts.py#L658) |
| CC12 | Bound remote calls: timeout, idempotent retries with backoff, paged lists | present | [shiploop_prompts.py:659 — CODE_CRAFT rule 12](../skills/shiploop/scripts/shiploop_prompts.py#L659) |
| CC13 | No hard-coded URLs, IDs, credentials, limits or environment names | present | [shiploop_prompts.py:660 — CODE_CRAFT rule 13](../skills/shiploop/scripts/shiploop_prompts.py#L660) |
| CC14 | Inject the clock, randomness and I/O | present | [shiploop_prompts.py:661 — CODE_CRAFT rule 14](../skills/shiploop/scripts/shiploop_prompts.py#L661) |

## T1–T52 acceptance crosswalk

These are stable acceptance references, not 52 passing tests. Each points to the recommendation’s current source and paired acceptance procedure above. Historical fixtures must be updated where the lifecycle changed.

| ID | Recommendation | Current target |
|---|---|---|
| T1 | R01 | Missing step Proof is refused; also check unwritten/later-step dependencies. |
| T2 | R01 | Proof observes current-step behavior; the new path-aware gate is not a complete semantic oracle. |
| T3 | R04 | Resolve selected skills/cards; no mandatory cards_na form. |
| T4 | R04 | Use selected design/example context; no new match form. |
| T5 | R01 | Keep per-step paths for actual Proof-order consumers; 4/3 sizing remains guidance. |
| T6 | R01 | Failing Proof refuses completion on either route. |
| T7 | R03 | Evidence stays in existing result/notes/receipts; no criterion_evidence schema. |
| T8 | R02 | Current emitted/saved/review surfaces share the step identity and relevant checks. |
| T9 | R02 | Quote only due criteria/cases; narrowed commands must not retain later criteria. |
| T10 | R02 | Assignment, contract and current start/resume route survive real emission. |
| T11 | R22 | Work binds accepted criteria, served requirements and design IDs. |
| T12 | R19 | Rebuilt contract and receipt preserve the action through recovery. |
| T13 | R04 | Rubric and lint guidance follow applicability. |
| T14 | R14 | Use relevant history and full-message locators; no new quota. |
| T15 | R20 | Exercise distinct library/CLI/service/UI/data-config-docs boundaries. |
| T16 | R13 | Full normal emission plus durable field spills; old 19,500/20,000 normal-output criterion retired. |
| T17 | R02 | Use current state-version compatibility/refusal, not the old state-v9 assumption. |
| T18 | R13 | Resolve locators at the pinned revision and installed path. |
| T19 | R02 | Keep one shared assignment per surface. |
| T20 | R04 | Keep applicable static considerations; no extra form/extraction. |
| T21 | R04 | Retain one authoritative Code craft text and actual consumers. |
| T22 | R13 | Resolve actual guide locators; no invented Method section/API. |
| T23 | R13 | Built package contains selected references; installed-host qualification is separate. |
| T24 | R04 | Retain all 14 rules; reopen CC3/6/9 additions only from a demonstrated gap. |
| T25 | R05 | Responsible reviewer rejects illegal deciding transitions, including review-added cases. |
| T26 | R07 | Later-owned checks remain planned; due required observations remain open. |
| T27 | R03 | Final-candidate evidence matches the actual acceptance owner and current commands. |
| T28 | R06 | Actor, entry and runner prerequisites retain owner and due stage. |
| T29 | R05 | Changed setup invalidates an inherited observation procedure. |
| T30 | R18 | Return, commits, retention, host termination and product evidence stay distinct. |
| T31 | R02 | Superseded: ask-agent now has one action and Proof per step, just like inline. |
| T32 | R22 | Quality first, then measured reads/tokens/time; no character-count performance claim. |
| T33 | R03 | Retarget to document-review import: changed lines linted and step tests rerun; stale semantics tracked in R08. |
| T34 | R05 | Qualify final review/person-ask inheritance before adding a shared-walk invocation. |
| T35 | R15 | All relevant surfaces preserve the same already-granted test scope. |
| T36 | R06 | A probe/zero-test summary cannot satisfy the harness gate; one runner count still does not prove product behavior. |
| T37 | R08 | Reject errors and obsolete verdicts through all cache layers; intended-copy/mutation semantics remain separate. |
| T38 | R09 | Remote mutation restoration remains conditional on an authorized supported route. |
| T39 | R10 | Mutation and whole-check reuse landed; retain provenance and qualify missing-input invalidation. |
| T40 | R11 | Superseded by fix-forward, not arbitrary prefix caching; preserve exact completed definitions. |
| T41 | R11 | Resume unfinished suffix; earlier behavior is repaired by a new step with new criterion IDs. |
| T42 | R12 | Use current check/complete, generated done_argv, result fields and notes-file contract. |
| T43 | R13 | Essential facts remain reachable through full output and safe durable field files. |
| T44 | R07 | Partial replies plus omitted obligations cannot silently close required outcomes; compose the callback fixture. |
| T45 | R08 | Passed IDs derive from sound observed verdicts; source anchors alone are not evidence of behavior. |
| T46 | R16 | Absent, already-present and wrong-revision targets receive truthful distinct observations. |
| T47 | R17 | Pending return decisions remain explicit after leftover commits. |
| T48 | R18 | Keep policy, host termination and cleanup report observed outcomes. |
| T49 | R19 | Ordinary stage backing state is run-owned; active receipt recovery survives a fresh process. |
| T50 | R20 | Apply only relevant package/runtime/surface guidance. |
| T51 | R21 | Changed external fixture/target/authority invalidates or bypasses every applicable reuse route. |
| T52 | R22 | Producer loop and document-owned Improve remain distinct; first-trivial review, no seven-attempt cap. |

## Simplicity and completion

Use one stage directive, one bound Until contract, current Improve review, and script-owned state/callbacks. Preserve the per-step lifecycle, existing field files and existing receipts. Avoid another ledger, schema, symbol language, review quota or distributed cache. Shorten repeated wording only while preserving scope, authority, observation and recovery. A code anchor proves where an obligation is handled; it does not prove the software satisfies it.

Close a recommendation when its required behavior has valid evidence at the final candidate, or when a later recorded decision supersedes it. Keep optional items explicitly deferred with a reopening condition. Recheck intervening main changes affecting the cited code before implementation; unrelated commits do not justify rerunning the entire historical audit.

## Verification and limits

- The October anchor comparison has **80 exact excerpts retained and 48 changed**, out of 128. Changed excerpts were reinterpreted through current source and later decisions, not merely assigned new line numbers. [Comparison](shiploop-implement-prompt-audit-evidence/reanchor-20261115/old-anchor-comparison.json).
- **97 selected tests passed**: runner counts 49, masked-zero-exit controls 9, packet bounds/spills 21, loop contracts/Work 18. All 5,590 tracked skills/test file hashes and the source HEAD remained unchanged. [Receipt](shiploop-implement-prompt-audit-evidence/reanchor-20261115/test-receipt.json).
- Fresh committed-helper probes reproduce mixed pytest pass/error acceptance and obsolete candidate/Proof receipt reuse, show package-version invalidation at the whole-answer layer, retain a 132,026-character packet body, and confirm the ordinary start lacks a directory option. The probes stub only their declared helper inputs; they are not full callback or live acceptance. [Probe results](shiploop-implement-prompt-audit-evidence/reanchor-20261115/probe-results.json) and [reproducer](shiploop-implement-prompt-audit-evidence/reanchor-20261115/probe_current.py).
- Two fresh read-only CLI reviews explicitly requested `gpt-6-astra` / `high` with the `shiploop-judge` profile, no model fallback. Both exited successfully. Launch controls establish the requested model, not independently verified server identity. The parent reconciled their findings with direct source inspection and probes. Full transcripts remain at the evidence location in the [validation record](shiploop-implement-prompt-audit-evidence/reanchor-20261115/validation.json).
- Source anchors, IDs, links and excerpts are structurally validated by the [reproducible document check](shiploop-implement-prompt-audit-evidence/reanchor-20261115/validate_sources.py). Markdown visual rendering was not inspected. No runtime source change, full repository suite, new CI, installed-host test, live platform run or comparative prompt-quality result is claimed. The historical 716-test receipt qualifies only its original snapshot.
- This update is retained audit/planning work. Its documentation commit does not mark outstanding code repairs or semantic acceptance scenarios complete.
