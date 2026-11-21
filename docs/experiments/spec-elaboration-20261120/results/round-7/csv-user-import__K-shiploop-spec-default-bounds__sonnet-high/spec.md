# User administration: product specification

Maintained requirements for the product's user-administration area. First increment: **bulk user import from CSV**.
Structure and technology decisions are AD-<n> in `architecture.md ## Decisions`; this file holds behaviour only.

## Basis and evidence limits

- **Request (2026-11-21):** "Let admins upload a CSV to bulk-create users." This is the only instruction; every
  requirement below traces to it or to a recorded assumption (A-<n>) filling a choice the request leaves open.
- **Baseline:** none. This stage ran alone: no repository, discovery or research result, earlier spec or selected
  baseline existed. The product is therefore treated as having no recorded user-administration requirements
  (nothing to preserve, nothing retired). Facts about the existing product (sign-in, roles, user schema, audit
  facility, runtime limits) are **unknown**, not observed. They are carried as assumptions A-1, A-2, A-9 and open
  gaps G-2, G-3, never as evidence. Unavailable inspection does not establish absence.
- **Guides applied:** behavior-model, traceability, requirements-definition (incl. state and data assessment),
  service-discovery (asynchronous, authorization, observability, verification), interaction-design, UI
  visual-direction (light expressive starting point).

## Assumptions (defaults for choices the request leaves open)

Unattended run: each is the best default, recorded so the requester can overturn it. Changing one changes only the
clauses that cite it.

| ID | Assumption | Cited by |
|---|---|---|
| A-1 | The product is a web application with existing sign-in, a user store, role-based access and an "admin" role. Not inspected. | R-1, R-8, R-10 |
| A-2 | Roles are exactly `member` and `admin`; the default for a new user is `member`. If the real role set differs, only A-2 and the R-6 values change. | R-6 |
| A-3 | CSV columns: `email` (required), `name` (required), `role` (optional). No other attributes are importable. | R-3 |
| A-4 | Limits: file at most **1,048,576 bytes (1 MiB)**; at most **1,000** data rows; email at most **254** characters; name 1 to **100** Unicode code points. These are product defaults chosen for an admin-sized batch, not platform limits; platform limits are gap G-3. | R-2, R-4, R-5 |
| A-5 | All-or-nothing: if any row is invalid or conflicts, no user is created and the admin gets the complete list of problems. | R-8 |
| A-6 | Email identity is the trimmed, lower-cased address; uniqueness is global across all users regardless of status. | R-7 |
| A-7 | The CSV carries no secrets. Created users have **no credential** and the product's existing "not yet activated / invited" state (the value `invited` is introduced if none exists). The feature sends **no email**. See G-1. | R-8 |
| A-8 | Import is synchronous within one request (AD-1). | R-8, R-9 |
| A-9 | Audit events go to the product's primary datastore, in the same transaction as the users (AD-2); retention follows the product's existing audit-retention policy, none is added here. | R-11 |
| A-10 | Any admin may create `admin` users through the CSV; there is no separate "can import" permission. See G-4. | R-1, R-6 |
| A-11 | Input is UTF-8 (optional BOM), comma-delimited. No delimiter or encoding auto-detection; spreadsheet "CSV (semicolon)" exports are rejected with the normal errors. | R-3, NFR-8 |
| A-12 | Row numbers are record positions in the file, counting blank records, so the header is normally row 1 and numbers match a spreadsheet view. | R-3, R-9 |
| A-13 | File extension and declared MIME type are not checked; content alone decides. | R-2 |
| A-14 | Messages are English only; no localisation. | R-9, R-10 |
| A-15 | The UI follows the product's existing identity if one exists; otherwise the light expressive starting point applies (NFR-6). | R-10, NFR-6 |

## Fixtures and seed state (concrete inputs for every acceptance line)

**Seed state S0** (4 users): `admin1@example.com` (admin, the acting admin, id referred to as ADMIN1),
`admin2@example.com` (admin), `member1@example.com` (member), `taken@example.com` (member, name "Existing Taken").
Sessions exist for admin1, admin2 and member1; "no session" means a request with no credentials. Unless a line says
otherwise, each acceptance line starts from S0. "N users" means the total in the user store.

Fixture files (LF endings unless stated; `⏎` shows nothing, content is literal):

- **FX-1** `valid3.csv` (119 bytes):
  `email,name,role` / `ada@example.com,Ada Lovelace,member` / `grace@example.com,Grace Hopper,admin` /
  `alan@example.com,Alan Turing,` (third role cell empty), each line ending LF.
- **FX-2** (UTF-8 BOM, CRLF endings, spaced and mixed-case): header ` Email , NAME ,Role`; one row
  `  Mixed.Case@Example.COM  , Mary Jane ,MEMBER`.
- **FX-3** `invalid-rows.csv`: header `email,name,role`; rows (header = row 1):
  r2 `not-an-email,Bad Email,member`; r3 `ok1@example.com,,member`; r4 `ok2@example.com,Okay Two,superuser`;
  r5 `taken@example.com,Dup Existing,member`; r6 `dup@example.com,First Dup,member`;
  r7 `DUP@example.com,Second Dup,member`.
- **FX-S1** (size boundary, accepted): the 61-byte text `email,name` / `sz1@example.com,Size One` /
  `sz2@example.com,Size Two` (each line LF), followed by 1,048,515 extra LF bytes: total **1,048,576** bytes.
