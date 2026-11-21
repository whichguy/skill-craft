# User service specification

## Scope

Node HTTP API for a single process. The actor for imports is a caller presenting the operator-configured administrator credential.

## Requirements

### R-1 — Upload and create users

Basis: request for CSV bulk creation and the existing user shape in src/users.js.

- POST /users/import accepts a raw UTF-8 text/csv body with name and email headers (either order, each once), optional BOM, LF or CRLF, quoted fields, comma escaping by quoting, and doubled quotes. Ignore blank records. Require at least one user row. Trim name and email, require a nonempty name and an email of the form local@domain.tld without whitespace, and preserve email casing as supplied.
- HTTP case T-1 starts from the three seed users with an administrator secret configured. Send UTF-8 BOM followed by `name,email\r\n"Ng, Jo",jo@example.com\r\n"Dee ""D"" Ray",dee@example.com\r\n` (each `\r\n` denotes CRLF). The stored names are `Ng, Jo` and `Dee "D" Ray`. Expect 201 and {"created":2}. GET /users/4 and /users/5 show the uploaded values and server-assigned IDs. T-2 rejects a malformed file or invalid row with 400 and a useful error, including its CSV record number when applicable. T-3 checks 415 for an unsupported content type.

### R-2 — Restrict imports to administrators

Basis: request specifies admins. The baseline has no identity system.

- The operator configures ADMIN_TOKEN when starting the server. A matching Authorization Bearer credential is required. Missing credential, wrong credential and absent configured secret yield 401 with a Bearer challenge and zero writes. HTTP case T-4 verifies each path. Credentials are kept in the server configuration and never included in responses.

### R-3 — Keep imports atomic and resolve conflicts

Basis: default behavior for bulk creation without an existing mutation contract.

- Reject duplicate emails case-insensitively within a file or against current users with 409 and a record number. Failed files create no users and consume no IDs. T-2 and T-5 compare list snapshots across invalid or conflicting batches, retry a completed batch, and issue concurrent conflicting imports, expecting one winner.
- Records are held in the existing process-local store, visible from the established GET routes and reset with a process restart. No data is written to disk. A synchronous validation and insertion boundary resolves concurrent requests.

### R-4 — Preserve existing reads and bound upload cost

Basis: existing GET contract and default safety bounds for the new write surface.

- Existing unauthenticated GET routes preserve their response shapes and 404 behavior. Run the existing suite and assert committed rows via T-1.
- Accept at most 1 MiB of body bytes and 1,000 data rows. T-6 checks the byte and row limits return 413 and leave the list untouched. Malformed UTF-8 returns 400 in T-2. Responses report errors without echoing raw input.

## Non-functional requirements

Verify authorization, bounded intake, atomicity and read compatibility at the real local HTTP boundary. The limits bound a single upload on the dependency-free in-memory service. CSV payloads are held only for request processing. The API has no graphical interface or remote promotion target.

## Retired

None.
