# User Administration — Product Specification

Status: proposed by the spec stage on 2026-11-21. Not yet planned, built or tested. `KNOWLEDGE/` in the stage text is this
directory; this file is `KNOWLEDGE/spec.md` and its companion is `architecture.md`.

## 1. Basis, sources and evidence limits

| Source | Locator | Status | Use |
| --- | --- | --- | --- |
| Request, 2026-11-21 | "Let admins upload a CSV to bulk-create users." | Accepted user instruction (only one) | Origin of R-1 … R-10 (see per-R basis) |
| Prior spec, research, discovery results | none exist | Absent | Nothing preserved from them |
| Repository / existing product | none supplied (no repository in this run) | Absent | Existing user model, roles, auth, UI, API conventions are **unknown**; see gaps G-1 … G-9 |
| GUIDES (`behavioral-requirements.md#behavior-model`, `#traceability-and-review`, `requirements-definition.md`, `platforms/ui.md#light-expressive-starting-point`) | as named | Harness guides | Shape of this document |

**Evidence limits.** Everything below about the *current* product is unobserved. Where this spec needs a fact about the existing
system (what "admin" means, the user fields, the default role, the UI shell, API conventions) it states an **assumption (A-n)**
and an **open gap (G-n)**. Assumptions are defaults chosen so the work can proceed unattended; each is overridable by a person
without changing the rest of the spec. The plan stage must reopen the real repository and reconcile A-1 … A-9 before
implementation of the affected requirements. No numeric production bound has been invented; test fixtures use *test-only*
configuration values (section 9).

### Assumptions (record of defaults taken)

| ID | Assumption | Gap | Affects |
| --- | --- | --- | --- |
| A-1 | The product already has authenticated sessions and a notion of an "admin" role distinct from non-admin users; a request can be attributed to a user whose current role is read from the user store. | G-1 | R-1 |
| A-2 | A user is identified for login by one email address, unique **case-insensitively** across all user records of any status (active, invited, deactivated). Users also have a display `name`. | G-5, G-6 | R-4, R-5, R-8 |
| A-3 | Imported users get the product's existing default non-admin role, named `member` in fixtures. The CSV cannot choose a role. | G-3 | R-4, R-8 |
| A-4 | Imported users are created without a usable credential and reach the product through the existing "set/reset password" or invite mechanism. The CSV carries no password. No email is sent by this feature. | G-2 | R-8 |
| A-5 | Whole-file atomicity: if any row is invalid, no user is created. | G-4 | R-6 |
| A-6 | Name is 1–100 characters after trimming, counted as Unicode code points; email is ≤ 254 characters after trimming (RFC 5321 path limit as commonly applied; not re-verified in this run). | G-6 | R-4 |
| A-7 | The product is single-tenant for user identity (one email namespace). | G-7 | R-5 |
| A-8 | The product has, or can add, an audit/log sink; an import attempt writes one entry with no row content. | G-8 | NFR privacy, operability |
| A-9 | Admin upload surface is a page at `/admin/users/import` and the API is `POST /api/admin/users/import` (multipart, one part named `file`). Paths are placeholders to be aligned with existing conventions. | G-9 | R-2, R-10 |

## 2. Scope

**In scope.** An admin uploads one CSV file with an email and a name per row; the system validates the whole file and either
creates every user in it or creates none, and tells the admin exactly what happened.

**Non-goals (domain rules the request leaves out; each bounds the R-n named).**

| Left out | Bounds | Consequence in this spec |
| --- | --- | --- |
| Updating, upserting, deactivating or deleting existing users by CSV | R-5, R-6 | An email that already exists is a row error; existing users are never modified. |
| Assigning role, groups, teams or permissions from the CSV | R-3, R-4, R-8 | A `role` (or any other) column is rejected, not ignored. |
| Passwords or secrets in the CSV | R-3, R-8 | No such column exists; `password` is an unknown header. |
| Sending invitation or welcome emails | R-8 | See G-2. |
| Dry-run / preview-only validation, import history page, undo/rollback of a committed import, downloadable template | R-6, R-7, R-10 | Not offered. The expected columns are described on the page. |
| Formats other than comma-separated UTF-8 text (Excel `.xlsx`, `;` or tab delimiters, other encodings) | R-2, R-3 | Rejected with an explanatory file error. |
| Background/asynchronous import of very large files | R-9 | Synchronous only, bounded by the limits of R-9. |

## 3. Behavior model

### 3.1 Actors, channels, state ownership

| Actor | Interaction / channel | State owner | Observable outcome |
| --- | --- | --- | --- |
| Admin (browser) | Opens upload page; `POST` multipart to the import endpoint (request/response, synchronous; the response *is* the completion signal) | Client memory: chosen file, request state, last result (transient). Server: the user store (authoritative, durable). | Result panel; later, the new users exist |
| Non-admin / anonymous caller | Same endpoint or page | none | 403 / 401, nothing changes |
| User store | Read existing emails; insert users in one atomic unit | Existing product | Imported users visible wherever users are listed |
| Audit/log sink | One entry per attempt | Existing product (A-8) | Entry with admin id, time, outcome, counts, error codes only |

Only the user store changes. The uploaded bytes and the result report are transient (request lifetime); no import record is
persisted by this feature beyond the audit entry. There are no other services; section 7 records the service-boundary concerns.

### 3.2 Flows

| ID | Flow | Requirements |
| --- | --- | --- |
| F-1 | Admin uploads a valid file → every row becomes a user → 201 with created users | R-1, R-2, R-3, R-4, R-5, R-6, R-7, R-8 |
| F-2 | File-level rejection (size, encoding, CSV syntax, headers, row count, missing file) → 4xx with `file_errors`, nothing created | R-2, R-3, R-9, R-7 |
| F-3 | Row-level rejection (any invalid or conflicting row) → 422 with every `row_errors` entry, nothing created | R-4, R-5, R-6, R-7 |
| F-4 | Unauthenticated / non-admin caller → 401 / 403, file not read, nothing created | R-1 |
| F-5 | Commit-time conflict (another writer took an email between validation and commit) → 422 `ALREADY_EXISTS` for that row, nothing created | R-5, R-6 |
| F-6 | Admin UI: choose file → submit → pending → one of {success, file-level rejection, row-level rejection, auth failure, unconfirmed network failure} → retry or choose another file | R-10, R-7 |

### 3.3 Request phases and transitions

The import request is stateless between calls (no persisted import entity); these are its phases within one call. The only
persisted state change is T-8.