- **FX-S2**: FX-S1 plus one more LF: **1,048,577** bytes.
- **FX-R1**: header `email,name` and 1,000 rows `user0001@example.com,User 0001` ... `user1000@example.com,User 1000`.
- **FX-R2**: as FX-R1 with 1,001 rows (`user1001@example.com,User 1001` added).
- **FX-R3**: header `email,name` and 1,000 rows each `bad,Name N` (N = 1..1000).
- **FX-MIN**: `email,name` / `solo@example.com,Solo`.
- **FX-Q**: `email,name` / `q@example.com,"Hopper, Grace ""Amazing"""`.
- **FX-ORD**: header `name,email` / `Zoë 山田,zoe@example.com`.
- **FX-H1** `email,role` / `x@example.com,member`. **FX-H2** `email,name,phone` / `x@example.com,X,1`.
  **FX-H3** `email,name,Email` / `x@example.com,X,y@example.com`. **FX-H4** `email,phone` / `x@example.com,1`.
  **FX-H5** header `email,name,role` only (no rows). **FX-H6** zero bytes. **FX-H7** three LF bytes only.
- **FX-E1** (invalid UTF-8): bytes of `email,name` LF `x@example.com,` then `0xFF 0xFE` then LF.
- **FX-M1** (unterminated quote): `email,name` / `x@example.com,"unterminated` LF.
- **FX-W1**: `email,name` / `x@example.com` / `y@example.com,Y,extra`.
- **FX-B1**: `email,name` / (blank line) / `a1@example.com,A One` / (blank line) / `bad,B Two`.
- **FX-B2**: `email,name` / `q@example.com,"Line1` LF `Line2"` / `bad,B` (the second record spans two physical lines).
- **FX-X1**: `email,name,<img src=x onerror=alert(1)>` / `x@example.com,X,1`.
- **FX-U1**: `email,name` / `x@@example.com,A` / `x@@example.com,B`.
- **FX-D3**: `email,name` / `rep@example.com,One` / `rep@example.com,Two` / `Rep@example.com,Three`.
- **FX-C1**: `email,name` / `race@example.com,Race A` / `only-a@example.com,Only A`.
  **FX-C2**: `email,name` / `race@example.com,Race B` / `only-b@example.com,Only B`.
- **FX-P1**: `email,name` / `marker@example.com,PRIVACY-MARKER-7f3a`.
- **FX-EMAIL254**: `email,name` / `a@` + 248 `d` + `.com` (254 chars) `,N`. **FX-EMAIL255**: same with 249 `d` (255 chars).
- **FX-NAME100**: `email,name` / `n1@example.com,` + 100 `N`. **FX-NAME101**: same with 101 `N`.

**Error codes and exact messages** (row-level errors never echo cell values; `row` is the A-12 row number):

| Code | HTTP | Level | Message |
|---|---|---|---|
| `invalid_upload` | 400 | file | Upload exactly one file in the 'file' field. |
| `file_too_large` | 413 | file | The file is larger than 1 MiB. |
| `file_empty` | 422 | file | The file is empty. |
| `invalid_encoding` | 422 | file | The file is not valid UTF-8 text. |
| `malformed_csv` | 422 | file | The file is not valid CSV. |
| `no_data_rows` | 422 | file | The file has a header but no users. |
| `too_many_rows` | 422 | file | The file has more than 1,000 users. |
| `missing_column` | 422 | header (`column` = missing name) | Required column is missing. |
| `unknown_column` | 422 | header (`column` = trimmed header text, first 100 chars) | Column is not recognized. Allowed columns: email, name, role. |
| `duplicate_column` | 422 | header (`column` = normalized name) | Column appears more than once. |
| `wrong_field_count` | 422 | row (`column` null) | Row has a different number of fields than the header. |
| `invalid_email` | 422 | row, `email` | Email address is not valid. |
| `already_exists` | 422 | row, `email` | A user with this email already exists. |
| `duplicate_in_file` | 422 | row, `email`, plus `first_row` | Email repeats an earlier row. |
| `name_required` | 422 | row, `name` | Name is required. |
| `name_too_long` | 422 | row, `name` | Name must be at most 100 characters. |
| `name_invalid_characters` | 422 | row, `name` | Name must not contain control characters. |
| `invalid_role` | 422 | row, `role` | Role must be member or admin, or left blank for member. |
| `forbidden` | 403 | file | You do not have permission to import users. |
| `internal_error` | 500 | file | The import could not be completed. Check the user list before retrying. |

Surfaces used in acceptance lines: **API** = HTTP client against the AD-3 endpoint; **UI** = the admin page in a real
browser; **DB** = test-harness read of the user and audit stores; **LOG** = captured application logs.

## Processing order (gates)

An import attempt passes these gates in order and stops at the first gate that fails (header errors and row errors
are each *collected* within their gate):
G1 authenticated (401) -> G2 current role is admin (403 `forbidden`) -> G3 exactly one `file` part (400) ->
G4 size at most 1,048,576 bytes (413) -> G5 UTF-8 decodes, parses as CSV, has a non-blank record (422 file-level) ->
G6 header valid (422, all header errors together) -> G7 at most 1,000 non-blank data rows (422) ->
G8 every row valid, no in-file or existing-email duplicates (422, **all** row errors together) ->
G9 one atomic commit (201), or conflict on commit (422 `already_exists` rows), or datastore failure (500).

## Requirements

### R-1: Only admins can import users
- **Behaviour:** the import page and endpoint are available only to an authenticated user whose *current* role is
  admin (A-1, A-10). Authorization is decided per request from the current stored role. A rejected caller creates
  nothing, and the rejection reveals nothing about existing users (the file is not read or parsed).
- **Boundaries / errors:** unauthenticated 401; non-admin 403 `forbidden`; an admin demoted after loading the page is
  rejected on submit (revocation takes effect without a new sign-in).
- **Consumer outcome:** admins can import; everyone else cannot and cannot probe which emails exist.
- **Basis:** request 2026-11-21 "Let admins ..."; A-1, A-10. Added; nothing preserved. Evidence limit: sign-in and
  role mechanism not inspected (G-2).
