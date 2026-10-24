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

## Decisions

| date | experiment | arms | n | means | spread | gate | verdict | record |
|---|---|---|---|---|---|---|---|---|
