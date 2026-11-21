# User service specification

## Scope

The HTTP user service exposes process-local records. Basis for bulk creation: “Let admins upload a CSV to bulk-create users.” (2026-11-21). Baseline is ec1f94c, README.md and src/{server,users}.js. Baseline tests cover reads only.

## Requirements

### R-1 Admin bulk creation

- CSV-01. POST /users/import with a configured admin bearer token and a UTF-8 text/csv file with one name and one email header, in either order, creates each row in input order. The HTTP response is 201 with `{created, users}`, where created is the count and users contains their assigned numeric IDs and fields. Example from the seeded store: James, james@example.test then Mary, mary@example.test yield IDs 4 and 5 and can be read by GET /users/:id and GET /users. Confirm on an isolated loopback server.
- CSV-02. Quoted commas, quote escaping and line breaks in names, LF and CRLF, an optional UTF-8 BOM, optional final newline and blank lines are accepted. Values are trimmed. Check exact persisted values via the response and read routes.
- CSV-03. Invalid credentials or an unconfigured admin token return 401 without mutation. Verify with otherwise valid upload data and a before/after GET.
- CSV-04. Malformed CSV, invalid UTF-8, missing or unexpected columns, empty imports and invalid rows return 400. A valid row has exactly two fields, a nonempty trimmed name and a trimmed email with one @, nonempty local and domain parts, and a dotted domain. Fields cannot contain NUL. A row error identifies its starting file line and omits field values. A duplicate email (case-insensitive across existing users and within the upload) returns 409 and identifies the conflicting line. Failures leave the entire store unchanged. Verify status, line, and before/after GET. Retrying a successful import yields 409.
- CSV-05. Media types other than text/csv return 415. Requests above 1 MiB return 413, including when no Content-Length is present. Verify via actual HTTP requests and read-back after failure.
- CSV-06. Overlapping imports with the same email produce one 201 and one 409. Existing GET status, ordering, seeded IDs and user field shape remain available. Verify via concurrent requests and regression tests.

The caller owns the CSV file; the service holds bytes during the request and never persists the source file. Valid records share the existing process-local lifecycle and read visibility, and reset on process restart. The operator configures the admin credential; responses and logs omit it. Imports complete synchronously after body receipt. User invitations, individual admin accounts and durable storage are outside the existing product scope.

## Non-functional requirements

Apply authorization before intake and cap buffered request bodies at 1 MiB to bound per-request memory. Avoid returning submitted values in errors. Assert the bounds and rejection behavior over loopback. The existing product provides a programmatic HTTP interface.

## Retired

None.
