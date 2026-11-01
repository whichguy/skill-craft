# Specification

## Requirements

### R-1: Filter users
Basis: request S2-S3, S7. GET /users filters names by literal case-insensitive substring; empty name matches all. Without page or size the result is an id-ordered JSON array and unknown parameters are ignored. Confirm by HTTP tests for mixed case, literal punctuation, empty and absent filters, and unmatched names. For example, `name=ADA` returns Ada Lovelace; `name=%2E` returns no users and `name=` returns all three. Existing store state is read only; no authentication or persistence changes.

Implemented in src/server.js and covered by TC_1 in test/user-listing.test.js. (W1/S1)

### R-2: Paginate users
Basis: request S4-S5. When page or size occurs, GET /users responds with page, size, total matched, pages rounded up (zero for no matches), and items in id order. Defaults are page 1 and size 10; out-of-range pages have empty items. Filter before pagination. With the baseline three users, `size=2&page=2` returns id 3, total 3 and pages 2; `name=missing&size=2` returns total 0, pages 0 and empty items. Confirm using HTTP tests for defaults, partial final pages, no matches and out-of-range pages.

Implemented in src/server.js and covered by TC_2 in test/user-listing.test.js. (W1/S1)

### R-3: Validate pagination
Basis: request S6. Invalid or empty page and size return HTTP 400 JSON with an explanatory error. Page is an integer >=1 and size an integer 1..100. Confirm by HTTP tests for valid boundaries and invalid blank, zero, negative, fractional and non-numeric values.

Implemented in src/server.js and covered by TC_3 in test/user-listing.test.js. (W1/S1)

### R-4: Preserve existing behavior
Basis: request S1, S7-S9. GET /users/:id and all other existing behavior remain unchanged; no dependencies. Add node:test coverage under test and run npm test including unchanged existing tests. Confirm by full suite and review. State is a fixed in-memory process-owned array, reloads on restart; clients may read records as currently exposed. No async processor or external boundary is introduced.

The id route is covered by TC_4 and the existing suite. (W1/S1)

## Non-functional requirements
No new runtime dependencies; verify package.json. Existing Node >=20 and PORT behavior remain. No UI or hosted service is in scope; no performance bound specified.
