# User service specification

## Requirements

### R-1 Read users

Basis: README.md, src/server.js and src/users.js at ec1f94c. Preserve GET /users (200 list in ID order) and GET /users/:id (200 user or 404). Existing users and response shape stay intact. Observe through HTTP with npm test.

### R-2 Admin CSV upload

Basis: “Let admins upload a CSV to bulk-create users” (2026-11-21), applied to the HTTP-only, process-memory service at ec1f94c. Acceptance is observed by HTTP tests on fresh Node processes.

- An admin presents the configured bearer token and POSTs raw UTF-8 text/csv to /users/import. Missing or invalid credentials return 401 and leave the account list unchanged. With no configured token, the import is disabled and rejects all credentials. HTTP tests compare the store before and after denials.
- The header contains exactly name and email in either order. Each record supplies both. Accept standard CSV quotes, escaped quotes, embedded newlines inside quotes, LF or CRLF, and an optional UTF-8 BOM. Trim each name and email and require a nonempty name and an email with an at sign and a dotted domain. Malformed CSV, invalid UTF-8, missing rows, or invalid field values return 400. Errors identify the logical record where applicable without echoing row data. A non-CSV media type returns 415. Confirm with HTTP uploads.
- A valid upload returns 201 with a JSON object containing the created count and records in file order, with server-assigned IDs. Read back by list and ID. A duplicate email, case-insensitively within the file or in the existing store, returns 409. Any failure leaves the store and next available ID unchanged. Test a valid row preceding a conflict, and two overlapping uploads racing for one address.
- The store owns user records and serves them through the existing GET routes until process exit. Upload bodies and tokens are not logged. No external services or users' sign-in credentials are involved. Verify the existing public read projection and restart lifetime through the local runtime.

## Non-functional requirements

The upload accepts at most 1 MiB and 1,000 data records. A bigger body or batch returns 413 with no new accounts, including when the client streams without a content length. Failure messages contain no input field values or credentials. The API has no graphical UI.
