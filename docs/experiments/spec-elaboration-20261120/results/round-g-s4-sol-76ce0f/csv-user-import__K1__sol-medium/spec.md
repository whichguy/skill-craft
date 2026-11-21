# User service specification

## Scope

The service exposes user records over HTTP. The upload adds a write path to the existing process-local user store.

## Requirements

### R-1 Admin CSV upload

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). Existing API and data model: src/server.js and src/users.js at ec1f94c.

- A configured administrator can POST UTF-8 `text/csv` to `/users/import` using the server's bearer credential. A new server without a configured credential, or a request with a missing or incorrect credential, returns 401 and creates nothing. Check through real HTTP.
- CSV requires one `name` and one `email` header in either order, and at least one data row. Accept quoted commas, escaped quotes, quoted multiline fields, LF or CRLF and an optional UTF-8 BOM. Trim surrounding whitespace in user fields. Check the imported values via JSON and GET read-back.
- Create one user for each valid row, in file order. Assign unused IDs, return 201 with the created records and make them visible through existing GET endpoints. A fresh server with three seeded records and a two-row file for `Ivy,ivy@example.com` and `Noah,noah@example.com` returns IDs 4 and 5 and lists five records. This follows from the seeded maximum ID of 3 and sequential assignment. Repeat as a loopback HTTP test.
- Reject invalid UTF-8, missing or invalid headers, malformed quoting, missing fields, blank names or malformed emails with 400. Reject a duplicate email (already present or repeated in the batch, case-insensitive) with 409. Return 415 for an unsupported media type. Return 413 for bodies over 1 MiB. Confirm with HTTP and verify that each rejected batch leaves the original users intact.
- Write all records together after validation, including a final duplicate check against current state. Concurrent uploads sharing an email can create it only once. The owner is the service process; read visibility and reset on restart follow existing store behavior. Keep upload contents and bearer credentials out of errors and logs.

## Non-functional requirements

Use a bounded body and immediate synchronous commit after validation. Test unauthorized requests, chunked oversized requests and overlapping writes against the live loopback service. Browser UI, graphical accessibility and external persistence are outside the existing API's scope.

## Retired

None.
