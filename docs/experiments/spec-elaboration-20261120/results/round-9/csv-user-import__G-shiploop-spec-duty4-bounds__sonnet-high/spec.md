# User administration — product specification

Status: draft produced by the spec stage, run on its own. Nothing is implemented or tested. Every check below is
**planned**, not run.

## Source, baseline and evidence limits

- **Request (2026-11-21, verbatim):** "Let admins upload a CSV to bulk-create users."
- **Prior spec:** none (no `KNOWLEDGE/spec.md`, no earlier R-<n>). Nothing to preserve, nothing retired.
- **Baseline / discovery / research:** none exist. There is no repository, no current-system baseline, and no
  platform or runtime target. Everything about the existing product (user model, roles, auth, API conventions, UI
  identity, storage engine) is **unknown**, not absent. Each place this matters is an open gap (G-n) under its R-<n>.
- **Guides applied:** behavioral-requirements.md#behavior-model, #traceability-and-review,
  #actors-channels-and-state-ownership; requirements-definition.md (NFR assessment and
  #state-and-data-change-assessment); service-discovery.md#verification; platforms/ui.md#light-expressive-starting-point.
- **External evidence used:** RFC 5321 §4.5.3.1 (fetched 2026-11-21 from rfc-editor.org, lines 3484-3496): local-part
  max 64 octets, domain max 255 octets, path max 256 octets including the two angle brackets. *Inference (not stated
  in the RFC text):* an address without brackets is therefore at most 254 characters.

Terms: **row** = 1-based data record of the file (the header is not a row; fully empty lines are skipped and not
counted). **Effective bound** = the value actually enforced, i.e. the smaller of the configured bound and any runtime
limit (see R-7). **Uploader** = the authenticated admin making the request.

## Requirements

### R-1 Only admins can use bulk import

- **Basis:** request 2026-11-21, "Let admins upload…". The words "admins" bound who may; the request is silent on
  non-admins, so denial is the safe reading (A-5).
- **Behaviour:** the bulk-import operation is available only to an authenticated user who currently holds the admin
  role. Authority is evaluated on the server from current account state on every request; nothing the client sends
  (role claim, hidden field, cached page) grants it. An unauthenticated caller is rejected as unauthenticated; an
  authenticated non-admin is rejected as forbidden. A rejected caller learns nothing about the file or about existing
  users, and no user is created.
- **Rules the request leaves out (bounded here):** what "admin" means in this product (single role vs permission) —
  G-4; whether sub-admin or tenant-scoped admins exist — G-4; rate limiting — excluded (no basis for a number, see
  R-14).
- **Open gaps:** **G-4** how admin status is determined and how an admin session is established in a test
  environment; which CSRF mechanism the existing session scheme uses. Owner: user/maintainer or discovery of the
  existing auth. Dependent work (R-1 checks) stays unready until known; other R-<n> may proceed.
- **Freshness vs revocation:** the admin check runs at request start (A-5). An admin demoted *before* a request
  begins gets 403. A request already past the check when demotion happens may complete (alternative: re-check
  immediately before commit; revalidate if the product needs revocation to cut off in-flight work).
- **Acceptance**
  - **R-1/A1** — surface: HTTP API (default route `POST /api/admin/users/bulk`, multipart field `file`; A-8). Confirm:
    automated API test.
    - Positive: an authenticated admin submitting S-1 gets 201 and the users exist (see R-5).
    - Failure: with no session → 401 and zero users created; with a session of a non-admin (`member@example.com`)
      → 403, zero users created, body contains no row/user details.
    - Boundary: an account demoted from admin to non-admin, then submitting S-1 with its previously valid session
      → 403 and zero users created (authority is current, not cached).
  - **R-1/A2** — surface: browser (admin UI, R-11). Confirm: browser test.
    - Positive: admin sees the entry point to the import page.
    - Failure: a non-admin navigating directly to the page URL sees an access-denied state, and a submit attempt
      (forged) is rejected per R-1/A1.
    - Boundary: n/a: covered by R-1/A1 (the server decides; UI hiding is convenience only).
  - **R-1/A3** — surface: HTTP API. Confirm: API test. State-changing cross-site request protection.
    - Positive: a same-origin upload with the product's normal credential/CSRF token succeeds.
    - Failure: an upload lacking the required CSRF token/header (if the session scheme is cookie-based, G-4) →
      rejected, zero users created.
    - Boundary: n/a: only applicable if G-4 resolves to cookie sessions; otherwise record `n/a: token auth`.

### R-2 The operation accepts a CSV file and parses it deterministically

- **Basis:** request 2026-11-21, "upload a CSV". Format details are the request's silence; defaults A-9.
- **Behaviour:** the file is parsed as RFC 4180-style CSV: comma delimiter, optional double-quote quoting with
  `""` escapes (quoted fields may contain commas and line breaks), LF or CRLF line endings, UTF-8 encoding with an
  optional leading BOM (stripped). The first record is the header. Fully empty lines are skipped. The file is judged
  by its content, not by its name or declared media type. A file that is not valid UTF-8, has an unterminated
  quote, is zero bytes, or has a header but no data rows is rejected as a whole with a file-level error
  (`NOT_UTF8`, `MALFORMED_CSV`, `EMPTY_FILE`, `NO_DATA_ROWS`) and nothing is created. Other delimiters
  (semicolon, tab) are not accepted; such a file is reported through the header rules in R-3 (S-8).
- **Rules the request leaves out (bounded here):** other encodings, other delimiters, Excel-native formats
  (.xlsx), compressed uploads, multiple files per request, a header-less mode — all out of scope (see Out of scope).
