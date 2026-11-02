# User store architecture

## Structure
CommonJS node:http server src/server.js consumes ordered in-memory src/users.js.

## Decisions
AD-1: Compose filter and pagination at GET /users; retain existing paginate helper because its floor calculation is incompatible with a partial final page and existing behavior must remain. Use native URL and array operations without dependencies.

## Real-boundary checks
Planned TC_1 through TC_4 exercise loopback HTTP using node:test, fetch and a fresh listening server shut down after each case. R-1 filtering and compatibility, R-2 pagination, R-3 validation and R-4 preservation are due during the test stage and full suite. No hosted system, cache, asynchronous processor or UI exists.

## Stack
Node >=20, CommonJS and built-in HTTP and test modules; no external dependencies.

## Conventions
Single-quoted strings, semicolons and small functions; test/server.test.js supplies the server lifecycle pattern.

## Interfaces and boundaries
Only GET /users adds query handling; GET /users/:id and the store remain unchanged. User records remain process-local, with no migration or write path. Validation occurs before pagination; filtering is literal substring comparison.

Validated decimal page text may exceed JavaScript safe integers; the endpoint writes exact JSON number digits for such out-of-range pages. The store and full suite remain local and stateless across process runs.

## Superseded
None.
