# User Administration: product specification

Status: draft produced by the spec stage, run on its own. Nothing is implemented, tested or verified.
Date of this revision: 2026-11-21.

## Source and baseline

- **Request (verbatim, 2026-11-21):** "Let admins upload a CSV to bulk-create users."
- **Baseline:** none. No repository, discovery result, research result, earlier spec or selected baseline exists in this run.
  Everything below is therefore *proposed intent*; no behaviour is *observed*. The existing user model, role model,
  authentication scheme, UI stack and hosting platform are **unknown** (see G-1 to G-7). Where this spec needs one, it states
  an assumption (A-n) rather than a fact.
- **Evidence kinds used below:** *Request* (the sentence above), *Assumption* (A-n: a default chosen so work can proceed,
  overridable by a person), *Gap* (G-n: an unresolved prerequisite or decision, kept open under its R-n), *Source-backed*
  (cited external document).
- **Structure and technology decisions** are AD-n entries in `architecture.md` and are referred to here only by ID.
  "Import API" and "Import page" below are the two consumer surfaces defined in AD-1.

## Request outcomes

| Outcome | Wording derived from the request | Requirements | Acceptance lines |
| --- | --- | --- | --- |
| O-1 | An admin can upload a CSV file. | R-1, R-2, R-11 | AC-1.1 to AC-1.4, AC-2.1 to AC-2.5, AC-11.1 to AC-11.3 |
| O-2 | The rows of that CSV become newly created users. | R-3, R-4, R-5, R-6 | AC-3.1 to AC-3.3, AC-4.1 to AC-4.4, AC-5.1 to AC-5.3, AC-6.1 to AC-6.3 |
| O-3 | (Implied by "upload ... to create") The admin learns what happened to the file. | R-7, R-11 | AC-7.1 to AC-7.3, AC-11.2 to AC-11.4 |
| O-4 | (Not requested; protections needed because the action is bulk and privileged) Safe repeated and concurrent use, traceability, data protection. | R-8, R-9, R-10, R-12 | AC-8.1, AC-8.2, AC-9.1, AC-9.2, AC-10.1 to AC-10.3, AC-12.1 |

## Requirements

Every requirement below has basis *Request, 2026-11-21* unless it says otherwise; "Preserved behaviour" is **none** for all of
them because no earlier spec or baseline exists (they are all *added*). "Pending" lists implementation and checks that do not
exist yet. Source-section locators: the only source is the request sentence; evidence limit: no product code or documentation
was available to read.

Fixtures used by several acceptance lines (all UTF-8, LF line endings, final newline present; line 1 is the header):

- **Accounts:** `admin1@example.com` (admin), `admin2@example.com` (admin), `member1@example.com` (non-admin).
- **FX-A `valid-3.csv`**
  ```
  email,name,role
  ada@example.com,Ada Lovelace,member
  grace@example.com,Grace Hopper,admin
  alan@example.com,Alan Turing,
  ```
- **FX-B `mixed-errors.csv`** (precondition: a user `exists@example.com` already exists)
  ```
  email,name,role
  ok1@example.com,Ok One,member
  not-an-email,Bad Email,member
  ok1@example.com,Dup Of Row 1,member
  ok2@example.com,,member
  ok3@example.com,Ok Three,superuser
  exists@example.com,Existing Person,member
  ```
- Limits for boundary cases are set by test configuration (see G-1): `max_rows = 5`, `max_bytes = 1024`.

### R-1 Only administrators can import

Behaviour: the import (Import API and Import page) is available only to an authenticated user who is an administrator *at the
time the request is authorised and again at commit*. Boundaries: authorisation is decided from the authoritative current
user/role record, not solely from a long-lived token claim (A-1). Error behaviour: unauthenticated callers are told to
authenticate; authenticated non-admins are refused; in both cases the body is not read and nothing is created. Consumer
outcome: a refused caller sees no import controls on the page and a refusal from the API.
Basis: request word "admins". Left out: any new role or permission model (see G-2 for what "admin" means).

- **AC-1.1** Positive: `admin1@example.com` posts FX-A and receives `outcome: created`. Failure: n/a: failures are AC-1.2 to
  AC-1.4. Boundary: n/a: no boundary distinct from AC-1.2. Surface: Import API. Confirmed by: integration test against a seeded
  store.
- **AC-1.2** Positive: n/a: covered by AC-1.1. Failure: `member1@example.com` posts FX-A and is refused (HTTP 403 per AD-1);
  user count is unchanged; no import audit record is written; an application log line records actor id and reason `not_admin`
  but no file content. Boundary: refusal happens before the body is read, so an over-limit file from `member1` is also 403, not
  413. Surface: Import API. Confirmed by: integration test, log capture.
- **AC-1.3** Positive: n/a. Failure: a request with no session/credential is refused (HTTP 401 per AD-1), nothing created.
  Boundary: an expired session behaves as unauthenticated. Surface: Import API. Confirmed by: integration test.
- **AC-1.4** Positive: n/a. Failure: `admin2@example.com` starts an import, the test pauses the request after parsing and
  before commit, `admin2` is demoted to non-admin, the request resumes: it is refused (403), zero users are created, no audit
  record is written. Boundary: the same demotion *after* commit completes leaves the committed import intact. Surface: Import
  API with a test pause seam (AD-3). Confirmed by: integration test.
- Pending: implementation, tests. Open: G-2, G-6.

### R-2 Accept one CSV file per import

