# User service specification

## Requirements

### R-1 Admin CSV upload

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21).
The admin sends UTF-8 CSV as the raw body of POST /users/import with Content-Type text/csv and a valid configured Authorization bearer token. The API returns HTTP 201 and a JSON object with createdCount and users. Each created user has a server-generated numeric ID and the provided name and email. GET /users and GET /users/:id observe the records. Existing read routes stay public and retain their JSON and 404 behavior as documented by README.md and src/server.js.

- Acceptance: on a fresh process, importing `name,email\nAva,ava@example.com\nNoah,noah@example.com\n` creates users 4 and 5 in row order. Confirm HTTP 201, count 2, both returned records and read-back by list and ID.
- Acceptance: absent, malformed or wrong credentials return 401 before parsing. Missing admin configuration returns 503. Confirm the user list is unchanged. The operator supplies the credential through configuration. Import creates no accounts with admin authority.

### R-2 Validate the entire batch before creation

Basis: atomicity and format defaults for the 2026-11-21 CSV upload, using name and email from src/users.js. The CSV must contain exactly the name and email headers, in either order, and at least one data record. Accept unquoted and quoted cells, escaped double quotes, embedded line breaks in quoted cells, LF or CRLF, and an optional UTF-8 BOM. Skip physically blank lines. Trim surrounding whitespace in data fields, require a nonempty name and a plausible email address with a dotted domain. Compare email addresses case-insensitively while preserving the submitted spelling.

- Acceptance: malformed syntax, invalid UTF-8, missing or extra columns, empty input, and invalid names or emails return 400. Include the starting physical line of an error when attributable to a row. Unsupported media returns 415. Confirm unchanged state by list read-back.
- Acceptance: an email already stored, or repeated within the same file, returns 409 with its row. Confirm a valid preceding row is absent after failure and retrying a successful file creates no additional records.
- Acceptance: two overlapping administrator uploads for the same unused email create one record and yield one 201 and one 409. The process-local store commits synchronously and resets on process restart. The raw upload and token are kept out of application logs.

## Non-functional requirements

- R-2 bounds an upload to 262144 bytes and 1000 user records per request. Confirm each exact boundary succeeds with valid fixture data and a one-unit excess returns 413 with unchanged state.
- The consumer surface is machine-facing HTTP. Compatibility is verified using the actual server and store on loopback.

## Retired

None.
