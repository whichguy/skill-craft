# User service specification

## Requirements

### R-1 Admin CSV import

Adds the Nov 21, 2026 request, “Let admins upload a CSV to bulk-create users.” The pre-change service described in README.md exposes user reads only.

- With a configured admin token, POST /users/import accepts a raw UTF-8 text/csv upload, with optional UTF-8 BOM, LF or CRLF, quoted fields, doubled quotes and quoted line breaks. The header contains exactly name and email in either order. Require at least one data record, trimming name and email, with a nonblank name and email of the form local@domain.tld without whitespace. Permit a final record terminator.
- An authorized upload of `name,email\n"Jordan, Alex",alex@example.net\nSam Lee,sam@example.net\n` into a fresh process returns 201 with `{"created":2}`. GET /users includes the two new records with IDs 4 and 5 and GET /users/4 returns Jordan's complete record. Cases T1 and T2 exercise the HTTP surface.
- The import endpoint requires the configured bearer token. With no valid token or no configuration, return 401 and keep the store unchanged. Unsupported media returns 415. Tests T3 and T4 verify denial followed by list read-back.
- Invalid encoding, CSV syntax, header, row width, name or email results in 400. Where a record can be identified, return its 1-based logical record number including the header. Duplicate emails, case-insensitive within an upload or against existing users, return 409 with the conflicting record number. No row is created on any failure. Tests T5 and T6 assert the response and list read-back. A repeated successful batch consequently receives 409. Concurrent batches are applied serially by the process; at most one can create a shared email (T8).
- Allow up to 1 MiB and 1,000 data records. Exceeding either bound returns 413 without a write (T7). These are operating defaults for this local service.

### R-2 Preserve existing reads

Preserves the baseline at 3558d4c (src/server.js, src/users.js, test/server.test.js). GET /users and GET /users/:id retain their JSON shape, seeded data and public access. A missing ID returns 404. Users remain shared in one process and live only until it exits. An admitted batch becomes visible through both reads; the original tests and T1 verify this behavior.

## Non-functional requirements

Bounded bytes and records are verified at the HTTP boundary by T7. Authorization precedes processing and the token and submitted fields never appear in errors or new logs. Keep the CSV transient and the same public name, email and ID projection for stored users. For non-loopback access use TLS termination before sending the bearer token or user data. The target has no visual UI, queue, remote store or stated throughput SLA.
