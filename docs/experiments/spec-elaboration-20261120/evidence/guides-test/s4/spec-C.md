# User service specification

## Requirements

### R-1 Administrator CSV creation

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). The starting service at ec1f94c provides public GET /users and GET /users/:id and process-local seeded users.

- An operator configures ADMIN_TOKEN. POST /users/import accepts the matching Authorization: Bearer credential. Missing, invalid or unconfigured credentials return 401 and leave users unchanged. Confirm with real HTTP requests and GET readback.
- Upload raw UTF-8 text/csv with a name,email header (either order), and at least one data record. Allow BOM, LF, CRLF, quoted fields and doubled quotes. A successful request returns 201 with created count and the new records, in input order. GET by ID and list expose them with the same shape as existing records. Confirm with a two-record upload and seeded/new GETs.
- Trim values, require a name and a syntactically plausible email, and require case-insensitive email uniqueness across the entire store and upload. Assign IDs in ascending order after the existing highest ID. Invalid input returns 400, duplicate email returns 409, and non-CSV media returns 415. Report the CSV record's starting line for malformed rows or conflicts when available. Reject the entire batch on any error. Verify via status, response and unchanged list.
- Existing GET behavior and seeds are preserved. Users remain process-local, shared among the same process's server instances and reset on restart. Validation and commit are synchronous once the request is decoded so concurrent uploads cannot both create the same email. The service stores user fields, never the raw upload or credential. No browser UI, user updates, roles within records, or external persistence is required.

## Non-functional requirements

- Limit the request body to 1 MiB and data records to 1,000. Return 413 when either limit is exceeded. Confirm by HTTP test. Error replies exclude raw row values and credentials.
- Existing HTTP service has no visual interface. Latency and availability targets follow the local dependency-free baseline with no service SLA.

## Retired

None.
