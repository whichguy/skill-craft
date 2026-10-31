# Environment

## Targets and runtimes
The requested target is the local checkout, returned from the isolated worktree at release. No remote deployment or return-triggered deployment is evidenced in the repository; local tests can run before return. Node >=22, CommonJS and standard library only (README.md, package.json); Node v26.12.1 observed. State is in memory or DATA_FILE; notification delivery uses an in-memory sink or NOTIFY_FILE, via worker and outbox (README.md). No external account is needed.

## Commands
`npm test` runs `node --test`; `npm start` starts src/server.js. The unchanged baseline passed 117 tests in the worktree (run notes/baseline-test.txt). No linter is configured.

## Platform facts
CONTRIBUTING.md requires envelope errors, store-owned mutations with audit/outbox/persistence, worker-only delivery, cursor listings, no dependencies and tests. src/tickets/validate.js trims and validates single-line names; src/templates.js supplies notification wording. src/persistence.js explicitly maps fields and must support old files. src/tickets/query.js currently uses OR for multiple filters; requested intersection changes that. README.md requires first four raw CLI columns retain their positions for scripts/weekly-report.js.

## Skills
No repository-local skill is referenced by README.md or CONTRIBUTING.md.

## Access and accounts
Local process operator and API callers use local files and HTTP. Agents are named strings, not authenticated identities. No remote access required.

## Harnesses and suites
Use built-in node:test and node:assert; test/helpers.js creates an ephemeral HTTP server with worker off and cleanup. File tests use isolated temporary directories and cleanup; no shared fixture. Existing test suite ran successfully in baseline. Revalidate by running new focused file and full suite after implementation. No remote target or browser is required.

## Harnesses and suites plan
All checks planned, owned by implementation/test stages. R-1: HTTP cases create ticket, assign, unassign, invalid values, missing ticket, states, and no-op side effects. R-2: HTTP reads and isolated data file legacy and restart tests. R-3: inspect outbox/audit and worker delivery with separate pending events. R-4: HTTP combined status, priority, assignee and cursor tests. R-5: invoke CLI against isolated data and verify table/raw fields and existing report; run full suite. Expected failure control: run added tests on baseline before feature. Full suite checks no-dependency behavior and existing contracts. No credentials or remote access are needed.

## ID convention
New test names use `TC_1` through `TC_5` corresponding to requirements, with descriptive suffixes.

## Commands
Focused suite (new file, short, no external dependencies):
```sh
node --test test/assignment.test.js
```
Full suite (all existing and new tests, short):
```sh
npm test
```

## Prepared environment
Node v26.12.1 and built-in test runner are present; `node --help` starts (run/notes/node-help.txt), and unchanged `npm test` completed successfully. No installation or secrets are required. Isolated worktree and per-test temporary files prevent source data changes. Local checkout is the operator entry; no documented branch-triggered deploy or necessary pre-return consumer check was found.

## Verified assignment checks
`node --test test/assignment.test.js` passed four cases; `npm test` passed 121 cases after assignment. The tests use test/helpers.js's isolated server, per-test temporary directories and teardown. Revalidate after implementation changes. The local notifier and file sink are the delivery boundary; no remote relay verification was requested.

## Integrated suite
System-test uses `node --test test/assignment.test.js` to exercise the assembled HTTP, store, file, worker and CLI boundaries, followed by `npm test` for the full service. Each case owns its server or temporary file and cleans it on completion; no credentials or external service are required. Revalidate when the candidate changes. Both checks are local and due at system-test; remote relay behavior is outside the requested local target.

## Local return and verification
The user's requested target is the original local `master` checkout. User request authorizes returning reviewed source changes; it does not request a remote deployment. At release, review and return the candidate with the guarded workspace commands, then release-verify runs `npm test` and `node --test test/assignment.test.js` in a clean copy of the returned result. The focused suite failed against the original base and passes on the candidate, so it distinguishes the feature's absence and presence. Tests create isolated files and servers and clean them up. Stop if source drift or a failing check prevents return; investigate rather than overwrite.

Rollback a fast-forward on the original branch with no later commits or conflicting work:
```sh
git reset --keep 2e416e91118338a32979ff152d67afadf09f861f
```
With later work, reverse only reviewed paths using the run branch and baseline; inspect the diff before applying it. No automatic push or deployment is included.

## Returned result
The reviewed candidate was returned to the original local branch at 7ee4c070aba76afb9944afd080bdfecad45ac941 by a verified fast-forward receipt. Post-return checks run against a fresh copy of that tree; no hosted deployment or account access was involved.

## Operational observations
As of 2026-10-29, local tests observed audit via `GET /tickets/:id/audit` and pending/sent outbox via `GET /admin/outbox`; worker and notifier tests exercise successful delivery and retry. Operators use docs/operations.md for data-file recovery and dead notifications, and `LOG_REQUESTS=1` for request logging. No hosted instance or alerting system was in scope or observed. Restoring a deployment and inspecting a production relay remain with its operator; local source rollback is above.