- **Acceptance**
  - **R-2/A1** — surface: HTTP API. Confirm: API tests using the named sample files.
    - Positive: S-1 (CRLF, quoted comma field `"Hopper, Grace"`) → 2 rows parsed, second name stored exactly
      `Hopper, Grace`. S-7 (S-1 prefixed with bytes EF BB BF) → same result, header column still recognised as `email`.
      S-15 (S-1 with a blank line between the rows and two trailing blank lines) → 2 rows, numbered 1 and 2.
    - Failure: S-4 (zero bytes) → 422 `EMPTY_FILE`; S-3 (`email,name,role` + newline only) → 422 `NO_DATA_ROWS`;
      S-10 (valid header, then byte FF inside a name) → 422 `NOT_UTF8`; S-11 (`ada@example.com,"Ada` with an
      unterminated quote) → 422 `MALFORMED_CSV` naming the record where parsing failed. In every case zero users
      are created.
    - Boundary: S-8 (semicolon-delimited) → the header is one column named `email;name`, so the result is the two
      header errors of R-3, not a crash and not a partial parse.
  - **R-2/A2** — surface: HTTP API. Confirm: API test.
    - Positive: a valid S-1 sent with filename `users.txt` and media type `application/octet-stream` is accepted
      (content decides).
    - Failure: an HTML or binary file named `users.csv` → 422 `MALFORMED_CSV` or `NOT_UTF8` or header errors,
      whichever the content triggers; never executed, never stored.
    - Boundary: n/a: covered by R-2/A1.

### R-3 Columns and per-row validation

- **Basis:** request 2026-11-21, "bulk-create users"; the column set is not stated, so this is default A-2/A-4
  pending G-3.
- **Behaviour:** the header must contain `email` (required). `name` and `role` are optional columns. Header names are
  trimmed and matched case-insensitively; each may appear once. Unknown columns, or a duplicated column, reject the
  whole file (typos such as `emial` must not silently drop data; a `password`, `token` or other secret-like column
  is simply an unknown column — the CSV never carries credentials, see R-9). Each row must have exactly as many fields
  as the header (`ROW_FIELD_COUNT`). Each row is validated by **the same rules as creating a single user through the
  existing path** — bulk import must never be looser than single creation. Until G-3 gives those rules, the default
  rules are: `email` trimmed, required (`EMAIL_REQUIRED`), exactly one `@`, local part 1–64 chars, whole address
  ≤ 254 chars (RFC 5321 evidence above), no whitespace or control characters, domain non-empty labels separated by
  dots with at least one dot (`EMAIL_INVALID`); `name` trimmed, may be blank; `role` blank → the same default role as
  single creation, otherwise must be a role the uploader is allowed to assign (`ROLE_NOT_ALLOWED`; a role value that
  does not exist is also `ROLE_NOT_ALLOWED`). A value longer than the user model's field limit → `FIELD_TOO_LONG`
  (limit from G-3).
- **Rules the request leaves out (bounded here):** which attributes a user has beyond email/name/role; the role set,
  default role and the "assignable roles" rule; the name/field length limits; update-on-match (this feature only
  creates, never edits an existing user) — **G-3**.
- **Open gaps:** **G-3** the existing user model (attributes, roles, default role, single-create validation rules and
  length limits). Interim: the defaults above; plan stays unready for the role/length clauses only.
- **Acceptance**
  - **R-3/A1** — surface: HTTP API. Confirm: API tests.
    - Positive: S-1 passes validation (role blank → default role). S-14 (` ada@example.com ` with surrounding
      spaces) creates the user with email `ada@example.com`.
    - Failure: S-5 (`name,role` header, no `email`) → 422, one error `MISSING_REQUIRED_COLUMN` (column `email`),
      no row errors; S-6 (`email,name,password` header, one data row with value `hunter2`) → 422
      `UNKNOWN_COLUMN` (column `password`), and the value `hunter2` appears nowhere in the response, logs or audit
      record; header `email,email` → 422 `DUPLICATE_COLUMN`; S-9 (`ada@example.com,Ada` under a three-column
      header) → row 1 `ROW_FIELD_COUNT`; a row with blank email `,Ada,` → `EMAIL_REQUIRED`; a row `grace@example.com,Grace,no-such-role`
      → `ROLE_NOT_ALLOWED` (column `role`).
    - Boundary: an address of exactly 254 characters (local part 64 × `a`, then `@`, then domain labels of 63, 63,
      57 characters and `com`, joined by dots: 64+1+63+1+63+1+57+1+3 = 254) is accepted; the same with one extra
      leading `a` (255 characters, local part 65) → `EMAIL_INVALID`; a 65-character local part with a short
      domain → `EMAIL_INVALID`. (Lengths derived by hand arithmetic; **NOT-REPLAYED**, no run was possible.)
  - **R-3/A2** — surface: HTTP API. Confirm: API test, after G-3.
    - Positive: a row whose role is assignable by the uploader creates a user with that role.
    - Failure: a role the uploader may not assign (for example an admin role if single creation does not let this
      uploader assign it) → `ROLE_NOT_ALLOWED`, nothing created (no privilege escalation through CSV).
    - Boundary: n/a: depends on G-3; blocked until the role model is known.

### R-4 Duplicate email handling (within the file and against existing users)

- **Basis:** request silent; needed because a user record without unique identity cannot be created correctly (A-2).
- **Behaviour:** email identity is compared after trimming and case-insensitively. If an email already belongs to an
  existing user, that row is an error `EMAIL_EXISTS`; existing users are never modified or overwritten. If the same
  email appears more than once in the file, the first occurrence is kept and every later occurrence is an error
  `EMAIL_DUPLICATE_IN_FILE` whose message names the first row. All such errors are reported together with other row
  errors (R-6).
- **Rules the request leaves out (bounded here):** update/upsert of existing users; skipping duplicates silently
  (rejected as default: silent skip hides data loss) — alternative: skip-and-report. Revalidate if the user wants
  "import what's new".
