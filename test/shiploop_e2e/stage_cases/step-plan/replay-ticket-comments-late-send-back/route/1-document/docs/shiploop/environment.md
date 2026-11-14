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

## Bulk reassignment and escalation discovery (2026-10-29)

Observed: Node v26.12.1; package requires Node >=22, no dependencies. `npm test` executes `node --test`; baseline passed 121 tests on the unchanged isolated checkout, output in the run notes. CONTRIBUTING.md requires CommonJS, store-owned mutations, outbox notifications, worker jobs, node:test coverage, decision records and release notes. Existing patterns: src/store.js assignment and persistence; src/app.js validation and routing; src/worker.js and src/server.js worker composition; src/templates.js notifications; test/assignment.test.js and test/worker.test.js. README.md describes local service and configuration. No applicable repo-local skill found. Source return is a local guarded Git operation; no remote is configured and no deployment trigger was observed. No hosted delivery was requested or verified.

### Bulk and escalation suite plan

Planned, due implementation/test: R-6 HTTP component cases cover matching open/in_progress versus final/other agents, sorted IDs, no matches, invalid names/equality and side effects; store/outbox and notifier assertions verify audit and delivery. R-7 deterministic manual-clock cases cover strict age, eligible/ineligible states, ONCALL absent, configured threshold, repeat ticks, persisted restart and legacy records; exercise real worker composition and rendered notification. R-1–R-5 preservation and standard-library compatibility: full `npm test`. Use node:test, test/helpers.js ephemeral server and manualClock, isolated temp data files cleaned by test hooks; no external account, browser or service required. Test-first base should fail new cases. Planned checks are not passes.

Focused (new tests, after authoring):
```sh
node --test test/reassignment-escalation.test.js
```
Full (all test files, under one second at baseline):
```sh
npm test
```

### Preparation for bulk and escalation

Node v26.12.1 and node:test are available; `node --help` starts successfully (run notes). Baseline ran in the isolated worktree with fresh test fixtures. No packages, accounts, remote environments or additional setup are needed. Local source return has no configured remote or observed deployment trigger.

### Verified bulk and escalation checks

Focused `node --test test/reassignment-escalation.test.js` passed TC_1–TC_3; `npm test` passed 124 tests. The test suite uses isolated temp files and a manual clock; all three new tests fail against the item base. The API contract comment check used during this run is specific to the review and is not a general-purpose operator command.

### Release route for bulk and escalation

Local source delivery is authorized by the requested repository change; no remote push or deployment is in scope. Review and return the committed candidate to the original clean master through the guarded workspace route at release. Run `npm test` in the clean returned copy at release-verify; it requires Node >=22 and no installed packages, uses ephemeral HTTP ports and temporary files, and should pass all 124 tests. A failed check stops release completion. Operators configure ONCALL and DATA_FILE as described in README and docs/operations.md. Monitor the outbox and worker logs under the existing operating procedure.

Rollback from a fast-forward with no later commits, on master:
```sh
git reset --keep aefada8f237127f69a2c436d49f32ad798df151e
```
For later commits, reverse only kept paths using `git diff --binary aefada8f237127f69a2c436d49f32ad798df151e shiploop/run-d0df79316ac3487a -- <kept paths> | git apply -R`; inspect later changes first.

Focused command:
```sh
node --test test/reassignment-escalation.test.js
```
The one-off contract search `rg -q 'Bulk reassignment' src/app.js` is a review check, not an operator command.

### Returned candidate verification

The source checkout received the reviewed candidate through a verified fast-forward; the post-return test is run from a clean copy of the returned tree by ShipLoop. The source branch itself is not a hosted deployment. Node and isolated test fixtures remain the only prerequisites.

### Operational handoff (2026-10-29)

Local tests observed audit entries, outbox status and worker delivery/retry behavior; docs/operations.md describes `GET /admin/outbox`, stderr warnings, data backups and recovery. This is a source delivery, not a running production deployment: live log access, alerting and mail relay observation were not assessed. The service operator owns those production checks and restoration of DATA_FILE. No production monitoring was changed.

## Comments discovery (2026-10-31)

Observed: Node >=22, no dependencies; npm test runs node --test (package.json, README.md). The unchanged execution checkout passed 124 tests, exit 0; see run scratch/baseline.log. HTTP handlers validate and delegate to TicketStore; errors use the established envelope (src/app.js, src/http.js, src/errors.js). The store owns state, audit and outbox, saved together; persistence uses version 1 JSON and explicit record fields (src/store.js, src/persistence.js). Notifications are asynchronous through the worker and templates (src/outbox.js, src/worker.js, src/templates.js). Names are trimmed, case-sensitive and limited to 64 characters (src/tickets/validate.js). Local checkout return is the requested delivery; no deployment or CI configuration was discovered and no hosted target is named. Return is not a prerequisite to local candidate checks. No repository-local skill was identified (README.md and repository file list). No external account or identity is required. Revalidate state and response contracts during implementation.

## Comment suite plan

Planned R-8: node:test HTTP component cases using test/helpers.js and isolated server port 0 with worker disabled; test valid creation and retrieval, ordering with equal timestamps, all statuses, validation and unchanged state on errors (TC_Comments_API). Planned outbox and worker checks for self, unassigned, multiple authors, and rendered payload (TC_Comments_Notify); check audit actor and comment data on each addition and no audit on failure. Planned separate temporary data-file fixture with teardown and restart plus pre-change file (TC_Comments_Persist). Existing suite preserves all prior features. npm test is the full suite; node --test test/comments.test.js is focused and smoke. The new test file will be added before implementation for expected-failure control. No remote service, account or browser required.

```sh
node --test test/comments.test.js
```

```sh
npm test
```

Both execute locally, use standard library only, and require Node >=22. Focused command targets TC_Comments_API, TC_Comments_Notify and TC_Comments_Persist; full command includes all existing cases. Fixtures must be unique and cleaned up. Checks are planned, not passed.

## Comment preparation

Node and node:test runner start successfully; output is in run/scratch/runner-readiness.log. Baseline full suite passed before edits. Tests use isolated free-port service and temporary fixture directory, no install or remote access. Candidate checkout is isolated; return to source is authorized at the guarded release boundary and no evidence of branch-triggered deployment was found. Consumer is local API caller; no account required.

S1 verification: node --test test/comments.test.js ran two cases and npm test ran 126, all passed; tests use manualClock and isolated data files.
