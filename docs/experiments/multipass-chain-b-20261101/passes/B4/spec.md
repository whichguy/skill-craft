# User and team API specification

## Requirements

### R-1: Filtered listing
Basis: user request 2026-11-01. GET /users returns an id-ordered JSON array when neither pagination parameter is present. A name query filters by literal case-insensitive substring; an empty value matches all, and unrelated parameters are ignored. Confirm by HTTP node:test cases for absent, empty, mixed-case, special-character and no-match queries. Preserve existing store and GET /users/:id behavior.
Implementation and HTTP coverage are in src/server.js and test/server-listing.test.js (TC_1, TC_4). (W1/S1)

### R-2: Pagination
Basis: user request 2026-11-01. With page or size present, filter first then return JSON object page, size, total, pages and items. Page defaults to 1, size defaults to the valid PAGE_SIZE environment variable, or 25 when it is unset or invalid (non-decimal, zero, or above 50), page is 1-based, page count rounds up and equals zero for no matches, and beyond-last items are empty. Confirm by HTTP tests covering defaults, first, middle and partial pages, empty and out-of-range results and filtered totals.
An explicit valid size overrides PAGE_SIZE; confirm for both endpoints by HTTP node:test. Configured default, fallback and page slicing are verified for both endpoints by HTTP node:test; neither parameter still returns an array. State remains read-only process-local, accessible to HTTP clients and removed on exit; no cache, async event, identity or new storage. Implemented in src/server.js and verified over HTTP by TC_2 in test/server-listing.test.js. (W1/S2)

Implemented and verified for both routes by TC_11 in test/server-page-size.test.js. (W1/S1)

### R-3: Validation
Basis: user request 2026-11-01. Page must be a whole number >=1; size must be a whole number in 1..50. Empty and invalid values return status 400 and a JSON error describing the parameter. Confirm with HTTP boundary and invalid-input tests.
Confirm both endpoints accept size 50 and reject 51 with HTTP 400 and the existing JSON error form; verify the configured and fallback defaults, explicit override, and actual page slicing via node:test. Validation uses decimal digits and is covered by TC_3 in test/server-listing.test.js. (W1/S2)

Implemented and verified for both routes by TC_12 in test/server-page-size.test.js. (W1/S1)

### R-4: Compatibility and verification
Basis: user request 2026-11-01. Existing behavior, including GET /users/:id, PORT and npm start, and existing tests remains intact; add node:test cases under test/ run by npm test. Confirm full suite and existing HTTP tests. Store remains fixed process-local state, accessible to existing HTTP clients and removed on process exit; no new state, logging, identity, caching or async process is introduced.

### R-5: User roles and role filtering
Basis: user request 2026-11-01. Fixed records have role values: Ada Lovelace admin, Grace Hopper member, Alan Turing viewer. GET /users/:id and all GET /users array and page item responses expose each role; confirm by HTTP node:test on each id, array and page. GET /users?role=admin, member or viewer retains only exact matches, combined with the existing name filter before pagination; confirm matching and nonmatching combinations and filtered totals over HTTP. Every supplied role must be one of those exact literals, including repeated parameters; invalid, empty or differently cased values return HTTP 400 with a JSON error explaining role; confirm HTTP tests. Repeated valid conflicting filters yield no users. With no role filter preserve all previous listing behavior. Records remain fixed process-local state accessible to existing HTTP clients, removed at process exit; no mutation, new persistence, cache, async processing, identity or event stream is introduced. Implementation is in src/users.js and src/server.js; HTTP regression tests are in test/server-roles.test.js.

Role projection is implemented in src/users.js and covered by TC_5 in test/server-roles.test.js. (W1/S1)

Role filter validation and conjunction are implemented in src/server.js and verified by TC_6 and TC_7 in test/server-roles.test.js. (W1/S2)

### R-6: Team data and detail
Basis: user request 2026-11-01. Fixed records are {id:1,name:"Analytical Engine",members:[1]}, {id:2,name:"Compilers",members:[2]}, {id:3,name:"Computing Machinery",members:[3]}, {id:4,name:"Cryptanalysis",members:[3]}, {id:5,name:"Data Systems",members:[1,2]}. GET /teams/:id returns the corresponding JSON record; absent or malformed ids return HTTP 404 and {"error":"not found"} as users do. Confirm each record and missing/malformed ID via HTTP node:test. State is static and process-local, readable by existing HTTP clients, with no writes, concurrency, persistence, secrets, async events or cache. Preserve user data and detail behavior.

Detail records and 404 behavior are implemented in src/teams.js and src/server.js, verified by TC_8 in test/server-teams.test.js. (W1/S1)

### R-7: Team listing
Basis: user request 2026-11-01 and R-1 through R-3. GET /teams returns the five records in ID order as an array, filtered by case-insensitive literal name substring. Presence of page or size returns the same metadata, defaults, bounds, errors and huge-page representation as /users, after filtering. Empty and unrelated parameters follow /users behavior. Confirm HTTP node:test covering list, filtering, no matches, pagination, defaults, invalid values, boundaries and exact large page JSON. Role filtering is specific to users; unrelated team parameters are ignored. Preserve existing routes and tests; confirm npm test.

Listing is implemented in src/server.js and verified by TC_9 and TC_10 in test/server-teams.test.js. (W1/S2)

## Non-functional requirements
No new dependencies; existing Node >=20 and CommonJS conventions apply. Confirm package.json and npm test. No UI or numeric performance target was requested; no new external service or persistence is needed.

## Retired
The former R-2 default size of 10 and R-3 maximum of 100 were superseded by the 2026-11-01 pagination request; all other clauses remain active.
