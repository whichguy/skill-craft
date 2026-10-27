# Remaining recommendations: smallest effective changes

**Fix acceptance correctness first. Simplify the instructions by removing duplicate rules and leaving state, verdicts and transitions with the existing scripts.** The lifecycle stays the same for a library, CLI, service, UI, data/configuration package or documentation package. Project-specific commands, targets and observers are inputs to that lifecycle.

Source checked on 2026-10-25: the working checkout is `98983fa2`; fetched main is `5485b896`. All 128 previously anchored excerpts remain unchanged on main. The local links below use verified working-tree line numbers; [the locator record](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/remaining-20261025/source-refresh.json) also records their exact positions on fetched main. This turn changes documentation only; it does not rebase the checkout or qualify the newer main with the previous 716-test result.

“Before” is labeled as a literal excerpt or observed/source-derived behavior. Every “after” is proposed. A source defect, a reproduced helper failure, and an unproven qualification gap are different evidence levels. The [fresh helper probe](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/remaining-20261025/judge-probe.json) reproduces the two remaining R08 cases on `5485b896`; it is not a full callback or live-platform trial.

## Priority order

| Order | Priority | IDs | Recommendation | Smallest next action |
|---|---|---|---|---|
| 1 | P1 | R08 | Reject false acceptance; invalidate obsolete receipts | Code repair |
| 2 | P1 | R05 | Validate inherited procedures at the last responsible review | Focused behavioral trial, then prompt repair if needed |
| 3 | P1 | R07 | Keep required observations open through partial replies and revisions | Continuity qualification first |
| 4 | P1 | R21 | Prevent reuse when external state can have changed | Freshness qualification; conservative rerun if needed |
| 5 | P2 | R19 | Keep stage-loop backing state with the run | Small code repair |
| 6 | P2 | R15 | Carry existing test authority consistently into Improve | Conditional wording repair |
| 7 | P2 | R16 | Report observed release state and the remaining delta | Prompt/reference repair |
| 8 | P2 | R17 | Remove the contradictory source-return message | Delete one phrase; keep existing review output |
| 9 | P3 | R22 | Shorten Work while retaining the bound loop contract | Optional equivalence pilot |
| 10 | P3 | R01 / R13 | Align route-specific metadata and keep essential facts visible | Clarify and qualify; avoid new fields |
| 11 | Defer | R04 | Do not expand all fourteen Code craft rules | Reopen individual omissions only with evidence |
| 12 | Defer / conditional | R09 / R10 / R11 | Keep remote mutation and broader reuse out of this change | Require an enabled route or measured benefit first |

## 1. R08 — truthful verdicts and current receipts

**Adopt the narrow code repair. No additional model instruction is needed.** The current judge already says a recognized reporter failure overrides exit zero. The parser does not count pytest `error` summaries as failures, and the reuse paths trust saved passed verdicts without requiring current judge semantics.

```text
Before behavior:
  exit 0 + "1 passed, 1 error" → passed
  old false-pass receipt + unchanged tree/command → reused

After behavior:
  recognized failure/error → failed, even at exit 0
  receipt from obsolete judge semantics → rerun; never inherit its pass
```

**Where:** [shiploop_test_counts.py — _pytest: error count omitted from failed tally](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_counts.py:56); [shiploop_test_loop.py — judge](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:655); [shiploop_test_loop.py — _reused](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:1131); [shiploop_test_loop.py — step_proof](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:1394).

**Acceptance:** add real-callback fixtures for mixed pass/error output in focused, check and step-Proof routes; none may advance the action or supply a passed ID to primary acceptance. Replay an obsolete false-pass receipt through candidate and step-Proof reuse; both must execute a fresh check and refuse the bad result. Positive controls: genuine passes, passing titles containing `FAILED`, deliberate negated checks, and current-version unchanged local receipts still behave correctly. Keep zero-tests, missing-ID and test-floor precedence. Cancelled/skipped outcomes remain separate qualifications.

**Keep it simple:** version the existing receipt contract and check that version in both reuse paths. Do not introduce another evidence ledger or ask the model to manually adjudicate runner output. Rejudging old output is an alternative only if the saved capture is complete; rerunning is the simpler safe fallback.

