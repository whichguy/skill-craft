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
result changes. Checks: `test/shiploop-e2e-experiments.test.py` 39 OK and `test/shiploop-e2e-slice.test.py` 58 OK on
the committed files; `./test/run-all.sh --group quick --changed-from 78ea131b` PASS (exit 0; started before the ID
redaction, which the two files above were rerun after).

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
| F11 | ShipLoop's path catalog classes Apex test classes (`*Test.cls`, its `-meta.xml`) as `code`, not `test`, on main and on the templates branch: the "tests are not a step" refusal and `item_scope`'s test detection do not see them (chess run 3 W3 put `SLChessGameTest` in a product step "because the check runs it"). The E6 evaluator counts them as product files. **Decided 2026-10-24, not fixed:** a fix (`b4198328`, picked as `66703f48`) was reverted on the templates branch (`df6b91e2`) under the owner's rule that ShipLoop stays generic, catalogs included; the gap stays as a known limit. | firm (finding); decided (no fix) | `item_scope.classify` on those paths; `references/path-classes.json`; `df6b91e2` |
| F12 | Sonnet 5.5 on arm T also merged the K1 engine, into 2 steps (band ≥ 3). One sample: it says the case is not at the ceiling for Sonnet, not that Sonnet fails it. | exploratory (n = 1) | smoke record |
| F13 | Safety: a slice ran its case `checks` at grading in the harness's own environment, and a regrade did again, so a Salesforce case with an `sf` check would have reached the logged-in org even with a host-side shim. `fake_sf` now goes into both environments; E6's Salesforce checks call no `sf`. | firm | `slice.py` `fake_sf`, `regrade`; `PlanSizing.test_fake_sf_is_first_on_both_paths_and_answers_without_a_real_org` |
| F14 | Privacy: run knowledge files record the org ID, the CLI user ID and the instance host. `build_fixtures.py` redacts them by pattern (no ID is in the script). Seven files committed before this work, under `docs/experiments/` (packet-review-2026-10-17, run-analysis-2026-10-18, run-insights-2026-10-18), still hold the org ID in a public repository. | firm | `git grep` at `78ea131b` |

**Coordination.** E-EFF1 asked for no Grok runs while its R1 pair runs, and a word before anything touching `run.py`,
`slice.py`, `sessionlog.py`, `hosts.py`, `metrics.py` or `clear.py` lands on main (its manifest hashes them); this
branch changes `slice.py`. The templates branch renames a step's `check` to `proof` after `9ed4ec24`.

**Next.** R1 on the owner's go, after E-EFF1's Grok pair: E6-K1, K3, K5 first on Grok 4.7 medium, arms T, B, C, 4
samples each (36 slices), then the rest (experiment plan section 5).

## 3. 2026-10-24: R1, the first three cases on Grok

**Question.** Does a measurable step bound in the step-plan template (arm B), or the same bound as a refusal (arm C),
keep Grok 4.7's step plans inside each case's band where the current text (arm T) does not, without over-splitting a
small item?

**Conditions.** Grok 4.7 medium (harness default), slices seeded at and stopped after step-plan, planning review
`stage`, inline. Arms T = `9ed4ec24`, B = T + `e6-size-prose.json`, C = T + `e6-size-gate.json`; 4 samples per arm
per case; the three arms ran in parallel, each through K1, K3, K5 in order, 16:02 to 19:55. Output
`/Users/dadleet/e2e-runs/e6-r1-20261024` (not committed); every sample's score in
[`r1-results-2026-10-24.json`](experiments/shiploop-plan-sizing-20261024/r1-results-2026-10-24.json), written by
`r1_report.py`; decisions in `<out>/E6-K<n>/decision-*.json` and the template journal.

**Harness incident.** Homebrew replaced Python 3.14.7 with 3.14.9 at 18:33 (and `python3` now resolves to 3.15.1); the
three slices still running on 3.14.7 (K3/T/4, K3/C/3, K3/B/4) crashed at grading on a lazily imported standard module
after their step plans were accepted. Each was regraded with `slice.py --regrade` on 3.14.9 and scored; no sample was
rerun or lost. Later slices ran on 3.14.9 or 3.15.1 (harness interpreter only; the model and its plugin are unchanged).

**Results.**

