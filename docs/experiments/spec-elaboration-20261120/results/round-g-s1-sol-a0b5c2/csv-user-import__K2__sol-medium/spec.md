# User directory specification

## Scope

The user directory provides an HTTP interface. Current-system sources are README.md, src/server.js, src/users.js and the baseline tests at 3558d4c. The import is defined by the 2026-11-21 request “Let admins upload a CSV to bulk-create users.” The detailed interface and limits are project defaults derived during definition. Verification is due on the local HTTP candidate before source return and in the returned tree.

## Requirements

### R-1 Admin bulk creation

- CSV-1: An administrator can submit a UTF-8 CSV file to POST /users/import using Content-Type text/csv. It has one header record containing exactly name and email in either order. Accept LF and CRLF, an optional UTF-8 BOM and final newline, double-quoted fields, escaped double quotes and quoted line breaks. Trim leading and trailing whitespace from values. Return HTTP 201 and JSON with created count and users in CSV order. Each user has a new numeric ID, name and email. A loopback HTTP test uploads a file and confirms the full response and independent reads.
- CSV-2: Require an admin bearer credential. Missing or invalid credentials, including a server with no credential configured, receive HTTP 401 and cause no store write. An HTTP test compares the directory before and after denied attempts. The existing project has no individual admin identity service. The configured credential represents the admin actor and stays out of responses and the directory.

### R-2 Validation and atomicity

- CSV-3: Return HTTP 415 for a non-CSV media type. Return HTTP 400 for invalid UTF-8, a missing or invalid header, malformed quoting, missing data, extra columns, empty names or emails without non-whitespace local and domain parts separated by a single @ and with a dotted domain. A failed record response includes its starting line when identifiable. Compare full directory contents before and after rejection.
- CSV-4: Return HTTP 409 for an email already present or repeated within the file, compared case-insensitively. No failed upload creates any user. Two concurrent requests for the same email can create at most one user. Verify HTTP outcomes and a full or targeted read-back.
- CSV-5: Return HTTP 413 above 1 MiB or 1,000 data records, leaving the directory unchanged. Verify over-limit CSV uploads over HTTP.

### R-3 User read compatibility

- CSV-6: Preserve public GET /users and GET /users/:id behavior, ordered numeric IDs, JSON records and missing-ID 404. Newly imported records become visible through both reads and share the existing in-process lifetime. The process owns all records and drops new records on restart. There is no secondary store, index to invalidate, or background processor. Use existing read tests and independent HTTP read-back after import.

## Non-functional requirements

CSV-2 covers access control and keeps the credential out of consumer data. The service does not log uploaded content. CSV-4 covers atomicity and concurrent writes. CSV-5 bounds resource use for the small in-memory service using implementation defaults, with no timing SLA. CSV-6 covers compatibility. The repository supplies an HTTP-only consumer surface and has no graphical or terminal UI, remote target or persistence requirement.

## Verification

Start with a fresh process and the three seeds. A valid file containing `name,email\nKatherine Johnson,katherine@example.com\n` with valid admin credentials will yield one record with ID 4, which the unchanged ID lookup can then find. Repeat the same file and expect HTTP 409 and four directory records. This sequence follows the initial seed IDs, create and duplicate rules and is planned for candidate HTTP verification.

## Retired

None.
