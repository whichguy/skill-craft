# User store API specification

## Requirements

### R-1: Filtered listing
Basis: user request 2026-11-01. GET /users returns an id-ordered JSON array when neither pagination parameter is present. A name query filters by literal case-insensitive substring; an empty value matches all, and unrelated parameters are ignored. Confirm by HTTP node:test cases for absent, empty, mixed-case, special-character and no-match queries. Preserve existing store and GET /users/:id behavior.
Implementation and HTTP coverage are in src/server.js and test/server-listing.test.js (TC_1, TC_4). (W1/S1)

### R-2: Pagination
Basis: user request 2026-11-01. With page or size present, filter first then return JSON object page, size, total, pages and items. Page defaults to 1, size defaults to 10, page is 1-based, page count rounds up and equals zero for no matches, and beyond-last items are empty. Confirm by HTTP tests covering defaults, first, middle and partial pages, empty and out-of-range results and filtered totals.
Implemented in src/server.js and verified over HTTP by TC_2 in test/server-listing.test.js. (W1/S2)

### R-3: Validation
Basis: user request 2026-11-01. Page must be a whole number >=1; size must be a whole number in 1..100. Empty and invalid values return status 400 and a JSON error describing the parameter. Confirm with HTTP boundary and invalid-input tests.
Validation uses decimal digits and is covered by TC_3 in test/server-listing.test.js. (W1/S2)

### R-4: Compatibility and verification
Basis: user request 2026-11-01. Existing behavior, including GET /users/:id, PORT and npm start, and existing tests remains intact; add node:test cases under test/ run by npm test. Confirm full suite and existing HTTP tests. Store remains fixed process-local state, accessible to existing HTTP clients and removed on process exit; no new state, logging, identity, caching or async process is introduced.

## Non-functional requirements
No new dependencies; existing Node >=20 and CommonJS conventions apply. Confirm package.json and npm test. No UI or numeric performance target was requested; no new external service or persistence is needed.

## Retired
None.
