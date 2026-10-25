---
Execute: ask
Status: R-1 (corpus analysis) done 2026-10-24; R0 (harness) built 2026-10-24 as E6 of the template-field harness,
  one smoke sample; R1 and R1g done 2026-10-24; R2 (shape on K2, K4, K6, K7) done 2026-10-25; R3 (downstream) not
  started
Branch: exp/plan-sizing-1b1e33, on the template-field harness branch 78ea131b (worktree-agent-a34bc5d47d282ddad)
Opened: 2026-10-24
Consumer: the owner, who approves, strikes or re-scopes a round before any run is launched; later, whoever changes a
  planning template and needs to re-validate it
Journal: docs/shiploop-plan-sizing-journal.md
---

# ShipLoop plan sizing (E-SIZE1): are steps small enough for the inner loop?

Question (owner, 2026-10-24): once ShipLoop has a prompt and plans it, are the plan's steps small enough to implement
inside the iteration loops, or are they at times too big? Analyse, then optimise the planning templates, with
experiments built so they can be **rerun whenever a template changes again**, and so the same setup serves later
prompt-refining work.

## 0. What the saved runs already say (R-1, journal entry 1)

Corpus: every ShipLoop run under `/Users/dadleet/e2e-runs` (51 full runs, 63 work items with an accepted step plan,
95 implement loop receipts), measured by
[`plan_shape.py`](experiments/shiploop-plan-sizing-20261024/plan_shape.py); rows in
[`plan-shape-rows-2026-10-24.json`](experiments/shiploop-plan-sizing-20261024/plan-shape-rows-2026-10-24.json), table in
[`plan-shape-summary-2026-10-24.txt`](experiments/shiploop-plan-sizing-20261024/plan-shape-summary-2026-10-24.txt).

- **Oversized steps are a Grok 4.7 behaviour, worst when the only proof is a remote deploy.** Sonnet 5.5: 39 items,
  median 3 steps, p90 3 criteria per step (max 7, one step). Luna: 5 steps per item. Grok 4.7 medium: 14 of 20 items in one step, up to 12 criteria in it; all 8 Salesforce chess items (three
  runs, 10/17 to 10/20) were one step.
- **The sizing prose worked for Grok on local work.** Before `STEP_SIZING` (10/11) Grok's battleship items were
  mostly one step; after it, local battleship split into 4 to 6 steps. Salesforce chess after it did not.
- **One chess step was an engine.** Chess run 4 W1 S1 (`DX project and SLChessEngine`): 7 criteria, 793 changed
  lines in 5 files, 21.4 minutes in one implement. Chess run 3 W2 put the whole rules engine (R-4 to R-9) under 2
  criteria. Steps of 6 or more criteria took 12 to 21 minutes; steps of 1 to 5 took a median of 0.5 to 2.3.
