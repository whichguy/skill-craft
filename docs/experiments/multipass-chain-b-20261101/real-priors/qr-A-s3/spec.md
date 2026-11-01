# Specification

## Requirements

### R-1 Filtering and compatibility
Basis: request GET /users and src/server.js baseline. GET /users returns users in id order, filtered by case-insensitive literal name substring when name is present; empty name matches all. Without page or size the result remains an array; unrelated parameters are ignored. Confirm by HTTP tests for mixed case, literal metacharacters, empty and absent name, unknown parameter and no match. Preserve GET /users/:id and other routes; confirm existing tests and query-bearing id requests. The static in-memory store remains process-owned and unchanged by reads; no authentication, cache, async work or state migration is introduced. Duplicate keys default to first value. Implementation and checks pending.

Observed in src/server.js and test/listing.test.js: literal name filtering preserves id order and empty name matches all. (W1/S1)

### R-2 Pagination
Basis: request pagination. When page or size is present, return JSON object page, size, total, pages, items, with defaults 1 and 10, total after filtering, pages ceiling(total/size), including 0 for no matches. Items are ordered by id and slice the selected 1-based page; pages after last are empty. Confirm with HTTP tests for both defaults, partial and empty pages, out-of-range and filter interaction. Implementation and checks pending.

Observed in src/server.js and test/listing.test.js: paginated responses contain counts and the filtered slice. (W1/S2)

### R-3 Validation
Basis: request input validation. page must be a whole number at least 1 and size a whole number 1 through 100; invalid or empty present values return HTTP 400 JSON with an error explaining the invalid parameter. Confirm with HTTP boundary and malformed-value tests. Implementation and checks pending.

Observed invalid pagination values return JSON errors with HTTP 400. (W1/S2)

### R-4 Existing behavior and tests
Basis: request compatibility. Existing tests pass unchanged, new node:test tests in test/ run under npm test, and npm start remains operational. Confirm with full npm test and server smoke check. No dependencies added.

## Non-functional requirements
Dependency-free Node >=20 as in package.json. No performance target supplied; list is in memory and has three users. No UI, remote deployment, persistent data or additional privacy contract is requested. Errors are JSON and no new logs of user data are needed.

## Retired
None.
