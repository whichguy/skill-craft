# Node Base User Service

## Requirements

### R-1 Admin CSV upload

**Basis.** “Let admins upload a CSV to bulk-create users” (2026-11-21). This adds a write route to the read-only HTTP surface in src/server.js at 7b65835. The repository defines neither a web UI nor an admin account system. Operator-configured bearer access is a delivery default.

- **R-1a Access.** An admin POSTs a CSV file as the raw request body to `/users/import` with `Authorization: Bearer <ADMIN_TOKEN>`. With absent, invalid or unconfigured credentials, the endpoint returns 401 and leaves the store unchanged. Verify correct, incorrect, missing and disabled credentials over HTTP.
- **R-1b Upload.** The request media type is `text/csv` with an optional UTF-8 charset. An unsupported type or charset returns 415. The input is UTF-8, optionally starts with a BOM, and has a header with exactly one `name` and one `email` in either order. It accepts LF and CRLF separators, quoted values, embedded commas and line breaks in quotes, and doubled quotes. An optional final newline is accepted. Empty files, header-only files, invalid UTF-8, broken quoting, interior empty records and wrong field counts return 400. Verify via table-driven HTTP uploads.

### R-2 Validate and create the batch

**Basis.** The 2026-11-21 request requires creating multiple users. The existing record shape at 7b65835 is `{ id, name, email }` (src/users.js). Required fields, case-insensitive email uniqueness and atomicity are defaults. Imported users cannot assign their own IDs or privileges.

- **R-2a Success.** The server trims name and email, requires a nonempty name and an email with one `@`, no whitespace and a dotted domain. With every row valid, it creates all users in file order with consecutive, server-assigned IDs and returns 201 and `{"created":n}`. In a fresh process, uploading `name,email\n"Nora, Jr.",nora@example.com\nSam,sam@example.com\n` yields two records with IDs 4 and 5. Observe the count over POST and exact records via GET. Fields with blank names or invalid email return 400.
- **R-2b Atomic failure and retry.** An email matching any existing user or earlier row, regardless of case, returns 409. All invalid batches leave users and the next ID unchanged. When a data record is identifiable, the JSON error includes its one-based CSV record number, counting the header as one. A quoted line break does not increment that number. Retrying a previously successful file returns 409 and adds no duplicates. Concurrent requests containing the same new email produce one 201 and one 409. Verify through POST results and GET snapshots before and after failure.
- **R-2c Lifetime.** All requests served in one process observe the same store. A fresh process again contains only the initial users. The upload is read for validation and discarded after the request. Errors omit source field values and credentials. Verify fresh-process state and representative validation/authentication errors.

### R-3 Preserve user reads

**Basis.** Preserve the observed GET behavior in src/server.js and src/users.js at 7b65835. Imported records have the same visibility and fields as existing records.

- **R-3a Compatibility.** Public `GET /users` returns the initial users plus imported users in ID order. Public `GET /users/:id` returns the matching record or the existing 404 response. Unmatched routes retain their 404 response. Verify over the same HTTP listener before and after an import.

## Non-functional requirements

- **NFR-1, R-1 and R-2, bounded work.** For local HTTP uploads, the configured defaults are 1 MiB and 1,000 data records per request. An upload above either bound returns 413 before any user mutation, including when the sender omits Content-Length. Verify exact-limit and over-limit cases over HTTP. No service latency or throughput promise applies.
- **NFR-2, R-1 and R-2, credential and data handling.** Check the credential before parsing input. Keep credentials and rejected raw values out of logs and response bodies. Verify precedence with invalid credentials and malformed data, and inspect server output and error bodies. Existing public reads expose accepted user records by design.
- **NFR-3, R-1 through R-3, runtime compatibility.** Keep the declared Node 20+ CommonJS and dependency-free runtime. Run the existing suite and HTTP cases. No visual interface, hosted availability target, or persistent migration applies.

## Retired

None. Implementation and consumer checks are pending.
