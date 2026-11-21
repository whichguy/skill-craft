# User API specification

## Scope

The Node HTTP API serves a shared process-local user store.

## Requirements

### R-1 Read users

The baseline at 3558d4c serves GET /users in ID order and GET /users/:id returns the matching user or 404. Confirm with the existing suite and import read-back.

### R-2 Create users from a CSV upload

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21, S1). Existing reads and seeded records follow src/server.js and src/users.js at 3558d4c. Confirm the clauses through the local HTTP server.

- An administrator sends POST /users/import with `Authorization: Bearer <token>` and a UTF-8 `text/csv` body. The operator configures `ADMIN_IMPORT_TOKEN`. A missing or incorrect credential returns 401, and an unconfigured server returns 503. Neither case creates users. An unsupported content type returns 415.
- A valid upload has a header with exactly `name` and `email` in either order, then 1 to 1,000 records. Accept LF and CRLF, optional initial BOM, quoted fields, escaped quotes and quoted line breaks. Trim outer whitespace from values. Names must be nonempty and emails must have a nonempty local part, a dotted domain and no whitespace. New users get increasing numeric IDs and existing read routes expose them. Return 201 with `{"created":2}` for two rows such as `New User,new@example.com` and `Another User,another@example.com` after a `name,email` header.
- Reject malformed CSV, invalid UTF-8, missing or extra columns, invalid values and an empty batch with 400. Validation errors tied to a data record identify its logical CSV row (header is row 1). Case-insensitive email collisions within the upload or with stored users return 409. Reject the whole batch on failure, preserving existing records. Verify via GET /users before and after each rejected upload.
- Reject more than 1 MiB of body data or more than 1,000 user records with 413. Test with synthetic inputs and verify the store remains unchanged.

The process owns created users until restart. Requests share the store. Simultaneous uploads resolve conflicts against the latest store at write time. CSV and token are not logged or kept as separate records. Stored user names and emails use the same visibility as existing records. No UI or remote lifecycle is part of this API.

## Non-functional requirements

Authorization defaults to disabled until configured. Keep input memory bounded by the documented body limit and validation synchronous after body collection. Verify error responses and store state via loopback. No graphical interface is in scope.

## Retired

None.
