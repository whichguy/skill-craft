### battleship: e2e-runs/20261028/pa-ds-battleship-4ed4e3

Model `deepseek-v4.1-flash:1017-cloud`, ShipLoop 1.17.0, plan: 3 planned items (1 added later), 8 steps; active 372.5 min, Improve 102.3 min.

| stage | item | passes | passes (N non-trivial / T trivial; what the pass edited) | findings | product / records / unacted | min | files changed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 27 | 0 / 27 / 0 | 15.8 | `docs/shiploop/spec.md` x4, stage result |
| test-strategy | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 14 | 0 / 14 / 0 | 14.4 | `docs/shiploop/architecture.md` x4, `docs/shiploop/environment.md` x4 |
| plan | - | 5 | 1 N records; 2 N records; 3 N records; 4 N records; 5 T none | 8 | 0 / 8 / 0 | 13.7 | `docs/shiploop/architecture.md` x2, `docs/shiploop/environment.md` x2 |
| release-plan | - | 3 | 1 N records; 2 N records; 3 T none | 8 | 0 / 8 / 0 | 7.7 | `docs/shiploop/environment.md` x2, stage result |
| release-plan | - | 2 | 1 N records; 2 T none | 3 | 0 / 3 / 0 | 3.8 | `docs/shiploop/environment.md`, stage result |
| step-plan | W1 | 3 | 1 N records; 2 N records; 3 T none | 6 | 0 / 6 / 0 | 8.0 | stage result |
| step-plan | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 2.5 | - |
| implement | W1 | 2 | 1 N product-behaviour; 2 T records | 4 | 2 / 0 / 2 | 4.8 | `rules.js`, `test-support/random.js`, stage result |
| implement | W2 | 2 | 1 N product-behaviour; 2 T none | 5 | 5 / 0 / 0 | 10.2 | `page.js`, `server.js` |
| implement | W3 | 2 | 1 N product-behaviour; 2 T none | 1 | 1 / 0 / 0 | 5.7 | `test-support/browser.js` |
| implement | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 0.9 | - |
| system-test-author | - | 3 | 1 N records; 2 N product-behaviour; 3 T none | 5 | 1 / 4 / 0 | 5.2 | `docs/shiploop/environment.md` x2, `docs/shiploop/system-tests.md`, `test/system.test.js`, stage result |
| system-test-author | - | 2 | 1 N records; 2 T product-comments | 5 | 1 / 4 / 0 | 2.2 | `docs/shiploop/environment.md`, `docs/shiploop/spec.md`, `docs/shiploop/system-tests.md`, `test/system.test.js` |
| carry-forward | W3 | 2 | 1 N product-behaviour; 2 T none | 3 | 2 / 0 / 1 | 5.8 | `docs/shiploop/environment.md`, `docs/shiploop/spec.md`, `rules.js`, `test-support/browser.js`, +2 more files |
| carry-forward | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 1.5 | - |

### hello: e2e-runs-owner-note/20261028/pc-ds-hello-note-b45e87

Model `deepseek-v4.1-flash:1017-cloud`, ShipLoop 1.17.0, plan: 1 planned items (0 added later), 1 steps; active 152.3 min, Improve 42.0 min.

| stage | item | passes | passes (N non-trivial / T trivial; what the pass edited) | findings | product / records / unacted | min | files changed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | - | 3 | 1 N records; 2 N records; 3 T none | 5 | 0 / 5 / 0 | 5.0 | `docs/shiploop/spec.md` x2 |
| test-strategy | - | 2 | 1 N records; 2 T none | 6 | 0 / 6 / 0 | 7.4 | `docs/shiploop/architecture.md`, `docs/shiploop/environment.md`, stage result |
| plan | - | 2 | 1 N records; 2 T none | 4 | 0 / 4 / 0 | 6.2 | `docs/shiploop/architecture.md`, stage result |
| release-plan | - | 2 | 1 N records; 2 T records | 3 | 0 / 3 / 0 | 2.7 | `docs/shiploop/environment.md` x2, stage result |
| step-plan | W1 | 1 | 1 T none | 0 | 0 / 0 / 0 | 0.8 | - |
| implement | W1 | 1 | 1 T none | 0 | 0 / 0 / 0 | 2.4 | - |
| system-test-author | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 8 | 0 / 8 / 0 | 12.6 | `docs/shiploop/environment.md` x3, `docs/shiploop/architecture.md` x2, stage result |
| carry-forward | W1 | 2 | 1 N product-comments; 2 T records | 2 | 1 / 1 / 0 | 4.9 | `test_hello.py`, `docs/shiploop/architecture.md` |