## 2. R05 — inherited procedures must remain possible

**Pilot a narrow fixture first.** The shared procedure walk already checks actor, authority, state transitions and observability. The gap is explicit application at the later end-of-work/person boundary; it is not a need for another general planning checklist.

Current literal end-review opening:

```text
Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input
```

Proposed addition, reusing the shared procedure walk:

```text
For an inherited procedure affected by this change, apply the procedure walk
to its current setup, state, authority and observer. Validate each transition,
including cases added during review; a helper that applies inputs unchecked
is not validation. Repair an invalid procedure or send it back before asking
for its observation.
```

**Where:** [shiploop_prompts.py — PROCEDURE_WALK and planning review focus](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:753); [shiploop_prompts.py — END_REVIEW_FOCUS_HEAD](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:2523); [shiploop_prompts.py — DUTIES[release-verify]: unresolved consumer observations](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:1806). Change the shared walk only for a missing transition rule; add its later consumer only where the fixture demonstrates a gap.

**Acceptance:** use a generic stateful task whose valid earlier procedure becomes invalid after a setup change. The review must identify the first impossible transition, reject any impossible expected result, and keep the required observation open. Include a helper that accepts an illegal transition and a case introduced by the reviewer. Positive control: an unchanged valid procedure remains accepted. Test reviewer behavior on the fixture; a snapshot containing the new sentence is insufficient. If the existing review already passes, retain that evidence and make no prompt edit.

## 3. R07 — preserve required acceptance through partial replies

**Qualify before changing code or prose.** Existing transition and terminal validators already enforce recorded required obligations, and partial-reply tests exist. The open question is continuity when a later revision omits an obligation.

```text
Before: recorded required obligations are gated; omission across a revision
        has not been qualified end to end.
After:  an unanswered required behavior remains open across partial replies,
        stage transitions and revisions; removing its row cannot finish it.
Prompt change: none unless the fixture identifies a missing instruction.
```

**Where:** [shiploop_consumer_delivery.py — validate_transition](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_consumer_delivery.py:657); [shiploop_consumer_delivery.py — validate_terminal](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_consumer_delivery.py:689); [shiploop_primary.py — check_unverified](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_primary.py:141); [shiploop-consumer-delivery.test.py — test_a_partial_person_reply_closes_no_required_behavior_and_the_ask_again_it_names_is_accepted](/Users/dadleet/src/skill-craft/test/shiploop-consumer-delivery.test.py:1317).

**Acceptance:** create one requirement with two observable outcomes; answer only one. Carry the result through an item revision that drops the unanswered obligation. Completion must remain refused, with the unmet requirement still identifiable. A later valid observation can close it; a plan, lower-layer check, lack of reply or ordinary declined observation cannot. A separately authorized change to required scope must retain its existing explicit decision path.

**Keep it simple:** use the current obligation records and validators. Do not introduce another requirement-to-evidence form.

## 4. R21 — do not reuse an observation of changed external state

**Qualify existing reuse, then repair only the demonstrated boundary.** Tree and command equality do not establish target or fixture freshness.

```text
Before source behavior:
  same action/stage/item + command + tree + acceptable floor → reusable
After required behavior:
  changed or unknown relevant external state → execute the check again
Prompt change: none; the script decides whether reuse is valid.
```

**Where:** [shiploop_test_loop.py — _reused](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:1131); [shiploop_test_layers.py — test_layers, targets and criterion confirm contract](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_layers.py:1); [shiploop_test_loop.py — stage_commands](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:329).

**Acceptance:** hold repository, command and action constant while changing a declared target or persistent fixture. The old pass must not satisfy completion. Positive control: an unchanged, demonstrably local check still reuses its current receipt. Cover the effect of an expired authority scope separately; command presence is not authority.

**Keep it simple:** prefer rerunning target-bound/stateful checks when freshness cannot be proved. A comprehensive distributed fingerprint/cache system is not justified by this recommendation.

## 5. R19 — durable loop state, without another recovery system

**Adopt a small launcher repair.** The stage-loop start supplies a receipt but no directory, so the isolated runtime defaults its backing state to temporary storage. The receipt itself does not recreate missing state.

