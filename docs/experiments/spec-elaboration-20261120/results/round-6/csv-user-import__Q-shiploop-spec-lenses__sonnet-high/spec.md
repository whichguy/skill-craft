# Admin User Management: Product Specification

Version 1, written 2026-11-21 by the spec stage run on its own. Scope of this version: the request
**"Let admins upload a CSV to bulk-create users."** (request, 2026-11-21).

## 0. Reading notes

### Sources inspected and their status

| Source | Status | Finding |
| --- | --- | --- |
| Request text, 2026-11-21 | accepted, the only authority | One sentence. Every R-n below is traced to it or to an assumption A-n. |
| `KNOWLEDGE/spec.md` before this run | absent | No earlier requirements, so no R-n was kept, changed or retired. `## Retired` is empty. |
| Discovery and research results | absent | Nothing ran before this stage. Facts about the existing product are unknown, not absent (see G-1 to G-9). |
| Repository, selected baseline | absent | The stage runs without one. The "current-system baseline" is therefore **unknown**, and `evidence limits` in each R-n say so. |
| `GUIDES/` (behavior model, requirements definition, service discovery, UI visual direction) | read | Used for form and for the checklist of lenses. They are not product sources. |

Observation, inference and unknown are kept apart: everything under "Existing behavior" is an **unknown**, every
rule written below is an **inference or decision** stated as an A-n or R-n, and nothing here is an observation of
running code.

### Assumptions (recorded defaults for open choices; a person may overturn any of them)

| ID | Assumption | Why this default |
| --- | --- | --- |
| A-1 | The product is a web application: an admin signs in through a browser and calls an HTTP backend. The import has two consumer surfaces: the **admin import page** (UI) and the **import endpoint** (API, multipart upload, JSON result). | A "CSV upload by admins" implies a browser; no other surface is named. |
| A-2 | Users, roles, sign-in, sessions and a single-user "create user" action already exist, and "admin" is a role the product already defines. The import adds no sign-in, role or identity model. | The request says "admins" and "bulk-create", which presupposes both. Unverified (G-1). |
| A-3 | **Parity rule.** A user created by import must be indistinguishable from one created by the existing single-user create: same field rules, same normalization, same default role, same credential bootstrap, same notification, same audit trail. Where this spec is stricter (admin role cannot be imported, A-7) the stricter rule wins. | "A rule enforced on one path and not another" must never be true. |
| A-4 | **All-or-nothing.** A file that has any problem creates no user at all, and every problem found is reported. | Makes retry after correction safe and removes the half-imported state. Recorded as a product decision to confirm (G-6). |
| A-5 | An email that already belongs to any existing account (active or deactivated) is a row error, never a skip, update or overwrite. | Silently skipping hides data errors; updating exceeds "create". |
| A-6 | Single-tenant. If the product has tenants or organizations, G-2 applies. | Request names no tenant. |
| A-7 | An import may assign only non-admin roles. A row asking for `admin` is rejected. | A CSV is a file passed around outside the product; granting admin through it is privilege escalation the request did not ask for. |
| A-8 | Limits (configurable, see R-12): file size 1,048,576 bytes (1 MiB); data rows 1,000; email 254 characters (local part 64); name 1 to 100 characters. | Chosen so a full file is far below typical request limits and finishes in one request. Values are **defaults awaiting owner confirmation** (G-5); they are not derived from the runtime, which is unknown (G-3). |
| A-9 | The import is synchronous: one request carries the file and returns the final result. No background job. | The row cap keeps work small; avoids an async status model the request does not need. Decision recorded as AD-2 in `architecture.md`; revisit if G-3 shows the platform cannot finish 1,000 rows inside its request timeout. |
| A-10 | Emails are normalized by trimming and lowercasing and compared case-insensitively, unless the existing single-create path does otherwise (A-3 then governs). | Common product convention. |
| A-11 | Default role for a row without a role value is `member`. The role catalogue used in examples is `member` and `admin`. | Needed to write replayable examples; real catalogue is G-4. |

### Sample data used by the acceptance lines

Every acceptance line starts from **Seed-A** unless it says otherwise.

**Seed-A** (written directly into the store by test setup, not through the product):

| email | role | state | session |
| --- | --- | --- | --- |
| `ada@example.com` | admin | active | `S-ada`, signed in |
| `mia@example.com` | member | active | `S-mia`, signed in |
| `bob@example.com` | member | active | none |

"No session" means an anonymous caller. User count in Seed-A is 3. Setup may write the store directly; every action
after setup is a product action and must be permitted by the R-n it exercises.

Sample files (`\n` line endings unless stated; UTF-8 without BOM unless stated):

- **F-valid3**
  ```
  email,name,role
  alice@example.com,Alice Ng,member
  carol@example.com,Carol Diaz,
  dave@example.com,"Dave, Jr.",member
  ```
- **F-mixed**
  ```
  email,name,role
  erin@example.com,Erin Fox,member
  not-an-email,Frank Li,member
  bob@example.com,Bob Again,member
  ERIN@example.com,Erin Two,member
  gina@example.com,,member
  hal@example.com,Hal Roy,admin
  ivy@example.com,Ivy Cho,wizard
  ```
- **F-multiline** (CRLF line endings, a quoted field holding a line break, one trailing empty line):
  `email,name` / `jo@example.com,"Jo⏎Ann"` / `bad-email,Kim Lee` / (empty line).
- **F-bom** (UTF-8 BOM, CRLF, header with odd case and spaces): `﻿Email , NAME` / `zoe@example.com,Zoë Ångström`.
- **F-latin1**: `email,name` / `zoe@example.com,Zo\xEB` where `\xEB` is the single Latin-1 byte (invalid UTF-8).
- **F-pw**: header `email,name,password`, one row `x@example.com,X,pw`.
- **F-conc-1**: `email,name` / `x1@example.com,X One` / `shared@example.com,Shared`.
- **F-conc-2**: `email,name` / `shared@example.com,Shared Two` / `y2@example.com,Y Two`.
- **F-xss**: `email,name` / `n2@example.com,"<img src=x onerror=alert(1)>"`.
- **F-rows-1000** / **F-rows-1001**: header `email,name`, then 1,000 / 1,001 rows `u<i>@example.com,User <i>` for i = 0..999 / 0..1000.
- **F-size-cap**: header `email,name`, one valid row `pad@example.com,Pad` (31 bytes in all), then `\n` characters until the file is
  exactly 1,048,576 bytes. **F-size-cap+1**: the same plus one more `\n` (1,048,577 bytes).
- **F-email-254**: header `email,name`, one row whose email is 64 × `a`, `@`, then the domain
  63 × `b` `.` 63 × `c` `.` 57 × `d` `.com` (domain 189, whole address 254 characters), name `N`.
  **F-email-255**: the same with a 65-character local part (255 characters).
- **F-name-100** / **F-name-101**: header `email,name`, row `n1@example.com,` plus 100 / 101 × `x`.

Expected results for these files were derived by hand from the rules below. A local reference script for them was
written, but running it was not permitted in this environment, so the derivations are **NOT-REPLAYED** by machine
(see "9. Replay record").

## 1. Request outcomes

