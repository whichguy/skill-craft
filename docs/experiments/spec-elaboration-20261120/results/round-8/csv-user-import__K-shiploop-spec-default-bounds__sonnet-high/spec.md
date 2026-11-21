# Admin Console, User Administration: Product Specification

Living spec for administrator-facing user management. This run adds one capability, bulk user creation from a CSV
file. Status of everything below: **accepted intent where it quotes the request; every other clause is a labelled
default (A-n) awaiting product-owner veto**; implementation and checks are all pending (nothing is built or run).

## Sources, baseline and evidence limits

- Request (2026-11-21, verbatim): "Let admins upload a CSV to bulk-create users."
- Inspected: `KNOWLEDGE/spec.md` (absent before this run), the discovery and research results (none exist), a
  selected current-system baseline (none exists), the repository (none supplied). **Observed behaviour of the current
  system: none.** Everything about the existing product (stack, admin role model, user record, single-user creation,
  admin screens, audit trail) is an unknown, recorded as G-1 and its siblings, not assumed away.
- Consequence: every requirement below is **added**. Nothing is preserved or modified because no earlier requirement
  was supplied; where an existing behaviour must be preserved once found (single-user creation, authorization),
  R-7, R-12 and G-1 say so.
- External sources used: RFC 5321 §4.5.3.1 (read 2026-11-21): local-part at most 64 octets, a path at most 256 octets
  including the angle brackets, hence an address of at most 254; RFC 4180 (informational, read 2026-11-21): quoting
  with doubled quotes, one record per line, header optional. Both feed defaults (A-5, A-6), not platform claims.
- No other system is the reference, so there is no parity/difference mapping.

## Vocabulary and shared fixtures

- **Row N** is the Nth CSV *record*: the header is row 1, the first record after it is row 2. Empty lines count as
  records for numbering, and equal physical line numbers unless a quoted field contains a line break.
- **Data row**: a record after the header that is not blank. **Blank record**: an empty line (zero characters). A
  line of spaces or `,,` is not blank.
- **Surfaces.** UI = the "Import users" screen in a browser, signed in as the named actor. API = the import operation
  over HTTP (AD-3): `multipart/form-data` with exactly one file part named `file`. LIST = the product's existing
  user list or lookup, used to read back persisted users (G-1 if none exists: read back through the test store).
- **Seed state S0** (4 users, every acceptance line starts from S0 unless it says otherwise; all addresses are in the
  reserved `example.com` domain): `admin@example.com` (role admin), `admin2@example.com` (admin),
  `member@example.com` (member), `existing@example.com` (member, name "Existing User"). Actors: Admin A =
  `admin@example.com`, Admin B = `admin2@example.com`, Non-admin = `member@example.com`, signed in unless stated.
- **Check order** (first failing step decides a file-level rejection): authentication, authorization (R-1), `no_file`,
  `file_too_large`, `file_empty`, `not_utf8`, `malformed_csv`, header checks `missing_column` then `unknown_column`
  then `duplicate_column`, `no_data_rows`, `too_many_rows` (R-2, R-3, R-4); then every row is validated and the
  results gathered together (R-5, R-6, R-8); then commit (R-7, R-9).

### Fixtures (byte-exact; `\n` is LF, `<BOM>` is bytes EF BB BF)

| ID | Content |
|---|---|
| FX-1 | `email,name,role\n` `ada@example.com,Ada Lovelace,admin\n` `grace@example.com,Grace Hopper,\n` `alan@example.com,Alan Turing,member\n` |
| FX-2 | FX-1 with `<BOM>` first and every `\n` replaced by CRLF |
| FX-3 | ` Name ,ROLE,Email\n` `Ada Lovelace,Admin,  ADA@Example.COM  \n` (two leading/trailing-space cells) |
| FX-4 | `email,name\n` `hopper@example.com,"Hopper, Grace"\n` `amazing@example.com,"Grace ""Amazing"" Hopper"\n` |
| FX-5 | `email,name,role\n` `ada@example.com,Ada Lovelace,admin\n` `not-an-email,Bad Email,member\n` `grace@example.com,,member\n` `alan@example.com,Alan Turing,owner\n` `existing@example.com,Existing Again,member\n` `ADA@example.com,Ada Dup,member\n` |
| FX-6 | `email,name,role\n` `bad,,wizard\n` |
| FX-7 | `email,name,role\n` `ada@example.com,Ada\n` `grace@example.com,Grace,member,extra\n` |
| FX-8 | `email,name\n` `\n` `ada@example.com,Ada Lovelace\n` `\n` `grace@example.com,Grace Hopper\n` ; FX-8b = `email,name\n` `\n` `not-an-email,Bad\n` |
| FX-9 | 0 bytes; FX-9b = `<BOM>` only |
| FX-10 | `email,name,role\n`; FX-10b = `email,name,role\n` followed by three `\n` |
| FX-11 | `email,role\n` `ada@example.com,admin\n` |
| FX-12 | `email,name,password\n` `ada@example.com,Ada,x\n`; FX-12b = `email,name,Email\n` `ada@example.com,Ada,b@example.com\n`; FX-12c = `email,name,,role\n` `ada@example.com,Ada,,\n` |
| FX-13 | `email,name\n` `sv@example.com,Bj` + byte F6 + `rk\n` (Latin-1); FX-13b = same with `Björk` as UTF-8 bytes C3 B6 |
| FX-14 | `email,name\n` `ada@example.com,"Ada Lovelace\n` (unterminated quote); FX-14b = `email,name\n` `ada@example.com,Ada "The" Lovelace\n` (bare quote); FX-14c = `email,name\r` `ada@example.com,Ada\r` (lone CR) |
| FX-15 | `email;name\n` `ada@example.com;Ada\n` |
| FX-16 | base = `email,name\n` `size@example.com,Size Edge\n` (38 bytes) followed by `\n` padding to **exactly 2,097,152 bytes**; FX-16b = the same padded to 2,097,153 bytes |
| FX-17 | `email,name\n` then one line per n: `user{n:04d}@example.com,User {n:04d}\n`; FX-17a n=1..5000 (155,011 bytes); FX-17b n=1..5001 |
| FX-18 | single-row files `email,name\n{email},{name}\n`: email of 254 chars = 64×`a` + `@` + 63×`b` + `.` + 63×`c` + `.` + 61×`d`; email of 255 chars = same with 62×`d`; `{65×a}@example.com`; `{64×a}@example.com`; name of 100×`a`; name of 101×`a`; name of 100×`é` |
| FX-19 | `email,name,role\n` `a1@example.com,A,Admin\n` `a2@example.com,B,MEMBER\n` |
| FX-20 | `email,name\n` `x1@example.com,<script>alert(1)</script>\n` `x2@example.com,=1+1\n`; FX-20b = `email,name\n` `x1@example.com,Ada` + TAB + `L\n` |
| FX-21 | `email,name\n` `ada@example.com,"Ada` LF `Lovelace"\n` `grace@example.com,Bad Mail\n` `not-email,N\n` |
| FX-22 | `email,name\n` then k lines `bad{i},N\n` for i=0..k-1; FX-22a k=100, FX-22b k=101, FX-22c k=150 |
| FX-23 | `email,name\n` `ada@example.com,"` + 2,000,000×`a` + `"\n` |
| FX-24 | `email,name\n` `race@example.com,Racer One\n` `x1@example.com,X One\n`; FX-24b = `email,name\n` `race@example.com,Racer Two\n` `y1@example.com,Y One\n` |

## Assumptions (labelled defaults, not user requirements)

A later run must not promote these into binding conditions merely because they are written here (maintained-
requirements policy); each is open to product-owner veto, and the R-n it bounds is named.