| T | Origin | Before → trigger/guard | Operation | After and observation | Failure / recovery |
| --- | --- | --- | --- | --- | --- |
| T-1 | R-1, F-4 | Received → caller has no valid session | none | 401, store unchanged | Sign in and retry |
| T-2 | R-1, F-4 | Received → session user's *current* role is not admin | none | 403, store unchanged | — |
| T-3 | R-2, F-2 | Authorized → no/duplicate `file` part, size > limit | none | 400 `NO_FILE`/`INVALID_UPLOAD`, or 413 `FILE_TOO_LARGE` | Fix and resubmit |
| T-4 | R-2, R-3, R-9, F-2 | Authorized → bytes not UTF-8, CSV unparseable, headers wrong, no records, too many rows | decode, parse, check headers/row count | 400 with `file_errors` (all header problems together) | Fix and resubmit |
| T-5 | R-4, R-5, F-3 | Parsed → ≥ 1 row invalid or conflicting | validate every row, collect all errors | 422 with `row_errors`, store unchanged | Fix and resubmit |
| T-6 | R-6, F-1 | Parsed → all rows valid | begin atomic unit; re-check emails against the store | proceeds to T-8, or T-7 | — |
| T-7 | R-5, R-6, F-5 | Atomic unit → an email now exists (concurrent writer) | roll back the whole unit | 422 `ALREADY_EXISTS` for that row, store unchanged | Resubmit |
| T-8 | R-6, R-8, F-1 | Atomic unit → all inserts succeed | commit; write audit entry | 201 with created users; store gains exactly N users | Lost response: see R-6.4 |
| T-9 | R-6 | Any phase → unexpected server fault before commit | roll back | 5xx; store unchanged | Resubmit; replay-safe by R-6.4 |

Phase order is fixed: auth (T-1/T-2) → upload checks (T-3) → decode/parse/header/row-count (T-4) → row validation (T-5) →
commit (T-6…T-8). The first failing phase decides the response; later phases do not run. File-level errors therefore never
appear together with row errors.

## 4. Requirements

Common conventions used by the acceptance lines below.

* **Row number** = 1-based position of a data record after the header record (the first record after the header is row 1).
* **Surface** "API" = the import endpoint of A-9 called with the session named; "UI" = the page of A-9 in a browser; "Store" =
  reading the user store directly in the test; "Log" = the audit/log sink.
* Response shape (assumption, to be aligned with API conventions at plan time): success
  `201 {"status":"created","created_count":N,"users":[{"id","email","name"}]}`; rejection
  `{"status":"rejected","file_errors":[{"code","header?","message"}],"row_errors":[{"row","field","code","message","first_row?"}]}`.
* Fixtures (`S0`, `C0`, `FX-*`, sessions) are defined in section 9. Expected results there were hand-walked (section 9.3).

---

### R-1 Only administrators may import

**Behavior.** The import endpoint and page are available to a caller whose *current* role is admin. Everyone else is refused
before the file is read.
**Boundaries.** Role is evaluated at the start of each request from the user store (A-1); a role change takes effect on the
caller's next request. A request already past authorization completes under that authorization.
**Error behavior.** No session → 401. Authenticated non-admin → 403. Neither reveals file validation results and neither
creates, changes or deletes any user.
**Consumer outcome.** Non-admins can neither perform nor learn about imports; the admin navigation shows the import page only
to admins.
**Basis.** Request 2026-11-21 "Let admins upload…". **Change type:** added. **Preserved:** existing authentication and roles
unchanged (unobserved). **Locators:** this spec §3.3 T-1/T-2. **Evidence limits:** role model unseen (A-1/G-1).
**Pending:** implementation and checks TC-1.x. **Open gap G-1:** which existing role/permission means "admin", and the auth
mechanism (session cookie vs token); decide at plan after reading the repository.

* **R-1.1 positive** — With `S0`, `admin` session, `FX-OK3` → not refused (proceeds; outcome per R-6.1). Surface API. Confirm TC-1.1.
* **R-1.2 failure** — No session, `FX-OK3` → 401; `member` session, `FX-OK3` → 403; Store afterwards equals `S0` (4 users). Surface API. Confirm TC-1.2.
* **R-1.3 failure (revocation)** — Steps: (1) session of `admin2` (role admin in `S0`) imports `FX-V1` → 201, 5 users; (2) test setup sets `admin2.role = member` in the store (direct fixture edit; the product need not offer role editing); (3) same session imports `FX-V2` → 403; Store has 5 users and no `v2@example.com`. Walk: step 1 permitted by R-1 (admin); step 3 refused by R-1 boundary (role read per request). Surface API + Store. Confirm TC-1.3.
* **R-1.4 positive/failure (UI visibility)** — As `admin` the admin navigation contains the import page link and the page loads; as `member` the link is absent and opening `/admin/users/import` directly shows a "not permitted" view (HTTP 403), with no upload control. Surface UI. Confirm TC-1.4.
* **R-1.5 boundary** — n/a: the set of roles is {admin, non-admin}; finer role distinctions are unobserved (G-1).

### R-2 Upload intake

**Behavior.** One file in a multipart part named `file` is accepted for processing. Content type and file extension are not
trusted; acceptance depends on the content passing R-3, R-4 and R-9.
**Boundaries.** Exactly one `file` part. Size limit = `IMPORT_MAX_BYTES` measured on the raw bytes of the file part; a file of
exactly that size is accepted, one byte more is refused. UTF-8 only; a leading UTF-8 byte-order mark is accepted and ignored.
Lines may end in LF or CRLF. Fields follow RFC 4180 quoting (quoted fields may contain commas, doubled quotes, line breaks).
**Error behavior.** No `file` part → 400 `NO_FILE`; more than one `file` part → 400 `INVALID_UPLOAD`; over the limit → 413
`FILE_TOO_LARGE`; bytes not valid UTF-8 → 400 `NOT_UTF8` (message tells the admin to save as "CSV UTF-8"); unterminated quote
→ 400 `MALFORMED_CSV`; zero bytes or only blank lines → 400 `EMPTY_FILE`. In every case nothing is created.
**Consumer outcome.** Admins get a precise reason the file itself is unusable.
**Basis.** Request "upload a CSV". **Change type:** added. **Locators:** §3.3 T-3/T-4. **Evidence limits:** hosting
platform/proxy body limits unknown (G-2). **Pending:** TC-2.x.
**Open gap G-2 (part):** `IMPORT_MAX_BYTES` production value, and whether a platform/proxy limit sits below it (then the proxy's
refusal must still reach the admin as the 413 behavior); see also R-9 and NFR performance.

* **R-2.1 positive** — `admin`, `FX-BOM` (BOM + CRLF) → 201, user `fred@example.com` / `Fred Ford` created. Surface API + Store. Confirm TC-2.1.
* **R-2.2 failure** — `admin`: no file part → 400 `NO_FILE`; two file parts → 400 `INVALID_UPLOAD`; `FX-EMPTY` (0 bytes) → 400 `EMPTY_FILE`; `FX-WS` (`\n\n  \n`) → 400 `EMPTY_FILE`; `FX-NOTUTF8` → 400 `NOT_UTF8`; `FX-UNTERM` → 400 `MALFORMED_CSV`. Store equals `S0` after each. Surface API + Store. Confirm TC-2.2.
* **R-2.3 boundary (size)** — Under `C0` (`IMPORT_MAX_BYTES=2048`): `FX-B2048` (valid one-row file padded with trailing newlines to exactly 2048 bytes) → 201 with 1 user; `FX-B2049` (same plus one more `\n`) → 413 `FILE_TOO_LARGE`, Store equals `S0`. Surface API + Store. Confirm TC-2.3.
* **R-2.4 failure (wrong dialect)** — `FX-H4` (semicolon-delimited) → rejected by R-3.3 with a message that mentions commas. Surface API. Confirm TC-3.3.