### All 25 runs, by stage

| stage | group | children | passes | non-trivial | passes editing product | of which behaviour | passes editing records only | passes editing nothing | findings | product | records | unacted | min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spec | planning | 25 | 94 | 70 | 0 | 0 | 75 | 19 | 231 | 0 | 231 | 0 | 139.6 |
| test-strategy | planning | 24 | 67 | 43 | 0 | 0 | 46 | 21 | 141 | 0 | 139 | 2 | 108.0 |
| plan | planning | 24 | 47 | 23 | 0 | 0 | 23 | 24 | 47 | 0 | 47 | 0 | 73.8 |
| release-plan | planning | 24 | 42 | 19 | 0 | 0 | 22 | 20 | 52 | 0 | 52 | 0 | 47.9 |
| step-plan | step-level planning | 31 | 48 | 17 | 0 | 0 | 18 | 30 | 34 | 0 | 33 | 1 | 83.5 |
| test-spec | step-level planning | 25 | 33 | 8 | 0 | 0 | 9 | 24 | 15 | 0 | 14 | 1 | 37.0 |
| implement | build | 73 | 105 | 32 | 35 | 27 | 6 | 64 | 75 | 65 | 6 | 4 | 144.3 |
| system-test-author | build | 25 | 42 | 17 | 8 | 7 | 11 | 23 | 46 | 11 | 34 | 1 | 78.8 |
| carry-forward | carry-forward | 24 | 42 | 18 | 7 | 6 | 13 | 22 | 40 | 13 | 25 | 2 | 80.4 |

### By plan size and stage group

Plan size is the planned work items and the steps of the first accepted step plans.

| plan size | runs | group | children | passes | non-trivial | product | behaviour | records only | nothing | findings | f: product | f: records | f: unacted | min total | min per run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | 7 | planning | 28 | 45 | 17 | 0 | 0 | 19 | 26 | 36 | 0 | 36 | 0 | 53.9 | 7.7 |
| 1 item, 1 step | 7 | step-level planning | 15 | 18 | 3 | 0 | 0 | 3 | 15 | 3 | 0 | 3 | 0 | 17.4 | 2.5 |
| 1 item, 1 step | 7 | build | 14 | 17 | 3 | 1 | 0 | 4 | 12 | 9 | 1 | 8 | 0 | 22.9 | 3.3 |
| 1 item, 1 step | 7 | carry-forward | 7 | 10 | 3 | 1 | 0 | 3 | 6 | 4 | 1 | 3 | 0 | 9.5 | 1.4 |
| 1 item, 2+ steps | 10 | planning | 40 | 90 | 50 | 0 | 0 | 51 | 39 | 132 | 0 | 130 | 2 | 108.0 | 10.8 |
| 1 item, 2+ steps | 10 | step-level planning | 18 | 28 | 10 | 0 | 0 | 10 | 18 | 14 | 0 | 13 | 1 | 26.5 | 2.6 |
| 1 item, 2+ steps | 10 | build | 33 | 55 | 22 | 17 | 14 | 6 | 32 | 32 | 21 | 10 | 1 | 55.9 | 5.6 |
| 1 item, 2+ steps | 10 | carry-forward | 10 | 17 | 7 | 1 | 1 | 7 | 9 | 15 | 3 | 12 | 0 | 28.6 | 2.9 |
| 2+ items | 7 | planning | 28 | 102 | 75 | 0 | 0 | 83 | 19 | 247 | 0 | 247 | 0 | 207.3 | 29.6 |
| 2+ items | 7 | step-level planning | 23 | 35 | 12 | 0 | 0 | 14 | 21 | 32 | 0 | 31 | 1 | 76.5 | 10.9 |
| 2+ items | 7 | build | 51 | 75 | 24 | 25 | 20 | 7 | 43 | 80 | 54 | 22 | 4 | 144.2 | 20.6 |
| 2+ items | 7 | carry-forward | 7 | 15 | 8 | 5 | 5 | 3 | 7 | 21 | 9 | 10 | 2 | 42.3 | 6.0 |