| Case (band) | T | B | C | decide |
| --- | --- | --- | --- | --- |
| K1 chess engine (3+ steps) | 0.25 (2, 3, 2, 2 steps) | 0.75 (4, 6, 6, 2) | 1.00 (6, 3, 5, 3) | T vs C **supports**; T vs B and B vs C inconclusive (A/A spread 0.50) |
| K3 board and entry metadata (2+, layers apart) | 1.00 | 1.00 | 1.00 | ceiling, every pair |
| K5 one bug fix (exactly 1) | 1.00 | 1.00 | 1.00 | ceiling, every pair |

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F15 | The control reproduces chess run 4: T planned the engine in 2 steps in 3 of 4 samples, one step carrying up to 9 criteria. | firm (n = 4) | r1-results, E6-K1 T |
| F16 | A countable step bound in the template text moves Grok: 7 of 8 B and C plans split the engine into 3 to 6 steps, against 1 of 4 for T; `decide` supports C over T on K1. | interim (n = 4 per arm) | decision-T-C.json; r1-results |
| F17 | C's refusal never fired: 0 gate refusals in its 12 samples. B and C therefore ran identical prompt text in effect, and their K1 difference (0.75 against 1.00) is sampling noise; pooled, the prose bound split the engine in 7 of 8. The gate is untested insurance. | firm (0 refusals); the pooling is interim | gate-refusal count over C's events |
| F18 | K3 does not reproduce run 4's W3 merge: every arm, the control included, keeps the component and its tab, app and flexipage in separate steps. The case cannot separate the arms and needs changing before more samples (the decide rule's own advice). | firm | decision-*.json on E6-K3 |
| F19 | No over-splitting: every K5 plan in every arm is one step; B and C stay within their own bound (at most 4 criteria). | firm (n = 12) | r1-results, E6-K5 |
| F20 | Cost: B and C took about as long as T on K3 and K5 and 2 to 5 minutes longer on K1, where they plan more steps; in a full run each extra step adds an implement and its Improve review, which R2 measures. | interim | r1-results `mean_minutes` |

**Next.** Grok to E-EFF1 for its R2 pair (75 minutes). Then R1g: the winner's generic wording `Cg` on K1, K3 and K5,
4 samples each, before any ShipLoop change (owner, 2026-10-24); then the remaining cases (K2, K4, K6, K7), whose arms
await the owner's choice.

## 4. 2026-10-24: R1g, the generic wording re-checked

**Question.** Does arm C in a generic wording (`Cg`: "a file that only describes another changed file counts with
it"; the gate's companion-file rule by name, no stack's file convention) keep C's result, as the owner required before
any ShipLoop change?

**Conditions.** As R1 (Grok 4.7 medium, seed and stop at step-plan), arm `Cg` = `9ed4ec24` +
`e6-size-gate-generic.json`, 4 samples on each of K1, K3 and K5 in three parallel lanes, 21:03 to 22:43, Python 3.14.9
for the harness throughout; compared with R1's own T and C samples in the same output folder (same commit, cases and
host). E-EFF1's second hello pair ran on Grok just before (its slices had ended); another session's Grok chess run was
active throughout.

**Results.**

| Case | T | C (R1) | Cg | decide T vs Cg | decide C vs Cg |
| --- | --- | --- | --- | --- | --- |
| K1 | 0.25 | 1.00 | 0.75 (4, 2, 7, 5 steps) | inconclusive: +0.50 inside the A/A spread 0.50 | contradicts (Cg no better; -0.25, inside the spread) |
| K3 | 1.00 | 1.00 | 1.00 | ceiling | ceiling |
| K5 | 1.00 | 1.00 | 1.00 | ceiling | ceiling |

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F21 | The generic wording does not reproduce C's verdict: Cg is inconclusive against T on K1 (0.75 vs 0.25). By the owner's rule no ShipLoop change follows from R1 alone. | firm (the verdict); interim (the effect) | decision-T-Cg.json on E6-K1 |
| F22 | Cg's gate never fired either (0 refusals in 12 samples), so B, C and Cg ran the same bound in prose, differing only in the companion-file clause; on K1 they put 10 of 12 plans inside the band (B 3, C 4, Cg 3) against 1 of 4 for T. Their spread across arms (0.75 to 1.00) is within one arm's sampling noise. | interim (pooling arms the decide rule keeps apart) | r1-results; gate-refusal counts |
| F23 | The decide threshold is coarse at 4 control samples: the A/A spread is the difference of two 2-sample means, so it can only be 0, 0.5 or 1, and T's [0, 1, 0, 0] fixes it at 0.5. An arm needs a mean above 0.75 against this control to be "supports"; more samples of the arm move its mean but not the threshold. | firm (arithmetic of experiment.py `judge`) | experiment.py `judge`, arms.aa_spread |
| F24 | The generic wording keeps the over-split guard: every Cg K5 plan is one step, and every Cg K3 plan keeps the layers apart. | firm (n = 4 each) | r1-results |

**Next.** Owner's call: more K1 samples (T and Cg, to firm up F21/F22), the remaining cases, or both.

## 5. 2026-10-25: R2, shape on the remaining cases

**Question.** Owner, 2026-10-24: "Skip extra K1 samples; run K2, K4, K6 and K7 with T and Cg, 4 samples each (32
slices)." Does the generic bound (`Cg`) split the second engine case (K2, the Node engine) and keep the battleship
server (K4), the rename (K6) and the added function (K7) inside their bands?

