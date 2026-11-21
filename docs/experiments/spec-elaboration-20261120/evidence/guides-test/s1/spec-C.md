
# node-base product specification

## Requirements

### R-1 Admin CSV import

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). The prior HTTP surface is documented in README.md and implemented by src/server.js. The upload adds a mutation to the existing user store.

- **Authorized upload.** An HTTP client with the configured admin bearer token can post a UTF-8 file to POST /users/import with Content-Type text/csv. A missing or incorrect credential, or absent token configuration, returns 401 and writes zero users. An authorized upload with another media type returns 415. Confirm via loopback HTTP and read-back.
- **CSV contract.** Require a header containing exactly name and email in either order. Accept UTF-8 with an optional BOM, LF or CRLF, and double-quoted fields with doubled quotes. Ignore blank lines and trim field values. Require at least one record, a nonempty name, and a plausible, non-whitespace email with a domain containing a dot. Wrong field counts, malformed quoting, invalid UTF-8 and invalid fields return 400. For row errors, include the one-based CSV line where the record starts, including the header in the count. Confirm with valid and invalid files at the HTTP surface.
- **Creation and conflicts.** For a valid batch, append users in CSV order, assign fresh numeric IDs, and respond 201 with the number created in a created field. GET /users and GET /users/:id see the new rows immediately. An email matching an existing or same-file email case-insensitively returns 409 with the conflicting row line. Every rejected batch leaves the store unchanged, and simultaneous imports obey the same uniqueness rule. Confirm with success, late rejection, duplicate and concurrent requests.
- **Data lifetime.** The service keeps created users with the existing process-local user records. Upload bodies are request-scoped and diagnostics omit raw user values and credentials. The process starts with the existing seeds. There are no account invitations or role changes in CSV. Confirm record shape and read-back through GET.

### R-2 Existing user reads

Preserve the GET /users list and GET /users/:id lookup, with 404 for an unknown ID. Source: README.md, src/server.js, src/users.js and baseline loopback test. Confirm with the existing suite and read-back after import.

## Non-functional requirements

- Bound buffering to 1 MiB and accept at most 1,000 data records per upload. Over either limit return 413 and write zero users. These are local defaults to constrain work while supporting a useful bulk operation. Confirm at the HTTP boundary, including an oversized streaming request.
- Use operator-controlled admin access and deny by default. Confirm that public reads still work and denial does not mutate the store.
- Keep Node 20+ compatibility and the dependency-free runtime. The product surface is HTTP. No rendered interface, hosted verification, new retention system or distributed latency target applies.

## Retired

None.