Behaviour: the import takes exactly one file and reads it as CSV: comma-separated, `"` quoting with `""` as an escaped quote,
quoted fields may contain commas and newlines, CRLF or LF record separators, an optional UTF-8 byte-order mark ignored, lines
that are entirely empty ignored. The file is parsed by content; its name and declared media type do not decide validity.
Boundaries: size and row-count limits are configured values (`max_bytes`, `max_rows`, the latter counting data rows, header
excluded); exceeding either rejects the whole file before any user is created (G-1: default values unresolved).
Error behaviour (file-level codes, each rejecting the whole import, nothing created): `no_file`, `empty_file` (zero bytes),
`no_data_rows` (header only), `invalid_encoding` (not valid UTF-8), `malformed_csv` (for example an unterminated quote),
`file_too_large`, `too_many_rows`. Checks run in this order and the first file-level failure among the first six stops processing: `no_file`,
`file_too_large`, `empty_file`, `invalid_encoding`, `malformed_csv`, then the header checks of R-3 (which report all their
errors together), then `no_data_rows`, then `too_many_rows`. Consumer outcome: the result report (R-7) names the code.
Basis: request word "CSV". Left out: other formats (XLSX, TSV), multiple files per request, other encodings, custom
delimiters.

- **AC-2.1** Positive: FX-A with CRLF line endings and a leading BOM yields the same result as FX-A (3 users created).
  Failure: n/a: see AC-2.2 to AC-2.4. Boundary: a quoted name `"Hopper, Grace"` keeps the comma; a quoted name containing a
  newline is one record. Surface: Import API. Confirmed by: integration test, one case per variant.
- **AC-2.2** Positive: n/a. Failure: a request without a file part returns `outcome: rejected`, `file_errors: [no_file]` (400);
  a 0-byte file returns `empty_file`; `email,name,role\n` returns `no_data_rows`; the byte `0xFF` in a name returns
  `invalid_encoding`; `email,name\n"ada@example.com,Ada\n` returns `malformed_csv`. Every case leaves the user count unchanged.
  Boundary: n/a: the empty and header-only cases are the boundaries. Surface: Import API. Confirmed by: integration test.
- **AC-2.3** Positive: a data-row count of exactly `max_rows` (5) is accepted when otherwise valid. Failure: 6 data rows
  returns `too_many_rows` (422) and nothing is created, not even the first 5. Boundary: blank lines do not count toward the
  limit. Surface: Import API with `max_rows = 5`. Confirmed by: integration test.
- **AC-2.4** Positive: a file of exactly `max_bytes` (1024) bytes, otherwise valid, is accepted. Failure: 1025 bytes returns
  `file_too_large` (413). Boundary: the size check does not require the server to buffer the whole oversize body first (the
  request is cut off once the limit is passed; AD-2). Surface: Import API with `max_bytes = 1024`. Confirmed by: integration
  test; the no-full-buffering clause is confirmed by streaming a body larger than the limit and observing the server stops
  reading (method decided at test design).
- **AC-2.5** Positive: a file named `users.txt` with valid CSV content is accepted. Failure: a file named `users.csv` holding
  PNG bytes (first byte `0x89`, not valid UTF-8) is rejected `invalid_encoding`. Boundary: n/a. Surface: Import API. Confirmed by: integration
  test.
- Pending: implementation, tests. Open: G-1.

### R-3 Header contract

Behaviour: line 1 is the header. Header names are matched after trimming whitespace and ignoring case. Required columns:
`email`, `name`. Optional column: `role`. Column order is free. Boundaries: any other column (including `password`) is an error
(A-2: strict, so nothing is silently ignored, and so a password can never travel in the file). A column appearing twice is an
error. Error behaviour: header problems are file-level, are all listed together, stop row processing and create nothing:
`missing_column` (one entry per missing required column, naming it), `unknown_column` (naming it), `duplicate_column` (naming
it). Consumer outcome: the report lists each header error with the column name.
Basis: request word "bulk-create users"; field set is A-2/A-3, see G-3.

- **AC-3.1** Positive: header `Name , EMAIL` (reordered, odd case, spaces) with row `ada@example.com,Ada Lovelace` creates one
  user with no role given (defaults to `member`, R-4). Failure: n/a: AC-3.2. Boundary: the `role` column may be absent entirely.
  Surface: Import API. Confirmed by: integration test.
- **AC-3.2** Positive: n/a. Failure: header `email,phone` returns `file_errors` containing `missing_column: name` and
  `unknown_column: phone`; header `email,name,password` returns `unknown_column: password`; header `email,name,email` returns
  `duplicate_column: email`. No rows are evaluated (no `row_errors`). Boundary: a header with only `name` reports
  `missing_column: email`. Surface: Import API. Confirmed by: integration test.
- **AC-3.3** Positive: n/a. Failure: n/a: n/a, no distinct failure beyond AC-3.2. Boundary: the page's format help (R-11) lists
  exactly the required and optional columns of this requirement. Surface: Import page. Confirmed by: UI test reading the help
  text against the contract.
- Pending: implementation, tests. Open: G-3.

### R-4 Row validation

Behaviour: each data row is checked independently of the others; the first failing rule in this order gives the row's single
error code: `wrong_field_count`, `invalid_email`, `missing_name`, `invalid_role`. Rules, with values trimmed of surrounding
whitespace first:
- field count equals header column count;
- `email`: exactly one `@`; non-empty local part of at most 64 octets; domain containing at least one `.`, not starting or
  ending with `.`; no whitespace; total length at most 254 octets. The 64 and 254 limits are source-backed: RFC 5321 s4.5.3.1.1
  (local-part 64 octets) and s4.5.3.1.3 (path 256 octets including the two angle brackets, so 254 for the address; the 254 is
  derived by subtraction, not quoted). Checked 2026-11-21 against the RFC text. Deliverability is not checked (A-4);
