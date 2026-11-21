# User directory specification

## Scope

Local HTTP user directory. The 2026-11-21 request “Let admins upload a CSV to bulk-create users” adds a batch write interaction. The baseline comes from README.md, src/server.js, src/users.js and test/server.test.js at ec1f94c. No earlier written product requirements were found.

## Requirements

### R-1 Admin-only CSV import

An admin sends a UTF-8 file as the body of POST /users/import with media type text/csv. Existing HTTP clients remain the delivery surface. The configured ADMIN_TOKEN is the authority for this write. Its absence disables imports. This API shares the existing directory and process lifetime.

- Acceptance: A matching Authorization bearer credential and a CSV with header `name,email` followed by `Mina Tan,mina@example.test` and `"Ng, Lee",lee@example.test` returns 201 with both created users, in file order, with IDs 4 and 5 on a fresh process. GET /users includes both and GET /users/5 returns Lee. Verify over loopback against a newly started process.
- Acceptance: Missing or wrong credentials and missing server configuration each yield 401 and leave the existing records intact. Verify over HTTP. A valid credential with a media type other than text/csv yields 415. Existing unauthenticated GET routes keep their responses.
- Acceptance: CSV accepts name and email headers in either order, LF and CRLF records, an optional UTF-8 BOM and terminating newline, and quoted fields with commas, embedded line breaks and escaped double quotes. Verify exact returned field values over HTTP.

### R-2 Atomic validation and bounded uploads

Derived from the batch creation request and the existing user directory model. The process-local user store owns IDs and email uniqueness and makes a batch visible together. Each admitted record has a trimmed nonempty name and email with an address-like local and dotted domain part. Email uniqueness ignores case. Users, including imported records, remain readable through the current directory endpoints until process restart. The original file is discarded after processing and upload errors omit user values and credential contents.

- Acceptance: Malformed CSV, invalid UTF-8, absent or unexpected headers, no data rows, incorrect column count, and invalid field values each produce 400. Row-specific errors identify the one-based logical CSV record. Verify rejection and unchanged GET state after a valid first row followed by an invalid one.
- Acceptance: Duplicates in the file or directory return 409 with a record number. Retrying a successful file or racing imports of the same email creates only one copy. Verify concurrent requests and GET state.
- Acceptance: A body over 1 MiB returns 413 for both declared and streamed requests. A body of exactly 1 MiB is accepted when otherwise valid. Verify on loopback and check the rejected uploads add no records.

## Non-functional requirements

Use a 1 MiB input limit as this run's resource policy and verify both byte-limit paths. Check authorization before interpreting payloads. Validate before writing and return errors without displaying submitted personal data. No graphical interaction, remote integration or database lifecycle is involved.

## Retired

None.
