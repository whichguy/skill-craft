# Architecture

## Decisions
AD-1: Reuse existing node:http server and URL parsing, ordered listUsers and pagination helper; correct helper's page count for partial pages. Avoid dependencies.

## Real-boundary checks
Planned local HTTP component tests start createServer on localhost, query actual endpoints and assert status and JSON; server closes per test. They observe the same HTTP boundary used by clients. Paginator unit tests use arrays. No remote, cache, authorization, async or UI boundary exists. Existing baseline has seven tests passing but no listing coverage; new cases remain planned.

## Structure
AD-2: Keep server routing and query validation in src/server.js; use existing CommonJS listUsers and paginate exports. Correct src/paginate.js page counting; no new exported names or storage. HTTP request/response remains synchronous with read-only in-process data; no migration, worker, cache or remote environment.

## Conventions
Reuse node:test and the existing ephemeral localhost fixture; no dependencies or config changes.

## Interfaces and boundaries
GET /users owns filtering and optional page envelope; GET /users/:id remains unchanged. paginate keeps its existing return shape.

W1 local HTTP and paginator checks passed; system-test owns the pending npm start process smoke and full suite rerun. Page values larger than JavaScript's safe integer range retain their exact decimal JSON representation and have empty items, since they necessarily exceed the available in-memory array.

## Stack
CommonJS on Node >=20, node:http, node:test and built-in fetch; no dependencies.

## Superseded
None.