- **AC-1.1 positive:** admin1 POSTs FX-1 -> 201 (not 401/403). [API; automated API test with admin1's session]
- **AC-1.2 failure (unauthenticated):** no credentials, FX-1 -> 401; DB still 4 users. [API; automated; DB count]
- **AC-1.3 failure (non-admin, no leak):** member1 POSTs FX-1 and, separately, FX-3 (which contains
  `taken@example.com`) -> both 403 with the identical body `errors: [{row:null, column:null, code:"forbidden",
  message:<table>}]`; DB 4 users. Identical bodies prove no existence signal. [API; automated; DB count]
- **AC-1.4 boundary (revocation):** admin2 loads the import page; the harness then sets admin2's stored role to
  `member`; admin2 submits FX-1 -> 403, DB 4 users. Walk: admin2 can sign in in S0; the page is reachable while admin;
  the role change is a harness write to the store (not a product action); the submit is checked against the stored
  role (AD-3), so 403 is recomputed. **NOT-REPLAYED:** no implementation exists here. [API/UI; automated]
- **AC-1.5 UI visibility:** admin1 sees an "Import users" entry in the admin area; member1 sees none and, navigating
  directly to the import page, gets the product's forbidden state, not the form. [UI; automated browser test]

### R-2: File intake and limits
- **Behaviour:** exactly one file in the `file` part; at most 1,048,576 bytes; UTF-8 with optional BOM; at most 1,000
  non-blank data rows; not empty. Extension/MIME ignored (A-13). The size cap is enforced while reading (AD-4).
- **Boundaries:** 1,048,576 accepted, 1,048,577 rejected; 1,000 rows accepted, 1,001 rejected; blank records are not
  counted toward 1,000 but are counted for row numbers (A-12). A platform limit lower than these is gap G-3.
- **Errors:** `invalid_upload` 400, `file_too_large` 413, `file_empty`/`invalid_encoding`/`too_many_rows` 422.
- **Basis:** request "upload a CSV"; A-4, A-11, A-13. Added. Limits are defaults (A-4), not requested values.
- **AC-2.1 positive + boundary (size):** admin1 POSTs FX-S1 (1,048,576 bytes) -> 201, `created` 2, DB 6 users
  (`sz1@example.com`, `sz2@example.com` added). [API; automated; byte length asserted equal to 1,048,576 in the test]
- **AC-2.2 boundary (size over):** FX-S2 (1,048,577 bytes) -> 413 `file_too_large`; DB 4 users. [API; automated]
- **AC-2.3 failure (upload shape):** a multipart request with no `file` part, one with the part named `upload`, and
  one with two `file` parts -> each 400 `invalid_upload`; DB 4 users. [API; automated]
- **AC-2.4 failure (empty):** FX-H6 (zero bytes) and FX-H7 (three LF bytes) -> 422 `file_empty`, `row` null. [API]
- **AC-2.5 failure (encoding):** FX-E1 -> 422 `invalid_encoding`; DB 4 users. [API]
- **AC-2.6 positive (BOM):** FX-2 -> 201; the BOM is not part of the first header name (see AC-3.2). [API]
- **AC-2.7 boundary (rows):** FX-R1 -> 201, `created` 1000, DB 1,004 users. FX-R2 -> 422, exactly one error
  `too_many_rows`, DB 4 users. FX-B1's blank records do not count toward 1,000 (n/a as a separate case: covered by
  AC-3.9 numbering). [API; automated; DB count]
- **AC-2.8 positive (extension/MIME ignored):** FX-1 sent as `users.txt` with content type
  `application/octet-stream` -> 201. [API]
- **AC-2.9 failure (oversized stream):** a 20 MiB body is answered 413 and the handler's counted bytes read do not
  exceed 1,048,576 plus one read chunk (AD-4); DB 4 users. [API with a counting stream; automated]

### R-3: CSV structure and header contract
- **Behaviour:** comma-delimited, `"` quoting with `""` escape, quoted fields may hold commas and newlines, LF or CRLF
  records, optional final newline. The header is the first non-blank record; names are trimmed and case-insensitive;
  `email` and `name` required, `role` optional, any order; unknown and duplicate columns rejected. Every non-blank
  data record must have exactly the header's field count. Fields are trimmed. Records whose fields are all empty are
  skipped. Row numbers per A-12. Header errors are reported together, in the order missing (email, name), unknown
  (file order), duplicate (file order of first occurrence).