**Conditions.** As R1g: Grok 4.7 medium, seed and stop at step-plan, arm T = `9ed4ec24`, arm Cg = `9ed4ec24` +
`e6-size-gate-generic.json`, 4 samples per arm per case, output `/Users/dadleet/e2e-runs/e6-r1-20261024`, Python
3.14.9. 08:47 to 11:22 in four lanes. Two lanes were refused at launch (`run` takes `--sample` or `--samples`, not both)
and relaunched at 08:49. From 09:57 the lanes that finished early took later samples of the slow ones (K7 samples 1 to 4
in part, K4 Cg 4). The original lanes skipped those as finished earlier: 7 skips, no cut slice. E-EFF1 held its runs
until this batch ended. Another session's Grok chess run may have shared the host, which matters to minutes, not to
plan shape. Renaming: the downstream round that entries 3 and 4 call R2 is R3 from now on (plan section 5).

**Results.** All 32 slices passed. The steps column gives each sample's step count; max criteria is the largest step's
criteria count over the 4 samples.

| Case | Band | T (steps) | Cg (steps) | Max criteria T / Cg | Minutes T / Cg | decide T vs Cg |
| --- | --- | --- | --- | --- | --- | --- |
| K2 node-chess-engine | 3+ | 0.50 (2, 4, 1, 6) | 0.75 (2, 10, 4, 5) | 6 / 4 | 16.4 / 16.7 | **supports**: +0.25 beyond the A/A spread 0.00 |
| K4 node-battleship-server | 2-7 | 1.00 (3, 4, 4, 6) | 1.00 (4, 5, 3, 4) | 4 / 2 | 20.2 / 21.5 | ceiling |
| K6 node-rename | 1 | 1.00 (1, 1, 1, 1) | 1.00 (1, 1, 1, 1) | 3 / 4 | 13.8 / 14.2 | ceiling |
| K7 node-add-function | 1-2 | 1.00 (1, 1, 1, 1) | 1.00 (1, 1, 1, 1) | 4 / 4 | 12.5 / 10.6 | ceiling |

**Harness changes** (this commit; none changes an earlier result, since all read run folders only):
- `progress_card.py`: `model()` split from `card()`. `--json` prints the model with ISO `progress.updatedAt` and
  `etaAt`, a running slot's `since`, and `events` (the finished samples, newest first). `--meta JOB.json` turns it into
  a Live Run Card job document (`job_document`). The card's tip now says "1 step", not "1 steps". Test:
  `ProgressCard.test_the_model_carries_iso_times_for_a_live_card_and_renders_as_the_card`.
- The Live Run Card (https://claude.ai/artifact/6UrX5dfz95wMNfpMMzwdz8): a page that subscribes to its `jobs` store
  and redraws on every write. Source and R2's job meta are in `docs/experiments/shiploop-plan-sizing-20261024/live-card/`.
  This round's job, `jobs/e6-r2`, was written on every 3.5-minute tick and every finished sample.
- `improve_drift.py` compares each sample's submitted plan (the Improve record's `seed_result`) with the scored plan.
- `r2-results-2026-10-25.json`: every E6 round (R1, R1g, R2) from `r1_report.py --json`, superseding
  `r1-results-2026-10-24.json` as the complete table.

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F25 | The generic wording wins K2, its first "supports": Cg 0.75 against T 0.50, whose pairs tie (T 0, 1, 0, 1), so the A/A spread is 0. The margin is one sample. | firm (the verdict); interim (the effect, n = 4) | `E6-K2/decision-T-Cg.json` |
| F26 | Across both engine cases Cg puts 6 of 8 plans in band against 3 of 8 for T (K1 3 against 1, K2 3 against 2). | interim (pooling two cases the decide rule keeps apart) | r2-results |
| F27 | No harm on the guards: K4, K6 and K7 are at the ceiling in both arms, Cg kept every rename and added function to 1 step, and K4 within 2 to 7. With R1g's K3 and K5, Cg has 20 of 20 samples in band on the five non-engine cases. | firm (n = 4 each) | r2-results; decision files |
| F28 | Cg's gate refused nothing in 28 samples (C's nothing in 12): every plan met the bound in its first submission, so the prose did the work and the gate is untested insurance. Updates F17 and F22. | firm (exact refusal messages counted in the events) | events.jsonl of every C and Cg slice |
| F29 | The bound caps the criteria count, not its text: Cg's largest step stayed within 4 criteria in all 28 samples while T's K2 steps reached 6, but Cg K2 sample 1 put 1,121 characters into 2 criteria. T's merged steps press on the text limit instead: its largest K1 and K2 steps are 1,166 to 1,200 of 1,200 characters in 6 of 8 samples. | interim (descriptive; the clear Cg case is n = 1) | per-step criteria characters from the scored plans |
| F30 | The bound can swing to many tiny steps: Cg K2 sample 2 planned 10 one-criterion steps, in band because K2 has no upper limit. In a full run each step adds an implement and an Improve round, which only R3 can price. | exploratory (n = 1) | E6-K2/Cg/2 plan |
| F31 | E6 measures the planner, not Improve. The scored plan is the one after the step-plan Improve child, but in 80 samples Improve changed no step count; it lengthened the largest step's criteria in 29, median +0 and at most +375 characters. | firm | `improve_drift.py` output on the run folder |
| F32 | ShipLoop defect found here: an Improve final result skips `_check_producer_bounds`. The Improve import path in `shiploop_navigator.py` runs 12 gates on `final_result`, the sizing gate among them, but not the producer bounds, so K4 Cg sample 2's S1 grew from 846 to 1,221 criteria characters and was stored over `STEP_CRITERIA_LIMIT` (1,200). The same holds on main `c91cfb90`. The generic fix is to call `_check_producer_bounds(child["stage"], final_result)` beside those gates; it is not made here. | firm (code read on both commits; one stored instance) | `improve_drift.py`; the import path after `final_result = receipt.get("final_result")` |
| F33 | Cost at step-plan: Cg's minutes are within 2 of T's on every R2 case. | interim (shared host) | r2-results `mean_minutes` |

