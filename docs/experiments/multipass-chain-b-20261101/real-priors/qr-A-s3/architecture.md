# Architecture

## Decisions
AD-1: Compose URLSearchParams, listUsers, filtering and pagination within the HTTP listing route. Existing paginate helper floors page counts and is left unchanged to preserve existing behavior; use a ceiling and slice for this endpoint. Confirm by HTTP tests.

## Real-boundary checks
Planned: node:test plus fetch against an ephemeral local server exercises the actual HTTP boundary and JSON response for R-1 through R-3, and existing suite covers R-4. No remote, browser, account, persistent target, cache, asynchronous processor or event sink applies. Fixture server is closed after each case and starts with static store state. No host tool beyond the available Node runtime is required.

## Stack
Node >=20, CommonJS and node:http, no dependencies.

## Structure
AD-2: Keep query handling inside src/server.js's existing GET /users branch; it imports listUsers and uses built-in URLSearchParams. New HTTP tests use CommonJS and createServer from test/listing.test.js. No new persistent schema or storage; in-memory USERS remains unchanged. No remote environment exists.

## Conventions
Use strict mode, small functions, JSON responses via existing send, node:test and assert/strict with ephemeral ports, as in existing server tests.

## Interfaces and boundaries
HTTP GET request/response, read-only static process-owned state; no cache, identity, migration, asynchronous queue or external integration. Pagination validation is server side. No new configuration or event channel.

## Superseded
None.

## Completed item observations
W1 emits exact digits for arbitrary-length positive page numbers in JSON and uses numeric offsets only for slicing. HTTP tests verify the real local boundary; system and release checks are still due.
