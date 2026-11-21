# Admin User Management: product specification

Living contract for administrator-facing user management. This run adds one capability, bulk user import from a CSV
file (R-1 to R-8). Structure and technology choices live in `architecture.md` as AD-<n>; nothing here is one.

## Basis, baseline and readiness

- **Incoming request (2026-11-21):** "Let admins upload a CSV to bulk-create users." Quoted as source `REQ`.
  Its three outcomes: **O-1** only admins can do this; **O-2** an admin can upload a CSV; **O-3** the upload creates
  many users.
- **Baseline:** none. There is no repository, no earlier spec, no discovery or research result and no selected
  baseline to reopen, so every R-<n> below is **added** and nothing is preserved or retired (`## Retired` is empty).
  Nothing is known about the host product's user model, authentication, role model, storage, runtime or UI stack.
  Those are open prerequisites (G-2, G-3, G-6), not assumptions of absence.
- **Status vocabulary:** *accepted* = stated in `REQ`. *Default* = a chosen value recorded as an assumption A-<n>.
  *Open* = a gap G-<n> the user or discovery must close. Every acceptance line is **pending implementation and
  checks**; nothing here claims a test has run.
- **Readiness:** the import can be planned and built now with the limits and the host seams as configuration (see
  G-1, G-2, G-3). Release is unready until G-1 (limit values) and G-2 (admin identity) are closed. G-4, G-5, G-6
  keep only their own work unready.

### Request outcome to acceptance traceability

| Outcome | Acceptance lines |
| --- | --- |
| O-1 only admins | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-7.2 |
| O-2 upload a CSV | AC-2.1 to AC-2.5, AC-6.1 to AC-6.4, AC-8.1 to AC-8.6 |
| O-3 bulk-create users | AC-3.1 to AC-3.4, AC-4.1 to AC-4.5, AC-5.1 to AC-5.3, AC-8.3 |

## Requirements

Acceptance-line form: `AC-<R>.<n>` with kind (positive / failure / boundary), the consumer surface where it is
observed, and how it is confirmed. A kind that would add nothing is `n/a: <reason>`. Each AC id doubles as the
planned test-case locator.

Shared fixtures (all emails `@example.com`; "store" is the host user store read through an independent query):

- **Actors:** `admin` (an admin identity), `member` (authenticated, not admin), `anon` (no session).
- **Initial store S0:** one user `existing@example.com`, name `Existing User`.
- **F-OK:** `email,name` / `ada@example.com,Ada Lovelace` / `grace@example.com,Grace Hopper`, LF line ends, trailing LF.
- **F-MIX:** `email,name` / `ada@example.com,Ada Lovelace` / `not-an-email,Bad Mail` /
  `existing@example.com,Eve Existing` / `ADA@example.com,Ada Again` / `grace@example.com,` / `,Nobody`.
- **Test limits** (values for tests only, not product defaults): `MAX_DATA_ROWS=3`, `MAX_FILE_BYTES=200`.

### R-1 Only admins can use bulk import

- **Basis:** `REQ` "Let admins" (2026-11-21). Added. **Source locators:** requirements-definition.md; service-discovery.md
  "Cache and authorization". **Evidence limits:** how the host decides "admin" is unknown (G-2).
- **Behaviour:** the import page and the import request are available only to an authenticated identity the host
  authorizes as admin. The decision is taken from the host's current authorization source on every request, with no
  decision cached across requests, so a revocation takes effect on that identity's next request. A request already
  past authorization when a revocation lands completes (it is bounded and synchronous, AD-1).
- **Boundaries:** page load and submit are separate requests and are both checked. Hiding the navigation entry is a
  courtesy, never the control.
- **Error behaviour:** `anon` gets 401 (page navigation goes to the host sign-in). `member` gets 403. In both cases
  nothing is parsed, nothing is created and the body carries no uploaded content.
- **Consumer outcome:** an admin sees and uses the page; others cannot use it by any route.
- **Rules left out (bounds R-1):** creating, editing or deleting an admin role, per-admin quotas, delegated or
  partial-admin roles. The CSV cannot grant any role (see R-3 `unknown_column`).
- **Open gaps:** G-2 (admin identity; release wiring only).
- AC-1.1 positive: `admin` opens the import page, 200, file chooser present. Surface: browser; confirmed by response + rendered control.
- AC-1.2 failure: `anon` submits F-OK, 401, store still S0. Page navigation redirects to sign-in. Surface: HTTP; confirmed by status + store read-back.
- AC-1.3 failure: `member` submits F-OK, 403, store still S0, body has none of F-OK's values; `member` opening the page gets 403. Surface: HTTP + browser; confirmed by status, store read-back, body scan.
- AC-1.4 boundary: `admin` loads the page, the admin grant is then removed, the submit of F-OK gets 403 and the store is S0. Surface: HTTP; confirmed by status + store read-back. Prerequisite G-2 for the revocation mechanism.

