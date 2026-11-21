# Node-base user service specification

## Requirements

### R-1 Admin CSV upload

- Basis: “Let admins upload a CSV to bulk-create users” (2026-11-21). Adds a write operation to the HTTP surface described in README.md and src/server.js. The baseline exposes no admin identity, so a server-configured bearer credential represents the administrator. Implementation and tests are pending at definition.
- R-1.a POST /users/import accepts a UTF-8 file as the raw request body with media type text/csv, optionally with parameters. An authorized request with a different media type returns 415. Check on loopback HTTP.
- R-1.b Only the configured ADMIN_TOKEN bearer credential authorizes import. Missing, malformed, incorrect, and unconfigured credentials return 401 before CSV processing and leave the user list unchanged. Check with requests bearing valid, invalid and absent credentials and read back the list.
- R-1.c CSV has exactly the name and email headers, either order, followed by one or more records. Accept an optional initial UTF-8 BOM, LF or CRLF line endings, an optional final newline, and quoted fields with embedded commas, line breaks and doubled quotes. Reject invalid UTF-8, malformed CSV, unexpected field counts, invalid headers and missing data with 400. Exercise these cases by posting bytes over loopback.
- R-1.d Requests may contain up to 1,048,576 bytes and 1,000 data rows. An exceeded bound returns 413 before any write. Verify exact limits and overflowing bodies with and without Content-Length.
- R-1.e A successful response is 201 with JSON containing the created count and the created user records in CSV order. Errors return a JSON error message plus a 1-based logical CSV row number where applicable. Error bodies omit original input and credentials. Check response bodies on loopback.

### R-2 User records and atomicity

- Basis: bulk-create request (2026-11-21) and the observed id/name/email model in src/users.js. The process owns and shares the existing in-memory array. Successful records are readable through the existing public GET endpoints and reset when the process exits. No persistence, invitation, user-role assignment or external side effect is in scope. Implementation and tests are pending at definition.
- R-2.a Trim surrounding field whitespace. Require a nonempty name and a practical email with one @, a dotted domain, and no whitespace. Assign server-generated numeric IDs above the existing IDs in CSV order. On a fresh process, importing `name,email\nKatherine Johnson,katherine@example.com\nDorothy Vaughan,dorothy@example.com` returns IDs 4 and 5. Confirm the records in list and detail responses.
- R-2.b Invalid row values return 400. An email already present or repeated within the file, compared case-insensitively, returns 409. Either rejection leaves the store and next ID unchanged. Simultaneous imports containing the same email can create it only once. Check through HTTP with a valid row before the rejected one, a follow-up valid import and two competing requests.
- R-2.c Preserve public GET /users in ID order, GET /users/:id and 404 for unknown IDs and routes, including when import is unconfigured. Check the existing suite and the import integration checks.

## Non-functional requirements

- Security and privacy: R-1.b/e define the credential boundary and diagnostic handling. Authorization is checked on each upload with the server's configured credential and configuration changes take effect when the server is recreated. CSV bytes are held only while processing and are omitted from logs. Accepted name and email values inherit the existing public GET policy. No job or event system exists.
- Capacity and reliability: R-1.d limits per-request work and memory. R-2.b defines write consistency. Synchronous commit and GET read-back are verified on the real local HTTP boundary. No load SLA or persistence guarantee was requested.
- Compatibility and usability: retain Node >=20 and CommonJS with native dependencies only, consistent with package.json and README.md. A browser UI and its visual criteria are inapplicable because this service provides an HTTP API.

## Retired

None.

## Key questions

- K1 Admin uploads to POST /users/import and observes 201 and GET read-back (R-1, R-2).
- K2 Preserve public reads and process lifetime (R-2).
- K3 Raw UTF-8 text/csv with name/email and JSON status/results (R-1).
- K4 Bound bytes and rows, validate structure and values, reject duplicates (R-1, R-2).
- K5 The server owns process-local users and applies batches atomically (R-2).
- K6 Node >=20, no dependencies, ADMIN_TOKEN configuration (R-1, Non-functional requirements).
- K7 HTTP boundary and process-local user store (R-1, R-2).
- K8 npm test runs native loopback and store tests (R-1, R-2).
- K9 Local checkout and local HTTP observation (environment.md).
- K10 Authorization, capacity, privacy and predictable errors (Non-functional requirements).
- K11 Unauthorized or partial creation is disproved through before/after HTTP reads (R-1, R-2).
- K12 CSV is the defined text/csv dialect and admin means possession of the configured bearer credential (R-1).