- **Boundaries / errors:** `missing_column`, `unknown_column`, `duplicate_column` (row = header's row number);
  `no_data_rows`; `malformed_csv`; `wrong_field_count` (row-level, other checks for that row skipped).
- **Basis:** request "upload a CSV"; A-3, A-11, A-12. Added. Left out: other delimiters, `.xlsx`, auto-detection.
- **AC-3.1 positive:** FX-1 -> 201; users per AC-8.1 (blank role cell yields `member`). [API]
- **AC-3.2 positive (tolerance):** FX-2 -> 201; the stored user is email `mixed.case@example.com`, name
  `Mary Jane`, role `member`. [API; DB read of the stored fields]
- **AC-3.3 positive (quoting):** FX-Q -> 201; stored name is exactly `Hopper, Grace "Amazing"`. [API; DB read]
- **AC-3.4 positive (column order):** FX-ORD -> 201; stored name `Zoë 山田`, email `zoe@example.com`. [API; DB read]
- **AC-3.5 failure (header):** FX-H1 -> 422 `[{row:1, column:"name", code:"missing_column"}]`; FX-H2 ->
  `[{row:1, column:"phone", code:"unknown_column"}]`; FX-H3 -> `[{row:1, column:"email", code:"duplicate_column"}]`;
  FX-H4 -> two errors in order `[{row:1, column:"name", code:"missing_column"}, {row:1, column:"phone",
  code:"unknown_column"}]`. DB 4 users in each case. [API; automated; exact-array assertion]
- **AC-3.6 failure (no rows):** FX-H5 -> 422 `[{row:null, column:null, code:"no_data_rows"}]`. [API]
- **AC-3.7 failure (malformed):** FX-M1 -> 422 `[{row:null, column:null, code:"malformed_csv"}]`. [API]
- **AC-3.8 failure (field count):** FX-W1 -> 422 `[{row:2, column:null, code:"wrong_field_count"}, {row:3,
  column:null, code:"wrong_field_count"}]`. [API]
- **AC-3.9 boundary (row numbering):** FX-B1 -> 422 `[{row:5, column:"email", code:"invalid_email"}]` (blank
  records at rows 2 and 4 are skipped but counted; `a1@example.com` at row 3 is valid). FX-B2 -> 422
  `[{row:2, column:"name", code:"name_invalid_characters"}, {row:3, column:"email", code:"invalid_email"}]` (the
  multi-line quoted record is one row, so `bad` is row 3). [API; automated; exact-array assertion]

### R-4: Email validation
- **Behaviour:** after trimming: at most 254 characters, only ASCII printable characters (U+0021 to U+007E), exactly
  one `@`, non-empty local part, domain containing at least one `.` and no empty label. Syntax only; deliverability
  is not checked. Internationalised addresses must be supplied in ASCII (punycode) form (A-4 default).
- **Basis:** request (users need an identity); A-4, A-6. Added. Left out: MX/deliverability checks, verification mail.
- **AC-4.1 positive:** `  x@example.com ` (surrounding spaces) is accepted and stored `x@example.com`. [API; DB]
- **AC-4.2 failure:** each of `not-an-email`, `a@b`, `@example.com`, `a@@example.com`, `a b@example.com`,
  `a@example..com`, `a@example.com.`, `ünï@example.com`, and an empty cell, as the email of a single-row file, -> 422
  with exactly one error `{row:2, column:"email", code:"invalid_email"}`. [API; automated table-driven]
- **AC-4.3 boundary:** FX-EMAIL254 -> 201; FX-EMAIL255 -> 422 `invalid_email` at row 2. [API]

### R-5: Name validation
- **Behaviour:** after trimming: 1 to 100 Unicode code points (a combining sequence counts per code point); no control
  characters (U+0000 to U+001F, U+007F, which includes tab and newline); any other Unicode is allowed.
- **Basis:** request (users need a display name); A-4. Added. Left out: Unicode normalisation; neutralising spreadsheet
  formula prefixes (`=`, `+`, `-`, `@`). Names are stored verbatim; any future CSV export must neutralise them.
- **AC-5.1 positive:** FX-ORD name `Zoë 山田` accepted (AC-3.4); FX-NAME100 -> 201. [API]
- **AC-5.2 failure:** empty name (`n2@example.com,`) -> `name_required`; a name containing a tab ->
  `name_invalid_characters`; each reported at row 2, column `name`. [API; automated]
- **AC-5.3 boundary:** FX-NAME101 -> 422 `[{row:2, column:"name", code:"name_too_long"}]`. [API]

### R-6: Role validation and default
- **Behaviour:** optional `role` column; value trimmed, compared case-insensitively to `member` and `admin` (A-2); an
  empty or whitespace-only cell, or an absent column, means `member`. Any other value is `invalid_role`.
- **Basis:** request "bulk-create users" (users need a role); A-2, A-10. Added. Open: G-2 (role set), G-4 (admin via CSV).
  Left out: groups, per-row permissions, other attributes.
- **AC-6.1 positive:** FX-1 yields ada `member`, grace `admin`, alan `member`; FX-2 `MEMBER` yields `member`; a file
  without a `role` column (FX-MIN) yields `member`. [API; DB]
- **AC-6.2 failure:** `superuser` (FX-3 row 4) -> `{row:4, column:"role", code:"invalid_role"}`. [API]
- **AC-6.3 boundary:** a cell holding only spaces -> `member`. Case variants (`Admin`, `ADMIN`) -> `admin`. [API; DB]

### R-7: Email uniqueness (in the file, against existing users, under concurrency)
- **Behaviour:** identity is the trimmed lower-cased email (A-6). A row whose email matches an existing user is
  `already_exists`. Among rows whose email is syntactically valid, the first occurrence stands; each later occurrence
  is `duplicate_in_file` with `first_row`. A row can carry both `already_exists` and `duplicate_in_file`. A row with an
  invalid email takes part in no duplicate checks. At commit, the store's unique constraint decides races (AD-2): the
  losing import creates nothing and reports `already_exists` for the rows that conflict with committed users.
- **State and data:** resource = user store (insert-only); target identity = normalized email; before: N users with
  distinct normalized emails; after: N + k (success) or N (any rejection); invariant: no two users share a normalized
  email. Recovery: nothing to repair after a rejection or a rolled-back commit; unknown outcome handled by AC-8.5.
  Unknown: whether the real store already enforces case-insensitive uniqueness (G-2).
- **Basis:** request "bulk-create users"; A-5, A-6. Added. Left out: updating or skipping existing users (upsert).
- **AC-7.1 failure (existing and in-file):** FX-3 -> 422 with exactly these five errors in this order:
  `{row:2, email, invalid_email}`, `{row:3, name, name_required}`, `{row:4, role, invalid_role}`,
  `{row:5, email, already_exists}`, `{row:7, email, duplicate_in_file, first_row:6}`. (Row 6 is the valid first
  occurrence and has no error.) DB 4 users. [API; exact-array assertion]
- **AC-7.2 failure (case):** a row `Taken@Example.com,T` -> `already_exists`. [API]
- **AC-7.3 boundary (three occurrences):** FX-D3 -> 422 `[{row:3, email, duplicate_in_file, first_row:2},
  {row:4, email, duplicate_in_file, first_row:2}]`. [API]
- **AC-7.4 boundary (invalid first occurrence):** FX-U1 -> 422 two `invalid_email` errors (rows 2, 3), no
  `duplicate_in_file`. [API]
- **AC-7.5 concurrency:** admin1 POSTs FX-C1 and admin2 POSTs FX-C2 concurrently, with a harness barrier so both pass
  G8 before either commits. Expected: exactly one 201 and one 422; the 422 body is `[{row:2, email,
  already_exists}]` (race@example.com is row 2 of both files); the user store holds exactly one
  `race@example.com`; total users 6; of `only-a@example.com` and `only-b@example.com` only the winner's exists.
  Walk: both admins exist in S0 and pass G1/G2; the first commit adds 2 users; the second commit violates the unique
  constraint on row 2 and rolls back, so its `only-*` row is not kept. **NOT-REPLAYED:** needs the implementation
  and a commit-time barrier seam (plan item). [API; automated with barrier; DB]
- **AC-7.6 (conditional):** if the product has deactivated or soft-deleted users, a row matching one is
  `already_exists`; seed one such user in the test. **Unresolved:** whether the concept exists (G-2).

### R-8: Atomic creation and the created record
- **Behaviour:** when G1 to G8 pass, all rows become users in **one atomic commit** together with the audit event
  (R-11); otherwise no row becomes a user. Each created user has: normalized email, trimmed name, role (R-6),
  no credential, the product's not-yet-activated state (A-7), `created_by` = the acting admin, a creation time.
  The import sends no email and sets no password.
- **Errors / recovery:** any failure before or during the commit (validation, conflict, datastore or audit-write
  error) leaves zero new users. If the response is lost after a successful commit the outcome is unknown to the client;
  recovery is re-upload, which fails safely with `already_exists` for every row (R-7, AC-8.5). After a commit there is
  no undo in this feature (left out).
- **State and data:** resources = user store (insert), audit store (insert); actor = admin per R-1; before/after and
  invariants as R-7; partial-failure rule = rollback of the single transaction (AD-2).
- **Basis:** request "bulk-create users"; A-5, A-7, A-8, A-9. Added. Open: G-1 (how created users obtain a
  credential), G-2 (user schema). Left out: invitation email, password setup, welcome messages, background import.
- **AC-8.1 positive:** admin1 POSTs FX-1 -> 201; DB 7 users; the three new users are `ada@example.com` (Ada Lovelace,
  member), `grace@example.com` (Grace Hopper, admin), `alan@example.com` (Alan Turing, member), each with
  `created_by` ADMIN1, a creation time within the test window, no credential and the not-yet-activated state; the test
  mail sink records 0 messages. [API; DB read of every field (a response-only check does not satisfy this)]
- **AC-8.2 failure (nothing partial):** FX-3 -> 422; DB still 4 users and `ok1@example.com`, `ok2@example.com`,
  `dup@example.com` are absent. [API; DB read, not just the response's `created: 0`]
- **AC-8.3 failure (fault injection):** with a harness fault on the 3rd insert, and separately on the audit-event
  insert, FX-1 -> 500 `internal_error`; DB 4 users, 0 audit events for the attempt's `import_id`.
  **NOT-REPLAYED:** needs an injection seam in the implementation (plan item). [API with injected fault; DB]
- **AC-8.4 boundary (size of batch):** FX-MIN (one row) -> 201, `created` 1; FX-R1 (1,000 rows) -> 201 with the
  same all-or-nothing behaviour: with a fault injected on row 1,000's insert, DB still 4 users. [API; DB]
- **AC-8.5 recovery (unknown outcome):** admin1 POSTs FX-1 (commit succeeds, harness drops the response), then POSTs
  FX-1 again. Expected second response: 422 with three errors `{row:2,email,already_exists}`, `{row:3,email,
  already_exists}`, `{row:4,email,already_exists}`; DB stays 7 users. Walk: start is S0 plus admin1's session; the
  first action is permitted (R-1); after it all three emails exist, so each row of the second upload matches an
  existing user (R-7) and G8 fails; the observer (API response) sees the three errors. Hand-recomputed from the rules;
  **NOT-REPLAYED** against a product. [API with response-drop proxy; DB]

### R-9: Result contract
- **Behaviour:** `application/json`. Success 201: `{import_id, created, users:[{id,email,name,role}]}` in file
  order. Failure: `{import_id, created:0, errors:[{row, column, code, message, first_row?}]}` with status per the code
  table. `import_id` is a new UUID per attempt and is the key of the attempt's audit event. A failed import at G8
  reports **every** row error (never only the first), ordered by row ascending, within a row by column
  (`email`, `name`, `role`) then code. File-level gates report only that gate's errors. Messages are the table's text
  verbatim; cell values are never echoed (header text for `unknown_column` excepted).
- **Basis:** request (admin must learn what happened to the upload); A-5, A-12, A-14. Added. Left out: downloadable
  error CSV, template download.
- **AC-9.1 positive:** FX-1 -> 201 body `created: 3`, `users` of length 3 in file order (ada, grace, alan), each with
  a non-empty `id`, and a UUID `import_id`. [API; schema and value assertions]
- **AC-9.2 failure:** FX-3 -> 422 with the five errors of AC-7.1, each `message` equal to the table's text, and
  `created: 0`. [API; exact-array assertion including messages]
- **AC-9.3 boundary (gating):** a file with 1,001 rows in which row 2 has an invalid email -> only `too_many_rows`
  (G7 stops before G8). FX-R3 (1,000 rows, all `invalid_email`) -> 422 with **1,000** errors, none truncated, rows
  2..1001 ascending. [API; automated; length and order asserted]
- **AC-9.4 failure (status mapping):** the status for each code in the table matches (400, 401, 403, 413, 422, 500)
  as exercised in AC-1.x, AC-2.x, AC-3.x. [API]

### R-10: Admin import page (UI)
- **Behaviour:** page "Import users" in the admin area (A-1) with this journey: **empty** (instructions naming the
  columns `email`, `name`, `role` (optional), the limits 1,000 users / 1 MiB / UTF-8 comma-separated, and the
  all-or-nothing rule; a file chooser that is keyboard operable plus a drop zone; the primary "Import users" button
  disabled) -> **selected** (file name and size, e.g. `valid3.csv` and `119 B`; button enabled; a file over 1,048,576
  bytes shows an inline error and sends no request) -> **pending** (button reads "Importing…" and is disabled, the
  file chooser disabled, a status region announces progress; there is no cancel control because cancelling the request
  could not undo a server effect) -> **success** (count and the list of created users, focus moves to the summary
  heading, "Import another file" returns to empty) or **rejected** (heading "Nothing was imported: N problems found"
  and a table of Row, Column, Problem built from the response; focus moves to the heading; the file stays shown;
  choosing a file always re-reads it, even the same path) or **failure** (401 "Your session has expired. Sign in
  again."; 403 "You do not have permission to import users."; 413 or client size error "The file is larger than 1 MiB.";
  network error or 5xx: "We couldn't confirm the result. Check the Users list before trying again; re-importing the
  same file is safe because emails that already exist are rejected."). Failure messages stay visible (alert region)
  until the user acts. Only one request is in flight; later responses never replace newer state. File content and
  results are held in component memory only. Text from the file or response is always rendered as text, never as
  markup.
- **Basis:** request "Let admins upload"; A-1, A-14, A-15; interaction-design and UI guides. Added. Left out: preview or
  dry-run step, import history screen.
- **AC-10.1 empty state:** admin1 opens the page: the heading, the column list, the limits text and the disabled
  button are present; the limits text is built from the same constants the server enforces (AD-6). [UI; automated]
- **AC-10.2 positive + pending:** choose FX-1 (shows `valid3.csv`, `119 B`), click Import users with the response held
  by the test: button label "Importing…", disabled, status region text present; release the 201 response: summary
  "3 users created" and rows ada/grace/alan with roles, focus on the summary heading; "Import another file" returns
  to the empty state. [UI; automated; response completion controlled, no fixed sleeps]
- **AC-10.3 rejected:** choose FX-3 -> heading "Nothing was imported: 5 problems found" and five table rows matching
  AC-7.1 (row 7's problem text includes "row 6"); DB 4 users; focus on the heading. [UI; automated]
- **AC-10.4 failure states:** hold or stub responses 401, 403, 413 and 500, and drop the connection: each shows its
  message above in an alert region, keeps the file selected and re-enables the button; the 500/network text contains
  "Check the Users list". [UI with controlled responses; automated]
- **AC-10.5 boundary (client size check):** a 1,048,577-byte file shows "The file is larger than 1 MiB." and the
  network log has 0 POSTs; FX-S1 (1,048,576 bytes) enables the button. [UI; automated with network log]
- **AC-10.6 double submit:** two rapid clicks on Import users produce exactly one POST. [UI; network log]
- **AC-10.7 escaping:** FX-X1 -> the unknown-column problem shows the literal text `<img src=x onerror=alert(1)>`; the
  DOM has no `img` created from it and no script runs. [UI; DOM query]
- **AC-10.8 storage:** after FX-1 succeeds, `localStorage`, `sessionStorage` and IndexedDB contain no `@example.com`
  string. [UI; storage read]
- **AC-10.9 keyboard and assistive tech:** the whole journey (choose, import, read result, import another) is
  completable with keyboard only; every control has an accessible name; pending and result states are announced
  through a live region. [UI; automated keyboard run plus an automated accessibility scan, which is not a complete
  audit; manual keyboard and screen-reader pass recorded]
- Interface quality criteria are NFR-6.

### R-11: Audit, privacy and retention
- **Behaviour:** every attempt that reaches G2 yields exactly one audit event: `import_id`, actor id, UTC time,
  outcome (`created`, `rejected_forbidden`, `rejected_upload`, `rejected_validation`, `failed_internal`), data-row
  count (when parsed, else null), created count, error count. **No emails, names or file content** appear in audit or
  application logs. A successful import's event is committed in the same transaction as the users (fail closed,
  AD-2); events for rejected attempts are best effort and never change the response. Authentication failures (G1) are
  owned by the existing authentication facility and not re-emitted. The uploaded bytes and parsed rows exist only in
  request memory; any temporary spool file is deleted before the response completes; error reports are not stored; the
  UI persists nothing (AC-10.8). Created users are personal data under the product's existing user lifecycle.
- **State and data:** audit store (insert-only, owner: product audit facility, readable by whoever may read audit today,
  retained per the existing policy, A-9); no new quota beyond R-2.
- **Basis:** request (bulk creation of accounts is a security-relevant operation); A-9. Added. Left out: an
  audit-viewer or import-history UI.
- **AC-11.1 positive:** after FX-1 succeeds: exactly one event with outcome `created`, created 3, rows 3, actor ADMIN1,
  `import_id` equal to the response's. [API; DB]
- **AC-11.2 failure:** after FX-3: one event `rejected_validation`, rows 6, error count 5, created 0; after member1
  POSTs FX-1: one event `rejected_forbidden`, rows null. [API; DB]
- **AC-11.3 privacy:** after FX-1, FX-3 and FX-P1 have been imported by admin1, a search of captured logs, the audit
  store, the process's temp directory and browser storage for the literal strings `ada@example.com`, `Ada Lovelace`,
  `taken@example.com` and `PRIVACY-MARKER-7f3a` finds none; the marker is found only in the user store and the
  FX-P1 response. [LOG, DB, filesystem scan, UI storage; automated]
- **AC-11.4 boundary (fail closed):** covered by AC-8.3: an audit-insert fault yields no users.

## Non-functional requirements

Operating conditions: admin-initiated, low-frequency, one file per request, at most 1,000 rows and 1 MiB. No SLA,
availability or throughput figure was requested and none is invented here.

- **NFR-1 Security.** Authorization per R-1/AD-3; the size cap enforced while reading (AD-4, AC-2.9); file text rendered
  as text only (AC-10.7); the import never evaluates cell contents. Verification: AC-1.x, AC-2.9, AC-10.7.
- **NFR-2 Capacity.** Bounds are A-4's 1 MiB and 1,000 rows, behaviour at the bound per AC-2.1, AC-2.7. A platform limit
  lower than these is G-3.
- **NFR-3 Performance. Unresolved bound (G-5).** No latency target was requested and no platform timeout is known.
  Observable criterion until resolved: a valid 1,000-row import (FX-R1) completes inside a single request on the target
  runtime without a gateway or runtime timeout, and the UI shows the pending state throughout. The numeric target is
  to be set by the requester or from the measured result on the target runtime; AD-1 is revalidated if it cannot be met.
- **NFR-4 Data integrity and recovery.** Atomicity, unique constraint and rollback per R-7, R-8, AD-2. Verification:
  AC-7.5, AC-8.2, AC-8.3, AC-8.5.
- **NFR-5 Accessibility.** WCAG AA contrast (4.5:1 normal text, 3:1 large text and UI component boundaries) in both
  themes; keyboard-only completion; visible focus; accessible names; announced async status. Verification: AC-10.9
  plus contrast measured from rendered computed styles for each state in each theme.
- **NFR-6 Designed interface (applies: R-10 is a graphical UI).**
  - *Visual reference and starting appearance:* the **light Google Gemini look with Material 3 Expressive principles**
    (airy composition, tonal rounded surfaces, friendly precise sans-serif from local fonts, a confident primary action,
    a restrained luminous accent, purposeful transitions), from the UI visual-direction guide. It is the starting point
    only: if the product already has an identity or design tokens, the page inherits them (A-15, unresolved because the
    product was not inspected), and the plan records the concrete choice in an AD. Appearance: **light first with a dark
    option** (follows the product's theme control, else the OS preference).
  - *Observable criteria:* (1) one visual system: a spacing scale, a type scale and a semantic palette defined once as
    tokens, with light and dark values, used by every state; (2) designed empty, selected, pending, success, rejected
    and failure states (R-10), not unstyled defaults; the drop zone has distinct idle, drag-over, focused and disabled
    looks; the primary activity (the file and the Import button) has the strongest weight, the rules text is quieter;
    (3) at 360 px and at 1280 px viewport width the page has no horizontal overflow
    (`document.scrollWidth <= clientWidth`), and the problems table reflows or scrolls inside its own container;
    (4) visible keyboard focus on every control and AA contrast (NFR-5); (5) motion only to explain change (state
    transitions, pending indicator), honoring `prefers-reduced-motion: reduce` (no animation or transition remains
    when set); (6) one icon set; (7) one memorable, useful signature element (the drop zone resolving into a file card
    with a size/validity indication). Verification: automated rendered checks at both widths and both themes, a
    reduced-motion run, and review of screenshots of each state against these criteria.
- **NFR-7 Operability.** Audit and log content per R-11; log lines carry `import_id`, outcome and counts only.
- **NFR-8 Compatibility.** Browsers: the product's existing supported set (unresolved, G-2). CSV exported from common
  spreadsheet tools as "CSV UTF-8" (BOM, CRLF) is accepted (AC-3.2); semicolon-delimited and non-UTF-8 exports are not
  (A-11), and the page's instructions say UTF-8 comma-separated.
- **NFR-9 Maintainability and testability.** Limits defined once (AD-6); parsing and validation are a pure function
  testable without UI or store (AD-5). Verification: unit tests of every fixture; a test that fails if the UI text and
  server limit constants diverge.
- **NFR-10 Abuse and rate limiting: excluded with reason.** The endpoint is admin-only, bounded by R-2, and the product
  has no stated rate policy; no numeric rate limit is invented. Revisit if non-admin or automated callers are added.

## State and information lifecycle (summary of where each piece lives)

| State | Owner and location | Who may read | Concurrent changes | Ends / removed | Quotas met |
|---|---|---|---|---|---|
| Uploaded bytes, parsed rows | request handler memory (temp spool, if any, deleted before response) | nobody else | n/a: per request | end of request | 1 MiB, 1,000 rows |
| Created users | product user store | per the product's existing user-read policy | unique normalized email; losing writer rolls back (AD-2) | existing user lifecycle (deletion is not part of this feature) | none added |
| Audit events | product audit store (A-9) | per existing audit-read policy | insert-only | existing retention policy | none added |
| Error report | the HTTP response only | the uploading admin | n/a | not stored | up to 1,000 rows of errors, bounded by R-2 |
| UI selection, request status, result | page component memory | the admin's own browser | one request in flight (AC-10.6) | page reload or "Import another file" | n/a |

Personal data (email, name): shown to the uploading admin in the success list and rejection table (row numbers and
messages only for rejections), stored only as users, never in logs or audit, never in browser storage. Information
one user must not see: a non-admin learns nothing about existing emails (AC-1.3).

## Service boundary contracts

Only one boundary exists: browser or API client -> import endpoint -> user/audit store (same service, one datastore).
- **Current authority:** role read from the user store on each request (AC-1.4); no cache of authorization.
- **Freshness versus revocation:** a revoked admin is rejected on their next request, mid-session (AC-1.4).
- **Incremental state / async completion / recovery:** none; synchronous (AD-1). Unknown-outcome recovery = re-upload
  (AC-8.5), and the UI states it (AC-10.4).
- **Owned event coverage:** import audit events (R-11); authentication events stay with the existing auth facility.
- **Not applicable:** caches, queues, outbound calls to other services, mail (excluded by A-7).

## Open gaps and readiness

| ID | Under | Gap | Safe interim / default | Smallest confirming step | Blocks |
|---|---|---|---|---|---|
| G-1 | R-8 | How do created users obtain a credential? | A-7: no credential, no email; existing activation/reset flow, `invited` state if none exists | Requester decides whether imports must send invitations; or plan finds the product's existing admin-created-user flow | R-8's credential/state clause and any mail work; not parsing or validation |
| G-2 | R-1, R-6, R-7, R-8, R-11, NFR-8 | Product baseline unknown: sign-in/role mechanism, role names, user schema, deactivated users, store transactions and case-insensitive unique index, audit facility, supported browsers, stack | A-1, A-2, A-9, AD-2, AD-5 defaults | Plan's first item inspects the repository and schema and records them; any difference changes only the cited assumptions | R-6 role set, AD-2/AD-5 choice, AC-7.6; independent: R-2/R-3/R-4/R-5 pure parsing and validation work |
| G-3 | R-2, NFR-2, NFR-3 | Deployment request-body limit and request time limit unknown | A-4 limits stand as product defaults | Upload FX-S1 and FX-R1 to the target runtime; must admit a 1,048,576-byte file part plus multipart framing and finish within the time limit; else the requester lowers A-4 | R-2 limit acceptance on that runtime |
| G-4 | R-6, R-1 | May an admin create `admin` users via CSV? | A-10: yes | Requester confirms | AC-6.1 admin row only |
| G-5 | NFR-3 | Numeric latency target | observable criterion in NFR-3 | requester or measured on target runtime | NFR-3 numeric acceptance only |

No material requirement conflict was found. Work depending on G-2 stays unready until its confirming step runs;
independent work proceeds.

## Request-outcome traceability

| Request outcome | Requirements | Acceptance lines |
|---|---|---|
| "admins" can do it, others cannot | R-1 | AC-1.1 to AC-1.5 |
| "upload a CSV" (file intake, format, the upload page) | R-2, R-3, R-10 | AC-2.x, AC-3.x, AC-10.x |
| "bulk-create users" (valid rows become users, bad rows are explained, no partial state) | R-4, R-5, R-6, R-7, R-8, R-9 | AC-4.x to AC-9.x |
| accountability for creating accounts in bulk (assumed, A-9) | R-11 | AC-11.x |

Primary outcomes (what the request asked for directly): R-1, R-2, R-3, R-8, R-10.

## Evidence record for item 10 (replay and checks)

- Fixture byte counts and expected results above were **derived by hand** from the rules: FX-1 is 16 + 36 + 37 + 30 =
  119 bytes; FX-S1's text is 11 + 25 + 25 = 61 bytes, so 1,048,576 - 61 = 1,048,515 padding LF bytes; FX-EMAIL254 is
  2 + 248 + 4 = 254 characters. No script or product was executed: a reference oracle script was drafted in the session
  scratchpad but its run was not approved, so it is **not** evidence.
- Ordered procedures walked on paper from their start state with the permitting rule named: AC-1.4 (R-1, AD-3),
  AC-7.5 (R-1, R-7, AD-2), AC-8.5 (R-1, R-7, R-8). All three are **NOT-REPLAYED** because no implementation exists;
  AC-1.4, AC-7.5 and AC-8.3 also need plan items for a role-change harness write, a commit barrier and a fault-injection
  seam. Their expected results above are the recomputed ones.
- Platform and library claims: none relied on. AD-4's streaming cut-off and AD-5's parser strictness are requirements on
  the chosen stack and are checked by AC-2.9 and AC-3.7, not assumed.
- No documented command exists yet, so no command was run.

## Retired

None. First specification of this area; nothing prior to retire or weaken.

## Submission

- **summary:** Specified bulk user import from CSV as R-1 to R-11 with 15 recorded assumptions (A-1..A-15), six AD
  decisions (AD-1..AD-6), NFR-1..NFR-10, and concrete fixtures (S0, FX-*) for every acceptance line. Defaults chosen
  and recorded as assumptions: 1 MiB and 1,000-row caps, email 254 and name 100 limits, all-or-nothing, case-insensitive
  global email uniqueness, roles `member`/`admin` with default `member`, no credential and no email sent, synchronous
  single-request import, audit in the same transaction, no retention of the file. Open: G-1 (credential provisioning),
  G-2 (product baseline unknown, nothing inspected), G-3 (platform request limits), G-4 (admin creation via CSV),
  G-5 (latency bound). No material requirement conflict. Unverified: AC-1.4, AC-7.5, AC-8.3, AC-8.5 are NOT-REPLAYED
  (owner: plan and test-strategy, due before implement); no fixture result was executed.
- **primary:** R-1, R-2, R-3, R-8, R-10.
- **evidence_refs:** KNOWLEDGE/spec.md; KNOWLEDGE/architecture.md; sections R-1 to R-11, Non-functional requirements,
  State and information lifecycle, Service boundary contracts, Open gaps; guides GUIDES/behavioral-requirements.md
  (behavior model, traceability, interaction design), GUIDES/requirements-definition.md, GUIDES/service-discovery.md,
  GUIDES/platforms/ui.md (light expressive starting point), GUIDES/current-system-baseline.md. No repository or
  prior-stage source existed. `backchain-check` does not exist here (duty 11 omitted).
