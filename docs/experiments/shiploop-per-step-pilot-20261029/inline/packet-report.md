# Packet report: /Users/dadleet/e2e-runs/20261029/pilot-terra-inline-32f436

Run status **active**. Emissions: run trace (RUN/trace.jsonl names every packet ShipLoop printed, kept as sent in packets/sent/). Tokens: characters / 4 (an estimate, not a tokenizer count).

- packets 15, emissions 15, characters written to packet files 249469 (~62367 tokens)
- reached the model: not measured on this host
- `next` calls 1, ShipLoop failures 3, model glue 0, turns –, cost unreported

**Slice PASS**: process PASS, inner_loop PASS, no_overshoot PASS, assembled PASS, checks PASS

Send-back loops 0; test-spec before implement: True.
Gates not exercised: none (10 base-run and mutation-check records, none says skipped).

## Packets

| # | stage | kind | outcome | chars | ~tokens | emissions | next | repeated | skill refs | missing | largest section |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intake | producer | done | 11681 | 2920 | 1 | 0 | 0% | 2 | 0 | Result template: (6345) |
| 2 | step-plan | producer | done | 24316 | 6079 | 1 | 1 | 21% | 11 | 0 | Current stage guidance: (9029) |
| 3 | improve (step-plan) | improve | done | 1569 | 392 | 1 | – | 0% | 1 | 0 | (opening) (1569) |
| 4 | test-spec | producer | done | 19744 | 4936 | 1 | 0 | 37% | 3 | 0 | Result template: (9842) |
| 5 | implement | producer | done | 25327 | 6331 | 1 | 0 | 36% | 6 | 0 | Result template: (10893) |
| 6 | test | producer | done | 23728 | 5932 | 1 | 0 | 40% | 3 | 0 | Result template: (8143) |
| 7 | document | producer | done | 21287 | 5321 | 1 | 0 | 53% | 3 | 0 | Result template: (9601) |
| 8 | improve (document) | improve | done | 1566 | 391 | 1 | – | 19% | 1 | 0 | (opening) (1566) |
| 9 | implement | producer | done | 25330 | 6332 | 1 | 0 | 77% | 6 | 0 | Result template: (11446) |
| 10 | test | producer | done | 25482 | 6370 | 1 | 0 | 80% | 3 | 0 | Result template: (9649) |
| 11 | document | producer | done | 23850 | 5962 | 1 | 0 | 82% | 3 | 0 | Result template: (12046) |
| 12 | improve (document) | improve | done | 1566 | 391 | 1 | – | 27% | 1 | 0 | (opening) (1566) |
| 13 | carry-forward | producer | done | 25239 | 6309 | 1 | 0 | 48% | 10 | 0 | Result template: (11452) |
| 14 | improve (carry-forward) | improve | done | 1581 | 395 | 1 | – | 18% | 1 | 0 | (opening) (1581) |
| 15 | system-test-author | producer | – | 17203 | 4300 | 1 | 0 | 50% | 2 | 0 | Result template: (8622) |

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
| step-plan | done | 83.1 | – | 20 | 77352 |
| test-spec | done | 17.0 | – | 4 | 85951 |
| validate-existing | done | 0% | – | 0 | – |
| implement | done | 22.0 | – | 5 | 96488 |
| test | done | 34.0 | – | 7 | 108269 |
| document | done | 41.0 | – | 11 | 121670 |
| implement | done | 19.0 | – | 4 | 129874 |
| test | done | 32.0 | – | 7 | 141601 |
| document | done | 34.0 | – | 8 | 150860 |
| carry-forward | done | 37.0 | – | 10 | 161302 |
| system-test-author (incomplete) | – | 30% | – | 0 | – |
