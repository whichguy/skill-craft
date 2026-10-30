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
| 2026-10-24 | E6-K1 | T=9ed4ec24 vs B=9ed4ec24+e6-size-prose.json | 4/4 | 0.25/0.75 | 0.50 | - | **inconclusive**: +0.50 is inside the A/A spread 0.50 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K1/decision-T-B.json |
| 2026-10-24 | E6-K1 | T=9ed4ec24 vs C=9ed4ec24+e6-size-gate.json | 4/4 | 0.25/1.00 | 0.50 | - | **supports**: mean 1.00 vs 0.25: +0.75 beyond the A/A spread 0.50 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K1/decision-T-C.json |
| 2026-10-24 | E6-K1 | B=9ed4ec24+e6-size-prose.json vs C=9ed4ec24+e6-size-gate.json | 4/4 | 0.75/1.00 | 0.50 | - | **inconclusive**: +0.25 is inside the A/A spread 0.50 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K1/decision-B-C.json |
| 2026-10-24 | E6-K3 | T=9ed4ec24 vs B=9ed4ec24+e6-size-prose.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K3/decision-T-B.json |
| 2026-10-24 | E6-K3 | T=9ed4ec24 vs C=9ed4ec24+e6-size-gate.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K3/decision-T-C.json |
| 2026-10-24 | E6-K3 | B=9ed4ec24+e6-size-prose.json vs C=9ed4ec24+e6-size-gate.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K3/decision-B-C.json |
| 2026-10-24 | E6-K5 | T=9ed4ec24 vs B=9ed4ec24+e6-size-prose.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K5/decision-T-B.json |
| 2026-10-24 | E6-K5 | T=9ed4ec24 vs C=9ed4ec24+e6-size-gate.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K5/decision-T-C.json |
| 2026-10-24 | E6-K5 | B=9ed4ec24+e6-size-prose.json vs C=9ed4ec24+e6-size-gate.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K5/decision-B-C.json |
| 2026-10-24 | E6-K1 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 0.25/0.75 | 0.50 | - | **inconclusive**: +0.50 is inside the A/A spread 0.50 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K1/decision-T-Cg.json |
| 2026-10-24 | E6-K1 | C=9ed4ec24+e6-size-gate.json vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/0.75 | 0.00 | - | **contradicts**: no better: mean 0.75 vs 1.00 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K1/decision-C-Cg.json |
| 2026-10-24 | E6-K3 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K3/decision-T-Cg.json |
| 2026-10-24 | E6-K3 | C=9ed4ec24+e6-size-gate.json vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K3/decision-C-Cg.json |
| 2026-10-24 | E6-K5 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K5/decision-T-Cg.json |
| 2026-10-24 | E6-K5 | C=9ed4ec24+e6-size-gate.json vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K5/decision-C-Cg.json |
| 2026-10-25 | E6-K2 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 0.50/0.75 | 0.00 | - | **supports**: mean 0.75 vs 0.50: +0.25 beyond the A/A spread 0.00 | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K2/decision-T-Cg.json |
| 2026-10-25 | E6-K6 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K6/decision-T-Cg.json |
| 2026-10-25 | E6-K7 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K7/decision-T-Cg.json |
| 2026-10-25 | E6-K4 | T=9ed4ec24 vs Cg=9ed4ec24+e6-size-gate-generic.json | 4/4 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6-r1-20261024/E6-K4/decision-T-Cg.json |
| 2026-10-28 | E6D2-K2 | T=337b09c5417f81a8949a4ee8351361baa373ea79+e6-no-size-bound.json vs Cg=337b09c5417f81a8949a4ee8351361baa373ea79 | 3/3 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6d2-deepseek-20261028/E6D2-K2/decision-T-Cg.json |
| 2026-10-28 | E6D2-K4 | T=337b09c5417f81a8949a4ee8351361baa373ea79+e6-no-size-bound.json vs Cg=337b09c5417f81a8949a4ee8351361baa373ea79 | 3/3 | 1.00/1.00 | - | - | **ceiling**: every sample of both arms scored 1: the case does not separate the arms at this bound, so change the case before adding samples | /Users/dadleet/e2e-runs/e6d2-deepseek-20261028/E6D2-K4/decision-T-Cg.json |
| 2026-10-30 | E7-K1 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json | 4/4 | 0.84/0.81 | 0.06 | - | **contradicts**: no better: mean 0.81 vs 0.84 | /Users/dadleet/e2e-runs/e7-20261030/E7-K1/decision-A-P.json |
| 2026-10-30 | E7-K1 | P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 4/4 | 0.81/0.83 | 0.11 | - | **inconclusive**: +0.02 is inside the A/A spread 0.11 | /Users/dadleet/e2e-runs/e7-20261030/E7-K1/decision-P-C.json |
| 2026-10-30 | E7-K1 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 4/4 | 0.84/0.83 | 0.06 | - | **contradicts**: no better: mean 0.83 vs 0.84 | /Users/dadleet/e2e-runs/e7-20261030/E7-K1/decision-A-C.json |
| 2026-10-30 | E7-K1 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs M=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-m.json | 4/4 | 0.84/0.86 | 0.06 | - | **inconclusive**: +0.03 is inside the A/A spread 0.06 | /Users/dadleet/e2e-runs/e7-20261030/E7-K1/decision-A-M.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json | 4/4 | 0.55/0.58 | 0.13 | - | **inconclusive**: +0.03 is inside the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-P.json |
| 2026-10-30 | E7-K2 | P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 4/4 | 0.58/0.75 | 0.14 | - | **supports**: mean 0.75 vs 0.58: +0.17 beyond the A/A spread 0.14 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-P-C.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 4/4 | 0.55/0.75 | 0.13 | - | **supports**: mean 0.75 vs 0.55: +0.20 beyond the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-C.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs M=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-m.json | 4/4 | 0.55/0.62 | 0.13 | - | **inconclusive**: +0.08 is inside the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-M.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 8/8 | 0.45/0.69 | 0.13 | - | **supports**: mean 0.69 vs 0.45: +0.23 beyond the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-C.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs D=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-d.json | 8/8 | 0.45/0.63 | 0.13 | - | **supports**: mean 0.63 vs 0.45: +0.18 beyond the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-D.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs M=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-m.json | 8/8 | 0.45/0.65 | 0.13 | - | **supports**: mean 0.65 vs 0.45: +0.19 beyond the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-M.json |
| 2026-10-30 | E7-K2 | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json | 8/4 | 0.45/0.58 | 0.13 | - | **inconclusive**: +0.13 is inside the A/A spread 0.13 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-A-P.json |
| 2026-10-30 | E7-K2 | D=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-d.json vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 8/8 | 0.63/0.69 | 0.40 | - | **inconclusive**: +0.05 is inside the A/A spread 0.40 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-D-C.json |
| 2026-10-30 | E7-K2 | P=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-p.json vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 4/8 | 0.58/0.69 | 0.14 | - | **inconclusive**: +0.11 is inside the A/A spread 0.14 | /Users/dadleet/e2e-runs/e7-20261030/E7-K2/decision-P-C.json |
| 2026-10-30 | E7-K2 | note on the n=8 lines above | - | - | - | - | **read with design §7b**: the three "supports" (C, D, M over A) are within an A/A gap measured in the same round (7 arm-M runs that behaved as A scored +0.17 over A, p 0.08); against all 15 A-condition runs C is +0.15 (p 0.06), D +0.10 (p 0.17); no arm adopted | docs/shiploop-test-stage-prompt-design-2026-10-30.md §7b; docs/experiments/test-stage-prompt-20261030/e7_analysis.py |
| 2026-10-30 | E7-F | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs D=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-d.json | 8/8 | 0.60/0.63 | 0.00 | - | **supports**: mean 0.63 vs 0.60: +0.02 beyond the A/A spread 0.00 | /Users/dadleet/e2e-runs/e7-20261030/E7-F/decision-A-D.json |
| 2026-10-30 | E7-F | A=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 8/8 | 0.60/0.58 | 0.00 | - | **contradicts**: no better: mean 0.58 vs 0.60 | /Users/dadleet/e2e-runs/e7-20261030/E7-F/decision-A-C.json |
| 2026-10-30 | E7-F | D=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-d.json vs C=7fce12e4b9edff9b2c849bc8f8402ea7f63f143d+e7-c.json | 8/8 | 0.63/0.58 | 0.17 | - | **contradicts**: no better: mean 0.58 vs 0.63 | /Users/dadleet/e2e-runs/e7-20261030/E7-F/decision-D-C.json |
| 2026-10-30 | E7-F | note on the three lines above | - | - | - | - | **read with design §7d**: no arm adopted. Over all 8 + 8 samples A vs D is +0.02 (p 0.50) and A vs C −0.02 (p 0.84); A's 2-against-2 spread was 0.00 on this discrete metric, so the "supports" is noise | docs/shiploop-test-stage-prompt-design-2026-10-30.md §7d |
