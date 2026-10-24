# ShipLoop plan sizing journal

Living record for E-SIZE1 ([experiment plan](shiploop-plan-sizing-experiment-plan-2026-10-24.md)). Entries are edited,
not deleted: a superseded claim is marked with the date and the reason.

## 1. 2026-10-24: R-1, corpus analysis of saved runs

**Question.** Are ShipLoop's step plans small enough for one implement iteration, or are steps at times too big? Where
and why?

**Data and method.** Every run directory under `/Users/dadleet/e2e-runs` with a ShipLoop `state.md` (117 items with an
accepted step plan: 63 from 51 full runs, 45 slice seeds, 9 probes). Measured by
[`plan_shape.py`](experiments/shiploop-plan-sizing-20261024/plan_shape.py) (`export`, then `summary`) on checkout
6ed81762 plus this uncommitted script; no model calls. Host, model and effort come from each run's `result.json` or
`invocation.json`. Minutes are the gap between accepted actions. Evidence:
[rows](experiments/shiploop-plan-sizing-20261024/plan-shape-rows-2026-10-24.json),
[summary](experiments/shiploop-plan-sizing-20261024/plan-shape-summary-2026-10-24.txt). Per-step `criteria` lists exist
only in step plans written after `STEP_SIZING` (commit 153139f1, 10/11); older plans count 0 there.

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F1 | Oversized steps come from Grok 4.7 medium: 14 of its 20 full-run items were one step, up to 12 criteria in it. Sonnet 5.5 (39 items): median 3 steps, p90 3 criteria per step. Luna (2 items): 5 steps. | firm (descriptive) | summary table |
| F2 | After `STEP_SIZING` (10/11) Grok split local battleship into 4 to 6 steps; all 8 Salesforce chess items (runs of 10/17, 10/19, 10/20) stayed one step. Before 10/11 Grok's `custom` battleship items were mostly one step. | firm (descriptive); the cause is interim | rows, `case` and run dates |
| F3 | Big chess steps: run 4 W1 S1 is 7 criteria, 793 lines in 5 files, 21.4 implement minutes; run 3 W2 put R-4 to R-9 under 2 criteria (20.5 minutes). Steps of 6 or more criteria took 12 to 21 minutes; steps of 1 to 5, a median of 0.5 to 2.3 (platform confounds this: chess steps include deploys). | firm (descriptive), confounded | rows; run 4 `commits/` diffs |
| F4 | All 95 implement Until Loop receipts end at iteration 1: a step is done in one shot whatever its size. | firm | `loops/*-terminal.json` `progress.action_number` |
| F5 | No measurable step bound exists: "too large to review and recheck in one pass" is prose; the gates are text lengths (`STEP_TASK_LIMIT` 700, `STEP_CRITERIA_LIMIT` 1,200, `WORK_ITEM_CONTEXT_LIMIT` 2,500 in `shiploop_navigator.py`). Run 4 W1's task was 698 characters. | firm | `shiploop_prompts.py` `STEP_SIZING`; navigator producer limits |
| F6 | The templates price splitting but not size: `plan` duty 14 ("Every item pays a fixed round of stages and reviews") and the step `check` rule (runs now with only accepted steps; on a remote-only target, the recorded test route). Grok's run 4 W2 summary: "One step, because the controller is a thin delegate and the games are one proof." | interim (mechanism inferred from text and one quote) | `shiploop_prompts.py` plan duty 14, step-plan duty 4; run 4 W2 step-plan result |
| F7 | Offline gate replay over 42 steps with per-step criteria: refusing more than 3 declared paths catches 4 of 8 chess steps and refuses 0 of 34 others; the 4 missed declared no paths. Criteria > 4 catches 4 of 8 and refuses 3 of 34; requirements served > 4 catches 4 and refuses 4. | interim (n = 8 against 34; "too big" label is inferred) | replay over the rows |
| F8 | No evidence yet that big steps produce worse results: chess run 4 built every item in one step each and reached release-plan. | firm (absence in this corpus) | commit 6ed81762 (chess run 4 report, `test/shiploop_e2e/LEARNINGS.md`); rows |

**Effect on earlier results.** None superseded. `STEP_SIZING`'s source comment (owner, 2026-10-10) recorded the opposite
failure, steps split by file type with a no-op test step; F1 shows Sonnet no longer does that and K5 to K7 keep watching
for it.

**Next.** R0 harness, then R1 shape round (experiment plan section 5), on the owner's go.

## 2. 2026-10-24: R0, the harness, and one smoke sample

**Question.** Can a real run's step-plan point be replayed repeatably and scored by a script, so template arms can be
compared on it?