### Improve minutes and product edits, by stage group

| runs | stage group | passes | min | share of Improve min | passes editing product | behaviour passes | findings | f: product | f: records | min per behaviour pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all 25 runs | planning | 250 | 369.3 | 47% | 0 | 0 | 471 | 0 | 469 | - |
| all 25 runs | step-level planning | 81 | 120.5 | 15% | 0 | 0 | 49 | 0 | 47 | - |
| all 25 runs | build + carry-forward | 189 | 303.5 | 38% | 50 | 40 | 161 | 89 | 65 | 7.6 |
| ShipLoop 1.16 and later (5 runs) | planning | 72 | 162.8 | 51% | 0 | 0 | 179 | 0 | 179 | - |
| ShipLoop 1.16 and later (5 runs) | step-level planning | 10 | 21.4 | 7% | 0 | 0 | 9 | 0 | 9 | - |
| ShipLoop 1.16 and later (5 runs) | build + carry-forward | 48 | 137.6 | 43% | 19 | 16 | 81 | 41 | 36 | 8.6 |

### How Improve scales with plan size, per run

| plan size | runs | active min | Improve min | Improve share | planning min | planning fixes | build behaviour passes | behaviour passes / build passes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | 7 | 57.5 | 14.8 | 26% | 7.7 | 5.1 | 0.0 | 0 / 27 |
| 1 item, 2+ steps | 10 | 62.0 | 21.9 | 35% | 10.8 | 13.0 | 1.5 | 15 / 72 |
| 2+ items | 7 | 310.2 | 67.2 | 22% | 29.6 | 35.3 | 3.6 | 25 / 90 |

### What each review was given, and when it stopped

Scope is the `context.scope` text in each child's `start.json`; it names product files only when it lists "Files this item changed" or "Files the executed items changed". Every run used `planning_review: stage`.

| stage | reviews | scope names product files | stop rule: 1 trivial pass | reviews that edited nothing | passes | passes that edited nothing | of which the review's last pass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | 25 | 0 | 25 | 2 | 94 | 19 | 19 |
| test-strategy | 24 | 0 | 24 | 3 | 67 | 21 | 21 |
| plan | 24 | 0 | 24 | 8 | 47 | 24 | 24 |
| release-plan | 24 | 0 | 24 | 11 | 42 | 20 | 20 |
| step-plan | 31 | 0 | 31 | 16 | 48 | 30 | 30 |
| test-spec | 25 | 0 | 25 | 17 | 33 | 24 | 24 |
| implement | 73 | 73 | 73 | 38 | 105 | 64 | 64 |
| system-test-author | 25 | 0 | 25 | 15 | 42 | 23 | 23 |
| carry-forward | 24 | 24 | 24 | 10 | 42 | 22 | 22 |

### By plan size and stage