- `name`: non-empty after trimming (a maximum length is unresolved, G-3);
- `role`: empty or absent means `member`; otherwise case-insensitively `member` or `admin`; stored lower-case.
The email is normalised to lower case for storage and comparison. Consumer outcome: invalid rows appear in the report with
physical line number, the submitted email text and the code.
Basis: request. Left out: phone, department, groups, any field beyond email/name/role (G-3); address deliverability checks;
Unicode (IDN) normalisation beyond lower-casing.

- **AC-4.1** Positive: FX-A line 4 (`alan@example.com,Alan Turing,` empty role) creates `alan@example.com` with role `member`.
  Failure: n/a: AC-4.2. Boundary: `Grace@Example.COM` is stored as `grace@example.com`; role `Admin` is stored as `admin`.
  Surface: Import API then the user store read. Confirmed by: integration test reading the created records.
- **AC-4.2** Positive: n/a. Failure: FX-B (precondition above) returns exactly `row_errors` for lines 3 (`not-an-email`,
  `invalid_email`), 5 (`ok2@example.com`, `missing_name`), 6 (`ok3@example.com`, `invalid_role`), plus the R-5 errors of lines
  4 and 7 (AC-5.1, AC-5.2); line 2 is not listed. A row `a@b` returns `invalid_email` (domain has no dot); `a@b..c` is accepted
  (its domain contains a dot and neither starts nor ends with one; consecutive dots are not checked, A-4). Boundary: a 65-octet local part is `invalid_email`, a 64-octet one is accepted; a 254-octet address is
  accepted, 255 is `invalid_email`. Surface: Import API. Confirmed by: integration test; the exact FX-B result is also asserted
  in AC-7.1.
- **AC-4.3** Positive: n/a. Failure: a row with one field fewer than the header (`ada@example.com` under `email,name`) returns
  `wrong_field_count` for its line; a row failing both `invalid_email` and `missing_name` reports only `invalid_email`.
  Boundary: n/a. Surface: Import API. Confirmed by: integration test.
- **AC-4.4** Positive: a `name` of `<script>alert(1)</script>` is accepted and stored unchanged. Failure: n/a. Boundary: the
  value is never interpreted as markup anywhere it is shown (AC-10.3). Surface: Import API. Confirmed by: integration test.
- Pending: implementation, tests. Open: G-3.

### R-5 Uniqueness of email

Behaviour: an email (compared normalised) must be unique within the file and must not belong to any existing user.
`duplicate_in_file` is reported on every row after the first row with the same normalised email, whether or not that first row
is itself valid. `already_exists` is reported on a row that would otherwise be valid but whose email is an existing user. The
import only creates; it never updates, overwrites or merges an existing user. Boundaries: "existing user" means any record
holding that normalised email including deactivated ones (A-5; G-4). Precedence: R-4 codes come before R-5 codes;
`duplicate_in_file` before `already_exists`. Consumer outcome: both appear in the report with line and email.
Basis: request word "create" (create-only is A-6). Left out: update-or-insert, skipping existing rows, merging.

- **AC-5.1** Positive: n/a. Failure: FX-B line 4 (second `ok1@example.com`) returns `duplicate_in_file`; a case variant
  `OK1@Example.com` on a later line also does. Boundary: the first occurrence (line 2) is not reported as a duplicate.
  Surface: Import API. Confirmed by: integration test.
- **AC-5.2** Positive: n/a. Failure: FX-B line 7 (`exists@example.com`) returns `already_exists`; `Exists@Example.com`
  does as well. Boundary: if `exists@example.com` appears on two lines, the first returns `already_exists` and the second
  `duplicate_in_file`. Surface: Import API. Confirmed by: integration test.
- **AC-5.3** Positive: after FX-A has succeeded, importing `email,name\nAda@Example.com,Ada Again` is rejected with
  `already_exists` on line 2 and the stored Ada record is unchanged (name still `Ada Lovelace`). Failure: same. Boundary: n/a.
  Surface: Import API then store read. Confirmed by: integration test.
- Pending: implementation, tests. Open: G-4.

### R-6 All-or-nothing creation

Behaviour (A-7): a file is imported entirely or not at all. If the file has no file-level error and no row error, every row is
created in a single atomic commit and `outcome` is `created`. If any file-level or row error exists, no user is created and
`outcome` is `rejected` with **all** errors listed, so one correction pass is enough. Each created user has: the normalised
email, trimmed name, role (default `member`), a `created_by` reference to the importing admin, and the import identifier (R-9).
Created users hold no credential from the import and receive no message from it (R-12). Boundaries: the commit
re-checks email uniqueness inside the same atomic step, so a user created by someone else after validation turns the whole
import into a rejection (R-8). Error behaviour: if the commit itself fails (store error, timeout), nothing is persisted, the
Import API answers `outcome: failed` with the import identifier (HTTP 500 per AD-1), and a retry of the same file is safe.
Consumer outcome: after `created`, every row's user exists; after `rejected` or `failed`, the user set is exactly what it was.

- **AC-6.1** Positive: `admin1` imports FX-A: result `outcome: created`, `rows_total: 3`, `rows_created: 3` (201); exactly
  `ada@example.com` (member), `grace@example.com` (admin), `alan@example.com` (member) now exist, each with `created_by` =
  `admin1`. Failure: n/a: AC-6.2, AC-6.3. Boundary: a one-data-row file creates one user. Surface: Import API, then user store
  read. Confirmed by: integration test.