```text
Before command fragment:
  start --receipt RUN/until-loop/A1.json ...
After command fragment:
  start --receipt RUN/until-loop/A1.json --directory RUN/until-loop ...
```

These are illustrative path substitutions, not literal runnable commands. Keep the script-generated arguments and receipt name.

**Where:** [shiploop_loops.py — start_command](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:548); [until_loop_ephemeral.py — start](/Users/dadleet/src/skill-craft/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:949); [until_loop_ephemeral.py — main: receipt chooses isolated path](/Users/dadleet/src/skill-craft/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1278); [until_loop_ephemeral.py — _check_start_receipt: occupied active receipt is refused](/Users/dadleet/src/skill-craft/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:406).

**Acceptance:** start a stage, confirm its backing state is under the run, and resume from a fresh process using the receipt's exact `next_argv`; the same loop advances once. Delete only the isolated fixture's backing state: recovery must remain incomplete, not fabricate success or reset an occupied active receipt. Keep concurrent runs isolated.

**Keep it simple:** reuse the current `--directory` option and recovery receipt. No new recovery prompt, state format or watcher.

## 6. R15 — preserve already-authorized test scope in Improve

**Repair the conflict only for a concrete authorized test route.** A blanket prohibition can contradict the producer's authorized isolated test setup; the correction must not create a new grant.

Current literal opening:

```text
No push, deploy, install or credential access.
```

Proposed replacement:

```text
No push or release effect. Use an already-authorized test route only within
its recorded target, setup and access limits. A recorded command grants no
authority; otherwise no deploy, install or credential access.
```

**Where:** [shiploop_navigator.py — Improve opening authority](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:8626); [shiploop_navigator.py — improve_start_contract](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:8105). Retain the separate release-effect guard in [shiploop_prompts.py](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:2795).

**Acceptance:** render producer and Improve for the same bounded authorized fixture; both preserve its target and limits. Negative controls: identical command with no grant, expired/narrower scope, and a release operation. None gains authority from the prompt or command text. Check emitted text and the actual permitted/refused behavior separately.

## 7. R16 — observe the target instead of requiring absence

**Adopt the wording correction in all four copies.** One observation can report present or absent; it cannot prove discrimination between both states.

Current literal clauses:

```text
release-check runs it once before the real deploy to prove it tells them apart.
... save its "not there yet" output ...
```

Proposed replacement:

```text
Define the check's expected present and absent outcomes. At release-check,
record the current target state, candidate identity and remaining delta.
Validate discrimination with authorized fixtures or independent controls.
Do not alter the target merely to obtain absence.
```

**Where:** [shiploop_prompts.py — DUTIES[release-plan]: one observation claimed to discriminate states](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:1742); [shiploop_prompts.py — DUTIES[release-check]: current target and not-there-yet wording](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:1765); [testing-and-documentation.md — Release-check absence wording](/Users/dadleet/src/skill-craft/skills/shiploop/references/testing-and-documentation.md:173); [salesforce.md — Release-check absence wording](/Users/dadleet/src/skill-craft/skills/shiploop/references/platforms/salesforce.md:54). The platform-card copy is a consistency edit; the core rule is platform neutral.

**Acceptance:** use an authorized already-present candidate, an absent target fixture, and a present-but-wrong-revision fixture. Record each actual state and the remaining work; no fabricated absence or destructive setup. A check accepting both positive and negative controls is refused. No redundant release effect is triggered merely because the candidate already exists.

## 8. R17 — delete the misleading return phrase

**Adopt the deletion.** Existing return output already lists pending review; another instruction would duplicate it.

```text
Before:
  ShipLoop committed these files that were left uncommitted (no action needed):
After:
  ShipLoop committed these files that were left uncommitted:
```

**Where:** [shiploop_protocol.py — plan-return: no-action-needed message before review](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_protocol.py:319); [shiploop_workspace.py — plan_return](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_workspace.py:1322); [shiploop_workspace.py — commit_leftovers](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_workspace.py:1294).