**Next.** Owner's call on a ShipLoop change. Option (a): take Cg's wording into the step-plan template: the prose and
the gate as tested, or the prose alone, since the gate never fired. Option (b): more K1 samples first, since F23's
coarse threshold left K1 inconclusive. Option (c): R3 downstream to price the extra steps; it needs the owner's go, and
K1 and K3 need org `de`. Separately, F32 is a small generic navigator fix with its own change note. Grok stays with
E-EFF1 until it reports its R2 finished.

## 6. 2026-10-25: the bound ported into ShipLoop

**Decision.** Owner, 2026-10-25: "Port Cg's sizing prose into ShipLoop's step-plan template (generic wording, no gate
since it never fired), with a change note and tests; no release yet."

**Change.** Commit `7cf4bb90` on branch `feat/step-size-bound-9227d2` (worktree
`.claude/worktrees/step-size-bound-9227d2`), cut from origin/main `ed07b3bb`, which contains `9ed4ec24` (arm T). It is
not pushed and not released. The quick group (`run-all.sh --group quick --changed-from origin/main`) passed 50 suites,
and `check-release-boundary.py --base origin/main` passed. `DUTIES["step-plan"]` in `shiploop_prompts.py` takes
Cg's three prose edits, which are also Bg's: the countable bound (at most 4 criteria and 3 product files, with the
companion-file clause), `paths` naming every changed file, and the shared proof script on a remote-only target. Main
renamed a step's `check` to `proof` in `92339292`, so the ported text says "proof" where the arm said "check"; the
meaning is unchanged. Cg's fourth edit, the `_check_step_sizing` refusal, is not ported (F28: it never fired). The
unused `STEP_SIZING` constant (F9) is removed, because its text contradicted the bound. The change note is
`changes/shiploop/step-size-bound.md` (minor). The new test,
`test_the_step_plan_packet_bounds_each_step_by_criteria_and_product_files` in `shiploop-packet-completeness.test.py`,
reads the rendered step-plan producer packet; it would fail on origin/main, where the text is absent.

**Released, 2026-10-25** (owner: "release as well"; then "Fold the Improve size-limit fix (F32) into this release"):
skill-craft 2.11.0 with ShipLoop 1.11.0, release commit `5d3628b0` on main, pushed through `scripts/release-push.py`.
It ships four notes: `step-size-bound` (the port, `f23cdb20`), `improve-final-result-bounds` (the F32 fix, `b8630f41`:
the Improve import now calls `_check_producer_bounds`; its test failed before the fix), and two from other sessions
already on main (`no-run-caps`, `judge-zero-exit-masked-failure`). A wider quick-group selection then failed
`shiploop-step-packets` and `shiploop-packet-recut`. When a Test layers block sits at its gate limit, the ask-agent
step-plan head had 140 characters of headroom under the 20,000 host cut (19,860 on main), and the port added about
330, so the head dropped its References block. `58a8f2eb` shortened the wording, keeping every obligation: the
remote-only sentence keeps only "steps share one proof script", the bound drops the implied "More criteria or files",
and two clauses that repeated others go. The at-limit head is now 19,925, and the normal heads grew by 65, recorded in
`head_table.json`. So the shipped text is the tested Cg prose, shortened; the shortening changes no rule, and no slice
ran on it.

**What the port carries from the evidence.** Cg = prose and gate, the gate never refused, so the shipped text is the
one every Cg sample planned under (F28). The verdicts it rests on: K2 supports (F25), K1 inconclusive (F21, F23), and no
harm on the five other cases (F27). The open questions travel with it: count against text (F29), many tiny steps
(F30), and the downstream cost (R3, not run).

## 7. 2026-10-25: faster rounds (harness, no Grok run)

