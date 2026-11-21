# User API specification

## Requirements

### R-1 Admin CSV import

- Add, based on “Let admins upload a CSV to bulk-create users” (2026-11-21). In the local HTTP API, accept POST /admin/users/import from an operator authorized with an Authorization Bearer value matching ADMIN_TOKEN. Missing or invalid credentials and missing token configuration return 401 with a bearer challenge before processing data. Confirm with loopback requests and unchanged GET readback.
- Accept a raw UTF-8 text/csv body, optionally with a UTF-8 BOM, with exactly the name and email columns in either order. Accept LF or CRLF, optional trailing newline, comma and newline inside quoted fields, and doubled quotes. Trim name and email; require nonempty name and a conventional non-whitespace local@domain.tld address. Confirm with an actual file-shaped HTTP payload.
- A valid upload creates each row in input order with a new ascending numeric ID. Respond 201 with JSON containing created count and users. Confirm that list and ID GET endpoints observe the new users in the same process. Columns cannot supply privileges or IDs.
- Return 415 for the wrong media type, 413 above 1 MiB or 1,000 data rows, 400 for invalid UTF-8, syntax, header or rows, and 409 for an email conflict with the store or within the batch (case-insensitive). Error text identifies the relevant record when feasible without echoing submitted values. Every rejection leaves state unchanged. Confirm with loopback failures and GET readback. An empty file or header-only file is invalid.

### R-2 Existing user reads

- Preserve the public GET /users array and GET /users/:id object or 404 established by src/server.js at ec1f94c. The store starts with the same three seeds and lasts for the process. Confirm the existing suite and imported-record readback. No change to read authorization or lifetime.

## Non-functional requirements

R-1 resource bounds govern parsing and storage preparation for one request. Authentication precedes body handling. The user list receives the batch synchronously, so simultaneous requests with colliding emails cannot both commit. The server emits a sanitized HTTP result and stores names and emails in the same process memory exposed by the existing GET surface. The upload body is transient. Additional persistence, hosted availability targets and graphical accessibility do not apply to the local API scope. Verification is due at the HTTP boundary.

## Behavior model

### Flows

F-1 (R-1, R-2): An operator configures the process credential. An administrator sends a CSV to POST /admin/users/import. The HTTP layer authenticates, checks content type and size, reads UTF-8, and validates rows. The store checks all identities and applies T-1. The response reports 201; a subsequent GET reads the result. A failed check terminates with the matching status and T-2. An interrupted request before body completion never commits.

### State and transitions

| ID | Before and guard | After | Observation |
| --- | --- | --- | --- |
| T-1 | User store seeded or populated; caller authorized; all rows valid and unique | Same existing users plus the new rows, with consecutive IDs | 201, list and ID GET |
| T-2 | Any auth, transport, validation, size or identity failure | Store and next ID unchanged; administrator can correct and retry | Error status and unchanged GET |

### Verification cases

- R-1/R-2 valid example from a fresh process: header name,email, rows ""Doe, Jane",jane@example.com" and "Kai,kai@example.com". Following F-1, T-1 creates IDs 4 and 5 and GET /users/5 returns Kai. Derived from three seeds and ordered ID assignment; HTTP execution is pending.
- R-1 failure example: a valid Jane row followed by ADA@example.com fails at the existing Ada email under T-2. Readback has three seeds and a subsequent valid Jane-only upload gets ID 4. Also exercise unauthorized and unconfigured requests, malformed CSV and invalid UTF-8, wrong media type and both bounds.

## Retired

None.