### R-2 Upload a CSV file and validate it as a file

- **Basis:** `REQ` "upload a CSV" (2026-11-21). Added. **Source locators:** RFC 4180 §2 for CSV structure (primary source, not
  re-fetched in this run). **Evidence limits:** the column set is a default (A-3, G-3).
- **Behaviour:** the request carries exactly one file in a part named `file`. Accepted format (default A-3, A-4): UTF-8 with
  an optional leading BOM that is stripped; comma delimiter; RFC 4180 double-quote quoting; LF or CRLF; first record is a header.
  Header cells are trimmed and matched case-insensitively against `email` and `name`; both are required, order is free, nothing
  else is allowed. Records are numbered from the header as row 1, so the first data record is row 2 (matches a spreadsheet).
  One final line terminator does not start a record. The file name and declared content type are never trusted.
- **Boundaries:** 0 bytes; header only; last record without a terminator; BOM; reordered, upper-case or padded headers.
- **Error behaviour (file-level, nothing created):** `file_missing`, `multiple_files`, `file_empty`, `invalid_encoding`
  (any byte sequence that is not valid UTF-8, which includes UTF-16 files), `malformed_csv` (for example an unterminated
  quote), header errors `missing_column`, `unknown_column`, `duplicate_column` (all of them listed, with row 1 and the
  column name, in that order, `missing_column` in required order and the others in header order), `no_rows` (header and zero
  data records). Size and row-count errors are R-6. When header errors exist no data row is evaluated.
- **Consumer outcome:** the admin gets one response listing every file-level problem found at this stage, in R-5's shape.
- **Rules left out (bounds R-2):** other delimiters, other encodings, Excel `.xlsx`, multi-file or zipped upload, a downloadable template.
- **Open gaps:** G-3 (final column set; defaults A-3, A-4 apply meanwhile).
- AC-2.1 positive: ` Name ,EMAIL` header with record `  Ann  ,  Ann@Example.com ` is accepted by intake; a BOM-prefixed F-OK is accepted. Surface: HTTP; confirmed by 201 and store read-back (creation is R-4).
- AC-2.2 failure: header `email,email,role` with one data record returns 400 with exactly `(row 1, name, missing_column)`, `(row 1, role, unknown_column)`, `(row 1, email, duplicate_column)`; store S0. Surface: HTTP; confirmed by body + store read-back.
- AC-2.3 failure: bytes `FF FE` then `email,name` return 400 `invalid_encoding`; `email,name` / `a@example.com,"Ada` returns 400 `malformed_csv`; a request with no `file` part returns 400 `file_missing`; two `file` parts return 400 `multiple_files`. Each leaves S0. Surface: HTTP; confirmed by body + store read-back.
- AC-2.4 boundary: empty body part returns 400 `file_empty`; `email,name` + LF returns 400 `no_rows`; `email,name` / `z@example.com,Zed` with no final LF returns 201 with created_count 1. Surface: HTTP; confirmed by status + store read-back.
- AC-2.5 boundary: valid F-OK content sent as `ada.txt` with content type `application/octet-stream` is accepted (201); the same bytes as AC-2.3's invalid-encoding sample named `users.csv` with `text/csv` are rejected. Surface: HTTP; confirmed by status.

### R-3 Validate every row and report every problem

- **Basis:** `REQ` "bulk-create users" implies each created user must be valid (2026-11-21); the rule set is default A-4. Added.
  **Evidence limits:** the host's own user-model constraints are unknown (G-3); any value the host would reject is also a row error `invalid_value` on that field.
