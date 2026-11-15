| Measure | pp-1 | pp-2 | pp-4 |
|---|---|---|---|
| ShipLoop status | done | done | done |
| work items | 1 | 1 | 1 |
| M1 migrate-before applies | yes | yes | yes |
| M1 migrate-after applies | no | no | no |
| M1 switchover applies | yes | yes | yes |
| M1 state applies | yes | yes | yes |
| M1 config applies | yes | yes | yes |
| M2 order | same (held) | same | same |
| M3 release | last | last | last |
| M4 rollback planned | yes | yes | yes |
| M4 data-aware | no | yes | yes |
| M5 docs named in plan | CHANGELOG.md, README.md, docs/api.md, docs/decisions/, docs/operations.md | CHANGELOG.md, README.md, docs/api.md, docs/operations.md, the word documentation | CHANGELOG.md, README.md, docs/api.md, docs/decisions/, docs/operations.md, the word documentation |
| M6 setup in plan | yes | yes | yes |
| M7 suite | yes | yes | yes |
| M7 pristine | yes | yes | yes |
| M7 migrate | yes | yes | yes |
| M7 restart | yes | yes | yes |
| M7 switch | yes | yes | yes |
| M7 rollback | yes | yes | yes |
| M7 off | yes | yes | yes |
| M7 cli | yes | yes | yes |
| M8 D1_readme_DUE_TIMES | yes | yes | yes |
| M8 D2_readme_settings | yes | yes | yes |
| M8 D3_operator_procedure | yes | yes | yes |
| M8 D4_changelog_and_version | yes | yes | yes |
| M8 D6_api_due_overdue | yes | yes | yes |
| M8 miss | no | no | no |
| M8 D5 new decision records | none | none | none |
| M9 new settings | RESPONSE_HOURS_HIGH, RESPONSE_HOURS_LOW, RESPONSE_HOURS_NORMAL, RESPONSE_HOURS_URGENT | DUE_HOURS_HIGH, DUE_HOURS_LOW, DUE_HOURS_NORMAL, DUE_HOURS_URGENT | RESPONSE_HOURS_HIGH, RESPONSE_HOURS_LOW, RESPONSE_HOURS_NORMAL, RESPONSE_HOURS_URGENT |
| M9 setup miss | no | no | no |
| binds: migrate-before | yes | yes | yes |
| binds: switchover | yes | yes | yes |
| validity: EADDRINUSE | 0 | 0 | 0 |
| validity: port 4180 starts | 6 | 0 | 1 |

| # | Prediction | Probability | n | Outcome |
|---|---|---|---|---|
| P1 | migrate-before applies to at least one work item, in every run | 70% | 3 | held |
| P2 | switchover applies to at least one work item, in every run | 55% | 3 | held |
| P3 | state applies to at least one work item, in every run | 80% | 3 | held |
| P4 | config applies to at least one work item, in every run | 80% | 3 | held |
| P5 | migrate-after applies in at most one run | 65% | 3 | held |
| P6 | the migration comes before the feature in every run | 70% | 3 | missed as written |
| P7 | the release is planned last in every run | 60% | 3 | held |
| P8 | in every run that reaches release-plan, its result plans a rollback | 90% | 3 | held |
| P9 | in every run that reaches release-plan, the rollback is data-aware | 55% | 3 | missed as written |
| P10 | in every run, the plan names at least one product document | 70% | 3 | held |
| P11 | in every run, the plan names DUE_TIMES and a setting for the hours | 75% | 3 | held |
| P12 | in every completed run, migrate, restart and switch pass | 55% | 3 | held |
| P13 | in every completed run, rollback passes | 75% | 3 | held |
| P14 | in every completed run, off passes | 50% | 3 | held |
| P15 | in every completed run, there is no documentation miss | 40% | 3 | held |
| P16 | in every completed run, there is no setup miss | 65% | 3 | held |
| P17 | migrate-before and switchover both bind in every run | 35% | 3 | held |
