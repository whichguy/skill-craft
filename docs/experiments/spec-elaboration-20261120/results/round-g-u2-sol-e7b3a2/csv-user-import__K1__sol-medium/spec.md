# User service specification

## Scope

The service exposes process-local user records over HTTP. The CSV import creates records with generated IDs and the same name and email fields as existing records.

## Requirements

### R-1 Admin CSV upload

Basis: “Let admins upload a CSV to bulk-create users.” (2026-11-21). Adds a write interface to the read-only baseline in README.md and src/server.js.

- R-1.a: An operator holding the configured admin token can POST a raw UTF-8 `text/csv` body to `/users/import`. Missing or invalid credentials return 401 before mutation. When no token is configured, writes are disabled and return 503. Verify with HTTP and unchanged list snapshots.
- R-1.b: Require exactly `name` and `email` headers in either order and at least one data record. Handle UTF-8 BOM, LF and CRLF, optional final newline, quoted commas, escaped quotes and quoted newlines. Trim field edges, require a non-empty name and a basic email shape. Malformed CSV, headers or data return 400 with a logical record number where applicable. Unsupported content type returns 415. Verify with direct HTTP inputs and read-back.
- R-1.c: A successful request returns 201 with `{created, users}`. Each record gets a distinct sequential ID and appears at the existing detail and list endpoints. Compare returned records with read-back. For a fresh fixture, two valid records produce IDs 4 and 5.
- R-1.d: Reject existing or in-batch email collisions case-insensitively with 409 and the offending record number. Any failed batch leaves state and ID allocation unchanged. Two simultaneous uploads sharing an email can create it only once. Verify via competing HTTP requests, a mixed batch and subsequent read-back.

The store owns the records in server-process memory. The admin config carries only the write credential. Imported records have the same public visibility as existing records and are discarded on process restart. Error bodies omit submitted values and credentials. Upload bytes are request-scoped. Import completion is synchronous and needs no job or cache. Editing, deleting, account sign-in and durable storage are outside CSV creation.

### R-2 Existing read API

Preserve the public JSON list in ID order, numeric detail lookup and JSON 404 behavior described by src/server.js and its baseline test. Verify via the existing suite plus HTTP list and detail read-back after an import.

## Non-functional requirements

Enforce an initial operational limit of 1 MiB per request and 1,000 data records, with 413 and zero writes on overflow. This is a product default for bounded local processing, checked through HTTP at each limit. Require no runtime dependencies beyond Node. The HTTP API has no rendered interface, external deployment requirement or availability SLA.

## Retired

None.
