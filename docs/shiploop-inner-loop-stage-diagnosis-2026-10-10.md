# ShipLoop inner loop: what each stage is for, and which stages earn their place (2026-10-10)

Status: **proposal**, for an owner decision. Nothing here is implemented.

Owner questions, 2026-10-10:
- Do we need baseline?
- Why are test-red and test-green separate stages, when red and green could be judged inside test-author?
- What is test-refine for? It reads like "after implement, run the tests and fix the code or the tests until both
  work".
- Why is static-checks separate?
- For every stage: its role, its purpose, how it differs from the others, and how it hands results on.

Sources:
- the stage table, `skills/shiploop/scripts/shiploop_stage_spec.py` (goal, done-when, the gates `complete_runs`,
  `reads`);
- the gate texts (`_CHECK_TEXT` in `shiploop_navigator.py`);
- four live step slices of 2026-10-10 (Claude Sonnet 5.5, inline, node fixture; the median figures below;
  evidence in `test/shiploop_e2e/evidence/step-slices-2026-10-10.json`).

## Stage by stage

"Gate" is what ShipLoop runs or checks by script before it accepts `done`. "Read by" is the later stages whose
packets list this stage's result. Time and turns are medians over four runs.

| Stage | Role and purpose | Gate | Reads, and read by | Live cost | Finding |
|---|---|---|---|---|---|
| get-next-work-item | Confirm the item is still the right next one; its prerequisites are done | none (ShipLoop records the lint base) | reads spec and plan; read by none | seeded in the slices | A check whose first half the script already knows (prerequisites accepted). The second half, "still required", is a judgement step-plan makes anyway. |
| **step-plan** | Turn the item into ordered steps, criteria, test commands and paths | Shape checks (commands, criteria, deps, paths; new: step sizing) + an Improve review | reads spec, test-strategy, plan, prepare; read by 9 stages | 47 s, 15 turns | **The core plan of the item. Keep.** |
| **test-spec** | Specify the test cases before code: one per criterion, each with an oracle and a RED/GREEN definition | knowledge-home close (the test-spec file) + an Improve review | reads spec, test-strategy, plan, step-plan; read by 7 stages | 30 s, 9 turns | **Keep.** |
| baseline | Run the recorded commands on the unchanged base; classify the failures that already exist | **none**: the model's own report | read by regression only | 6 s, 2 turns | **No gate reads its result.** Regression refuses every failing command, whatever baseline recorded. The run is not script-checked, and its only consumer ignores it. |
| test-author | Write the tests the spec calls for | test-probe: runs the focused commands once and refuses unless a test ran | read by test-red | 6 s, 2 turns | **Write the failing tests, but RED is checked one stage later.** |
| test-red | Run the new tests and confirm they fail for the right reason | test-red: runs the focused commands and refuses unless they fail inside a test | read by none | 5 s, 1 turn | **Runs the same commands test-author's gate just ran**, with the opposite expectation. "Do not edit product code" is prose only. 1 turn in every run. |
| **implement** | Make the planned change, one step at a time | lint gate | reads spec, plan, step-plan, test-spec; read by 5 stages | 6 s, 3 turns per step | **Keep.** |
| test-green | Loop on the focused commands until they pass | lint gate + test loop (Until Loop terminal packet, then ShipLoop reruns them) | read by verify | 20 s, 7 turns | **The real "make it work" loop**, but over the focused commands only. |
| test-refine | "Tighten the tests against the actual implementation" | test-rerun: reruns every recorded command | read by none | 6 s, 2 turns | **Unclear purpose** (the owner's reading). In practice it reruns everything and the model adds a test or does nothing. "Tighten weak assertions" belongs in test-author (write tight tests) or in a review. |
| regression | Rerun the retained suites; fix the code, not the checks | lint gate + test loop over every recorded command | reads test-strategy, baseline; read by verify | 12 s, 3 turns | **The same loop as test-green**, widened from focused to all commands. |
| static-checks | Formatting, lint, type and build checks, plus tracing each changed entry point | quality loop terminal packet + rerun every recorded command | read by verify | 16 s, 6 turns | The name hides the purpose. It is a **code-quality review loop** (code craft, entry points), not just "static" tools: the lint gate already ran at implement, test-green and regression. |
| document | Update the documentation the change affects | none | read by none | 6 s, 2 turns | **Keep, conditional** on a changed public behaviour. |
| skill-assess | Decide whether a reusable skill or helper change is warranted | none | read by skill-validate | 6 s, 2 turns | **Almost always "not applicable"**: one sentence, then the model submits. In the live runs it was done through a self-written shell function. |
| skill-validate | Validate a changed skill on real input | none | read by none | 4 s, 1 turn | Applies only when skill-assess said yes; otherwise N/A. |
| **verify** | Confirm every criterion on the current candidate, with evidence after the last edit | test-rerun | reads 8 stages; read by integrate | 6 s, 1 turn | **Keep.** Its 1 turn says the evidence already exists by then: it mostly rubber-stamps reruns that just happened. |
| integrate | Assemble the item in the execution checkout | none | read by integration-verify | 4 s, 1 turn | **Inline, one worktree: a no-op.** The candidate is already assembled where implement wrote it. |
| integration-verify | Rerun on the integrated result; check shared interfaces | test-rerun | read by carry-forward | 5 s, 2 turns | **Inline, one worktree: a repeat of verify's rerun** on the same tree. |
| **carry-forward** | Record lessons, revise the queue; the last item's end-of-work review | the end Improve review | read by none | 19 s, 6 turns | **Keep.** |

Two numbers frame this:
- **One item's inner loop has 17 stages.** In the live runs, 9 of them took 1-2 turns: baseline, test-author,
  test-red, test-refine, skill-assess, skill-validate, verify, integrate and integration-verify. Each costs a full
  packet, a result file and a callback.
- **The recorded commands are rerun about six times** after implement: test-green, test-refine, regression,
  static-checks, verify and integration-verify. On a large suite that is the dominant cost of an item.

## The owner's questions, answered

1. **Baseline: not as a model stage.** No gate reads its result. Regression refuses any failing command whatever
   baseline said, and baseline itself is not script-checked. If a before-state matters (to tell an old failure
   from a new one), ShipLoop should run the recorded commands on the unchanged base itself when step-plan is
   accepted, and record the exit codes. That is a script fact, with no model turn.
2. **Test-red: fold into test-author.** test-author's gate already runs the focused commands. Make that one run
   require "a test ran AND failed inside a test" (RED, or `red_na` for characterisation tests). One stage then
   writes the failing tests and proves they fail for the right reason. "No product edits before RED" becomes a
   script check: no product path changed since the item's lint base.
3. **Test-green, test-refine and regression: one post-implement goal.** This is the owner's "execute the tests and
   fix the code or the tests until both are functioning properly": **one stage, one Until Loop**.
   - It loops over *all* recorded commands (focused and regression) until each passes.
   - Fix the code. Change a test only for an independent, recorded reason; never weaken an assertion.
   - Its gate: ShipLoop reruns every command, with the test-count floor (a removed or newly skipped test is
     refused).
   - It is a single goal: "the code behaves as the tests define, or iterate until it does".
   - test-refine's "tighten weak assertions" moves to test-author (write tight tests) and to verify's review.
4. **Static-checks: keep the quality loop, merge its tools.** Lint, type and build commands become `check`-suite
   commands in the same loop as the tests, so one loop ends only when tests and static tools all pass. The
   code-craft review (trace each changed entry point with a valid, a boundary and an invalid input) is a review
   of the candidate. It belongs in verify, which today takes 1 turn because nothing is left for it to do.
5. **Smaller cuts.**
   - skill-assess and skill-validate become one conditional stage, issued only when the step plan declares a skill
     or helper path (ShipLoop already classifies paths, `item_scope.skill_surface`).
   - integrate and integration-verify collapse into verify on the inline route, where nothing is assembled; they
     stay for chained or parallel work, where assembly is real.
   - get-next-work-item becomes a script check (prerequisites accepted), with "still required" asked in step-plan.

## Proposed inner loop

**9 stages, from 17.** Each restates its own purpose, operation and check (S-6).

| Stage | Role | Gate | Hands on |
|---|---|---|---|
| step-plan | Steps (behaviour-sized), criteria, test commands (focused, regression, check), paths; confirms the item is still required | shape and sizing checks; Improve review | steps, criteria, commands, paths |
| test-spec | Cases per criterion, each with an oracle and RED/GREEN | test-spec file; Improve review | the cases, with IDs |
| test-author | Write the cases as tests, tight from the start; prove they fail for the right reason | focused commands run and fail inside a test (or `red_na`); no product path changed | failing tests |
| implement (per step) | Make the step's change against its criteria | lint gate | the candidate |
| test-pass | One Until Loop: every recorded command (tests, lint, type, build) passes; fix code, change a test only for a recorded reason | ShipLoop reruns all, with the test-count floor | a green candidate |
| document | Changed public behaviour documented (conditional) | none (as today) | docs |
| skills | Reusable skill or helper change validated (only when declared) | none (as today) | skill evidence |
| verify | Each criterion confirmed with evidence after the last edit; review the candidate (entry points, code craft); on chained work, assemble and check shared interfaces | rerun all (once) | the verified item |
| carry-forward | Lessons, queue revision; end-of-work review on the last item | Improve review | the queue, the knowledge home |

What changes for the run:
- 8 fewer packets, results and callbacks per item.
- Recorded commands rerun about 2 times instead of 6: test-pass and verify.
- A "make it work" step the model can treat as one goal.

What does not change:
- the Improve reviews (planning stages, end of work);
- the knowledge home and its closes;
- the outer stages.

## Costs and risks

- **It is a graph change, not a packet change.** It touches the stage table, the navigator's graph, the test-loop
  and quality-loop contracts, item_scope's skip rules, the progress view, the Run Review exporter, the E2E harness
  stage lists and most ShipLoop suites. It needs a SPEC note (S-9/S-10: which checks prove which stage), a
  clear-the-context probe on the merged stages (S-6), and the fork's and E2E's review.
- **Ordering with the packet re-cut.** Merging stages first means re-cutting 9 inner packets instead of 17. So the
  graph change should land **before** the re-cut, or the re-cut is done twice.
- **What the separate stages bought** and the merged ones must keep:
  - test-red's "fail for the right reason" (kept as test-author's gate);
  - regression's "the old suites still pass" (kept: the one loop runs them);
  - static-checks' quality loop exit on "only trivial findings" (kept as part of verify's review, or as a second
    exit condition on test-pass);
  - integration on chained/parallel work (kept on that route).
- **Evidence still missing.** The live runs are one host, inline, small node items. On a large suite, or with
  parallel steps, test-refine and integration-verify may do more than here. Before the graph change ships, a
  probe on a larger case (the Checkers or Battleship examples, judged for SDLC fidelity) and an ask-agent run should
  confirm the merged stages keep what the separate ones caught.
