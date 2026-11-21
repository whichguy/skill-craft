# User service specification

## Requirements

### R-1 Admin CSV import

Basis: “Let admins upload a CSV to bulk-create users” (2026-11-21). Existing HTTP consumer and record shape come from README.md, src/server.js and src/users.js.

- R-1.1 An administrator can POST a UTF-8 CSV file as a text/csv body to `/users/import`. A valid file creates one user per data record in order and returns HTTP 201 with `{"created":2}` for a two-record batch. IDs are server-assigned and monotonically increasing. Verify over loopback HTTP with a synthetic bearer token, `name,email\nDana,dana@example.com\nEvan,evan@example.com`, and read Dana and Evan at IDs 4 and 5 on a fresh process using the existing reads.
- R-1.2 Accept exactly the two headers `name` and `email` in either order, optional UTF-8 BOM, LF and CRLF, optional final newline, and standard CSV quoting including commas, doubled quotes, and embedded line breaks. Trim surrounding whitespace from data fields. Require a non-empty name and a simple email in user@example.com form. Invalid UTF-8 or CSV, a header-only file, wrong columns, or invalid field data return 400. Record-specific errors include the logical CSV record number counting the header as 1. Other media types return 415. Verify positive and negative examples over HTTP.
- R-1.3 The configured admin bearer credential is required before upload processing. Missing or incorrect credentials return 401 and a Bearer challenge when configured. With no credential configured, the endpoint returns 503. Verify both conditions and read back unchanged state.
- R-1.4 Email addresses compare case-insensitively within a file and against all existing users. A duplicate yields HTTP 409 and identifies the conflicting record number. Any rejected file leaves the store and its next generated ID unchanged. A corrected file can be retried. Test late failure, existing and intra-file duplicates, and two overlapping requests for the same address.
- R-1.5 A file can include up to 256 KiB and 1,000 data records. A request beyond either boundary returns 413, with no users created. Verify a byte overflow with and without Content-Length and a row overflow via HTTP.

State: the process keeps id, name and email in the existing shared collection until restart. Existing public reads expose the same shape. Requests share only committed users. Request bytes and bearer credentials do not appear in errors or logs. The service has no external cache, queue or persistence.

### R-2 Existing user reads

Basis: baseline ec1f94c, src/server.js and src/users.js. `GET /users` still lists all stored users in ID order. `GET /users/:id` returns the stored record or 404. Test existing seeded and missing IDs and post-import reads over HTTP.

## Non-functional requirements

Bounded request memory uses the R-1.5 payload limits. R-1.3 defines configuration and rejected auth. R-1.4 defines consistency and retry. The current consumer is an HTTP client. Graphical interface, visual polish and accessibility checks for a graphical UI are inapplicable. No throughput or durability target was requested.

## Retired

No retired requirements.
