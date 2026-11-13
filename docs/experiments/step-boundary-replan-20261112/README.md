# Step-boundary re-plan: journal (2026-11-12)

Owner question (verbatim): "After each task for inner loop, should we have a step to determine if there are any key
learnings that would update the overall pending step plan? The idea would be to elicit out any knowledge leaned and
determine if there is a plan that would be better to execute upon."

Status: **interim**. The evidence and an Astra max review are recorded below. Nothing has been built; which candidate to
pursue is the owner's decision.

## Files

| File | What it is |
|---|---|
| `runs.txt` | the 300 E2E run folders scanned (state.md newer than 2026-10-29, with a `results/` folder) |
| `agg.py` → `agg.out` | items, step counts, plan versions, send-backs by stage, carry-forward queue edits |
| `late.py` → `late.out` | send-backs after at least one step of the current plan was documented, with summaries and result paths |
| `redo.py` → `redo.out` | step boundaries; minutes from a late send-back until the redone plan catches up with the done steps |
| `astra-brief.md` | the brief sent to Astra (question and facts first, candidates second) |
| `astra-review.json`, `astra-review.md` | Astra's review, gpt-6-astra, effort max, read-only consult, no fallback |

Run: `python3 agg.py runs.txt` (same for the others), from this folder.

## E1 — what exists today (firm)

- Each step's `document` stage is its reflection (navigator.md "Each step's reflection"; prompts duty in
  `shiploop_prompts.py`). Work the step plan lacks is a send-back. The owner chose this over a separate knowledge stage
  on 2026-10-28 ("Go with C", 7bba525ed74ad436ddbbe526db029714fdec47cb).
- `carry-forward` maps observations to the future queue and may replace it (carry-forward.md).
- A send-back makes the item's inner results non-current (`shiploop_planning_revision` current-result projection). The
  redone plan re-runs implement, test and document for every step, committed ones included; a step with nothing left
  to change makes no new commit (`test/shiploop-step-edges.test.py`, committed-prefix replay).

## E2 — measurements (firm as counted; see the corrections in E3)