- **Acceptance**
  - **R-4/A1** — surface: HTTP API. Confirm: API test, seeded users `root@example.com` (admin),
    `member@example.com`, `existing@example.com`.
    - Positive: S-1 (neither address exists) creates both.
    - Failure: S-2 (see samples) → row 3 `EMAIL_EXISTS`, row 4 `EMAIL_DUPLICATE_IN_FILE` (references row 1); a row
      `Existing@Example.com` → `EMAIL_EXISTS` (case-insensitive). The existing user `existing@example.com`
      has unchanged name, role and state after the attempt.
    - Boundary: `ada@example.com` and `ADA@example.com` in one file → row 2 is `EMAIL_DUPLICATE_IN_FILE`.

### R-5 Valid files create all their users, atomically

- **Basis:** request 2026-11-21, "bulk-create users" — the primary outcome. Atomicity is default A-1.
- **Behaviour:** if and only if the file passes R-2, R-3, R-4 and R-7 with no error, one user is created per row, all
  or none: after the request, either every row's user exists or none does. The success response states how many
  users were created and lists each created user's id and email in file order. Each created user is in the same
  initial state a single-created user would be (R-9, G-2).
- **Rules the request leaves out (bounded here):** partial-success mode (alternative A-1: create the valid rows,
  report the rest — revalidate if the admin wants it); ordering guarantees among users beyond file order in the
  response; import of password or credentials (R-9).
- **Open gaps / prerequisites:** **G-6** the user store must support an all-or-nothing multi-user write (one
  transaction) or an equivalent compensation; no store is known. If it cannot, the observable contract (all or
  none) still holds and the plan must provide compensation (AD-2 in architecture.md).
- **State and data assessment:** resource: user records in the user store (authority: the store; target identity: the
  email, compared case-insensitively). Before: none of the file's emails exist. After: all exist, exactly once each.
  Changed: only user records (created); observed: existing users (read for conflicts); out of scope: roles of
  existing users, sessions, mail. Partial failure: any failure before commit leaves the store unchanged; failure
  during commit rolls back everything (or compensates, G-6); the response says nothing was created, except when the
  outcome is unknown (R-8). Check: user count and the set of emails before/after.
- **Acceptance**
  - **R-5/A1** — surface: HTTP API plus the user list read path. Confirm: API test then read-back of the users.
    - Positive: admin `root@example.com`, seeded users as in R-4/A1, uploads S-1 → 201,
      `{"status":"created","createdCount":2,"users":[{"id":…,"email":"ada@example.com"},{"id":…,"email":"grace@example.com"}]}`;
      read-back shows both users, user count +2.
    - Failure: S-2 → 422 `{"status":"rejected","createdCount":0,…}`; read-back shows **none** of its rows exist,
      in particular row 1 `ada@example.com` (valid on its own) was not created; user count unchanged.
    - Boundary: a one-row file (`email` header + `ada@example.com`) creates exactly 1 user.
  - **R-5/A2** — surface: HTTP API with fault injection in the store. Confirm: integration test (after G-6).
    - Positive: n/a: covered by R-5/A1.
    - Failure: with the store configured to fail on the second insert of a two-row S-1 upload → 5xx
      `INTERNAL`, `createdCount` 0, read-back shows neither user.
    - Boundary: n/a: covered by R-8/A1.

### R-6 Rejections explain exactly what to fix

- **Basis:** derived from R-5 atomicity: an all-or-nothing rejection is only usable if it says which rows failed.
- **Behaviour:** a rejected import returns `status: "rejected"`, `createdCount: 0`, and an `errors` array. Each
  entry has `row` (1-based data row, or null for file/header errors), `column` (or null), a stable machine-readable
  `code`, and a human-readable `message`. Row validation (R-3, R-4) reports **all** problems of all rows in one
  response, ordered by row, then column order in the header. File-level and header errors (R-2, R-3 header rules,
  R-7) stop processing: only those are returned. Messages never echo credentials or the raw value of a secret-like
  column.
- **Acceptance**
  - **R-6/A1** — surface: HTTP API. Confirm: API test.
    - Positive: S-2 → exactly these entries, in order: `{row:2,column:"email",code:"EMAIL_INVALID"}`,
      `{row:3,column:"email",code:"EMAIL_EXISTS"}`, `{row:4,column:"email",code:"EMAIL_DUPLICATE_IN_FILE"}`,
      `{row:5,column:"role",code:"ROLE_NOT_ALLOWED"}` — four entries, `createdCount` 0.
    - Failure: S-5 (no `email` column) → a single entry `{row:null,column:"email",code:"MISSING_REQUIRED_COLUMN"}`
      and no row-level entries even though row 1 would otherwise be checked.
    - Boundary: S-8 → two header entries (`MISSING_REQUIRED_COLUMN` for `email`, `UNKNOWN_COLUMN` for
      `email;name`), both with `row:null`.
  - **R-6/A2** — surface: HTTP API. Confirm: API test. No leakage.
    - Positive: n/a: covered by R-6/A1.
    - Failure: S-6 → neither the response body, nor server logs, nor the audit record contains `hunter2`.
    - Boundary: the row `bad,,no-such-role,extra` under the header `email,name,role` (four fields, three columns,
      and it would also fail email and role checks) → `ROW_FIELD_COUNT` is the only entry for that row (a row that
      cannot be aligned to the header is not further validated).

### R-7 Upload size and row-count bounds (values OPEN)

- **Basis:** derived, not requested. An unbounded upload to a synchronous, all-or-nothing, in-memory-validated
  operation cannot work safely (memory, request time, one huge transaction), so a maximum bytes bound and a
  maximum rows bound are necessary (duty 4). Only their **values** are open.
