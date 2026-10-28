# Census of cosmos-sdk at 27246c287d98

- 4275 tracked files; 16057 commits from 2016-02-05 to 2026-10-28 (620 in the last 365 days); size class huge; census took 1.43 s.
- Classes (files / text lines): code 2136 / 1160240; config 40 / 2839; docs 353 / 81116; test 1746 / 189985
- Code lines by extension: .go 1046635, .yaml 53148, .sum 15191, .proto 13699, .h 10474, .c 7020, .mod 3680, (none) 2097, .toml 1278, .s 919, .sage 893, .sh 821

## Map (code, test and docs weight; commits touching it in 365 days)

| Path | Code files / lines | Test files / lines | Docs files | Commits 365d |
|---|---|---|---|---|
| api | 166 / 441602 | 0 / 0 | 1 | 164 |
| api/cosmos | 151 / 374315 | 0 / 0 | 0 | 132 |
| api/tendermint | 12 / 67002 | 0 / 0 | 0 | 5 |
| api/amino | 1 / 242 | 0 / 0 | 0 | 0 |
| x | 598 / 238461 | 259 / 59341 | 22 | 1038 |
| x/tx | 37 / 56518 | 13 / 2802 | 1 | 129 |
| x/staking | 61 / 36909 | 32 / 9638 | 1 | 182 |
| x/gov | 65 / 33055 | 29 / 8184 | 1 | 103 |
| x/auth | 95 / 21846 | 47 / 10278 | 3 | 139 |
| x/distribution | 47 / 21828 | 18 / 4151 | 1 | 74 |
| x/bank | 38 / 17610 | 20 / 8105 | 1 | 67 |
| x/authz | 37 / 8791 | 15 / 3055 | 1 | 20 |
| x/feegrant | 33 / 7645 | 16 / 3196 | 2 | 24 |
| enterprise | 170 / 124503 | 70 / 30677 | 9 | 2023 |
| client | 149 / 89898 | 42 / 6383 | 2 | 379 |
| testutil | 83 / 65483 | 13 / 1390 | 3 | 93 |
| contrib | 99 / 45404 | 16 / 2955 | 8 | 253 |
| crypto | 166 / 33921 | 31 / 6748 | 4 | 70 |
| types | 71 / 26907 | 47 / 9438 | 2 | 99 |
| tests | 0 / 0 | 1063 / 34895 | 0 | 807 |
| store | 66 / 14031 | 41 / 8392 | 7 | 371 |
| tools | 93 / 12567 | 12 / 2876 | 9 | 604 |
| baseapp | 32 / 7685 | 18 / 7114 | 0 | 134 |
| server | 27 / 11258 | 11 / 2231 | 1 | 79 |
| depinject | 53 / 9327 | 11 / 1957 | 3 | 19 |
| proto | 129 / 10271 | 0 / 0 | 2 | 40 |
| collections | 43 / 5939 | 29 / 2230 | 2 | 49 |
| internal | 29 / 3711 | 16 / 2726 | 1 | 138 |
| simapp | 19 / 4435 | 9 / 1498 | 1 | 384 |
| math | 11 / 2174 | 8 / 2936 | 1 | 15 |

## Root files

.clang-format, .dockerignore, .gitattributes, .gitignore, .golangci.yml, .goreleaser.yml, .markdownlint.json, .markdownlintignore, .mergify.yml, AGENTS.md, CHANGELOG.md, Dockerfile, LICENSE, Makefile, NOTICE, README.md, RELEASE_NOTES.md, UPGRADING.md, buf.work.yaml, codecov.yml, docker-compose.yml, go.mod, go.sum

## Documentation

- READMEs: README.md (83 lines), client/v2/README.md (258 lines), collections/README.md (1207 lines), contrib/githooks/README.md (21 lines), contrib/images/simd-dlv/README.md (37 lines), contrib/x/README.md (5 lines), contrib/x/circuit/README.md (261 lines), contrib/x/crisis/README.md (112 lines), contrib/x/nft/README.md (91 lines), core/README.md (11 lines), core/appmodule/README.md (232 lines), crypto/keys/secp256k1/internal/secp256k1/README.md (5 lines), crypto/keys/secp256k1/internal/secp256k1/libsecp256k1/README.md (62 lines), depinject/README.md (205 lines), depinject/appconfig/README.md (232 lines)
- Instruction files at the root: .github/PULL_REQUEST_TEMPLATE.md, AGENTS.md, CHANGELOG.md, README.md, RELEASE_NOTES.md, UPGRADING.md, api/CHANGELOG.md, collections/CHANGELOG.md, collections/README.md, core/CHANGELOG.md, core/README.md, depinject/CHANGELOG.md, depinject/README.md, docs/DOC_WRITING_GUIDELINES.md, docs/README.md, enterprise/README.md, errors/CHANGELOG.md, errors/README.md, log/CHANGELOG.md, log/README.md, math/CHANGELOG.md, proto/README.md, scripts/README.md, server/README.md, simapp/README.md, store/CHANGELOG.md, telemetry/README.md, x/README.md
- Markdown-like files in all: 246
- Decision records (found by content): docs/architecture (58: adr-002-docs-structure.md … adr-template.md)

## Hot spots (code and test files changed most in 365 days)

- go.mod (167)
- tests/go.mod (165)
- tests/systemtests/go.mod (164)
- simapp/go.mod (162)
- tests/systemtests/go.sum (158)
- go.sum (157)
- simapp/go.sum (156)
- tests/go.sum (155)
- client/v2/go.mod (150)
- client/v2/go.sum (148)
- enterprise/poa/simapp/go.mod (131)
- enterprise/poa/tests/systemtests/go.mod (126)

## Recent commits

- 2026-10-28 ci: bump go to 1.27.3 (#26919)
- 2026-10-28 build(deps): Bump github.com/go-jose/go-jose/v4 from 4.1.4 to 4.1.6 in /tests in the go_modules group across 1 directory (#26921)
- 2026-10-28 build(deps): Bump go.opentelemetry.io/contrib/bridges/otelslog from 0.20.1 to 0.21.0 (#26903)
- 2026-10-28 perf(blockstm): batch MVData index updates (#26773)
- 2026-10-26 build(deps): Bump docker/login-action from 4.6.0 to 4.7.0 (#26917)
- 2026-10-22 fix(enterprise/poa): truncate fee shares so allocations never exceed the balance (#26875)
- 2026-10-21 chore: bump golangci-lint to v2.15.0 (#26897)
- 2026-10-21 chore(deps): fix open Dependabot alerts (#26896)
