# User listing specification

## Requirements

### R-1: Filtering and compatibility
Basis: user request, src/users.js, src/server.js; existing GET /users array and id order remain. GET /users?name= filters by case-insensitive literal substring, including empty matching all; unknown parameters are ignored. Confirm by HTTP tests comparing full ordered records, mixed-case partial text, literal metacharacters, empty and no-match queries. GET /users/:id remains unchanged, confirmed by existing tests. State: process-owned read-only in-memory users remain unchanged, with no identity or new persistence. No filtering failure expected. Pending implementation and checks.

### R-2: Pagination
Basis: user request. With page or size, return JSON object with page, size, total matching count, pages rounded up (zero if none) and ordered items; default page 1 and size 10. Out-of-range pages return empty items. Confirm by HTTP tests for each default, combined filtering, partial last page, no matches, and beyond last page. State remains unchanged; no new recovery or concurrent mutation. Pending implementation and checks.

### R-3: Pagination validation
Basis: user request. Reject empty, non-whole, page below 1 or size outside 1–100 with HTTP 400 JSON error explaining the parameter. Confirm by HTTP tests for invalid strings, fractional, zero, negatives, empty, size 101 and valid boundaries. Default decimal digit syntax; duplicate query parameters use first parsed value. Pending implementation and checks.

### R-4: Existing project behavior
Basis: request, README and package.json. No dependencies; npm start and all existing tests remain functional. Confirm by npm test and server start smoke test. No new state, authorization, external service, async completion, event or recovery path.

## Non-functional requirements
No new performance, availability or quota bound was requested; existing local in-memory operation suffices. No new access policy or logging of personal data is introduced. HTTP responses preserve existing user fields; no new persistent copies are created.

W1 verified R-1 through R-3 via local HTTP and helper tests; existing suite passed for R-4. The npm start process smoke remains due at system-test. Exact decimal page values beyond JavaScript's safe integer range remain valid and return an empty page.

## Retired
None.
