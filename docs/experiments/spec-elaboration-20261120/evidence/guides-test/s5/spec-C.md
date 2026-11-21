# Node user service specification

## Requirements

### R-1 Administrator CSV user creation

Basis: “Let admins upload a CSV to bulk-create users” (2026-11-21). Existing contracts are observed in src/server.js and src/users.js. The CSV interface, credential model, validation and atomicity are recorded defaults.

- A caller with the configured administrator bearer credential can POST a UTF-8 file as `text/csv` to `/users/import`. Accept a `name,email` header, an optional UTF-8 BOM, CRLF or LF, and CSV quoted fields with escaped quotes. Trim field edges and skip blank lines. Confirm through loopback HTTP using a real CSV body with quoted delimiters, BOM and CRLF.
- A successful upload returns HTTP 201 with `{"created":2}` for two valid rows. Each user has a unique incremental numeric ID and appears in both existing GET routes. Confirm by comparing pre-upload list and post-upload records.
- Missing or invalid authorization returns 401 with a Bearer challenge. When no credential is configured, nobody can import. Confirm using requests with no, incorrect and unconfigured credentials and identical GET snapshots.
- Incorrect media type returns 415. Malformed UTF-8/CSV, header mismatch, no data, empty names, invalid emails and incorrect field counts return 400 with an actionable error, including the record number where applicable. Confirm via HTTP while verifying the batch has made no writes.
- Email duplicates within an upload or against the store, ignoring case, return 409. Validate the entire batch before adding any users. Concurrent uploads sharing an email can create it once only. Confirm through GET and concurrent HTTP imports.
- Requests larger than 1 MiB or containing more than 1,000 records return 413 and leave no created users. Confirm via HTTP.

The store owns user records for the server process lifetime. Authorization belongs to configured server operators. Imported records have the same read visibility as existing records. Request data is transient and errors do not echo personal fields or secrets. Creation is synchronous after validation. Invitations, passwords, roles and durable storage are outside this feature. Automated loopback execution and local return remain due.

### R-2 Existing user reads

Basis: src/server.js and test/server.test.js at ec1f94c. GET /users lists users in ID order. GET /users/1 returns Ada Lovelace on a fresh process and a missing numeric ID returns 404. Confirm through the existing and added HTTP tests. No external dependency is involved.

## Non-functional requirements

Authentication fails closed and runs before parsing. File limits apply to streamed bytes as well as declared lengths. Errors omit personal field values. No UI is involved because the existing consumer is the HTTP API.
