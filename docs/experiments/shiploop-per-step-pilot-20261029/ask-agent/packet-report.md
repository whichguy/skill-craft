# Packet report: /Users/dadleet/e2e-runs/20261029/pilot-terra-ask-agent-32f436

Run status **active**. Emissions: run trace, and packet-archive for the packets the trace never printed (stages the harness seeded). Tokens: characters / 4 (an estimate, not a tokenizer count).

- packets 15, emissions 15, characters written to packet files 286660 (~71665 tokens)
- reached the model: not measured on this host
- `next` calls 5, ShipLoop failures 0, model glue 0, turns –, cost unreported

**Slice PASS**: process PASS, inner_loop PASS, no_overshoot PASS, assembled PASS, checks PASS

Send-back loops 0; test-spec before implement: True.
Gates not exercised: none (10 base-run and mutation-check records, none says skipped).

## Packets

| # | stage | kind | outcome | chars | ~tokens | emissions | next | repeated | skill refs | missing | largest section |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intake | producer | done | 11951 | 2987 | 1 | 0 | 0% | 2 | 0 | Result template: (6594) |
| 2 | step-plan | producer | done | 26664 | 6666 | 1 | 2 | 20% | 11 | 0 | Result template: (10357) |
| 3 | improve (step-plan) | improve | done | 1590 | 397 | 1 | – | 0% | 1 | 0 | (opening) (1590) |
| 4 | test-spec | producer | done | 23171 | 5792 | 1 | 0 | 35% | 3 | 0 | Result template: (12448) |
| 5 | implement | producer | done | 29077 | 7269 | 1 | 0 | 35% | 6 | 0 | Result template: (12693) |
| 6 | test | producer | done | 27036 | 6759 | 1 | 0 | 44% | 3 | 0 | Result template: (10334) |
| 7 | document | producer | done | 25046 | 6261 | 1 | 1 | 55% | 3 | 0 | Result template: (12162) |
| 8 | improve (document) | improve | done | 1587 | 396 | 1 | – | 19% | 1 | 0 | (opening) (1587) |
| 9 | implement | producer | done | 28896 | 7224 | 1 | 0 | 72% | 6 | 0 | Result template: (13074) |
| 10 | test | producer | done | 30186 | 7546 | 1 | 0 | 80% | 3 | 0 | Result template: (12947) |
| 11 | document | producer | done | 28552 | 7138 | 1 | 1 | 82% | 3 | 0 | Result template: (15384) |
| 12 | improve (document) | improve | done | 1587 | 396 | 1 | – | 27% | 1 | 0 | (opening) (1587) |
| 13 | carry-forward | producer | done | 29166 | 7291 | 1 | 1 | 51% | 10 | 0 | Result template: (14510) |
| 14 | improve (carry-forward) | improve | done | 1602 | 400 | 1 | – | 18% | 1 | 0 | (opening) (1602) |
| 15 | system-test-author | producer | – | 20549 | 5137 | 1 | 0 | 53% | 3 | 0 | Result template: (11925) |

## Stages (metrics.py)

| stage | outcome | seconds | turns | tool calls | context peak |
|---|---|---|---|---|---|
| intake | done | – | – | – | – |
| discovery | done | – | – | – | – |
| research | done | – | – | – | – |
| spec | done | – | – | – | – |
| test-strategy | done | – | – | – | – |
| plan | done | – | – | – | – |
| prepare | done | – | – | – | – |
| step-plan | done | 324.6 | – | 39 | 71350 |
| test-spec | done | 69.0 | – | 5 | 77393 |
| validate-existing | done | 0% | – | 0 | – |
| implement | done | 66.0 | – | 4 | 83148 |
| test | done | 84.0 | – | 6 | 90379 |
| document | done | 225.0 | – | 24 | 101827 |
| implement | done | 67.0 | – | 4 | 107526 |
| test | done | 61.0 | – | 4 | 113730 |
| document | done | 180.0 | – | 19 | 124599 |
| carry-forward | done | 216.0 | – | 21 | 136770 |
| system-test-author (incomplete) | – | 0% | – | 0 | – |