| Outcome | Meaning | Carried by |
| --- | --- | --- |
| O-1 | An admin can upload a CSV file. | R-1, R-2, R-14 |
| O-2 | Only admins can. | R-1, R-11 (authority at commit) |
| O-3 | The file's rows are read as user definitions. | R-3, R-4, R-5 |
| O-4 | Those users are created in bulk. | R-6, R-8, R-13 |
| O-5 (implied) | The admin can tell what happened and fix the file. | R-7, R-14 |
| O-6 (implied, operator) | The feature can be switched, bounded, observed. | R-9, R-10, R-12 |

Primary outcomes (listed again in `## Submission`): O-1 to O-4 through R-1, R-2, R-3, R-6, R-14.

## Requirements

Each requirement lists: **Basis**, **Preserved / changed**, **Source locators**, **Evidence limits**,
**Pending** (implementation and checks, none done), then the behaviour and the acceptance lines (`AL`).
Acceptance lines name surface and confirmation. Surfaces: **UI** (admin import page in a browser), **API** (import
endpoint), **STORE** (user store and audit store read directly), **LOG** (captured application logs), **MAIL**
(captured outbound mail). Confirmation: **E2E** (browser-driven test), **API-T** (HTTP-level test),
**DB** (store assertion), **LOGSCAN** (log assertion).

For every R-n: Preserved/changed is *added* (first version; nothing existed in this spec); Source locators are the
request sentence and the A-n listed; Evidence limits are "no repository, no discovery, no runnable system";
Pending is "implementation and the checks named in the acceptance lines, none written or run". Differences are
stated per requirement only where they exist.

### R-1 Only admins may import

Basis: request 2026-11-21 ("Let admins ..."); A-2.
Behaviour. The import page and the import endpoint are available to a signed-in user holding the admin role and to nobody else.
- No session: the API answers 401; the UI sends the person to the existing sign-in. No file is read.
- Signed in without admin: the API answers 403; the page entry is not shown in navigation and opening its address shows the existing "not allowed" page. The body of the upload is not parsed, and the response says nothing about which emails exist.
- The check is made on the server on every request. Hiding the UI entry is not the control.
- Role is read from the authority (the user store) when the import commits, not trusted from a long-lived token (see R-11).
- Dimension "who is refused" lists: anonymous, non-admin signed-in, admin whose role was removed during the request. Left out: per-admin enablement (not requested).

Acceptance lines
- AL-1.1 positive: `S-ada` opens the import page and sees the upload form; a POST of F-valid3 from `S-ada` is accepted for processing. Surface UI+API. Confirm E2E, API-T.
- AL-1.2 failure: anonymous POST of F-valid3 gets 401; STORE user count stays 3. Surface API. Confirm API-T, DB.
- AL-1.3 failure: `S-mia` POST of F-valid3 gets 403; count stays 3; the response body contains no email from Seed-A. `S-mia` navigation shows no import entry; direct page address shows the not-allowed page. Surface API+UI. Confirm API-T, E2E, DB.
- AL-1.4 boundary: a request carrying a non-admin session but a forged "role=admin" header, cookie or form field gets 403. Surface API. Confirm API-T.
- AL-1.5 failure (no existing user may see what they may not): a 403 for `S-mia` is identical whether or not the uploaded emails exist. Surface API. Confirm API-T (post F-mixed and F-valid3, compare bodies, ignoring the request id).

### R-2 File intake

Basis: request 2026-11-21 ("upload a CSV"); A-8, A-9.
Behaviour. One file per submission, sent in a multipart field named `file`. Outcomes by input:
- no file or more than one file part: 400 `FILE_REQUIRED`; nothing is read.
- zero bytes: 422 `FILE_EMPTY`.
- larger than 1,048,576 bytes: 413 `FILE_TOO_LARGE`; reading stops once the limit is exceeded, so the server never buffers an unbounded body.
- bytes that are not valid UTF-8 (a UTF-8 BOM is allowed and ignored): 422 `FILE_NOT_UTF8`; no row is processed, no character is replaced.
- the file name and declared media type are never used to accept or refuse a file (`.csv`, `.txt`, none; `text/csv`, `application/vnd.ms-excel`, `text/plain` all fine). Content decides, so a spreadsheet saved as `.xlsx` and renamed `.csv` fails as `FILE_NOT_UTF8` or `FILE_MALFORMED_CSV`.
- the file is held in memory only for the request and never written to disk or the store (R-10).

Acceptance lines
- AL-2.1 positive: F-bom is accepted and creates `zoe@example.com` with name `Zoë Ångström`. Surface API. Confirm API-T, DB.
- AL-2.2 failure: empty body file gives 422 `FILE_EMPTY`; F-latin1 gives 422 `FILE_NOT_UTF8`; a POST with no file part gives 400 `FILE_REQUIRED`; count stays 3 in each. Surface API+UI. Confirm API-T, E2E, DB.
- AL-2.3 boundary: F-size-cap (exactly 1,048,576 bytes, one valid row and blank lines) is accepted and creates `pad@example.com`; F-size-cap+1 gives 413 `FILE_TOO_LARGE` and count stays 3. Surface API. Confirm API-T, DB.
- AL-2.4 boundary: a valid file named `users.dat` with media type `application/octet-stream` is accepted; a valid file named `users.csv` with a non-CSV binary body (the first bytes of a ZIP archive, `PK\x03\x04`) gives 422. Surface API. Confirm API-T.
- AL-2.5 failure: a body of 50 MiB is refused with 413 without the process memory growing past a small multiple of the cap during the request. Surface API. Confirm API-T with memory sampling. Platform-dependent; see R-16 and G-3.

### R-3 CSV format and header

Basis: request ("CSV"); A-8.
Behaviour. RFC 4180 style: comma separator; fields may be double-quoted, a quoted field may hold commas, doubled quotes and line breaks; `\n` and `\r\n` both end a record. Everything else:
- Header row required. Recognized columns: `email` (required), `name` (required), `role` (optional). Names are matched after trimming and ignoring case; order is free. BOM ignored.
- Unknown column (including `password`, `id`, `status`): 422 `HEADER_UNKNOWN_COLUMN`, naming the column. Nothing is ignored silently, so nobody believes a password or status was applied. The import never accepts a credential from a file.
- Missing required column: 422 `HEADER_MISSING_COLUMN`. Repeated column after normalization: 422 `HEADER_DUPLICATE_COLUMN`.
- Record with more or fewer fields than the header: row error `ROW_FIELD_COUNT`.
- Unterminated quote, or a quote inside an unquoted field: 422 `FILE_MALFORMED_CSV`, naming the row where the problem starts.
- Records that are empty lines are ignored and are not counted; a record of only commas is not empty and fails as `ROW_EMAIL_MISSING` and `ROW_NAME_MISSING`.
- Header only, or no non-empty record after it: 422 `NO_DATA_ROWS`.
- More than 1,000 data records: 422 `TOO_MANY_ROWS` stating the limit and the count found; no row is validated.
- Every field is trimmed of leading and trailing whitespace before validation.
- Row numbers in every message are record numbers with the header as row 1 (the number a spreadsheet shows), not physical line numbers, so a quoted line break does not shift later rows.
- File-level errors (anything starting `FILE_`, `HEADER_`, `NO_DATA_ROWS`, `TOO_MANY_ROWS`) stop processing; row validation (R-4, R-5) runs only on a file that passed them.