| ID | Default taken (the request leaves it open) | Rationale | Bounds |
|---|---|---|---|
| A-1 | A web product with an existing admin role, an HTTP backend and an admin console exists or will exist. | "Upload" and "admins" imply it; the repository is unknown (G-1). | R-1, R-11 |
| A-2 | Columns: `email` (required), `name` (required), `role` (optional; `member` or `admin`; blank means `member`). Header names are case-insensitive, trimmed, any order. | Smallest set that identifies and labels a user and fixes access; no field beyond what a user needs. | R-3, R-5 |
| A-3 | **All-or-nothing**: if any problem exists, nothing is created; otherwise every row is created in one atomic commit. | No partial state to explain or repair; a fixed file can be re-uploaded whole. Partial import was considered and not chosen. | R-7 |
| A-4 | An email that already exists, or repeats within the file, is an error. No update, skip or merge. Email comparison is case-insensitive after trimming; the stored form is lower-case. | Bulk-*create* was asked for; silently updating accounts is a privilege risk. | R-6 |
| A-5 | Limits: file at most **2,097,152 bytes** (2 MiB); at most **5,000 data rows**; email at most **254** characters with local part at most **64** (RFC 5321 §4.5.3.1); name 1 to **100** Unicode code points; at most **100** row errors reported per response. | 5,000 rows is a realistic one-organisation onboarding batch and keeps one atomic commit small; 2 MiB is above a 5,000-row file of ordinary rows (FX-17a is 155,011 bytes) and bounds the memory a hostile upload can claim; the two limits are independent and either may reject. | R-2, R-4, R-5, R-8 |
| A-6 | Format: UTF-8 with an optional BOM, comma delimiter, line ends LF or CRLF, RFC 4180 quoting with strict handling (a bare quote or lone CR is malformed). File name and extension are not trusted; content decides. | Predictable parsing; a BOM is tolerated because some spreadsheet exports add one (the rule does not depend on that). Semicolon-delimited and other encodings are out of scope. | R-2 |
| A-7 | Created users get exactly the initial state and onboarding that single-user creation gives them. **No password or credential column**; a column named `password` is rejected, never ignored. | Credentials in a file at rest are a hazard; onboarding is the product's existing concern (G-1). | R-3, R-7, R-12 |
| A-8 | Single step: submitting the file validates and, if clean, creates. No server-held preview, no second "confirm" request. | Avoids holding uploaded personal data between requests (R-10). The submit button is the confirmation. | R-7, R-10, R-11 |
| A-9 | Error entries identify problems by row number, column and code and never echo submitted cell values; unknown columns are reported by position. | Privacy and reflected-content safety. | R-8, R-16 |
| A-10 | The uploaded file is processed in memory and never persisted; the audit record holds counts and outcome only. | Minimum personal-data retention. | R-10 |
| A-11 | Email syntax rule (deliberately simpler than RFC 5322): printable ASCII only (0x21 to 0x7E), exactly one `@`, local part 1 to 64 characters, domain contains at least one `.` and no empty label. Internationalised addresses are out of scope. | Rejects typos without a full address grammar. | R-5 |
| A-12 | A retry of the same file after an unknown outcome is safe and is the recovery path (R-9). | Follows from A-3 and A-4. | R-9, R-11 |
| A-13 | An admin may assign either role through import, the same authority as single-user creation. | Unknown whether single-user creation restricts `admin` (G-2). | R-1, R-5 |
| A-14 | Processing is synchronous within one request; the result is the response. | At most 5,000 rows; revisited if G-3 shows the platform cannot finish within its limit (AD-1). | R-7, R-15 |
| A-15 | UI direction: inherit the existing admin console's identity if one exists (G-1); otherwise the "light expressive starting point" (light Gemini look and feel, Material 3 Expressive principles), light first with a dark option. | UI visual-direction guide; explicit constraints and identity take precedence. | R-13 |
| A-16 | An unknown header column rejects the file rather than being ignored. | Silent ignoring hides mistakes such as a mis-spelled `email`. | R-3 |
| A-17 | If the audit record cannot be written after users are committed, the creation stands, the response is still success, and an operational error is logged. If the audit trail shares the user store, the record is written in the same atomic commit instead. | Never undo a committed creation for diagnostics; never lose the record when it can be atomic. | R-10 |

## Requirements

Conventions for every requirement below, unless it says otherwise: **Basis** that says "request" is the 2026-11-21
request quoted above, and "A-n" is the labelled default of that ID (a design decision, not a user requirement).
**Change:** added. **Preserved:** none (no earlier requirement or baseline exists). **Source-section locators:** none
(no prior spec, repository or discovery result). **Evidence limit:** no repository or running product was inspected,
so no acceptance line has been observed to pass. **Pending:** implementation and every check; none is authored.

### R-1: Only authenticated administrators can import

- **Basis:** request 2026-11-21 ("Let admins upload…"); A-1, A-13. **Change:** added. **Preserved:** none found (G-1).
  **Evidence limit:** the product's authorization model is unseen. **Pending:** implementation, all checks.
- **Behaviour:** the import screen and the import operation are available only to a signed-in user whose *current*
  role is admin. The role is decided when the file is submitted, not when the page was loaded.
- **Boundaries:** a request with no session is unauthenticated; a signed-in non-admin is unauthorized; an admin
  demoted after loading the page is unauthorized at submit.
- **Error behaviour:** nothing is read from the file, nothing is created. API: 401 unauthenticated, 403 unauthorized,
  body `{"status":"forbidden"}`. UI: unauthenticated users are sent to the product's sign-in; non-admins do not see
  the entry point, and a direct visit shows "You don't have permission to import users."
- **Consumer outcome:** admins reach the import; nobody else can create a user this way.
- **Acceptance lines**
  - **R-1.1 Positive.** Admin A submits FX-1. Expect not 401/403 (outcome per R-7.1). Surface: API and UI. Confirmed
    by: api test, ui flow.
  - **R-1.2 Failure (unauthenticated).** No session, FX-1 over the API. Expect 401; LIST still shows exactly the 4 S0
    users. Surface: API. Confirmed by: api test.
  - **R-1.3 Failure (not admin).** Non-admin submits FX-1. Expect 403 `{"status":"forbidden"}`, LIST shows the 4 S0
    users; in the UI the import entry point is absent and a direct visit shows the denial text. Surface: API and UI.
    Confirmed by: api test, ui flow.
  - **R-1.4 Boundary (revocation).** Setup: Admin B loads the Import screen; then the test sets `admin2@example.com`'s
    role to member through the test store (the product's role-edit surface is unknown, G-1, so the store is the
    seam); Admin B submits FX-1. Expect 403 and still 4 users. Surface: API and UI. Confirmed by: api test, ui flow.
    If the product caches roles in a session claim and this passes only after the cache lapses, the lag is G-4.
- **Rules the request leaves out:** who may grant `admin` (A-13, G-2); session lifetime (existing product policy).
- **State and data:** reads current role from the user store (owner: the user store); changes nothing on denial.
- **Open gaps:** G-2, G-4.

### R-2: File intake accepts a bounded UTF-8 CSV and rejects anything else whole

- **Basis:** request ("upload a CSV"); A-5, A-6. **Change:** added. **Pending:** implementation, all checks.
- **Behaviour:** the file part is read as UTF-8 text (an initial BOM is dropped) and parsed as comma-separated records
  per A-6. Content, not file name or declared MIME type, decides.
- **Boundaries:** size limit 2,097,152 bytes inclusive; a 0-byte or BOM-only file is empty; a lone CR, an unterminated
  quote or a bare quote is malformed.
- **Error behaviour (file-level, nothing created, one error only, per the check order):** `no_file` (no `file` part),
  `file_too_large` (HTTP 413), `file_empty`, `not_utf8`, `malformed_csv` (reports the row where the offending record
  starts). All except 413 and the 401/403 of R-1 are HTTP 422 with `file_error` set (R-8).
