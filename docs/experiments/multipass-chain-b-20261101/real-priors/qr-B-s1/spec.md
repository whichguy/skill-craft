# Specification

## Requirements

### R-1 Listing and filtering
Basis: request S2, S3, S7; src/server.js and src/users.js. Preserve id ordering and array form without page or size; change listing to filter case-insensitive literal substring of name. Empty name matches all; unknown parameters ignored. Confirm by HTTP tests for no filter, mixed case, literal punctuation, empty and no match. Failure: n/a, all names are text.

Implemented in src/server.js; HTTP coverage in test/user-listing.test.js TC_1 (W1/S1)

### R-2 Pagination
Basis: request S4, S5. After filtering, page and size select id-ordered slices; either parameter changes response to {page,size,total,pages,items}, defaults page=1 and size=10, pages is ceiling of total/size (zero for none), out-of-range items empty. Confirm by HTTP tests covering partial pages, defaults, filtering, no matches and beyond last page. Failure: invalid values addressed by R-3.

Implemented in src/server.js; HTTP coverage in test/user-listing.test.js TC_2 (W1/S2)

### R-3 Validation
Basis: request S6. page must be a whole number >=1, size 1..100; reject empty or invalid values with 400 and explanatory JSON error. Confirm by HTTP boundary and invalid-input tests. Default: decimal digit strings and first repeated value.

Implemented in src/server.js; HTTP coverage in test/user-listing.test.js TC_3 (W1/S2)

### R-4 Compatibility and execution
Basis: request S1, S7-S9. Preserve GET /users/:id and other existing behavior, npm start and PORT; no dependencies. Existing node:test tests remain unchanged and pass alongside new tests under test/. Confirm by npm test and HTTP lookup test. State remains the process-owned static in-memory store; no mutation, identity or external service is added.

## Non-functional requirements
Node >=20 per package.json; no new dependencies. No performance, UI, security or persistence bounds requested beyond existing behavior; no UI or remote service is affected.
