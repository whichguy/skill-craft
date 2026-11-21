# User API specification

## Scope

A dependency-free HTTP API with process-local storage.

## Requirements

### R-1 Administrator CSV import

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). Existing public reads, seed users and ID order are preserved (src/server.js and src/users.js at 7b65835). New behavior is verified at the local HTTP boundary.

- With ADMIN_TOKEN configured, send a matching Authorization bearer token and a UTF-8 text/csv body to POST /users/import. A file containing `name,email\nRobin Example,robin@example.test\nTaylor Example,taylor@example.test\n` on a fresh server returns 201 with a created count of 2 and the new users with IDs 4 and 5. GET /users and GET /users/4 show committed data. Verify using Node HTTP integration tests.
- Missing or incorrect credentials receive 401. An unconfigured import receives 503. Neither changes store state. Verify using independent local servers and GET readback. The server does not include credentials or upload contents in errors or logs.
- The two headers are required once each and may be reordered. UTF-8 BOM, LF and CRLF, quoted delimiters or line breaks, and doubled quotes are accepted. Names and emails must be nonempty after trimming, and emails must have an address-shaped value. Verify valid and malformed examples through HTTP.
- Bad encoding, CSV syntax, header or record data receives 400 with an error and row number where applicable. A repeated email, including case-only variants within the file or already stored, receives 409 with its row number. Incorrect media type receives 415. Oversize requires 413. A rejected batch creates no users and consumes no IDs. Verify failure before a successful retry through HTTP.
- The process owns the store and replaces it with seed data on process restart. A synchronous conflict check and commit resolve concurrent submissions without duplicates. Existing GET visibility applies to created users. The request body is temporary. Verify concurrent upload outcomes and readback in the same server.

## Non-functional requirements

The upload accepts at most 1 MiB and 1,000 data rows as implementation defaults. The service rejects oversized requests with 413 without creating users. Only a configured shared administrator credential grants import access. Graphical accessibility does not apply to the HTTP surface.

## Retired

None.

## Key questions

- K1 Administrator HTTP caller uploads and reads back users (R-1).
- K2 Existing public reads and store lifetime are preserved (R-1).
- K3 POST /users/import accepts raw CSV and returns JSON (R-1).
- K4 Invalid or duplicate records fail the entire batch (R-1).
- K5 The server process owns imported user state (R-1).
- K6 Node.js >=20, built-in modules and ADMIN_TOKEN (Scope, R-1).
- K7 The existing HTTP and store entry points are the integration seams (R-1).
- K8 Local HTTP tests exercise write and readback (R-1).
- K9 Source checkout and local HTTP verification (Scope).
- K10 Authorization and request bounds (Non-functional requirements).
- K11 Partial writes and duplicate conflicts (R-1).
- K12 An admin is an operator holding the configured bearer credential (R-1).