- **AC-6.2** Positive: n/a. Failure: with the FX-B precondition, importing FX-B returns `outcome: rejected`, `rows_total: 6`,
  `rows_created: 0`; the user count before and after is identical; line 2's `ok1@example.com` was **not** created even though
  that row was valid. Boundary: a file with 4 valid rows and 1 invalid row creates none. Surface: Import API, then store read.
  Confirmed by: integration test comparing the full user set before and after.
- **AC-6.3** Positive: n/a. Failure: with a store whose write is made to fail on the third insert (fault injected at the
  store boundary), FX-A returns `outcome: failed` and none of the three users exist; re-sending FX-A after the fault is removed
  returns `created`. Boundary: n/a. Surface: Import API with a fault-injecting store double. Confirmed by: integration test
  (a double is acceptable here because it is the only way to cause the fault; the real atomic behaviour is separately
  confirmed against the real store engine in AC-8.1).
- Pending: implementation, tests. Open: G-2 (admin role assignment), G-4.

### R-7 Result report

Behaviour: every import that gets past authorisation returns one structured result: `outcome` (`created`, `rejected` or
`failed`), `import_id`, `rows_total` (data rows, ignoring blank lines), `rows_created`, `file_errors` (list of
`{code, column?}`), `row_errors` (list of `{line, email, code}` ordered by line; `line` is the physical 1-based line on which
the record starts, header = line 1, so it matches a spreadsheet row; `email` is the submitted text, empty if blank), and, on
`created`, `created` (list of `{line, email, role}`). `file_errors` and `row_errors` are never both non-empty. Boundaries:
the lists are bounded by `max_rows`. The result is returned once and is not stored for later retrieval (A-8: no import history
page; the audit record R-9 holds counts only). Consumer outcome: the admin can fix and re-upload using only the report.
Basis: implied by request.

- **AC-7.1** Positive: FX-A result is exactly `{outcome: created, rows_total: 3, rows_created: 3, file_errors: [],
  row_errors: [], created: [lines 2, 3, 4 with emails ada@, grace@, alan@example.com and roles member, admin, member]}`.
  Failure: FX-B result (precondition above) is exactly `outcome: rejected`, `rows_total: 6`, `rows_created: 0`,
  `file_errors: []`, `row_errors` = `[3 invalid_email, 4 duplicate_in_file, 5 missing_name, 6 invalid_role, 7 already_exists]`
  with emails `not-an-email`, `ok1@example.com`, `ok2@example.com`, `ok3@example.com`, `exists@example.com`. Boundary: a quoted
  multi-line record starting on line 3 reports `line: 3`. Surface: Import API. Confirmed by: integration test with exact
  deep-equality on the body (not a status-only or count-only check).
- **AC-7.2** Positive: n/a. Failure: a header error never comes with `row_errors`. Boundary: n/a. Surface: Import API.
  Confirmed by: covered by AC-3.2's assertion; separately asserted here as a schema invariant test.
- **AC-7.3** Positive: n/a. Failure: the `failed` body carries `import_id` and no `created` or error lists. Boundary: n/a.
  Surface: Import API. Confirmed by: AC-6.3's assertion.
- Pending: implementation, tests. Open: none.

### R-8 Concurrent and repeated submissions

Behaviour: the user store, not application memory, enforces uniqueness of normalised email, so two overlapping imports can
never create the same email twice. Of two overlapping imports that both contain an email absent at validation time, one commits
and the other is rejected as a whole with `already_exists` on its conflicting rows only. Repeating a successful upload
creates nothing and reports `already_exists` for every row (AC-5.3 form); repeating a rejected upload after fixing the file
simply imports it. The page prevents a second submission while one is pending (R-11). Consumer outcome: no duplicate user, and
the losing admin is told which rows collided.
Basis: request implies bulk privileged use; resolution rule is A-9.

- **AC-8.1** Positive: n/a. Failure: with the real store engine, `admin1` sends C1 = `email,name\nrace@example.com,Racer One`
  and `admin2` sends C2 = `email,name\nrace@example.com,Racer Two\nextra@example.com,Extra`; both are paused after validation
  and before commit, then released C1 first. Result: C1 `created`; C2 `rejected` with `row_errors` = `[2 already_exists
  race@example.com]`; exactly one `race@example.com` user (`Racer One`); `extra@example.com` does **not** exist. Released C2
  first: C2 `created` (users `race@example.com` = `Racer Two` and `extra@example.com`), C1 `rejected` with
  `[2 already_exists]`. Boundary: both orders are run. Surface: Import API with the pause seam (AD-3). Confirmed by:
  integration test against the real store engine; walk of both orders recorded under "Replay record".
- **AC-8.2** Positive: n/a. Failure: re-sending FX-A after a `created` result returns `rejected` with `already_exists` on
  lines 2, 3, 4 and `rows_created: 0`. Boundary: n/a. Surface: Import API. Confirmed by: integration test.
- Pending: implementation, tests. Open: none.

### R-9 Audit record

Behaviour: each import by an administrator that reaches a decision stores one audit record: `import_id`, actor id, time of
completion, `outcome`, `rows_total`, `rows_created`, and a count per error code. It stores **no** emails, names or file
content and no file name. For `created`, the audit record is written in the same atomic commit as the users, so a created
user always has an audit record and an audit record saying `created` always has its users. For `rejected` and `failed`, the
record is written afterwards on a best-effort basis; if that write fails the failure is logged and the business result is
unchanged (explicit choice: no fail-closed for non-committing outcomes). Retention follows the application's existing audit
retention (G-5). Consumer outcome: an operator can answer who imported how many users, when, and with what outcome.
Basis: A-10 (traceability for a bulk privileged action).

