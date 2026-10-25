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

**What the port carries from the evidence.** Cg = prose and gate, the gate never refused, so the shipped text is the
one every Cg sample planned under (F28). The verdicts it rests on: K2 supports (F25), K1 inconclusive (F21, F23), and no
harm on the five other cases (F27). The open questions travel with it: count against text (F29), many tiny steps
(F30), and the downstream cost (R3, not run).
