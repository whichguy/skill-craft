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

## Open (owner)

1. The unmerged round 2 branch (`stepplan2-cf7d87`), which another session built: merge, rebase or drop.
2. Which candidates to pursue, and whether to run the frozen-boundary replay first.