**Harness change.** Branch `exp/plan-sizing-1b1e33`, on the template-field experiment harness `78ea131b`, which already
had seed and stop points, pinned arms, overlays and script evaluators (experiment plan section 4); E6 is one more
experiment there. Added: the `slice.py` case key `fake_sf`; four replay fixtures and their builder
([`build_fixtures.py`](experiments/shiploop-plan-sizing-20261024/build_fixtures.py), `--check` passes); seven cases with
bands; [`e6_step_size.py`](../test/shiploop_e2e/evaluators/e6_step_size.py) and its committed verify records; arms B
and C as overlays on `9ed4ec24`; `PlanSizing` tests. The slice fixture test no longer requires `package.json` and item
`W1` (a replay keeps its run's tree and item ID); every earlier case still meets the weaker assertion, so no earlier
result changes.

**Smoke.** E6-K1, arm T (`9ed4ec24`), Claude Sonnet 5.5 (`claude-sonnet-5-5`, host default effort), inline,
planning review `stage`, Backchain `one`: slice verdicts all pass, 2.8 minutes, value 0. Sonnet planned the engine in
2 steps (S1: 4 criteria serving 4 requirements; S2: 5 criteria serving 7), no step paths declared, no `sf` call during
step-plan. Evidence: [`smoke-e6-k1-T-1.json`](experiments/shiploop-plan-sizing-20261024/smoke-e6-k1-T-1.json) (the run
folder is `/Users/dadleet/e2e-runs/e6-smoke-20261024/`, not committed). The smoke ran before the fixture redaction below;
the plan text the model read differed only in those IDs.

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F9 | The `STEP_SIZING` constant is defined in `shiploop_prompts.py` and referenced nowhere (main `6ed81762`, `288075c9`, `9ed4ec24`): the sizing text a step-plan packet prints is duty 4. F2's "after `STEP_SIZING`" means after the 10/11 change that wrote both. | firm | `grep -rn STEP_SIZING skills/shiploop/scripts/` |
| F10 | A product-file bound alone misses the engine step: run 4 W1 is one engine file (2 product files once tests and config are left out), W3 is 6. Arm C therefore caps criteria at 4 as well; applied to T's own navigator it refuses run 4 W1 (no step paths; 7 criteria) and accepts battleship-1 W2's six one-file steps. | firm (hermetic) | `PlanSizing.test_arm_c_refuses_an_oversized_or_undeclared_step_and_accepts_a_split_plan` |
| F11 | ShipLoop's path catalog classes Apex test classes (`*Test.cls`, its `-meta.xml`) as `code`, not `test`, on main and on the templates branch: the "tests are not a step" refusal and `item_scope`'s test detection do not see them (chess run 3 W3 put `SLChessGameTest` in a product step "because the check runs it"). The E6 evaluator counts them as product files. | firm | `item_scope.classify` on those paths; `references/path-classes.json` |
| F12 | Sonnet 5.5 on arm T also merged the K1 engine, into 2 steps (band ≥ 3). One sample: it says the case is not at the ceiling for Sonnet, not that Sonnet fails it. | exploratory (n = 1) | smoke record |
| F13 | Safety: a slice ran its case `checks` at grading in the harness's own environment, and a regrade did again, so a Salesforce case with an `sf` check would have reached the logged-in org even with a host-side shim. `fake_sf` now goes into both environments; E6's Salesforce checks call no `sf`. | firm | `slice.py` `fake_sf`, `regrade`; `PlanSizing.test_fake_sf_is_first_on_both_paths_and_answers_without_a_real_org` |
| F14 | Privacy: run knowledge files record the org ID, the CLI user ID and the instance host. `build_fixtures.py` redacts them by pattern (no ID is in the script). Seven files committed before this work, under `docs/experiments/` (packet-review-2026-10-17, run-analysis-2026-10-18, run-insights-2026-10-18), still hold the org ID in a public repository. | firm | `git grep` at `78ea131b` |

**Coordination.** E-EFF1 asked for no Grok runs while its R1 pair runs, and a word before anything touching `run.py`,
`slice.py`, `sessionlog.py`, `hosts.py`, `metrics.py` or `clear.py` lands on main (its manifest hashes them); this
branch changes `slice.py`. The templates branch renames a step's `check` to `proof` after `9ed4ec24`.

**Next.** R1 on the owner's go, after E-EFF1's Grok pair: E6-K1, K3, K5 first on Grok 4.7 medium, arms T, B, C, 4
samples each (36 slices), then the rest (experiment plan section 5).
