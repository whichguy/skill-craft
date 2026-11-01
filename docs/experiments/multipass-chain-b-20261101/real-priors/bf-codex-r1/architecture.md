# Architecture

## Decisions
AD-1: Compose the existing URL parser, store and HTTP response helper; avoid new dependencies. Existing pagination helper floors partial pages, so correct it with regression coverage or use a local calculation without changing its public behavior.

## Real-boundary checks
Planned component checks use actual local node:http server on ephemeral loopback, fetch, and process-local static store. No deployed target, browser, cache, async queue or external service is involved. Tests close server after each case; no lasting data is changed. R-1 to R-4 are due at test and full suite at verify. No remote check is claimed.

## Structure
Node CommonJS module src/server.js owns HTTP query processing; src/users.js remains source of ordered users. No schema or persistent state changes. test/user-listing.test.js imports createServer and exercises the public HTTP interface.

## Interfaces and boundaries
Local HTTP request/response, one process; validate caller-controlled pagination before slicing. No cache, async processing, migration or external service.

## Stack
Node.js CommonJS, node:http and node:test, no dependencies.

## Conventions
Strict mode and small functions; HTTP tests use ephemeral loopback servers closed in finally.

## Superseded
None.
