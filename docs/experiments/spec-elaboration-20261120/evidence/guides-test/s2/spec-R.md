# User API specification

## Requirements

### R-1 Admin CSV upload
- Add per “Let admins upload a CSV to bulk-create users” (2026-11-21). The 3558d4c baseline in src/server.js has HTTP reads and no administrator identity. The chosen admin identity is possession of the server's ADMIN_TOKEN bearer credential. Without configuration, all imports are denied.
- An authenticated POST /users/import accepts a raw UTF-8 text/csv body. A UTF-8 BOM, LF/CRLF, quoted commas and line breaks, and doubled quotes are supported. The header contains exactly name and email in either order. Trim surrounding whitespace in values and ignore blank lines. Media types other than text/csv return 415. Missing or incorrect authorization returns 401 before CSV processing. Verify through real HTTP in test, acceptance and local release verification (T-1 and T-2).
- A nonempty batch with valid rows gets 201 and a JSON object containing created users in CSV order. On a fresh process, name,email followed by Mia,mia@example.com and Leo,leo@example.com creates IDs 4 and 5; both IDs resolve via GET and the list includes both. Verify over HTTP (T-1).

### R-2 Batch validation and consistency
- Add as the failure semantics for R-1. Each row requires exactly two fields, a nonblank name and a syntactically plausible email. Empty/header-only, malformed CSV or UTF-8, bad headers and invalid rows return 400. Data errors identify the 1-based starting line when known. Duplicate emails, including case variants, within the file or current store return 409.
- Reject a body above 256 KiB or above 1,000 data records with 413. Exactly the stated limits are permitted.
- On any rejection, preserve the existing list and next ID. Stage rows before a synchronous append to the shared process-local store. Competing requests for the same email leave one creation. An unchanged retry after success is a conflict. Correct rejected files and resubmit. Test rollback, boundaries and concurrent callers via HTTP (T-2 through T-5).
- The existing module owns created records. The process restart resets them to the seed records, as before. Public GET visibility follows R-3. The credential stays in server configuration; upload data and credentials are absent from application logs. Code review checks logging and state placement.

### R-3 Existing reads
- Preserve the baseline src/server.js and src/users.js contracts at 3558d4c. Public GET /users returns all records in ID order. A known numeric ID returns the existing id/name/email shape, and unknown IDs return 404. On a fresh process the seed users are unchanged. Cover baseline and post-import compatibility through HTTP tests (T-1 and T-6).

## Non-functional requirements
- Resource default: R-2 caps each upload; body size is enforced for declared and streamed input. Test exact and over-limit cases. There is no service latency SLA or external storage requirement for the local process.
- Security: R-1 is default closed. R-2 protects state integrity and avoids writing credentials and rejected input to logs. Verify denials, atomicity and inspect implementation.
- Compatibility: use the declared Node 20+ runtime and existing HTTP response model. Verify the package suite on the available runtime. UI accessibility is outside the HTTP-only surface.

## Retired
None.
