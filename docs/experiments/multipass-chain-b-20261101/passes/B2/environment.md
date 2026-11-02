# Environment

## Targets and runtimes
Local Node HTTP server; Node >=20 specified in package.json, tested on v26.12.1. No npm dependencies. Local source checkout is the delivery target; no remotes or deployment configuration observed. Return to source has no observed automated deployment trigger.

Local source delivery: review the candidate paths, run the complete test suite, use the guarded workspace return to the original branch, then rerun npm test against a clean copy of the returned tree. Stop on source drift or failing tests. No remote publication or service deployment is part of this local project.

Local delivery procedure: review the guarded return plan and path dispositions, then return the tested candidate to the source checkout; run npm test on a fresh copy of the returned tree. Stop for source drift or failed checks. The developer runs npm start and an HTTP client reaches GET /users and GET /users/:id locally. No remote publication is implied. For a clean fast-forward with no later commits, rollback with git reset --keep to the pre-return commit; for a working-tree return reverse the reviewed delta while preserving unrelated work.

## Platform facts
CommonJS, node:http, node:test and assert/strict. src/users.js returns an ordered copy of the fixed in-memory array. src/server.js is the endpoint boundary. src/paginate.js uses floor for page counts, so its partial-page behavior is unsuitable without a compatible fix. Existing style uses single quotes, semicolons and small functions.

For a clean fast-forward return with no later commits, rollback uses `git reset --keep <pre-return-commit>` from the original branch; if there are later changes, reverse only reviewed paths while preserving later work. The run receipt retains the exact baseline and route.

## Skills
No repository-local skill links found in README or tracked files.

## Access and accounts
Local developer and HTTP consumer; no external account or target required. The developer operating the local process owns support and recovery. There is no authentication or audit trail in this server.

## Harnesses and suites
R-1: HTTP component tests for omitted, empty, case-insensitive, literal metacharacters, unknown parameter and no match. R-2: HTTP tests for defaults, first and partial last page, filtered totals, zero matches and out-of-range. R-3: HTTP tests for empty, nonnumeric, decimal, zero, negative, 101 size, boundaries and error field. R-4: run existing suite unchanged. Tests use node:test and fetch, createServer listening on loopback port 0 and close in finally; fixed in-memory users isolate requests and no mutable fixture exists. Focused suite is test/server-listing.test.js; full suite npm test. Base execution of new tests must fail before feature implementation. No remote tools or external accounts required.

Integrated system verification reuses the real loopback HTTP cases in test/server-roles.test.js and test/server-listing.test.js and existing tests through npm test. Each case starts and closes its own server; no shared mutable fixture or remote target. The full suite runs locally in seconds and is owned by the delivery workflow; repeat after candidate changes.

R-5 HTTP component cases: each id and unpaged and paged list expose all exact roles; role=admin/member/viewer returns its user; combine role and name for match and mismatch; filter before page and check totals and empty out-of-range page; invalid, empty, case-changed and repeated role values return the specified results. R-4 preservation: existing npm test, with only whole-user fixture role fields added. New tests live in test/server-roles.test.js, use node:test, fetch, loopback port 0 and close in finally. The new tests failed against the base and passed against the candidate; rerun them at system-test and release verification. No state persists across test servers. No browser, remote account or remote test is applicable. Baseline npm test was green before edits.

## ID convention
New role test names contain TC_5 (role projection), TC_6 (role filters), TC_7 (role validation).

New node:test names contain TC_1 (filtering), TC_2 (pagination), TC_3 (validation), TC_4 (compatibility).

## Commands
`npm start` runs src/server.js using PORT or 3000. Node and npm must be on PATH; no install is required. Startup output and process errors go to the invoking terminal stdout/stderr; there is no built-in request log, alerting, or persistent log sink. The operator can check a running instance with GET /users and rerun npm test for diagnostics. Stop the local process to clean up; restart it with npm start after a fix.

Focused HTTP suite:
```sh
node --test test/server-listing.test.js
```
Focused role suite (seconds, local loopback, Node >=20; TC_5, TC_6, TC_7):
```sh
node --test test/server-roles.test.js
```
Full suite, including focused cases, approximately seconds, no setup beyond Node >=20:
```sh
npm test
```

Syntax check, run from project root:
```sh
node --check src/server.js
```

For the initial local return, with the original branch checked out and no later commits, rollback is:
```sh
git reset --keep 51f2eab199bec99f89969b8790b84134f13a1f39
```
To reverse just the retained paths while preserving later work, from the original checkout:
```sh
git diff --binary 51f2eab199bec99f89969b8790b84134f13a1f39 shiploop/run-ebb0e87d96ef1140 -- README.md docs src test | git apply -R
```
