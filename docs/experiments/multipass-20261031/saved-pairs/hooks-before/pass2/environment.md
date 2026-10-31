# Environment

## Targets and runtimes
Observed: Node >=22, standard library only (README.md, package.json); local Node v26.12.1. The service listens via npm start and PORT; DATA_FILE is optional durable state, NOTIFY_FILE optional JSONL sink and worker can be disabled. The source checkout is the requested delivery target; no hosted target or deployment is identified. No .github workflow or configured hooksPath was observed; remote branch automation is unknown, and source return is not needed for local tests. Platform guide: none applicable.

## Commands
Observed: npm test runs node --test; npm start runs src/server.js. No lint or typecheck command is configured. Tests use ephemeral ports and temporary files (CONTRIBUTING.md, test/helpers.js).

## Platform facts
Binding repository conventions in CONTRIBUTING.md: CommonJS, no dependencies, error envelopes, store-owned audited changes, notifications through outbox and worker, cursor pages, decisions for new contracts and changelog/version on release. README.md describes CLI raw columns used by weekly report. src/tickets/validate.js trims and validates single-line names; src/tickets/query.js currently uses OR despite docs/api.md promising AND. src/persistence.js explicitly projects version 1 records; old tickets lack assignee. src/store.js owns mutable state; src/templates.js and src/notifier.js render worker deliveries. API validation errors are 400, state conflicts 409, missing tickets 404. No repo-local skills were found in README or CONTRIBUTING.

## Access and accounts
No remote target, identity or account is named. Local process identity runs tests; the request grants local repository changes only. Agent names are notification recipients, with no authentication or directory in the existing service.

## Skills
No repository-local skills found (README.md, CONTRIBUTING.md, file listing). ShipLoop applies to the run.

## Harnesses and suites
Planned: node:test with test/helpers.js starts an isolated HTTP service on port 0, worker off, closes connections in finally. Filesystem tests use fresh temporary directories and cleanup; worker delivery tests use a manual clock or controlled worker and local sinks. CLI tests use child process and isolated persisted fixture. No remote or browser target is in scope. Harness available: baseline npm test ran successfully. Revalidate if runtime or test setup changes.

## Harnesses and suites plan
Planned, due item test and system test: R-1 HTTP tests for valid names, null, limits, invalid body, unknown and inactive ticket, actor/audit and no-op; R-2 create/read/list, legacy v1 and restart round trip; R-3 pending/reassignment and worker delivery; R-4 intersecting status/priority/assignee including empty and pagination; R-5 CLI table/raw plus weekly report; R-6 full existing suite unchanged. Each test creates its own state, checks independently, tears it down. Expected-failure control: run new tests against unchanged baseline; assignment route and combined filtering must fail. Body limits and other existing nonfunctional behavior use unchanged suite.

## ID convention
New test names include TC_1 for assignment, TC_2 persistence, TC_3 notifications, TC_4 filters, TC_5 CLI, TC_6 existing suite.

## Commands
Focused planned suite (local Node, independent fixtures):
```sh
node --test test/assignment.test.js
```
Smoke planned: same focused command. Full suite planned (includes all test/ files and existing cases):
```sh
npm test
```
Both are expected to complete quickly and need no services; planned commands do not claim future passes.

## Prepared environment
Node test runner started with `node --test --help` (run/notes/runner-help.log); baseline suite passed in this isolated worktree. No installation, extra configuration or remote account is needed. Temporary fixtures are owned and cleaned by tests. Local source return was checked for local hooks and workflows; no automatic deployment was identified, but external branch automation is unknown. Local tests can run before return.

## Verified focused commands
These commands passed on the assembled local candidate, with independent fixtures under test/assignment.test.js.
```sh
node --test --test-name-pattern=TC_1 test/assignment.test.js
node --test --test-name-pattern=TC_2 test/assignment.test.js && rg -q "PUT /tickets/:id/assignee" src/app.js
node --test --test-name-pattern=TC_3 test/assignment.test.js
node --test --test-name-pattern=TC_4 test/assignment.test.js
npm test
```
The full suite passed 122 tests after S4; system-test must rerun on the assembled candidate.

## Integrated test plan
Local system check `test/assignment-system.test.js` starts an isolated loopback service with a temporary data and notification file, assigns through HTTP, ticks the existing worker, restarts, reads the assignment and audit, filters, and invokes the real CLI. It cleans its fixture; it does not test an external mail relay. The default full suite includes this case and all prior regression tests. Run at system-test; no remote target is specified. Revalidate if the service startup or file format changes. Both commands completed locally; executor owns repeat runs:
```sh
node --test test/assignment-system.test.js
npm test
```

## Commands
```sh
node --test --test-name-pattern=TC_1 test/assignment.test.js
node --test --test-name-pattern=TC_2 test/assignment.test.js && rg -q "PUT /tickets/:id/assignee" src/app.js
node --test --test-name-pattern=TC_3 test/assignment.test.js
node --test --test-name-pattern=TC_4 test/assignment.test.js
```

