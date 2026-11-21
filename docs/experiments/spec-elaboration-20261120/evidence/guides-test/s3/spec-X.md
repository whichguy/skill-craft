# User service

## Requirements

### R-1 Admin-only CSV upload

Added for “Let admins upload a CSV to bulk-create users” (2026-11-21). The baseline has no write endpoint or role model (src/server.js and src/users.js at ec1f94c). A configured server-side bearer token identifies an admin for this operation.

- **C1** POST /users/import with a matching Authorization bearer token and a UTF-8 text/csv body creates users and returns 201 JSON with a created count. Missing or wrong authorization returns 401. If ADMIN_TOKEN is unset or empty, the route returns 503. Authorization precedes media and body handling. Confirm at the local HTTP endpoint and observe GET /users.
- **C2** Accept name and email headers in either order, with case and surrounding whitespace normalized. CSV supports CRLF and LF, a UTF-8 BOM, escaped quotes and quoted commas/newlines. Data fields are trimmed. Bad headers, malformed CSV or UTF-8, empty imports, a blank name or an email without one @ and a dotted domain return 400. Unsupported media returns 415. Confirm at the HTTP endpoint with literal fixture bodies and verify store state after rejection.
- **C3** Accept up to and including 256 KiB and 1,000 data records. Exceeding either returns 413. Confirm through HTTP with exact and over-limit inputs, including streamed input without a declared length.

### R-2 Atomic bulk creation

Added for the same request. Augments the existing process-local store (src/users.js at ec1f94c).

- **C4** A successful batch appends users with unique increasing numeric IDs in file order. Existing and within-file email comparisons are case-insensitive. A conflict returns 409. No failure writes a partial batch. An accepted batch is readable on GET /users and GET /users/:id. Check a successful two-row import, replay, an in-file duplicate after a valid row, an invalid later row, and two overlapping imports. Row errors identify logical CSV record numbers, counting the header as 1, when applicable. Error responses omit raw row data and credentials.
- **C5** Preserve public GET list and ID lookup, seeded records, response shapes and 404 for unknown IDs. Imported users stay in the current service process and disappear on restart. Confirm against the read suite and an isolated restarted process.

## Non-functional requirements

The per-request limits in C3 bound memory use. C1 limits writes to the operator and C4 protects state consistency through retries and concurrent uploads. Tests use synthetic users. UI accessibility is inapplicable to this HTTP-only service. No throughput or hosted availability commitment is defined.

## Behavior model

- F-1 (R-1, R-2): operator sends a completed file, server authorizes, checks media and bounds, decodes and validates records, commits synchronously, and responds. Client observes changes using the existing read routes.
- T-1 (F-1, C1/C2/C3): incomplete or rejected request leaves the user store as observed before this request. Caller can correct and resend. Payload bytes are transient.
- T-2 (F-1, C4): authorized, bounded, valid unique rows append together after a synchronous check against the current process store. An overlapping conflict or replay leaves the existing set intact. On a lost response, use readback before retrying.
- T-3 (C5): service restart restores seeded records. Configured authorization is read at server creation. There is no asynchronous completion or derived state.

Worked case: on fresh seeded state, upload `name,email` followed by `"Lee, Sam",sam@example.test` and `Jo,jo@example.test` with the configured bearer token. The records are new, so the count is 2 and lookup of ID 4 returns Lee, Sam. Replaying hits the existing email conflict at record 2 and leaves five records. This is a spec walk. Test execution is pending.

## Retired

None.