- **Behaviour:** before anything is created, every data record is validated and all failing (row, field) pairs are reported, not just the first. Values are trimmed. Per record: field count must equal the header's, else `(row, *, column_count)` (this includes an empty line, which is one empty field). `email`: required (`email_required`); shape `^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$` (`invalid_email`); unique within the file compared case-insensitively (`duplicate_in_file`, also giving `first_row`); not already in the store, compared case-insensitively (`email_exists`). Checks run in that order and the first failure is the only one reported for the field. `name`: required (`name_required`); no control characters U+0000 to U+001F or U+007F (`name_invalid`).
- **Boundaries:** duplicate detection includes earlier rows that are themselves invalid; a record spanning several physical lines is one row.
- **Error behaviour:** any row error means nothing at all is created (R-4); the response is 422 and lists errors ordered by row then column.
- **Consumer outcome:** the admin can fix the file in one pass.
- **Rules left out (bounds R-3):** email deliverability or ownership verification, domain allow or deny lists, IDN or Unicode normalization, name format or length beyond the host model (G-3), formula-injection neutralization (values are stored verbatim after trim; any later CSV export owns that risk).
- **Open gaps:** G-3 (host field constraints; default A-4 applies meanwhile).
- AC-3.1 failure: F-MIX against S0 returns 422 with exactly `(3,email,invalid_email)`, `(4,email,email_exists)`, `(5,email,duplicate_in_file,first_row 2)`, `(6,name,name_required)`, `(7,email,email_required)`; row 2 is not listed; S0 unchanged. Surface: HTTP + browser; confirmed by body, store read-back, rendered error table.
- AC-3.2 positive: record `ada@example.com,"Lovelace, Ada"` is valid and stored with name `Lovelace, Ada`; `  Ann@Example.com ` is stored as `ann@example.com` (A-4). Surface: HTTP; confirmed by store read-back.
- AC-3.3 boundary: `email,name` / `ada@example.com,"Line1<LF>Line2"` / `bad,Bad` returns 422 with exactly `(2,name,name_invalid)` and `(3,email,invalid_email)`, although `bad,Bad` is physical line 4. Surface: HTTP; confirmed by body.
- AC-3.4 failure: `email,name` / `a@example.com` / `b@example.com,B,extra` returns 422 `(2,*,column_count)` and `(3,*,column_count)`; `email,name` / `z@example.com,Zed` / empty line returns 422 `(3,*,column_count)`. Surface: HTTP; confirmed by body + store read-back.

### R-4 Create all users, or none

- **Basis:** `REQ` "bulk-create users" (2026-11-21). Added. Atomicity is default A-1 (alternative: partial import).
  **Evidence limits:** host store transaction and uniqueness capability unknown (G-3).
- **Behaviour:** when R-2 and R-3 pass, exactly one user is created per data record, as one atomic unit: all appear or none do.
  Email is stored in the host canonical form (default lower case, A-4) and name trimmed. Import only creates. It never
  changes or replaces an existing user. Email uniqueness is enforced again at commit, independently of the earlier validation read.
  Of two concurrent imports containing the same email, exactly one commits. The other creates nothing and returns 409 `import_conflict`,
  or 422 `email_exists` if it validated after the first commit. A failure while committing creates nothing and returns 500 `import_failed`;
  re-uploading the same file is safe.
- **Boundaries:** one data record; maximum rows (R-6); the same file uploaded twice.
- **Consumer outcome:** the admin sees the created count and finds exactly those users in the user store.
- **Rules left out (bounds R-4):** updating or upserting existing users, roles or permissions for new users (default role comes from the host, G-3),
  welcome or invitation email, and how new users first sign in (G-4), deactivating or deleting imported users, undoing an import.
- **Open gaps:** G-3 (store atomicity and uniqueness; if unmet, R-4 needs a user decision), G-4 (credential provisioning; a user decision that blocks only sign-in for imported users).
- AC-4.1 positive: `admin` submits F-OK against S0 and gets 201, created_count 2. The store holds `ada@example.com`/`Ada Lovelace` and `grace@example.com`/`Grace Hopper`, and `existing@example.com`/`Existing User` is unchanged. Surface: HTTP + store; confirmed by status, body and read-back.
- AC-4.2 failure: F-MIX leaves `ada@example.com` absent (its row was valid). A fault injected at the second insert of a valid file returns 500 `import_failed` and leaves S0. Surface: store with fault seam; confirmed by read-back (not by the response alone).
- AC-4.3 failure: F-OK a second time against the store after AC-4.1 returns 422 with `(2,email,email_exists)` and `(3,email,email_exists)`; the store keeps 3 users and each name is unchanged. Surface: HTTP + store; confirmed by body + read-back.
- AC-4.4 boundary: `admin` A uploads `email,name` / `new@example.com,Neo A` while `admin` B uploads `email,name` / `new@example.com,Neo B`, concurrently, against S0. Exactly one response is 201 and the other is 409 or 422; the store holds exactly one `new@example.com`, named by the 201 caller's file. Surface: HTTP x2 + store; confirmed by read-back. A pause seam between validation and commit makes the 409 interleaving deterministic; without one the oracle above still holds for either interleaving.
- AC-4.5 boundary: a one-row file `email,name` / `solo@example.com,Solo` returns 201 with created_count 1. Surface: HTTP + store; confirmed by read-back.

### R-5 Result contract

