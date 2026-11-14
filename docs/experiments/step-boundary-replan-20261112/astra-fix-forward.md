**Fix-forward is sound for ShipLoop. I recommend implementing a guarded pilot, but the draft is not yet a complete retention contract.** Preserve completed steps as historical executions, amend unfinished work, and add corrective work when necessary. Preserve testing obligations separately: an earlier completion must never become immunity from regression testing or evidence that a newly discovered defect is resolved.

The strongest reasons to proceed are the unnecessary replay demonstrated by the code and the mostly unchanged completed prefixes in the retained runs. The remaining risks concern evidence ownership, amendment baselines, and advancement—not a fundamental need to repeat completed implementation.

I inspected the first review, source, relevant commit messages, measurement scripts and retained results. The checkout is now `c5c59da6d44d664568d1afb5d750f56af308c764`; its difference from requested `3d42222e2e1783e64bf78b2d2760ca7ff92a7538` is documentation only. ShipLoop source is identical. No files were changed, test suites executed or live runs launched. Read-only calculations and direct probes of the pure projection functions were performed.

**The measurements support the direction, with several important corrections.**

| Claim | Verified interpretation |
|---|---|
| 81 send-backs followed by an accepted plan | Correct. There are 82 inner send-backs with a preceding plan; one has no subsequent accepted replan. |
| 73 before any documented step; 8 after | Correct **within the current plan revision**. Across the item’s full history, the split is **72 before any documentation; 9 after**. |
| 1 done-row change; 48 later-only; 32 no-row changes | Reproduces exactly under the script’s definition. It compares four fields by position, not complete step identity or retained ancestry. |
| In 32, only item-wide fields changed | Slightly overstated. In **two**, only `summary` and `evidence_refs` changed; criteria, commands, expectations and paths were also unchanged. |
| Six of eight late cases leave completed work’s listed contracts unchanged | Confirmed for the examined rows, criteria and command associations. Additional comparison of test-spec cases found no completed-case changes in seven of the eight; gym is the exception. |

The ancestry correction matters to the design. Both scripts reset `documented` on every accepted plan. In p0-terra’s **second** amendment, previously documented S1’s C2 and Proof become stronger, but that transition enters the “later-only” bucket because the first amendment reset the counter. The new Proof adds empty-value and line-three assertions. [fixforward.py — comparison and reset](/Users/dadleet/src/skill-craft/docs/experiments/step-boundary-replan-20261112/fixforward.py:50), [p0 first amended Proof](/Users/dadleet/e2e-runs/20261030/p0-terra-ask-agent-55bfcd/.shiploop-runs/seed/run/results/nav-22ffe6e240574302801b29bbc993400a.md:124), [p0 second amended Proof](/Users/dadleet/e2e-runs/20261030/p0-terra-ask-agent-55bfcd/.shiploop-runs/seed/run/results/nav-c10b026f8d07492eb0b335ec65931936.md:129).

The two plans changing only narrative/evidence are [csv-report-s2](/Users/dadleet/e2e-runs-sp/20261101/csv-report-s2/.shiploop-runs/work-20261101-150740-e90b5a/run/results/nav-cec32bdcdf3945b4977923b2e380d56c.md:77) and [P-ticket-import-s2](/Users/dadleet/e2e-runs-xr/20261031/P-ticket-import-s2/.shiploop-runs/work-20261031-230254-d42cae/run/results/nav-30c4e208bda04e9c80960d7e24117e5d.md:220). The latter still requests a substantive test-spec correction. “No plan-row change” therefore does not mean “no useful corrective work.”

Two methodological limits remain:

- `row()` omits `id`, `deps` and `skills`. My additional comparison found no changes to those omitted fields in the eight late completed prefixes, but the function is not a general retention validator. [fixforward.py — compared fields](/Users/dadleet/src/skill-craft/docs/experiments/step-boundary-replan-20261112/fixforward.py:21).
- `fixforward_detail.py` does not actually map command test IDs through test-spec cases; it intersects them directly with criterion IDs. An independent mapping confirmed the six-of-eight finding here, but the script would miss other possible associations. [fixforward_detail.py — `touches`](/Users/dadleet/src/skill-craft/docs/experiments/step-boundary-replan-20261112/fixforward_detail.py:30).