Acceptance lines
- AL-3.1 positive: F-valid3 (quoted field with a comma, an empty role) is read as three records: `Dave, Jr.` is one name. Surface API. Confirm API-T (via the created list in R-7).
- AL-3.2 positive: CRLF and LF files, a missing final newline, and columns in order `name,role,email` all parse to the same users. Surface API. Confirm API-T.
- AL-3.3 failure: F-pw gives 422 `HEADER_UNKNOWN_COLUMN` naming `password`; header `email` alone gives `HEADER_MISSING_COLUMN` naming `name`; header `email,Email,name` gives `HEADER_DUPLICATE_COLUMN`; count stays 3. Surface API+UI. Confirm API-T, E2E, DB.
- AL-3.4 failure: `x@example.com,"Open` (unterminated quote) gives `FILE_MALFORMED_CSV` at row 2; a data line `x@example.com,X` under a 3-column header gives `ROW_FIELD_COUNT` at row 2. Surface API. Confirm API-T.
- AL-3.5 boundary: header-only file gives `NO_DATA_ROWS`; F-rows-1000 is accepted (1,000 users created); F-rows-1001 gives `TOO_MANY_ROWS` and creates none; a valid row between and after blank lines is row 2 (header row 1, blank lines uncounted). Surface API. Confirm API-T, DB.
- AL-3.6 boundary (row numbering): F-multiline gives two row errors: row 2 `ROW_NAME_INVALID` (line break in name) and row 3 `ROW_EMAIL_INVALID` (`bad-email`), although `bad-email` sits on physical line 4. Surface API. Confirm API-T.

### R-4 Row validation

Basis: request ("bulk-create users"); A-3, A-7, A-8, A-10, A-11.
Behaviour. After trimming, per row; every failing check is reported, so one row can carry several errors:
- `email` (required, `ROW_EMAIL_MISSING`): at most 254 characters, local part (before `@`) at most 64, exactly one `@`, no whitespace, local part non-empty, domain containing a dot with text on both sides; else `ROW_EMAIL_INVALID`. If the existing single-create path is stricter, it governs (A-3).
- `name` (required, `ROW_NAME_MISSING`): 1 to 100 characters (Unicode code points), no control characters including line breaks and tabs; else `ROW_NAME_INVALID`. Stored exactly as given after trimming; a leading `=`, `+`, `-`, `@` or HTML is not altered or refused (R-14 escapes on display).
- `role` (optional): empty means `member`; compared ignoring case with the product's role catalogue: not in it gives `ROW_ROLE_UNKNOWN`; `admin` or any role the import may not grant gives `ROW_ROLE_NOT_ALLOWED` (A-7).
- Each error carries: `row`, `column` (`email`, `name`, `role` or none), `code`, `message` in words an admin can act on, and the offending value for `email` and `role` only (the name value is omitted from errors to bound exposure; length is stated instead).
- Dimension "fields a row holds" lists `email`, `name`, `role`. Left out and why: password (never accepted, R-3), status, id, phone, groups and any other attribute (not requested; G-1 asks whether the single-create has more required fields).

Acceptance lines
- AL-4.1 positive: F-valid3: `carol@example.com` with empty role is created as `member`; `alice@example.com` keeps `member`; `dave@example.com` has name `Dave, Jr.`. Surface STORE. Confirm DB.
- AL-4.2 failure: F-mixed row 3 `ROW_EMAIL_INVALID` (value `not-an-email`), row 6 `ROW_NAME_MISSING`, row 7 `ROW_ROLE_NOT_ALLOWED` (value `admin`), row 8 `ROW_ROLE_UNKNOWN` (value `wizard`); a row with both an invalid email and an empty name reports both errors. Surface API+UI. Confirm API-T, E2E.
- AL-4.3 failure: `a@b`, `a b@example.com`, `@example.com` and `a@@example.com` each give `ROW_EMAIL_INVALID`; a row `,` gives `ROW_EMAIL_MISSING` and `ROW_NAME_MISSING`. Surface API. Confirm API-T.
- AL-4.4 boundary: F-email-254 accepted, F-email-255 `ROW_EMAIL_INVALID`; local part of 64 accepted, 65 refused; F-name-100 accepted, F-name-101 `ROW_NAME_INVALID`; name `"  Pat  "` is stored as `Pat`. Surface API+STORE. Confirm API-T, DB.
- AL-4.5 boundary: `ADMIN`, ` Member ` match the catalogue ignoring case and spaces (the first still `ROW_ROLE_NOT_ALLOWED`, the second accepted as `member`). Surface API. Confirm API-T.
- AL-4.6 failure (no escalation): there is no input in any column by which an import creates an admin: F-mixed row 7 refused, role cell `Admin` refused, and a `role` value containing a line break or the string `member,admin` is `ROW_ROLE_UNKNOWN`. Surface API+STORE. Confirm API-T, DB (no user with role admin besides `ada`).

Domain rules the request leaves out and this requirement bounds: email syntax, name rules, role rules, case and whitespace handling, limits. Unresolved: G-1 (exact single-create rules), G-4 (role catalogue).

### R-5 Duplicate emails

Basis: request; A-4, A-5, A-10.
Behaviour.
- Within the file, case-insensitively after trimming: the first occurrence is valid; every later occurrence gets `ROW_EMAIL_DUPLICATE_IN_FILE` naming the row of the first.
- Against existing accounts, including deactivated ones, if the product has that state: `ROW_EMAIL_EXISTS`. The message says an account already exists and gives no detail of it (no name, role or state). Existing accounts are never changed.
- A duplicate against the store is detected both by checking up front (for the report) and by the store's own uniqueness guarantee at commit (for races, R-11). If the store refuses at commit, the whole import is rejected with the same code for that row and nothing is created.
- The error report for an email that already exists is visible only to the admin who passes R-1, who can already see the user list (G-2 if tenants).

Acceptance lines
- AL-5.1 failure: F-mixed row 4 (`bob@example.com`) gives `ROW_EMAIL_EXISTS`; row 5 (`ERIN@example.com`) gives `ROW_EMAIL_DUPLICATE_IN_FILE` naming row 2; row 2 itself has no error. Surface API+UI. Confirm API-T, E2E.
- AL-5.2 positive/boundary: `Bob@Example.com ` (case and trailing space) against Seed-A is `ROW_EMAIL_EXISTS`; after an import, `bob@example.com` still has its original name, role and state. Surface API+STORE. Confirm API-T, DB.
- AL-5.3 failure: re-uploading F-valid3 after it was imported gives `ROW_EMAIL_EXISTS` on rows 2, 3 and 4 and the user count stays 6. Surface API+UI. Confirm API-T, E2E, DB.
- AL-5.4 boundary: if the product has a deactivated user `dee@example.com`, a row for it gives `ROW_EMAIL_EXISTS` and the user stays deactivated. Conditional on G-1. Surface API. Confirm API-T. Otherwise `n/a: product has no deactivated state`.

### R-6 Create the users, all or nothing

