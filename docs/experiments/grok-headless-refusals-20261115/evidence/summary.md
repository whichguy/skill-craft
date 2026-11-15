# Grok headless refusals: summary

267 Grok runs read; 168 kept Grok's session store, so each of their shell calls is paired with Grok's own decision; 193 refused shell calls.

## By Grok build and permission mode

| build | mode | runs | shell calls | refused | per 100 calls | runs with a refusal | floor | classifier timeout | classifier escalation | stream only | classifier blocks (model told) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.0.46 | auto | 5 | 690 | 3 | 0.43 | 2 | 0 | 2 | 1 | 0 | 3 |
| 1.0.62 | auto | 3 | 1348 | 11 | 0.82 | 3 | 5 | 5 | 1 | 0 | 13 |
| 1.0.62 | bypassPermissions | 3 | 676 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1.0.70 | auto | 250 | 8171 | 151 | 1.85 | 68 | 125 | 5 | 4 | 17 | 38 |
| 1.0.70 | bypassPermissions | 1 | 616 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1.0.77 | auto | 5 | 2186 | 28 | 1.28 | 4 | 28 | 0 | 0 | 0 | 2 |

## Auto mode by run kind

| kind | runs | shell calls | refused | runs with a refusal |
|---|---|---|---|---|
| delivery | 27 | 6878 | 82 | 21 |
| slice | 139 | 5232 | 96 | 41 |
| start-route probe | 97 | 285 | 15 | 15 |

## Delivery runs

| date | run | build | mode | shell calls | refused (floor, timeout) | sessions (cancelled) | ShipLoop at the end | resume stop |
|---|---|---|---|---|---|---|---|---|
| 2026-10-05 | ~/e2e-runs/20261005/v1210-battleship-grok-medium | 1.0.46 | auto | 124 | 0 (0, 0) | None (None) | active at inner-loop |  |
| 2026-10-06 | ~/e2e-runs/20261006/v1220-battleship-grok-medium-none | 1.0.46 | auto | 169 | 0 (0, 0) | 1 (0) | done at done | ShipLoop run is done |
| 2026-10-07 | ~/e2e-runs/20261007/v1230-battleship-grok-none | 1.0.46 | auto | 188 | 2 (0, 1) | 3 (2) | blocked at system-test | ShipLoop run is blocked |
| 2026-10-08 | ~/e2e-runs/20261008/r1-battleship-grok-none | 1.0.46 | auto | 112 | 1 (0, 1) | 2 (1) | blocked at system-test-author | ShipLoop run is blocked |
| 2026-10-09 | ~/e2e-runs/20261008/r3-battleship-grok-none | 1.0.46 | auto | 97 | 0 (0, 0) | 1 (0) | active at inner-loop | stopped by /Users/dadleet/e2e-runs/20261008/r3-battleship-grok-none/stop |
| 2026-10-17 | ~/e2e-runs/20261017/bs-sf-int-b7c77f | 1.0.62 | bypassPermissions | 354 | 0 (0, 0) | 1 (0) | done at done | ShipLoop run is done |
| 2026-10-17 | ~/e2e-runs/20261017/salesforce-chess-int-802e29 | 1.0.62 | bypassPermissions | 261 | 0 (0, 0) | 1 (0) | blocked at release-verify | ShipLoop run is blocked |
| 2026-10-18 | ~/e2e-runs/2026-10-18/battleship-1 | 1.0.62 | auto | 454 | 4 (2, 2) | 3 (2) | active at inner-loop | run deadline spent |
| 2026-10-18 | ~/e2e-runs/20261018/bs-release-update-436528 | 1.0.62 | bypassPermissions | 61 | 0 (0, 0) | 1 (0) | done at done | ShipLoop run is done |
| 2026-10-19 | ~/e2e-runs/20261019/chess-sf-full-05fe25b | 1.0.62 | auto | 482 | 3 (2, 1) | 4 (3) | active at inner-loop | run deadline spent |
| 2026-10-21 | ~/e2e-runs/20261020/chess-sf-full-9e52e8 | 1.0.62 | auto | 412 | 4 (1, 2) | 5 (4) | active at release-plan | run deadline spent |
| 2026-10-24 | ~/e2e-runs/20261024/chess-sf-full-ed3292 | 1.0.70 | auto | 146 | 4 (4, 0) | 0 (0) | blocked at inner-loop | not evaluated (regraded) |
| 2026-10-24 | ~/e2e-runs/effort-eeff1-r1/control-hello | 1.0.70 | auto | 188 | 2 (2, 0) | 13 (2) | done at done | ShipLoop run is done |
| 2026-10-24 | ~/e2e-runs/effort-eeff1-r1/treatment-hello | 1.0.70 | auto | 200 | 4 (4, 0) | 13 (4) | done at done | ShipLoop run is done |
| 2026-10-24 | ~/e2e-runs/effort-eeff1-r1b/control-hello | 1.0.70 | auto | 166 | 3 (3, 0) | 5 (3) | done at done | ShipLoop run is done |
| 2026-10-24 | ~/e2e-runs/effort-eeff1-r1b/control-hello-failed-no-session-id | 1.0.70 | auto | 16 | 0 (0, 0) | 1 (0) | active at spec | no host session id to resume |
| 2026-10-24 | ~/e2e-runs/effort-eeff1-r1b/treatment-hello | 1.0.70 | auto | 195 | 2 (2, 0) | 12 (2) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/20261024/chess-sf-full-12a23d | 1.0.70 | bypassPermissions | 616 | 0 (0, 0) | 1 (0) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/20261025/gate-212-8a49cf-grok-hello | 1.0.70 | auto | 17 | 2 (2, 0) | None (None) | active at spec |  |
| 2026-10-25 | ~/e2e-runs/20261025/gate-2132-f7ba78-grok-hello | 1.0.70 | auto | 167 | 3 (3, 0) | 4 (3) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/effort-eeff1/control-hello | 1.0.70 | auto | 261 | 3 (3, 0) | 18 (3) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/effort-eeff1/control-seat-reservations | 1.0.70 | auto | 296 | 8 (5, 3) | 27 (8) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/effort-eeff1/treatment-hello | 1.0.70 | auto | 171 | 1 (1, 0) | 13 (1) | done at done | ShipLoop run is done |
| 2026-10-25 | ~/e2e-runs/effort-eeff1/treatment-seat-reservations | 1.0.70 | auto | 266 | 2 (2, 0) | 20 (2) | done at done | ShipLoop run is done |
| 2026-10-26 | ~/e2e-runs/20261025/gate-2132-f7ba78-grok-web/battleship | 1.0.70 | auto | 352 | 6 (6, 0) | 7 (6) | done at done | ShipLoop run is done |
| 2026-10-26 | ~/e2e-runs/20261025/gate-2132-f7ba78-grok-web/battleship-scoring | 1.0.70 | auto | 213 | 0 (0, 0) | 1 (0) | done at done | ShipLoop run is done |
| 2026-11-10 | ~/e2e-runs/20261110/grok46-hello-1 | 1.0.77 | auto | 3 | 0 (0, 0) | 1 (0) | active at test-strategy | no host session id to resume |
| 2026-11-14 | ~/e2e-runs-planning-points/20261114/pp-1 | 1.0.77 | auto | 590 | 11 (11, 0) | 12 (11) | done at done | ShipLoop run is done |
| 2026-11-14 | ~/e2e-runs-planning-points/20261114/pp-2 | 1.0.77 | auto | 635 | 5 (5, 0) | 6 (5) | done at done | ShipLoop run is done |
| 2026-11-14 | ~/e2e-runs-planning-points/20261114/pp-3 | 1.0.77 | auto | 445 | 8 (8, 0) | 4 (4) | active at release-plan | resumed host made no ShipLoop progress 3 times in a row (revision 40) |
| 2026-11-14 | ~/e2e-runs-planning-points/20261114/pp-4 | 1.0.77 | auto | 513 | 4 (4, 0) | 5 (4) | done at done | ShipLoop run is done |