Thus the data establishes a concrete replay problem. It does not establish a measured quality improvement or the time fix-forward would save.

**Gym does not demonstrate that replay was necessary to repair completed S1.**

The original plan has:

- S1: backend Apex behavior and contract searches.
- S2: browser UI journeys.

The replacement plan does not combine both sets of obligations. It acknowledges the deployed backend and 13 passing Apex tests, replaces the plan with UI diagnostic work renumbered S1/C1, and leaves Apex verification to the system stage. [Original gym steps](/Users/dadleet/e2e-runs/2026-10-31/shiploop-gym-salesforce-91y7tnl1/gym-published-baseline-01/.shiploop-runs/work-20261031-104327-2692a2/run/results/nav-1d3296014de74b6785c58de950ff674a.md:134), [replacement plan and summary](/Users/dadleet/e2e-runs/2026-10-31/shiploop-gym-salesforce-91y7tnl1/gym-published-baseline-01/.shiploop-runs/work-20261031-104327-2692a2/run/results/nav-c7ab7e8ebc72472abb9999cb53ee91df.md:128).

That diagnostic implementation subsequently reports **blocked**: `gym-ui` still returns `controller-response-invalid`, and the checker exposes insufficient diagnostic information. No successful correction is recorded. [Gym’s subsequent blocked result](/Users/dadleet/e2e-runs/2026-10-31/shiploop-gym-salesforce-91y7tnl1/gym-published-baseline-01/.shiploop-runs/work-20261031-104327-2692a2/run/results/nav-14eae8522a8247a5bbc5a2d426fd0584.md:8).

Fix-forward should retain backend S1, amend pending S2 to perform that diagnosis, preserve the UI acceptance obligation, and block if the same external diagnostic limitation remains. Only if diagnosis establishes a defect in completed backend work should it create a corrective step.

That is not demonstrably worse than the observed route. It gives clearer provenance and avoids repurposing S1/C1. Whether it ultimately fixes the UI remains unknown.

**Rules 1–5 address the six hazards unevenly.**

| Hazard | What the draft closes | What remains |
|---|---|---|
| Same-ID oracle changes | Rule 3 states the right prohibition for completed cases. | Enforce it when accepting the new **test-spec**, including criterion, requirement, oracle, RED, GREEN and mock fields. A frozen plan cannot validate a case authored afterward. [Case canonicalization](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_expectations.py:475). |
| `case_step` moves an old criterion | Not closed. New test IDs alone do not establish ownership. | A new step listing C1 moves **every C1 case** to that step under the current last-listing rule. [case_step/new_cases](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_iteration.py:150). |
| Three cursor readers | Rule 4 describes the desired outcome. | All three independently count implementations after the latest plan. They need one shared execution projection. [implement_progress](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2731), [step_number](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:493), [current_step](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:313). |
| Retained plan becomes the final plan | Rule 5 identifies the missing check. | Closure needs a durable, candidate-bound result, a failure route and a dirty-work check. It must not fabricate another completed step. [active_commands](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_iteration.py:198). |
| Replayed commits absorb unfinished work | Avoiding replay removes the misleading new S1 execution. | Dirty work must remain inside the resumed step’s diff, tests, review and commit scope—including when pending work is reordered or removed. [_iteration_base](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:4583), [_commit_stage](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3197). |
| Provenance and recovery | Rule 4 promises retention. | Original action/plan/receipt identities, obligations, counts and transactional advancement still need an explicit contract. Existing receipts cannot simply become receipts for a new plan. [Receipt comparison](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_loops.py:671), [commit records](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3088). |

I reproduced the ownership hazard directly: adding S3/C1 while leaving S1’s row unchanged moves TC-1 from S1 to S3, removes it from S2’s due cases, and makes it “new” at S3. Rules 1 and 3, as written, permit that transformation.

**I would make these changes to the rules before building them.**

1. **Freeze completed execution records; distinguish them from current obligations.**

   A completed step means its final accepted document result, after the applicable Improve review and commit transition—not an implement result or a terminal document-loop receipt. Pending review results are not yet accepted history. Preserve legitimate no-change completion explicitly; accepted document history does not invariably imply a new Git commit. [_apply/Improve acceptance](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:4283), [_commit_stage exceptions](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3223).

   Copy retained canonical rows mechanically instead of asking the planner to reproduce them. Preserve the entire row and its source-plan identity.

   A later finding may challenge the sufficiency of that historical evidence without erasing it. Record the finding and corrective obligation. Item completion remains unavailable until the correction and required revalidation succeed.

