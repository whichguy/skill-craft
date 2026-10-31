# Environment

## Targets and runtimes
Binding: local Node.js >=22, no dependencies (README.md, package.json); observed Node v26.12.1. Local API and CLI consume the source returned to the original checkout. No hosted target was requested. No configured hooksPath was observed; CI or remote deploy on local return is not evidenced; return need not precede local consumer checks. No external operations authorized.

## Commands

```sh
node --test test/api.test.js
```

`npm test` runs `node --test`; `npm start` starts server (package.json). No lint command found. Unchanged baseline passed 117 tests, exit 0 (run/notes/baseline-test.txt).

## Platform facts
CONTRIBUTING.md requires CommonJS, strict mode, standard library, error envelopes, store-owned changes, audit and outbox notifications, cursor pages and decision records. Existing status helper `isActive` defines open and in_progress. `src/tickets/query.js` uses AND among supplied filters; before this change it used OR. Data files enumerate fields (`src/persistence.js`); legacy records need defaulting. CLI raw columns are consumed positionally by weekly report (README.md, src/format.js). Worker owns notification delivery; templates map event types.

## Access and accounts
Local operator and API callers; actor header identifies change author, agent names are notification recipients, no identity service. No remote access is needed.

## Skills
No repository-local skill links found in README.md or CONTRIBUTING.md.

## Harnesses and suites
Existing node:test and test/helpers.js start isolated ephemeral-port servers with worker off; temporary files use isolated directories and teardown. Available and verified by baseline. Executed assignment checks cover: R-1 HTTP/store valid, invalid, missing, both active and inactive statuses, no-op audit/timestamps; R-2 new and old records and restart; R-3 outbox repeated assignments and worker delivery; R-4 compound filters and pages; R-5 CLI table/raw and weekly report compatibility. Full suite preserves existing behavior and covers nonfunctional dependency constraint. New assignment tests failed on the prior base. No external host tools or remote target are needed.

For R-6/R-7, test/reassignment-escalation-system.test.js reuses test/helpers.js `withService(settings, fn)` and `ticketBody(overrides)` with a scheduled worker, ephemeral HTTP listener, temporary data and notification files, and deterministic clock. It is ready locally; system-test owns candidate execution and release-verify owns returned-source execution. Revalidate on service configuration, worker timing, helper or Node runtime changes.

## ID convention
Tests use descriptive node:test names rather than formal IDs.

## Commands
Focused planned assignment checks after writing them:
```sh
node --test test/assignment.test.js
```
Full suite, planned after implementation (baseline already passed all 117 existing cases):
```sh
npm test
```

New-feature checks retained from W1:
```sh
node --test test/reassignment-escalation.test.js
rg -q "Bulk reassign active tickets" src/store.js
node --check src/app.js && node --check src/store.js && node --check src/tickets/validate.js && node --check src/worker.js && node --check src/templates.js && node --check src/config.js && node --check src/server.js
node --test test/reassignment-escalation-system.test.js
```
Both run locally with Node >=22; temporary fixtures are created and cleaned by tests.

## Preparation readiness
Node test runner and CLI help started successfully; see run/notes/runner-help.txt. No packages, external services or setup are required. Worktree is isolated; data fixtures will use temporary files. Local return has no observed automation and is not required before isolated consumer tests.

Intermediate API regression:
```sh
node --test test/api.test.js
```

The focused assignment suite uses test/assignment.test.js with isolated ephemeral ports, in-memory stores and cleaned temporary files; node:test is available without setup. Full `npm test` passed 125 tests after implementation. Revalidate on runtime or harness changes.

System integration case: `node --test test/assignment-system.test.js` runs an isolated HTTP service, temporary persistent data and notification files, worker tick, restart and CLI; available locally, cleaned by test teardown, owner system-test. Revalidate on service or fixture changes.

## Local delivery and rollback
For the 2026-10-29 bulk/escalation run, the target is the original clean `master` checkout and the user request authorizes local source return. No publication, deployment, account or external access change is requested. Release checks the candidate and return plan, keeps product code, documentation and tests, excludes runtime artifacts, and stops on drift, failing checks or an invalid receipt. Release then executes the guarded local return. Release-verify runs the commands below in a clean copy of the returned tree, with temporary isolated test data and teardown; SYS-1 must show Bob's assignment and exactly one Morgan escalation after restart, and the full suite must pass. Check the same commands on the starting revision to establish the new feature is absent. No migration or live data operation is needed; DATA_FILE remains the existing persistence mechanism. Operators inspect `/admin/outbox` and notification output for retries.

```sh
node --test test/reassignment-escalation-system.test.js
npm test
```

If the return fast-forwards master and no later commits exist, rollback from the checkout root with:
```sh
git reset --keep d7decd765f1a6e5fe0f129bc5e1a2019802b4781
```
For a working-tree return or only the reviewed kept paths after a fast-forward:
```sh
git diff --binary d7decd765f1a6e5fe0f129bc5e1a2019802b4781 shiploop/run-4776f1c3739dd54a -- <kept paths> | git apply -R
```