- **Consumer outcome:** an admin gets a plain statement of what is wrong with the file as a whole and that nothing was
  created.
- **Acceptance lines**
  - **R-2.1 Positive.** FX-2 (BOM and CRLF) behaves exactly as FX-1; FX-13b creates `sv@example.com` with name
    `Björk`; FX-4 creates names `Hopper, Grace` and `Grace "Amazing" Hopper`. Surface: API. Confirmed by: unit test of
    the parser plus api test.
  - **R-2.2 Failure.** FX-9 and FX-9b: 422 `file_empty`. FX-13: 422 `not_utf8`. FX-14: 422 `malformed_csv` row 2;
    FX-14b: `malformed_csv` row 2; FX-14c: `malformed_csv` row 1. A request with no `file` part: 422 `no_file`. Each
    leaves 4 users. Surface: API. Confirmed by: api test (parser rows also by unit test).
  - **R-2.3 Boundary (size).** FX-16 (2,097,152 bytes): not rejected for size and creates `size@example.com` (name
    "Size Edge", role member), 5 users. FX-16b (2,097,153 bytes): 413 `file_too_large`, 4 users. The handler reads no
    more than 2,097,153 bytes of the body before it rejects (checked with a counting stream, so a lying or absent
    `Content-Length` cannot make it buffer more). Surface: API. Confirmed by: api test and unit test with a counting
    stream.
  - **R-2.4 Boundary (content over name).** A file named `users.txt` with FX-1 content creates the 3 users; a binary
    PNG named `users.csv` returns 422 `not_utf8` or `malformed_csv`. Surface: API. Confirmed by: api test.
  - **R-2.5 Boundary (one huge field).** FX-23 (a 2,000,000-character name inside the size limit): 422 with one row
    error `too_long` on row 2 name; the process stays responsive. Surface: API. Confirmed by: api test.
- **Rules the request leaves out:** encodings other than UTF-8, other delimiters, Excel binary formats, compressed
  files (all rejected, A-6). **State and data:** the file is request-scoped and not persisted (R-10).

### R-3: The header must name the known columns exactly

- **Basis:** request ("CSV to bulk-create users" needs a column mapping); A-2, A-7, A-16. **Change:** added.
- **Behaviour:** the first record is the header. Header cells are trimmed and compared case-insensitively with
  `email`, `name`, `role`; order is free. `email` and `name` must be present; `role` may be absent.
- **Boundaries:** an empty header cell is an unknown column; the same column twice is a duplicate.
- **Error behaviour:** `missing_column` (lists the missing canonical names), then `unknown_column` (lists 1-based
  column positions, never the cell text), then `duplicate_column` (positions of all copies); 422, nothing created.
- **Consumer outcome:** a mis-labelled file fails before any row is judged, with the column to fix.
- **Acceptance lines**
  - **R-3.1 Positive.** FX-3 (header ` Name ,ROLE,Email`) creates one user: email `ada@example.com`, name `Ada
    Lovelace`, role `admin`. Surface: API. Confirmed by: api test, LIST read-back.
  - **R-3.2 Failure.** FX-11: `missing_column` columns `["name"]`. FX-15 (semicolon): `missing_column` columns
    `["email","name"]`. FX-12: `unknown_column` positions `[3]` (no `password` column is ever honoured). FX-12c:
    `unknown_column` `[3]`. FX-12b: `duplicate_column` `[1,3]`. All 422, 4 users. Surface: API. Confirmed by: unit +
    api test.
  - **R-3.3 Boundary.** The `role` column omitted (FX-4) creates users with role member. Surface: API. Confirmed by:
    api test.
- **Rules the request leaves out:** extra columns (rejected, A-16), password/credential column (rejected, A-7),
  template download (out of scope, see Out of scope).

### R-4: A file has at most 5,000 data rows

- **Basis:** the request gives no volume; default A-5. **Change:** added.
- **Behaviour:** blank records are ignored and do not count; data rows are counted after the header checks pass.
- **Boundaries:** exactly 5,000 data rows is accepted; 5,001 is rejected.
- **Error behaviour:** `too_many_rows`, 422, nothing created, no row validation performed.
- **Acceptance lines**
  - **R-4.1 Positive / Boundary (at the limit).** FX-17a (5,000 rows, `user0001` to `user5000`): 201, 5,000 created,
    LIST shows 5,004 users including `user5000@example.com`. Surface: API. Confirmed by: api test (also timed, R-15).
  - **R-4.2 Failure / Boundary (over).** FX-17b (5,001 rows, last `user5001@example.com`): 422 `too_many_rows`; 4
    users; no `user0001@example.com`. Surface: API and UI. Confirmed by: api test, ui flow.
  - **R-4.3 Boundary (blank rows).** FX-8 creates 2 users; FX-8b gives one row error at **row 3** (blank row 2 counted
    for numbering, not as a data row). Surface: API. Confirmed by: unit + api test.

### R-5: Every row is validated and normalised column by column

- **Basis:** request (create users from rows); A-2, A-5, A-11, A-13. **Change:** added.
- **Behaviour:** per cell: trim leading/trailing whitespace; then apply, in this precedence and reporting at most one
  code per cell: `required` (empty email or name), `invalid_characters` (any control character U+0000 to U+001F or
  U+007F inside the value, including tab or a line break from a quoted field), `too_long`, then format (`invalid_email`
  per A-11, `invalid_role`). Role: case-insensitive match to `member` or `admin`; blank means member. Stored forms:
  email lower-case, name as trimmed (inner spacing and case kept), role lower-case. A record whose field count differs
  from the header gets one row-wide error `wrong_field_count` (column null) and no per-cell checks.
- **Boundaries:** email 254 characters accepted, 255 `too_long`; local part 64 accepted, 65 `invalid_email`; name 100
  code points accepted, 101 `too_long`.
- **Error behaviour:** all row errors across the file are gathered in one pass (not first-failure-only) and returned
  together (R-8); nothing is created.
- **Acceptance lines**
  - **R-5.1 Positive.** FX-1 stores `ada@example.com`/`Ada Lovelace`/admin, `grace@example.com`/`Grace Hopper`/member
    (blank role defaults), `alan@example.com`/`Alan Turing`/member. FX-19 stores roles admin and member (`Admin`,
    `MEMBER` normalised). Valid emails also include `first.last+tag@sub.example.co.uk`. Surface: API, LIST read-back.
    Confirmed by: unit + api test.
  - **R-5.2 Failure.** FX-6 yields exactly three row errors on row 2: email `invalid_email`, name `required`, role
    `invalid_role`. FX-7 yields `wrong_field_count` on rows 2 and 3. FX-20b yields `invalid_characters` on row 2 name.
    FX-21 yields `invalid_characters` row 2 name and `invalid_email` row 4 (row 3 valid; row numbers are records).
    Each of these invalid emails yields `invalid_email`: `ada`, `ada@`, `@example.com`, `ada@example`,
    `ada @example.com`, `a@b@example.com`, `ada@.com`, `ada@example..com`, `adä@example.com`. Surface: API. Confirmed
    by: unit + api test.
  - **R-5.3 Boundary.** The FX-18 files: 254-character email and 64-character local part are accepted; 255-character
    email is `too_long`; 65-character local part is `invalid_email`; 100-character and 100×`é` names are accepted;
    101-character name is `too_long`. Surface: API. Confirmed by: unit + api test.
  - **R-5.4 Positive (content kept verbatim).** FX-20 creates names `<script>alert(1)</script>` and `=1+1` unchanged.
    Surface: API, LIST. Confirmed by: api test (rendering safety under R-16.1).