2. **Freeze case ownership as well as case definitions.**

   For the smallest implementation, keep `case_step`’s existing algorithm but reject amendments that change the effective owner of a retained case.

   Give corrective work **new criterion IDs as well as new case IDs**, tied to the same unchanged requirement where appropriate. For example, S3/C7/TC-9 can prove a newly exposed R-1 boundary failure without moving S1/C1/TC-1.

   This avoids adding a new case-to-step schema immediately. If you want later steps to reuse old criterion IDs while assigning cases independently, explicit case ownership becomes necessary.

3. **Replace “only what changed reruns” with “only unfinished work re-enters implementation.”**

   New or changed case specifications can be authored incrementally. The stored current test-spec should still be a complete, validated catalog assembled from retained cases plus the amendment.

   Subsequent steps must continue running earlier cases and minimum regression. The final candidate must satisfy full regression and deferred checks. This preserves the deliberate existing cadence: earlier cases at every step, exhaustive regression at the last. [due_cases/active_commands](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_iteration.py:171).

   Also invalidate prior **unfinished-step** receipts when the amendment changes their contract. Keeping edits does not keep an obsolete implement/test acceptance.

4. **Protect shared commands and allow explicit evidence corrections.**

   Freezing commands that confirm *only* completed criteria leaves a hole: a mixed command can stop checking completed behavior while its pending portion changes.

   Preserve the retained obligation’s effective command coverage, registered tests and compatible count floor. Changes to command text, selectors, target, suite or scope need an explicit disposition and fresh verification where applicability changes.

   Conversely, an invalid historical command cannot remain mandatory forever merely because it is frozen. Permit an append-only correction or supersession record, with rationale and replacement evidence. Do not rewrite the old execution or silently transfer its pass/count to the replacement.

   P0’s first amendment is a useful control: its unchanged search command covers both C3 and C6 and changes `focused` to `check`; the original document says that combined command awaits S2. This is not evidence that an already executed S1 suite was rerun under a new label. [Old command](/Users/dadleet/e2e-runs/20261030/p0-terra-ask-agent-55bfcd/.shiploop-runs/seed/run/results/nav-49a22f541c1b4ca4af8b7e062965166d.md:160), [S1 document](/Users/dadleet/e2e-runs/20261030/p0-terra-ask-agent-55bfcd/.shiploop-runs/seed/run/results/nav-d714aa0cceeb406a9e9fa7bcb4160b2a.md:16).

5. **Make the amendment baseline explicit, and preserve dirty-work ownership.**

   Record the committed frontier against which the pending work is now planned. Run pending expectations against that named base, separately from the dirty candidate. Preserve prior expectation observations with their original bases.

   Check **all expectations applicable to the remaining work whose applicability changed**, not merely rows newly added to JSON. A previously “absent” path may now exist because a retained step created it.

   This requires more than changing `validate-existing.entry`: `check_step_plan` also validates expectation states against the recorded lint base. Both must agree about the amendment base. [Plan expectation gate](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_expectations.py:386), [check_place/_run_at](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_expectations.py:781).

   Retain unfinished edits outside that baseline. If a corrective step is inserted before the interrupted step, every existing dirty change needs an explicit execution owner; otherwise the corrective commit can absorb unrelated pending work just as replay does today.

6. **Allocate fresh IDs; schedule by dependencies.**

   “IDs only grow” should mean no renumbering or reuse, including IDs removed by earlier amendments. Allocation order need not equal execution order: `[S1 completed, S3 correction, S2 pending]` is valid when S2 needs the correction.

   Today IDs are arbitrary unique text, and dependencies must name earlier list entries. Numeric monotonicity is not the current schema. [_normalise_steps](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2670).

   Removing a step must also account for its required criteria, cases, assumptions and dependent work. Removing rows cannot itself discharge the obligations they represented.

