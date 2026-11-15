# Environment

Standing facts for the help-desk ticket service. Binding requirements, observed practices, and proposals are marked.

## Targets and runtimes

- **Source checkout:** Git repository `helpdesk-tickets` on branch `master`. Binding: `package.json` name and version 1.4.0.
- **Execution:** product work lands on `master`. Returning to `master` does not trigger CI or a deploy: there is no `.github/`, GitLab CI, Jenkinsfile, or Makefile. Binding from absence of those files plus `docs/operations.md` (operators start `npm start` via the host's service manager).
- **Runtime:** Node.js `>=22` (`package.json` `engines.node`). Stdlib only; `package.json` has no `dependencies`. Binding: `CONTRIBUTING.md` "No dependencies", README "Running".
- **Local process:** `npm start` runs `node src/server.js` on `PORT` (default 4180). Optional `DATA_FILE` JSON state and `NOTIFY_FILE` notification log. Binding: README "Configuration", `src/config.js`.
- **Production host:** one Node process per host behind an internal load balancer (`docs/operations.md` "Process"). No deploy automation in this repository. Source return to `master` is the local delivery boundary.
- **Platform:** Node.js stdlib `node:http` (not Express). Tests use `node --test` spec reporter. Observed: `src/server.js`, `src/http.js`, `package.json` scripts.test.
- **CLI / report consumers:** `bin/tickets.js` and `scripts/weekly-report.js` read `DATA_FILE` and never write it. Binding: `bin/tickets.js` header, `docs/operations.md` "The command line and the weekly report".

## Commands

- **Start:** `npm start` → `node src/server.js`. Binding: `package.json` scripts, README.
- **Test:** `npm test` → `node --test` (spec reporter; finds every file under `test/`). Binding: `package.json` scripts, `CONTRIBUTING.md` "Tests".
- **Weekly report:** `npm run report:weekly` → `node scripts/weekly-report.js`. Binding: `package.json`, README.
- **Lint / format / typecheck:** none. Observed: no eslint, prettier, editorconfig, or tsconfig in the tree.
- **CLI:** `node bin/tickets.js list|show` with `DATA_FILE` or `--data FILE`. Binding: README "Command line".

## Skills

none

## Harnesses and suites

- **Harness:** Node built-in `node:test` + `node:assert/strict`. Binding: every file under `test/`.
- **HTTP fixture:** `test/helpers.js` `withService` starts `createService` on port 0, memory-only, `WORKER_INTERVAL_MS=0`, `silentLogger`, `manualClock`. Binding: `test/helpers.js`.
- **Full suite:** `npm test` (all `test/*.test.js`). There is no separate smoke command.
- **Persistence fixtures:** temp directories via `node:os`/`node:fs` `mkdtempSync` in `test/persistence.test.js` and `test/service.test.js`.
- **Minimum regression for later steps:** `npm test`.

## ID convention

- Existing tests use descriptive `node:test` titles, not `TC-<n>` ids. Observed: `test/api.test.js`, `test/store.test.js`.
- Command that lists titles already taken: `npm test` (spec reporter prints each title).
- New tests follow the same title style in new files under `test/`. Binding: `CONTRIBUTING.md` "Each module has its own `test/<module>.test.js`".

## Access and accounts

- No remote accounts, SSO, or deploy credentials. Observed: local stdlib process and optional filesystem paths.
- Runtime identity for mutations is the `X-Actor` header (default `system`). Binding: `docs/api.md` "The actor", `src/http.js` `actorOf`.
- Data-file path is operator configuration (`DATA_FILE`), not a secret store. Binding: README, decision 8.

## Platform facts

House style checked at commit `7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6`.

- **CommonJS, strict mode, named exports.** Every source file starts with `'use strict';` and ends with `module.exports = { ... }`. Observed: `src/config.js:1`, `src/store.js:177`, `src/tickets/query.js:48`. Binding: `CONTRIBUTING.md` "Conventions".
- **No default exports, no npm packages.** Observed: `package.json` has no `dependencies`; imports are `node:*` or relative. Binding: `CONTRIBUTING.md`.
- **Config from env, freeze the result.** `loadConfig(env)` uses `wholeNumber` / `filePath`; bad values throw `ConfigError` naming the variable. Observed: `src/config.js:22-46`. Tests pick known keys so extra settings can be added (`test/config.test.js:7-8`).
- **Errors through the envelope.** Handlers throw `InvalidError` (400), `NotFoundError` (404), `ConflictError` (409); never write an error body by hand. Observed: `src/errors.js`, `src/app.js:56-58`. Binding: `CONTRIBUTING.md`, decision 4.
- **Store owns mutations.** Ticket, audit, and outbox change together in `TicketStore`; a no-op change writes nothing. Observed: `src/store.js:142-150`. Binding: `CONTRIBUTING.md`, decision 7.
- **Persistence names every kept field.** `ticketRecord` / `readTicket` round-trip only listed keys; extra JSON keys on a ticket are dropped on load. Observed: `src/persistence.js:98-148`. Probe: a `due` field on disk is ignored by 1.4.0 and omitted on the next save. Version must stay `1` or 1.4.0 refuses the file (`src/persistence.js:79`). Binding: decision 8.
- **Times are ISO 8601 UTC via the injected clock.** Observed: `src/store.js:134-136`, `src/clock.js`, `docs/api.md` "Times".
- **Listings are cursor pages** `{ items, next }`. Observed: `src/pagination.js`, `src/store.js:51-59`. Binding: decision 5.
- **Query parser ignores unknown parameters.** Observed: `src/tickets/query.js:18-30`, `test/query.test.js:40-42`. `matchesFilters` uses `.some` (OR) (`src/tickets/query.js:42-46`) while `docs/api.md` "List tickets" says filters combine with AND. Observed conflict; existing tests only pass one filter.
- **Active tickets** are `open` and `in_progress` (`src/tickets/states.js:22-23`, `isActive`).
- **HTTP tests** use `withService` and field asserts, not full-object snapshots of tickets. Observed: `test/api.test.js`, `test/helpers.js`.
- **CLI raw columns** are `id, status, priority, title` in that order. Binding: `src/format.js:12`, `scripts/weekly-report.js:9`.
- **Releases** bump `package.json` version and add a `CHANGELOG.md` section. Binding: `CONTRIBUTING.md` "Releases".
- **Decisions** go in `docs/decisions/NNNN-....md` from `template.md`, indexed in `docs/decisions/README.md`. Binding: `CONTRIBUTING.md` "Decisions".
- **Comments** are module-level purpose plus non-obvious contracts; tests named as behaviour sentences. Observed: `src/store.js:14-21`, `test/store.test.js:16`.