Basis: request ("bulk-create users"); A-3, A-4.
Behaviour.
- When every check in R-2 to R-5 passes and the admin is still admin at commit (R-11), exactly one user per data row is created in a single atomic step together with the audit record (R-9): after the step either all N users and the audit record exist or none does. HTTP 201.
- Each user has: email (normalized), name, role (from the file or `member`), the same initial state, credential state and timestamps as a single-create user (A-3), and a reference to the import that created it.
- No user is created by a file that has any error (A-4), and a failure after validation (store unavailable, commit error) leaves no user: 500 `IMPORT_FAILED`, "No users were created". The store must make that sentence true; if the outcome cannot be known (connection lost at commit) the response says the outcome is unknown and tells the admin to check the user list before retrying (re-upload is safe, R-11).
- Credentials: the import never sets, receives, echoes, logs or stores a password. How a created user first signs in is whatever single-create does (A-3). If the product has no such mechanism, created users hold no usable credential until one exists, and that is an open prerequisite (G-1), not something this import invents.
- Order of creation inside the batch carries no meaning.

Acceptance lines
- AL-6.1 positive: `S-ada` imports F-valid3: STORE shows 6 users; the three new ones have the fields in AL-4.1, an import reference equal to the one in the audit record, and the same initial state and credential state as a user made by single-create. Surface STORE+UI. Confirm DB, E2E.
- AL-6.2 failure: F-mixed creates nobody: count stays 3 and no `erin@example.com` exists, even though row 2 was valid. Surface STORE. Confirm DB.
- AL-6.3 failure (partial failure): with the store made to fail on the 2nd insert of F-valid3 (fault injection at the store boundary), the response is 500 `IMPORT_FAILED`, count stays 3, no audit record says "created", and no invitation is sent (R-8). Surface API+STORE+MAIL. Confirm API-T with fault injection, DB.
- AL-6.4 boundary: F-rows-1000 creates 1,000 users and one audit record; a single-row file creates one. Surface STORE. Confirm DB.
- AL-6.5 failure: no response, log line or audit record produced by any import contains a password, and F-pw is refused (AL-3.3). Surface LOG+API. Confirm LOGSCAN, API-T.

### R-7 Result reporting

Basis: request (implied: an admin must be able to tell the outcome and fix the file); A-4.
Behaviour. Every submission that reaches the server ends in exactly one of: **created**, **rejected**, **failed**, **refused** (R-1), or **disabled** (R-12). The consumer-visible response contract:

| Case | HTTP | Body |
| --- | --- | --- |
| created | 201 | `outcome:"created"`, `count`, `users:[{id,email,name,role}]` in file order |
| rejected, file level | 422 (413 for `FILE_TOO_LARGE`, 400 for `FILE_REQUIRED`) | `outcome:"rejected"`, `count:0`, `errors:[{row?,column?,code,message}]` |
| rejected, rows | 422 | as above, one entry per row error, ordered by row then column, **all** errors listed (at most 1,000 rows, so no truncation) |
| failed | 500 | `outcome:"failed"`, `code:"IMPORT_FAILED"`, text stating whether anything was created (never: "no users created" unless guaranteed) |

- `count` of created users equals the number of data rows; `users` contains no secret and no hidden field.
- The result shows the admin exactly what changed so a mistaken import can be identified (R-9 for the matching audit record). There is no undo in this version (G-8): a mistaken import is corrected through the existing user management.
- The result is the response to the submission; it is not stored for later viewing (R-10).

Acceptance lines
- AL-7.1 positive: F-valid3 returns 201, `count:3`, three `users` with ids, emails `alice@example.com`, `carol@example.com`, `dave@example.com` in that order. Surface API+UI. Confirm API-T, E2E.
- AL-7.2 failure: F-mixed returns 422 with exactly these (row, code) pairs: (3, `ROW_EMAIL_INVALID`), (4, `ROW_EMAIL_EXISTS`), (5, `ROW_EMAIL_DUPLICATE_IN_FILE`), (6, `ROW_NAME_MISSING`), (7, `ROW_ROLE_NOT_ALLOWED`), (8, `ROW_ROLE_UNKNOWN`), and `count:0`. Surface API. Confirm API-T.
- AL-7.3 failure: a file with 300 bad rows lists 300 errors (none dropped, none aggregated). Surface API+UI. Confirm API-T, E2E.
- AL-7.4 failure: the outcome shown by the UI always equals the STORE state: no "success" shown when the count is unchanged, no error shown for a commit that happened. Surface UI+STORE. Confirm E2E, DB.
- AL-7.5 boundary: error messages are readable by an admin without the spec: each names the row, the column and the rule, for example "Row 3, email: 'not-an-email' is not a valid email address." Surface UI. Confirm E2E (text assertion on the sample rows).

### R-8 Notifications to created users (conditional)

Basis: A-3 (parity with single-create).
Behaviour. If single-create sends the new user an invitation or welcome message, an import sends the same message to each created user, **after** the atomic commit of R-6 and never for a rejected or failed import. At most one message per created user per import. A failure to send does not undo the users; it is reported in the result as `notification_failures` (emails only) and logged without the address (R-9, R-10). No automatic retry in this version; the admin uses whatever resend the product already has (G-1). If single-create sends nothing, no mail is sent and the rest of this requirement is `n/a: product sends no creation mail`.

Acceptance lines
- AL-8.1 positive: after a created import of F-valid3, MAIL holds three messages, one per address, none before the commit. Conditional on G-1. Surface MAIL. Confirm DB+mail capture.
- AL-8.2 failure: for a rejected F-mixed or a failed import (AL-6.3), MAIL holds zero messages. Surface MAIL. Confirm mail capture.
- AL-8.3 failure: with the mail transport failing for `carol@example.com` only, the import still returns 201 with three users and `notification_failures` naming `carol@example.com`; no retry storm. Surface API+MAIL. Confirm API-T with fault injection.
- AL-8.4 boundary: a submit that is sent twice (R-11) yields at most one message per user. Surface MAIL. Confirm mail capture.

### R-9 Audit and observability

Basis: request (operators: "seeing what went wrong"); A-3.
Behaviour.
- Every submission that passes R-1 writes one audit record: import id, acting admin id, UTC timestamp, outcome (`created`, `rejected`, `failed`), data-row count when known, created count, error count per code. It holds no file content, no email, no name. For `created` it is written in the same atomic step as the users (R-6). For `rejected` and `failed` it is written best-effort and its own failure never changes the response.
- A refused attempt (R-1) is recorded by the product's existing security or access logging, if any; no new audit stream is invented (G-1).
- One structured log line per submission: import id, admin id, outcome, counts, error codes with counts, duration in ms, size in bytes. No file content, emails or names (R-10).
- Retention of audit records: same as the product's existing audit records; value unresolved (G-9).
- Operators can find "who imported what, when and how it ended" from the audit record, and from an import id in the result they can find the users it created.