**Acceptance:** leave one product configuration file and one unignored tool-state file. After the local leftover commit, both appear in the existing path review, and any pending decision still blocks return. An excluded file never reaches the target. Positive control: once all required decisions are complete, no added sentence incorrectly claims review is pending.

## 9. R22 — a shorter directive with the existing loop contract

**Pilot the wording-only simplification.** Keep production, Improve and acceptance distinct. Until Loop governs continuation; Improve reviews/repairs the candidate; ShipLoop validates it. A second loop around every duty or consideration adds no demonstrated function.

Current literal `WORK_STEP`:

```text
Implement all of step {step} of this item's plan, anchored in the criteria
that have been stated ({criteria}{serving}) and the design directions that
have been applied ({decisions}), until each criterion assigned to this step
is satisfied and none of the others is broken. Do duty items {items} of
{run}/packets/{action}.md. Write no tests and start no later step.
```

Proposed `WORK_STEP`:

```text
Implement step {step}: satisfy {criteria}{serving} under {decisions}.
Do duty items {items} of {run}/packets/{action}.md.
Write no tests and start no later step.
```

**Keep the bound Exit/Repeat conditions.** They still require evidence after the last edit, preservation of other requirements, no later-step work, passing Proof and lint, and the existing blocked/send-back/pause rules. Improve still stops on its first trivial review. Do not replace these with “until every delivery item is anchored”: a source location does not demonstrate behavior, and a step must not consume later steps' delivery obligations.

**Where:** [shiploop_loops.py — WORK_STEP](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:95); [shiploop_loops.py — REPEAT_STEP](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:146); [shiploop_loops.py — step_anchors](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:192); [shiploop_navigator.py — step_block](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:6854); [shiploop_navigator.py — IMPROVE_TRIVIAL_REVIEWS = 1](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:8102).

**Acceptance:** render inline head, full packet and Improve handoff for a multi-step item. The same step, C/R/AD bindings, exact proof, review base, authority and recovery locators must survive. A current-step proof cannot require later work; a repair that breaks it must fail re-proof. Preserve the separate whole-plan ask-agent route and test-stage ownership. Compare representative behavior before/after, then actual tokens and elapsed time; source-length reduction alone is not acceptance.

The proposed `WORK_STEP` template is 161 characters versus 364 (55.8% shorter). That measures only this template, not the whole prompt, tokens, performance or quality.

## 10. R01/R13 — fewer repeated fields, no missing context

**Clarify the inline/worker distinction; qualify before adding a gate.** Item paths are required. Per-step paths are optional in the schema and unused by inline execution, although the producer prompt currently asks for them. The 4-criteria/3-product-file rule is guidance, not a script cardinality limit.

```text
Before literal clause:
  Its `paths` (inside the item's) name every file it changes.
Proposed replacement:
  The item's `paths` name its changed files. On the ask-agent route, each
  step also declares the paths its worker owns.
```

**Where:** [shiploop_prompts.py — DUTIES[step-plan]: proof and criterion confirmation](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:1259); [shiploop_navigator.py — _normalise_steps: optional per-step paths](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2550); [shiploop_navigator.py — step-plan submit gate: required item paths](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2636); [shiploop_navigator.py — step_block](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:6854); [shiploop_navigator.py — PRINT_LIMIT, HEAD_LIMIT and HEAD_REQUIRED_END](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:1935); [shiploop_navigator.py — _check_producer_bounds](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3139). Preserve a per-step field when a real consumer needs it; this proposal does not remove the existing schema field.

**Acceptance:** inline execution without per-step paths still preserves item scope and all criteria/proof data; worker delegation retains ownership paths. Use long installed paths and multibyte text near current packet bounds: the full active assignment, exact callback and referenced locators remain accessible. Positive control: ordinary small packets stay concise. Do not add a second packet format or opaque symbol language.

## Deferred and conditional items