7. **Make closure and the document boundary explicit transitions.**

   Zero pending steps may enter closure only when no unfinished product edits or corrective obligations remain. The closure result must identify the active plan/spec, candidate/base and command contracts, and record the applicable final checks. Failure returns to amendment/corrective work, or blocks when an external prerequisite is genuinely required.

   Do not simulate closure by reissuing document for the last retained step: current commit attribution selects the latest implement action and would misrepresent the execution. [_commit_stage attribution](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:3244).

   For your boundary question, allow **document/done plus a pending amendment request** when the current step can truthfully complete. Its existing Improve review can reconcile the request; commit the step first, then process the amendment before starting another step. If the current step cannot satisfy its own contract, only earlier completed steps are retained.

   Preserve the existing automatic N/A document behavior. Do not add a compulsory model action to those boundaries. [_document_entry](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:4701).

Rule 6 also needs a wording correction: carry-forward’s incompatible-findings rule includes a changed **completed-work assumption**. Furthermore, blocked routing is not already uniform: the current document prompt still directs a changed requirement intent to send-back. Align that explicitly. Distinguish a defect violating an unchanged requirement, which can be corrected, from a change to the requirement or authority itself. [carry-forward incompatibilities](/Users/dadleet/src/skill-craft/skills/shiploop/references/carry-forward.md:81), [document’s current instruction](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py:1533).

**Use one authoritative item-execution projection, with several small adapters.**

The projection should derive the ordered active plan, retained completed prefix, original source actions for each retained step, current unfinished step, and amendment lineage. A root-aware validation layer checks the referenced commit and receipt artifacts. That is one execution decision with separate validation—not several independent cursor calculations.

Keep original events and append corrections. This matches the ordinary compensating-event approach; it does not require a new storage system alongside ShipLoop’s existing history. [Microsoft’s event-sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing).

| Area | Smallest coherent change |
|---|---|
| `planning_revision.current_actions`, `step_actions` | Derive inner currentness from the shared item projection. Retain original completed actions while excluding abandoned unfinished attempts. Keep global planning reconciliation behavior. |
| `implement_progress`, `test_loop.step_number`, `loops.current_step` | Become adapters over the same projected step and stage. Do not independently add a retained-prefix count. |
| `step_view`, `_previous_step_results`, packet result labels | Select actions by explicit provenance. Both currently associate actions with plan positions; abandoned attempts make count-only fixes unsafe. |
| `_step_plan`, `_test_cases` readers | Use the same active plan and complete current case catalog. Existing helpers independently search raw history. |
| `case_step`, `new_cases`, `due_cases` | Can retain their algorithms initially **if** amendment acceptance freezes retained ownership and corrective work uses fresh criteria. |
| `registered`, `accepted_counts`, `floor_detail`, assumptions/handoffs | Carry retained obligations exactly once. Preserve compatible counts and review-added tests; explicitly account for superseded commands. |
| `expectations.check_step_plan`, `entry`, `_run_at`, `check_complete` | Use the amendment’s named baseline and pending expectation scope; preserve dirty edits and historical observations. |
| `stage_spec`, `_canonical_result`, `_apply_result`, loop receipt routing | Add a distinguishable inner amendment event/mode. Preserve historical send-back semantics and outer send-backs. Support successful-document amendment requests separately from failed-stage requests. |
| `_first_item_review`, step-plan/test-spec packets | Treat amendments under the existing planning-review policy; show fixed source records, pending work, dirty-work ownership, requested changes and fresh-ID constraints. |
| Iteration/commit bookkeeping and `check.answer_key` | Preserve original identities; create fresh unfinished-step identities; bind amendment/closure evidence into transactional saves and cache invalidation. |

Several non-obvious consumers are important:

- `step_view` currently zips steps with the last implementation rows; `_previous_step_results` starts positional association anew at each plan. Both require provenance, not a larger counter. [step_view](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:7530), [_previous_step_results](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:846).
- `assumptions.open_items` first iterates `current_actions`, then reads `step_actions`. Updating only the latter still loses retained document obligations. [open_items](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_assumptions.py:197).
- Counts and review-added registrations are keyed by command string. Changed text can lose evidence; unchanged text with changed meaning can inherit inappropriate evidence. [registered](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:431), [accepted_counts](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_test_loop.py:1069).
- Changing the outcome name without updating `_first_item_review` would bypass the existing amended-plan review rule for later items. [_first_item_review](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:510).

