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

## Bulk reassignment and escalation discovery (2026-10-29)
Observed Node v26.12.1; package.json requires Node >=22 and npm test runs node --test. Baseline in this isolated worktree: npm test exit 0, 122 tests passed; output retained in run notes. CONTRIBUTING.md requires dependency-free CommonJS, store-owned changes and audit/outbox, worker-owned scheduled work, tests and a decision record. README.md and CONTRIBUTING.md have no repository-local skill links. Source checkout is the requested delivery target; no remote publication is requested. No tracked CI configuration or Git remote was found; external branch automation is unknown. No UI or remote identity is involved. Existing src/store.js owns assignment, audit, outbox and state; src/worker.js delivers notifications; src/persistence.js explicitly serializes records; src/server.js wires the worker; src/config.js validates environment settings. Test fixtures isolate services and data files. Return need not precede local candidate tests.

## Reassignment and escalation test plan
Planned, not yet passed: R-5 HTTP/component checks use node:test and test/helpers.js with loopback port 0, isolated in-memory store, worker off; assert mixed active/inactive/source tickets, numeric ordering, count, invalid inputs and outbox/audit effects. R-6 component checks use fake clock, disposable DATA_FILE and notifier; assert boundary, eligible/ineligible tickets, absence of ONCALL, repeated ticks, delivery rendering, restart and legacy load. R-1–R-4 and nonfunctional compatibility are covered by full existing suite plus new cases. Tests own setup and teardown; no shared persistent fixtures. Baseline npm test already passed 122 cases. No browser, remote service or account required. All checks due in item test and system test.

## Commands for this change
Focused cases after tests exist (planned):
```sh
node --test test/bulk-escalation.test.js
```
Full suite (baseline passed; candidate planned):
```sh
npm test
```
Both commands use Node >=22 and disposable local fixtures; no dependency installation. New test IDs are descriptive titles rather than a numeric catalog; full suite includes all test/*.test.js. Focused suite exercises new scenarios; full suite checks preservation.

## Preparation for reassignment and escalation
Node's test runner starts (`node --help`, output in run notes); npm is present and baseline ran successfully. The worktree is isolated; tests use temporary files and loopback. No install, credentials, external account or fixture provisioning is needed. The consumer is the local source/API operator; return does not need to precede local test observation. No tracked CI/deploy route was found; external automation remains unknown.

## Verified reassignment and escalation commands
The local node:test runner and test/helpers.js fixture were revalidated for this change. Focused tests use loopback and disposable data files; each owns cleanup. Owner: maintainers; rerun when service or persistence changes.
```sh
node --test test/bulk-escalation.test.js test/escalation-store.test.js test/escalation-service.test.js
```
```sh
rg -q 'Reassign active tickets' src/store.js
```
`npm test` is the full regression suite; the candidate passed 125 tests. Local checks exercise worker, outbox and file persistence; no external relay was observed.

## Harnesses and suites: assembled reassignment service
The system case in test/system-bulk-escalation.test.js uses test/helpers.js, local HTTP and a fresh temporary DATA_FILE to observe assignment and escalation delivery, then restarts with the same file to check no duplicate. Cleanup is owned by node:test. Run `node --test test/system-bulk-escalation.test.js` for the focused system case and `npm test` for all tests; both passed locally after authoring. Owner: maintainers; rerun after changes to worker, persistence, API or return. No remote relay or hosted target is claimed.

## Commands
```sh
node --test test/bulk-escalation.test.js test/escalation-store.test.js test/escalation-service.test.js
```
```sh
rg -q 'Reassign active tickets' src/store.js
```

## Local release for bulk reassignment and escalation
Target: original master checkout at baseline 48c016cc74c18ae8499d5d8cc00b2d6dd853cb00. The user requested the source change; guarded local return is within that authority. No deploy, push, external access or account change is requested. Release-check confirms full suite and source status; release reviews the exact candidate paths then uses the workspace return. Release-verify runs `npm test` in a clean copy of the returned tree, including system and item cases; no dependencies or external services are required. Tests create and clean isolated files and loopback services. Stop on any failure or source drift. The operations owner monitors outbox state and worker errors as in docs/operations.md.

## Commands
Pre/post local consumer check:
```sh
npm test
```
If the fast-forward is the latest change, restore the original source branch with:
```sh
git reset --keep 48c016cc74c18ae8499d5d8cc00b2d6dd853cb00
```
If later commits exist, inspect them before selecting a rollback. For a working-tree return, reverse only the reviewed kept paths using the run branch and baseline commit. No command here publishes or deploys.

## Returned reassignment service verification
A clean copy of the returned source ran `npm test` with 126 passes, including the local API, notification and restart system case. The source fast-forward receipt identifies the returned tree; this does not establish a hosted deployment or external mail relay delivery. Runtime configuration and operational recovery remain in README.md and docs/operations.md.

## Reassignment operations observation (2026-10-29)
Local tests observed ticket audit through the service, pending/sent outbox through `/admin/outbox`, worker notification delivery and durable restart. `docs/operations.md` gives worker logs, dead events and data-file recovery; local source rollback is recorded above. No running hosted target or alerting system was identified or checked; a future deployment's operators own those checks. There is no authentication subsystem in this service. Test-owned files and services are cleaned up by node:test.