Acceptance lines
- AL-9.1 positive: AL-6.1 leaves one audit record with outcome `created`, `count 3`, admin id of `ada`, a timestamp within the test's time window, and no email. Surface STORE. Confirm DB.
- AL-9.2 failure: F-mixed leaves one audit record with outcome `rejected` and error counts `ROW_EMAIL_INVALID:1, ROW_EMAIL_EXISTS:1, ROW_EMAIL_DUPLICATE_IN_FILE:1, ROW_NAME_MISSING:1, ROW_ROLE_NOT_ALLOWED:1, ROW_ROLE_UNKNOWN:1`. Surface STORE. Confirm DB.
- AL-9.3 failure: a 403 from `S-mia` writes no import audit record and no user. Surface STORE+LOG. Confirm DB, LOGSCAN.
- AL-9.4 boundary: a failure to write the `rejected` audit record (fault injection) still returns the same 422 and logs the audit failure. Surface API+LOG. Confirm API-T.
- AL-9.5 failure: LOG scan of all imports in this requirement's lines finds none of the emails or names from the sample files. Surface LOG. Confirm LOGSCAN.

### R-10 Privacy of uploaded data

Basis: request (files carry personal data); A-8.
Behaviour. The file and the parsed rows exist only in the memory of the request. They are not written to disk, caches, error trackers, request logs or the audit record. The response goes only to the admin who made the request, over the product's authenticated channel. Error responses include an email or role value only where R-4 allows. Where shown: the admin's page for the duration of that page view. Stored: only the created users (their purpose) and the counts in the audit record. Removed: when the request ends (file), or never by this feature (users, audit, governed by existing policy). Request-body logging by the platform, a proxy or an error tracker is turned off or redacted for the import endpoint.

Acceptance lines
- AL-10.1 positive: after F-valid3 and F-mixed, a scan of the filesystem under the application's temp and data directories finds no copy of the file. Surface STORE+LOG. Confirm filesystem scan (where the runtime allows).
- AL-10.2 failure: LOGSCAN (AL-9.5) and an error-tracker capture of a forced 500 (AL-6.3) contain no sample email. Surface LOG. Confirm LOGSCAN.
- AL-10.3 boundary: the request returned to `S-ada` is not retrievable by `S-mia` or anonymously by any id or address in the response. Surface API. Confirm API-T.

### R-11 Repeats, races and interruptions

Basis: request; A-4.
Behaviour. The unique email guarantee lives in the store, not in the check made before it, so these hold:
- The same file submitted twice (double click, retry after a timeout): the first creates; the second finds every email existing and is rejected with `ROW_EMAIL_EXISTS` for each row, creating nothing. If the first was still running, exactly one of them commits (below).
- Two imports at once with overlapping emails (F-conc-1 and F-conc-2): exactly one commits; the other is rejected whole with `ROW_EMAIL_EXISTS` for the shared row and creates nothing. Which wins is not specified.
- An import racing with the existing single-create (when it exists) for one email: exactly one succeeds.
- Admin authority is checked at the start and re-read when committing: if the admin was demoted or deactivated in between, the response is 403 and nothing is created.
- The client disconnecting, or the platform timing out, never leaves a partial import: the request either committed fully or not at all; the admin can check the user list, and re-uploading the same file is safe (it creates everyone or, if it already did, creates no one).
- The UI prevents a second submit while one is in flight (R-14), but correctness never depends on it.
- A mid-request switch-off (R-12) does not interrupt an import already past the gate; it ends atomically as usual.

Acceptance lines
- AL-11.1 failure: from Seed-A, `S-ada` submits F-valid3 twice back to back. STORE: 6 users, each of the three emails exactly once; the second response is 422 with three `ROW_EMAIL_EXISTS`. Surface API+STORE. Confirm API-T, DB.
- AL-11.2 failure: `S-ada` submits F-conc-1 and a second admin (add `gus@example.com`, admin, `S-gus`, to the seed for this line) submits F-conc-2, released together by a barrier and repeated 50 times from Seed-A each time. Each run, STORE shows exactly one of {`x1`, `shared`} or {`shared`, `y2`} created, 5 users in all, `shared@example.com` once, and the loser's response is 422 with a single `ROW_EMAIL_EXISTS` error: at row 3 if F-conc-1 lost (`x1` is row 2, `shared` row 3), at row 2 if F-conc-2 lost (`shared` is row 2, `y2` row 3). Surface API+STORE. Confirm API-T, DB.
- AL-11.3 failure: `S-ada` starts F-valid3 with a test seam pausing before commit; setup changes `ada` to `member`; the import resumes and returns 403, count stays 3. Surface API+STORE. Confirm API-T with test seam (AD-3). Setup writes the store directly; this is the only way to demote her mid-request, so the case is NOT-REPLAYED until the seam exists.
- AL-11.4 boundary: the client aborts the connection mid-upload (half a body): count stays 3 and no audit record `created` exists. Aborting after commit: users exist, audit record exists. Surface API+STORE. Confirm API-T.
- AL-11.5 failure: if single-create exists, a single-create of `shared@example.com` and the import of F-conc-1 started together leave exactly one `shared@example.com`. Conditional on G-1. Surface API+STORE. Confirm API-T, DB.

### R-12 Operator controls

Basis: request (the people who run it); A-8.
Behaviour. Deployment configuration, read at startup or on each request, provides:
- `enabled` switch (default **on**). Off for everyone: the UI entry and the page are absent, the endpoint answers 404 and does nothing, no audit record is written. Users already created are untouched. Turning it back on restores the feature with no data change.
- limits from A-8 (`max_file_bytes`, `max_rows`, `max_email_chars`, `max_name_chars`), with those defaults. A value that is not a positive integer stops start-up with a message naming the setting; a limit above what the platform allows (G-3) is also refused at start-up.
- The effective configuration is written to the log at start-up, so an operator knows the feature is on and with which limits.
- Left out and why: per-admin or per-case enablement (not requested); self-service limits in the UI (not requested).
- Going back to the version before: the feature adds an audit store and an import reference on users (R-6). Removing the code leaves them in place and unused; users created stay valid; no destructive migration is needed to roll back.

Acceptance lines
- AL-12.1 positive: with defaults, start-up logs `enabled=true` and the four limits; AL-1.1 succeeds. Surface LOG+UI. Confirm LOGSCAN, E2E.
- AL-12.2 failure: with `enabled=false`, `S-ada` sees no import entry, a direct page address and a POST both give 404, count stays 3, no audit record. Surface UI+API+STORE. Confirm E2E, API-T, DB.
- AL-12.3 boundary: `max_rows=2` refuses F-valid3 with `TOO_MANY_ROWS` stating limit 2 and count 3; `max_rows=0` or `max_rows=abc` stops start-up naming `max_rows`. Surface API+LOG. Confirm API-T.
- AL-12.4 boundary: flipping `enabled` to false while an import is in flight lets that import finish atomically; the next request gets 404. Surface API. Confirm API-T with test seam.

### R-13 Preserved behavior and prohibitions

Basis: A-2, A-3; request ("create", not "update").
Behaviour. Nothing that exists changes for people who do not use the import:
- Existing users are never created twice, modified, deactivated or deleted by an import.
- The single-user create, sign-in, role management, user list and any export behave as before. The user list shows imported users like any other.
- Never true, however built: a non-admin creates a user through the import; an import creates an admin; two users share an email; users appear for an import reported as failed or rejected; an import reported as created lacks users; a rule of single-create is enforced there but not here (or the reverse for a rule this spec adds, when it is not meant to apply there); anyone sees, through the import, a user they may not see (G-2); a password appears in a file, response, log or audit.
- If the product has a user quota or seat limit, an import that would exceed it is rejected whole with a code `USER_LIMIT_EXCEEDED` stating the free capacity; nothing is created. Unresolved whether such a limit exists (G-7); `n/a` if not.

