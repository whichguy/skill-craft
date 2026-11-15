# Environment

Standing facts for the help-desk ticket service. Sources are repository paths. Each fact is a **binding requirement**, **observed practice**, or **proposal**.

## Targets and runtimes

- **local-dev** (observed practice): `npm start` runs `node src/server.js` on `PORT` (default 4180). State is in memory unless `DATA_FILE` is set. README.md "Running", "Configuration"; src/server.js.
- **test** (observed practice): `npm test` runs `node --test`. HTTP tests start the service on port 0 with the worker off and no data file (`test/helpers.js` `TEST_SETTINGS`). Node.js `>=22` (`package.json` `engines`).
- **production** (documented promise, docs/operations.md "Process"): one Node.js process per host behind an internal load balancer, started with `npm start` by the host's service manager. `DATA_FILE` holds tickets, audit and outbox. This repository has no CI, deploy workflow, or `.github/` directory; a source-branch return does not itself deploy. Operators enable `DUE_TIMES=on` themselves after the data file holds due (request S7).
- **delivery** (binding requirement of this isolated run): product files return to the original checkout at release or handoff. No production write is authorized.
- **runtime** (binding requirement): Node.js standard library only; no packages in `package.json` (CONTRIBUTING.md "No dependencies"; README.md). `type` is `commonjs`. Current `package.json` version is `1.4.0`.
- **platform guide**: none. The service uses `node:http`, not Express. GUIDES/platforms/node-express.md applies only for `node --test` reporter facts (`spec` or `tap`).

## Commands

- **start** (binding requirement): `npm start` → `node src/server.js` (package.json `scripts.start`; README.md).
- **test** (binding requirement): `npm test` → `node --test` (package.json `scripts.test`; CONTRIBUTING.md "Tests"). Finds every file under `test/`.
- **weekly report** (observed practice): `npm run report:weekly` → `node scripts/weekly-report.js` (package.json).
- **CLI** (observed practice): `node bin/tickets.js` with `DATA_FILE` or `--data FILE` (README.md "Command line"). Exit codes: 0 done, 1 no such ticket, 2 usage or data file (bin/tickets.js).
- **lint / format / typecheck**: none. No `.eslintrc`, Prettier, `.editorconfig`, or TypeScript config.

## Skills

none. No `SHIPLOOP.md`, `AGENTS.md`, or `skills/` in the repository.

## Harnesses and suites

- **full suite** (binding requirement): `npm test` (`node --test`) from the repository root. Baseline at `7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6`: 117 tests, 26 suites, 0 fail. Output: run `scratch/baseline-npm-test.txt`.
- **HTTP harness** (observed practice): `test/helpers.js` `withService(settings, fn)` starts `createService` on port 0, worker off, memory only, silent logger, optional `manualClock`. JSON client `get`/`post`/`patch`. `ticketBody(overrides)` for create bodies.
- **unit harness** (observed practice): `node:test` `describe`/`test` plus `node:assert/strict`. Module tests import `src/` directly. Persistence tests write a temp directory via `os.tmpdir()` and delete it in `t.after`.
- **clock** (observed practice): `src/clock.js` `manualClock` / `systemClock`. Code takes a clock; tests hold time still.
- **smoke suite**: none separate from the full suite.

## ID convention

none in the current suite. Tests use sentence titles (`test/api.test.js`, `test/store.test.js`). The test files are the home of names. A command that lists titles: `node --test --test-reporter=spec`. New due-times tests should keep `node:test` under `test/` and may prefix titles with stable `TC-due-` tokens so later stages can name them.

## Access and accounts

none. The HTTP API has no authentication. `X-Actor` is an optional name recorded in the audit log, default `system` (docs/api.md "The actor"; src/http.js). Operators hold the process environment and the `DATA_FILE` path on the host (docs/operations.md). No credentials, tenants, or remote accounts.

## Platform facts