- **Behaviour:** the operation enforces `MAX_BYTES` (request body size) and `MAX_ROWS` (data rows). A body larger
  than `MAX_BYTES` is rejected `FILE_TOO_LARGE` (HTTP 413) **while streaming**: the server stops reading at the
  bound, so a body of 10 × `MAX_BYTES` or a chunked body without a declared length is also refused without being
  fully buffered. A file within `MAX_BYTES` with more than `MAX_ROWS` data rows is rejected `TOO_MANY_ROWS` (422).
  Both are file-level errors, create nothing, and state the bound in the message. A file at exactly the bound is
  accepted. The **effective** bound is the smaller of the configured value and any runtime limit (request body
  limit, request time limit, transaction/statement limit); the product must never advertise a bound the runtime
  would break first.
- **Labelled defaults:** none chosen. **No default is supportable:** there is no repository, runtime or platform
  evidence to derive a value from, and a number guessed here could exceed a real runtime limit or needlessly
  restrict admins. The bound is therefore **kept open (G-1)** rather than invented.
- **Open gap G-1:** values of `MAX_BYTES` and `MAX_ROWS`. Missing evidence: the deployment runtime's request-body
  and request-time limits, and the measured time to create N users in the real user store. Owner: user (product
  decision on how large an import must be) plus discovery of the runtime. Confirming observation: (1) read the
  runtime's documented limits; (2) time a create of N users against the real store. Due: before the plan stage
  freezes the limits; revalidate whenever the runtime or store changes. Safe interim behaviour: the feature must not
  ship without both values set; the behaviour *shape* above is final. Affected work: R-7 checks and any capacity
  check stay unready; R-1 to R-6 and R-8 to R-11 are unaffected.
- **Acceptance** (written against the effective values; **NOT-REPLAYED** until G-1 closes)
  - **R-7/A1** — surface: HTTP API. Confirm: API test with generated files.
    - Positive: a valid file of exactly `MAX_ROWS` rows `u1@example.com` … `uN@example.com` (N = `MAX_ROWS`) and
      at most `MAX_BYTES` bytes → 201, N users created.
    - Failure: the same with N+1 rows → 422 `TOO_MANY_ROWS`, zero created; a body of `MAX_BYTES`+1 bytes → 413
      `FILE_TOO_LARGE`, zero created.
    - Boundary: a valid one-row file padded with trailing newline characters to exactly `MAX_BYTES` bytes → 201
      (empty lines are skipped, so padding does not add rows); `MAX_BYTES`+1 bytes → 413.
  - **R-7/A2** — surface: HTTP API with a chunked body. Confirm: integration test.
    - Positive: n/a: covered by R-7/A1.
    - Failure: a chunked upload with no `Content-Length` that streams past `MAX_BYTES` → 413 and the server did not
      read substantially beyond the bound (observed via bytes consumed on the test connection or process memory).
    - Boundary: n/a: covered by R-7/A1.

### R-8 Concurrency, retries and unknown outcomes

- **Basis:** derived from R-4/R-5; request silent. Default A-1/A-3.
- **Behaviour:** the uniqueness of emails is guaranteed by the user store at write time, not only by the
  pre-commit check. If two imports (or an import and a single creation) overlap on an email and the other change is
  committed first, the later import's commit fails as a whole, creates nothing, and returns 409 `CONFLICT` with a
  message to retry (rows are not identified; a retry returns precise `EMAIL_EXISTS` rows). A second submission of an
  already imported file is not an error of the system: every row is `EMAIL_EXISTS` (R-4), nothing changes. A
  client that did not receive a response (timeout, dropped connection) may not assume either outcome; recovery is to
  look at the user list or resubmit — the resubmission result (`EMAIL_EXISTS` rows) shows what was created. There is
  no automatic retry and no import identifier.
- **Acceptance**
  - **R-8/A1** — surface: HTTP API with two concurrent clients. Confirm: integration test with the store's
    commit paused by a test hook.
    - Positive: two admins concurrently upload files with disjoint emails → both 201, all users exist.
    - Failure: two concurrent uploads of S-1 → exactly one 201 and one 409 `CONFLICT` (or, if the second began
      after the first committed, a 422 with `EMAIL_EXISTS` on rows 1 and 2); in both cases exactly 2 users exist.
    - Boundary: a single creation of `grace@example.com` committed between an import's validation and its commit →
      the import returns 409 `CONFLICT`, `ada@example.com` (row 1) was **not** created.
  - **R-8/A2** — surface: HTTP API. Confirm: API test.
    - Positive: n/a: covered by R-5/A1.
    - Failure: resubmitting S-1 immediately after its success → 422, `EMAIL_EXISTS` for rows 1 and 2, user count
      unchanged.
    - Boundary: client abort after the server has committed (connection closed before the response) → 2 users
      exist; resubmission yields the same `EMAIL_EXISTS` result as above.

### R-9 New users carry no secrets in the file; activation is not decided here

- **Basis:** derived; request silent on how new users get access. Needed for safety: putting passwords in an
  uploaded file would spread secrets into files, uploads and logs.
- **Behaviour:** the CSV carries no password or other secret (a column that looks like one is an unknown column,
  R-3). The feature sends no email or other notification (A-7). Created users are put in the same initial
  state a single-created user would be (G-2). The feature creates no usable credential on its own.
- **Open gap G-2:** how a bulk-created user first gets access (invitation email, set-password link, admin-set
  temporary password, external identity provider). That is a product decision that needs the user; the interim is
  "same initial state as single creation, no notification". Dependent work: R-9 activation checks only.
