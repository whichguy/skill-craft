# Planning stage clock, battleship, three runs (accept to accept, minutes)

| Stage | Grok 4.7 medium, 1.21.0 | Luna xhigh, 1.21.0 | Luna max, 1.16.1 |
|---|---|---|---|
| intake | 2.1 | 2.5 | 4.1 |
| discovery | 1.8 | 10.6 | 12.7 |
| research | 2.1 | 10.1 | 24.7 |
| spec | 20.0 | 55.0 | 52.7 |
| test-strategy | 19.6 | 79.8 | 94.3 |
| plan | 12.2 | 121.0 | 196.4 |
| prepare | 0.7 | 14.7 | 10.4 |
| select-work | 0.3 | 2.7 | 3.3 |
| step-plan | 9.4 | 38.7 | 187.7 |
| test-spec | 4.5 | 39.9 | 61.2 |
| **Planning window (intake to the first test-spec accept)** | **72.7** | **375.0** (375.9 by the engine's start stamp) | **647.5** |

Sources: Grok and Luna xhigh: `<run>/.shiploop-runs/*/run/timeline.json` (`accepted`) joined to `state.md` history, run
directories under /Users/dadleet/e2e-runs/20261005/ (v1210-battleship-grok-medium, v1210-battleship-luna-xhigh, both kept
on the owner's machine); Luna max: test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json. One run
each; stage times vary about 2x between runs of the same model. The exporter's intake reads 2.5 min where the harness line
says 3.4 (different start reference).

Luna xhigh after planning (not comparable to Grok, which was stopped at the end of test-spec): W1 baseline 2.9, test-author 14.2,
test-red 3.5 (outcome revise: the tests had no real module to load), then the redo: step-plan 120.1, test-spec 25.2,
baseline 5.1, test-author 12.2, test-red 3.3, implement 6.1, 2.1, 1.6, 12.2; stopped by the owner at 588 min in W1 implement.
The redo after the revise (165.9 min of stages vs 99.2 the first time through them) is 28% of that run.

Grok medium's Improve children: 5 children, 26 passes, 42.4 min (58% of its window): spec 9 passes 15.2 min, test-strategy 7
passes 13.1, plan 4 passes 5.2, step-plan 3 passes 6.4, test-spec 3 passes 2.5. Luna xhigh: 5 children, 22 passes, 203.4 min (54%).
