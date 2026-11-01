# Architecture

## Decisions
AD-1: Extend the existing HTTP listing handler, reuse listUsers and native URL parsing. The existing paginate helper floors partial pages and cannot be reused unchanged.

## Real-boundary checks
Planned HTTP component tests exercise actual local node:http server and fixed store via loopback; no remote target, identity, caching, state mutation or asynchronous processor. GET /users/:id remains covered by existing suite and a query regression. Revalidate tests against unchanged base as a failure control before implementation.

## Structure
AD-2: Keep listing handling in CommonJS src/server.js; existing createServer imports listUsers from src/users.js. Add HTTP tests under test/user-listing.test.js. No new exports, data storage, schema or migration. Node process serves existing in-memory records over request/response.

## Conventions
Use strict mode, native modules and node:test with loopback fixture as test/server.test.js.

## Interfaces and boundaries
Only GET /users query handling changes; all other routes and PORT startup remain.