- **Basis:** `REQ` implies the admin learns the outcome (2026-11-21); shape is default A-2. Added.
- **Behaviour:** the import request completes synchronously and its response is the only result carrier. Body is JSON:
  `{ outcome: "created"|"rejected"|"failed", created_count: <n>, errors: [{ row, field, code, first_row? }] }`;
  file-level errors have `row` and `field` null except header errors (R-2). `errors` is never truncated. Messages
  are rendered from stable `code` values by the client. Status map: 201 created; 400 file-level; 413 `file_too_large`; 422 row errors;
  409 `import_conflict`; 401, 403 (R-1); 500 `import_failed`. Responses never echo email or name values from the file.
- **Boundaries:** errors list length equals the number of failing (row, field) pairs, up to the R-6 row bound.
- **Rules left out (bounds R-5):** a stored import-history record the admin can reopen, downloadable error report, localized messages.
- **Open gaps:** none.
- AC-5.1 positive: F-OK as `admin` returns 201 and a body with `outcome:"created"`, `created_count:2`, `errors:[]`. Surface: HTTP; confirmed by body schema check.
- AC-5.2 failure: each status in the map is produced by its trigger (AC-1.2, 1.3, 2.2, 3.1, 4.2, 4.4, 6.2) and carries its `outcome`. Surface: HTTP; confirmed by status + `outcome` per case.
- AC-5.3 boundary: a body from AC-3.1 contains none of the strings `Bad Mail`, `Eve Existing`, `Nobody`, `not-an-email`. Surface: HTTP; confirmed by substring scan of the raw body.

### R-6 Upload size and row-count bounds

- **Basis:** `REQ` is silent on size. A bound is introduced because an unbounded upload cannot be handled safely (memory, parse time, atomic
  transaction size, request time). Introduced limits: `MAX_FILE_BYTES` (checked first, while reading) and `MAX_DATA_ROWS` (data records, header excluded).
  **Value basis: none.** No repository, runtime, platform limit or user figure is available, so **no default value is chosen**;
  the values stay open as G-1. Added.
- **Behaviour:** both limits are required configuration read at request time, exposed to the admin page for display, with no value baked into code
  and no value silently assumed. At or under a limit, the file is processed normally. Over `MAX_FILE_BYTES` the upload is rejected with 413 `file_too_large` after
  at most `MAX_FILE_BYTES + 1` bytes of the body have been read, before parsing. A file within the byte limit with more than `MAX_DATA_ROWS` data records is rejected 400 `too_many_rows` before any row validation. Nothing is created in either case.
- **Boundaries:** exactly at the limit is accepted; one over is rejected. The two limits are independent.
- **Consumer outcome:** the admin is told which limit was hit and what the limits are.
- **Open gaps:** G-1 (both limit values).
- **Interim, until G-1 closes:** plan, build and test with the limits injected; tests use the test limits above. Release is unready.
- AC-6.1 boundary: with `MAX_DATA_ROWS=3`, a file with 3 data rows (`u01..u03@example.com`, name `N`) returns 201 with created_count 3. Surface: HTTP; confirmed by store read-back.
- AC-6.2 failure: with `MAX_DATA_ROWS=3`, 4 such rows return 400 `too_many_rows` and the store is S0, and no row is evaluated (4 rows where row 3 is also an invalid email still give only `too_many_rows`). Surface: HTTP; confirmed by body + store read-back.
- AC-6.3 boundary: with `MAX_FILE_BYTES=200` and `MAX_DATA_ROWS=1000`, a file of exactly 200 bytes (header `email,name` LF = 11 bytes; rows `u01..u09@example.com,N1` LF = 19 bytes each; row `u10@example.com,N` LF = 18 bytes) returns 201 created_count 10. Changing row 10's name to `N1` makes 201 bytes and returns 413 `file_too_large`, store S0. Surface: HTTP; confirmed by status + store read-back + a size assertion on the fixture before sending.
- AC-6.4 failure: with `MAX_FILE_BYTES=200`, a 10,000-byte valid body is rejected 413 and an instrumented read counter shows at most 201 body bytes consumed. Surface: HTTP + server counter; confirmed by counter, not only status. If a limit is not configured the request is refused with 500 `import_failed` and an audit `failed` record rather than falling back to any value.

### R-7 Audit and handling of uploaded personal data

- **Basis:** bulk account creation is security-consequential (service-discovery.md "Select scope"); this is a design requirement, not in `REQ`. Added.
- **Behaviour:** every import attempt, including denied ones, writes one audit record: event `user_import`, actor id, UTC timestamp, outcome (`created`, `rejected`, `denied`, `failed`),
  data-row count when parsed, created_count, and the distinct set of error codes. It holds no email, no name, no file name and no file content. Uploaded bytes live only in request memory (or a transient spool removed before the response is sent). Neither logs nor audit nor any other store retains them. The only durable personal data is the created users, by design.