**Question.** Owner, 2026-10-25: "These are taking far too long. I need some way to get more efficient validation of
these things"; then "Build the E6 harness speedups on exp/plan-sizing-1b1e33: slice.py --planning-review none for
shape rounds, early stop when a verdict can't change, and one shared job queue instead of fixed lanes, with hermetic
tests; no Grok runs until E-EFF1 frees it."

**Harness changes** (this commit):
- `slice.py --planning-review stage|none` passes ShipLoop's run option, through `run.seed_run`, to `workspace start`.
  With `none` it names the build's Improve card (`--improve-skill`), which `none` requires. Under `none` no Improve
  child starts after spec, test-strategy, plan, step-plan or test-spec (`stage_spec.reviewed_stages`). The invocation
  records the option, and so does each sample's `score.json`, read from its `command.json`. `decide` refuses arms
  whose samples ran under different options, because the packets differ: under `none` they no longer direct an Improve
  stage.
- `experiment.py queue <ids> --arms T,Cg --jobs N` runs a round as one ordered list: sample 1 of every experiment and
  arm, then sample 2, and so on. It runs at most N slices at once, skips finished samples, and refuses a second queue
  in the same output folder (`.queue.lock`). It replaces the hand-run lanes of R2, whose slowest lane set the end and
  whose rebalancing had to avoid cutting a running sample.
- Early stop, on by default in `queue`: before each launch, `possible_verdicts` enumerates every 0-or-1 outcome of
  the missing samples. When each pair (the control against an arm) has one possible verdict left, the experiment's
  remaining samples are skipped. It needs a binary value (`BINARY = True` in `e6_step_size.py`) and no gate.
- Tests: `RoundSpeedups` in `test/shiploop-e2e-experiments.test.py`. It covers a real seed under `none` and its refusal
  without the card, settled and open verdicts (including R2's K2), the queue's concurrency cap and finished-sample
  skip, the early stop, the lock refusal, and `decide`'s mixed-option refusal. It makes no host call and no Grok run.

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F34 | Skipping the step-plan Improve child removes about half of each shape slice. Across 80 slices the child took a median 8.2 of 17.1 minutes (51% of all slice time) and changed no step count (F31). A `none` round therefore needs its own control samples: its packets differ from the `stage` rounds', and `decide` refuses to mix them. | firm (timing); the halving is a forecast until a `none` round runs | `start.json` and `slice-result.json` times over the run folder |
| F35 | The strict early stop that was asked for, where no completion can change the verdict, would have saved 1 of 104 recorded slices (1%). Eight of the 13 pairs end at the ceiling, and a ceiling (every sample in band) is never settled before the last sample. A looser rule, stopping once supports is certain or impossible, would save 46 of 104 (44%). It does so by cutting every guard case (K3 to K7) to 3 slices, because a control already at the ceiling makes supports impossible from the start. That removes the evidence the guard cases exist for, that the arm does no harm, so the looser rule is not built. | firm (replay of r2-results through possible_verdicts) | replay over `r2-results-2026-10-25.json`, sample order T1, Cg1, T2, ... |
| F36 | Forecast for a round like R2 (32 slices, 4 at a time): about 8.5 minutes per slice under `none`, with the queue removing the lane tail. That is roughly 70 to 80 minutes, against 2 h 35 min (08:47 to 11:22). | exploratory (forecast) | F34; R2's timeline (entry 5) |

**Next.** Grok stays with E-EFF1. The first round to use these is R3, the downstream round, or a `none` re-baseline
of K1 and K2; the owner chooses which.

## 8. 2026-10-26: R3 attempted (no data: the Grok balance ran out), the rig merged with main

**Question.** Owner, 2026-10-26: "Merge to main and commit clear improvements, publish. Rebase. Plan and implement
fixes based on learnings, implement, then continue with testing and fixing." R3 ran in its smaller form, K2 only (6
full-item slices, arms T and Cg, 3 each), as the owner's go to continue testing, once the E2E trio had freed Grok.

**Conditions.** `experiment.py queue E6D-K2 --arms T,Cg --samples 3 --jobs 4 --host grok --timeout=10800`, started
06:40 from a frozen worktree at da86f8a0 (so rebasing the branch could not change the harness under it), into
`/Users/dadleet/e2e-runs/e6-r3-20261026`, under the default planning review (stage).

**Results.** None usable. From about 07:05 every Grok call returned "API error (status 402 Payment Required): Grok
Build usage balance exhausted". T 1, T 3, Cg 1, Cg 2 and Cg 3 carry the 402 in stderr. T 2's six sessions each ended
with Grok's stopReason "cancelled" before it, most likely the same cause. No slice finished an implement step. The
queue was stopped at 07:12, and the two other Grok sessions and the owner were told. R3 reruns once the balance is
topped up; its failed samples must first be moved aside (`queue` skips a sample whose slice-result.json exists).

