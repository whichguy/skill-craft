# Environment

## Targets and runtimes
Local Node HTTP server; Node >=20 specified in package.json, tested on v26.12.1. No npm dependencies. Local source checkout is the delivery target; no remotes or deployment configuration observed. Return to source has no observed automated deployment trigger.

Local source delivery (authorized by the requested workspace change): review the candidate paths, run the complete test suite, use the guarded workspace return to the original branch, then rerun npm test against a clean copy of the returned tree. Stop on source drift or failing tests. No remote publication or service deployment is part of this local project.

Local delivery procedure: review the guarded return plan and path dispositions, then return the tested candidate to the source checkout; run npm test on a fresh copy of the returned tree. Stop for source drift or failed checks. The developer runs npm start and an HTTP client reaches GET /users and GET /users/:id locally. No remote publication is implied. For a clean fast-forward with no later commits, rollback with git reset --keep to the pre-return commit; for a working-tree return reverse the reviewed delta while preserving unrelated work.

Node and npm are available locally; `node --help` starts the test runner and `npm test` runs without installation. The checkout is isolated and the client needs only local HTTP access. No source-return deployment trigger was found.

Pre-return release-check verifies the suite and reviewed paths; release performs guarded return. Release-verify runs `npm test` on a fresh copy of the returned tree, requiring TC_8, TC_9, TC_10 and all existing tests. Earlier base red checks establish the new cases fail before their respective changes. Stop on source drift or failure. No external deployment, access change or account is required.

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

R-6 and R-7 HTTP component cases (TC_8, TC_9, TC_10): verify all five records and detail/404; literal mixed-case, empty and no-match name filters; page/size defaults, filtered and empty totals, last and out-of-range pages; invalid inputs, exact errors, boundary size and huge page text. Due test and system-test, owner implementation. Expected failure against base: /teams returns 404. Existing npm test preserves R-1 through R-5; rerun after edits. Reuse node:test/fetch and a fresh loopback port 0 server closed in finally; no mutable state or remote target. Node >=20 required; baseline succeeded. Revalidate if server or runtime changes. No browser or external service needed.

## ID convention
Team test names contain TC_8 (records and detail), TC_9 (filtering and pagination), TC_10 (validation and large pages).

New role test names contain TC_5 (role projection), TC_6 (role filters), TC_7 (role validation).

New node:test names contain TC_1 (filtering), TC_2 (pagination), TC_3 (validation), TC_4 (compatibility).

## Commands
`npm start` runs src/server.js using PORT or 3000. Node and npm must be on PATH; no install is required. Startup output and process errors go to the invoking terminal stdout/stderr; there is no built-in request log, alerting, or persistent log sink. The operator can check a running instance with GET /users and rerun npm test for diagnostics. Stop the local process to clean up; restart it with npm start after a fix.

Team focused/smoke suite (seconds; local loopback; TC_8 through TC_10):
```sh
node --test test/server-teams.test.js
```

Focused team detail and listing commands (local loopback, Node >=20):
```sh
node --test --test-name-pattern='TC_8' test/server-teams.test.js
node --test --test-name-pattern='TC_9|TC_10' test/server-teams.test.js
```

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
git reset --keep d6f67a3847cb434429ce4c06a650ea1b95c0f420
```
To reverse just the retained paths while preserving later work, from the original checkout:
```sh
git diff --binary d6f67a3847cb434429ce4c06a650ea1b95c0f420 shiploop/run-14e3d4729258be09 -- README.md docs src test | git apply -R
```

Observed: README.md, package.json and src/server.js describe a dependency-free Node >=20 service, tested locally by `npm test` (node --test). src/users.js and test/server-listing.test.js are canonical store and HTTP-test examples. Baseline on unchanged execution checkout passed 15 tests (run notes/baseline-test.txt). Binding request: return changes to the original checkout, preserve existing tests and expose team HTTP routes. No hosted target, remote access, cache, CI deployment or applicable repository-local skill is identified. Runtime data is static in-process; requests have no session state. Source return has no observed automatic deployment configuration; revalidate before return.