- **AC-9.1** Positive: after AC-6.1 one audit record exists: actor `admin1`, outcome `created`, `rows_total 3`,
  `rows_created 3`, equal `import_id` to the one in the result and in each created user. Failure: after AC-6.2 one record:
  outcome `rejected`, `rows_created 0`, error counts `{invalid_email: 1, duplicate_in_file: 1, missing_name: 1,
  invalid_role: 1, already_exists: 1}`. Boundary: after AC-6.3 (`failed`) the record is present if the audit store is up.
  Surface: audit store read. Confirmed by: integration test; assert no email string from the fixtures occurs in any stored
  audit field.
- **AC-9.2** Positive: n/a. Failure: with the audit write failing for a `rejected` import, the Import API still returns
  `rejected` with the full report and an error log line is emitted. Boundary: with the audit write failing inside the `created`
  commit, the whole import fails atomically (`failed`, no users). Surface: Import API with a fault-injecting audit double.
  Confirmed by: integration test.
- Pending: implementation, tests. Open: G-5.

### R-10 Protection of uploaded data

Behaviour: the file and its rows are personal data. They are held only for the duration of the request, are not written to
durable storage by the import (any temporary file created by the platform's multipart handling is removed when the request
ends, including on failure), and never appear in application logs, metrics or audit records. Logs carry `import_id`, actor id,
outcome, counts and error-code tallies only. Every value from the file that is echoed back (emails in `row_errors`,
`created`) is output-encoded for the context in which it is shown, so markup or script in a field is displayed as text.
Values are written to the store only through parameterised or equivalent injection-safe operations. The import does not
neutralise spreadsheet-formula prefixes (`=`, `+`, `-`, `@`) in stored values; that is the duty of any future export (left
out, recorded so it is not lost). Basis: A-10, platform security practice.

- **AC-10.1** Positive: n/a. Failure: after running FX-B and FX-A, captured logs and metrics contain none of the fixture
  emails or names. Boundary: also none when the import fails (AC-6.3). Surface: log/metric capture. Confirmed by: integration
  test with string search over all captured sinks.
- **AC-10.2** Positive: n/a. Failure: after a request that fails mid-way, no file derived from the upload remains in the
  process's temporary directory. Boundary: n/a. Surface: filesystem listing of the configured temp directory before and after.
  Confirmed by: integration test.
- **AC-10.3** Positive: a row `<img src=x onerror=alert(1)>,Bad,member` is reported with that text visible literally and
  no script runs. Failure: same. Boundary: the same literal-text rendering holds in the success list for a name or email
  that contains `<` and `&`. Surface: Import page. Confirmed by: browser test asserting the DOM text equals the input and
  that no `img`/`script` element was created from it.
- Pending: implementation, tests. Open: none.

### R-11 Import page

Behaviour: administrators see an import page in the admin area with: a short description of the format (required columns
`email`, `name`, optional `role` with its two values; the limits that apply; that nothing is created if any row is wrong);
one file chooser that is also a drop target; the chosen file's name and size; and one primary "Import" action. States, each
designed (not default browser rendering), and what each says truthfully:
1. *Idle*, no file: format help, disabled primary action.
2. *File chosen*: name and size, enabled action, a way to change the file.
3. *Sending*: the action is disabled and the page shows upload progress while bytes are sent, then an indeterminate
   "Creating users…" once sending is complete. It never shows success before the Import API answers.
4. *Created*: the count created and the list of created users, plus an action to import another file.
5. *Rejected*: states plainly "No users were created", then file-level errors in words, or a table of row errors (line, email,
   problem in words). A summary line states how many rows have problems out of how many. The file can be replaced and sent
   again.
6. *Failed or unknown outcome* (server error, or the connection broke after sending began): states that the result is not
   confirmed, that nothing is assumed, and tells the admin to look at the user list before sending again; sending again is
   safe (R-8). The `import_id`, if known, is shown.
7. *Refused* (not signed in or no longer an admin): says so and offers sign-in, and keeps no created/rejected content.
After a result, keyboard focus moves to the result heading; a polite live region announces state changes (sending,
created, rejected, failed). The result survives only in the open page (no import history, A-8). Basis: request word "upload"
implies an upload surface; A-11 assumes a page in addition to the API.

- **AC-11.1** Positive: as `admin1`, choosing FX-A and activating Import ends in state *Created* showing `3` and the three
  emails. Failure: choosing FX-B ends in *Rejected* showing "No users were created", "5 of 6 rows have problems" and five table
  rows with lines 3, 4, 5, 6, 7. Boundary: a file of 0 bytes ends in *Rejected* with a file-level message, not an empty table.
  Surface: Import page in a browser. Confirmed by: browser test with stable accessible queries.
- **AC-11.2** Positive: during *Sending* (response held by a test proxy) the Import action is disabled and a progress/status
  message is present; pressing Enter or clicking again sends no second request (exactly one request observed). Failure: with
  the connection dropped after the body is sent, the page shows state 6, not success and not "nothing happened". Boundary: when
  the held response is then released as `created`, the page moves to *Created* (the late answer is not discarded). Surface:
  Import page. Confirmed by: browser test with a controllable network layer.