## Local delivery and rollback
The user requested this source repository as the target and authorized the local change. Release owner: run executor. Release-check reruns `npm test` and the integrated case in the isolated worktree; stop on failure. At release, review every candidate path and use ShipLoop's guarded workspace return to the original `master`. The return may fast-forward from the clean baseline when all candidate paths are kept; it does not push or deploy. The return itself has no observed local hook or workflow; remote automation is unknown. Release-verify runs `npm test` and the integrated check in a clean copy of the returned tree; failures return to corrective work. Tests create and clean isolated files and ephemeral servers; no service credentials or remote operation are needed. Monitor test output and the return receipt. Local checkout is accessed through `npm start` and `bin/tickets.js` (README.md).

For a clean fast-forward with no subsequent commits, rollback from the original branch root using:
```sh
git reset --keep af3dd1bf3740f58f8db05e28561a966cac71cf1e
```
If later commits must be preserved, reverse only reviewed kept paths (this leaves an uncommitted patch and requires the run branch):
```sh
git diff --binary af3dd1bf3740f58f8db05e28561a966cac71cf1e shiploop/run-524b1c1b6bd60b52 -- <kept paths> | git apply -R
```

## Bulk reassignment and escalation discovery

Observed 2026-10-29: Node v26.12.1; `npm test` passes 123 tests on unchanged execution checkout (run baseline-test.txt). Local HTTP and optional JSON DATA_FILE are the delivery boundary; no remote or CI configuration was found. `src/store.js`, `src/worker.js`, `src/persistence.js`, `src/tickets/validate.js`, and assignment tests are canonical examples. CONTRIBUTING.md requires no dependencies, CommonJS, audited store changes and worker-owned background work. No repository-local skill applies. Revalidate new persisted fields against version-1 input, and return the reviewed candidate to the original checkout at handoff.

## Harnesses and suites plan

Planned R-7: node:test HTTP and store cases, isolated service on port 0 and worker off: mixed active and inactive assignments, ordering, validation, audit and notification per ticket; due test stage. Planned R-8: deterministic fake-clock worker and temporary data file cases for strict age, eligibility, no ONCALL, delivery and restart; due test stage. Planned R-6: full existing suite after changes. Each test uses isolated state and cleanup, no external account. Existing test/helpers.js and test/assignment-system.test.js are available harnesses. Before feature edits, run new regression tests against base and retain expected failures. Nonfunctional compatibility confirmed by full suite and version-1 file reload.

## Commands

Focused planned cases (once created, local, seconds):
```sh
node --test test/reassignment-escalation.test.js
```
Full suite (local, seconds; all node:test files, no setup):
```sh
npm test
```

## ID convention
New cases use descriptive node:test names, mapping to R-7 and R-8 in test plan.

## Prepared environment for current change
Node v26.12.1 and node:test runner start locally (`node --test --help`, exit 0; run/notes/runner-help.txt). No packages or external account are required. Fresh local worktree and isolated temporary fixtures suffice; original checkout return triggers no identified CI or deploy. The baseline suite passed before edits.

## Verified bulk and escalation suites

`node --test test/reassignment.test.js`, `node --test test/escalation-config.test.js`, `node --test test/escalation.test.js` and `npm test` passed in the execution checkout; full suite had 127 tests. Each uses node:test, fresh service/store, injected clock or temporary data files cleaned after use. Revalidate after changes to API, worker, persistence or configuration. The suite needs no account or external target.

## Commands

Local focused suites and syntax checks, each seconds with no external prerequisites:
```sh
node --test test/reassignment.test.js
node --test test/escalation-config.test.js
node --test test/escalation.test.js
node --test test/bulk-escalation-system.test.js
node --check src/store.js
rg -i "bulk reassignment" src/store.js
```
`npm test` runs all retained cases including system integration; each fixture owns and removes its temporary directory. ST_2 exercises local HTTP, outbox, worker and real file restart, no host account; system-test owns rerun.

## Local source delivery for bulk and escalation

Target is the original master checkout; user requested local implementation and authorizes guarded source return. No push or deployment requested. Release-check confirms tests and source state; release reviews every changed path and uses ShipLoop workspace return. Release-verify runs `node --test test/bulk-escalation-system.test.js` and `npm test` in a clean copy of the returned result; focused test requires ST_2 to pass, original base lacks the new endpoint and fails. Fixtures use local ephemeral server and cleaned temporary files, seconds, no account. Stop on test failure or source drift. Consumer starts `npm start` and calls the HTTP API; configured worker requires ONCALL and DATA_FILE for restart durability.

Rollback, in source repository with master checked out and no later commits: `git reset --keep 0a2287591584e8eea9528e5120b19823ac3f9dea`. If only run files should be reversed, `git diff --binary 0a2287591584e8eea9528e5120b19823ac3f9dea shiploop/run-728c3fb13942d8b2 -- <kept paths> | git apply -R`; this leaves changes uncommitted. Never apply a rollback without checking current work.

## Returned candidate verification

Local master was fast-forwarded to the reviewed candidate. A clean archive of that exact tree ran the integration test and full `npm test` successfully (128 tests); fixtures clean up without accounts or external services. ShipLoop repeats these commands against its returned-tree copy before accepting release verification.

## Operational evidence (2026-10-29)

Local system tests observed audit retrieval through GET /tickets/:id/audit, outbox and file notification delivery, with restart from DATA_FILE. Worker test exercises retry and failure logging using the local fake notifier. Operators use GET /admin/outbox and docs/operations.md for dead events and restore; no external running production target or monitoring account was requested or observed. Local rollback route is recorded above.