Acceptance lines
- AL-13.1 positive: after any rejected import, STORE equals Seed-A field for field (users, roles, states). Surface STORE. Confirm DB (snapshot diff).
- AL-13.2 positive: after AL-6.1, the existing user list shows 6 users, sign-in of `mia@example.com` and single-create (if present) still work. Surface UI. Confirm E2E regression.
- AL-13.3 failure: with a quota of 5 in the seed, F-valid3 gives `USER_LIMIT_EXCEEDED` and creates nobody; with a quota of 6 it is accepted. Conditional on G-7. Surface API+STORE. Confirm API-T, DB.

### R-14 Admin import page

Basis: request ("admins upload"); A-1.
Behaviour (interaction, component and state premises, truthful async feedback). One page reachable from the admin navigation, containing:
- A heading, a short statement of the format with the example header `email,name,role`, which columns are required, the limits (rows and bytes), that rows are created together or not at all, that existing emails are refused, and that no passwords are included. The numbers come from the configured limits (R-12), not hard-coded text.
- A labelled file chooser (one file, keyboard reachable) and a primary "Import users" action that stays disabled until a file is chosen. The chosen file name and size are shown; a file over the size limit is flagged before sending, but the server's answer is authoritative.
- In flight: the file chooser and action are disabled, a status "Importing N bytes..." appears without a made-up progress percentage, announced to assistive technology. Not cancellable in this version.
- Created: a success summary ("3 users created") and a table of the created users (email, name, role), with name and email shown as plain text (HTML in `F-xss` is displayed literally, never executed). The form is reset and ready for another file.
- Rejected: a summary ("Nothing was imported. 6 problems in 5 rows.") and a table of all errors (row, column, message), reachable without scrolling the page sideways; the chosen file remains selectable for replacement.
- Failed and unknown outcome: a plain message from R-6/R-11 with the instruction to check the user list.
- Network failure before any response: "We could not confirm the result" with the same advice; never a success.
- Not signed in, not admin, disabled: R-1 and R-12 behaviours, no partial page.
- No separate template download in this version (the format is on the page); no drag-and-drop requirement.

Acceptance lines
- AL-14.1 positive: `S-ada` opens the page: it shows the format text, a disabled action, no table. Chooses F-valid3: action enabled, file name `F-valid3.csv` and its size shown. Submits: status text appears, then "3 users created" with three rows. Surface UI. Confirm E2E.
- AL-14.2 failure: F-mixed shows "Nothing was imported" with a table of six rows `(3,email)`, `(4,email)`, `(5,email)`, `(6,name)`, `(7,role)`, `(8,role)`; user list unchanged at 3. Surface UI. Confirm E2E.
- AL-14.3 failure: F-xss imported: the created-users table shows the text `<img src=x onerror=alert(1)>` literally and no script or image element from it exists in the page DOM. Surface UI. Confirm E2E (DOM query).
- AL-14.4 boundary: pressing the action twice quickly sends one request (verified by the number of requests the test server sees). Surface UI. Confirm E2E.
- AL-14.5 failure: with the network cut after the request is sent, the page shows the "could not confirm" message and no success text. Surface UI. Confirm E2E with network fault.
- AL-14.6 boundary: a 1,000-row rejected file shows all its errors in a table that scrolls vertically only; no element is wider than the viewport at 360 px or 1,280 px. Surface UI. Confirm E2E at both widths.
- AL-14.7 failure: submitting with no file chosen is impossible (action disabled), and the keyboard Enter key does not submit it. Surface UI. Confirm E2E.

## Non-functional requirements

Numbers are only given where the request, the platform or a standard supplies them. All others are unresolved and
say so; none is invented.

### R-15 Security and transport

Basis: request (personal data, privileged action); the runtime's own rules for shipping beyond a development environment.
- The page and endpoint are served only over TLS outside a development environment (plain HTTP is refused or redirected). Verification: deployment check of the environment. Development environments are exempt.
- The endpoint requires the same session authentication and request-forgery protection as the product's other state-changing admin actions (a request from another site, carrying the admin's cookies but not the protection token, is refused 403 and creates nothing). AL-15.1 (API-T, cross-origin request without the token).
- Output encoding: every value from the file shown in the page is encoded for HTML (AL-14.3). No CSV result export exists in this version, so formula-injection is `n/a`; if one is added, cells starting with `=`, `+`, `-` or `@` must be neutralized.
- Rate limiting of repeated uploads: unresolved, not requested; the file and row caps bound each request.
- Missing: confirmation that the existing product provides sessions and request-forgery protection (G-1).

### R-16 Capacity and latency

Basis: runtime's own rules; A-8, A-9. **Bound unresolved (G-3, G-5).**
- Hard limits come from the platform's request body size and request timeout. Their values are not known because the runtime is not identified. The configured file cap (R-12) must not exceed the platform's body limit including the multipart overhead; a 1,000-row valid file (under 40 KB for F-rows-1000) must finish inside the platform's request timeout.
- Memory: the process holds at most the file cap plus the parsed rows per request; reading stops at cap+1 bytes (AL-2.5).
- Numeric target for response time at 1,000 rows: **unresolved**; missing decision: the owner's latency target and the measured baseline on the real store. Observable acceptance until then: AL-6.4 completes without timeout on the target environment, and the measured time is recorded by the plan.
- Capacity under many admins at once: unresolved, not requested; correctness under concurrency is R-11.

### R-17 Interface quality, accessibility and visual direction (applies to R-14)