| IDs | Before → proposed handling now | Reopen only when | Source |
|---|---|---|---|
| R04 | Fourteen shared Code craft rules → retain them; no blanket expansion. CC3 complex-unit explanation, CC6 release-on-exit and CC9 composable-unit additions remain proposals. | A concrete defect survives the existing rule; add only the sentence needed and qualify it against that defect plus a good control. | [shiploop_prompts.py — CODE_CRAFT: fourteen rules](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:611); [implement-guidance.md — Considerations and Evidence](/Users/dadleet/src/skill-craft/skills/shiploop/references/implement-guidance.md:1) |
| R09 | Local mutation excludes remote routes → retain exclusion. | An explicitly authorized remote mutation path exists; then interrupted, failed and successful runs must all restore the accepted target state before enabling it. | [shiploop_mutation.py — split_remote](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_mutation.py:100); [shiploop_mutation.py — _remote_reason](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_mutation.py:112) |
| R10 | Base/mutation execution → keep current behavior. | Representative measured cost justifies reuse, and changed code, tests, target/fixture state and judge semantics all invalidate it correctly. | [README.md — Measured reuse deferral and built genericity fixes](/Users/dadleet/src/skill-craft/docs/experiments/shiploop-deepseek-review-20261024/README.md:65); [shiploop_test_loop.py — _base_run](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:1738) |
| R11 | Narrow repair with explicit prior step/result → retain it; no prefix cache. | An unchanged-prefix fixture proves reuse preserves exact definitions, scope and fresh relevant proof. A changed prerequisite must reopen its dependents. | [shiploop_navigator.py — _step_revisit_line](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:823); [shiploop_navigator.py — implement_progress](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2611) |

The separate [Improve scheduling proposal](/Users/dadleet/src/skill-craft/docs/shiploop-improve-schedule-proposal-2026-10-25.md:195) remains unbuilt and awaiting approval. Count result-only edits before using edit rates to change scheduling. Keep proposed review-skipping in shadow mode, preserve spec/test-spec coverage, and treat its mutant-disposition proposal as separate work. It does not supersede the current first-trivial rule or authorize dropping reviews here.

## Simplification rules that retain functionality

| Use one existing mechanism | Remove or avoid | Must remain observable |
|---|---|---|
| Shared Step block on every surface | Repeated assignment prose and a new symbolic DSL | Active task, criterion text/IDs, requirement/design links, exact proof, current scope |
| Bound Exit/Repeat contract | Another “until complete” clause in Work or a loop around each consideration | Regression protection, after-edit proof, no later work, honest blocked/send-back/pause |
| Current receipts and callbacks | A second evidence form, manual tallying or a parallel state ledger | Current action/candidate/judge identity and actual check outcome |
| Existing path-review output | “No action needed” and duplicate reminders | Every outstanding keep/exclude decision |
| Current applicability guide and platform cards | A universal UI/deployment checklist for every package | Only obligations the accepted package actually has |
| Conservative reruns at uncertain external boundaries | A new distributed cache before measuring benefit | Fresh target/fixture observations |

This follows the distinction between minimal and underspecified instructions: remove repetition, retain the information needed to act. Primary guidance supports starting with simple composable workflows while warning that a short prompt can still omit essential context. [Building effective agents](https://www.anthropic.com/research/building-effective-agents) and [Effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents). The local defects and acceptance fixtures above, not those general articles, determine which changes are warranted.

## One generic acceptance matrix

Use the same loop with different accepted criteria and proof commands. These are proposed fixtures, not completed package qualification.

| Package | Example criterion | Suitable observation |
|---|---|---|
| Library | Reject invalid input without modifying the input | Called API, returned/error value and unchanged input |
| CLI | Invalid option produces the specified failure and no output artifact | Exit, stderr and filesystem observation |
| Service | Repeated request does not repeat its committed effect | Response plus persistent-state observation |
| UI | A stale asynchronous reply cannot replace newer state | Interaction through the intended UI with controlled reply order |
| Data/config/docs | The delivered content satisfies its declared consumer contract | Schema/value check, actual consuming tool or rendered/example behavior as applicable |

For each fixture, prove current-step behavior and a negative control, then verify an unrelated required behavior remains intact. Later consumer observations stay open until their actual due stage. Source inspection counts only where the requirement itself is about source or documentation structure.

No source implementation changed in this review. Source locations, literal excerpts and links were structurally checked; visual rendering was not inspected. The earlier 716 passing tests qualify their recorded snapshot, not these proposed future changes.