- **AC-11.3** Positive: keyboard only: Tab reaches the file chooser and the Import action; Enter/Space activate them; after a
  result focus is on the result heading and the live region text changed. Failure: n/a. Boundary: with reduced motion
  requested, no animated transition runs and state still changes. Surface: Import page. Confirmed by: browser test
  (focus/role assertions) plus an automated accessibility scan; the scan is not a complete accessibility audit (recorded
  limit).
- **AC-11.4** Positive: `member1` sees no import entry and the page route shows state 7. Failure: n/a. Boundary: session
  expiry during *Sending* ends in state 7. Surface: Import page. Confirmed by: browser test.
- Pending: implementation, tests. Open: G-6 (existing admin shell and visual identity).

### R-12 Imported users and onboarding (scope boundary)

Behaviour: the import creates user records only. It sets no password, sends no email or invitation, and starts no
session (A-12). How a created user first gains access is a separate capability (G-7). Boundaries: a `password` or similar
column is rejected by R-3. Consumer outcome: the report and page do not claim the users can sign in.
Basis: A-12; the request says "create" only.

- **AC-12.1** Positive: n/a. Failure: after AC-6.1, no outbound message was attempted (mail double records zero sends) and
  the three users have no stored credential; the success text does not say users can sign in. Boundary: n/a. Surface:
  Import API with a mail/credential double and store read; Import page text. Confirmed by: integration and browser test.
- Pending: implementation, tests. Open: G-7 (**blocks** any claim that imported users can log in; does not block the import
  itself).

## Non-functional requirements

| ID | Attribute | Condition, bound or criterion | Verification | Status |
| --- | --- | --- | --- | --- |
| NFR-1 | Security: access | No import action succeeds for a non-admin or an actor demoted before commit (R-1). | AC-1.2 to AC-1.4 | accepted criterion |
| NFR-2 | Security: web | Import API honours the application's existing cross-site request protection for state-changing calls (e.g. CSRF token or same-site policy) | integration test: a cross-site form post without the protection is refused | bound to the existing scheme; scheme unknown (G-6) |
| NFR-3 | Security: injection and output | R-10: parameterised writes, output encoding. | AC-4.4, AC-10.3 | accepted criterion |
| NFR-4 | Privacy | R-10 and R-9: no personal data in logs, metrics, audit; no durable copy of the file. | AC-10.1, AC-10.2, AC-9.1 | accepted criterion |
| NFR-5 | Reliability, integrity | All-or-nothing commit; no partial user set after any failure (R-6, R-8). | AC-6.2, AC-6.3, AC-8.1 | accepted criterion |
| NFR-6 | Capacity | `max_bytes` and `max_rows` are enforced from configuration. **Numeric defaults are unresolved** (G-1); no value is invented. Tests use 1024 and 5 only to exercise boundaries. | AC-2.3, AC-2.4 | bound unresolved |
| NFR-7 | Latency and request lifetime | An import at the row limit must finish inside the hosting platform's request time limit, because processing is synchronous (AD-2). No numeric latency target is set: the request gives none and the platform limit is unknown (G-1). | load check at the chosen `max_rows` on the target runtime once G-1 is resolved | bound unresolved; blocks only the default limit values and AD-2's confirmation |
| NFR-8 | Memory | The file is processed without holding more than `max_bytes` of it, and an oversize body is cut off once the limit is exceeded. | AC-2.4 | accepted criterion |
| NFR-9 | Observability | Each import produces one structured log line (import id, actor id, outcome, counts, error tallies) and one audit record (R-9); refusals log actor id and reason. Required audit records are not subject to log sampling or debug switches. | AC-1.2, AC-9.1 | accepted criterion |
| NFR-10 | Compatibility | Import page works in the current stable releases of Chrome, Firefox, Safari and Edge (A-13). | browser test on at least one engine per family, or documented limit | assumption |
| NFR-11 | Accessibility | Import page meets WCAG 2.2 level AA for text and control contrast (4.5:1 text, 3:1 large text and components), has visible focus on every control, full keyboard operation, accessible names, and a polite live region for async state. | AC-11.3 plus contrast measurement of the chosen tokens in both themes | accepted criterion; AA is the standard named by this stage, not a user-set target |
| NFR-12 | Interface quality (deliverable has a UI) | A deliberately designed, polished interface, not unstyled scaffolding. Observable: (a) one visual system: spacing scale, type scale, palette tokens with a light and a dark theme, the dark theme chosen by the user's system preference with a manual override; (b) designed idle, sending, created, rejected, failed and refused states (R-11); (c) layout with no horizontal page overflow at 360 px and at 1440 px wide, the row-error table reflowing (for example stacked) at the narrow width; (d) visible focus states and AA contrast in both themes; (e) motion only to explain a change (progress, state transition), none when reduced motion is requested; (f) one icon set. **Visual reference and starting appearance (UI visual-direction guide):** light Gemini look and feel using Material 3 Expressive principles: airy light canvas, tonal rounded surfaces, friendly precise sans-serif from local fonts, one restrained saturated accent, confident primary action, subtle luminous accents, light first with the dark option. Precedence: an existing admin console identity (G-6) overrides this reference. The primary activity, choosing a file and seeing the outcome, gets the strongest position and weight. The concrete tokens are chosen at planning. | browser test at two widths, both themes and reduced motion; rendered-state review against (a) to (f); contrast measurement | accepted criterion; concrete treatment pending |
| NFR-13 | Maintainability, testability | The two seams AC-1.4 and AC-8.1 need (pause between validation and commit; fault injection at the store and audit boundaries) exist only in test builds or test configuration, not as production endpoints. | review of AD-3 implementation | accepted criterion |
| NFR-14 | Excluded | Availability target, throughput, multi-region, cost budget: excluded: a single bounded synchronous admin action with no promised volume. Compliance regime (for example GDPR retention): not assessed, the application's owner is unknown (G-5). |  | justified exclusion / gap |