House style checked at `7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6`.

- **No npm dependencies** (binding requirement): CONTRIBUTING.md:7-9; package.json has no `dependencies`. Do not add packages.
- **CommonJS, strict mode, named exports** (binding requirement): each file starts `'use strict';` and ends `module.exports = { ... }` (CONTRIBUTING.md:10-11; src/config.js:1, src/config.js:49; src/store.js:1, src/store.js:176).
- **Errors through the envelope** (binding requirement): throw `InvalidError` (400), `NotFoundError` (404), `ConflictError` (409) from src/errors.js; never write an error response by hand (CONTRIBUTING.md:12-15; src/app.js:56-58; src/errors.js:12-16).
- **Changes go through the store** (binding requirement): every ticket mutation is a `TicketStore` method that applies, audits, enqueues, and saves in one step (CONTRIBUTING.md:16-19; src/store.js:17-20, src/store.js:75-85).
- **Settings from environment variables** (binding requirement): unset or empty means the default; a bad value throws `ConfigError` naming the variable (README.md "Configuration"; src/config.js:8-47). Canonical new settings: add a key in `loadConfig` with a default so `test/helpers.js` `TEST_SETTINGS` (which omits unknown keys) still starts a service.
- **Persistence names every ticket field** (binding requirement): `ticketRecord` / `readTicket` keep only listed fields (src/persistence.js:98-108, 138-148; docs/decisions/0008-json-data-file.md). Extra JSON keys on a ticket are dropped on load (observed: a version-1 file with `due` loaded as `{id,title,priority,requester,status,created,updated}`). Data-file `version` is `1`; a version bump would stop 1.4.0 (`fromDocument` src/persistence.js:77-79).
- **Listings are cursor pages** (binding requirement): `{ items, next }` (CONTRIBUTING.md:26-27; src/app.js:22; src/store.js:51-59). Unknown query parameters are ignored (`test/query.test.js` "ignores parameters it does not know").
- **Times are ISO 8601 UTC** (documented promise): docs/api.md "Times"; store writes `clock.now().toISOString()` (src/store.js:134-136).
- **Tests live under `test/` as `test/<module>.test.js`** (observed practice): CONTRIBUTING.md:30-32; 17 test files plus `helpers.js`. HTTP tests use `withService`. Assertions: `node:assert/strict`. Existing tests that must keep passing destructure ticket fields (`test/store.test.js:21-30`, `test/persistence.test.js:18`, `test/config.test.js:7-18`) or snapshot create-audit `changes` without extra keys (`test/store.test.js:37-48`).
- **CLI `list --raw` columns are positional** (binding requirement): `id`, `status`, `priority`, `title` (src/format.js:12; README.md:70-72). Do not insert a column.
- **Decision records** (binding requirement for API, data file, or notification changes): copy docs/decisions/template.md, next number, index in docs/decisions/README.md (CONTRIBUTING.md:34-38). Releases bump `package.json` version and add CHANGELOG.md (CONTRIBUTING.md:40-42).
- **Active ticket statuses** (observed practice): `src/tickets/states.js` `ACTIVE` is `['open', 'in_progress']` (states.js:22-23, 38-40). `TicketStore.dueNotifications` is the outbox worker API, not ticket due times (src/store.js:113-116).
- **Filter matcher vs API prose** (observed implementation vs documented promise): docs/api.md:76 says filters combine with AND; `matchesFilters` uses `.some()` (src/tickets/query.js:42-46). Existing tests cover single filters only. Preserve today's matcher; implement overdue outside equality filters.
- **Canonical exemplars for this area**: src/config.js (new env settings), src/persistence.js (ticket record fields), src/store.js `create`/`update` (set-once fields, audit), src/tickets/query.js and src/app.js GET `/tickets` (list query), test/helpers.js and test/api.test.js (HTTP tests), test/config.test.js and test/persistence.test.js (config and data file).