The existing per-step implementation/test/document/Improve cycle, command execution machinery, RED/mutation checks and commit recovery primitive can remain. Their selected inputs change. Both inline and ask-agent routes already have per-step boundaries and need equivalent coverage. [Ask-agent lifecycle regression](/Users/dadleet/src/skill-craft/test/shiploop-navigator-contract.test.py:4483).

Preserve the decisions recorded in `b55909179b89bfc63bba67d4cdbb833c700df147`—cumulative floors, registered review tests and aggregate obligations—and `b385df5d7005de79e2522de308b3feb57b397716`—minimum regression each step, exhaustive regression at the last. Fix-forward should not accidentally undo either.

**Before shipping, require these negative controls.**

| Control | Required outcome |
|---|---|
| Identical amendment after completed S1 | S1’s original actions/commit remain selected; the next packet, loop contract, Proof and test cursor all identify S2. |
| Two consecutive amendments before another completion | Retained S1 survives both. Attempts to edit it are detected—the p0 ancestry case. |
| Same-ID case definition change | Rejected for retained evidence; correction requires a fresh identity or explicit supersession. Include changes to RED, requirement and mock, not only oracle. |
| Add an old criterion to a new step | Cannot move a retained case, remove it from interim regression or make it “new” again. |
| Mixed command drops an old case | Rejected or explicitly corrected with preserved coverage; include changed command text, selectors, target and suite. |
| Review-added test and open assumption from S1 | Both remain visible and binding after amendment; counts are neither reset nor double-added. |
| Dirty interrupted S2, including edits to an S1 file | Edits remain in the resumed/corrective step’s diff and gates. No completed-step commit absorbs them. |
| Remove every pending step | Required work cannot disappear; dirty product changes prevent closure; full regression/deferred checks run, and failure cannot reach carry-forward. |
| Successful document proposes amendment | Review and commit finish once before amendment. A failed current step cannot use this route to claim completion. |
| Crash and retry around amendment/commit/closure | Recovery selects the same source evidence and next step; no duplicate commit, stale receipt import or cached acceptance. |
| Compatibility controls | Both execution routes, N/A/no-change steps, unavailable/non-Git commit evidence, old send-back histories, outer send-backs and planning-review modes remain truthful. |

Extend the existing [step-edge tests](/Users/dadleet/src/skill-craft/test/shiploop-step-edges.test.py:98), [iteration tests](/Users/dadleet/src/skill-craft/test/shiploop-iteration.test.py:196), [count-floor tests](/Users/dadleet/src/skill-craft/test/shiploop-test-loop.test.py:3648), [aggregate handoff tests](/Users/dadleet/src/skill-craft/test/shiploop-handoff.test.py:2117) and [commit-recovery tests](/Users/dadleet/src/skill-craft/test/shiploop-navigator-contract.test.py:4534). Preserve legacy replay tests where they describe legacy events; add amendment-specific expectations instead of globally changing their meaning.

The cheapest useful live check is one isolated, local, two-step item:

1. Complete and commit S1 through the real gates.
2. Let S2 make actual uncommitted changes, then encounter a deliberately incorrect Proof command.
3. Have the real amendment flow repair the Proof and continue S2.
4. Verify that no S1 execution was recreated, S2 retained its edits and correct base, earlier tests still ran, and final regression/commit/carry-forward completed.

Use the same model and effort in any comparison arm. Measure actual actions, tokens and elapsed time; one successful continuation establishes viability, not a general savings claim. A tiny separate closure fixture can exercise zero-pending failure without another model run.

**Build in this order:**

1. Define completion, immutable identity, supersession, amendment baseline and closure contracts.
2. Add the pure history projection and adversarial fixtures, especially repeated amendments and abandoned unfinished actions.
3. Move all cursor, action-selection and obligation consumers onto it while preserving existing behavior.
4. Add amendment validation, complete test-spec materialization and baseline handling.
5. Wire routing, packets, existing review policy and the successful-document amendment request.
6. Add transactional closure, recovery and cache-binding coverage.
7. Run the focused suites, the local live continuation, independent review, and repository-required release qualification.

The owner’s direction is implementable. The essential qualification is: **completed executions stay fixed; unresolved obligations and verification continue moving forward.**