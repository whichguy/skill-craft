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
Operators inspect `GET /tickets/:id/audit` and `GET /admin/outbox`; worker failures appear in the outbox and stderr. See docs/operations.md for retry, dead events and data-file backup/restore. Integration tests observed outbox and notification file locally; no running production target was provided or assessed. The checkout owner can use the local rollback described above after reviewing subsequent changes.