| Quantity | Value |
|---|---|
| Runs / work items | 300 / 283 |
| Items ever multi-step (final plan multi-step) | 90 (89) |
| Steps in final plans | 430 |
| Step boundaries in final plans (Astra's history replay: 129 observed, 10 of them automatic N/A) | 147 |
| Step-plan versions per item | 1: 214, 2: 57, 3: 12 |
| Send-backs (inner work items + 2 global system-test) | 84 (82 + 2): implement 50, test-spec 17, test 10, validate-existing 3, document 2, system-test 2 |
| Send-backs after a documented step ("late") | 8 (7 with a prior Git commit receipt) |
| Carry-forwards with a later item / that replaced the queue | 10 / 4, and all 4 only added a new W2 after a single W1 |

Late send-backs, by cause (Astra's classification, matching mine except p0-terra, which I had not read):

| Cause | Cases |
|---|---:|
| A permission-set assignment re-run on each Proof run (not safe to repeat) | 3 |
| Shell quoting | 1 |
| A source search recorded as a `focused` suite, which needs test counts (p0-terra) | 1 |
| A deploy wrapper with no test-run summary | 1 |
| A tool the run's guard denies (osascript), stated by the guard from the start | 1 |
| A runtime failure needing diagnosis (gym S2) | 1 |

7 of 8 are faults in how a later step's Proof was chosen, written or classified, or in which tools it needs. They were
plausibly detectable at step-plan; none clearly needed knowledge that only an earlier step revealed.

Minutes from a late send-back to the redo catching up with the done steps:

| Case | file mtime | accepted trace event (Astra) |
|---|---:|---:|
| ui-live-2 | 2.9 | 3.4 |
| ticket-comments | 1.6 | 2.0 |
| ui-live-3 | 3.4 | 3.4 |
| salesforce-battleship | 3.7 | 5.1 |
| p0-terra | 14.6 | 16.1 |
| chess rerun-02 | 6.3 | 7.8 |
| chess baseline-01 | 9.8 | 11.0 |
| Total | 42.3 | 48.8 |

These intervals include re-planning and validation. They are not the work a cheaper re-plan would save.

## E3 — corrections to my first reading (firm)

- I briefed 82 send-backs; the stage counts sum to 84 (2 are global system-test send-backs).
- 147 is a count of nominal boundaries in final plans. Replaying history with the navigator's boundary predicate gives
  129 (Astra).
- I wrote that A2a (step-plan Proof "safe to repeat" wording) landed after 4 of the late runs. **It never landed.**
  211fe61b0bc13b8fa5af43241a04400e1794fe85 is not an ancestor of origin/main: the whole step-plan round 2 branch
  `stepplan2-cf7d87` (20 commits, head b6fcfa46581dc5a1679ee34764d019d34f486ba3: A1, A2a, D and the Python 3.9 fix)
  is unmerged, and main is 363 commits ahead of it. The owner had answered "Ship A2a (Recommended)" on 2026-11-01.
  Main's step-plan prompt says "safe to repeat locally" only for check commands.
- Result-file mtimes order events differently from state history in 131 runs (Astra). Use state history for order and
  accepted trace events for timing in any follow-up.

## E4 — Astra max review (interim; verdicts)

No new mandatory model action after every step or item. Keep reflection in `document` plus its Improve review, and
item re-planning in `carry-forward`.

- **A (one forward-impact question in document):** pilot, modified. Ask whether anything this step showed invalidates
  a pending assumption or changes the work, order, paths or verification of later steps; name the steps, the evidence
  and the smallest amendment, or say no consequential change was found. Do not promise that only later steps change.
  It cannot accept the current step and re-plan its suffix in one result (a document send-back comes before the step
  commits), and it does not run on steps whose document is automatic N/A.
- **B (keep unchanged done steps after a send-back):** defer until a retention contract is designed and tested. An
  unchanged step row does not prove its evidence still applies: a same-ID test case can change its oracle in test-spec;
  `case_step` moves a criterion to the last step that lists it; three cursor readers (`implement_progress`,
  `test_loop.step_number`, `loops.current_step`) count rows independently; an entirely retained, shortened plan never
  runs the last-step regression; and replayed S1 commits in the measured cases picked up later steps' uncommitted work.
  Needs negative controls for each.
- **C (plan-time Proof duty):** adopt the explicit duty (repeat under the intended setup and cleanup, available tools
  and the run's limits, the right suite classification and output, quoting under `/bin/sh -c`); pilot any automated
  refusal before shipping it.
- Cheapest next experiment: a frozen-boundary replay of the 8 late cases plus matched clean boundaries, with only the
  information available at each boundary, across arms (current duties, modified A, a separate action), same subject
  model and effort; judge actionable corrections, missed changes, unsupported re-plans and requirement weakening, then
  tokens and time. Add cases with genuinely new information; this corpus is mostly planning mistakes.

My verification of Astra's factual claims: A2a and the round 2 branch are not on main (git merge-base); the 4 queue
replacements each map W1 to [W2] (rescan); `_commit_stage` requires an accepted document done; `_document_entry`
records N/A for non-behavioural diffs. Not verified by me: the 129-boundary replay and the trace-event minutes.

## Owner answers (2026-11-12)

- Re-plan: "Replay first (Recommended)". Round 2: "Rebase and ship (Recommended)". It was done as a merge, which keeps
  the branch's cited hashes; see the merge commit message.
- Later the same day: "I want to avoid send back about redoing steps, I feel like this might be an excessive scenario,
  check on this. My idea is that at the end of an inner loop, even if there are things to change, we should add or
  augment existing or new steps in the step-plan not revisit old steps. This is a fix forward motion."

## E5 — do send-backs change done steps? (firm, with Astra's qualifications)

`fixforward.py` → `fixforward.out`, `fixforward_detail.py` → `fixforward_detail.out`, ordered by state history.

- 81 inner send-backs were followed by an accepted step plan (82 inner send-backs had a preceding plan; one was never
  replanned). Within the plan in force, 73 came before any documented step and 8 after. Across the item's full history
  the split is 72 and 9 (Astra: p0-terra's second amendment strengthened an already-documented S1's C2 and Proof, which
  my per-plan counter missed).
- The redone plan changed a done step's row (task, criteria, proof, paths) once. In 48 only the failing or a later
  step's row changed. In 32 no step row changed: 30 changed item-wide fields, and 2 changed only summary and evidence.
- Of the 8 late cases, 6 left everything a done step owns unchanged. p0-terra relabelled a shared command (C3 and C6,
  still awaiting S2) from focused to check. gym replaced the plan with UI diagnosis and later blocked. Astra also found
  no completed test-spec case changed in 7 of the 8.
- Limits: `row()` compares four fields by position (Astra checked id, deps and skills by hand for the 8). The detail
  script does not map test IDs through test-spec cases (Astra mapped them independently; the 6-of-8 finding holds).

Learning: replaying done steps after a send-back bought nothing at the step level in 7 of 8 cases. This supports
fixing forward. It measures no quality gain and no time saving.

## E6 — Astra max review of fix-forward (interim; `fix-forward-brief.md` → `astra-fix-forward.md`)

Verdict: fix-forward is sound. Build a guarded pilot. "Completed executions stay fixed; unresolved obligations and
verification continue moving forward." It corrects the draft rules:

1. Freeze completed records (a step is done at its accepted document, after review and commit) and copy their rows
   mechanically, never re-typed by the planner. A later finding can challenge their evidence and add a corrective
   obligation without erasing it.
2. Freeze case ownership too. Today `case_step` gives a criterion to the last step listing it, so a new step that
   re-lists C1 moves TC-1 (Astra reproduced this). Corrective work gets new criterion IDs as well as new case IDs.
3. Only unfinished work re-enters implementation. Every later step still runs the earlier cases and the minimum
   regression, and the last step runs the full regression (b385df5d7005de79e2522de308b3feb57b397716,
   b55909179b89bfc63bba67d4cdbb833c700df147 stay). Receipts of the unfinished step are invalidated when its contract
   changes.
4. Protect shared commands: a mixed command cannot drop a done step's case. An invalid old command is superseded by an
   appended correction, never rewritten.
5. Make the amendment base explicit (the last done commit), and check every expectation whose applicability changed.
   Dirty edits keep an owner, so a corrective step inserted earlier cannot absorb them.
6. IDs are never reused. Execution order follows deps, so [S1 done, S3 correction, S2 pending] is valid. Removing a
   step cannot discharge its obligations.
7. Closure is its own script transition when no step is pending (no simulated document). A successful document may
   carry an amendment request: review and commit first, then amend. Automatic N/A documents stay as they are.

Also: carry-forward's incompatible findings include a changed completed-work assumption, and the document prompt still
sends a changed requirement intent to send-back; align them. Implementation: one authoritative item-execution
projection, with adapters for current_actions/step_actions, implement_progress, test_loop.step_number,
loops.current_step, step_view, _previous_step_results, open_items and the count readers. Ten negative controls are listed
in astra-fix-forward.md. The cheapest live check is one local two-step item whose S2 has a wrong Proof and dirty edits.
Build order 1-7 is in the review.

Effect on the replay decision: fix-forward changes what a boundary finding costs. The frozen-boundary replay still tests
whether a forward-impact question catches anything; it is not started.

## Owner answers, later (2026-11-12)

- Fix-forward: "Build, replay after (Recommended)".
- After "Do we need to rework any of these with the scripts to make the purpose and functionality more clear?": I read
  it as asking whether prompt-only rules should be script-enforced. A1 and D already rest on script rules. A2a (Proof
  safe to repeat) was wording only, so the Proof-failure refusal now says it (routine, a message). The searched-command
  refusal got an explicit answer: "Add it (Recommended)".

## E7 — the build (interim until the live round)

Round 2 shipped first: skill-craft 2.36.6 / shiploop 1.33.10 (release 7ceaecf441448c1c394340ec2c98f848cd685b27). Then,
on branch `feat/fix-forward-5308ed`:
- Projection: `planning_revision._StepLists` feeds `current_actions`, `step_actions`, `built_steps` and `done_steps`.
  `implement_progress`, `test_loop.step_number`, `loops.current_step`, `step_view` and `_previous_step_results` read
  it, instead of each counting implement rows after the latest plan.
- Data: a step row may carry `"done": true`. Only the amendment gate decides which rows carry it, and a plan without
  marks reads as before.
- Gates: `_fix_forward_refusal` (step-plan) and `_frozen_case_refusal` (test-spec), both in `_check_fix_forward`.
  Case ownership follows `iteration.case_step`. A spanning criterion still owed by a later step stays with a step still
  to run.
- Packets: `_fix_forward_lines` prints the done rows to copy, and the cases due at done steps.
- Found while building: the item's lint base already moves to the last done step's tree when the next step begins,
  and a send-back keeps it. So Astra's amendment base was already in place, and the amendment restates a done step's
  expectation (absent becomes works). This corrected the first design draft.
- Also: `test_loop.REPEAT_LINE` on the Proof-failure refusal; `layers.check_confirms` refuses a focused command that
  `search_only` classifies as a search.
- Fail-first on the released tree 7ceaecf4: 5 new step-edge tests fail (4 errors, 1 failure), the Proof-refusal test
  errors, and the focused-search test fails (`fix-forward-failfirst.txt`). On the branch all pass.

## Open (owner)

1. The live round that has to precede the release, and then the boundary-question replay.