- **Rules the request leaves out:** name uniqueness (none required), phone/department/other attributes (out of scope),
  neutralising spreadsheet-formula prefixes on later export (not stored differently; any future export owns that).

### R-6: Email addresses are unique, within the file and against existing users

- **Basis:** unique accounts are implied by "create users"; A-4. **Change:** added.
- **Behaviour:** after trim and lower-casing, the first data row carrying a syntactically valid email owns it. A later
  row with the same email is `duplicate_in_file` and reports `related_row` (the owner's row number). A row whose email
  matches any existing user of any status is `already_exists`. Precedence on the email cell: the R-5 errors, then
  `duplicate_in_file`, then `already_exists`.
- **Error behaviour:** 422, gathered with the other row errors; nothing created (A-3), even for the valid rows.
- **Acceptance lines**
  - **R-6.1 Positive.** Rows with distinct, unused emails raise no R-6 error (FX-1 from S0 creates 3).
  - **R-6.2 Failure.** FX-5 from S0: 422 with exactly these five row errors, in this order: row 3 email
    `invalid_email`; row 4 name `required`; row 5 role `invalid_role`; row 6 email `already_exists`; row 7 email
    `duplicate_in_file` with `related_row` 2 (`ADA@example.com` repeats row 2's `ada@example.com`). `row_error_total`
    is 5. LIST still shows 4 users: **row 2 (`ada@example.com`, valid) was not created.** Surface: API and UI.
    Confirmed by: unit + api test + ui flow.
  - **R-6.3 Boundary (case and spacing).** FX-3's `  ADA@Example.COM  ` is stored as `ada@example.com`; submitting a
    file whose email is `EXISTING@example.com` gives `already_exists`. Surface: API. Confirmed by: api test.
- **Rules the request leaves out:** matching against deactivated or invited users (treated as existing, G-1), plus
  addressing aliases such as `+tag` (distinct addresses).

### R-7: A clean file creates every user atomically; any problem creates none

- **Basis:** request ("bulk-create users"); A-3, A-7, A-8, A-14. **Change:** added.
- **Behaviour:** when R-1 to R-6 find no problem, all rows are created in one atomic commit with the role of R-5 and
  the initial state of single-user creation (R-12). The response is 201 `{"status":"created","created_count":N}`.
  Otherwise nothing is created.
- **Boundaries:** N ranges from 1 to 5,000; a failure at any point before the commit leaves zero new users; no
  partially created set is ever visible to any reader.
- **Error behaviour:** an unexpected failure before commit rolls back: HTTP 500 `{"status":"error"}`, zero users
  created. A failure after commit (for example while sending the response) is an unknown outcome handled by R-9.
- **Consumer outcome:** the admin sees how many users were created; LIST shows exactly those users.
- **Acceptance lines**
  - **R-7.1 Positive.** Admin A submits FX-1 from S0: 201 `created_count` 3; LIST shows 7 users, the 3 new ones with
    the roles of R-5.1; in the UI the screen says `3 users created`. Surface: API, UI, LIST. Confirmed by: api test,
    ui flow.
  - **R-7.2 Failure (atomicity).** FX-5 from S0: user count stays 4 and none of `ada@`, `grace@`, `alan@` exists
    (see R-6.2). Surface: API, LIST. Confirmed by: api test.
  - **R-7.3 Failure (storage fault).** FX-17a with the store made to fail on the 2,500th insert (test seam): 500
    `{"status":"error"}`, LIST shows 4 users, no `user*` user. Surface: API. Confirmed by: api test with a fault-
    injecting store double; a real store is a G-7 check.
  - **R-7.4 Boundary.** `created_count` equals the number of data rows: 1 for FX-16, 5,000 for FX-17a. Surface: API.
    Confirmed by: api test.
- **State and data (item 7):** resource: user records in the product's user store (owner of truth); target identity:
  normalised email; before: S0 with N distinct unused emails; after: exactly +N users or unchanged; invariant:
  count after is count before or count before plus N, never between; recovery: rollback; check: LIST count before
  and after. **Unknown:** whether the store can give one transaction across 5,000 inserts (G-7).
- **Open gaps:** G-1 (initial state), G-7.

### R-8: The response says exactly what happened and what was wrong

- **Basis:** the admin must be able to correct the file; A-5, A-9. **Change:** added.
- **Behaviour (API body):** `{"status": "created"|"rejected"|"forbidden"|"error", "created_count": n,
  "file_error": null | {"code": c, "message": m, "row"?: n, "columns"?: [...]}, "row_errors": [{"row": n, "column":
  "email"|"name"|"role"|null, "code": c, "message": m, "related_row"?: n}], "row_error_total": n,
  "row_errors_truncated": bool}`. A rejected response has `created_count` 0. Row errors are ordered by row, then by
  column order email, name, role; the row-wide `wrong_field_count` stands alone for its row. A file-level error and
  row errors never appear together. Messages are distinct per code and name the row and column; they never contain a
  submitted cell value (A-9).
- **Boundaries:** at most 100 row errors are listed; `row_error_total` counts all; `row_errors_truncated` is true only
  when the total exceeds 100.
- **Acceptance lines**
  - **R-8.1 Positive.** FX-1 response: status created, `created_count` 3, `file_error` null, `row_errors` empty,
    total 0, truncated false. Surface: API. Confirmed by: api test.
  - **R-8.2 Failure.** FX-5 response exactly as R-6.2 with `created_count` 0, `file_error` null; FX-9 response has
    `file_error.code` `file_empty` and an empty `row_errors`. Surface: API. Confirmed by: api test.
  - **R-8.3 Boundary (the 100-error cap).** FX-22a (100 bad rows, rows 2 to 101): 100 listed, total 100, truncated
    false. FX-22b (101): 100 listed (rows 2 to 101), total 101, truncated true. FX-22c (150): 100 listed, total 150,
    truncated true, first row 2, last row 101. Surface: API and UI. Confirmed by: unit + api test, ui flow for the "and
    N more" wording of R-11.4.
  - **R-8.4 Failure (no echo).** Submit FX-5 and FX-12; no response body contains any of the strings `Existing
    Again`, `Bad Email`, `not-an-email`, `Ada Dup` or `password`. Surface: API. Confirmed by: api test scanning the
    body.

### R-9: Concurrent and repeated submissions never produce duplicates or partial sets

- **Basis:** consequence of R-6 and R-7 under real use; A-3, A-4, A-12. **Change:** added.
- **Behaviour:** uniqueness of the normalised email is enforced at commit time, not only by the earlier read in R-6,
  so two imports that each saw an address as free cannot both create it. The loser is rolled back whole. Resubmitting
  an already imported file creates nothing.
- **Error behaviour:** the commit-time loser gets 422 with at least the contested row as `already_exists` (it may
  list only the first conflict it can identify); the response is the same shape as a validation-time rejection.
  **Unknown outcome:** if the admin's client never receives a response, nothing guarantees whether users were
  created; the recovery is to check LIST and, if unsure, resubmit the same file, which creates no duplicates (all rows
  `already_exists` if the first attempt succeeded; the full set if it did not).
- **Acceptance lines**
  - **R-9.1 Positive (sequential repeat is safe).** Admin A submits FX-1 twice from S0: first 201 (7 users); second
    422 with `already_exists` on rows 2, 3 and 4, `row_error_total` 3; still 7 users. Surface: API and UI. Confirmed
    by: api test, ui flow.
  - **R-9.2 Failure (race, deterministic).** Admin A submits FX-24 and Admin B submits FX-24b. Interleaving, held by a
    test seam between validation and commit: B passes validation (S0 has no `race@`), A passes validation, A commits,
    B's commit then finds `race@example.com` already taken (mechanism: AD-4). Expect A 201 (`created_count` 2); B 422 with `already_exists` on row
    2; LIST shows 6 users: `race@example.com` named "Racer One", `x1@example.com`, and **no** `y1@example.com`.
    Surface: API. Confirmed by: api test with the seam (the seam must hold B after its validation pass; if the store
    cannot guarantee case-insensitive email uniqueness at commit, G-7 blocks this line).
  - **R-9.3 Boundary (unseamed concurrency).** Running the FX-24 / FX-24b pair simultaneously 50 times, each from a
    fresh S0, always ends with exactly one of A/B receiving 201 and the other 422, and with exactly 6 users: if A won,
    `x1@example.com` exists and `y1@example.com` does not, and `race@example.com` is "Racer One"; if B won, `y1@` exists,
    `x1@` does not, and `race@example.com` is "Racer Two". Surface: API. Confirmed by: api test (supports R-9.2;
    does not replace it).
  - **R-9.4 Failure (double-click).** In the UI, a second activation of the submit control while the first request is
    pending sends nothing (the control is disabled), observable as exactly one request. Surface: UI. Confirmed by: ui
    flow with a held response.
- **State and data:** shared contention is on single email keys, not independent load; owner: user store; check:
  count and membership after both responses. **Unknowns:** G-7.

### R-10: Each attempt is audited without keeping the upload or its personal data

- **Basis:** user creation is a security-relevant outcome; A-10, A-17. **Change:** added.
- **Behaviour:** every attempt that reaches the authorization decision writes one audit record: actor id (absent when
  unauthenticated), timestamp, outcome (`created`, `rejected`, `forbidden`, `error`), file size in bytes when read,
  data-row count when parsed, `created_count`, the file-level code or the row-error total. It holds **no** file
  name, cell value, email or name, and the logs hold none either. The uploaded bytes and parsed rows are discarded
  when the request ends, success or failure. If the product's single-user creation writes a per-user audit event,
  import writes the same event per created user (G-1).
- **Boundaries:** a rejected attempt is audited too; an audit-sink failure follows A-17.
- **Acceptance lines**
  - **R-10.1 Positive.** After Admin A's FX-1 import (S0): one audit record exists with actor `admin@example.com`,
    outcome `created`, rows 3, `created_count` 3, and a file size of 119 bytes (the length of FX-1). Surface: audit
    trail read (G-5). Confirmed by: api test reading the audit store.
  - **R-10.2 Failure.** FX-5 gives outcome `rejected`, `created_count` 0, row-error total 5; Non-admin's attempt gives
    outcome `forbidden` with actor `member@example.com`. Surface: audit trail read. Confirmed by: api test.
  - **R-10.3 Boundary (no personal data).** After FX-1, FX-5 and FX-13b, no log line, audit record or temp file
    contains `grace@example.com`, `Grace Hopper` or `Björk`, and the temp directory holds no file from the import
    (the set of files before and after is equal). Surface: log capture, audit read, filesystem listing. Confirmed by:
    api test with captured logs.
- **State and data:** audit trail retention is the product's existing policy, which is unknown (G-5); this spec fixes
  no retention period.

### R-11: The "Import users" screen walks an admin from file to result

- **Basis:** request ("admins upload a CSV"); A-1, A-8, A-12. **Change:** added.
- **Behaviour (states and transitions T-8 to T-12):**
  - *Empty*: shows the accepted columns (`email`, `name`, `role` optional), the limits (5,000 rows, 2 MiB) and a drop
    zone with a native "Choose CSV file" control; the submit control is disabled.
  - *File selected*: shows the file name and size; submit enabled; "Clear" returns to Empty. Choosing a new file
    replaces the old one and clears any earlier result. Dropping a file on the zone is identical to choosing it.
  - *Submitting*: submit and file controls disabled, an indeterminate busy indication and the text "Creating users…";
    no percentage that the server did not report.
  - *Succeeded*: `{N} users created` (`1 user created` when N is 1) and a link to the user list; the file is cleared.
  - *Rejected, file-level*: `Nothing was imported.` plus the file-error message and how to fix it; the file stays
    selected.
  - *Rejected, rows*: `Nothing was imported.` and `{T} problems found` (`1 problem found`), then a table of row,
    column, problem (and "duplicates row N" for `duplicate_in_file`); when truncated, a line `and {T-100} more`.
  - *Unknown outcome* (network failure, timeout or an unparseable or 5xx response): `We couldn't confirm the result.`
    and the advice to check the user list, and that sending the same file again will not create duplicates.
  - *Session ended or denied* (401/403): per R-1.
- **Error behaviour:** server rejections are rendered, never swallowed; a late response from a superseded submission
  cannot overwrite the current state (one submission is in flight at a time, by design).
- **Consumer outcome:** the admin always knows whether anything was created.
- **Acceptance lines**
  - **R-11.1 Positive.** Admin A opens Import users from S0, chooses FX-1, submits: Submitting is shown, then `3 users
    created`; the user list shows 7 users. Surface: UI. Confirmed by: ui flow with semantic queries and a held then
    released response.
  - **R-11.2 Failure (file-level).** Choosing FX-9 then submitting shows `Nothing was imported.` with the `file_empty`
    message; FX-16b shows the `file_too_large` message; the file is still shown as selected. Surface: UI. Confirmed
    by: ui flow.
  - **R-11.3 Failure (rows).** FX-5 shows `Nothing was imported.`, `5 problems found` and a table with five rows (3
    email, 4 name, 5 role, 6 email, 7 email "duplicates row 2"); 4 users remain. Surface: UI. Confirmed by: ui flow.
  - **R-11.4 Boundary (truncation).** FX-22c shows `150 problems found`, 100 table rows and `and 50 more`; FX-22a
    shows `100 problems found` and no "more" line. Surface: UI. Confirmed by: ui flow.
  - **R-11.5 Failure (unknown outcome).** With the network cut after the request is sent, the screen shows `We
    couldn't confirm the result.`, not success and not "nothing was imported", and resubmitting FX-1 once the network
    returns yields R-9.1's second-submission result if the first attempt had committed. Surface: UI. Confirmed by: ui
    flow with a held/dropped response.
  - **R-11.6 Boundary (inputs).** A drop of a file onto the zone gives the same File-selected state as choosing it;
    with no file the submit control is disabled; submitting while Submitting is impossible (R-9.4). Surface: UI.
    Confirmed by: ui flow.
- **UI planning views.** *Components:* file drop zone with native input, file summary, busy indicator, result banner,
  error table, "Clear" action; each with keyboard, focus and accessible-name behaviour (R-14). *Interaction model:*
  above; behaviour with the UI absent is the API of R-8. *Skin:* R-13.
- **Open gaps:** G-1 (where the screen lives in the console), G-5.

### R-12: Imported users are created exactly as single-user creation would create them

- **Basis:** A-7; the request implies imported users are ordinary users. **Change:** added.
- **Behaviour:** the initial status, onboarding (for example an invitation or set-password message) and any per-user
  audit event match what the product does for one user created by an admin. No password is read from the file.
- **Acceptance lines**
  - **R-12.1 Positive.** For the user `alan@example.com` created by FX-1 and for one created singly through the
    product, the stored status and onboarding artefacts (outbound message, token, audit event) are equal in kind
    (compared field by field, ignoring ids and timestamps). Surface: LIST/store and outbound-message capture.
    Confirmed by: integration test. **NOT-REPLAYED here:** the single-creation behaviour is unseen (G-1).
  - **R-12.2 Failure.** A rejected import (FX-5) sends no onboarding message and issues no token. Surface: outbound-
    message capture. Confirmed by: api test.
  - **R-12.3 Boundary.** Importing the 5,000 users of FX-17a sends 5,000 onboarding messages and not more or fewer,
    **if** single creation sends one; if sending is not atomic with the commit, the compensation rule is a G-1
    decision before this line is final. Surface: outbound-message capture. Confirmed by: integration test.
- **Open gaps:** G-1 (blocks R-12 and the initial-state clause of R-7; the rest of R-7 is not blocked).

## Non-functional requirements

Exclusions with reasons: availability, disaster recovery and capacity planning for a service are out (no new service
is introduced and the request sets no target); maintainability beyond the structure in `architecture.md` is out;
internationalised email is out (A-11); rate limiting is out (an existing platform concern; no number is invented).

### R-13: A deliberately designed interface, not scaffolding

- **Basis:** the deliverable has a UI (R-11); UI visual-direction guide; A-15. **Change:** added.
- **Visual direction (recorded):** named reference "light Gemini look and feel using Material 3 Expressive principles"
  as the *starting* appearance; the existing console's identity wins if one exists (G-1); web UI starts light with a
  dark option. The plan chooses concrete tokens, type and the screen's one visual signature (the drop zone is the
  focal point and visibly changes between idle, drag-over, selected and busy).
- **Acceptance lines (observed on the rendered screen, both themes, widths 360 and 1280 CSS px)**
  - **R-13.1 Positive (visual system).** One token set defines spacing, type scale, colours, radii and elevation; the
    screen uses only those tokens (a style check finds no raw colour or off-scale spacing value in the screen's own
    styles), and one icon set. Surface: UI source and rendered. Confirmed by: style scan + visual review of
    screenshots.
  - **R-13.2 Positive (themes).** Light is the default; dark applies under `prefers-color-scheme: dark`; both are
    complete (no unthemed region, text over surfaces meets R-14.3). Surface: UI. Confirmed by: screenshots in both.
  - **R-13.3 Positive (designed states).** Empty, file-selected, submitting, success, file-level rejection, row-error
    table with 1 row and with 100 rows plus the "more" line, unknown outcome, and denied each have a designed layout
    (none is an unstyled browser default). Surface: UI. Confirmed by: ui flow screenshots at both widths.
  - **R-13.4 Boundary (layout).** At 360 px and at 1280 px the page has no horizontal overflow
    (`scrollWidth <= clientWidth`); the error table fits its container at 360 px by reflow or by scrolling inside its
    own container. Surface: UI. Confirmed by: ui flow assertion at both widths.
  - **R-13.5 Boundary (motion).** Motion only explains a change (drop-zone state, result arrival); under
    `prefers-reduced-motion: reduce` computed animation and transition durations on the screen are 0. Surface: UI.
    Confirmed by: ui flow with the preference emulated.

### R-14: Accessible to keyboard and assistive technology

- **Basis:** R-11; the interface quality criteria of this stage. **Change:** added.
- **Acceptance lines**
  - **R-14.1 Positive (keyboard).** The whole flow (choose file, submit, clear, reach the error table and the user-list
    link) works with keyboard only; the drop zone is never the only way to supply a file. Surface: UI. Confirmed by:
    keyboard-only ui flow.
  - **R-14.2 Positive (names and announcements).** Every control has an accessible name; the result (`3 users
    created`, `Nothing was imported. 5 problems found`, unknown outcome) is announced through a polite live region;
    on completion focus moves to the result heading and returns to the file control after "Clear"; the error table
    is a real table with header cells. Surface: UI. Confirmed by: ui flow with accessible-tree queries.
  - **R-14.3 Boundary (contrast and focus).** Text meets WCAG 2.2 AA 4.5:1 (3:1 for large text and for UI component
    boundaries) in both themes; a visible focus indicator on every interactive element; no state is conveyed by colour
    alone. Surface: UI. Confirmed by: computed contrast on both themes plus an automated scan; the scan alone is not
    an audit, so a manual keyboard and screen-reader pass is a product-acceptance check (owner: tester, due
    product-acceptance).

### R-15: Capacity and responsiveness at the limits (bound unresolved)

- **Basis:** A-5, A-14. **Change:** added.
- **Operating condition:** one admin, FX-17a (5,000 rows, 155,011 bytes), the product's normal deployment.
- **Requirement:** the request reaches a terminal response (201 or 422) rather than being cut off, within the hosting
  platform's request limit. **Numeric time bound: unresolved**, because the platform and its limit are not known
  (G-3) and no baseline exists; none is invented. Interim acceptance line: the FX-17a run is timed and the
  duration and platform limit are recorded; the plan then sets a bound inside that limit. If it cannot finish inside
  the limit, AD-1 is revisited (asynchronous processing with a durable operation record) before the dependent plan.
- **Acceptance lines**
  - **R-15.1 Positive.** FX-17a returns 201 with its duration recorded against the platform's documented request
    limit. Surface: API on the real deployment target. Confirmed by: timed api test (the unit/local run proves only
    local speed). **Status: unresolved bound; G-3.**
  - **R-15.2 Boundary (memory).** Peak memory of the import handler stays bounded by the file limit plus parsed rows
    (no unbounded buffering), shown by R-2.3's counting-stream line plus FX-23. Surface: API. Confirmed by: R-2.3, R-2.5.

### R-16: Untrusted input is handled safely

- **Basis:** the file is attacker-controllable input from a privileged session. **Change:** added.
- **Acceptance lines**
  - **R-16.1 Positive (escaping).** After FX-20, the user `x1@example.com` is shown in LIST and in every product
    surface that renders names as the literal text `<script>alert(1)</script>`; no script runs. Surface: LIST/UI.
    Confirmed by: ui flow checking the text content and that no dialog/handler fires.
  - **R-16.2 Failure (no credentials by file).** FX-12 is rejected (R-3.2); no account created by import has a
    password or token chosen by the file. Surface: API. Confirmed by: api test.
  - **R-16.3 Failure (cross-site).** An import request without the product's anti-forgery proof (G-8) is refused and
    creates nothing. **Unresolved** until G-8 names the product's mechanism. Surface: API. Confirmed by: api test.
  - **R-16.4 Boundary (file name).** A file named `../../x"; DROP.csv` is processed by content only; the name appears
    in no path, log or audit record (R-10.3). Surface: API. Confirmed by: api test.

### R-17: Compatibility

- **Basis:** A-6. **Change:** added.
- **Requirement:** files produced by common spreadsheet tools' "CSV UTF-8" export are accepted; browsers follow the
  product's existing support policy (**unresolved**, G-6, no list is invented).
- **Acceptance lines**
  - **R-17.1 Positive.** FX-2 (BOM and CRLF, the shape those exports take) is accepted (R-2.1). Surface: API.
    Confirmed by: api test.
  - **R-17.2 Positive (real exports).** A real "CSV UTF-8" export of FX-1 from a spreadsheet application imports as
    FX-1 does. **Unverified:** no spreadsheet application is available to this stage. Owner: a tester with one;
    due: product-acceptance; surface: UI; it stays an open item until reported.

## Out of scope (request leaves it out; no R-n)

Updating or deactivating users from a file; partial import; dry-run or preview step (A-8); template download;
importing other attributes (phone, department, groups); password columns; scheduled or recurring imports;
importing from a URL or cloud drive; progress streaming for large files; downloading an error report file.

## Behaviour model

### Flows

| ID | Flow | R |
|---|---|---|
| F-1 | Admin chooses file, submits; server authorizes, parses, validates, commits atomically, audits; UI shows `N users created`. | R-1, R-2 to R-7, R-10, R-11 |
| F-2 | File-level rejection: first failing check in the check order stops processing; 413 or 422 `file_error`; nothing created; UI shows reason. | R-2, R-3, R-4, R-8 |
| F-3 | Row-level rejection: all rows validated together, errors gathered and capped; 422; nothing created. | R-5, R-6, R-8 |
| F-4 | Unauthorized: 401/403 before the file is read; audit `forbidden`. | R-1, R-10 |
| F-5 | Commit-time conflict: two imports race; the later commit is rejected whole (AD-4). | R-9 |
| F-6 | Unknown outcome: no response seen; admin checks the list, resubmits; duplicates impossible. | R-9, R-11 |

```mermaid
sequenceDiagram
  participant A as Admin (browser)
  participant S as Import endpoint
  participant U as User store
  participant L as Audit trail
  A->>S: F-1 POST file (multipart)
  S->>U: T-1 read current role of caller
  alt not admin / no session
    S-->>A: T-1 401 or 403 (F-4), file unread
    S->>L: audit forbidden
  else admin
    S->>S: T-2 size, UTF-8, structure, header, row cap (F-2)
    S->>U: T-3 read existing emails; validate all rows (F-3)
    alt any file or row error
      S-->>A: 413/422 with file_error or row_errors, nothing created
      S->>L: audit rejected
    else clean
      S->>U: T-4 insert all rows in ONE transaction
      alt an email was taken meanwhile (F-5)
        U-->>S: conflict, T-5 rollback
        S-->>A: 422 already_exists
      else commit ok
        S->>L: T-7 audit created (A-17)
        S-->>A: 201 created_count N
      end
    end
  end
```

### State inventory and transition ledger

Entity **import attempt** (transient, request-scoped, never persisted): Received, Authorized, Parsed, Validated,
Committed, RejectedFile, RejectedRows, Conflicted, Failed. Entity **user** (durable, user store): Absent, Created.
Entity **import screen** (transient, in the browser): Empty, FileSelected, Submitting, Succeeded, RejectedFile,
RejectedRows, UnknownOutcome, Denied. Cross-entity invariant: after any attempt, users created is 0 or N; the screen
never shows Succeeded unless the server returned 201.

| ID | R / F | Before, trigger and guard | Operation | After and observation | Failure and recovery | Cases |
|---|---|---|---|---|---|---|
| T-1 | R-1 F-4 | Received; caller role not admin (current role) | none; file unread | Rejected, 401/403; audit | n/a: nothing changed | R-1.2 to R-1.4 |
| T-2 | R-2 R-3 R-4 F-2 | Authorized; a file-level check fails (first in check order) | stop | RejectedFile, one `file_error`, 413/422 | n/a: nothing changed | R-2.2 to R-2.5, R-3.2, R-4.2 |
| T-3 | R-5 R-6 R-8 F-3 | Parsed; at least one row error | gather all, cap 100 | RejectedRows, 422 | n/a: nothing changed | R-5.2, R-6.2, R-8.3 |
| T-4 | R-7 F-1 | Validated; no errors | one transaction: insert N users | Committed, Absent to Created x N, 201 | any failure: rollback, 500 (R-7.3) | R-7.1, R-7.4 |
| T-5 | R-9 F-5 | Validated; an email is already taken at commit | rollback whole | Conflicted, 422 `already_exists` | retry yields the same rejection, harmlessly | R-9.2, R-9.3 |
| T-6 | R-7 | Validated; unexpected error before commit | rollback | Failed, 500 | resubmit is safe (A-12) | R-7.3 |
| T-7 | R-10 | Committed or rejected | one audit record | audited | sink fails after commit: A-17 | R-10.1, R-10.2 |
| T-8 | R-11 | Empty; user picks or drops a file | store file in memory | FileSelected | n/a | R-11.6 |
| T-9 | R-11 R-9 | FileSelected; submit (guard: not already Submitting) | send request, disable controls | Submitting; a second submit is ignored | n/a | R-9.4, R-11.1 |
| T-10 | R-11 | Submitting; response arrives | render by status | Succeeded / RejectedFile / RejectedRows / Denied | no or unparseable response: UnknownOutcome | R-11.1 to R-11.5 |
| T-11 | R-11 | any result; user picks another file | clear the result | FileSelected | n/a | R-11.6 |
| T-12 | R-11 | FileSelected or a rejection; "Clear" | drop file from memory | Empty; focus returns to the file control | n/a | R-14.2 |

Invalid or forbidden events: submit with no file is impossible (disabled control) and, by API, is `no_file`; a second
import event while one is pending is ignored by the UI and made safe by uniqueness on the server; the Succeeded state
accepts no resubmission of the same file except by choosing it again (it was cleared), and doing so is the R-9.1 case.

## State and information lifecycle

| State | Owner and location | Who may read | Simultaneous change | Ends | Quotas |
|---|---|---|---|---|---|
| Uploaded bytes | the request handler's memory (A-10) | nobody else | n/a: request-scoped | request end, success or failure | at most 2 MiB (read at most limit+1 bytes) |
| Parsed rows and validation result | handler memory | the submitting admin through the response only | n/a | request end | 5,000 rows, 100 errors listed |
| Created users | the existing user store | per the product's existing user-read authorization; never another client's import payload | unique normalised email at commit (R-9) | the product's existing deletion policy (unchanged) | unknown platform quota (G-3) |
| Audit record | the product's audit trail (G-5) | per its existing access policy | append-only | its existing retention (unknown, G-5) | n/a |
| Screen state, selected file, result | browser memory only; never local storage, never a URL | the admin at that browser | one request in flight | page leave or new file | n/a |

Personal data (emails, names): shown only to the submitting admin on success counts and in the user list under
existing rules; not stored beyond the user records; not in logs, audit, URLs or error bodies; discarded with the
request. Information one admin must not see: another admin's pending file or error report is never reachable (it
exists only in that request and that browser).

