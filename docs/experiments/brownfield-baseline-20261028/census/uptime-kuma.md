# Census of uptime-kuma at 2e8bf7da56f7

- 923 tracked files; 7433 commits from 2021-06-24 to 2026-10-28 (1362 in the last 365 days); size class large; census took 0.46 s.
- Classes (files / text lines): code 750 / 163995; config 35 / 2067; docs 18 / 1904; test 120 / 14901
- Code lines by extension: .json 86583, .js 36777, .vue 31671, .ts 3690, .mjs 2565, .sql 974, .scss 848, (none) 274, .go 154, .mts 103, .dockerfile 93, .conf 90

## Map (code, test and docs weight; commits touching it in 365 days)

| Path | Code files / lines | Test files / lines | Docs files | Commits 365d |
|---|---|---|---|---|
| src | 290 / 104142 | 0 / 0 | 1 | 1200 |
| src/lang | 80 / 67940 | 0 / 0 | 1 | 556 |
| src/components | 166 / 20817 | 0 / 0 | 0 | 379 |
| src/pages | 15 / 10525 | 0 / 0 | 0 | 165 |
| src/mixins | 6 / 1209 | 0 / 0 | 0 | 17 |
| src/assets | 5 / 848 | 0 / 0 | 0 | 4 |
| src/layouts | 2 / 439 | 0 / 0 | 0 | 3 |
| src/modules | 3 / 249 | 0 / 0 | 0 | 2 |
| server | 248 / 33605 | 0 / 0 | 4 | 744 |
| server/notification-providers | 111 / 8401 | 0 / 0 | 0 | 175 |
| server/model | 13 / 3996 | 0 / 0 | 0 | 112 |
| server/modules | 28 / 3896 | 0 / 0 | 4 | 39 |
| server/monitor-types | 28 / 3605 | 0 / 0 | 0 | 128 |
| server/socket-handlers | 11 / 1581 | 0 / 0 | 0 | 30 |
| server/routers | 4 / 1497 | 0 / 0 | 0 | 22 |
| server/monitor-conditions | 4 / 543 | 0 / 0 | 0 | 3 |
| server/utils | 4 / 248 | 0 / 0 | 0 | 3 |
| (root) | 15 / 17795 | 0 / 0 | 7 | 272 |
| test | 0 / 0 | 120 / 14901 | 0 | 339 |
| extra | 63 / 4840 | 0 / 0 | 1 | 180 |
| db | 120 / 3129 | 0 / 0 | 2 | 89 |
| docker | 6 / 352 | 0 / 0 | 0 | 14 |
| public | 8 / 132 | 0 / 0 | 0 | 8 |
| .github | 0 / 0 | 0 / 0 | 3 | 232 |
| config | 0 / 0 | 0 / 0 | 0 | 13 |

## Root files

.dockerignore, .editorconfig, .eslintrc.js, .gitignore, .npmrc, .prettierignore, .prettierrc.js, .stylelintrc, .ws-context, AGENTS.md, CLAUDE.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, LICENSE, README.md, SECURITY.md, compose.yaml, ecosystem.config.js, index.html, package-lock.json, package.json, playwright.config.js, tsconfig.json, vite.config.mjs

## Documentation

- READMEs: README.md (215 lines), db/knex_migrations/README.md (51 lines), db/old_migrations/README.md (3 lines), extra/push-examples/typescript-fetch/README.md (19 lines), server/modules/ping/README.md (9 lines), src/lang/README.md (20 lines), test/backend-test/README.md (35 lines)
- Instruction files at the root: .github/PULL_REQUEST_TEMPLATE.md, .github/REVIEW_GUIDELINES.md, AGENTS.md, CLAUDE.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, README.md, SECURITY.md
- Markdown-like files in all: 16
- Decision records (found by content): none

## Hot spots (code and test files changed most in 365 days)

- src/lang/en.json (141)
- package-lock.json (111)
- package.json (95)
- src/pages/EditMonitor.vue (93)
- server/model/monitor.js (59)
- server/server.js (47)
- src/lang/de-DE.json (36)
- src/components/NotificationDialog.vue (35)
- server/notification.js (34)
- src/components/notifications/index.js (33)
- src/lang/fr-FR.json (31)
- src/lang/pt-BR.json (30)

## Recent commits

- 2026-10-28 feat: api & mcp skeleton (as alpha) (#8072)
- 2026-10-27 chore: avoid adding more columns in `monitor` table (#7474)
- 2026-10-27 chore: combine modifed node-ping and make monitor standalone (#8060)
- 2026-10-27 chore: bump setup pin to 2.5.8 (#8062)
- 2026-10-27 feat: add Microsoft Graph email notification provider (#7948)
- 2026-10-26 feat: create the initial admin user from environment variables (#8056)
- 2026-10-26 chore: Update dependencies (#8058)
- 2026-10-26 chore: workflow hardening (#8057)