- **Error behaviour:** if the audit write fails after a successful commit, the import still stands and the response is 201, and the audit failure is reported through the host's operational error channel. If the audit write fails first, the import proceeds. The audit is not a gate (A-8).
- **Rules left out (bounds R-7):** audit retention period and who may read the audit (host policy, G-5); tamper-evidence.
- **Open gaps:** G-5 (retention and readers; host policy meanwhile).
- AC-7.1 positive: after AC-4.1 exactly one `user_import` record with outcome `created`, created_count 2, actor `admin`'s id exists. Surface: audit sink read-back; confirmed by query.
- AC-7.2 failure: after AC-1.3 a `denied` record exists with `member`'s id; after AC-3.1 a `rejected` record lists the five codes of AC-3.1 (no values). Surface: audit read-back.
- AC-7.3 boundary: after AC-4.1, AC-3.1 and AC-1.3, a scan of captured application logs, the audit records, and the process temp directory finds none of `ada@example.com`, `Ada Lovelace`, `Eve Existing`. The scanner is first proven with a planted sentinel that it must find, so an empty scan cannot pass vacuously. Surface: logs, audit, temp directory; confirmed by scan.

### R-8 Admin import page

- **Basis:** the consumer surface for `REQ` "upload a CSV" is a web page for admins (default A-2; alternative API-only). Added.
  **Evidence limits:** whether the host has an established admin UI identity is unknown (G-6).
- **Behaviour:** a page "Import users" containing: a native file input named "CSV file" (a drag-and-drop zone may sit over it, never replace it); help text naming the columns `email` and `name`, UTF-8 and the two limits; an "Import users" button, disabled until a file is chosen. A chosen file larger than `MAX_FILE_BYTES` is flagged before upload as a hint only, with the server remaining the authority. On submit the page shows a pending state (button disabled, label "Importing", indeterminate indicator, no fabricated percentage), and a second submit cannot start a second request.
  The result is shown only from the server response: `created` shows "N users created" and offers "Import another file"; `rejected` shows "Nothing was imported", the error count and a table with columns Row, Field, Problem sorted by row (a file-level error is a single message), with the file chooser still usable; 401 says the session expired with a sign-in link; 403 says the admin permission is missing; 500 `import_failed` says nothing was created. If the connection is lost before a response arrives the page says the outcome could not be confirmed, that nothing or all rows may have been created, and that re-uploading is safe because already-created rows will be reported as `email_exists`. Result changes move focus to the result heading and are announced (status for success, alert for failure).
- **Boundaries:** no file chosen (empty state); one file replaced by another before submit; 1 error and the maximum number of errors (the table scrolls inside its own region, with the total shown).
- **Consumer outcome:** an admin can complete or correct an import using keyboard alone and always knows whether users were created.
- **Open gaps:** G-6 (host UI identity; the NFR-6 starting point applies meanwhile).
- AC-8.1 positive: `admin` chooses F-OK and submits; page shows pending, then "2 users created". Surface: browser, with the server response held until the pending state is asserted. Confirmed by rendered text, disabled button during the hold, and store read-back.
- AC-8.2 failure: F-MIX renders "Nothing was imported", 5 errors, and a table whose rows are exactly the five of AC-3.1 in order. Surface: browser; confirmed by table text + store read-back.
- AC-8.3 failure: response never arrives (connection dropped after the request is sent): page shows the unconfirmed-outcome message and not "created" or "nothing was imported". Surface: browser with a network fault; confirmed by rendered text.
- AC-8.4 boundary: no file chosen shows the empty state with a disabled button; a double-click on Import issues exactly one request. Surface: browser with a request counter; confirmed by counter.
- AC-8.5 failure: 401 and 403 responses show their distinct messages; 500 shows the nothing-created message. Surface: browser with stubbed responses; confirmed by text.
- AC-8.6 boundary: the page's keyboard and assistive-technology behaviour is as in NFR-6 (focus to result heading, status/alert announcement). Surface: browser; confirmed by NFR-6's checks.

## Behavior model

Stateless request-in, result-out, apart from the atomic write to the host user store (so no lifecycle state machine for the import itself; the
only stateful entities are listed below).

### Flows

- **F-1 Import (R-1 to R-7):** admin page, then `POST` import request, then (1) authorize, T-6; (2) read body with `MAX_FILE_BYTES` cap, T-2; (3) decode and parse, header check, T-2;
  (4) count rows against `MAX_DATA_ROWS`, T-2; (5) validate all rows against file and store, T-3; (6) atomic create, T-1, T-4, T-5; (7) audit, R-7; (8) respond (R-5).