| plan size | stage | children | passes | product | behaviour | records only | nothing | children edited in pass 1 | findings | f: product | f: records | min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | spec | 7 | 13 | 0 | 0 | 7 | 6 | 5 | 14 | 0 | 14 | 15.5 |
| 1 item, 1 step | test-strategy | 7 | 11 | 0 | 0 | 4 | 7 | 4 | 9 | 0 | 9 | 12.0 |
| 1 item, 1 step | plan | 7 | 11 | 0 | 0 | 4 | 7 | 4 | 7 | 0 | 7 | 17.1 |
| 1 item, 1 step | release-plan | 7 | 10 | 0 | 0 | 4 | 6 | 3 | 6 | 0 | 6 | 9.3 |
| 1 item, 1 step | step-plan | 8 | 11 | 0 | 0 | 3 | 8 | 3 | 3 | 0 | 3 | 9.1 |
| 1 item, 1 step | test-spec | 7 | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 8.3 |
| 1 item, 1 step | implement | 7 | 7 | 1 | 0 | 0 | 6 | 1 | 1 | 1 | 0 | 6.2 |
| 1 item, 1 step | system-test-author | 7 | 10 | 0 | 0 | 4 | 6 | 1 | 8 | 0 | 8 | 16.7 |
| 1 item, 1 step | carry-forward | 7 | 10 | 1 | 0 | 3 | 6 | 3 | 4 | 1 | 3 | 9.5 |
| 1 item, 2+ steps | spec | 10 | 29 | 0 | 0 | 19 | 10 | 10 | 56 | 0 | 56 | 39.0 |
| 1 item, 2+ steps | test-strategy | 10 | 27 | 0 | 0 | 17 | 10 | 10 | 48 | 0 | 46 | 38.3 |
| 1 item, 2+ steps | plan | 10 | 18 | 0 | 0 | 8 | 10 | 6 | 12 | 0 | 12 | 20.2 |
| 1 item, 2+ steps | release-plan | 10 | 16 | 0 | 0 | 7 | 9 | 4 | 16 | 0 | 16 | 10.4 |
| 1 item, 2+ steps | step-plan | 10 | 16 | 0 | 0 | 6 | 10 | 5 | 10 | 0 | 9 | 21.4 |
| 1 item, 2+ steps | test-spec | 8 | 12 | 0 | 0 | 4 | 8 | 4 | 4 | 0 | 4 | 5.1 |
| 1 item, 2+ steps | implement | 23 | 39 | 15 | 12 | 2 | 22 | 15 | 22 | 19 | 2 | 33.1 |
| 1 item, 2+ steps | system-test-author | 10 | 16 | 2 | 2 | 4 | 10 | 4 | 10 | 2 | 8 | 22.8 |
| 1 item, 2+ steps | carry-forward | 10 | 17 | 1 | 1 | 7 | 9 | 7 | 15 | 3 | 12 | 28.6 |
| 2+ items | spec | 7 | 39 | 0 | 0 | 36 | 3 | 7 | 105 | 0 | 105 | 85.1 |
| 2+ items | test-strategy | 7 | 29 | 0 | 0 | 25 | 4 | 7 | 84 | 0 | 84 | 57.6 |
| 2+ items | plan | 7 | 18 | 0 | 0 | 11 | 7 | 6 | 28 | 0 | 28 | 36.4 |
| 2+ items | release-plan | 7 | 16 | 0 | 0 | 11 | 5 | 6 | 30 | 0 | 30 | 28.2 |
| 2+ items | step-plan | 13 | 21 | 0 | 0 | 9 | 12 | 7 | 21 | 0 | 21 | 53.0 |
| 2+ items | test-spec | 10 | 14 | 0 | 0 | 5 | 9 | 4 | 11 | 0 | 10 | 23.5 |
| 2+ items | implement | 43 | 59 | 19 | 15 | 4 | 36 | 19 | 52 | 45 | 4 | 105.0 |
| 2+ items | system-test-author | 8 | 16 | 6 | 5 | 3 | 7 | 5 | 28 | 9 | 18 | 39.2 |
| 2+ items | carry-forward | 7 | 15 | 5 | 5 | 3 | 7 | 4 | 21 | 9 | 10 | 42.3 |

### Planning-stage Improve cost, one-item runs