### R-3 Header contract

**Behavior.** The first record is a header. Recognised headers are `email` and `name`, matched after trimming whitespace and
case-insensitively; column order is free. Both are required.
**Boundaries.** Exactly the set {email, name}; any other header, a missing required header, or a repeated header (after
normalisation) is a file error. All header problems in one file are reported together.
**Error behavior.** `MISSING_HEADER` (with `header`), `UNKNOWN_HEADER` (with the offending text), `DUPLICATE_HEADER`; 400;
nothing created. A header-only file → 400 `NO_DATA_ROWS`.
**Consumer outcome.** A `role` or `password` column is refused loudly rather than silently dropped, so nobody believes a role
was applied.
**Basis.** Request "bulk-create users" (columns are not given; set by A-2/A-3/A-4 defaults). **Change type:** added.
**Locators:** §3.3 T-4. **Evidence limits:** columns beyond email+name are a product decision (G-3). **Pending:** TC-3.x.

* **R-3.1 positive** — `FX-NORM` (`NAME, Email ` header; row ` Eve Evans ,  EVE@Example.COM `) → 201; user `eve@example.com`, name `Eve Evans`. Surface API + Store. Confirm TC-3.1.
* **R-3.2 failure** — `FX-H1` (`email` only) → 400 `MISSING_HEADER`(name); `FX-H2` (`email,name,role`) → 400 `UNKNOWN_HEADER`(role); `FX-H3` (`email,name,Email`) → 400 `DUPLICATE_HEADER`(email); `FX-HDRONLY` → 400 `NO_DATA_ROWS`. Store equals `S0`. Surface API. Confirm TC-3.2.
* **R-3.3 failure (all together)** — `FX-H4` (`email;name` / `x@example.com;X`) → 400 with exactly the set {`UNKNOWN_HEADER`("email;name"), `MISSING_HEADER`(email), `MISSING_HEADER`(name)}; no `row_errors`. Order of `file_errors` is unspecified; tests compare as a set. Surface API. Confirm TC-3.3.
* **R-3.4 boundary** — n/a: header-count boundaries are fully covered by the missing/unknown/duplicate groups (0 extra, 1 extra, 1 repeated).

### R-4 Row validation

**Behavior.** Each data record is valid when: it has the same number of fields as the header; after trimming, `email` is
non-empty, ≤ 254 characters and matches `^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$` (one `@`, a dot-separated domain of ≥ 2 non-empty labels,
no whitespace); and after trimming `name` is 1–100 characters (A-6). Email is stored lowercased and trimmed; name is stored
trimmed and otherwise verbatim (a name beginning with `=`, `+`, `-` or `@` is stored as typed).
**Boundaries.** Email length 254 valid / 255 invalid; name length 100 valid / 101 invalid. Fully blank records at the *end* of
the file are ignored; a fully blank record elsewhere is a row error. Row-level validation runs on **every** row so the admin
sees all problems at once.
**Error behavior.** Codes: `WRONG_FIELD_COUNT` (field null), `EMPTY_ROW`, `EMAIL_REQUIRED`, `EMAIL_TOO_LONG`, `EMAIL_INVALID`,
`NAME_REQUIRED`, `NAME_TOO_LONG`; 422; nothing created. `row_errors` are ordered by row, then by field (`email` before `name`).
A row may carry several errors (one per field).
**Consumer outcome.** The admin can fix the file from the report alone.
**Basis.** Request "bulk-create users"; rule set is a default (A-2, A-6). **Change type:** added. **Locators:** §3.3 T-5.
**Evidence limits:** existing model's validation rules unseen (G-6); the email pattern is deliberately pragmatic (it accepts some
addresses RFC 5322 rejects; it rejects quoted-local-part forms). **Pending:** TC-4.x. **Open gap G-6:** reconcile limits and the
email rule with the existing user model so import and single-create agree.

* **R-4.1 positive** — `FX-OK3` includes a quoted name `"Doe, Dan"` → stored name `Doe, Dan`. Valid emails: `a@b.co`. Surface API + Store. Confirm TC-4.1.
* **R-4.2 failure** — `FX-ROWS` (section 9) yields `EMAIL_INVALID` (row 2), `EMAIL_REQUIRED` (row 3), `NAME_REQUIRED` (row 5); `FX-FIELDS` → `WRONG_FIELD_COUNT` rows 1 and 2; `FX-BLANKMID` → `EMPTY_ROW` row 2 only (rows 1 and 3 not flagged). Invalid email examples, each in a one-row file with name `X`: `a@b`, `a@@b.co`, `a b@x.co`, `a@x..co`, `a@.x.co`, `a@x.co.` → `EMAIL_INVALID`; `a@b.co` valid. Surface API. Confirm TC-4.2.
* **R-4.3 boundary** — `FX-E254` (local part 242 `a`s + `@example.com`, total 254) → 201; `FX-E255` (243 `a`s, total 255) → 422 `EMAIL_TOO_LONG` row 1; `FX-N100` (name of 100 `n`) → 201; `FX-N101` (101 `n`) → 422 `NAME_TOO_LONG` row 1. Surface API + Store. Confirm TC-4.3.
* **R-4.4 positive (trailing blanks)** — covered by R-2.3 (`FX-B2048`, whose padding is trailing blank lines) and `FX-BOM` (trailing CRLF). Confirm TC-2.3.

### R-5 Email uniqueness