**Harness changes** (`dcb29a4f` merge, `e8b61ba7`, `da86f8a0`):
- Merged origin/main into the branch rather than rebasing: 17 commits and main had both changed 8 harness files, so
  one merge resolved two conflicts (`slice.py`'s resume guard with main's monotonic deadline; `test-groups` counts and
  family). The pre-merge head is commit `da86f8a0`, in main's history since the branch landed as PR #22 (merge
  `33dec1f9`).
- Main's navigator renamed a step's `check` to `proof`, and an open assumption's `check` and `consumer` to `settle`
  and `due_item`. `step_cases.json` now uses that shape, regenerated by `build_fixtures.py` (`current_assumption`), so
  `--check` matches. Rounds on arms pinned before the rename (R1 to R3 on 9ed4ec24) reproduce from `da86f8a0`.
  A new round on such an arm fails at seeding, never silently.
- `experiment.py` refuses a slice option written as two words (`--timeout 10800` had made "10800" an experiment id,
  and the queue ran nothing), naming the one-word form.
- The Live Run Card shows each update's number, when the next is due, and "Update overdue" in amber before the
  10-minute stale warning. `progress_card.job_document` passes a job's `refresh`.
- `e6_downstream.host_cancelled` counts host-cancelled sessions, so a host failure is not read as an undelivered item.

**Findings.**

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F37 | A Grok balance that runs out first shows as turns Grok "cancelled", then as HTTP 402 on every call; the harness saw a failed process, not a template result. A slice whose host failed must be rerun, not scored as not delivered. | firm; fixed for HTTP 401/402/403 in entry 9 (2026-10-26) | stderr.txt and events.jsonl of the six R3 slices |
| F38 | `experiments-shiploop-chain-native-pilot` timed out under `--jobs 8` (a 45-second subprocess limit, a 20-second hold) and passed alone (11 OK). Timing-sensitive suites need their own slot in a parallel run (superseded 2026-10-26, entry 9: the limits were safety nets, so they were raised instead). | firm (one failing parallel run, one passing serial run) | quick run on the merge; serial rerun |

**Next.** Top up the Grok balance (owner), then rerun R3 on K2. Meanwhile the merged rig lands on main.

## 9. 2026-10-26: fixes from R3 and the merge (harness only, no Grok run)

**Question.** The same instruction's second half: plan and implement fixes from what R3 and the merge taught, then
keep testing. Three fixes, each with a test that fails without it.

**Fixes.**
- **Main CI was red on the merge** (`33dec1f9`, run 40340118933): two ProgressCard tests raised AttributeError,
  because Linux's `os.stat` has no `st_birthtime` and `progress_card.sample_state` read it for a running sample.
  The card now dates a sample from the `started` its command.json records (`experiment.run` writes it at each
  launch), else the birth time, else the last change. Commit `6b6ce383`; main CI passed on it (run 40342755667).
  The local checks missed it because macOS has the field: a test now runs the card with a stat that has none.
- **A host refusal is a host failure, not a score (F37).** `experiment.host_failure` reads a slice's stderr.txt for
  HTTP 401, 402 or 403 (in Grok's "API error (status 402 …)" message or an error's `http_status` field). It never
  applies to a slice that passed, since a host that ran out after delivering did deliver. Such a sample is not
  `finished`. `score` records it with no value and its reason (`possible_verdicts` reads a missing value as an open
  sample, not a fixed one). `run` stops at it. `queue` starts no more samples once one is refused: R3 had run six
  slices into the 402. The next `run` or `queue` moves the slice to `slice.host-failed-<time>`, drops its stale
  score.json and runs it again. The card shows it as an error slot. On R3's folders it marks T 1, T 3 and Cg 1 to 3.
  It does not mark T 2, whose six sessions ended in Grok's "cancelled" (several causes, `metrics.session_stop`), so
  T 2 still has to be moved aside by hand before the rerun.
- **The pilot suite's wall-clock limits (F38)** were budgets for a few subprocess calls, not what its tests assert:
  `CALL_TIMEOUT_SECONDS` 180 (was 45) and B's hold `HOLD_TIMEOUT_SECONDS` 120 (was 20). A passing call returns as
  soon as it is done, and the hold ends at C's launch, so a passing run costs nothing more. It took 168 s alone
  while another suite ran beside it (72.5 s recorded). The journal's earlier "own slot" idea is not needed.