| run | model | ShipLoop | plan size | planning passes | planning min | share of active | all Improve min | active min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261028/pc-ds-hello-note-b45e87 | deepseek-v4.1-flash: | 1.17.0 | 1 item, 1 step | 9 | 21.4 | 14% | 42.0 | 152.3 |
| 20261024/gate-290-b60ed7-claude-batch/battle | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 10 | 3.5 | 18% | 6.3 | 19.4 |
| 20261024/gate-290-b60ed7-claude-batch/hello | claude-sonnet-5-5 | 1.9.0 | 1 item, 1 step | 4 | 1.0 | 10% | 2.5 | 10.2 |
| 20261024/gate-290-b60ed7-claude-batch/seat-r | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 7 | 2.1 | 10% | 5.4 | 20.7 |
| 20261024/gate-290-b60ed7-claude-csv-report | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 10 | 4.6 | 15% | 10.9 | 30.0 |
| 20261024/gate-290-b60ed7-codex-hello | gpt-6-luna | 1.9.0 | 1 item, 1 step | 5 | 19.3 | 15% | 32.7 | 124.6 |
| 20261025/gate-2100-96810d-claude-web/battles | claude-sonnet-5-5 | 1.10.0 | 1 item, 2+ steps | 8 | 2.5 | 11% | 6.0 | 22.9 |
| 20261025/gate-2100-96810d-claude-web/battles | claude-sonnet-5-5 | 1.10.1 | 1 item, 2+ steps | 8 | 3.3 | 14% | 7.0 | 23.3 |
| 20261025/gate-2132-f7ba78-grok-hello | grok-4.7 | 1.13.1 | 1 item, 1 step | 5 | 4.4 | 6% | 12.2 | 68.1 |
| 20261025/gate-2132-f7ba78-grok-web/battleshi | grok-4.7 | 1.13.1 | 1 item, 2+ steps | 8 | 15.0 | 13% | 32.5 | 113.7 |
| 20261025/trace-verify-1131-b096ae/hello | claude-sonnet-5-5 | 1.13.1 | 1 item, 1 step | 9 | 2.8 | 21% | 4.7 | 13.1 |
| 20261025/trace-verify-4fd9f1/hello | claude-sonnet-5-5 | 1.12.0 | 1 item, 1 step | 7 | 2.9 | 13% | 6.0 | 22.8 |
| 20261026/live-sonnet-battleship-01b9b3 | claude-sonnet-5-5 | 1.15.0 | 1 item, 2+ steps | 7 | 3.1 | 9% | 8.0 | 36.6 |
| 20261026/live-sonnet-hello-b01d1c | claude-sonnet-5-5 | 1.15.0 | 1 item, 1 step | 6 | 2.1 | 18% | 3.7 | 11.6 |
| 20261026/pilot-ollama-dsflash-993a9d-hello | deepseek-v4.1-flash: | 1.15.0 | 1 item, 2+ steps | 13 | 15.7 | 27% | 25.0 | 58.0 |
| 20261027/v2170-sonnet-battleship-491d9a | claude-sonnet-5-5 | 1.16.0 | 1 item, 2+ steps | 8 | 53.3 | 20% | 108.3 | 262.5 |
| 20261027/v2180-sonnet-battleship-36036c | claude-sonnet-5-5 | 1.17.0 | 1 item, 2+ steps | 11 | 4.9 | 15% | 9.7 | 32.5 |

### Planning stages, one-item plans, by pass number

| pass | passes | passes that edited | findings acted on | min |
| --- | --- | --- | --- | --- |
| 1 | 68 | 46 | 123 | 115.4 |
| 2 | 45 | 19 | 36 | 36.5 |
| 3 | 18 | 4 | 6 | 7.9 |
| 4+ | 4 | 1 | 1 | 2.1 |

### Findings fixed in records only, one-item plans, by the stage that found them

| stage group | record-only findings | contradiction / unverifiable | stale / wrong reference | missing content | behaviour defect | polish |
| --- | --- | --- | --- | --- | --- | --- |
| planning | 166 | 55 | 23 | 72 | 8 | 8 |
| step-level planning | 16 | 8 | 0 | 2 | 6 | 0 |
| build | 18 | 8 | 5 | 2 | 1 | 2 |
| carry-forward | 15 | 4 | 10 | 1 | 0 | 0 |

