# Environment

Standing facts for the help-desk ticket service. Runtime versions and working commands live here; product behaviour lives in the living spec; structure and decisions live in architecture.md.

## Targets and runtimes

- **local-dev (alias `local`)**: one Node.js process, `npm start` → `node src/server.js`, listens on `PORT` (default 4180). Optional `DATA_FILE` JSON document and `NOTIFY_FILE`. Binding: observed, README.md Running / Configuration, docs/operations.md Process. Platform guide: none (Node standard library `node:http`, not Express).
- **test (alias `test`)**: same code, `port: 0`, memory-only (`dataFile` null), worker off (`workerIntervalMs: 0`), injected `manualClock`. Binding: observed, test/helpers.js `TEST_SETTINGS` / `withService`.
- **production (alias `prod`)**: one process per host behind the internal load balancer, started by the host's service manager with `DATA_FILE` set (operations example `/srv/tickets/data/tickets.json`). Binding: documented, docs/operations.md. This run has no access to that host or file.
- **delivery**: source-only. Isolated execution worktree; original branch `master` at `7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6` is unchanged until the guarded workspace return. No CI workflows, no deploy on merge (no `.github/`). Returning to `master` does not itself publish. Binding: observed.
- **runtime**: Node.js `>=22` (`package.json` engines). Discovery host ran Node v26.12.1. No npm dependencies; Node standard library only. Binding: observed, package.json, CONTRIBUTING.md Conventions.

## Commands

- `npm start` — `node src/server.js` (README.md Running).
- `npm test` — `node --test`; finds every file under `test/`. Confirmed on the unchanged worktree at `7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6`: 117 tests, 26 suites, pass 117, fail 0, exit 0.
- `npm run report:weekly` — `node scripts/weekly-report.js` (reads `bin/tickets.js list --raw` by column position).
- Linters, formatters, type checkers: none configured (no eslint, prettier, tsc, Makefile, CI). Binding: observed absence.

## Skills

none

## Harnesses and suites

- **Harness**: Node.js built-in test runner `node:test` with `node:assert/strict`. HTTP tests use `test/helpers.js` `withService` (real `http.createServer` on port 0, JSON client). Time: `src/clock.js` `manualClock`. Persistence tests write a temp directory and delete it in `t.after`.
- **Full suite**: `npm test` / `node --test` (all `test/*.test.js`). This is also the smoke suite; there is no smaller established command.
- **CLI / weekly-report**: no automated tests. Binding: observed absence under test/.

## ID convention

none — tests use prose titles (`test('creates an open ticket and answers 201 with it')`) in `test/<module>.test.js`. There are no `TC-` IDs. The command that prints current titles is `node --test` (spec reporter). New due-time tests follow the same file-per-module and prose-title pattern unless a later test-strategy records IDs for focused ShipLoop commands.

## Access and accounts

none — the HTTP API has no authentication. `X-Actor` (at most 64 characters) is audit attribution, default `system` (docs/api.md Conventions). Production is on the internal network (docs/operations.md). No deploy account, browser consumer, or MCP runtime identity.

## Platform facts

- **Stack**: CommonJS, `'use strict'`, named `module.exports = { ... }`. HTTP via `node:http`; JSON bodies; error envelope `{"error":{"code","message"}}`. Binding: observed, CONTRIBUTING.md, src/errors.js, src/http.js.
- **Configuration**: every setting is an environment variable; unset or empty means the default; a bad value stops start with `ConfigError` naming the variable (src/config.js, README.md Configuration). Hours that operators change without a code change follow this pattern.
- **Persistence**: one JSON document, `version` 1, fields named in `ticketRecord` / `auditRecord` / `eventRecord`. Load copies only those fields, so extra ticket keys (including a future `due`) are ignored by 1.4.0. A version other than 1 is refused. Decision 8: a format change must still load files the previous version wrote; a field older files lack takes its default on load. Binding: observed, src/persistence.js, docs/decisions/0008-json-data-file.md, probe RUN/scratch/probe-14-extra-fields.json.
- **Store**: every ticket mutation is a `TicketStore` method that applies the change, appends audit, enqueues notifications, and saves. Reads return copies. Binding: CONTRIBUTING.md, src/store.js.
- **List query**: `parseListQuery` reads `status`, `priority`, `limit`, `cursor` and ignores unknown parameters (including today's `overdue`). `matchesFilters` uses `.some` (OR) even though docs/api.md says filters combine as AND. Existing tests only assert single filters. Binding: src/tickets/query.js, test/query.test.js, docs/api.md List tickets.
- **Active tickets**: `open` and `in_progress` (`src/tickets/states.js` `ACTIVE`).
- **CLI**: `bin/tickets.js` reads the data file and never writes it. `list --raw` columns are id, status, priority, title in that order; `scripts/weekly-report.js` reads them by position. Binding: src/format.js `RAW_COLUMNS`, README.md Command line.
- **Clock**: injected `{ now() }`; tests use `manualClock`. `store.dueNotifications()` is the outbox's due-to-send list, not ticket due times.
- **Start/save**: `createService.start()` does not save; `stop()` and each store mutation do. A load-time backfill of `due` must write the data file itself if operators need the file to hold due times before the first ticket change.
- **House style (checked at 7771e8acda315d2121fc3d2cb387ffb3d8fcfcc6)**: no dependencies; file-level purpose comments; `InvalidError` / `NotFoundError` / `ConflictError` rather than hand-written error responses; tests colocate as `test/<module>.test.js` with `describe`/`test` and `assert.equal` / `assert.deepEqual` / `assert.throws`; API changes and data-file format changes get a decision record (docs/decisions/template.md) and a CHANGELOG.md / package.json version bump on release. Evidence: CONTRIBUTING.md, test/api.test.js, test/store.test.js, docs/decisions/README.md.
