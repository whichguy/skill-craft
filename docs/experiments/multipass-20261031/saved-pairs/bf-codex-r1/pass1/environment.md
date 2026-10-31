# Environment

## Targets and runtimes
Binding: local Node.js service and CLI, Node >=22, no dependencies (README.md, package.json). Observed Node v26.12.1. API listens on PORT; DATA_FILE persists state, NOTIFY_FILE is a relay sink, worker interval 0 disables delivery (README.md, src/server.js). Local source checkout is delivery target; no hosted deployment requested or identified. No CI or deploy configuration is present in the tracked repository; branch-triggered external automation is unknown. Local test from worktree suffices for requested source change; no remote consumer check requested.

## Commands
`npm test` runs `node --test`; `npm start` runs the service; `npm run report:weekly` uses raw CLI output (package.json, README.md). Baseline full suite passed 117 tests on unchanged isolated checkout; command, output and exit status retained in run notes. No lint or format script observed.

## Platform facts
Binding conventions (CONTRIBUTING.md): CommonJS, no dependencies, errors via envelope, all changes in TicketStore with audit/outbox and persistence, worker-only delivery, cursor pages, tests for changes, decision records. src/tickets/validate.js trims single-line values and returns InvalidError; src/tickets/states.js defines active states; src/store.js uses apply for no-op and audit; src/outbox.js deduplicates pending keys; src/templates.js renders notifications. src/persistence.js projects ticket fields, so older files need compatibility and assignments must survive restart. At the pre-change baseline, src/tickets/query.js ORed filters; the implemented predicate intersects them. src/format.js raw columns feed weekly report, so retain positions and append any new column. test/helpers.js provides isolated local HTTP service with worker off and manual clock.

## Access and accounts
Local filesystem and process are test and source delivery contexts. Runtime clients use the existing HTTP and CLI interfaces; X-Actor records audit identity. Notification recipient is the supplied agent name. No identity lookup or remote account is described.

## Skills
README.md and CONTRIBUTING.md have no repository-local skill links; none identified. ShipLoop is the user-selected external workflow.

## Harnesses and suites plan
Planned R-1: node:test HTTP cases through test/helpers.js isolated port 0 and worker disabled for validation, states, idempotence and audit; temporary DATA_FILE roundtrip and legacy fixture. R-2: deterministic manual clock and worker delivery tests, including two assignments pending simultaneously and unassignment. R-3: HTTP cases combine status, priority and assignee including empty, mismatch and cursor pages. R-4: spawn CLI against temporary DATA_FILE; verify table/raw and weekly-report output and run unchanged existing tests. Each case sets up fresh service or temporary file, teardown closes server and removes fixture; no external account required. Due implementation/test/verify. Initial new tests should fail against base. Existing full suite 117/117 passed before edits, but does not cover assignment or filter intersection.

## Harnesses and suites
Node built-in node:test and test/helpers.js are available and fit local API/store. Full suite `npm test` discovers test files; focused `node --test test/assignment.test.js` includes new cases, temporary files isolated and cleaned. Revalidate after changes. No browser or remote target is requested.

## ID convention
Tests use descriptive node:test names rather than additional numbered IDs; each planned case is described above.

## Commands
Focused planned (new assignment file):
```sh
node --test test/assignment.test.js
```
Full planned (all test/ cases and existing suite):
```sh
npm test
```
Both require Node >=22; seconds locally, fresh temporary fixtures.

## Preparation
Node runner help and npm version started successfully; unchanged full suite passed in isolated worktree. Test fixtures use loopback port 0 and disposable files; no installation or remote access is needed. Source return has no tracked CI configuration; external automation remains unknown and no hosted check is required by the local request.

Focused assignment cases (local, isolated fixtures):
```sh
node --test --test-name-pattern=TC_1 test/assignment.test.js
node --test --test-name-pattern=TC_2 test/assignment.test.js
node --test --test-name-pattern=TC_3 test/assignment.test.js
node --test --test-name-pattern=TC_4 test/assignment.test.js
```
Each ran one case successfully at item verification; `npm test` ran 121. Revalidate after changing the service or harness. Tests clean up temporary files and stop loopback servers.

## Integrated system checks
The system check `node --test test/system-assignment.test.js` exercises HTTP assignment, persisted restart, local worker notification file, intersecting filters and actual CLI (R-1–R-4). Each run owns a temporary directory and isolated loopback servers, cleans them on completion, and needs only Node >=22. The default full suite discovers it alongside the existing tests. Run at system-test; no remote target is needed.

## Commands
```sh
node --test --test-name-pattern=TC_1 test/assignment.test.js
node --test --test-name-pattern=TC_2 test/assignment.test.js
node --test --test-name-pattern=TC_3 test/assignment.test.js
node --test --test-name-pattern=TC_4 test/assignment.test.js
node --test test/system-assignment.test.js
```

## Local delivery and rollback
The authorized target is the original source checkout on master. At release, review all candidate paths and use the ShipLoop guarded workspace return; no remote publication or deployment is requested. The clean starting branch is expected to fast-forward. Release-check revalidates test results and source state; release-verify runs `npm test` in a clean copy of the returned tree, with temporary test fixtures. Any failure stops completion for correction. To reverse the fast-forward with master checked out and no later commits, run from the repository root:
```sh
git reset --keep d507f964237b016624448004ac6d7ba70ad8bd46
```
If there are later commits or local edits, inspect and preserve those changes before choosing a rollback. Source return does not prove any hosted deployment or external relay delivery.

## Returned-tree verification
The local guarded return completed to the original master checkout. A clean copy of the returned tree ran `npm test` successfully with 122 tests, including the integrated assignment case. No hosted target or external relay was observed.

## Operations observation
On 2026-10-29 local tests observed ticket audit via `GET /tickets/:id/audit`, pending/sent outbox via `GET /admin/outbox`, and worker delivery to a temporary notification file. See `docs/operations.md` for data-file recovery, worker retries and dead events. Operators of any later deployment own its monitoring and recovery; no hosted target or alerting service was identified or inspected in this source-only run. Local rollback procedure is above.