- **F-2 Page interaction (R-8):** choose file, submit, pending, render result per R-5 status, recover (fix file, re-submit).

### State inventory

| Entity | Meaning and invariant | Owner | Durability |
| --- | --- | --- | --- |
| User (by canonical email) | One per case-insensitive email, never modified by import | host user store | durable |
| Upload bytes | Exist only while the request runs | request handler | transient |
| Audit record | One per attempt, no personal values | host audit sink | durable (retention G-5) |
| Page state (selected file, pending, result) | Presentation only, lost on reload | browser tab | transient |

### Transition ledger

| ID | Trigger and guard | Operation and after | Failure and recovery | Cases |
| --- | --- | --- | --- | --- |
| T-1 | admin, valid file, all rows valid | create all users atomically, then 201 | see T-4, T-5 | AC-4.1, 4.5, 6.1, 6.3 |
| T-2 | admin, file-level fault (R-2, R-6) | no write; 400 or 413 | resend a corrected file | AC-2.2 to 2.5, 6.2 to 6.4 |
| T-3 | admin, one or more row errors | no write; 422 with every error | fix and resend | AC-3.1 to 3.4, 4.3 |
| T-4 | commit-time uniqueness conflict | rollback; 409 `import_conflict` | resend, then the per-row `email_exists` appears | AC-4.4 |
| T-5 | store fault during commit, or limits unset | rollback; 500 `import_failed` | resend is safe | AC-4.2, 6.4 |
| T-6 | not admin or not signed in | no parse, no write; 403 or 401 | sign in as admin | AC-1.2 to 1.4 |

