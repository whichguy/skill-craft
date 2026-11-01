# Architecture

## Decisions
AD-1: Keep HTTP parsing at server boundary and use the existing in-memory user store. Reuse or correct existing paginate helper only where appropriate; no new dependencies.

## Real-boundary checks
Planned: HTTP component tests exercise local server over loopback using node:test and fetch; setup opens an ephemeral port and teardown closes the server. User-store contents are immutable for these requests. Full npm test covers existing and new behavior. No remote deployment, browser, cache or asynchronous boundary is in scope.

## Structure
CommonJS `src/server.js` owns HTTP query parsing, reads `src/users.js`, and can use `src/paginate.js`; public exports remain unchanged. Tests import `createServer` and paginate using CommonJS. The fixed user data is process-local and unchanged; no migration or new storage.

## Interfaces and boundaries
HTTP request/response is the only affected boundary; no async processing, cache, external identity or additional connection.