Basis: the request delivers a user interface; guide `platforms/ui.md#light-expressive-starting-point`.
- Visual direction. The existing product's identity is **unknown** (G-9); if one exists, the page inherits its tokens and components and this list only adds what is missing. If the page is the product's first or has no identity, it uses the guide's reference: the light Google Gemini look with Material 3 Expressive principles (airy, tonal rounded surfaces, friendly precise type, one restrained saturated accent), light by default with a dark theme selectable and following the system setting. The upload area and result summary hold the strongest visual weight; the format help is quieter. The concrete choices are an AD in `architecture.md` and checked in the rendered page.
- Visual system. One spacing scale, one type scale and one palette with light and dark values; one icon set. Observable: styles draw spacing, font size and colour from tokens (no one-off values in the page's own CSS).
- States. Designed empty (before a file is chosen), loading (in flight), success, rejected and failed states each with its own layout and text (R-14).
- Layout. Works at 360 px and 1,280 px wide with no horizontal page overflow (AL-14.6); the primary action stays reachable at narrow width.
- Accessibility. Visible keyboard focus on every control; text contrast at least 4.5:1 and control/boundary contrast at least 3:1 (WCAG 2.1 AA) in both themes; the file chooser has a programmatic label; the in-flight and result messages are announced to assistive technology (live region); the error table uses table semantics with header cells; errors are not conveyed by colour alone.
- Motion. Used only to explain a change (for example the result appearing); disabled when the user prefers reduced motion.
- Verification. E2E at both widths in both themes with an automated accessibility scan (no serious or critical violations) plus keyboard-only walk of AL-14.1 and AL-14.2; contrast measured for the tokens. Acceptance lines: AL-17.1 (scan, both themes, both widths, each state), AL-17.2 (keyboard-only completion of AL-14.1), AL-17.3 (reduced-motion setting removes transitions).

### R-18 Compatibility

Basis: request; unknown runtime.
- Supported browsers and versions: **unresolved** (G-9); default is the product's existing support list. Files from common spreadsheet programs (UTF-8 CSV with or without BOM, CRLF) are accepted (AL-2.1, AL-3.2); Excel's "CSV (Comma delimited)" ANSI export is refused as `FILE_NOT_UTF8` and the page's format help says "UTF-8".
- Semicolon-separated files (some locales) are not supported: they fail as `HEADER_MISSING_COLUMN` and the help text names the comma separator. Not a silent misparse.
- Excluded: command-line or API clients beyond what the endpoint contract in R-7 gives; no public API promise is made.

## 4. State and data assessment

| Resource | Carrier | Target identity | Effect | Before / after invariant | Authorized actor | Partial failure / recovery | Check |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Users | user store (domain records) | new users by normalized email | **insert** N | Before: no row for any file email. After: N rows, each email once, or no new rows (R-6). Existing rows untouched. | admin (R-1) | atomic step; rollback; unknown outcome handled by R-11 | AL-6.1, 6.2, 6.3, 13.1 |
| Import audit record | audit store (derived data) | import id | insert 1 per submission past R-1 | After `created`: count in audit equals users carrying the import reference | system on behalf of admin | `created` record is part of the atomic step; others best-effort | AL-9.1 to 9.4 |
| Uploaded file and parsed rows | request memory | n/a | observe only | never persisted (R-10) | admin | dies with the request | AL-10.1 |
| Admin role / session | access assignments, session | acting admin | observe, re-read at commit | role at commit decides | n/a | demotion mid-request refuses (AL-11.3) | AL-11.3 |
| Creation notification | mail transport | each created user | send after commit (conditional) | at most one per user per import | system | failure reported, no rollback | AL-8.x |
| Logs | application log | import id | write | counts and codes only | n/a | log failure never changes the response | AL-9.5 |
| Configuration | deployment config | feature | observe | read at start-up (or per request) | operator | invalid value stops start-up | AL-12.x |

Unknowns: whether users are soft-deleted or carry other attributes (G-1); whether the user store can enforce a unique normalized-email constraint and run a transaction spanning N inserts plus the audit insert (G-3: an ordinary relational store can; unknown here). If it cannot be made atomic, the all-or-nothing rule (A-4) is not achievable as written and the owner must choose another rule before R-6 is ready.

## 5. Service boundaries (verifiable contracts)

- **User store (authority for users and for the admin role).** Current authority: the store is read for the admin role at commit and holds the unique-email guarantee. Freshness versus revocation: no admin role is cached beyond one request; a demotion takes effect on the next import and, at the latest, at an in-flight import's commit. Incremental state: not applicable; each import is one atomic write. Async completion: none (A-9). Recovery: atomic step; unknown outcome handled by checking the user list.
- **Session/identity layer (existing).** Contract: produces the acting admin id and, if it carries a role claim, that claim is advisory only (R-1). Cache and revocation: see above.
- **Mail transport (existing, conditional, R-8).** Async after commit; failures are reported, not retried; the transport's own duplicates are not suppressed here (one send per user per import is what the product guarantees). Owned event coverage: send success and failure counts in the import log line.
- **Owned events.** Per submission one log line and one audit record (R-9). Authentication success and failure reuse the existing sign-in logging (no new provider event). Sink failure is non-fatal and logged.
- Not applicable, one line each: caches (none introduced), queues or workers (none, A-9), webhooks and outbound calls other than mail (none), notifications to the admin beyond the on-page result (none).

## 6. Flows, states and transitions

### F-1 Successful import (R-1 to R-9, R-11, R-14)

```mermaid
sequenceDiagram
  participant A as Admin (browser)
  participant S as Import endpoint
  participant D as User + audit store
  participant M as Mail transport
  A->>S: POST file (session, anti-forgery token)
  S->>S: T-1 authorize admin (R-1), enabled (R-12)
  S->>S: T-2 read <= cap, UTF-8, parse, header, rows (R-2..R-5)
  S->>D: T-3 begin; re-read admin role; insert N users + audit; commit
  D-->>S: committed (or unique violation / error)
  S-->>A: 201 created, count, users
  S->>M: T-4 notifications after commit (conditional)
```

### F-2 Rejected import: same as F-1 up to T-2; any problem ends in 422/413/400 with all errors, no store write except the best-effort audit record (T-5).
### F-3 Raced or failed import: store raises a unique violation or error at T-3; transaction rolls back; 422 `ROW_EMAIL_EXISTS` for the clashing rows, or 500 `IMPORT_FAILED` (T-6).

### States

Import attempt (transient, owned by the request; its outcome is the audit record): `Received` (initial) → `Authorized` → `Validated` → `Committed` (terminal) | `Rejected` (terminal) | `Failed` (terminal) | `Refused` (terminal, from `Received`) | `Disabled` (terminal, from `Received`). Invariant: only `Committed` has created users, and `Committed` has created exactly N.
User (existing entity, new entry path): an imported user starts in the same initial state as a single-create user (A-3, G-1). The import never moves an existing user between states.

### Transition ledger

| ID | R / F | Before | Trigger and guard | Operation | After and observation | Failure and recovery | Cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-1 | R-1, R-12 / F-1 | Received | POST; guard: enabled, session valid, role admin | check | Authorized, or `Refused` (401/403), or `Disabled` (404); no store write | none needed | AL-1.2, 1.3, 12.2 |
| T-2 | R-2 to R-5 / F-1, F-2 | Authorized | file bytes; guards by order: size, non-empty, UTF-8, CSV, header, row count, row rules, duplicates | parse and validate in memory | Validated, or Rejected with all errors (413/422/400) | file errors stop at first stage; row errors all collected | AL-2.x to 5.x |
| T-3 | R-6, R-11 / F-1, F-3 | Validated | begin commit; guards: admin role still held, unique emails, quota (G-7) | insert N users + audit, commit | Committed (201); users and audit exist together | unique violation → Rejected; role lost → Refused 403; other error → Failed 500; all roll back | AL-6.x, 11.x |
| T-4 | R-8 / F-1 | Committed | after commit; conditional | send mail per user | notification_failures listed | failures reported, no rollback | AL-8.x |
| T-5 | R-9 / F-2 | Rejected or Failed | outcome known | write audit best-effort | audit record `rejected` or `failed` | write failure logged, response unchanged | AL-9.2, 9.4 |
| T-6 | R-6, R-11 / F-3 | Validated | store error at T-3 | rollback | Failed; nothing created | admin checks list; re-upload safe | AL-6.3, 11.4 |

Invalid or repeated events: a repeat POST of an already committed file → `ROW_EMAIL_EXISTS` for every row, no effect (AL-11.1); an abort before commit → nothing; an abort after commit → committed.

## 7. Open gaps and decisions needed

Gaps keep dependent work unready; independent work may proceed.

| ID | Gap | Blocks | Default used meanwhile |
| --- | --- | --- | --- |
| G-1 | Existing product facts unknown: single-create's fields, validation, normalization, default role, initial state, credential bootstrap (invitation or password set), notification, audit, soft-delete, sessions and request-forgery protection. | R-4 exact rules, R-6 user fields, R-8, R-13 | A-2, A-3, A-10, A-11 |
| G-2 | Tenancy: if users belong to an organization, imports create users only in the acting admin's organization and existence checks must not reveal other organizations' users. | R-1, R-5, R-13 | single-tenant (A-6) |
| G-3 | Runtime and platform unidentified: request body cap, request timeout, transaction support in the store. | R-2, R-6, R-12, R-16 | limits as A-8; synchronous (A-9) |
| G-4 | The role catalogue and which roles an import may grant. | R-4 | `member` default; only non-admin roles (A-7, A-11) |
| G-5 | Owner confirmation of limit values (1 MiB, 1,000 rows, 254/64, 100). | R-2, R-3, R-4, R-16 | A-8 |
| G-6 | Product decision on all-or-nothing versus creating valid rows, and on existing email as error versus skip. | R-5, R-6, R-7 | A-4, A-5 |
| G-7 | Whether a user quota or seat limit exists. | R-13 | none assumed |
| G-8 | Whether a bulk undo of a mistaken import is wanted. Out of scope now. | none | corrected via existing user management |
| G-9 | Existing visual identity, supported browsers, audit retention period. | R-9, R-17, R-18 | guide's light expressive starting point; product's existing lists |

A material conflict: none found between requirements. G-6 is the one product decision that, if reversed, rewrites R-5, R-6 and R-7.

## 8. Traceability

| Outcome | Requirements | Acceptance lines (first and key) |
| --- | --- | --- |
| O-1 upload | R-1, R-2, R-14 | AL-1.1, 2.1, 14.1 |
| O-2 admins only | R-1, R-11, R-13 | AL-1.2 to 1.5, 11.3 |
| O-3 rows read as users | R-3, R-4, R-5 | AL-3.1 to 5.4 |
| O-4 created in bulk | R-6, R-8, R-13 | AL-6.1, 6.4, 8.1 |
| O-5 know what happened | R-7, R-14 | AL-7.1 to 7.5, 14.2 |
| O-6 operators | R-9, R-10, R-12 | AL-9.x, 10.x, 12.x |

Prompt-to-outcome check: every R-n above has acceptance lines or a stated `n/a`. Features not in the request were left out: template download, drag-and-drop, background jobs, import history page, undo, per-admin switches, CSV result export, rate limiting.

## 9. Replay record

Walk of ordered cases from their stated start (reachability, permission of each action, observer):

- P-1 (AL-6.1/7.1): start Seed-A; `S-ada` is a seeded signed-in admin (start reachable by setup); R-1 permits her POST; R-2 to R-5 pass for F-valid3 (hand-checked: header `email,name,role`; 3 records; emails distinct and not in Seed-A; roles `member`, empty, `member`); T-3 commits; observer STORE sees 3 + 3 = 6. Recomputed: 201, count 3.
- P-2 (AL-5.3/11.1): after P-1, the same POST is permitted (no rule limits repeats); every email exists; result rows 2, 3, 4 `ROW_EMAIL_EXISTS`; count stays 6.
- P-3 (AL-7.2): from Seed-A, F-mixed: row 2 valid; row 3 invalid email; row 4 `bob` exists; row 5 `ERIN@...` duplicates row 2; row 6 empty name; row 7 role `admin`; row 8 role `wizard`. Six errors on six rows, count 0 created.
- P-4 (AL-3.6): F-multiline records: header (1), `jo` with name containing a line break (2), `bad-email` (3); the final empty line is ignored. Errors: row 2 name, row 3 email.
- P-5 (AL-2.3): F-size-cap = 31 content bytes + 1,048,545 `\n` bytes = 1,048,576; blank lines are ignored so one valid row remains. F-email-254 domain length 63 + 1 + 63 + 1 + 57 + 4 = 189, plus 64 + 1 = 254.
- P-6 (AL-11.2): reachable only if a second admin is added to the seed (done in the line); with `S-gus` both submissions pass R-1. Whichever commits first leaves 3 + 2 = 5 users, and the other finds `shared@example.com` existing. The check is an invariant over both orders, so the winner is not predicted.
- P-7 (AL-11.3): needs a test seam that pauses before commit; **NOT-REPLAYED: seam does not exist, so the case stays open**.
- Machine replay: a local reference script applying these rules to the sample files was written, but running it was not permitted in this environment. Every expected result above is therefore **hand-derived, NOT-REPLAYED by machine**, and none is claimed as executed. No command is documented in this spec, so no command-exit record is needed. No test or product code exists; every acceptance line is a plan, not an observation.
- Weaker-stand-in check: each failure line names exact codes and rows (AL-7.2, AL-9.2), and the store state is checked (a status code alone would not pass them); a hardcoded `201` would not pass AL-6.1 because it also checks the stored fields.
- Platform claims that decisions rest on (a relational store with a transaction and a unique index can do R-6; platforms cap request bodies and time) are general facts and are **unverified here** with no primary-source probe; G-3 holds them open and AD-1 names them.

## Retired

None. (First version; no earlier R-n existed.)

## Submission

summary: First specification for "Let admins upload a CSV to bulk-create users." No repository, discovery, research or earlier spec existed, so the product's current behaviour is unknown, and the spec is built from the request plus recorded assumptions. Eighteen requirements (R-1 to R-14 functional, R-15 to R-18 non-functional), flows F-1 to F-3 and transitions T-1 to T-6. Assumptions taken as defaults (A-1 to A-11): web app with admin page and HTTP endpoint; import must match single-create in every rule (parity); all-or-nothing import with every error reported; existing email is a row error; admin role cannot be imported; row limit 1,000, file limit 1 MiB, email 254/64, name 100; synchronous request; `member` default role; a feature switch defaulting on. Open gaps (G-1 to G-9) hold dependent work unready: the existing single-create rules and credential bootstrap (G-1), tenancy (G-2), runtime limits and transaction support (G-3), role catalogue (G-4), owner confirmation of limits (G-5), the all-or-nothing and skip decisions (G-6), quota (G-7), bulk undo (G-8), visual identity, browser list and audit retention (G-9). The latency bound is unresolved, none was invented. No material requirement conflict found. All expected results were hand-derived; the local reference script could not be run, and one case (AL-11.3) needs a test seam that does not exist, so both are marked NOT-REPLAYED. `backchain-check` does not exist here and was not run (duty 11 left out). No product code and no tests written.

primary: R-1, R-2, R-3, R-6, R-14

evidence_refs: KNOWLEDGE/spec.md (sections 0 to 10, R-1 to R-18), KNOWLEDGE/architecture.md (AD-1 to AD-4), the request text of 2026-11-21, GUIDES/behavioral-requirements.md (Behavior model, Traceability and review, Actors channels and state ownership), GUIDES/requirements-definition.md, GUIDES/service-discovery.md (Verification), GUIDES/current-system-baseline.md (Planning and review handoff), GUIDES/platforms/ui.md (Light expressive starting point).