### Planning stages on one-item plans

| stage | children | passes | product | records only | nothing | children edited in pass 1 | findings acted on | contradiction / unverifiable | behaviour defect | stale / wrong reference | missing content | polish | min | min in passes that edited nothing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spec | 17 | 42 | 0 | 26 | 16 | 15 | 70 | 26 | 3 | 2 | 36 | 3 | 54.5 | 6.6 |
| test-strategy | 17 | 38 | 0 | 21 | 17 | 14 | 57 | 18 | 2 | 12 | 22 | 1 | 50.4 | 7.8 |
| plan | 17 | 29 | 0 | 12 | 17 | 10 | 19 | 4 | 0 | 3 | 10 | 2 | 37.3 | 19.8 |
| release-plan | 17 | 26 | 0 | 11 | 15 | 7 | 22 | 7 | 3 | 6 | 4 | 2 | 19.7 | 7.9 |

### Nature of acted-on findings, by stage group (all runs)

| group | findings | behaviour defect | contradiction / unverifiable | stale / wrong reference | missing content | polish |
| --- | --- | --- | --- | --- | --- | --- |
| planning | 469 | 45 | 139 | 65 | 199 | 21 |
| step-level planning | 47 | 9 | 24 | 5 | 9 | 0 |
| build | 116 | 56 | 14 | 10 | 15 | 21 |
| carry-forward | 38 | 12 | 5 | 18 | 3 | 0 |

### Per run

