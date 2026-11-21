# User management specification

## Requirements

### R-1 Admin CSV upload

- With import configured, POST /users/import with the configured Bearer credential and a UTF-8 text/csv body containing header columns name and email creates all records together. Accept column reordering, BOM, LF or CRLF, empty records and standard quoted fields with doubled quotes. Return HTTP 201 and JSON with createdCount and users. Verify by submitting multiple rows and reading their assigned IDs via existing GET routes.
- Missing or wrong credentials return 401 with a Bearer challenge. With no configured credential, return 403. Both leave the store unchanged. Verify through loopback with configured and unconfigured servers.
- Imported users use unique sequential numeric IDs, the existing name/email shape and public GET visibility. Observe collection ordering and individual reads. Existing records survive each failed upload. State is scoped to one process as in the original service.

### R-2 Validation and safe retry

- Reject unsupported media types with 415; reject uploads above 256 KiB or 1,000 nonempty data records with 413. Verify by making real HTTP requests and comparing state.
- Reject invalid UTF-8, malformed CSV, missing or additional columns, empty input and invalid required fields with HTTP 400. A row validation failure identifies the CSV record number (header is record 1).
- Compare normalized email addresses case-insensitively and reject duplicates inside the upload or against existing users with 409 and a record number. Retrying after failure or success cannot leave a partial batch. Verify with duplicates following a valid row and read-back of the unchanged collection.
- Preserve the original JSON read responses, missing-ID status and list order. Verify with the existing suite.

## Non-functional requirements

Bound request memory and row work by the declared limits. Keep upload bytes and credentials out of errors and logs. Configure credentials per server and fail closed. Use dependency-free Node APIs and an immediate response; no UI, persisted file, asynchronous job or new hosted service is required.

## Acceptance criteria

The local HTTP integration tests exercise R-1 and R-2. Run the same suite on the locally delivered source tree.