- **Acceptance**
  - **R-9/A1** — surface: HTTP API plus store read-back. Confirm: API test, plus inspection of captured outbound
    mail (none).
    - Positive: after S-1, the two users exist with the initial state of a single-created user, no credential set by
      this feature.
    - Failure: S-6 (`password` column) → rejected as `UNKNOWN_COLUMN`; no user created.
    - Boundary: n/a: covered by R-3/A1.
  - **R-9/A2** — surface: test mail sink. Confirm: API test.
    - Positive: n/a: a no-notification rule has no positive case.
    - Failure: after a successful S-1 import the test mail sink holds zero messages.
    - Boundary: n/a: covered by R-5/A1.

### R-10 Personal data lifecycle, logging and audit

- **Basis:** derived: the file is a bulk list of personal data (emails, names).
- **Behaviour:**
  - *Uploaded file bytes:* held only for the duration of the request, in memory (or request-scoped temporary
    storage deleted at request end, success or failure); never written under a client-supplied filename;
    not retained afterwards.
  - *Created users:* stored in the user store like any user, readable by whoever may read users today; removal
    follows the existing user-deletion rules (preserved, unchanged).
  - *Response / error report:* returned only to the uploader; not stored server-side (A-6). It contains emails and
    row numbers taken from the uploader's own file.
  - *Diagnostic logs:* never contain file contents, row values, emails or names; only counts, codes and a request
    correlation id. Untrusted values are sanitised if ever logged.
  - *Audit record (owned by this feature):* one record per attempt, written for success and for rejection:
    timestamp, uploader id, outcome (`created`, `rejected`, `conflict`, `failed`), row count, created count, error
    code counts, and, on success, the created user ids. No file contents, no emails of rejected rows, no filename.
    Retention and removal follow the product's existing audit retention (G-7). Failure to write the audit record
    does not change the business result but is itself logged as an operational error.
- **Open gap G-7:** the product's existing audit sink and retention period (unknown). Interim: audit record goes to
  whatever audit facility exists; if none, plan raises it before implementation.
- **Acceptance**
  - **R-10/A1** — surface: captured server logs and audit sink. Confirm: API test with log capture.
    - Positive: after S-1 the audit sink holds one record with outcome `created`, uploader id of `root@example.com`,
      row count 2, created count 2, two user ids; no email strings.
    - Failure: after S-2 one record with outcome `rejected`, created count 0, code counts `EMAIL_INVALID`:1,
      `EMAIL_EXISTS`:1, `EMAIL_DUPLICATE_IN_FILE`:1, `ROLE_NOT_ALLOWED`:1; captured logs contain none of the strings
      `ada@example.com`, `existing@example.com`, `Bad Row`.
    - Boundary: after a 401/403 attempt a record is still written (or, if the product's convention is to log
      denials elsewhere, that destination holds an entry) with no file data.
  - **R-10/A2** — surface: server filesystem / process inspection. Confirm: integration test.
    - Positive: n/a: no retention is the positive.
    - Failure: after success and after rejection, no file derived from the upload remains in the temp area.
    - Boundary: an upload with filename `../../etc/x.csv` creates no file at any such path.

### R-11 Admin interface for uploading and seeing the result

- **Basis:** request 2026-11-21, "Let admins upload a CSV" — an admin acts through an interface; delivery surface
  is assumed to be a web admin UI over R-1..R-10 (A-10, **G-5**).
- **Behaviour:** an admin-only page offers: a heading and help text that lists the accepted columns (`email`
  required; `name`, `role` optional), states that existing users are never changed, that nothing is created if any
  row is invalid, and the size/row limits (values from G-1); a file picker (keyboard and pointer; drag-and-drop is
  an enhancement, never the only path) and an **Import users** button disabled until a file is chosen.
  - *Submitting:* the button and picker are disabled, an indeterminate progress status "Validating and creating
    users…" is shown (no fake percentage; processing is synchronous, AD-1), and double submission is impossible.
  - *Success:* a panel states "N users created" and lists them (id/email), and offers to import another file.
  - *Rejected:* a panel states "No users were created. N problems in M rows." and lists errors as a table
    (Row, Column, Problem) in file order; file-level errors (no row number) appear as a banner in the same panel instead of a table.
  - *Unknown outcome (network failure/timeout, no server response):* the page says it could not confirm whether
    users were created, tells the admin to check the user list before retrying, and offers no automatic retry.
  - *Denied (401/403):* a permission or sign-in message, no result data.
  - *Client-side pre-check:* a file over `MAX_BYTES` is refused before upload with the same message as the server's;
    this is only a convenience, the server decides (R-7).
  - *Empty state:* before any file is chosen, the page shows the help text and an empty result area that says what
    will appear there.
- **Open gap G-5:** whether the product actually has a web admin area or is API-only, and its existing visual
  identity and component set; if API-only, R-11 and R-12 are replaced by API documentation. Owner: user.
- **Acceptance**
  - **R-11/A1** — surface: real browser (Chromium-class), viewport 1280×800. Confirm: automated browser test with
    the sample files.
    - Positive: admin chooses S-1, presses **Import users** → progress status appears, then the success panel reads
      "2 users created" and lists `ada@example.com`, `grace@example.com`; the status region is announced
      (`aria-live`).
    - Failure: S-2 → rejected panel "No users were created. 4 problems in 4 rows." with the four table rows of
      R-6/A1 in order; S-3 → banner stating the file has no data rows.
    - Boundary: Import button is disabled with no file; after pressing it once, a second press is not possible while
      the progress status is shown.
  - **R-11/A2** — surface: browser with the network blocked after request send (offline emulation). Confirm: browser test.
    - Positive: n/a: covered by R-11/A1.
    - Failure: connection dropped before the response → the "could not confirm" state appears; no success panel.
    - Boundary: a file above `MAX_BYTES` (after G-1) is refused client-side with no network request sent.
  - **R-11/A3** — surface: browser, keyboard only. Confirm: browser test.
    - Positive: Tab reaches the file picker, then **Import users**; Enter/Space operate them; the result panel
      receives or announces focus.
    - Failure: n/a: covered by R-12/A1.
    - Boundary: n/a: covered by R-12/A1.

