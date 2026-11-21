# User service specification

## Scope

The service lists and retrieves users and supports admin CSV import. The original read API is documented by src/server.js and src/users.js at ec1f94c. The 2026-11-21 request “Let admins upload a CSV to bulk-create users.” grounds R-1 through R-3. The defaults below govern this HTTP-only project.

## Requirements

### R-1 Admin upload access

Admins send `POST /users/import` using the configured `ADMIN_TOKEN` as an Authorization bearer credential. When unset or unusable, the route returns 503. With configuration, a missing, malformed or wrong credential returns 401 with a Bearer challenge. Check authorization before handling the CSV. On denial, the existing store is unchanged and the response exposes no credential or input content. Verify through HTTP with configured and unconfigured servers (C-1).

### R-2 CSV file validation

Accept a raw UTF-8 `text/csv` request body, including content type parameters, optional leading UTF-8 BOM, LF and CRLF, and optional final line break. Header has exactly `name` and `email`, in either order. Support quoted fields, doubled quotes and embedded delimiters and newlines in quoted fields. Each record has the same two fields. Trim values, require a nonempty name and an email with one @ and a nonempty dotted domain, without whitespace or controls. Email validation checks structure only. At least one data record is required. Unsupported media types get 415, malformed CSV or field values get 400, and oversized body or record count gets 413. Errors describe the issue and include the logical record number when applicable (header is record 1). They omit field contents. Verify success and invalid variants through HTTP (C-2, C-3, C-5).

### R-3 Atomic user creation

With a valid authorized request, create all rows with server-assigned numeric IDs in file order and return 201 with a JSON `created` count. Existing user GET endpoints expose the new records by list and ID as soon as the request succeeds. An email already present or repeated in the upload is a 409 for the first conflicting record, using a case-insensitive comparison. Store the trimmed email as supplied. Rejection, including a disconnected incomplete upload, leaves the store and ID allocation unchanged. Overlapping uploads share the same store and only one can create an overlapping email. After a successful request whose response is lost, retry reports the duplicate and creates zero additional records. Verify via HTTP and read-back (C-2, C-3, C-4, C-6).

### R-4 Existing read service and state lifetime

Public list and ID read behavior, seed records, JSON shape and unknown ID 404 remain as evidenced by src/server.js, src/users.js and test/server.test.js at ec1f94c. New records share the existing process-scoped store and age out on process restart. Public reads include the same name and email fields for seed and imported users. The server does not persist uploaded bodies or log row contents. Verify seed behavior, unchanged reads on rejection and successful read-back (C-1 through C-6). Persistence, invitation delivery, identity-provider integration and a browser client are outside this scope.

## Non-functional requirements

Accept up to 1,048,576 bytes and 1,000 data records per upload as implementation defaults. Count bytes received for all request framing, including chunked input. Reject when either limit is exceeded and keep the store unchanged (C-5). The service exposes HTTP JSON and has no rendered interface.

## Flows and state transitions

F-1 (R-1–R-3) starts with a caller bearing a configured token. The request temporarily holds bounded bytes. At end of input the server parses and validates the file. T-1 validates email uniqueness against the current process store, then synchronously appends the batch. 201 and existing GET reads expose completion. C-2 and C-6 observe this transition.

F-2 (R-1–R-4) covers denial, invalid input, limits, duplicates and interrupted input. T-2 discards transient input without mutation, and replies with the applicable error if the connection remains available. The caller can correct validation failures and resend. Competing requests are resolved at T-1; neither partial effects nor queued work exist. C-1 and C-3 through C-6 observe T-2.

F-3 (R-4) reads the live store. The store starts with the seed records at process launch, contains unique IDs in ascending order, and accepts public reads. T-3 (process restart) discards imported records and restores seeds. Credential configuration belongs to the server operator and lasts for the running server instance. CSV bytes are transient and discarded after response or interruption. No remote dependencies or separate job state are involved.

## Verification cases

| Case | Setup and observable result |
| --- | --- |
| C-1 | Fresh service with and without the admin token. Missing and wrong credentials produce 401, unconfigured upload produces 503, and public reads show seeds. |
| C-2 | In a fresh process upload `name,email` then `"Lovelace, Ada",ada-import@example.com` and `Grace Import,grace-import@example.com`. Expect 201, count 2, and records with IDs 4 and 5 through GET. Exercise BOM, CRLF, escaped quotes, quoted newline and reversed column order. |
| C-3 | Reject unsupported media type, malformed encoding, malformed quoting, bad headers, empty upload and invalid later rows. Read the store and verify that no earlier valid row from a rejected upload was inserted. |
| C-4 | Reject a second row with `ADA@EXAMPLE.COM`, and an intra-file case-insensitive duplicate. A successful batch replay reports 409 and leaves state intact. |
| C-5 | Test the inclusive byte and record boundaries and one above each. Use chunked framing for a streamed overflow. A rejected upload preserves the store. |
| C-6 | Disconnect after a complete-looking prefix, then confirm it was discarded. Race two authorized requests containing one common new email. Expect one 201, one 409, exactly one inserted email and a consistent ID sequence. |

## Retired

None.
