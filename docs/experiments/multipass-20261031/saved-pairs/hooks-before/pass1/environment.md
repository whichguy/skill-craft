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
