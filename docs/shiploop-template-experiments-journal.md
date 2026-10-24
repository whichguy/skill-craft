# ShipLoop template-field experiments journal

One line per `experiment.py decide`: the experiment, the arms compared (ref and overlay), n per arm, the mean score of
each arm, the A/A spread (the first arm's samples 1-2 vs 3-4), the verdict and the decision file. The plan, cases,
evaluators and arms are in test/shiploop_e2e/experiments.json; run outputs are not committed.

## Harness (2026-10-24, status: firm)

Built in test/shiploop_e2e/ (experiment.py, overlay.py, evaluators/e1-e5, experiments.json, overlays/, cases
stand-in-parser, ui-component, stateful-target and node-seeded-early-validation). Arms: A = release 2.8.0 (288075c9),
T = feat/shiploop-templates-6d625a (text-only batch), B = T plus a field overlay (round 1); in round 2 B names the built
commit with no overlay. Every evaluator verify passes (test/shiploop-e2e-experiments.test.py); E2 and E3 verify on run 4's
own records (W3 step-plan 0075307f, test-strategy 2214de28). Overlays are prompt-only: a test_cases row keeps its six keys,
so E1 asks for Stand-in rejected at the end of red, and E4 carries its targets row by value in the seeded step-plan
summary that the test-spec packet quotes.

## Round 2 harness (2026-10-24, status: firm for the harness, exploratory for the cases)

Round 1 hit a ceiling: every E1 and E3 sample in every arm scored 1.0, and `decide` called it inconclusive "for want of
samples 1-4", which hid the real cause. Changes (test/shiploop_e2e/):
- `judge` reports `ceiling` (every sample of both arms 1) or `floor` (every one 0) as its own verdict at any n; every
  experiment now runs 4 samples per arm, since the A/A spread needs the control's samples 1-4 (the docstring said so,
  the defaults were 5 and the round ran 3). Hermetic tests in test/shiploop-e2e-experiments.test.py (Decide).
- E1b (E1 kept as is for the record): case `stand-in-rules` on fixture node-orders, four subtle stand-ins each modelled
  on a run-4 miss (`one-rule-missing`, `tested-only`, `limit-never-trips`, `cross-field`); the value is the fraction
  killed (0-1). `verify E1b`: a run-4-style weak test file lets all four survive, a strong one kills all four. Arms
  A = 288075c9, T = 9ed4ec24, B = T + overlays/e1b-stand-in.json (a `Stand-in rejected:` line per row, absence paired
  with count assertions, budgets checked at their stated value).
- E2: overlay reworded to the built branch's names (`test_layers` keyed `code` and `layer`; `confirm:
  executed|searched|inspected`); arm F = d21c770e, the templates branch head at build time (its committed field is still
  `surfaces`; the evaluator reads `surfaces` and `test_layers` rows and the criterion `confirm` field). T and B pinned to
  9ed4ec24; E4 and E5 too, which clears the quick-tier "`old` occurs 0 times" failure of their B overlays.
- `run --sample N` runs exactly one sample, so each sample can be its own background task.

## E6 plan sizing (2026-10-24, status: firm for the harness, not yet run)

E6-K1 to E6-K7 ask whether a measurable step bound (arm B, prose) or the same bound as a refusal (arm C) keeps an item's
step plan inside its case's band, where Grok 4.7 put every Salesforce chess item in one step. Plan, cases and arms:
docs/shiploop-plan-sizing-experiment-plan-2026-10-24.md; findings: docs/shiploop-plan-sizing-journal.md. Harness
additions: `slice.py` case key `fake_sf`, four replay fixtures built by
docs/experiments/shiploop-plan-sizing-20261024/build_fixtures.py, evaluators/e6_step_size.py with committed verify
records, overlays e6-size-prose and e6-size-gate (against 9ed4ec24), tests `PlanSizing`.

## Decisions

| date | experiment | arms | n | means | spread | gate | verdict | record |
|---|---|---|---|---|---|---|---|---|
| 2026-10-24 | E1 | A=288075c9 vs T=9ed4ec24 | 3/3 | 1.00/1.00 | - | - | **inconclusive**: the first arm needs scored samples 1-4 for the A/A spread | /Users/dadleet/e2e-runs/experiments-r1-20261024/E1/decision-A-T.json |
| 2026-10-24 | E1 | T=9ed4ec24 vs B=9ed4ec24+e1-stand-in.json | 3/3 | 1.00/1.00 | - | - | **inconclusive**: the first arm needs scored samples 1-4 for the A/A spread | /Users/dadleet/e2e-runs/experiments-r1-20261024/E1/decision-T-B.json |
| 2026-10-24 | E1 | A=288075c9 vs B=9ed4ec24+e1-stand-in.json | 3/3 | 1.00/1.00 | - | - | **inconclusive**: the first arm needs scored samples 1-4 for the A/A spread | /Users/dadleet/e2e-runs/experiments-r1-20261024/E1/decision-A-B.json |
| 2026-10-24 | E3 | A=288075c9 vs T=9ed4ec24 | 3/3 | 1.00/1.00 | - | - | **inconclusive**: the first arm needs scored samples 1-4 for the A/A spread | /Users/dadleet/e2e-runs/experiments-r1-20261024/E3/decision-A-T.json |
