# Packet report: /Users/dadleet/e2e-runs/20261029/pilot-terra-ask-agent-OLD-32f436

Run status **active**. Emissions: run trace (RUN/trace.jsonl names every packet ShipLoop printed, kept as sent in packets/sent/). Tokens: characters / 4 (an estimate, not a tokenizer count).

- packets 11, emissions 11, characters written to packet files 212879 (~53219 tokens)
- reached the model: not measured on this host
- `next` calls 4, ShipLoop failures 6, model glue 0, turns –, cost unreported

**Slice PASS**: process PASS, inner_loop PASS, no_overshoot PASS, assembled PASS, checks PASS

Send-back loops 0; test-spec before implement: True.
Gates not exercised: none (5 base-run and mutation-check records, none says skipped).

## Packets

| # | stage | kind | outcome | chars | ~tokens | emissions | next | repeated | skill refs | missing | largest section |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intake | producer | done | 12023 | 3005 | 1 | 0 | 0% | 2 | 0 | Result template: (6638) |
| 2 | step-plan | producer | done | 28024 | 7006 | 1 | 2 | 19% | 12 | 0 | Result template: (10613) |
| 3 | improve (step-plan) | improve | done | 1618 | 404 | 1 | – | 0% | 1 | 0 | (opening) (1618) |
| 4 | test-spec | producer | done | 24141 | 6035 | 1 | 0 | 36% | 3 | 0 | Result template: (12790) |
| 5 | implement | producer | done | 32306 | 8076 | 1 | 0 | 38% | 7 | 0 | Result template: (14998) |
| 6 | test | producer | done | 31138 | 7784 | 1 | 0 | 51% | 3 | 0 | Result template: (13598) |
| 7 | document | producer | done | 28969 | 7242 | 1 | 1 | 63% | 3 | 0 | Result template: (15287) |
| 8 | improve (document) | improve | done | 1615 | 403 | 1 | – | 19% | 1 | 0 | (opening) (1615) |
| 9 | carry-forward | producer | done | 29316 | 7329 | 1 | 1 | 49% | 10 | 0 | Result template: (13725) |
| 10 | improve (carry-forward) | improve | done | 1630 | 407 | 1 | – | 18% | 1 | 0 | (opening) (1630) |
| 11 | system-test-author | producer | – | 22099 | 5524 | 1 | 0 | 58% | 2 | 0 | Result template: (13439) |

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
| step-plan | done | 425.9 | – | 48 | 84935 |
| test-spec | done | 68.0 | – | 5 | 91218 |
| validate-existing | done | 0% | – | 0 | – |
| implement | done | 32.0 | – | 10 | 105557 |
| test | done | 101.0 | – | 6 | 111844 |
| document | done | 191.0 | – | 19 | 124521 |
| carry-forward | done | 219.0 | – | 20 | 136522 |
| system-test-author (incomplete) | – | 100% | – | 0 | – |