**Behavior.** An email may be created once. Uniqueness is checked case-insensitively (on the normalised form) against (a) all
existing user records of any status and (b) earlier rows in the same file.
**Boundaries.** The *first* in-file occurrence of an email (among rows whose email is syntactically valid, regardless of other
errors in that row) is the reference; every later occurrence is `DUPLICATE_IN_FILE` with `first_row`. The first occurrence is
additionally flagged `ALREADY_EXISTS` if the email exists in the store. Existing users are never updated (no upsert).
**Error behavior.** 422 `ALREADY_EXISTS` or `DUPLICATE_IN_FILE`; nothing created. A conflict discovered only at commit time
(F-5) is reported as `ALREADY_EXISTS` for the affected row and nothing is created.
**Consumer outcome.** No duplicate account can result from an import, a repeated upload, or two admins importing at once.
**Basis.** Request "bulk-create users" (implied by a user's identity); rule is a default. **Change type:** added. **Preserved:**
existing users untouched. **Locators:** §3.3 T-5/T-7. **Evidence limits:** whether deactivated/soft-deleted users hold the
email is unknown. **Pending:** TC-5.x. **Open gap G-5:** existing uniqueness rules (case rules, deactivated/soft-deleted users,
aliases). **Open gap G-7:** multi-tenant scoping, if any.

* **R-5.1 positive** — A file whose emails are all new and distinct (`FX-OK3`) creates all rows (R-6.1).
* **R-5.2 failure (existing, in-file)** — `FX-ROWS`: row 4 `carol@example.com` → `ALREADY_EXISTS`; row 6 `good@example.com` → `DUPLICATE_IN_FILE` (`first_row` 1); row 7 `GINA@example.com` → `DUPLICATE_IN_FILE` (`first_row` 5, whose own error is `NAME_REQUIRED`). Row 1 is **not** flagged. Surface API. Confirm TC-5.2.
* **R-5.3 failure (concurrent)** — Two admin sessions (`admin`, `admin2`) submit `FX-X` and `FX-Y` released together by a barrier. Both interleavings were walked serially (X then Y, Y then X): exactly one request returns 201 and the other 422 with `ALREADY_EXISTS` on row 1 (`race@example.com`); the Store has 6 users, exactly one `race@example.com`, plus the winner's second user (`r1@example.com` or `r2@example.com`) and not the loser's. The winner is not predictable; assertions are symmetric. Surface API + Store. Confirm TC-5.3. (Real simultaneity is `NOT-REPLAYED` until built; see 9.3.)
* **R-5.4 boundary (replay)** — After `FX-OK3` succeeded (Store has 7 users), submitting the identical file again → 422 with `ALREADY_EXISTS` on rows 1, 2, 3; Store still 7. Surface API + Store. Confirm TC-5.4.

### R-6 Atomic creation

**Behavior.** If and only if every row is valid, all rows are created together as one atomic unit; each becomes one user
(R-8). If anything fails, no user from the file exists afterwards.
**Boundaries.** All-or-nothing applies to validation errors, commit-time conflicts and unexpected faults. Existing users and
unrelated data are unchanged by every outcome. Imports have no partial-success state (A-5).
**Error behavior.** See T-5, T-7, T-9. After a fault the admin may resubmit the same file safely.
**Consumer outcome.** The admin never has to work out which half of a file was applied.
**Basis.** Request "bulk-create users"; atomicity is a default (A-5/G-4). **Change type:** added. **Locators:** §3.3 T-6…T-9.
**Evidence limits:** transaction support of the existing store unknown. **Pending:** TC-6.x.
**Open gap G-4 (user decision):** all-or-nothing vs create-valid-rows-and-report-the-rest. Default is all-or-nothing because it
makes retry trivial and avoids half-onboarded teams. Changing the decision rewrites R-6, R-7, T-5 and the rows of section 9.

* **R-6.1 positive** — `admin`, `FX-OK3` against `S0` → 201, `created_count` 3; Store has 7 users: the original 4 plus `alice@example.com`/`Alice Adams`, `bob@example.com`/`Bob Brown`, `dan@example.com`/`Doe, Dan`, each role `member`; the original 4 are unchanged. Also `FX-R10` (10 rows `u01…u10@example.com`) → 201, 10 created. Surface API + Store. Confirm TC-6.1.
* **R-6.2 failure (nothing created)** — `FX-ROWS` against `S0` → 422; Store equals `S0` (4 users) — in particular valid row 1 `good@example.com` was **not** created. Surface API + Store. Confirm TC-6.2.
* **R-6.3 failure (commit-time conflict)** — see R-5.3; the loser's non-conflicting row is absent. Confirm TC-5.3.
* **R-6.4 recovery** — After a 201 whose response the client never received, resubmitting the file produces the R-5.4 outcome (422 `ALREADY_EXISTS` for every row) and no duplicates; that outcome is how the admin confirms the first attempt committed. Surface API + Store. Confirm TC-5.4.
* **R-6.5 failure (fault injection)** — With the store made to fail on the second of three inserts (test hook), `FX-OK3` → 5xx and Store equals `S0`. Surface API + Store. Confirm TC-6.5. (`NOT-REPLAYED` until a fault-injection seam exists; owner: plan/test-strategy.)

### R-7 Result report

**Behavior.** Every attempt that passes authorization returns a machine-readable and human-readable result: success (count
and created users) or rejection (file errors *or* row errors with row numbers, field and code, and a message the admin can act
on).
**Boundaries.** All row errors for the file are reported (bounded by R-9's row limit, so the report is bounded). Messages and
codes identify rows by number and field and do not echo field values back except `header` text for header errors. The report
is returned to the uploader only and is not stored.
**Error behavior.** The shape is the same for every rejection; `status` is `rejected`. A response never claims success unless
the commit happened.
**Consumer outcome.** The admin can correct and resubmit without guessing.
**Basis.** Request (feedback on an upload is implied by "upload … to bulk-create"). **Change type:** added. **Locators:**
§4 conventions. **Evidence limits:** API conventions unseen (A-9). **Pending:** TC-7.x.

* **R-7.1 positive** — 201 body for `FX-OK3`: `created_count` 3 and `users` listing the three new users with ids, emails and names, and no password or credential field. Surface API. Confirm TC-7.1.
* **R-7.2 failure** — `FX-ROWS` 422 body: `row_errors` exactly (row, field, code[, first_row]) = (2,email,EMAIL_INVALID), (3,email,EMAIL_REQUIRED), (4,email,ALREADY_EXISTS), (5,name,NAME_REQUIRED), (6,email,DUPLICATE_IN_FILE,1), (7,email,DUPLICATE_IN_FILE,5), in that order, each with a non-empty `message`; no `file_errors`; no `users`. Surface API. Confirm TC-7.2.
* **R-7.3 failure (file errors)** — 400 bodies carry `file_errors` and no `row_errors` (R-2.2, R-3.2). Confirm TC-2.2.
* **R-7.4 boundary** — n/a: bounded by R-9; an unbounded report cannot occur.

### R-8 Created users

**Behavior.** Each created user has the normalised email, the trimmed name, the default non-admin role (A-3), and no usable
credential (A-4); the CSV can set nothing else. The feature sends no message.
**Boundaries.** Admin role can never be granted by import (there is no role column, R-3).
**Error behavior.** n/a here beyond R-6 (creation is all-or-nothing).
**Consumer outcome.** Imported people exist as ordinary members and can become active through the product's existing
credential flow.
**Basis.** Request "bulk-create users". **Change type:** added. **Preserved:** every existing user's data and the existing
single-user creation behavior (unobserved; plan to re-check). **Locators:** §1 A-3/A-4. **Evidence limits:** the existing
credential/invite mechanism is unseen. **Pending:** TC-8.x.
**Open gap G-2 (onboarding, user decision):** how imported users get credentials (existing reset link, invite email on import,
or admin-shared). Default: none beyond what already exists; no email sent. **Open gap G-3 (user decision/prerequisite):** the name
of the existing default role, and whether CSV should ever carry a role.

* **R-8.1 positive** — After R-6.1, Store rows for the three new users have role `member`, normalised lowercase emails, and credential state "none/unset" per the existing model; `FX-NORM` row stores `eve@example.com`, `Eve Evans`. Surface Store. Confirm TC-8.1.
* **R-8.2 failure** — `FX-H2` (`role` column with value `admin`) → 400; Store has no new user and no user's role changed. Surface API + Store. Confirm TC-3.2.
* **R-8.3 boundary** — n/a: no input chooses role, status or credentials.

### R-9 Size and row limits

**Behavior.** A file may hold at most `IMPORT_MAX_ROWS` data records and at most `IMPORT_MAX_BYTES` bytes (R-2). Import is
synchronous.
**Boundaries.** Row count excludes the header and ignored trailing blank records. Exactly `IMPORT_MAX_ROWS` rows is accepted;
one more → 400 `TOO_MANY_ROWS`, nothing created, no per-row validation reported.
**Error behavior.** The message states the limit in force.
**Consumer outcome.** The admin knows to split the file.
**Basis.** Request, plus the need for a bounded synchronous operation. **Change type:** added. **Locators:** §3.3 T-4.
**Evidence limits:** no workload data. **Pending:** TC-9.x.
**Open gap G-2 (unresolved bound):** production `IMPORT_MAX_ROWS` and `IMPORT_MAX_BYTES`, and the maximum acceptable
response time, need a user decision informed by the largest expected team import and platform request limits. The behavior at
the bound is specified; only the value is open. Dependent work that is value-independent (parameterised limits) may proceed.

* **R-9.1 positive** — Under `C0` (`IMPORT_MAX_ROWS=10`): `FX-R10` → 201. Confirm TC-6.1.
* **R-9.2 boundary/failure** — `FX-R11` (11 valid rows `u01…u11@example.com`) → 400 `TOO_MANY_ROWS`, Store equals `S0`, no `row_errors`. Surface API + Store. Confirm TC-9.2.
* **R-9.3 failure** — n/a: size-limit failure is R-2.3.

### R-10 Admin upload page

**Behavior.** An admin-only page (A-9) lets the admin choose a CSV, submit it, and read the result.
**Content.** It states the expected format (columns `email` and `name`, comma-separated, UTF-8, one header row, the two limits in
force, atomic behavior in one sentence). The file is chosen with a native file control (keyboard operable) and optionally by
dropping a file on a labelled drop zone; both paths feed the same selected-file state.
**States** (each designed, not default): *empty* (no file chosen; submit disabled; format guidance shown); *ready* (file name and
size shown, submit enabled, "choose a different file" available); *pending* (submit disabled, "Importing…" status, file control
locked; shown only while the request is in flight); *success* (count of users created and a list/table of them, a clear way to
start another import); *file rejected* (the `file_errors` messages, file kept selected); *rows rejected* (a table of row, field,
message for every row error, with a count and the reminder that nothing was created); *not permitted* (401 → prompt to sign in;
403 → "not permitted"); *unconfirmed failure* (network error or 5xx: states that the result could not be confirmed and nothing
may have been created, and that re-submitting is safe because duplicates are rejected, R-6.4).
**Async feedback truthfulness.** Success is displayed only after a 201. Draft state (selected file), request state, and accepted
result are separate; at most one request is in flight (a second submit is ignored while pending); choosing a different file
discards the previous result; a response that arrives after the admin chose a different file or navigated away is not shown as
the result of the new selection.
**Consumer outcome.** An admin completes an import, or fixes the file, without leaving the page or reading documentation.
**Basis.** Request "Let admins upload…" (the upload must be done by admins through a UI). **Change type:** added. **Locators:**
§3.2 F-6; NFR interface. **Evidence limits:** no existing UI shell or design tokens observed; existence of a UI (vs API only)
is assumed from "admins … upload" (A-9, G-9). **Pending:** TC-10.x.
**Open gap G-9 (prerequisite):** the existing admin UI shell/navigation and design tokens; if the product has an identity it
takes precedence over the visual starting point in NFR interface.

* **R-10.1 positive** — As `admin`, open the page (empty state visible, submit disabled); choose `FX-OK3` (ready state shows name and size, submit enabled); submit; while the response is held by the test (controlled response completion) the pending state shows and a second activation of submit sends no second request; after release the success state shows "3 users created" and the 3 users; Store has 7 users. Surface UI + Store. Confirm TC-10.1.
* **R-10.2 failure** — Submit `FX-ROWS`: the rows-rejected state lists the six errors from R-7.2 in order, says nothing was created, keeps the file selected; Store equals `S0`. Submit `FX-H2`: the file-rejected state shows the unknown-header message. Surface UI + Store. Confirm TC-10.2.
* **R-10.3 failure (network)** — With the request aborted by the test harness, the unconfirmed-failure state shows and not the success state. With a 403 forced for the session (R-1.3 state), the not-permitted state shows. Surface UI. Confirm TC-10.3.
* **R-10.4 boundary (state hygiene)** — After a rejection, choose another file: the previous result panel is cleared and the new file's name is shown; a held response from the *earlier* submission completed afterwards does not replace the panel. Surface UI. Confirm TC-10.4.
* **R-10.5 keyboard/accessibility** — The whole flow (open page, choose file, submit, read result, start over) is completable by keyboard alone; after submit, focus moves to the result region (announced via a live region); errors are announced, not colour-only. Surface UI. Confirm TC-10.5 (semantic queries plus a manual screen-reader spot check recorded in test evidence).

## 5. Non-functional requirements

Operating condition for all: one admin at a time using the page interactively, files up to the R-9 limits, user store shared
with the rest of the product. No SLA, load or availability figure was requested; none is invented.

| Attribute | Requirement (observable) | Verification | Status |
| --- | --- | --- | --- |
| **Security — authorization** | Authorization is enforced on the server for every import request (R-1); hiding the link is not a control. Session/CSRF protection for the state-changing `POST` uses whatever the existing authentication mechanism requires; a request lacking it is refused with no effect. | TC-1.2, TC-1.3; CSRF-less request test once the mechanism is known | Gap G-1 (mechanism unknown) |
| **Security — input handling** | The file is data only: no cell is evaluated or executed; names that begin with `=`, `+`, `-`, `@` are stored verbatim and any future CSV export must neutralise them (out of scope here, noted for that export). File content is never interpolated into queries; row messages never reflect raw field values into HTML unescaped. | TC-4.1 variant with name `=1+1`; UI test that the report renders a name such as `<b>x</b>` as text | Proposed |
| **Privacy / data handling** | Emails and names are personal data. They are shown only to the uploading admin in the response; stored only in the user store; **not** written to logs or the audit entry; the uploaded file is not persisted (no temp file survives the request); the audit entry holds admin id, timestamp, outcome, counts and error codes only (A-8). Removal of an imported user is by the product's existing user deletion. | After `FX-ROWS` and `FX-OK3`, search log output and the upload temp area for `good@example.com`, `dan@example.com`, `Doe, Dan`: no matches; audit entries present with counts | Retention period of audit entries: gap G-8 (follow existing log retention; not invented) |
| **Integrity** | R-6: no partial import under validation error, conflict or fault; the store enforces email uniqueness as a backstop independent of the application check. | TC-6.2, TC-5.3, TC-6.5 | Proposed |
| **Performance / capacity** | The behavior at the bound is fixed (R-2.3, R-9.2). The numeric bounds `IMPORT_MAX_ROWS`, `IMPORT_MAX_BYTES` and a maximum response time for a file at the limit are **unresolved**; once chosen, a timing check at the limit under the target platform's request timeout is required. | Pending value | **Unresolved — G-2**; blocks only the value-dependent check, not parameterised work |
| **Reliability / availability** | No availability target is requested. Justified exclusion of a numeric target: interactive admin function; safe retry by R-6.4 covers a failed attempt. Crash/fault behavior is required (T-9, R-6.5). | TC-6.5 | Target excluded with reason; revisit if the user states one |
| **Compatibility** | Accepts CSV exported by common spreadsheets as "CSV UTF-8" (BOM or not, LF or CRLF). Legacy-encoding exports fail with `NOT_UTF8` and a message naming the fix. Supported browsers: the product's existing matrix. | TC-2.1, TC-2.2; browser matrix pending | Browser matrix: gap G-9 |
| **Operability / observability** | Each attempt after authorization writes one audit entry (A-8) so an admin action can be traced; a failed write of the entry does not change the import outcome and is itself logged. | TC-NFR-log (Log surface) | Proposed; depends on A-8 |
| **Testability** | Limits are configuration, so tests can run under `C0`; the user store can be seeded; the response of the page's request can be held and released by the test. | Test strategy | Proposed |
| **Interface quality** (R-10 deliverable has a UI) | A deliberately designed interface, not unstyled scaffolding, with these observable criteria: (1) a consistent visual system: spacing scale, type scale, and a palette with a light and a dark theme (light is the default for a new web UI; dark selected by the system preference and user toggle); (2) designed empty, ready, pending, success, error and not-permitted states (R-10); (3) works at 360 px and 1280 px widths with no horizontal page overflow — the error table scrolls inside its own container or reflows; (4) visible keyboard focus on every control and WCAG 2.2 AA text/non-text contrast in both themes; (5) motion only to explain a state change (e.g. result panel entering), honouring `prefers-reduced-motion`; (6) one icon set. **Visual reference/starting appearance:** no existing product identity was available, so unspecified choices follow `platforms/ui.md#light-expressive-starting-point` (light Gemini look and feel using Material 3 Expressive principles: luminous light canvas, tonal rounded surfaces, humanist/geometric sans-serif from local fonts, restrained saturated accent, the upload/result area as the strongest focal point, supporting guidance quieter). Explicit visual constraints, an established product identity or platform conventions (G-9) take precedence. The plan records concrete tokens in an AD. | Rendered screenshots at both widths in both themes for each state; automated contrast and focus checks; reduced-motion emulation | Proposed; concrete treatment is the plan's |

## 6. State and data assessment

| Carrier | Owner / location | Affected how | Before → after invariant | Authority and check | Recovery | Unknowns |
| --- | --- | --- | --- | --- | --- | --- |
| User records (target identity: a new user keyed by normalised email) | User store (existing) | **Changed**: insert only | Before: no record with that email. After: exactly N new records (N = file rows) or zero; all other records byte-identical. Email unique case-insensitively across all records | Admin role (R-1); TC-6.1, 6.2, 5.3, 6.5 | Roll back the unit (T-7/T-9); replay is safe (R-6.4). No built-in undo of a committed import (non-goal) | Soft-delete/deactivated semantics (G-5); tenant scoping (G-7); credential state field (G-2) |
| Audit entry | Existing log/audit sink | Changed: one append per attempt | Contains no row content | TC-NFR-log | Sink failure is logged and does not alter the outcome | Sink existence/retention (G-8) |
| Uploaded file bytes | Request memory (and any framework temp spool) | Observed only | Gone when the request ends | Temp-area check in NFR privacy | n/a | Framework spooling behavior unknown until stack chosen |
| Admin sessions / roles | Existing | **Observed** (read per request), not changed | n/a | R-1.3 | n/a | G-1 |
| Browser page state | Client memory | Transient | Selected file, request state, result held separately | TC-10.x | Reload resets everything | none |
| Config `IMPORT_MAX_ROWS`, `IMPORT_MAX_BYTES` | Application configuration | Read | Fixed during a request | TC-2.3, TC-9.2 | n/a | Production values (G-2) |

Transition correctness (above) is separate from workload quality (NFR performance). Contention: two imports sharing an email
are the hot-record case (R-5.3); independent imports share no record and need no coordination beyond the uniqueness backstop.
No schema migration is *required* by the behavior; if the existing store lacks a case-insensitive unique constraint on email,
adding one is a plan decision (AD-3 proposed in `architecture.md`) and, on a populated store, is a migration whose existing
duplicates (case variants) would have to be surveyed first — recorded as an unknown, not a decision.

## 7. Service boundaries (Service discovery guidance, verification)

One service plus its store; no external dependency is introduced.

* **Current authority:** the admin role is read from the user store at the start of each request (R-1.3). Freshness vs
  revocation: no caching of the role by this feature; a revoked admin is refused on the next request; an in-flight import
  finishes. If the existing auth layer caches roles, its staleness bound becomes the effective revocation bound (G-1).
* **Incremental state:** the import inserts only; it never reads-modify-writes existing records, so unrelated remote changes are
  preserved (R-6 boundaries).
* **Async completion and recovery:** none: synchronous request/response, the response is the completion signal (AD-2). A lost
  response is recovered by replay (R-6.4).
* **Owned event coverage:** the audit entry is the only event this feature owns (NFR operability); delivery to the sink is not
  the outcome of the import.
* **Cache, worker, notification, webhook concerns:** inapplicable (no cache, worker, queue or outbound call; emails are out of
  scope, G-2).

## 8. State and information lifecycle (Interaction design guide)

| State | Owner/location | Who may read | Simultaneous changes | Ends and removal | Quotas |
| --- | --- | --- | --- | --- | --- |
| File bytes | Server request memory | The handling request only | One request = one file; independent requests do not share | At request end; nothing persisted | `IMPORT_MAX_BYTES` and any proxy/body limit (G-2) |
| Result report | Response body and client memory | Only the uploader (it contains row numbers and, on success, emails/names the admin could already list) | n/a | Discarded when the admin picks another file or leaves the page; never stored server-side | bounded by `IMPORT_MAX_ROWS` |
| New user records | User store | Whoever may read users today (unchanged by this feature) | Uniqueness backstop decides (R-5.3) | Existing user deletion | Existing |
| Audit entry | Log sink | Operators with existing log access | Append-only | Existing log retention (G-8) | Existing |
| Page state (file, request, result) | Browser memory | The user of that tab | Single in-flight request; stale responses ignored (R-10.4) | Reload/navigation | none |

Personal data (emails, names): shown to the uploading admin on success; stored only in the user store; not logged; retained as
long as the user record; removed with the user record. No identity, sharing or persistence beyond the above is added.

## 9. Replay fixtures, cases and evidence

### 9.1 Fixtures

**Seed `S0`** (user store before every case unless stated): `id 1 admin@example.com "Ada Admin" admin`;
`id 2 member@example.com "Mia Member" member`; `id 3 carol@example.com "Carol Existing" member`;
`id 4 admin2@example.com "Bo Admin" admin`. Sessions: `admin` = user 1, `admin2` = user 4, `member` = user 2, `anon` = none.
**Config `C0`** (test-only values, not production claims): `IMPORT_MAX_ROWS=10`, `IMPORT_MAX_BYTES=2048`. Start reachability:
`S0` and the sessions are seeded by test setup directly in the store; no product function is needed to reach them (A-1).

**Files** (`\n` is LF; spaces are literal):

* `FX-OK3`: `email,name` / `alice@example.com,Alice Adams` / `bob@example.com,Bob Brown` / `dan@example.com,"Doe, Dan"` (LF, trailing LF)
* `FX-NORM`: `NAME, Email ` / ` Eve Evans ,  EVE@Example.COM ` (trailing LF)
* `FX-BOM`: bytes `EF BB BF` + `email,name\r\nfred@example.com,Fred Ford\r\n`
* `FX-ROWS`: `email,name` / `good@example.com,Good Person` / `not-an-email,Bad Email` / `,No Email` / `carol@example.com,Carol Dup` / `gina@example.com,` / `good@example.com,Good Again` / `GINA@example.com,Gina G`
* `FX-FIELDS`: `email,name` / `hal@example.com` / `ivy@example.com,Ivy,extra`
* `FX-BLANKMID`: `email,name` / `j@example.com,J` / *(empty line)* / `k@example.com,K`
* `FX-H1`: `email` / `x@example.com`; `FX-H2`: `email,name,role` / `x@example.com,X,admin`; `FX-H3`: `email,name,Email` / `x@example.com,X,y@example.com`; `FX-H4`: `email;name` / `x@example.com;X`
* `FX-EMPTY`: 0 bytes; `FX-WS`: `\n\n  \n`; `FX-HDRONLY`: `email,name\n`; `FX-NOTUTF8`: `email,name\n` + bytes `FF FE` + `@example.com,X\n`; `FX-UNTERM`: `email,name\n"a@example.com,Al\n`
* `FX-R10`: header + 10 rows `uNN@example.com,User NN` (NN = 01…10); `FX-R11`: the same with an 11th row `u11@example.com,User 11`
* `FX-B2048`: `email,name\npad@example.com,Pad Person\n` followed by `\n` characters until the file is exactly 2048 bytes; `FX-B2049`: that plus one more `\n`
* `FX-N100` / `FX-N101`: `email,name\nn1@example.com,` + 100 / 101 letters `n`; `FX-E254` / `FX-E255`: `email,name\n` + (242 / 243 letters `a`) + `@example.com,E`
* `FX-V1`: `email,name\nv1@example.com,V One`; `FX-V2`: `email,name\nv2@example.com,V Two`
* `FX-X`: `email,name\nrace@example.com,Racer One\nr1@example.com,R One`; `FX-Y`: `email,name\nrace@example.com,Racer Two\nr2@example.com,R Two`

### 9.2 Case index

| Case | Requirement | Steps and expected (recomputed) |
| --- | --- | --- |
| TC-1.1 | R-1.1 | `admin` POST `FX-OK3` → 201 |
| TC-1.2 | R-1.2 | `anon` → 401; `member` → 403; Store = `S0` |
| TC-1.3 | R-1.3 | `admin2` `FX-V1` → 201 (5 users); set `admin2.role=member`; `admin2` `FX-V2` → 403; 5 users, no `v2@` |
| TC-1.4 | R-1.4 | UI as `admin`/`member` |
| TC-2.1 | R-2.1 | `FX-BOM` → 201, `fred@example.com` / `Fred Ford` |
| TC-2.2 | R-2.2, R-7.3 | NO_FILE, INVALID_UPLOAD, EMPTY_FILE (`FX-EMPTY`, `FX-WS`), NOT_UTF8, MALFORMED_CSV, all 400, Store = `S0` |
| TC-2.3 | R-2.3, R-4.4 | `FX-B2048` → 201 (1 user: `pad@example.com`); `FX-B2049` → 413 |
| TC-3.1 | R-3.1 | `FX-NORM` → 201, `eve@example.com` / `Eve Evans` |
| TC-3.2 | R-3.2, R-8.2 | H1 → MISSING_HEADER(name); H2 → UNKNOWN_HEADER(role); H3 → DUPLICATE_HEADER(email); `FX-HDRONLY` → NO_DATA_ROWS; 400, Store = `S0` |
| TC-3.3 | R-3.3, R-2.4 | `FX-H4` → set {UNKNOWN_HEADER("email;name"), MISSING_HEADER(email), MISSING_HEADER(name)}, no `row_errors` |
| TC-4.1 | R-4.1 | `FX-OK3` name `Doe, Dan`; email `a@b.co` valid; name `=1+1` stored verbatim |
| TC-4.2 | R-4.2 | `FX-ROWS` rows 2,3,5; `FX-FIELDS` rows 1,2 WRONG_FIELD_COUNT; `FX-BLANKMID` row 2 EMPTY_ROW only; six invalid emails → EMAIL_INVALID |
| TC-4.3 | R-4.3 | E254 → 201; E255 → EMAIL_TOO_LONG; N100 → 201; N101 → NAME_TOO_LONG |
| TC-5.2 | R-5.2, R-6.2, R-7.2 | `FX-ROWS` → 422 with exactly the six errors of R-7.2; Store = `S0` (4 users) |
| TC-5.3 | R-5.3, R-6.3 | `FX-X` ‖ `FX-Y` → one 201, one 422 ALREADY_EXISTS row 1; 6 users |
| TC-5.4 | R-5.4, R-6.4 | `FX-OK3` twice: 201 then 422 ALREADY_EXISTS rows 1,2,3; 7 users |
| TC-6.1 | R-6.1, R-9.1, R-7.1, R-8.1 | `FX-OK3` → 201, 7 users, role `member`; `FX-R10` → 201, 10 created |
| TC-6.5 | R-6.5 | Store fails on 2nd of 3 inserts → 5xx; Store = `S0` |
| TC-9.2 | R-9.2 | `FX-R11` → 400 TOO_MANY_ROWS; Store = `S0` |
| TC-10.1 … 10.5 | R-10.1 … R-10.5 | Browser flows as written in R-10 |
| TC-NFR-log | NFR privacy/operability | Log/temp-area search after TC-5.2 and TC-6.1 |

### 9.3 Walk and evidence for the ordered cases

Method: each expected result above was walked by hand against the rules of R-1…R-9 in phase order (T-1…T-9), checking that
each action is permitted by the stated spec rule (e.g. the `admin2` import in TC-1.3 step 1 is permitted by R-1 because `S0`
gives `admin2` the admin role; step 3 is refused because the role is read per request). A throwaway reference model of the
same rules was written at
`/private/tmp/claude-501/-Users-dadleet-e2e-runs-spec-elaboration-20261120-round-7-csv-user-import--M-shiploop-spec-members--sonnet-high-2ec480/4c997001-6755-43ca-959f-d96cdbd3513c/scratchpad/oracle.py`
to recompute them mechanically, but **its execution was not approved in this run**, so
`NOT-REPLAYED: oracle execution not permitted; results are hand-computed.` These are plans, not observed results.

Hand-recomputed highlights: `FX-ROWS` has 7 data rows; row 5's email `gina@example.com` is syntactically valid and is therefore the
reference for row 7 `GINA@example.com`; row 1 is the reference for row 6; row 1 itself carries no error, so the six errors of
R-7.2 are the complete set. `FX-B2048` is 2048 bytes because the padding is whole blank trailing records, ignored by R-4; one
more byte exceeds `IMPORT_MAX_BYTES`. `FX-E254` is 242 + 12 = 254 characters. Under TC-5.3 both serial interleavings give the
symmetric result stated; real concurrency is `NOT-REPLAYED` until built (owner: test-strategy, due phase: implementation tests).
TC-6.5 and the UI controlled-response cases (R-10) need seams that do not exist yet (owner: plan, due phase: test-strategy).
The documented-command check (duty 10) does not apply: the spec documents no command. Duty 11 (`backchain-check`) is left out
as instructed.

## 10. Traceability

| Request outcome | Requirement(s) | Acceptance lines |
| --- | --- | --- |
| O-1 "admins" (and only admins) may do this | R-1, R-10 | R-1.1–R-1.4, R-10.1 |
| O-2 "upload a CSV" | R-2, R-3, R-9, R-10 | R-2.1–R-2.4, R-3.1–R-3.3, R-9.1–R-9.2, R-10.1–R-10.5 |
| O-3 "bulk-create users" | R-4, R-5, R-6, R-8 | R-4.1–R-4.4, R-5.1–R-5.4, R-6.1–R-6.5, R-8.1–R-8.2 |
| O-4 (implied) the admin learns the outcome | R-7, R-10 | R-7.1–R-7.3, R-10.1–R-10.3 |

Every requirement has an acceptance line; every modelled behavior traces to O-1…O-4 (no expansion beyond the request except the
defaults listed in A-1…A-9, each visible as a gap).

## 11. Open gaps (index)

| Gap | Under | Kind | Decision or prerequisite needed | Work held unready |
| --- | --- | --- | --- | --- |
| G-1 | R-1 | Prerequisite | Existing admin role/permission and auth mechanism (incl. CSRF) | R-1 implementation and its NFR check only |
| G-2 | R-2, R-8, R-9, NFR | User decision | (a) production `IMPORT_MAX_ROWS`, `IMPORT_MAX_BYTES`, response-time bound, platform body limit; (b) how imported users get credentials / any invite email | Value-dependent limit check; any invitation behavior (out of scope until decided) |
| G-3 | R-3, R-8 | User decision / prerequisite | Default role name; whether CSV may ever carry a role | R-8 role assertion |
| G-4 | R-6 | User decision | All-or-nothing (default) vs partial success | Nothing now; a change rewrites R-6/R-7 |
| G-5 | R-5 | Prerequisite | Existing uniqueness/case rules, deactivated and soft-deleted users | R-5 existing-user check semantics |
| G-6 | R-4 | Prerequisite | Existing name/email limits and validation | R-4 boundaries |
| G-7 | R-5 | User decision | Multi-tenant scoping, if any | R-5 |
| G-8 | NFR | Prerequisite / decision | Audit/log sink and retention | Operability check |
| G-9 | R-2, R-10 | Prerequisite | Existing UI shell, design tokens, browser matrix, route/API conventions | R-10 visual treatment only |

No material requirement conflict was found. Independent work (parsing and validation rules, atomic commit, response shape) can
proceed on the stated defaults.

## 12. Retired

None. No prior requirements existed.

## Submission

**summary.** Specified admin CSV bulk-create-users as R-1…R-10: admin-only access (R-1), upload intake (R-2), header contract
with `email` and `name` only (R-3), row validation (R-4), case-insensitive uniqueness against the store and within the file
(R-5), all-or-nothing atomic creation (R-6), a complete result report (R-7), created users with the default role and no
credential (R-8), size and row limits (R-9), and an admin upload page (R-10); non-functional criteria for security, privacy,
integrity, compatibility, operability and interface quality are in section 5. There was no repository, research, earlier spec
or baseline, so everything about the existing product is an assumption (A-1…A-9), each with an open gap (G-1…G-9). Open
decisions for a person: all-or-nothing vs partial success (G-4, default all-or-nothing); production size/row limits and a
response-time bound (G-2, unresolved, not invented, behavior at the bound is specified); how imported users get credentials
and whether any email is sent (G-2, default none); default role and role-in-CSV (G-3, default `member`, no role column);
existing uniqueness/tenant rules (G-5, G-7). No material requirement conflict. Not verified: all replay results are
hand-computed (`NOT-REPLAYED`: the reference model's execution was not approved); concurrency, fault injection and UI
controlled-response cases need seams that do not exist yet. Duty 11 (`backchain-check`) omitted as instructed; no command is
documented.

**primary.** R-1, R-2, R-6, R-8, R-10. (R-3, R-4, R-5, R-7 and R-9 are the rules and feedback that make those outcomes work.)

**evidence_refs.** `spec.md` (this file: sections 3, 4 R-1…R-10, 5, 6, 7, 8, 9, 10, 11); `architecture.md` (AD-1…AD-4);
request text 2026-11-21; `GUIDES/behavioral-requirements.md#behavior-model`, `#traceability-and-review`,
`GUIDES/requirements-definition.md`, `GUIDES/platforms/ui.md#light-expressive-starting-point`; scratch reference model
`…/scratchpad/oracle.py` (written, **not executed**).
