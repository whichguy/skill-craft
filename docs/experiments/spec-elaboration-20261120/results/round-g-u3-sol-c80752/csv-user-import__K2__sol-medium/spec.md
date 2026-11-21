# User service specification

## Requirements

### R-1 Admin CSV user creation

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). The existing service and evidence are documented in environment.md and in the seeded store in src/users.js. Preserve public listing and lookup, adding one authorized write path. Acceptance is observable locally over the actual HTTP server.

- **Authorization.** `POST /users/import` requires a valid bearer credential configured for the server. A missing or wrong token returns 401. An unset server token disables import. Check with loopback HTTP requests and read back the store to confirm rejected requests created zero users.
- **Format and success.** An authorized request uses a UTF-8 raw `text/csv` body. The required header contains `name` and `email` exactly once, in either order. Accept a BOM, LF or CRLF, an optional final line break, and standard quoted fields with doubled quotes. Trim field edges. Require at least one data record, a nonblank name and a valid-looking email address. On success return 201 with `{ "created": N, "users": [...] }` containing allocated numeric IDs and the submitted fields. Check that uploading `name,email\nAvery,avery@example.com\nSam,sam@example.com` to a fresh process yields IDs 4 and 5 and that both GET routes read the inserted records.
- **Failure and recovery.** Reject invalid format or data with 400, duplicate email with 409 (case-insensitive across existing and imported records), unsupported media type with 415, and bodies over 1 MiB with 413. Row errors identify the failing record number where applicable. Create zero users on any rejection. Corrected uploads can be retried. A repeated successful upload conflicts and does not mutate data. Check with HTTP failures, list readback and a corrected upload.
- **State.** The process owns the user records, shared across requests until restart. Authorized writes run synchronously after validation, preserving IDs, insert order and uniqueness under competing requests. Both public read routes continue to expose user records. Keep credentials on the server and omit credentials, raw payloads and personal data from import errors. No queue, notifications or separate storage are needed. Verify competing duplicate requests and inspect JSON error bodies.

## Non-functional requirements

A 1 MiB per-request limit bounds CSV processing and buffering. Verify rejection at one byte over the limit. No graphical interface is involved. Loopback HTTP is the consumer boundary for authorization and readback.

## Retired

None.