## State and data assessment

| Carrier | Identity | Change | Before invariant | After invariant | Recovery | Checks |
| --- | --- | --- | --- | --- | --- | --- |
| User records (existing store, shape unknown, G-3) | normalised email, unique | **created** only; never updated or deleted by the import | set U, each email unique | `created`: U plus exactly the file's rows, still unique; `rejected`, `failed`: exactly U | the commit is one atomic unit; rollback on any error; retry is safe | AC-6.2, AC-6.3, AC-8.1, AC-8.2 |
| Audit record | `import_id` | **created** (one per import reaching a decision) | n/a | `created`: committed with the users; other outcomes: best-effort after | best-effort write failure is logged, not retried | AC-9.1, AC-9.2 |
| Uploaded file | request | **transient**: read, never stored | n/a | no durable copy; temp files removed | cleanup at request end including failure | AC-10.2 |
| Result report | `import_id` | **transient**: returned once, not stored | n/a | exists only in the response and the open page | re-upload (safe) | AC-8.2, AC-11.2 |
| Admin role | actor | **observed** (checked at start and at commit), never changed | n/a | unchanged | n/a | AC-1.2 to AC-1.4 |
| Sessions, credentials, email, other user fields | n/a | **out of scope** (R-12, G-3, G-7) | | | | AC-12.1 |

No migration of existing data is needed beyond what a unique constraint on normalised email may require; whether the existing
store already has one is unknown (G-4, G-3).

## Service boundaries

The only boundary is Import page (browser) to Import API to the existing user/audit store (AD-1). Contract points:
- **Current authority:** the user store's role record, read per request and again at commit (R-1, AC-1.4). Freshness versus
  revocation: no caching of the admin decision beyond the request.
- **Incremental state:** n/a: the import reads no remote snapshot beyond the existence check inside the commit.
- **Async completion and recovery:** none by design (AD-2): the answer to the request is the final outcome; a lost response
  is the *unknown outcome* of R-11 state 6, recovered by re-upload (R-8). If G-1 yields a limit the platform cannot serve
  synchronously, AD-2 must be reopened before the limit is adopted.
- **Owned events:** audit record and one log line per import (NFR-9). No events are emitted to other systems. No email service,
  queue, broker or cache is added.

## Interaction and lifecycle

| State | Owner and location | Who may read it | Simultaneous changes | Ends and is removed by | Runtime limits met |
| --- | --- | --- | --- | --- | --- |
| Uploaded file bytes | the Import API process, memory (and platform temp file if used) | nobody but the processing code | per-request, no sharing | end of request | `max_bytes`, `max_rows` |
| Created users | existing user store | per the existing user-read rules (unknown) | unique key; first committer wins (R-8) | outside this feature | store limits unknown |
| Audit record | audit store | operators with audit access (G-5) | independent per import | retention policy (G-5) | n/a |
| Result report | response body, the open page | only the importing admin | n/a | page navigation or reload | n/a |
| Page draft state (chosen file, request state) | the page, local memory | the admin's browser only | one pending request at a time | page reload (file must be chosen again) | n/a |

Personal data: emails and names are shown only to the importing admin on the page, stored only as user records,
never logged, never in audit; the uploaded file is not kept. One user cannot see another admin's result. No sharing,
identity or persistence beyond what R-6/R-9 need is added. UI premises: *components* are a file chooser/drop target, a status
region, a result summary and a row-error table; *interaction* is a single linear flow (choose, import, read result, retry)
with truthful async feedback (R-11); *skin* per NFR-12.

## Domain rules the request leaves out (bounded under their requirements)

- R-2: other file formats, delimiters and encodings; multiple files; resumable upload.
- R-4: any field beyond email/name/role; email deliverability or verification; internationalised domain handling.
- R-5/R-6: update, upsert, skip-existing or partial-import modes; a dry-run/preview-only call; delete via CSV.
- R-7/R-11: import history, downloadable error CSV, downloadable template, progress for server-side work, notifications.
- R-9: retention schedule and audit viewer.
- R-12: invitation email, password set flow, forced password change, single sign-on provisioning.

## Open gaps

- **G-1** (R-2, NFR-6, NFR-7) Default values for `max_bytes` and `max_rows`, and the hosting platform's request time limit. Owner:
  product owner with the runtime owner. Needed before: the defaults are adopted and NFR-7 is verified. Not blocking: the
  enforcement behaviour, which is specified and testable with configured values.
- **G-2** (R-1, R-4) What "admin" is in the existing system, and whether any admin may create other admins (A-14 assumes
  yes, audited). Owner: product owner. Needed before: R-1 is implemented against a real role model; escalation risk is
  accepted or `role` is removed from the file.
- **G-3** (R-3, R-4) The existing user's fields, required fields and length limits (a name maximum length in particular).
  Owner: product owner. Needed before: R-3/R-4 field lists are frozen.
- **G-4** (R-5) Whether deactivated or soft-deleted users count as existing and whether the store already has a unique index on
  normalised email. Owner: engineering. Needed before: A-5 is confirmed and AC-8.1 is built.
- **G-5** (R-9) Existing audit store, its retention and the compliance regime. Owner: operator. Needed before: R-9
  retention is stated.
