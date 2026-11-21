# User service specification

## Requirements

### R-1 Administrator CSV upload

Basis: “Let admins upload a CSV to bulk-create users” (2026-11-21). The established user-management surface is the HTTP API in src/server.js. Administrator identity and CSV details are product defaults because the baseline has no auth, write or upload UI.

- A1 (C1, C2): A configured administrator can POST a file body to /users/import as text/csv with a Bearer token. Without matching credentials return 401 with a Bearer challenge. If import is unconfigured return 503. Reject before parsing or writing. Confirm through loopback HTTP and GET read-back.
- A2 (C1, C3): Accept UTF-8 with an optional BOM, exactly the name and email header in either order, and at least one data record. Support LF and CRLF, quoted commas, quoted newlines, doubled quotes and optional final newline. Reject wrong media type with 415 and malformed encoding, syntax, headers or rows with 400. Report the 1-based CSV record number when the error belongs to a record. Confirm HTTP status, response and that rejected input creates nothing.
- A3 (C4): Accept at most 1 MiB on the wire and 1,000 user records per upload. Return 413 when either limit is exceeded, including a streamed body. Confirm via loopback with inputs at and above each limit.

### R-2 Atomic creation and read-back

Basis: the bulk-create outcome in the 2026-11-21 request. src/users.js defines numeric IDs, name and email, and process-lifetime state. Existing GET routes retain their response schema and visibility.

- A1 (C1): For a valid batch, return 201 with a created count and new user records in input order. Trim names and emails. Require a nonempty name and an email with nonempty local and dotted domain parts, without whitespace. Assign sequential IDs and expose the records through GET /users and GET /users/:id. Check response and both read endpoints.
- A2 (C3, C5): Reject invalid records with 400 and an email conflict with 409. Compare emails case-insensitively against the stored users and earlier rows in the upload. A rejected batch changes no users and consumes no IDs. Concurrent imports with an overlapping email permit one success and one conflict. Retrying a successful upload returns a conflict and creates nothing else. Check both response statuses, final users and generated IDs.
- A3 (C6): Existing reads still return seeded users and a missing ID still returns 404. A new process starts from the seed; there is no user database or upload file. Check existing suite and restart the app locally as a release check.

### Behavior model

F-1 (R-1, R-2): An HTTP client with the configured secret sends the CSV. The server checks credential and media type, collects a bounded body, decodes and parses it, then validates against the current store and synchronously appends all records. The caller receives 201 after the write. Public GET retains the baseline visibility of the shared store.

| Transition | Trigger and guard | Result and recovery | Check |
| --- | --- | --- | --- |
| T-1 | F-1 matches credential, format, limits and validations | Store appends whole batch before 201; GET shows same records. | C1 |
| T-2 | F-1 unauthorized, bad MIME, invalid data or limits exceeded | No append; correct configuration, credentials or input and retry. | C2, C3, C4 |
| T-3 | F-1 matches an existing email or overlaps a competing batch | 409; no records from the rejected batch. Inspect existing users before retry. | C5 |
| T-4 | F-1 disconnects before complete request, or process restarts | Incomplete body never commits. A disconnect after commit may hide the response; a replay conflicts. Restart resets the seed. | C5, C6 and review of complete-body guard |

The store owns records in memory. The HTTP request owns ephemeral CSV bytes. Tokens live in runtime configuration and request headers, never in returned user records or logs. No jobs, callbacks, migrations, files or caches need lifecycle changes. Account sign-in, invitations and new data persistence are outside the upload's scope.

### Reference scenario

Start a fresh process with a test-only configured bearer value. POST a body with header name,email and rows Test One,one@example.test and Test Two,two@example.test. The starting IDs are 1–3, so a 201 reports created 2 and records 4 and 5. GET /users/5 returns Test Two. POST again with the same credential and data. The first data record matches ID 4 and yields 409 on record 2. GET /users contains five records. This expected sequence was walked against T-1 and T-3; executable observation is due in work and release.

## Non-functional requirements

- Limit admitted CSV payload and record count per R-1. Check measured bytes, record counts and persisted state over HTTP. This is a resource budget, not a latency SLA.
- Fail closed and emit error reasons and row numbers without CSV values or credentials. Require trusted transport when exposing credentials off loopback. Test missing and incorrect credentials and inspect responses.
- Browser layout, accessibility and availability targets are outside this API-only change.

## Retired

None.