## Service boundary contracts

Boundaries: browser to import endpoint; endpoint to user store; endpoint to the audit trail; endpoint to the
product's onboarding mechanism (invite or message sender). No new service is added.

- **Current authority:** the user store's current role decides at submit (R-1.4); nothing is cached beyond that. If
  the product carries roles in a session token, how long a demotion takes to bite is unknown and not promised (G-4).
- **Freshness versus revocation:** existing-email checks read current store state, and the commit re-enforces
  uniqueness (R-9) because the earlier read can be stale by then.
- **Incremental state:** n/a: the whole file travels in one request; no resume, chunking or partial upload.
- **Async completion and recovery:** none by design (A-14, AD-1); the response is the completion. Lost response:
  R-9 unknown-outcome rule. If G-3 forces asynchronous work, a durable operation record, its processor and a
  recovery owner become required before planning, and R-9/R-11 are revised through the correction route.
- **Owned event coverage:** one audit record per attempt (R-10); authorization denial is covered by `forbidden`;
  onboarding messages are the product's existing events (R-12).

## Request-outcome traceability

| Request outcome | Acceptance lines |
|---|---|
| O-1 "admins" can do it, others cannot | R-1.1 to R-1.4 |
| O-2 "upload a CSV" | R-2.1 to R-2.5, R-3.1 to R-3.3, R-4.1 to R-4.3, R-11.1 to R-11.6, R-14, R-17 |
| O-3 "bulk-create users" from its rows | R-5.1, R-5.3, R-5.4, R-6.1, R-7.1, R-7.4, R-4.1, R-12 |
| O-4 (implied) bad input is handled without damage | R-5.2, R-6.2, R-6.3, R-7.2, R-7.3, R-8, R-9, R-10, R-16 |