- **G-6** (R-11, NFR-2, NFR-12) The existing admin application shell, authentication/session scheme (cookie or token),
  visual identity and UI toolkit. Owner: engineering. Needed before: the Import page is planned.
- **G-7** (R-12) How newly created users first obtain access (invitation email, admin-supplied link, SSO). Owner: product
  owner. Blocks: any claim that imported users can sign in; no other work.

## Assumptions (defaults taken because the run is unattended)

A-1 role checked from the authoritative record per request. A-2 CSV columns are `email`, `name`, optional `role`; unknown
columns are errors. A-3 `email` and `name` are the only mandatory user fields. A-4 email check is syntactic only. A-5
deactivated users still reserve their email. A-6 import is create-only. A-7 atomic all-or-nothing (alternative of
partial import is a legitimate product choice; changing it modifies R-6, AC-6.2, AC-7.1 and AC-11.1). A-8 no import history.
A-9 first committer wins on a race. A-10 audit and privacy rules are wanted for a bulk privileged action. A-11 both an
Import page and an Import API are wanted. A-12 no email, password or session created by import. A-13 browser set. A-14
any admin may create admins.

## Retired

None. No earlier requirement existed.

## Replay record (duty 10)

- **FX-B walk** (start: users = {`admin1`, `admin2`, `member1`, `exists@example.com`}; `admin1` is an admin per R-1, so the
  request is authorised): line 2 `ok1@example.com` valid and first occurrence and not existing -> valid; line 3 `not-an-email`
  has no `@` -> `invalid_email`; line 4 `ok1@example.com` valid format, name present, role member, earlier line 2 has the same
  email -> `duplicate_in_file`; line 5 name empty -> `missing_name`; line 6 role `superuser` not in {member, admin} ->
  `invalid_role`; line 7 `exists@example.com` valid, unique in file, present in store -> `already_exists`. Totals: 6 data
  rows, 5 row errors, 0 created, store unchanged. Matches AC-6.2, AC-7.1, AC-9.1 counts. Method: hand walk against the rules
  in R-4 and R-5.
- **FX-A then FX-A again** (R-6, R-8): first import: 3 valid, none existing -> created; second: each row valid, unique in
  file, existing -> `already_exists` on lines 2, 3, 4. Matches AC-8.2. Method: hand walk.
- **Race walk** (AC-8.1): both requests authorised (`admin1`, `admin2` are admins); both validate while `race@example.com`
  is absent; commit serialises on the unique key; the second committer finds the email present -> `already_exists` on its
  row for `race@example.com`, which is line 2 in both files (line 1 is the header); atomicity then discards C2's
  `extra@example.com` when C2 loses, and keeps it when C2 wins. C2-first order: C2 commits (`race@example.com` = Racer Two,
  `extra@example.com` created); C1 then finds `race@example.com` present -> `already_exists` on line 2, nothing created. Method:
  hand walk. The reachable-start condition
  (pause seam between validation and commit) is an implementation prerequisite (AD-3) that does not yet exist.
- A scratch script that mechanically applies the R-4/R-5 rules to FX-A and FX-B was written
  (`scratchpad/walk.py`) but its execution was not approved in this environment, so it is **NOT-REPLAYED: script run not
  permitted**; the walks above are by hand only. This leaves expected-result confirmation open until the first test run, and
  no execution is claimed.
- RFC 5321 limits (local part 64 octets; path 256 octets including brackets) were checked in the RFC text on 2026-11-21.
  No other platform, library or runtime capability claim is made by this spec: AD-1 to AD-4 contain none that a decision
  depends on beyond G-1.

## Submission

- **summary:** Specified bulk user creation from an admin-uploaded CSV as 12 requirements (R-1 to R-12), 14 NFRs, state/data
  and service-boundary assessments, and 7 open gaps; architecture decisions AD-1 to AD-4 are in `architecture.md`. Status: spec
  complete enough to plan, with items open. **Open (unresolved prerequisites/decisions):** G-1 numeric limits and platform
  request limit (blocks only the default limits and NFR-7 verification); G-2 admin role semantics; G-3 existing user fields;
  G-4 deactivated users and unique index; G-5 audit retention/compliance; G-6 existing admin shell, auth scheme and visual
  identity (blocks planning of the Import page); G-7 onboarding (blocks only claims that imported users can sign in). No
  requirement conflict found. **Assumptions recorded:** A-1 to A-14, notably all-or-nothing atomic import (A-7), create-only
  (A-6), strict columns `email,name,role` (A-2), page plus API (A-11), no email/password handling (A-12), any admin may grant
  admin (A-14). Nothing was executed against a product (none exists); the hand-walked examples are NOT-REPLAYED by a machine
  and the checks are all pending. Duty 11 (`backchain-check`) is left out as instructed.
- **primary:** R-1, R-2, R-6, R-11
- **evidence_refs:** `spec.md` (this file) with sections R-1 to R-12, Non-functional requirements, State and data assessment,
  Service boundaries, Interaction and lifecycle, Open gaps, Replay record; `architecture.md` AD-1 to AD-4; the request
  sentence (2026-11-21); guides `GUIDES/behavioral-requirements.md` (Behavior model, Traceability and review, Actors channels
  and state ownership), `GUIDES/requirements-definition.md`, `GUIDES/service-discovery.md` (Verification), `GUIDES/platforms/ui.md`
  (Light expressive starting point), `GUIDES/current-system-baseline.md` (Planning and review handoff: no baseline exists);
  RFC 5321 s4.5.3.1.1 and s4.5.3.1.3 (https://www.rfc-editor.org/rfc/rfc5321.txt, read 2026-11-21).