| run | case | model | ShipLoop | items | steps | children | passes | product passes | planning product passes | planning min | Improve min | active min | Improve share | final stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261028/pc-ds-hello-note-b45e87 | hello | deepseek-v4.1-flash:10 | 1.17.0 | 1 | 1 | 8 | 17 | 1 | 0 | 21.4 | 42.0 | 152.3 | 28% | done |
| 20261020/chess-sf-full-9e52e8 | chess-salesforce | grok-4.7 | 1.8.0 | 3 | 3 | 14 | 26 | 2 | 0 | 30.3 | 70.4 | 239.6 | 29% | release-plan |
| 20261024/chess-sf-full-12a23d | chess-salesforce | grok-4.7 | 1.9.0 | 3 | 10 | 27 | 41 | 5 | 0 | 22.1 | 75.6 | 873.1 | 9% | done |
| 20261024/chess-sf-full-ed3292 | chess-salesforce | grok-4.7 | 1.9.0 | 3 | 1 | 5 | 14 | 0 | 0 | 23.9 | 34.2 | 92.8 | 37% | inner-loop |
| 20261024/gate-290-b60ed7-claude-batch/battleship | battleship | claude-sonnet-5-5 | 1.9.0 | 1 | 3 | 11 | 19 | 1 | 0 | 3.5 | 6.3 | 19.4 | 32% | done |
| 20261024/gate-290-b60ed7-claude-batch/hello | hello | claude-sonnet-5-5 | 1.9.0 | 1 | 1 | 9 | 9 | 0 | 0 | 1.0 | 2.5 | 10.2 | 24% | done |
| 20261024/gate-290-b60ed7-claude-batch/seat-reser | seat-reservations | claude-sonnet-5-5 | 1.9.0 | 1 | 2 | 10 | 15 | 0 | 0 | 2.1 | 5.4 | 20.7 | 26% | done |
| 20261024/gate-290-b60ed7-claude-csv-report | csv-report | claude-sonnet-5-5 | 1.9.0 | 1 | 4 | 12 | 23 | 2 | 0 | 4.6 | 10.9 | 30.0 | 36% | done |
| 20261024/gate-290-b60ed7-codex-hello | hello | gpt-6-luna | 1.9.0 | 1 | 1 | 9 | 11 | 0 | 0 | 19.3 | 32.7 | 124.6 | 26% | done |
| 20261025/gate-2100-96810d-claude-web/battleship | battleship | claude-sonnet-5-5 | 1.10.0 | 1 | 2 | 10 | 18 | 4 | 0 | 2.5 | 6.0 | 22.9 | 26% | done |
| 20261025/gate-2100-96810d-claude-web/battleship- | battleship-scoring | claude-sonnet-5-5 | 1.10.1 | 1 | 3 | 11 | 19 | 2 | 0 | 3.3 | 7.0 | 23.3 | 30% | done |
| 20261025/gate-2132-f7ba78-grok-hello | hello | grok-4.7 | 1.13.1 | 1 | 1 | 9 | 10 | 0 | 0 | 4.4 | 12.2 | 68.1 | 18% | done |
| 20261025/gate-2132-f7ba78-grok-web/battleship | battleship | grok-4.7 | 1.13.1 | 2 | 5 | 16 | 25 | 1 | 0 | 25.9 | 48.9 | 205.4 | 24% | done |
| 20261025/gate-2132-f7ba78-grok-web/battleship-sc | battleship-scoring | grok-4.7 | 1.13.1 | 1 | 2 | 10 | 17 | 2 | 0 | 15.0 | 32.5 | 113.7 | 29% | done |
| 20261025/haiku55-max-battleship-d521a8 | battleship | claude-haiku-5-5 | 1.11.0 | None | None | 1 | 13 | 0 | 0 | 0.0 | 0.0 | 34.6 | 0% | spec |
| 20261025/trace-verify-1131-b096ae/hello | hello | claude-sonnet-5-5 | 1.13.1 | 1 | 1 | 9 | 16 | 0 | 0 | 2.8 | 4.7 | 13.1 | 36% | done |
| 20261025/trace-verify-4fd9f1/hello | hello | claude-sonnet-5-5 | 1.12.0 | 1 | 1 | 11 | 15 | 1 | 0 | 2.9 | 6.0 | 22.8 | 26% | done |
| 20261026/ds-flash-978478-battleship | battleship | deepseek-v4.1-flash:10 | 1.15.0 | 3 | 12 | 22 | 43 | 8 | 0 | 22.0 | 79.6 | 222.1 | 36% | done |
| 20261026/live-sonnet-battleship-01b9b3 | battleship | claude-sonnet-5-5 | 1.15.0 | 1 | 3 | 11 | 20 | 3 | 0 | 3.1 | 8.0 | 36.6 | 22% | done |
| 20261026/live-sonnet-hello-b01d1c | hello | claude-sonnet-5-5 | 1.15.0 | 1 | 1 | 9 | 12 | 0 | 0 | 2.1 | 3.7 | 11.6 | 32% | done |
| 20261026/pilot-ollama-dsflash-993a9d-hello | hello | deepseek-v4.1-flash:10 | 1.15.0 | 1 | 2 | 10 | 24 | 0 | 0 | 15.7 | 25.0 | 58.0 | 43% | done |
| 20261027/v2170-ds-battleship-759a03 | battleship | deepseek-v4.1-flash:10 | 1.16.0 | 3 | 9 | 10 | 41 | 8 | 0 | 27.8 | 59.5 | 165.7 | 36% | done |
| 20261027/v2170-sonnet-battleship-491d9a | battleship | claude-sonnet-5-5 | 1.16.0 | 1 | 3 | 8 | 14 | 1 | 0 | 53.3 | 108.3 | 262.5 | 41% | done |
| 20261027/v2180-sonnet-battleship-36036c | battleship | claude-sonnet-5-5 | 1.17.0 | 1 | 3 | 8 | 21 | 3 | 0 | 4.9 | 9.7 | 32.5 | 30% | done |
| 20261028/pa-ds-battleship-4ed4e3 | battleship | deepseek-v4.1-flash:10 | 1.17.0 | 3 | 8 | 15 | 37 | 6 | 0 | 55.4 | 102.3 | 372.5 | 27% | done |

### Label checks

`{"touched kind not among the pass's real changes": 32, "passes without labels": 0}`
