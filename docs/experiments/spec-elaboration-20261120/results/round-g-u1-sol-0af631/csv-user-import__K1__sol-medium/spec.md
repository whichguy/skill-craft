# Node-base requirements

## Scope

The product exposes a local Node HTTP user API. The request “Let admins upload a CSV to bulk-create users” (2026-11-21) adds batch creation to the existing read API.

## Requirements

### R-1 Admins can upload a CSV and read back the new users

Basis: 2026-11-21 request and the user fields in baseline src/users.js at 7b65835. The local API and import decisions below are defaults for that request.

- An administrator submits a raw UTF-8 CSV as `POST /users/import` with `Content-Type: text/csv` and `Authorization: Bearer <token>`. With a configured matching token and a valid file, respond 201 with `{"created":[{"id":4,"name":"Lin","email":"lin@example.com"}]}` for the input header `name,email` and data row `Lin,lin@example.com` on a fresh process. For two valid rows assign contiguous IDs and preserve row order. Confirm through HTTP and read the resulting IDs and collection via GET.
- CSV accepts exactly the lowercase name and email headers in either order, UTF-8 with optional BOM, LF or CRLF, a final newline, quoted commas and newlines, and doubled quote escapes. Confirm an upload with BOM, reversed headers and a quoted name over HTTP.
- Store ownership stays in one process. Existing GET routes expose the same shape and visibility for existing and imported users. Restart resets to the existing seed records. Verify seed and missing-user GET behavior and imported detail via HTTP. No UI or separate persistence is in scope.

### R-2 Reject invalid or unauthorized imports without creating users

Basis: admin restriction in the 2026-11-21 request and local integrity defaults.

- Missing, incorrect or unconfigured admin token produces 401. Invalid UTF-8, empty/header-only files, wrong headers, malformed quoting, inconsistent rows, blank names, malformed emails or duplicate emails produce 400. Include a record number starting at 1 for header, row and quoting errors. Wrong media type yields 415, and uploads above 1 MiB yield 413. Confirm over HTTP with denied, invalid and oversized requests.
- Trim names and emails. Email must have nonempty local and domain portions, a dot in the domain, and no whitespace or extra @. Check duplicates case-insensitively against existing users and earlier rows. When any row fails, user records and the next ID are unaffected. Confirm through a valid-then-invalid or duplicate batch, compare the collection before and after, and accept a corrected batch. A retry after successful creation fails on the existing email.

## Non-functional requirements

Accept at most 1,048,576 request bytes and stop buffering at the first excess. Check over HTTP including streamed input. Reject access before parsing or mutating. Keep token and raw CSV out of diagnostics, and use record numbers without echoing rejected values. Synchronous validation and commit avoid interleaving with other writes in the same process. No external service, hosted availability target, UI accessibility contract, or cross-process durability is in scope.

## Verification

Run `npm test` and exercise the real loopback HTTP API, including denial and read-back, before local source return. Planned acceptance example starting at 7b65835 seed state: GET /users yields IDs 1–3. POST a valid Lin row with the configured admin token, so R-1 permits the next ID 4. GET /users/4 then exposes the same record and retrying that upload produces 400 with the user still present once. This is a manual walk of the contract, with execution due during implementation and release.

## Retired

None.

## Key questions

- K1 Administrator uploads at POST /users/import and checks the created users via GET (R-1).
- K2 Preserve both existing GET routes and the in-memory lifecycle (R-1).
- K3 Raw UTF-8 text/csv with name and email, JSON results (R-1, R-2).
- K4 Validate before commit and reject bad rows or duplicates atomically (R-2).
- K5 The existing process-local store owns IDs, records and restart behavior (R-1, R-2).
- K6 Existing dependency-free Node runtime and an import-specific ADMIN_IMPORT_TOKEN (Environment, R-2).
- K7 Extend the existing HTTP entry and store with a CSV parsing seam (architecture decisions).
- K8 node:test over loopback with real reads and writes (Verification).
- K9 Deliver by local source return (Environment).
- K10 Gate with admin authorization, cap bytes and omit sensitive diagnostic content (Non-functional requirements).
- K11 Partial writes and access bypass get explicit rejection checks (R-2).
- K12 CSV means comma-delimited records with quote escapes. Admin means the caller holding the configured token (R-1, R-2).

