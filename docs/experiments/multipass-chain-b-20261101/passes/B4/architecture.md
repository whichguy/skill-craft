# User and team store architecture

## Structure
CommonJS node:http server src/server.js consumes ordered in-memory src/users.js and src/teams.js.

## Decisions
AD-1: Compose filter and pagination at GET /users; retain existing paginate helper because its floor calculation is incompatible with a partial final page and existing behavior must remain. Use native URL and array operations without dependencies.

### AD-2: Role data and request filtering
Use the existing CommonJS users module as the fixed in-memory data owner, adding a string role to each record; the existing HTTP server validates role query values and filters together with name before pagination. Reuse URLSearchParams and the existing JSON response helper. This avoids a new service, persistence, dependency or public module. No migration is needed. Status: implemented.

### AD-3: Team storage and shared list handling
Implemented: CommonJS src/teams.js exporting fixed ordered records with numeric id and member-id array, like src/users.js. The local Node server imports it and shares existing name and pagination handling between /users and /teams while retaining user-only role validation. This prevents response drift; duplicating validation risks divergent errors. No database, migration, shared state, asynchronous channel, new dependency or remote service. Routes are distinct namespaces; HTTP requests remain stateless. Verify actual responses and unchanged users via loopback tests.

### AD-4: Configurable listing page size
Change the shared CommonJS HTTP listing branch in src/server.js: validate PAGE_SIZE as decimal integer 1..50, fallback 25 for absent or invalid configuration, and use it when a page is requested without size. Explicit size overrides it; both endpoints retain identical validation and error shape. Alternatives: separate per-route handling risks drift; exposing invalid defaults breaks the size bound. No schema, migration or new dependency. Verify by loopback node:test and full suite. Status: implemented and verified by TC_11 and TC_12.

## Real-boundary checks
Planned TC_1 through TC_4 exercise loopback HTTP using node:test, fetch and a fresh listening server shut down after each case. R-1 filtering and compatibility, R-2 pagination, R-3 validation and R-4 preservation are due during the test stage and full suite. No hosted system, cache, asynchronous processor or UI exists.

R-5 checks run locally at the HTTP boundary against an ephemeral loopback server. The test starts with the fixed base store, sends requests, checks parsed JSON and closes the server; no retained test state. The suite observes actual server and store together; no remote target, authorization, cache, or async behavior is involved. Repeat at integrated test and release verification.

Planned team TC_8 through TC_10 run against the actual local server and static store via node:test and fetch on loopback. Each test owns and closes its ephemeral server; no retained state, remote access, cache, async processor or browser. New cases must fail against the unchanged base and pass with implementation; rerun full suite for user behavior. The project has no hosted target.

Planned page-size checks run locally against the real shared HTTP handler, using a fresh ephemeral loopback server and controlled/restored environment for each case; the base should fail new expectations. No remote or retained target, browser, cache, async channel or event sink applies. Full suite preserves the unrelated endpoints.

## Stack
Node >=20, CommonJS and built-in HTTP and test modules; no external dependencies.

## Conventions
Single-quoted strings, semicolons and small functions; test/server.test.js supplies the server lifecycle pattern.

## Interfaces and boundaries
GET /users and GET /teams share name and pagination handling; user role filtering remains user-only. Both detail routes read their respective fixed stores. User records remain process-local, with no migration or write path. Validation occurs before pagination; filtering is literal substring comparison.

Validated decimal page text may exceed JavaScript safe integers; the endpoint writes exact JSON number digits for such out-of-range pages. The store and full suite remain local and stateless across process runs.

## Superseded
None.