The requested target is the original local checkout on master; the request authorizes returning the reviewed source. No hosted deployment, publication or extra account is requested. Release owner uses the guarded workspace return after reviewing product paths and current checks. No branch automation was observed. Consumers run `npm start` (PORT selects the port) or `node bin/tickets.js`; release verification runs the system case and full suite in a clean copy of the returned tree. Setup uses Node >=22 and isolated temporary files; tests clean their fixtures. Stop on drift, failed tests or invalid receipt.

For a clean fast-forward return with master checked out and no later commits, rollback from the repository root:
```sh
git reset --keep db642630e3a3bcafe7df0a609c3f53c571bc753e
```
For a working-tree return or only its files, substitute the reviewed keep paths:
```sh
git diff --binary db642630e3a3bcafe7df0a609c3f53c571bc753e shiploop/run-a699f982e7458fb6 -- <kept paths> | git apply -R
```
If later commits exist, restore only the intended paths after review; do not reset away later work.

Release-check verifies the focused and full tests on candidate and their absence on the original base; release-verify reruns them against a clean copy of returned source. No deploy or credentials required.

Returned-source verification: the guarded local return fast-forwarded master; a clean archive of that tree passed the integration case and full suite (127 tests). No remote deployment was requested.

## Operations and recovery
2026-10-29 local verification: the service owns audit and outbox entries, retrieved via `GET /tickets/:id/audit` and `GET /admin/outbox`; notification delivery is observable in `NOTIFY_FILE` or the in-memory notifier, and worker failures are logged to stderr. Operators configure ONCALL and DATA_FILE and consult docs/operations.md for dead events and data-file backup/restore. The local integration test observed the notification file and restart; existing tests exercise worker retry/dead paths. No running production target or alerting service was supplied, so production monitoring, alert routing and recovery execution were not observed. Revalidate the local checks on worker, persistence or configuration changes.

Operators inspect `GET /tickets/:id/audit` and `GET /admin/outbox`; worker failures appear in the outbox and stderr. See docs/operations.md for retry, dead events and data-file backup/restore. Integration tests observed outbox and notification file locally; no running production target was provided or assessed. The checkout owner can use the local rollback described above after reviewing subsequent changes.

## This run discovery (2026-10-29)
Observed: Node >=22, no dependencies, CommonJS; `npm test` runs node:test. README.md, CONTRIBUTING.md and src/server.js define local API and worker. The guarded source return is local; no deploy or publication was identified. Store owns state and audit; worker owns asynchronous delivery; persistence is optional. No repository-local skill was found. Baseline: `npm test`, 127 passed, exit 0 in execution worktree; output retained in run notes. Contribution guidance asks for an issue for API/data/notification changes; creating an external issue is outside this request.

## New feature test strategy
Planned R-6: node:test HTTP requests using existing helpers on ephemeral port and isolated store, verify mixed active and final states, ID order, malformed and equal names with no changes, audit and each assignment notification. Planned R-7: controlled clock and isolated temporary DATA_FILE; exercise strict threshold, priorities, statuses, assigned and missing ONCALL; tick twice, deliver actual notification, reopen file and tick again, assert exactly one. Check config default and invalid values. Existing assignment, API, persistence and worker tests preserve prior behavior. Tests clean up servers and temp directories. Due: implementation test and system test; no remote test applies. Expected RED on base: endpoint absent and escalation absent. Full suite baseline 127 passed.
Focused planned command (new file, once created):
```sh
node --test test/reassignment-escalation.test.js
```
Full suite command (existing):
```sh
npm test
```
IDs: test names describe behavior rather than artificial IDs; R-6 and R-7 are requirement IDs.

## Current preparation
Node and npm start successfully; no installation is needed. Baseline suite passed in isolated worktree. Existing helpers use ephemeral local listeners and temporary files. Source return is local, with no identified deployment trigger; no remote account is required. The focused test file is planned and must be authored before its command can run.

S1: `node --test test/reassignment-escalation.test.js` and `npm test` passed locally with TC_1 and 128 tests respectively.

S2: focused test command ran 3 tests; `npm test` passed 130 including TC_2 with a data-file reload.

S3: focused suite ran 6 cases and npm test passed 133 locally.

## W1 retained commands and fixtures
2026-10-29 return verification: local master was fast-forwarded to 703730220458; a clean archive of that returned source ran the system case and full suite successfully (1 and 134 tests). No remote activation, credentials or extra access were required. The system test exercised real local HTTP, scheduled worker and temporary data and notification files with teardown.

Focused component suite (fresh local services, manual clock, temporary files cleaned by node:test):
```sh
node --test test/reassignment-escalation.test.js
```
Full suite:
```sh
npm test
```
Contract and syntax checks:
```sh
rg -q "Bulk reassign active tickets" src/store.js
node --check src/app.js && node --check src/store.js && node --check src/tickets/validate.js && node --check src/worker.js && node --check src/templates.js && node --check src/config.js && node --check src/server.js
```
Revalidate the fixture helpers in test/helpers.js when the service constructor or Node runtime changes. Local system verification remains due; no remote delivery was requested. The outbox must keep escalation events in every status, and DATA_FILE is needed for restart persistence.