## Refusals by ShipLoop stage (paired runs)

| stage | all paired runs | delivery runs |
|---|---|---|
| test-strategy | 47 | 11 |
| step-plan | 43 | 4 |
| inner-loop | 14 | 0 |
| research | 13 | 13 |
| release-verify | 10 | 10 |
| release-plan | 10 | 10 |
| discovery | 8 | 8 |
| system-test-author | 6 | 6 |
| test-spec | 4 | 3 |
| implement | 4 | 3 |
| test | 4 | 4 |
| prepare | 3 | 2 |
| carry-forward | 2 | 2 |
| plan | 2 | 0 |
| intake | 1 | 1 |
| spec | 1 | 1 |
| release-check | 1 | 1 |
| operations | 1 | 1 |
| handoff | 1 | 1 |
| product-acceptance | 1 | 1 |

Of 176 refusals in paired runs, 88 were followed by another refusal within the next 10 shell calls of the same run.

## Floor refusals by probe-derived shape

- 1.0.62: cd-relative-write 5
- 1.0.70: var-write 98, none found 15, cd-relative-write 8, cd-relative-write,var-write 2, backtick-in-dq 2
- 1.0.77: var-write 21, backtick-in-dq 4, cd-relative-write 3

## How well the shapes predict a floor refusal (paired auto runs)

- 1.0.46: flagged / not a floor refusal 20; not flagged / not a floor refusal 670
- 1.0.62: flagged / floor refusal 5; flagged / not a floor refusal 9; not flagged / not a floor refusal 1334
- 1.0.70: flagged / floor refusal 110; flagged / not a floor refusal 2; not flagged / floor refusal 15; not flagged / not a floor refusal 7647
- 1.0.77: flagged / floor refusal 28; not flagged / not a floor refusal 2155

Refusal to the next session's first tool call: median 10.9 s, 90th percentile 36.8 s, max 136.1 s (n = 166).