- **The loop does not absorb size.** All 95 implement receipts end at loop iteration 1: a step is one shot, however big.
- **Nothing measurable bounds a step.** The rule is "too large for one review"; the only gates are text lengths
  (task 700, criteria 1,200, item context 2,500 characters), which Grok met by compressing (W1's task: 698 characters).
- **The templates price splitting, not size.** `plan` duty 14 says every item "pays a fixed round of stages and
  reviews"; a step's `check` must run now with only accepted steps, and on a deploy-only target that is a deploy
  per step. Grok wrote: "One step, because the controller is a thin delegate and the games are one proof."
- **A file bound is the cleanest candidate gate.** Replayed offline, refusing a step that declares more than 3 paths
  caught 4 of the 8 chess steps and refused 0 of 34 other steps; the 4 it missed declared no paths (per-step `paths` is
  optional). Criteria counts and requirements served both refuse healthy Sonnet steps before they catch chess.

What the corpus cannot say: that a big step is *worse*. Chess run 4 built every item in one step each and reached
release-plan. The harm (one-shot reliability, a single Improve review over 800 lines, failure localisation, exposure
to a context clear mid-step) is the hypothesis the rounds below test, together with the opposite risk: over-split
steps each pay a lint gate, an Improve child and a commit.

## 1. Intent, outcome, self-grade

- **Intent.** Make step plans split work into units one implement iteration can carry, on every host and platform,
  without splitting small items, and leave behind a suite that re-validates any later planning-template change.
- **Observable end outcome.** (a) A template test suite: cases with declared shape bands, a script scorer that
  verifies itself, and pinned arms, run by `experiment.py run|score|decide`; (b) one `experiment.py decide` record per
  case and pair (`<out>/E6-K<n>/decision-<X>-<Y>.json`, one line in
  `docs/shiploop-template-experiments-journal.md`), summarised in this experiment's journal; (c) if an arm wins, the
  template change with its change note, in a commit that cites those records.
- **Self-grade** (not done until all hold): every case states its band before any arm runs (committed with R0); every
  arm names a commit; control and arms run under one recorded condition (host, model, effort, case revision); the
  scorer is a script, not a model, and its verify passes; the journal entry is in the same commit as each result; a
  small-item control never gets more steps under the winner than under control.

## 2. Candidate changes (arms)

Arms are plugin builds from a pinned commit plus an optional prompt overlay on the build copy
([`test/shiploop_e2e/overlay.py`](../test/shiploop_e2e/overlay.py)); nothing under `skills/` changes until an arm wins.

| Arm | Build | Change |
| --- | --- | --- |
| A | release 2.8.0 (`288075c9`) | none: the version chess run 4 ran |
| T, control | `9ed4ec24`, the templates branch's text-only batch | none |
| B, measurable prose | T + [`overlays/e6-size-prose.json`](../test/shiploop_e2e/overlays/e6-size-prose.json) | step-plan duty 4: a step satisfies at most 4 criteria and changes at most 3 product files (a `-meta.xml` sidecar counts with its file; tests, docs and the step's own check script do not); more, or a second module or layer, is another step. Per-step `paths` are required. On a remote-only target the steps share one proof script that each step extends, so a split costs one more run, not a new script. |
| C, gate | T + [`overlays/e6-size-gate.json`](../test/shiploop_e2e/overlays/e6-size-gate.json) | B's three edits, plus the same bound as a refusal in `_check_step_sizing` (at `complete` and `--check-only`): a step without `paths`, over 3 product files or over 4 criteria is refused with the split rule. Grok runs check-only on every draft, so a script refusal reaches it where prose did not. |

Why two counts (R0 finding, journal entry 2): a file count catches the layer-crossing step (chess run 4 W3: 6 product
files) but not the engine (W1: one engine file, two product files once tests and config are left out). The criteria
cap catches W1 (7 criteria), and the existing 1,200-character limit on a step's criteria text stops a model from
dodging it with fewer, larger criteria. Both bounds come from the replay in section 0; R1 may move them.

**Genericity (owner rule, restated 2026-10-24 with the Apex revert `df6b91e2`).** ShipLoop text, catalogs and gates
name no technology. Arms B and C, as run in R1, carry one stack detail: "a `-meta.xml` sidecar counts with its file"
in the duty-4 text and the matching `-meta.xml` collapse in C's gate. The general lesson is "a companion file that only
describes another file counts with that file". A winning arm ships only in a generic wording, and that wording is
re-validated (K1, K3, K5 × 4 samples) before any ShipLoop change. The evaluator, which is harness and not ShipLoop, may
keep the explicit `-meta.xml` rule.

Not in these arms: `plan` duty 14. Every E6 case seeds at step-plan, so the plan stage is synthetic and an edit to it
could not be observed. A plan-stage case (seed at `plan`, stop after `plan`, score items per plan) is the follow-up if
step sizing alone does not shrink the effective unit of work. The `STEP_SIZING` constant is also left alone: it is
defined in `shiploop_prompts.py` but printed by no packet (R0 finding); the text the model reads is duty 4.

## 3. The template test suite: cases and expectations

Each case is a step-slice case in [`test/shiploop_e2e/step_cases.json`](../test/shiploop_e2e/step_cases.json) with a
`shape` band written before any run, and one experiment per case in
[`experiments.json`](../test/shiploop_e2e/experiments.json) (`E6-K1` to `E6-K7`: seed at step-plan, stop after
step-plan, arms A, T, B, C, 4 samples each). A **replay case** starts where a real run's step plan started: that run's
worktree at the commit before the item's step-plan, its request verbatim, the plan's work item, and the plan's concern
rows, assumptions and summary as seeded records. [`build_fixtures.py`](experiments/shiploop-plan-sizing-20261024/build_fixtures.py)
writes them from the saved runs and `--check` proves the committed copies still match.

| Experiment | Case | Built from | Band (`shape`) |
| --- | --- | --- | --- |
| E6-K1 | `sf-chess-engine` (fake `sf`) | chess run 4 at `a6044d1`, item W1 | steps ≥ 3 |
| E6-K2 | `node-chess-engine` | K1's spec R-1 to R-5 and NFR-1 ported to a Node module | steps ≥ 3 |
| E6-K3 | `sf-chess-board-entry` (fake `sf`) | chess run 4 at `5383110`, item W3 | steps ≥ 2; no step touches both `lwc/` and tabs, apps or flexipages |
| E6-K4 | `node-battleship-server` | battleship-1 at `69b31b9`, item W2 (Grok split it into 6) | 2 ≤ steps ≤ 7 |
| E6-K5 | `node-fix-bug` | existing case | steps = 1 |
| E6-K6 | `node-rename` | existing case | steps = 1 |
| E6-K7 | `node-add-function` | existing case | 1 ≤ steps ≤ 2 |

The scorer, [`evaluators/e6_step_size.py`](../test/shiploop_e2e/evaluators/e6_step_size.py), gives 1 when the step
count is inside the band and no step joins a separated pair; it also reports criteria, requirements served and product
files per step, so the bounds can be re-derived. Its `verify` scores four committed step-plan excerpts (run 4 W1 and W3
fail; battleship-1 W2 and Sonnet's checkers-1 W1 pass) and six planted plans.

**Replay fidelity limits.** The knowledge files cite the old run's evidence as `run/notes/...` and `run/scratch/...`,
which resolve against the new seed run and are absent; the earlier stages are synthetic records, not the real
results; the fake org starts at the Developer Edition baseline, so a step plan that queries for W1's deployed engine
(K3) sees none. The first two also keep the old run's later notes, including its one-step plan, out of reach.

## 4. Harness: what existed and what R0 added

R0 found the harness this section first planned already built on the template-field experiment branch (`c55c5374` to
`78ea131b`, `test/shiploop_e2e/experiment.py`): `slice.py --seed-at/--stop-after/--ref/--overlay`, pinned arms,
script evaluators with `verify`, `run`/`score`/`decide` with the A/A-spread rule and a decisions journal
([`docs/shiploop-template-experiments-journal.md`](shiploop-template-experiments-journal.md)). E6 is one more
experiment there; the planned `score_shape.py`, manifest freezer and `report.py` were not needed (arms pin commits and
`experiment.py` refuses mixed commits per arm).

R0 added:

| Addition | Where |
| --- | --- |
| A case-level `fake_sf` (`{"orgs": "de"}`): `fake_sf.py` first on PATH as `sf`, for the host and for this process, so neither the host's commands nor the grading checks nor a regrade can reach the real logged-in org | `slice.py` `fake_sf` (three small hunks; none in `drive()` or the session loop) |
| Seven cases, four replay fixtures and their builder | `step_cases.json`, `fixtures/{chess-sf-w1,chess-sf-w3,battleship-w2,chess-node-w1}`, `build_fixtures.py` |
| The scorer and its verify records | `evaluators/e6_step_size.py`, `evaluators/e6_records/` |
| Arms B and C | `overlays/e6-size-prose.json`, `overlays/e6-size-gate.json` |
| Hermetic tests (no model): verify, every case's band and fixture, each replay seeds and its packet names the item, the fake is first on both PATHs, arm C's gate on T's own navigator | `test/shiploop-e2e-experiments.test.py` `PlanSizing` |

The fixture test in `test/shiploop-e2e-slice.test.py` no longer requires a `package.json` and item `W1`: a replay
keeps its run's tree (a Salesforce project, a zero-dependency Node app) and item ID.

**Coordination** (2026-10-24). The E-EFF1 session keeps uncommitted edits to `slice.py`, `run.py` and two tests in the
canonical checkout, hashes `run.py`, `slice.py`, `sessionlog.py`, `hosts.py`, `metrics.py` and `clear.py` in its frozen
manifest, and asked for no Grok runs while its R1 pair runs and a word before anything touching those files lands on
main. The templates-branch session (`feat/shiploop-templates-6d625a`, shipping as 2.9.0) renames a step's `check` to
`proof` after `9ed4ec24`: a winning arm ported there uses `proof`.

## 5. Rounds

- **R0, harness** (done 2026-10-24): section 4, plus one smoke sample of E6-K1 arm T on Claude Sonnet 5.5 (journal
  entry 2). Commands:
  `python3 test/shiploop_e2e/experiment.py verify E6-K1` and
  `python3 test/shiploop_e2e/experiment.py run E6-K1 --arm T --sample 1 --host claude --out <dir>`.
- **R1, shape** (`--stop-after step-plan`), per case: `experiment.py run E6-K<n> --arm T|B|C --samples 4 --host grok`,
  then `score E6-K<n>` and `decide E6-K<n> T B`, `decide E6-K<n> T C`. On Grok 4.7 medium that is 7 cases × 3 arms × 4
  samples = 84 slices; arm A on E6-K1 only (4 more) checks that the release still reproduces run 4. Sonnet 5.5 runs
  T and the leading arm on all seven as the no-regression host (56). Order: E6-K1, K3, K5 first (the failure, the layer
  crossing, the over-split guard); stop early if every arm is at the ceiling or floor there. Secondary measures:
  criteria, requirements and product files per step, step-plan minutes, check-only refusals, tokens.
- **R1g, generic re-validation** (owner, 2026-10-24: "if B or C wins, reword it generically and re-validate on K1, K3
  and K5 before any ShipLoop change"): arms `Bg` and `Cg` on E6-K1, K3 and K5
  ([`e6-size-prose-generic.json`](../test/shiploop_e2e/overlays/e6-size-prose-generic.json),
  [`e6-size-gate-generic.json`](../test/shiploop_e2e/overlays/e6-size-gate-generic.json)): the sidecar clause becomes
  "a file that only describes another changed file counts with it", and Cg's gate counts a file whose name is another
  listed file's name plus a suffix starting with a separator with that file, with no stack's file convention. Only the
  R1 winner's generic arm runs (4 samples per case), after E-EFF1's Grok pair; it ships only if it keeps the
  winner's result against T.
- **R2, shape on the remaining cases** (done 2026-10-25, journal entry 5; owner: "Skip extra K1 samples; run K2, K4,
  K6 and K7 with T and Cg, 4 samples each"): `experiment.py run E6-K<n> --arm T|Cg` at `--stop-after step-plan`, 32
  slices on Grok 4.7 medium in four lanes, then `score` and `decide E6-K<n> T Cg`. This name was the downstream
  round's until 2026-10-25; that round is now R3.
- **R3, downstream** (full slices, step-plan to carry-forward): K2, K4 × T and the R1 winner × 3 on Grok (12 runs). K1
  and K3 need a real Apex run to finish an item, so a downstream round on them needs the owner's go for org `de`.
  Quality first: slice verdicts (`inner_loop`, `assembled`, `checks`), send-backs, Improve material findings per step;
  then tokens; then item minutes and implement minutes per step. This is the round that says whether smaller steps
  are actually better, not just smaller.

**Decision rule** (memory `eval-decision-priority`; `skills/rubric-eval/SPEC.md` section 8): quality, then tokens,
then time; a tie keeps the control. Blocking for any arm: a K5 to K7 case over its band in a majority of repetitions,
or a slice check that passes under control and fails under the arm.

**Cost estimate** from R-1 medians (Grok: step-plan 1.1 minutes, p90 8.0; one item's inner loop 20, p90 51.5) plus
seeding, plugin build and the step plan's Improve review, which a stopped slice still runs (planning review `stage`):
R1 on Grok is roughly 84 slices at 5 to 15 minutes, 7 to 21 hours serial, less if the first three cases settle it; R3
about 4 to 10 hours. Grok has no spend cap in the harness; a Claude slice takes `--max-budget-usd` (default 10).

## 6. Reuse for other templates and prompt refining

The unit is a **template case**: a fixture, the stage to seed at and stop after, and a script evaluator over that
stage's accepted result (`shape` bands here; another template states its own properties, as E1 to E5 do). To
re-validate a changed template:

1. Point arm T at the new commit (or add the change as an overlay on the current one) in `experiments.json`.
2. `experiment.py verify E6-K1` (the scorer still tells run 4's plans from good ones).
3. `experiment.py run E6-K<n> --arm T --samples 4 --host grok` for each case, then `score` and `decide` against the
   last accepted arm's samples.

A new failure seen in a real run becomes a new replay case: add a row to `REPLAYS` in `build_fixtures.py` with the
run, its base commit, the item and a band, rebuild, and add its excerpt to `RECORDS` so `verify` covers it.
`rubric-eval` stays the tool for single-call wording A/B on frames; this suite is its stage-level complement, for
templates whose output depends on tools, gates and the repository (step-plan, plan, test-spec).

## 7. What this might harm

- Over-splitting: more steps each pay the lint gate, an Improve child and a step commit (K5 to K7, R3 tokens).
- A file count is a proxy: a two-file step can still hold an engine; R1's requirements-per-step column watches that.
- Platform sidecars (Salesforce `-meta.xml`) inflate counts unless collapsed; the scorer and gate must agree on how.
- Packet length: arm B adds about four lines to every step-plan packet.