Invalid/repeated event classes: a repeated upload of an already imported file is T-3 (all `email_exists`) with no change. Duplicate concurrent submissions are T-4.
Timeout and cancellation: a client that disconnects mid-upload leaves no partial effect, because the write happens only after the full body is read and validated; the atomic commit makes the outcome all or nothing even if the client never sees the response (AC-8.3 covers the page's honesty about it).

## Non-functional requirements

Basis: derived from `REQ` and the requirements-definition.md assessment; none is stated in `REQ`. No numeric bound is invented.

- **NFR-1 Security (R-1):** authorization is enforced server-side on every request. When the host authenticates by cookie session, the import request also requires the host's anti-forgery protection. Verification: AC-1.2 to 1.4; a cross-site submit without the anti-forgery token is rejected and creates nothing (planned, `NOT-REPLAYED` until the host auth mechanism is known, G-2).
- **NFR-2 Privacy (R-7):** uploaded values are not persisted, logged or echoed beyond the created users. Verification: AC-5.3, AC-7.3.
- **NFR-3 Resource bound (R-6):** memory held for an upload is bounded by `MAX_FILE_BYTES` regardless of what is sent. Verification: AC-6.4. The numeric value is open (G-1).
- **NFR-4 Reliability and integrity (R-4):** all-or-nothing under errors, store faults and concurrent imports. Verification: AC-4.2, AC-4.4.
- **NFR-5 Performance, capacity:** unresolved. The requirement is that an import of `MAX_DATA_ROWS` rows completes within the host runtime's request time limit; neither value is known (G-1). No latency target is invented.
- **NFR-6 UI quality and accessibility (R-8):** a deliberately designed interface, not unstyled scaffolding. Observable criteria: (a) one visual system with spacing and type scales and a palette with a light theme and a dark theme; (b) designed empty (AC-8.4), pending (AC-8.1), success, rejected and unconfirmed-outcome (AC-8.3) states; (c) usable with no horizontal overflow at 360 px and at 1280 px width; (d) visible keyboard focus on every control, and WCAG 2.x AA contrast (4.5:1 text, 3:1 control boundaries and focus indicators) in both themes; (e) motion only where it explains a change (pending to result), none under `prefers-reduced-motion`; (f) one icon set; (g) the whole task completes by keyboard alone, focus moves to the result heading, and results are announced. Verification: browser check at both widths in both themes, automated accessibility scan plus a manual keyboard walk (a DOM scan alone does not establish accessibility), measured contrast. **Visual reference (UI visual-direction guide, light expressive starting point):** a light Gemini-style look with Material 3 Expressive principles: luminous light canvas, tonal rounded surfaces, restrained saturated accent, humanist sans-serif from local fonts, short purposeful motion; the drop zone and the result panel are the visual focal point; dark theme available. Starting appearance is light with a dark option. Precedence: an established host UI identity, explicit visual constraints and platform conventions override this (G-6); concrete tokens are chosen by the plan in an AD.
- **NFR-7 Observability (R-7):** one audit record per attempt, as R-7. Failures of the audit write go to the host's operational error channel.
- **NFR-8 Compatibility:** supported browsers and server runtime are unresolved; inherit the host's supported list. Nothing is invented (G-2, G-6).
- **NFR-9 Testability:** limits, the admin decision, the store and the clock are injectable so AC-1.4, AC-4.2, AC-4.4 and AC-6.x run without production configuration.
- **Excluded, with reason:** availability SLA and load testing (not requested, single admin action, no stated volume); localization (not requested, codes are stable so it can be added); data-subject deletion of imported users (belongs to the host's user lifecycle).

## State and data assessment

- **Resources and target identity:** the host user store, identified by canonical (lower-case) email, uniquely; the audit sink; no files, caches or configuration are written. Access assignments are only read (R-1). Observed, not changed: existing users.
- **Before and after, success (T-1):** store S becomes S plus N new users (N = data rows); no existing user is altered; one `created` audit record. **After any failure (T-2 to T-6):** S unchanged, one audit record with the failing outcome, except that a failed audit write leaves no record (A-8).
- **Authorized actor and effect:** only admin; effect is create-only.
- **Partial failure and recovery:** commit is atomic, so no partial state exists to repair; recovery is re-upload. An unknown outcome (connection lost) is resolved by re-upload: `email_exists` rows prove an earlier commit.
- **Checks:** store read-back after every AC that claims "no change"; fault injection for AC-4.2; concurrent pair for AC-4.4.
- **Unknowns:** whether the host store supports multi-row atomic commit and a case-insensitive uniqueness guarantee (G-3). If it cannot, R-4 cannot be met as written and the user must decide between A-1's alternative (partial import) or a store change.

## Service boundaries

- **Admin authority (host identity and authorization):** current authority is the host's authorization source, queried per request. Freshness versus revocation: no cache, revocation takes effect on the next request (R-1, AC-1.4). Unknown mechanism: G-2.
- **User store:** authoritative for users and email uniqueness; read for validation, written atomically at commit; no cache or replica is introduced. Incremental state, async completion: not applicable, the import completes in the request (A-5, AD-1).
- **Audit sink:** owned event coverage is the `user_import` event (R-7); the host's sign-in events are the host's.
- **Outside this feature:** no third-party or remote service is called; no outbound email.

## State and information lifecycle

| State | Owner and location | Who may read | Simultaneous changes | Ends when | Quotas |
| --- | --- | --- | --- | --- | --- |
| Selected file, pending, result | browser tab memory | that admin only | n/a, single tab | reload or "Import another file" | none stored, no browser storage used |
| Upload bytes | server request memory | no one | n/a, per request | the response is sent | `MAX_FILE_BYTES`, host request limits (G-1) |
| Created users | host user store | per the host's user-admin permissions | uniqueness at commit (R-4) | host's own deletion flow | host store limits |
| Audit record | host audit sink | host's audit readers (G-5) | append-only | host retention (G-5) | host sink limits |

Personal data (emails, names): shown only in the page's file chooser by the browser itself; never echoed by the server (R-5); stored only as created users; never logged or audited (R-7); removed with the users by the host's own flow.
No identity, sharing or persistence beyond this is added. Offline use is not supported.

## Open gaps

- **G-1 (R-6, NFR-3, NFR-5):** values of `MAX_FILE_BYTES` and `MAX_DATA_ROWS`. Missing basis: runtime request size and time limits, store transaction
  limits, and the admin's expected file sizes. Needed from discovery of the host runtime or from the user. Interim: configurable, injected in tests;
  affects release readiness only. Behaviour at and beyond the bound is fully specified (AC-6.1 to 6.4). If the chosen row bound cannot finish within the runtime's request time limit, the AD-1 synchronous design is revisited.
- **G-2 (R-1, NFR-1, NFR-8):** how the host authenticates and decides "admin". Interim: one injectable admin decision, tested with `admin`, `member`, `anon` stubs. Blocks release wiring only.
- **G-3 (R-2, R-3, R-4):** the host user model: final column set (this spec defaults to `email`, `name`), its field constraints, default role of new users, canonical email form, and store atomicity and uniqueness. Interim: defaults A-3, A-4; the host's rejections surface as `invalid_value`. A decision needed from the user if columns beyond `email` and `name` are wanted.
- **G-4 (R-4):** how imported users first obtain credentials (invitation, reset link, none) and whether they are notified. This is a product decision for the user. Interim: the CSV carries no secret and the response and logs show none; sign-in provisioning is out of this change.
- **G-5 (R-7):** audit retention period and readers. Interim: host policy.
- **G-6 (R-8, NFR-6, NFR-8):** whether the host already has an admin UI identity, toolkit and supported browsers. Interim: NFR-6 starting point applies as a new UI.

## Assumptions (defaults chosen in this spec)

- **A-1 All-or-nothing import.** Basis: a single corrective upload cycle, no partial state to reconcile, a safe retry. Alternative: create the valid rows and report the rest, which needs per-row outcomes and an idempotency rule. Revalidate if admins need to import files where some rows are expected to fail.
- **A-2 Web delivery:** an admin page plus the HTTP import request it makes, with the status map of R-5. Alternative: API or CLI only. Revalidate when G-6 shows the host surface.
- **A-3 Columns:** `email` and `name`, both required, nothing else accepted. Basis: the minimum to identify and label a user; refusing unknown columns stops a `role` or `password` column from being silently ignored. Revalidate at G-3.
- **A-4 Row rules:** the email shape, case-insensitive uniqueness, canonical lower-case storage, and the name control-character rule. Basis: conservative and common practice, no RFC-complete validation claimed. Revalidate at G-3.
- **A-5 Synchronous completion**, no job record. Basis: R-6's bound keeps the work to one request. Revalidate at G-1.
- **A-6 Create-only:** an existing email is an error, not an update. Basis: `REQ` says "create"; upsert could overwrite a person's record from a spreadsheet.
- **A-7 No role column:** created users take the host default role. Basis: a CSV must not be a privilege-escalation path.
- **A-8 Audit is not a gate:** a failed audit write does not undo or block an import. Alternative: fail closed. Revalidate with the host's audit policy (G-5).

## Replay evidence

- **Method:** hand-walk of every worked example in R-1 to R-6 against the rules in this document from the stated start state S0 and actor. Each action
  was checked against the rule that permits it: AC-4.3 needs AC-4.1 first (the second upload is permitted by R-1 for `admin` and
  is decided by R-3's `email_exists` check); AC-6.3's byte counts were summed (11 + 9 x 19 + 18 = 200; 201 with `N1`). AC-3.3 row numbers were recounted by records (header 1, then 2, 3), not physical lines (line 4).
- **Recomputed:** F-OK twice gives 201 then 422 with two `email_exists`, store ending at 3 users. F-MIX gives the five errors of AC-3.1; row 2 is valid and absent from the store. Header `email,email,role` gives missing `name`, unknown `role`, duplicate `email`.
- **NOT-REPLAYED (execution):** an executable reference model of these rules was written in the run scratch area, but its execution was not approved in this run, so none of the examples has been executed. They remain open for test authors to replay against the built product. AC-1.4 and NFR-1's anti-forgery case are also `NOT-REPLAYED`: the host's role-revocation and session mechanisms are unknown (G-2).
- No documented command exists yet, so no exit code is recorded. The RFC 4180 reading and WCAG AA ratios are cited from primary sources by name but were not re-fetched here.

## Retired

None.

## Submission

- **summary:** Spec for "Let admins upload a CSV to bulk-create users." 8 requirements (R-1 to R-8), all added, no baseline existed. Rules the request left out are listed under the R they bound. Open: G-1 values of the file-size and row-count limits (introduced because an unbounded upload is unsafe, **no default chosen** since no runtime or platform evidence exists; behaviour at and beyond the bound is specified, release is unready until set); G-2 admin identity; G-3 host user model; G-4 credential provisioning (user decision); G-5 audit retention; G-6 host UI identity. Assumptions (value, basis, alternatives, revalidation in the Assumptions section): A-1 atomic all-or-nothing, A-2 web delivery, A-3 columns `email`/`name`, A-4 row rules, A-5 synchronous completion, A-6 create-only, A-7 no role column, A-8 audit not a gate. Worked examples were hand-walked only and are `NOT-REPLAYED (execution)`. No material requirement conflict.
- **primary:** R-1, R-2, R-4, R-8.
- **evidence_refs:** KNOWLEDGE/spec.md (sections R-1 to R-8, Behavior model, Non-functional requirements, State and data assessment, Service boundaries, State and information lifecycle, Open gaps, Assumptions, Replay evidence); KNOWLEDGE/architecture.md; GUIDES/behavioral-requirements.md#behavior-model; GUIDES/behavioral-requirements.md#traceability-and-review; GUIDES/requirements-definition.md; GUIDES/service-discovery.md; GUIDES/platforms/ui.md#light-expressive-starting-point; the incoming request `REQ`. The `backchain-check` receipt is not applicable here.
