# Architecture

## Decisions
AD-1: Extend GET /users in src/server.js using existing URL, send and listUsers; preserve other routes. Existing paginate helper floors page count, so calculate ceiling and slice for this contract. No dependency.

## Real-boundary checks
Planned TC_1 to TC_4 exercise actual HTTP on local ephemeral loopback; no remote service, cache, asynchronous processing or browser. With initial users [1,2,3], GET /users?page=2&size=2 should return id 3, total 3 and pages 2 (R-2). No mutable fixture persists; test teardown closes server.

## Structure
CommonJS local Node process: src/server.js owns the HTTP route, imports listUsers from src/users.js and responds via send. New query handling remains private to the server module; no exports or schema changes. Store remains static in process; no migration, cache or remote state.

## Interfaces and boundaries
HTTP request/response is synchronous; validation is server-side. No event delivery, authentication, async processing or deployment change.