Every modelled flow, state and transition traces to O-1 to O-4; no feature was added beyond them except the
defaults A-n. Each R has its flow and transitions above; R-13, R-15, R-16, R-17 are non-behavioural criteria and
trace to O-2 and O-4 through the UI and limits.

## Open gaps and unverified obligations

| ID | Under | Gap | Safe interim; what stays unready; confirming observation |
|---|---|---|---|
| G-1 | R-1, R-7, R-11, R-12, R-13 | No repository: the product's stack, admin role model, user record and initial state, single-user creation and its onboarding/audit, admin console identity and user list are unseen. | Defaults A-1, A-7, A-15. Unready: R-12, R-7's initial-state clause, R-11's placement, R-13's identity. Ready: R-2 to R-6, R-8 (pure rules). Confirm: read the repository's single-user creation and admin console at discovery or plan; if absent, the owner states them. |
| G-2 | R-1, R-5 | May an admin assign `admin` by import? Default A-13: same as single-user creation. | If single creation restricts it, import must match; unready: R-5 role clause only. Owner: product owner; due: plan. |
| G-3 | R-15 | Hosting platform and its request time and body limits are unknown, so no latency bound and AD-1 is provisional. | Time FX-17a on the target; record the platform's documented limit; unready: R-15 bound only. Due: plan (platform discovery). |
| G-4 | R-1 | Whether a demotion is honoured immediately where roles are cached in the session. | R-1.4 run on the real stack. Due: test stage. |
| G-5 | R-10 | Audit destination, retrieval access and retention are unknown. | Reuse the existing trail; no retention period invented; unready: the retention clause. Due: plan. |
| G-6 | R-17 | Browser support policy unknown; real spreadsheet exports unchecked (R-17.2, unverified, owner: a tester with a spreadsheet application, due: product-acceptance). | R-17.1 stands in. |
| G-7 | R-7, R-9 | Whether the store can do one atomic commit of up to 5,000 new users and guarantee case-insensitive email uniqueness at commit. | If not, A-3's guarantee cannot be met and this is a requirement conflict to resolve before planning R-7/R-9; confirm at plan with the store's documentation or a probe. |
| G-8 | R-16 | The product's anti-forgery/session mechanism for state-changing requests. | R-16.3 stays unresolved until named. Due: plan. |

