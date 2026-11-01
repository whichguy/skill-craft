# Specification

## Requirements

### R-1: Filter users
Basis S2-S3, S7; src/users.js and src/server.js. Preserve id order and user data. GET /users with `name` returns only case-insensitive literal substring matches; empty matches all. Without pagination return an array. Confirm by HTTP tests for case, literal punctuation, empty and no match. No state mutation; store stays in process memory as before.

### R-2: Paginate users
Basis S4-S5. After filtering, GET /users with page or size returns page, size, total, pages and items; default page 1 or size 10; pages is ceiling of total/size, zero when total is zero; page beyond last yields empty items. Confirm by HTTP tests of defaults, partial page, exact boundary, empty results and out-of-range page. Existing list order and data remain intact.

### R-3: Validate pagination
Basis S6. GET /users rejects empty, non-whole, out-of-range page or size with HTTP 400 JSON error explaining the parameter; page >=1 and size 1..100. Confirm by HTTP tests of boundaries and malformed values.

### R-4: Compatibility and operation
Basis S1, S7-S9. Unknown query parameters ignored; GET /users/:id and other existing behavior unchanged; npm start retains PORT behavior. Existing tests remain unchanged and new node:test tests run with npm test. Confirm with full suite and HTTP checks. State is existing process-owned data; no new identity, persistence, logging, async work or deployment.

Implementation and HTTP regression tests: src/server.js and test/users-listing.test.js. (W1/S1)

## Concrete acceptance examples
Against the baseline store (ids 1 Ada Lovelace, 2 Grace Hopper, 3 Alan Turing), `/users?name=la` returns ids [1, 3]; `/users?name=%2E` returns []; `/users?name=` returns [1, 2, 3]. `/users?page=2&size=2` returns page 2, size 2, total 3, pages 2, items [id 3]; `/users?name=none&page=1` returns total 0, pages 0 and items []; `/users?size=100` defaults page to 1 and returns all three. `/users?page=` and `/users?size=101` return 400 with an error. These are test oracles, not claims of execution; tests must assert complete metadata and actual user objects.

## Non-functional requirements
Dependency-free Node >=20, as package.json specifies; verify npm test and package manifest. No new performance, security, persistence or availability targets were specified; preserve existing behavior.