## Non-functional requirements

Quality attributes were screened against the request. Numeric bounds are not invented; where a bound is needed
and unsupported it is open under G-1.

### R-12 Interface quality and accessibility (applies if the delivery surface is a UI, G-5)

- **Basis:** the stage rule for any deliverable with a user interface; request itself gives no visual constraint.
- **Visual direction (recorded for the plan):** established product identity and platform conventions take
  precedence once discovered (G-5). Absent that, the reference is the **light Google Gemini look with Material 3
  Expressive principles** (platforms/ui.md#light-expressive-starting-point): luminous light canvas, tonal rounded
  surfaces, restrained saturated accent, humanist sans-serif from locally available fonts with fallbacks, primary
  action (file choice, Import) in the strongest position, result panel as the focal point. **Starts light with a
  dark option** (follows `prefers-color-scheme`, with a manual override only if the product already has one). The
  concrete treatment is chosen at plan time and recorded in an AD.
- **Observable criteria:**
  1. One visual system: spacing and type scales and a palette defined as tokens with a light and a dark theme.
  2. Designed empty, loading (progress), success, rejected, unknown-outcome and denied states (R-11), not default
     browser styling or raw JSON.
  3. Works at 360 px and 1280 px wide with **no horizontal page overflow**; the error table becomes stacked rows
     (or scrolls inside its own container) at narrow width.
  4. Visible keyboard focus on every interactive element; text contrast ≥ 4.5:1 (≥ 3:1 for large text and UI
     boundaries), WCAG 2.2 AA, in both themes.
  5. Motion only to explain a change (progress → result), disabled under `prefers-reduced-motion: reduce`.
  6. One icon set; no icon is the only carrier of meaning (errors have text).
  7. Errors and results are exposed to assistive technology: live region for status, programmatic association of
     table headers.
- **Acceptance**
  - **R-12/A1** — surface: real browser at 360×740 and 1280×800, light and dark. Confirm: automated browser test with
    axe-core (or equivalent) plus visual review of screenshots.
    - Positive: in all four combinations the empty page and the success panel for S-1 have zero axe contrast/name
      violations and `document.documentElement.scrollWidth <= innerWidth`.
    - Failure: the S-2 rejected panel at 360 px has no horizontal page overflow and every table cell is readable.
    - Boundary: with `prefers-reduced-motion: reduce` emulated, no CSS transition/animation longer than 0 ms runs on
      the result swap; every focusable element shows a visible focus indicator.

### R-13 Reliability and data integrity

Covered by R-5 (all-or-nothing), R-8 (concurrency, unknown outcome). Verification: R-5/A1–A2, R-8/A1–A2. No
availability or durability target beyond the existing user store's is stated and none is invented: **excluded,
reason:** the request sets none, and this feature adds no new store.

### R-14 Security, performance, compatibility and operability

- **Security:** server-side authority and CSRF (R-1); no secrets in files, logs, or notifications (R-6, R-9, R-10);
  filename never used as a path (R-10/A2); values are treated as data — stored and displayed escaped (UI escapes
  all echoed values; no CSV, XLSX or other export is produced by this feature, so spreadsheet-formula injection on
  output does not apply). Verification: R-1/A1, R-6/A2, R-10/A2, and a UI test that submits a name
  `<img src=x onerror=alert(1)>` (as a CSV row `ada@example.com,"<img src=x onerror=alert(1)>",`) and observes the
  success/readback screens rendering it as literal text, with no script execution.
- **Performance / capacity:** the only bound is R-7 (G-1). Acceptance: at `MAX_ROWS` rows the request completes
  within the runtime's request time limit (value from G-1, **unresolved**). No throughput, latency or concurrency
  number is stated or invented. Rate limiting and abuse thresholds: **excluded**, no basis for a number; revisit
  with the first evidence of misuse.
- **Compatibility:** CSV produced by common spreadsheet tools in "CSV UTF-8" mode (BOM, CRLF) is accepted (R-2/A1);
  locale-delimited (semicolon) files are rejected with an explanatory header error. Supported browsers: **unresolved**
  (follows the product's existing support policy, G-5).
- **Observability:** audit record per attempt (R-10). Login/authentication coverage: **n/a**, this feature adds no
  authentication of its own.
- **Maintainability:** **n/a**, no constraint beyond the product's existing practice.

## State, information lifecycle and service boundaries

| State | Owner / location | Who may read | Simultaneous changes | Ends / removed | Runtime quota |
| --- | --- | --- | --- | --- | --- |
| Uploaded bytes | the request handler, memory or request-scoped temp | the handling process only | n/a (per request) | end of request; deleted on success and failure | `MAX_BYTES` (G-1) |
| User records created | the existing user store (authority for existence and uniqueness) | whoever may read users today (preserved) | unique email enforced at write; loser fails whole (R-8) | existing user-deletion rules (preserved) | store limits (G-1, G-6) |
| Import result / error report | the HTTP response; in the UI, page memory | the uploader only | n/a | discarded when the page is left or a new import starts | bounded by `MAX_ROWS` entries |
| Audit record | the product's audit facility (G-7) | operators with existing audit access | append-only | per existing audit retention (G-7) | n/a |
| Admin status | the existing identity/authorization source (G-4) | server only | changes apply from the next request (R-1) | n/a | n/a |

Service boundaries (service-discovery.md#verification): **user store** — current authority for users, read for
conflicts and written in one atomic step, no cache of user existence is allowed to answer a conflict check (a stale
"does not exist" would defeat R-4); concurrent writers are arbitrated by the store's uniqueness guarantee (R-8).
**Identity/authorization** — current authority for admin status; freshness: checked each request, revocation applies
from the next request (R-1), no async completion. **Async completion/incremental state/event coverage:** n/a — the
operation completes within the request (AD-1); there is no job, queue, webhook or incremental sync, and no event is
published to other systems (A-7). **Owned event coverage:** the audit record of R-10 only. **Mail/notification
boundary:** none (R-9). No service is added.

## Behaviour model

**Flow F-1 (success), R-1 R-2 R-3 R-4 R-5 R-10:** admin → API: upload S-1 → authorize (T-1) → size guard while
streaming (T-2) → parse (T-3) → validate rows and duplicates against the store (T-4) → atomic create (T-5) → audit
(T-6) → 201 with created list → UI shows success panel.
**Flow F-2 (rejection), R-2 R-3 R-4 R-6 R-7:** same start; any of T-1…T-4 fails → no write → audit (T-6) → 4xx with
`errors` → UI shows rejected panel. **Flow F-3 (conflict/failure), R-8:** T-5 fails on uniqueness or store error →
rollback (T-7) → 409 or 5xx → UI shows rejected or unknown-outcome state.

Import attempt (transient entity, one per request): `Received → Authorized → Parsed → Validated → Committed`; any
state before Committed can go to `Rejected`; `Validated → Conflicted/Failed` on commit failure. `Committed`,
`Rejected`, `Conflicted/Failed` are terminal. User record: `Absent → Present` is the only transition this feature
performs.

| T | Before / guard | Operation | After / observation | Failure and recovery | Cases |
| --- | --- | --- | --- | --- | --- |
| T-1 | Received; caller authenticated and currently admin | evaluate authority | Authorized, else 401/403 with no data | none; nothing written | R-1/A1 |
| T-2 | Authorized; bytes ≤ `MAX_BYTES` | count bytes as streamed | within bound, else 413 | stops reading; nothing written | R-7/A1-A2 |
| T-3 | within bound; valid UTF-8 CSV, header OK, ≥ 1 row, rows ≤ `MAX_ROWS` | parse | Parsed, else file-level 422 | nothing written | R-2/A1, R-3/A1, R-7/A1 |
| T-4 | Parsed | validate each row, in-file duplicates, existing emails | Validated, else 422 with all row errors | nothing written | R-3/A1, R-4/A1, R-6/A1 |
| T-5 | Validated | create all users in one atomic write | Committed; 201 | on uniqueness conflict → T-7 | R-5/A1 |
| T-6 | any terminal state | write audit record (R-10) | one record per attempt | audit failure logged, business result unchanged | R-10/A1 |
| T-7 | commit failed | roll back/compensate; no user from this file remains | Conflicted/Failed; 409 or 5xx, `createdCount` 0 | admin resubmits (R-8) | R-5/A2, R-8/A1 |

Invalid/forbidden events: submit while not admin → T-1 rejection; submit the same file twice → second is T-4
rejection with `EMAIL_EXISTS` (no side effects); any attempt to modify an existing user → not possible through
this operation (R-4).

## Samples (named inputs for the acceptance lines)

Seed state unless stated: users `root@example.com` (admin), `member@example.com` (non-admin),
`existing@example.com` (non-admin, name `Existing`). Files are UTF-8, `\n` line endings unless stated; `⏎` is not
literal.

- **S-1** (CRLF): `email,name,role` / `ada@example.com,Ada Lovelace,` / `grace@example.com,"Hopper, Grace",`
- **S-2:** `email,name,role` / `ada@example.com,Ada Lovelace,` / `not-an-email,Bad Row,` /
  `existing@example.com,Existing,` / `ada@example.com,Dup Ada,` / `grace@example.com,Grace,no-such-role`
- **S-3:** `email,name,role` + newline (header only). **S-4:** zero bytes.
- **S-5:** `name,role` / `Ada,`. **S-6:** `email,name,password` / `ada@example.com,Ada,hunter2`.
- **S-7:** S-1 preceded by bytes EF BB BF. **S-8** (CRLF): `email;name` / `ada@example.com;Ada`.
- **S-9:** `email,name,role` / `ada@example.com,Ada`. **S-10:** `email,name` / `ada@example.com,` then byte FF, newline.
- **S-11:** `email,name` / `ada@example.com,"Ada` (no closing quote).
- **S-14:** `email,name,role` / ` ada@example.com ,Ada,`.
- **S-15:** S-1 content with an empty line between the data rows and two empty lines at the end.

Hand-walks (item 10), **NOT-REPLAYED** — no product or runtime exists, so nothing was executed; each was walked
against the spec rules: (a) admin `root@example.com` (reachable as admin per R-1, G-4) uploads S-1: T-1 pass, T-2 pass,
T-3 pass, T-4: neither email exists, T-5 creates 2 → 201 (R-1, R-5). Then uploads S-1 again: T-1 pass (still admin),
T-4 finds both emails → rows 1 and 2 `EMAIL_EXISTS`, 422, count unchanged (R-4, R-8). (b) S-2: row 1 valid in
isolation, row 2 `EMAIL_INVALID`, row 3 matches seeded `existing@example.com` → `EMAIL_EXISTS`, row 4 repeats
row 1's email → `EMAIL_DUPLICATE_IN_FILE`, row 5 `no-such-role` → `ROLE_NOT_ALLOWED`; since errors exist nothing is written
(R-5), so row 1 is also not created. Recomputed: 4 errors, rows 2,3,4,5 in that order, matching R-6/A1. (c) The
254-character email arithmetic in R-3/A1 was computed by hand (64+1+(63+1+63+1+57+1+3)=254); a script that would
have checked it was written but not run (the run command needed an approval that was not granted). The `csv`-module behaviour
claims in R-2 (quoted comma, CRLF, short row length) are likewise unexecuted.

## Open gaps (summary)

| ID | Under | Gap | Owner | Safe interim | Affected work |
| --- | --- | --- | --- | --- | --- |
| G-1 | R-7 | `MAX_BYTES`, `MAX_ROWS` values; runtime body/time limits; store create timing | user + runtime discovery | do not ship without values; behaviour shape final | R-7 checks, R-14 performance |
| G-2 | R-9 | how new users first get access | user | no notification; initial state = single create | R-9 activation checks |
| G-3 | R-3 | user model, roles, default role, single-create rules, length limits | discovery of existing code | defaults in R-3 | role/length clauses |
| G-4 | R-1 | admin definition, admin session in tests, CSRF scheme | discovery of existing auth | deny by default | R-1 checks |
| G-5 | R-11, R-12 | web admin UI vs API-only; product identity, browser support | user | UI per R-11/R-12 starting point | R-11, R-12 |
| G-6 | R-5 | store supports atomic multi-user write or compensation | discovery of store | compensation (AD-2) | R-5/A2 |
| G-7 | R-10 | existing audit sink and retention | discovery | use existing audit facility | R-10 audit lines |

## Out of scope

Editing or deleting users in bulk; update-on-match/upsert; partial-success import; downloading a template or an
error-report CSV; import history or job status pages; scheduled or asynchronous imports; email invitations
(G-2); multiple files; Excel/other formats; non-UTF-8 encodings; other delimiters; SSO/SCIM provisioning.

## Request-outcome traceability

| Request outcome | Acceptance lines |
| --- | --- |
| Admins can upload (and only admins) | R-1/A1-A3, R-11/A1-A3 |
| A CSV is accepted as the input | R-2/A1-A2 |
| Users are created from its rows | R-3/A1-A2, R-4/A1, R-5/A1-A2, R-9/A1-A2 |
| Bulk creation is safe to use and to recover from (derived) | R-6/A1-A2, R-7/A1-A2, R-8/A1-A2, R-10/A1-A2, R-14 |
| The upload is usable as an interface (derived) | R-11/A1-A3, R-12/A1 |

## Retired

None (first specification; no earlier R-<n>).

## Submission

**summary:** First specification for admin bulk user creation from a CSV upload (R-1…R-14), written with no
repository, baseline or runtime, so existing-product facts are open gaps G-1…G-7 rather than guesses. No material
requirement conflict. Unresolved and keeping dependent work unready: G-1 (R-7 size/row bounds, no supportable
default), G-2 (activation, needs the user), G-3, G-4, G-5, G-6, G-7 (see table).
Assumptions (value; basis; alternatives; revalidate when):
- **A-1** (R-5) all-or-nothing import; basis: safest, simplest recovery and idempotent retry; alt: create valid rows
  and report the rest; revalidate if admins want "import what's new".
- **A-2** (R-3, R-4) email trimmed, compared case-insensitively, stored as given (trimmed); basis: common email
  practice, no user model known; alt: store lower-cased; revalidate at G-3.
- **A-3** (R-5, R-8) processed synchronously in the request (AD-1); basis: bounded size makes it sufficient; alt:
  background job with status; revalidate if G-1 shows the runtime's request limit cannot cover `MAX_ROWS`.
- **A-4** (R-3) columns `email` (required), `name`, `role` (optional); unknown/duplicate column rejects the file;
  basis: minimal set implied by "users"; alt: ignore unknown columns; revalidate at G-3.
- **A-5** (R-1) admin checked at request start; basis: simplest correct freshness; alt: re-check before commit;
  revalidate if revocation must cut in-flight work.
- **A-6** (R-10) no server-side persistence of the result or import history; basis: not requested, avoids new
  personal-data storage; alt: stored import records; revalidate if admins need to review past imports.
- **A-7** (R-9) no notifications sent; basis: outward-facing messages not requested; alt: invitation email (G-2).
- **A-8** (R-1…R-8) default interface names: `POST /api/admin/users/bulk`, multipart field `file`, JSON bodies
  `{status, createdCount, users|errors}`, statuses 201/401/403/409/413/422/5xx, error codes as listed; basis: no
  existing conventions known; alt: follow the existing API conventions; revalidate at G-3/G-5 discovery.
- **A-9** (R-2) UTF-8, comma, RFC 4180 quoting, optional BOM; basis: what common spreadsheets export as "CSV UTF-8";
  alt: broaden encodings/delimiters; revalidate on first rejected real-world file.
- **A-10** (R-11) the delivery surface includes a web admin UI; basis: "admins upload" implies an interface; alt:
  API-only (G-5).
- **A-11** (R-7) *no value chosen*: no default for `MAX_BYTES`/`MAX_ROWS` because no runtime evidence exists; kept
  open as G-1 with confirming observations listed there.

**primary:** R-1, R-2, R-5, R-11 (the request's directly asked outcomes: admins upload; CSV accepted; users
created; and the interface through which an admin does it). R-11 is primary only if G-5 confirms a UI.

**evidence_refs:** `spec.md` (this file), requirement sections R-1 … R-14 within it, `architecture.md` (AD-1…AD-4);
sources used: the request text (2026-11-21); GUIDES/README.md, GUIDES/behavioral-requirements.md
(#behavior-model, #traceability-and-review, #actors-channels-and-state-ownership), GUIDES/requirements-definition.md
(#state-and-data-change-assessment), GUIDES/service-discovery.md (#verification, #runtime-state-placement,
#observability-coverage), GUIDES/platforms/ui.md (#light-expressive-starting-point); RFC 5321 §4.5.3.1
(rfc-editor.org/rfc/rfc5321.txt, fetched 2026-11-21). No `backchain-check` receipt (command does not exist here).
No test or hand-walk was executed; all are `NOT-REPLAYED`.