**Tests.** Three in `RoundSpeedups` fail on main's `experiment.py` (1 error, 2 failures) and pass with the fix:
`test_a_slice_the_host_refused_is_a_host_failure_never_a_score`, the R3 T 1 stderr verbatim, plus a passing slice, a
429, a product's 404 and no stderr, none of which count;
`test_run_moves_a_refused_slice_aside_reruns_it_and_stops_at_a_new_refusal`;
`test_the_queue_starts_no_more_samples_after_a_host_refusal` (one job: T 1 and Cg 1 ran, then "6 samples not
started"). There is also a card test. `shiploop-e2e-experiments` now has 58 tests. Of 7 runs of the suite, 6 were OK.
One, run beside another Python process, ended "FAILED (errors=1)" without its traceback kept, and it did not recur in
4 reruns. It is unexplained and noted here as exploratory.

**R3 rerun.** The plan's command wrote `--timeout 10800` in two words, which `experiment.py` refuses; it now reads
`--timeout=10800`. R3's arms are pinned to 9ed4ec24, so it runs from the frozen worktree at `da86f8a0` with this fix
cherry-picked onto a local branch there (old-shape fixtures, new host check).

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F39 | A macOS-only stat field passed every local check and failed Linux CI: local runs cannot prove a platform-portable harness, CI can. | firm | run 40340118933, `6b6ce383` |
| F40 | Reading the host's own refusal (HTTP 401/402/403) separates "the host could not run" from "the arm did not deliver" without guessing; Grok's "cancelled" stays ambiguous. | firm (5 of 6 R3 slices marked; T 2 not) | R3 folders; the three RoundSpeedups tests |

## 10. 2026-10-26: R3 rerun after a top-up (one sample delivered, then the balance ran out again)

**Question.** Owner, 2026-10-26: "I've added more credits, so you should be able to run now." R3 on K2 again: arms T
and Cg, 3 full-item slices each, 4 at a time.

**Conditions.** One test Grok call ended `end_turn` with no 402. E-EFF1 confirmed it needed no Grok. The notice to
the E2E session expired undelivered (different permission modes). The queue started at 10:00 from the frozen worktree,
local branch `r3-run-host-fix-572f8a` (`da86f8a0` plus this day's host-failure and card fixes), into
`/Users/dadleet/e2e-runs/e6-r3-20261026` with `--timeout=10800`, under the default planning review (stage).

**Results.** The balance ran out again at about 10:48, roughly 48 minutes of 4 parallel slices (about 190
slice-minutes). The host-failure fix worked as built: each refused slice was reported, and the queue started nothing
more (Cg 3 never launched).

| Sample | Outcome | Steps planned | Implement steps done | Minutes | Note |
| --- | --- | --- | --- | --- | --- |
| T 1 | delivered, every slice check passed | 2 | 2 (265 s each) | 39.7 | 156 turns, input peak 205k, 5 Improve children of 1 pass each, no send-backs |
| T 2 | host refused (402) at implement | 10 | 1 (622 s) | 47.4 | not scored |
| T 3 | host refused (402) before step-plan ended | – | 0 | 7.0 | not scored |
| Cg 1 | host refused (402) at document | 4 | 4 (337 s each) | 48.0 | test stage passed; not scored |
| Cg 2 | host refused (402) at implement | 15 | 2 (490 s each) | 47.4 | not scored |
| Cg 3 | not started | – | – | – | the queue stopped |

Only T 1 is a result. The rest are descriptive, read from the refused slices' own records (`e6_downstream.score`).
The frozen harness's `metrics.improve_reviews` reads Improve reviews one folder too deep, so it shows 0 passes for 5
children. Main's reader reads both layouts (fixed 2026-10-25), so R3's Improve passes are counted with main's reader.

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F41 | A full K2 item on Grok took about 40 to 50 minutes, and 4 parallel slices spent the top-up in about 48 minutes (about 190 slice-minutes). The 5 open samples need about 200 to 275 slice-minutes, roughly 1 to 1.4 times that top-up. | interim (one delivered item, four partial) | R3 slice records; queue.log |
| F42 | Under the full stage review, K2 step plans ranged 2 to 15 (T 2, 10; Cg 4, 15), wider than the shape rounds (R1: T 1 to 6, Cg 2 to 10). | exploratory (n = 4 plans) | step-plan results of the R3 slices; R1 score.json |

**Next.** R3 needs another top-up for its 5 open samples. A refused slice cannot be resumed (`slice.py`: that stop is
final), so each restarts from its seed.

## 11. 2026-10-28: R3 moves to today's ShipLoop on DeepSeek flash (E6D2)

**Question.** Owner, 2026-10-28: "I want to use DeepSeek Flash for the test runs", and "we should be able to use
Claude with DeepSeek as the harness and model". Grok is out of credits until its weekly reset, and R3 on Grok has one
delivered sample (entry 10).

**Design.** The R3 round on Grok cannot simply switch hosts. Its arms are pinned to 9ed4ec24, whose seed records only
the frozen harness at `da86f8a0` can still write, and that harness predates the Claude host on Ollama. R3 therefore
moves to today's ShipLoop. The bound has shipped since 2.11.0, so the question becomes sharper: does the shipped bound
deliver better than the same ShipLoop without it?
- Experiments `E6D2-K2` (node-chess-engine) and `E6D2-K4` (node-battleship-server), the original R3 request's two
  cases. Full items from step-plan to carry-forward, 3 samples per arm, descriptive, evaluator `e6_downstream.py`.
- Both arms are pinned to `337b09c5`. Cg is ShipLoop as shipped (no overlay). T is the same commit with the
  `e6-no-size-bound` overlay: one edit, the step-plan duty's sizing bullet back to its wording before the bound (no
  cap of 4 criteria and 3 product files; today's "proof" for "check"). The arms differ in the bound only.
- Subject: the Claude host (Claude Code) on `deepseek-v4.1-flash:1017-cloud` through the local Ollama server, the E2E
  default since 2026-10-26 (`hosts.RUN_DEFAULT_BACKEND`). `experiment.py --host` now defaults to `claude`, the last
  driver that still defaulted to Grok. `--host grok` and `--backend=anthropic` remain.
- Planning review: the default (stage). Timeout `--timeout=14400`: a full battleship run takes about 222 minutes on
  DeepSeek flash.

R3 on Grok (`E6D-K2`) stays as recorded in entries 8 to 10, and its comparison is not resumed here. The two rounds
differ in subject and in ShipLoop version, so no sample from one is read with the other.

## 12. 2026-10-28: R3 on DeepSeek flash (E6D2): 12 of 12 delivered; the shipped bound was faster and more predictable

**Question.** Does the step bound shipped in 2.11.0 deliver a full item better than the same ShipLoop without it?
The design is in entry 11.

**Conditions.** `experiment.py queue E6D2-K2 E6D2-K4 --arms T,Cg --samples 3 --jobs 4 --timeout=14400`. It ran from
10:36 to about 16:30 from the harness at `7c89dd4f` (worktree locked while it ran), with both arms pinned to
`337b09c5`, into `/Users/dadleet/e2e-runs/e6d2-deepseek-20261028`. Each slice was Claude Code through the local Ollama
server on `deepseek-v4.1-flash:1017-cloud`, confirmed in every slice's `invocation.json` (host claude, backend ollama,
that model). An E2E battleship run on the same model shared the server. No host refusal and no rate limit occurred:
the "429" strings in the event logs are token counts and timestamps.

**Results.** Every slice passed its process, inner-loop, overshoot, assembly and checks verdicts, so `decide` reads
both experiments as **ceiling** (delivery cannot separate the arms). The cost fields carry the comparison
(`r3_report.py`, exported as `docs/experiments/shiploop-plan-sizing-20261024/e6d2-report.json`):

| Case | Arm | Item minutes (median) | Steps planned | Implement s/step (median) | Turns (median) | Improve passes (median) | Send-backs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| K2 | T (no bound) | 72.7, 124.3, 145.5 (124.3) | 4, 7, 10 | 231 | 919 | 8 | 1, 0, 0 |
| K2 | Cg (shipped) | 78.3, 51.9, 63.4 (63.4) | 5, 6, 5 | 158 | 665 | 5 | 1, 0, 0 |
| K4 | T (no bound) | 123.9, 127.0, 82.9 (123.9) | 6, 3, 6 | 262 | 1,044 | 9 | 0, 0, 0 |
| K4 | Cg (shipped) | 96.1, 153.2, 55.9 (96.1) | 4, 5, 5 | 283 | 1,105 | 8 | 0, 0, 1 |

Totals across the three items: K2 193.6 minutes with the bound against 342.5 without it (−43%) and 2,236 turns against
2,785 (−20%). K4: 305.2 minutes against 333.8 (−9%) and 3,224 turns against 3,116 (+3%). Peak input was 144k to 155k
tokens in every slice.

| ID | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F43 | With the shipped bound, delivery is unchanged (12 of 12) and the median item finished sooner on both cases: 63 against 124 minutes (chess engine), 96 against 124 (battleship server). | interim (3 per arm per case, DeepSeek flash only; descriptive, no A/A spread) | e6d2-report.json; decision-T-Cg.json (ceiling) |
| F44 | The bound narrows plan size rather than inflating it: 5 to 6 steps against 4 to 10 (K2), 4 to 5 against 3 to 6 (K4). The largest unbounded plan (K2 T 3, 10 steps) was the slowest K2 item (145.5 minutes). | interim | step-plan results; e6d2-report.json |
| F45 | Tokens: turns fell 20% with the bound on K2 and rose 3% on K4 (no difference); peak input was the same in both arms. | interim | e6d2-report.json |
| F46 | DeepSeek flash plans the chess engine as 4 or more steps even without the bound, where Grok planned 1 to 2, so the bound's effect here is a narrower range, not more steps. | exploratory (compares two subjects across rounds) | E6D2 against R1 and R3 on Grok |

**Decision.** Keep the step bound as shipped. Under the decision priority (quality, then tokens, then time), quality
ties at 12 of 12. Tokens tie or favour the bound, and time favours it on both cases. The plan's "relax if slower with
no gain" branch does not apply. A firm claim would need 4 samples per arm, to measure the A/A spread. It would also
need a second subject (Grok 4.7 after its reset) to show the effect is not DeepSeek's alone.

**Harness.** `r3_report.py` reads `E6D*-*` folders (it read only `E6D-*`, so it skipped E6D2).
