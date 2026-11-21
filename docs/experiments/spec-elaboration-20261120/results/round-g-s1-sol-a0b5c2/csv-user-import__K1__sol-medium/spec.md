# User service specification

## Requirements

### R-1 Existing user reads

Basis: README.md and src/server.js at 3558d4c. `GET /users` returns users in ascending ID order. `GET /users/:id` returns the matching normal user record or 404. Existing unauthenticated reads and the records' `id`, `name`, and `email` shape carry forward. Confirm through loopback including newly created users.

### R-2 Admin CSV import

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). Acceptance is observable in a fresh local HTTP server. The service adds a synchronous file upload flow to the existing process-local user store.

- **Authorization.** The operator configures a nonempty `USER_IMPORT_ADMIN_TOKEN`. The upload endpoint accepts its bearer credential. Missing or incorrect credentials, and requests to an unconfigured importer, return 401 without parsing or changing user state. Confirm with loopback requests and an unchanged list.
- **Input.** `POST /users/import` takes raw UTF-8 bytes with `Content-Type: text/csv`, optionally with a content-type parameter, and the header `name,email` in that order. A UTF-8 BOM, LF or CRLF line endings, doubled quotes, quoted commas and quoted newlines are supported. Blank physical records may be ignored. Empty, header-only, malformed CSV, invalid UTF-8, incorrect headers, and rows with other column counts return 400. Other media types return 415. Confirm with valid and invalid loopback uploads.
- **Creation.** A valid upload has at least one data record. Trim both fields. Require a nonempty name and an email with nonempty local and domain parts, one at-sign, no whitespace and a dot in the domain. Email uniqueness is case-insensitive against existing and incoming rows. Allocate new sequential numeric IDs in file order, preserve email spelling, and return 201 with `{ "created": [ ...user records ] }`. Verify returned rows and both read routes.
- **Failures and retry.** Invalid or duplicate rows return 400 with the one-based starting line of the offending record when available, plus a brief reason. Never echo rejected field values or credentials. The entire batch may be corrected and retried. After a successful upload, resubmission is rejected as duplicate. Confirm that a failed batch with a valid prefix leaves the list and the next ID unchanged. Concurrent requests serialize their final duplicate check and append against the same in-process store, so at most one overlapping batch commits.
- **Lifecycle.** A complete checked request commits normal user records into the existing array, visible to existing readers. The original file and bearer credential are absent from responses and user records. An interrupted upload before a complete body has no effect. Process restart restores seed data. Account invitations, persistent storage, revocation lists, and browser UI fall outside the existing service scope.

### R-3 Resource limits

An upload can contain at most 1,048,576 body bytes and 1,000 data records. Excess returns 413 with no user changes. Verify over HTTP with a body just over the byte limit and a CSV with 1,001 rows. Body bytes must be counted for streaming requests as well as declared lengths.

## Behavior model

| Flow | Preconditions and ordered interaction | Consumer result |
| --- | --- | --- |
| F-1, authorized creation (R-1, R-2) | Start with seed IDs 1–3 and a configured token. POST `name,email\n"River, Lee",river@example.org\nSam,sam@example.org\n` with its bearer credential. T-1 validates then appends. GET /users/4 and GET /users. | 201, River at ID 4 and Sam at ID 5, both in the list. |
| F-2, failed upload (R-2, R-3) | Fresh seeded process. Missing bearer fails before reading CSV. Authorized `name,email\nSam,sam@example.org\nDuplicate,ADA@example.com\n` reaches T-2. Recheck list, then submit only Sam with the same authorized contract. | 401, then 400 at line 3; list stays at three. Corrected file yields ID 4. |
| F-3, competing uploads (R-2) | In a fresh process, two authorized POST requests each contain `name,email\nSam,sam@example.org\n`. Either can reach T-1 first; T-2 checks the updated store for the other request. | Exactly one 201, one 400, and one new record. |

## State and transitions

The process owns the shared user array and keeps seed IDs and unique normalized email keys. The HTTP request owns temporary bytes and parsed rows until response or disconnect. The operator owns the configured token. Customers use existing reads to see normal stored records.

| Transition | Guard and operation | State, fallback and verification |
| --- | --- | --- |
| T-1 (R-2, F-1/F-3) | Authorized request with complete, valid, bounded CSV; check existing and batch emails synchronously and append once. | One atomic in-process append. F-1 reads exact values; F-3 reads one copy. Successful retry hits T-2. |
| T-2 (R-2/R-3, F-2/F-3) | Authorization, body, schema, row validation, uniqueness or size failure; or stream cancellation before completion. | Users and next ID are unchanged. Reject with specified status when connection is open. Correct the request and retry. F-2 compares actual lists and ID; F-3 checks the race. |

## Non-functional requirements

Use the R-3 limits to bound work and buffering. Verify fail-closed admin access and sanitized row errors under R-2. The native HTTP service has no rendered interface, background processing, database, or hosted performance criterion. Runtime support remains Node.js >=20 per package.json.