Material requirement conflicts: **none open**. G-7 is the only item that would become one.

## Evidence for the replay duty (stage item 10)

Method: every fixture outcome above was walked by hand against the rules in this document, in the check order, from
S0, and the ordered cases were walked from their stated start (can the actor reach it, can each action happen in the
state the previous one leaves, can the named surface see the result). One result changed in the walk (the FX-1
byte count, below); the others matched the first draft. Byte counts are arithmetic.

- FX-16 base is 38 bytes: `email,name\n` 11 + `size@example.com,Size Edge\n` 27; padding to 2,097,152 and 2,097,153 bytes.
- FX-17a is 11 + 5,000 × 31 = 155,011 bytes (`user0001@example.com,User 0001\n` is 31 bytes); below both limits.
- FX-18's 254-character email is 64 + 1 + (63+1+63+1+61) = 254; the 255 form uses a 62-character last label.
- FX-1 is 119 bytes: `email,name,role\n` 16 + `ada@example.com,Ada Lovelace,admin\n` 35 +
  `grace@example.com,Grace Hopper,\n` 32 + `alan@example.com,Alan Turing,member\n` 36 (R-10.1 uses 119; an
  earlier draft of that line said 111, which this walk corrected).
- Ordered cases walked: R-1.4 (Admin B is admin in S0, so reaches the screen; the role change is a store setup; the
  submit then reads the current role, so 403); R-9.1 (second submit sees S0 + 3, so rows 2, 3, 4 are
  `already_exists`, total 3); R-9.2 (A and B both validate against S0; A commits first; B's commit meets
  `race@example.com`, so B is rejected whole, leaving 4 + 2 = 6 users); R-11.5 (the retry after a committed first
  attempt reproduces R-9.1, after an uncommitted one reproduces R-7.1).
