# Specification

## Requirements

### R-1: Listing and literal name filtering
Basis: request S2, S3, S7; existing src/server.js and src/users.js. GET /users without page or size returns a JSON array in ascending id order; absent or empty name retains every user; otherwise name is a case-insensitive plain substring (including regex metacharacters literally). Unrelated query parameters are ignored. Confirm by HTTP node:test requests for absent, empty, mixed-case, literal and no-match inputs and unrelated parameters. No user data is modified; store remains process-owned and lasts for process lifetime. Existing HTTP callers can read the returned records as before; no new identity or logging is introduced.

HTTP filtering and array compatibility are exercised by test/users-listing.test.js. (W1/S2)

### R-2: Pagination
Basis: request S4, S5. When page or size is present, GET /users filters first and returns JSON object page, size, total, pages and items; page defaults to 1 and size to 10, pages is ceiling(total/size), including 0 for no matches, and items are the id-ordered slice or empty beyond the final page. Confirm by HTTP tests for defaults, partial and exact pages, no matches, and out-of-range pages. Data remains read-only; no async, cache or external service applies.

The helper in src/paginate.js counts partial pages; test/list-pagination-helper.test.js exercises partial and empty lists. (W1/S1)

HTTP pagination metadata and large out-of-range page handling are exercised by test/users-listing.test.js. (W1/S2)

### R-3: Pagination errors
Basis: request S6. page must be a whole number at least 1 and size a whole number 1 through 100; an invalid or empty supplied value returns HTTP 400 with a JSON error explaining the offending parameter. Confirm by HTTP tests for zero, negative, fractional, nonnumeric, empty, oversized size and boundary values. Existing unrelated query parameters remain ignored.

HTTP rejection and boundary cases are exercised by test/users-listing.test.js. (W1/S2)

### R-4: Compatibility and tests
Basis: request S1, S7-S9; README.md and package.json. Existing behavior including GET /users/:id and existing tests remains intact, npm start remains available, no dependencies are added, and npm test runs new node:test tests under test/ with existing tests. Confirm by npm test and HTTP compatibility checks. The returned implementation and regression suite cover R-1 through R-4.

## Non-functional requirements

Use the existing dependency-free Node >=20 runtime and in-memory lifetime. HTTP clients receive JSON and no new persistence or external delivery is required. No numeric performance, availability, accessibility or UI target was requested; this is a small local machine API with no UI. Confirm runtime compatibility with npm test and package inspection.

## Replayable acceptance examples

Starting with the three users in src/users.js, `GET /users?name=a` returns Ada, Grace and Alan in id order; `GET /users?name=ADA` returns Ada; `GET /users?name=%2E` returns an empty array because a dot is literal. `GET /users?size=2&page=2` returns page 2, size 2, total 3, pages 2 and Alan as its only item. `GET /users?name=ada&size=2` returns total 1, pages 1 and Ada. `GET /users?name=nomatch&page=1` returns total 0, pages 0 and empty items. `GET /users?page=` returns 400 with an error identifying page. The HTTP tests exercise these outcomes against the static store.

## Retired

None.