- A scripted reference of these rules was written to the stage scratch directory (`oracle.py`) to recompute every
  fixture outcome mechanically; running it was **not permitted unattended** (interpreter calls need an approval that
  was not available), so those mechanical results are **NOT-REPLAYED: execution blocked**. The hand walk above is
  the only evidence, and no execution is claimed. Re-run it, or its product equivalent, at test-strategy.
- Not checkable here, left open with owner and phase: R-17.2 (tester, product-acceptance), R-15.1 and R-15.2 bound
  (plan, platform discovery), R-16.3 and R-12 (plan, repository), R-9.2 on a real store (test stage).

## Retired

none. No earlier requirement existed.

## Submission

**summary** (spec stage, 2026-11-21). Wrote `KNOWLEDGE/spec.md` (R-1 to R-17: R-1 to R-12 functional, R-13 to R-17
non-functional) and `KNOWLEDGE/architecture.md` (AD-1 to AD-4, all proposed). No repository, discovery, research or
baseline existed, so every requirement is **added** and nothing was observed to pass. The request is one sentence;
everything not in it is a labelled default, listed in `## Assumptions`: A-1 web product with admin role; A-2 columns
`email`, `name`, optional `role`; A-3 all-or-nothing; A-4 duplicates are errors, case-insensitive; **A-5 limits: file
2,097,152 bytes, 5,000 data rows, email 254 characters (local part 64, per RFC 5321 §4.5.3.1), name 1 to 100 code
points, 100 row errors reported**; A-6 UTF-8 with optional BOM, comma, LF or CRLF, strict RFC 4180 quoting; A-7 no
credential column, onboarding as single-user creation; A-8 single-step submit; A-9 no echo of submitted values; A-10 no
upload retention; A-11 simple ASCII email rule; A-12 retry-safe recovery; A-13 admins may assign either role; A-14
synchronous processing; A-15 UI direction (inherit identity, else light Gemini/Material 3 Expressive with dark
option); A-16 unknown columns rejected; A-17 audit-failure behaviour. Open gaps (each under its R-n, with what stays
unready): G-1 product baseline unseen (R-1, R-7, R-11, R-12, R-13); G-2 who may grant `admin` (R-1, R-5); G-3 platform
request limits, so R-15 has no numeric time bound and AD-1 is provisional; G-4 role-revocation lag; G-5 audit
destination and retention; G-6 browser policy and real spreadsheet exports (R-17.2, unverified, owner a tester, due
product-acceptance); G-7 store support for one atomic 5,000-row commit and a case-insensitive unique email
(R-7, R-9; becomes a material conflict if absent); G-8 anti-forgery mechanism (R-16.3). Open material requirement
conflicts: **none**. Independent work that may proceed: the pure CSV rules R-2 to R-6 and R-8. Replay evidence:
fixtures and ordered cases were hand-walked and one count corrected (FX-1 is 119 bytes); the scripted reference
check was written but **NOT-REPLAYED** because running it needed an approval that was unavailable. `backchain-check`
does not exist here (duty 11 left out), so no graph and no receipt exist.

**primary** (requirements carrying what the user asked for directly): R-1 (admins), R-2 (upload a CSV), R-7 (bulk-
create the users), R-11 (the upload screen an admin uses). Each needs a consumer-surface check or a passed lower-layer
test at product-acceptance.

**evidence_refs:** `KNOWLEDGE/spec.md` (whole); `KNOWLEDGE/architecture.md` `## Decisions` AD-1 to AD-4;
requirement sections `## Requirements` R-1 to R-12 and `## Non-functional requirements` R-13 to R-17; guides read:
`GUIDES/requirements-definition.md`, `GUIDES/behavioral-requirements.md#behavior-model`,
`#traceability-and-review`, `#actors-channels-and-state-ownership`, `GUIDES/platforms/ui.md#light-expressive-starting-point`,
`GUIDES/service-discovery.md`, `GUIDES/project-knowledge.md#maintained-product-requirements`,
`GUIDES/testing-and-documentation.md#stage-readiness-and-completion`; external: RFC 5321 §4.5.3.1 and RFC 4180
(fetched 2026-11-21); no discovery, research, baseline or backchain receipt exists.
