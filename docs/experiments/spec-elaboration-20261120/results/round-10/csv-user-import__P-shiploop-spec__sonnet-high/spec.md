# User administration: requirements

Living specification of what the product's user administration must do. Structure and technology choices are in
`architecture.md` (AD-<n>). Product decisions made inside this spec are PD-<n>; open prerequisites are OG-<n>.

**Request recorded here (2026-11-21):** "Let admins upload a CSV to bulk-create users."

## Contents

1. Scope, sources and baseline
2. Product decisions (PD) and open gaps (OG)
3. Fixtures used by the acceptance lines
4. Requirements R-1 … R-12
5. Non-functional requirements
6. Behavior model (flows, state, transitions)
7. State and data assessment; lifecycle of information; service boundary
8. Traceability
9. Replay check and evidence limits
10. Retired
11. Submission

---

## 1. Scope, sources and baseline

**In scope.** One new capability: an authenticated administrator uploads one CSV file that describes new users; the
product validates the whole file and, when every row is valid, creates all the users; otherwise it creates none and tells
the administrator exactly which rows to fix. The administrator can do this through an import page and through the
import operation that page uses (AD-2).

**Out of scope (non-goals).** Updating or deleting existing users from a CSV; importing only the valid rows of a
file with errors; a preview/dry-run step; undoing an import; assigning roles, passwords or any attribute other than
`email` and `name`; sending email or invitations; asynchronous or scheduled imports; export; an import-history screen;
a downloadable error report or CSV template; a format other than comma-separated UTF-8.

**Sources and their status.**

| Source | Status | What it supports |
|---|---|---|
| The request above, 2026-11-21 | accepted, the only user instruction | the capability, the actor (admins), the input format (CSV), the effect (bulk-create users) |
| `GUIDES/behavioral-requirements.md#behavior-model`, `#traceability-and-review`, `#actors-channels-and-state-ownership` | method | structure of R, F, T, cases |
| `GUIDES/requirements-definition.md` | method | NFR assessment, state and data assessment, baseline reconciliation |
| `GUIDES/service-discovery.md#verification` | method | service-boundary contracts (section 7) |
| `GUIDES/platforms/ui.md#light-expressive-starting-point` | method | UI starting appearance (NFR-1) |
| Repository, discovery result, research result, earlier spec, selected baseline | **none exist** | nothing |

**Current-system baseline.** None was available, so nothing about today's product is observed. Unknown to this spec:
the stack, the user model and its required fields, how "admin" is decided, whether a single-user create exists, the
email-uniqueness rule it applies, the audit mechanism, the product's API conventions, its admin UI and visual identity,
the supported browsers and the host's request-size and request-time limits. This is a first spec for the product, so
every R-<n> below is **added**; nothing is preserved or changed, and nothing is retired. Each decision that depends on an
unknown is a recorded default (PD) or an open gap (OG); the plan reopens them against the repository at discovery.

## 2. Product decisions and open gaps

Product decisions are defaults chosen for an unattended run because the request leaves them open. They are design
decisions with rationale, not user requirements; a later run does not treat them as binding on the user's behalf.
`Confirm` marks the ones whose reversal would change behaviour a user can see.

| ID | Decision (default) | Rationale | Confirm |
|---|---|---|---|
| PD-1 | **All-or-nothing:** if any row or the file is invalid, no user is created. | An admin can fix and re-upload the whole file with no partial state to reconcile; a re-upload after success is rejected row by row (R-5), so a retry cannot double-create. Row-by-row partial import would leave an undefined "which rows made it" state. | yes |
| PD-2 | **Strict header:** exactly the columns `email` and `name`, in any order, matched case-insensitively after trimming; any other column is an error. | An unknown column is more likely a typo (`emial`) or an attribute the admin expects to be applied (`role`) than noise; silently ignoring it would create users that are not what the admin intended. | yes |
| PD-3 | A row whose email already belongs to a user is an **error**, not an update and not a skip. | The request is "create"; updating or skipping would change existing records or hide the conflict. | yes |
| PD-4 | **Email normalisation:** trimmed, then lowercased, for comparison and for storage. If the product's existing user creation normalises differently, the existing rule wins (OG-1). | Case-variant duplicates (`ADA@…`, `ada@…`) must not become two users. | no |
| PD-5 | **Field rules:** email 1–254 characters after trim and of the form `local@domain.tld` (one `@`, no whitespace, non-empty local part, a dot inside the domain with characters on both sides); name 1–100 characters after trim; no ASCII control characters (U+0000–U+001F, U+007F) in either. | Smallest rules that keep obviously broken data out. The numbers are chosen defaults, not sourced from a platform document; plan checks them against the user store's column limits and the single-user create rules (OG-1) and the existing rule wins. | no |
| PD-6 | **A blank record is ignored:** a record whose every field is empty after trim (an empty line, `,` or `   ,  `) is not a data row and does not count toward row numbers. | Spreadsheet exports append empty rows. | no |
| PD-7 | **Error report cap:** at most 100 row errors are returned; the total is always returned. | Bounds the response for a file that is wrong everywhere. 100 is a chosen default. | no |
| PD-8 | The import sets **no credential and sends no message** (OG-4). | Not asked for; the safe default for a mass-creation action. | yes |
| PD-9 | The audit record holds **no file name and no cell contents**. | File names and rows are personal data; counts and the actor suffice (R-10, R-11). | no |
| PD-10 | "Admin" means whatever the product already treats as an administrator (OG-1); the import adds no role. | The request names admins, not a new permission. | no |
| PD-11 | `row` is the 1-based position among non-blank data records (first data record = 1); `line` is the 1-based physical line in the file on which that record starts (header = line 1). | A quoted field may span lines, so a row number alone does not locate the problem in a text editor. | no |
| PD-12 | The upload is read as comma-separated UTF-8 (an optional BOM is accepted and removed); CRLF and LF line endings are both accepted; a quoted field may contain commas, doubled quotes and line breaks as in RFC 4180. | The common export of spreadsheet tools. A semicolon-separated file therefore fails the header check (R-2) with a clear message. | no |

**Open gaps** (a missing prerequisite or user decision; each names the R it bounds and the default work proceeds on).

| ID | Gap | Bounds | Default applied meanwhile | Smallest confirming step |
|---|---|---|---|---|
| OG-1 | The product's user model, admin test, email-uniqueness/normalisation rule, existing user-creation validation and API conventions are unknown. | R-1, R-4, R-5, R-6 | `email` and `name` only; PD-4, PD-5, PD-10 as written | Discovery reads the user model and any single-user create path; where it requires more fields or applies different rules, the existing rule wins and this spec is corrected by the revision route before R-4/R-6 work is accepted. |
| OG-2 | **The numeric file limits (maximum bytes, maximum data rows) are unresolved.** No figure is invented. | R-3, NFR-2 | The limits are configuration values; tests set small ones. Release is **not ready** until a person sets production values at or under the host's hard request-body and request-time limits. | A person decides the values; discovery records the host limits. |
| OG-3 | Whether the product has a web admin area for the import page, and its visual identity. | R-12, NFR-1 | A new page in a web admin area, NFR-1 starting appearance | Discovery. If there is no web UI, R-12 and NFR-1 are void and R-1…R-11 stand on the operation alone. |
| OG-4 | What a newly created user can do next: how they obtain access (credential, invitation, single sign-on) and whether any message must go out. | R-7 | PD-8: nothing set, nothing sent | A person decides; if access must be issued, a new R-<n> is added. |
| OG-5 | The product's audit mechanism, who may read audit records, and their retention period. | R-10 | AD-5 fallback table; retention is the same as the product's other audit records, none invented | Discovery. |
| OG-6 | The route of the product's user list, used by the success message's link. | R-12 | The link target is the product's existing user list page | Discovery. |

Only the work bounded by an OG waits on it; independent requirements (for example R-2, R-8, R-9) proceed.

## 3. Fixtures

All values are exact. `\n` is a line feed, `\r\n` a carriage return plus line feed. "Store S0" is the starting user store.

**Store S0** (set up directly in the user store by the test, not through the product):

| email | name | role |
|---|---|---|
| admin@example.test | Admin User | admin |
| member@example.test | Member User | member (non-admin) |
| existing@example.test | Existing User | member |

Sessions: `A` = signed in as admin@example.test; `M` = signed in as member@example.test; `N` = no session.
Test limits where a case names them: `MAX_ROWS`, `MAX_BYTES` (OG-2).

**CSV fixtures.**

`ok-3` (107 bytes):
```
email,name\n
ada@example.test,Ada Lovelace\n
grace@example.test,Grace Hopper\n
linus@example.test,Linus Torvalds\n
```
`two-rows` (73 bytes): the first three lines of `ok-3`.

`bad-rows`:
```
email,name\n
ada@example.test,Ada Lovelace\n         (line 2, row 1, valid)
not-an-email,Bad Email\n                 (line 3, row 2)
,No Email\n                              (line 4, row 3)
grace@example.test,\n                    (line 5, row 4)
ADA@example.test,Ada Again\n             (line 6, row 5)
existing@example.test,Existing Again\n   (line 7, row 6)
```
`bad-header`: `emial,name\nada@example.test,Ada\n` · `role-col`: `email,name,role\nada@example.test,Ada,admin\n` ·
`header-only`: `email,name\n` · `empty`: zero bytes · `malformed`: `email,name\n"ada@example.test,Ada\n` (quote opened on line 2, never closed) ·
`bad-encoding`: `email,name\nada@example.test,Ada ` followed by the single byte `0xFF` then `\n` ·
`colcount`: `email,name\nada@example.test\ngrace@example.test,Grace,extra\n` ·
`bom-crlf-quoted`: bytes `EF BB BF` then `name,email\r\n"Hopper, Grace",grace@example.test\r\n` ·
`blank-records`: `email,name\n\nada@example.test,Ada\n,\n   ,  \n` (an empty line, one valid row, then two all-empty records) ·
`trim-case`: `email,name\n  Ada@Example.test  ,  Ada Lovelace  \n` ·
`ctrl-name`: `email,name\nada@example.test,"Ada\nLovelace"\n` (a line break inside the quoted name) ·
`name-100`: one row, name = `N` repeated 100 times · `name-101`: same with 101 · `email-254`: one row, email = `a` repeated 241 times + `@example.test` (254 characters), name `Long Email` · `email-255`: `a` repeated 242 times + `@example.test` ·
`bad-101`: header, then 101 rows `bad1,Name1` … `bad101,Name101` (each an `invalid_email`) · `bad-100`: the first 100 of those rows ·
`conc-A`: `email,name\nx@example.test,X\n` · `conc-B`: `email,name\nx@example.test,X2\ny@example.test,Y\n`.

## 4. Requirements

Notation. Each acceptance line (AL) states the case, then **Surface** (where it is observed) and **Confirm** (how). Surfaces:
**S1** the import operation (AD-2); **S2** the import page in a browser; **S3** the user store read back after the call (through
the product's user read path or a direct test read); **S4** the audit record read back; **S5** the captured application log output.
A line is `n/a: <reason>` where it would only repeat another line. Every R below is **added** by the request of 2026-11-21 and
nothing is preserved or changed (no earlier spec). Evidence limit common to all: no repository or earlier result was available
(section 1). Pending common to all: implementation and every check are pending; nothing is verified.

### R-1 Only administrators can import

- **Basis:** request 2026-11-21, "Let admins upload…"; PD-10; OG-1.
- **Behaviour:** the import operation and the import page are available to an authenticated administrator and to no one else.
  Authority is evaluated from the product's current role data on every request, not remembered from sign-in or page load.
- **Boundaries:** a state-changing request that lacks the product's cross-site request protection credential is refused like any other
  state-changing admin request of the product (mechanism unknown, OG-1).
- **Error behaviour:** `unauthenticated` (no session) and `forbidden` (signed in, not an admin) create nothing, read no file content,
  and reveal nothing about the file.
- **Consumer outcome:** an admin proceeds; others see a refusal and the user store is unchanged.
- **Locators:** `GUIDES/service-discovery.md#cache-and-authorization` (authority freshness). **Pending:** all checks.
- **AL-1.1 positive:** store S0, session A, upload `ok-3` → outcome `created`. S1; **Confirm** integration test through S1, then S3 shows 3 new users.
- **AL-1.2 failure:** S0, session N, upload `ok-3` → `unauthenticated` (401). S1, S3 shows S0 unchanged (3 users). **Confirm** integration test.
- **AL-1.3 failure:** S0, session M, upload `ok-3` → `forbidden` (403); the response contains no row or error detail; S3 shows S0 unchanged. **Confirm** integration test.
- **AL-1.4 boundary:** S0, session A established, then the test demotes admin@example.test to `member` directly in the store, then the page's
  submit sends `ok-3` on the already-open session → `forbidden`; S3 shows S0 unchanged. S1 and S2. **Confirm** integration test (S1) and a browser test that opens the page as admin, demotes, then submits (S2). Setup uses a test fixture, not a product feature.
- **AL-1.5 failure:** S0, session A cookie present but the request omits the product's CSRF credential → refused, S3 unchanged. **Confirm** integration test; `n/a` and recorded if discovery shows the product authenticates by a bearer header only (not sent automatically by a browser).
- **AL-1.6 consumer:** the import page, opened by session M, shows no import control and a "not available" message instead of the form; opened by N it redirects to the product's sign-in. S2. **Confirm** browser test. (Hiding is a convenience; AL-1.3 is the enforcement.)

### R-2 The file is accepted, decoded and parsed, or rejected as a whole

- **Basis:** request, "upload a CSV"; PD-2, PD-6, PD-11, PD-12.
- **Behaviour:** the uploaded part named `file` is decoded as UTF-8 (a leading BOM removed), parsed as comma-separated records, and its header
  checked. File-level checks run in this order and the first failing group stops processing: (1) `missing_file`; (2) size (R-3);
  (3) `empty_file` (zero bytes after BOM removal); (4) `invalid_encoding`; (5) `malformed_csv` (an unterminated quote; carries `line` of
  the opening quote); (6) header: `missing_column` (`email` or `name` absent), `unknown_column`, `duplicate_column`: **all header
  problems are reported together**; (7) `no_rows` (no non-blank data record); (8) row count (R-3).
- **Boundaries:** header matching ignores case and surrounding spaces and any column order; blank records are skipped (PD-6); BOM, CRLF and
  quoted commas/quotes/line breaks parse per PD-12; the file name and declared content type are not used to decide anything.
- **Error behaviour:** any file-level code → outcome `rejected`, no user created, the audit record written (R-10).
- **Consumer outcome:** the admin gets code(s) that say which structural fault to fix.
- **Locators:** PD-2 and PD-12 above. **Pending:** all checks.
- **AL-2.1 positive:** S0, A, `bom-crlf-quoted` → `created`, 1 user: email `grace@example.test`, name `Hopper, Grace` (column order swapped, BOM, CRLF, quoted comma all accepted). S1, S3.
- **AL-2.2 failure:** `bad-header` → `rejected`, file_errors = [`missing_column` (column `email`), `unknown_column` (column `emial`)]; S3 unchanged. `role-col` → [`unknown_column` (column `role`)]; S3 unchanged. S1.
- **AL-2.3 failure:** `empty` → [`empty_file`]; `header-only` → [`no_rows`]; `malformed` → [`malformed_csv` at line 2]; `bad-encoding` → [`invalid_encoding`]; a request with no `file` part → [`missing_file`]. Each: 422, S3 unchanged. S1.
- **AL-2.4 boundary:** `blank-records` → `created`, 1 user `ada@example.test` / `Ada`; the empty line and both all-empty records are not rows. S1, S3. A header named `  EMAIL ` and `Name` (`  EMAIL ,Name\nada@example.test,Ada\n`) → `created` 1 user. S1, S3.
- **AL-2.5 boundary:** a semicolon-separated file `email;name\nada@example.test;Ada\n` → `rejected` with `missing_column` for `email` and `name` and `unknown_column` for `email;name`; the page's message names comma as the required separator. S1, S2.
- **Confirm (all AL-2.x):** table-driven integration tests over S1 with S3 read-back; AL-2.5 message in a browser test.

### R-3 File size and row-count limits

- **Basis:** request; AD-1; **OG-2 (numbers unresolved)**.
- **Behaviour:** two configured limits apply: `MAX_BYTES` (file size) and `MAX_ROWS` (non-blank data records). Over either → `rejected`, nothing created.
  A file at exactly a limit is accepted. The server stops reading the upload at `MAX_BYTES + 1` bytes.
- **Boundaries:** the limits are configuration, readable by tests, and never exceed the host's hard request-body and request-time limits (unknown, OG-2).
- **Error behaviour:** `file_too_large` carries `limit` (413); `too_many_rows` carries `limit` and `found` (422).
- **Consumer outcome:** the admin is told the limit that was exceeded and, for rows, how many rows the file had.
- **Pending:** the production values and every check. **No default number is specified.**
- **AL-3.1 boundary:** `MAX_ROWS=2`: `two-rows` → `created` (2 users); `ok-3` → `rejected`, [`too_many_rows` limit 2, found 3]; S3 unchanged by the rejected call. S1.
- **AL-3.2 boundary:** `MAX_BYTES=107`: `ok-3` (107 bytes) → `created`; with `MAX_BYTES=106` the same file → `file_too_large`, limit 106, 413. S1.
- **AL-3.3 failure:** a body much larger than `MAX_BYTES` (for example 10 MB with `MAX_BYTES=106`) → `file_too_large` and the server never reads more than `MAX_BYTES + 1` bytes of the body. **Confirm** integration test asserting the response and that no parse call and no store call occurred (a counting test double on both). S1.
- **AL-3.4 positive/target:** at the production limits, a file of exactly `MAX_ROWS` valid rows completes in the target environment without hitting a platform timeout (NFR-2). Surface S1 in the target environment; **NOT-REPLAYED here**: production values unresolved (OG-2).

### R-4 Every row is validated

- **Basis:** request, "bulk-create users"; PD-5, PD-4, PD-6; OG-1.
- **Behaviour:** for each non-blank data record: the number of fields equals the header's (`column_count_mismatch`, carrying `expected` and `found`);
  neither field contains a control character (`invalid_characters`, with `field`); `email` is present (`email_required`) and valid (`invalid_email`) per PD-5; `name` is present
  (`name_required`) and at most 100 characters (`name_too_long`). Values are trimmed; the email is lowercased (PD-4). **Every** row is validated and
  **all** problems are collected, a row with several bad fields yielding one error per bad field; the first failure does not stop the scan.
- **Boundaries:** email of 254 characters valid, 255 invalid; name of 100 valid, 101 invalid.
- **Error behaviour:** any row error → `rejected`, nothing created (R-6).
- **Consumer outcome:** the admin sees every faulty row at once (up to the cap in R-8).
- **Pending:** all checks; field rules subject to OG-1.
- **AL-4.1 positive:** `trim-case` → `created`, 1 user with email `ada@example.test` and name `Ada Lovelace`. S1, S3.
- **AL-4.2 failure:** S0, A, `bad-rows` → `rejected`, `error_count` 5, errors in this order: row 2 line 3 `email` `invalid_email`; row 3 line 4 `email` `email_required`; row 4 line 5 `name` `name_required`; row 5 line 6 `email` `duplicate_in_file` (`first_row` 1); row 6 line 7 `email` `email_taken`. Row 1 (valid) produces no error and **no user is created**: S3 unchanged. S1, S3. (The last two codes belong to R-5.)
- **AL-4.3 failure:** `colcount` → `rejected`, `error_count` 2: row 1 `column_count_mismatch` (expected 2, found 1), row 2 `column_count_mismatch` (expected 2, found 3). `ctrl-name` → `rejected`, row 1 `name` `invalid_characters`. S1.
- **AL-4.4 boundary:** `name-100` and `email-254` → `created` (1 user each); `name-101` → `name_too_long` row 1; `email-255` → `invalid_email` row 1. S1, S3.
- **AL-4.5 boundary:** a row `a@b,Dot Missing` → `invalid_email`; `a b@example.test,Space` → `invalid_email`; `a@@example.test,Two At` → `invalid_email`. S1. (Each is a different clause of PD-5.)
- **Confirm (all):** table-driven integration tests over S1 with S3 read-back; a pure unit test of the row validator for the PD-5 clauses.

### R-5 Email addresses must be unique

- **Basis:** request, "create users"; PD-3, PD-4; AD-3; OG-1.
- **Behaviour:** two rows of the same file whose emails are equal after normalisation → the **later** row is `duplicate_in_file` with `first_row` pointing at the earlier. A row whose normalised email equals an existing user's → `email_taken`. A row that is already invalid (R-4) is not also checked for duplicates. Existing users are neither changed nor skipped.
- **Boundaries:** comparison ignores case and surrounding spaces; `email_taken` is also the result when a concurrent writer takes the email before commit (R-9).
- **Error behaviour:** → `rejected`, nothing created.
- **Consumer outcome:** the admin learns which rows collide and with what kind of collision.
- **Pending:** all checks.
- **AL-5.1 failure:** S0, A, `ok-3` first (→ `created`), then `ok-3` again → `rejected`, `error_count` 3, rows 1, 2, 3 each `email_taken`; S3 shows 6 users in total after both calls (3 + 3), unchanged by the second. S1, S3. (Walked in section 9.)
- **AL-5.2 failure:** `bad-rows` rows 5 and 6 per AL-4.2. A file with `Ada@example.test` on row 1 and `ada@example.test ` on row 2 → row 2 `duplicate_in_file` with `first_row` 1. S1.
- **AL-5.3 boundary:** a file whose row 1 is `existing@example.test` and whose row 2 repeats it: row 1 `email_taken`, row 2 `duplicate_in_file` (`first_row` 1); existing user Existing User still has name `Existing User`. S1, S3.

### R-6 A valid file creates all its users, atomically

- **Basis:** request, "bulk-create users"; PD-1; AD-1; OG-1.
- **Behaviour:** when the file passes R-2…R-5, one user is created per data row, with the trimmed name and the normalised email (PD-4), inside **one transaction**, and the
  outcome `created` is returned with `created_count` equal to the number of data rows. If any insert fails, the transaction is rolled back, no user remains, and the outcome is `failed` (500) with `created_count` 0.
- **Boundaries:** one row is a valid file; the order of users is not significant.
- **Error behaviour:** `rejected` and `failed` leave the store exactly as it was; a repeat of the same upload is safe (it succeeds if nothing was created, or is `rejected` row by row if it was). If the client never receives the response, the admin checks the user list; re-uploading the same file is then a safe way to find out (R-5 reports every row `email_taken` if the first call committed).
- **Consumer outcome:** the new users exist and are listed by the product's own user views; no partial set ever exists.
- **Evidence limit:** there is no undo; correcting a wrong but valid import is done with the product's existing user management (unknown, OG-1).
- **Pending:** all checks; a fault-injection seam on the store (NFR-7).
- **AL-6.1 positive:** S0, A, `ok-3` → 201 `{"outcome":"created","created_count":3}`; S3 shows exactly 6 users, 3 of them `ada@example.test`/Ada Lovelace, `grace@example.test`/Grace Hopper, `linus@example.test`/Linus Torvalds; S0's three users are unchanged. S1, S3.
- **AL-6.2 failure (atomicity):** S0, A, `ok-3` with the store forced to fail the **third** insert → `failed` (500), `created_count` 0; S3 shows S0 unchanged (neither Ada nor Grace exists). **Confirm** integration test with the fault-injection seam; and the audit record has outcome `failed` (R-10). S1, S3, S4.
- **AL-6.3 failure:** any `rejected` outcome in AL-2…AL-5 leaves S3 equal to S0; this line is checked in each of those cases and needs no separate case. `n/a: covered there`.
- **AL-6.4 boundary:** `two-rows` with `MAX_ROWS=2` → 2 users; a file with a single valid row → 1 user (`created_count` 1). S1, S3.

### R-7 Users created by import start in the product's default state

- **Basis:** request (silence on onboarding); PD-8; OG-4; OG-1.
- **Behaviour:** an imported user is created through the same creation rules as the product's single-user creation, if one exists (OG-1). The import itself sets no password or other credential, assigns no role beyond whatever the product gives a new user by default, and sends no email or other message.
- **Boundaries/errors:** `n/a: no new boundary; field validation is R-4/R-5`.
- **Consumer outcome:** the created users appear in the user list; how they sign in is **not decided here** (OG-4).
- **Pending:** the decision; checks.
- **AL-7.1 positive:** S0, A, `ok-3` → `created`; the new users hold the product's default new-user role/state and **no credential**, and the test mail sink (or the product's outbound-message log) holds **no** message produced by the import. S3 and the outbound sink. **Confirm** integration test.
- **AL-7.2:** failure `n/a: nothing is sent or set, so there is no sending failure to specify`; boundary `n/a: see R-6`.

### R-8 The admin gets a complete, structured error report

- **Basis:** request (an upload needs a usable result); PD-7, PD-11.
- **Behaviour:** a `rejected` row-level outcome carries `error_count` (the true total), `truncated`, and `errors` (at most 100, ordered by row, then by field in the order email, name), each with `row`, `line`, `field` when it applies, `code`, and `first_row` for `duplicate_in_file`. A file-level rejection carries `file_errors`. The body never contains the contents of a cell.
- **Boundaries:** exactly 100 errors → `truncated` false; 101 → `truncated` true, 100 listed, `error_count` 101.
- **Error behaviour:** `n/a: this requirement is the error contract`.
- **Consumer outcome:** the page shows every returned error as a row of a table (R-12).
- **Pending:** all checks.
- **AL-8.1 positive:** `bad-rows` → body per AL-4.2 with `truncated` false and no cell text (no occurrence of `Bad Email`, `No Email`, `Ada Again`) in the JSON. S1.
- **AL-8.2 boundary:** `bad-100` with `MAX_ROWS` ≥ 101 → `error_count` 100, 100 listed, `truncated` false; `bad-101` → `error_count` 101, 100 listed (rows 1–100), `truncated` true. S1.
- **AL-8.3 failure:** `n/a: the unrecoverable failure outcome is R-6/AL-6.2`.

### R-9 Concurrent and repeated imports resolve without partial effects

- **Basis:** request (several admins may act); AD-3.
- **Behaviour:** when two imports (or an import and a single-user create) want the same email at the same time, exactly one commits that email; the other, as a whole, creates nothing and reports `email_taken` for the collided row. There is no ordering guarantee between the two imports. The import page allows only one submission in flight at a time.
- **Boundaries:** a second submission of a file after the first has finished follows R-5.
- **Error behaviour:** the losing import is `rejected`, its audit record says so (R-10).
- **Consumer outcome:** the store holds each email once and never a fragment of the losing file.
- **Pending:** all checks.
- **AL-9.1 boundary:** S0, two admin sessions submit `conc-A` and `conc-B` at the same time (barrier-released parallel calls). End state is **one of two**: A won → users {x@example.test/X} and B `rejected` with row 1 `email_taken`, `y@example.test` **absent**; or B won → {x/X2, y/Y} and A `rejected` with row 1 `email_taken`. Never x twice, never `y` without `x/X2`, never both `created`. S1, S3; repeat the race at least 20 times so both orders are seen or the repeat count is recorded. **Confirm** integration test over a real store (a mock store cannot show the constraint).
- **AL-9.2 consumer:** on the page, while a submission is pending, the submit control cannot start a second request (activating it twice quickly sends exactly one request). S2. **Confirm** browser test counting requests.

### R-10 Each import attempt is audited

- **Basis:** request (mass creation of accounts is a security-relevant action); PD-9; AD-5; OG-5.
- **Behaviour:** every import attempt by an authenticated user writes one audit record: actor id, time, outcome (`created`, `rejected`, `failed`, `forbidden`), `row_count` (data records parsed, 0 if parsing did not reach rows), `created_count`, `error_count` and `byte_size`. No file name and no cell contents. A `created` record is committed in the same transaction as the users: either both exist or neither does. `unauthenticated` requests have no actor and are only in the ordinary request log.
- **Boundaries:** an attempt rejected at the file level still records, with `row_count` 0 if the failure came before rows were parsed.
- **Error behaviour:** if writing a non-`created` audit record fails, the admin's outcome is unchanged and the failure is logged (without file content); if the audit write inside a `created` transaction fails, the whole import is `failed` (R-6).
- **Consumer outcome:** an operator can answer "who imported how many users, when, with what result".
- **Evidence limit:** who may read the audit records and their retention are unresolved (OG-5).
- **Pending:** all checks.
- **AL-10.1 positive:** S0, A, `ok-3` → exactly one new audit record: actor = admin's id, outcome `created`, `row_count` 3, `created_count` 3, `error_count` 0, `byte_size` 107, time within the test's start/end window. S4.
- **AL-10.2 failure:** `bad-rows` as A → one record: `rejected`, `row_count` 6, `created_count` 0, `error_count` 5. Session M with `ok-3` → one record: actor = member's id, `forbidden`, `created_count` 0. Session N → no audit record. S4.
- **AL-10.3 boundary:** AL-6.2's induced failure → one record `failed`, `created_count` 0, and no `created` record exists. S4.
- **AL-10.4 failure:** no audit record contains `ada@example.test`, `Ada Lovelace`, or the file name `ok-3.csv`, in any field. S4.

### R-11 Uploaded content is not retained or logged

- **Basis:** request (the file holds personal data); PD-9; AD-4.
- **Behaviour:** the uploaded bytes live only in the memory of the request that carried them and are discarded when it ends; they are not written to disk, a queue, a cache, the audit record or the application log. Logs for an import record only the outcome class, counts and error codes. The only place the file's values persist is the user records of a `created` import.
- **Boundaries:** the error body returned to the uploading admin may name rows and codes (R-8) but not cell contents; no other client can fetch the result.
- **Error behaviour:** a `failed` outcome logs the error class and a request id, not row data.
- **Consumer outcome:** an operator reading logs, or a later request, cannot recover another admin's uploaded rows.
- **Pending:** all checks.
- **AL-11.1 failure:** with log capture on (S5), run `ok-3` (created), `bad-rows` (rejected), `ok-3` with a forced failure (failed), and a forbidden call: no captured line contains `ada@example.test`, `Ada Lovelace`, `grace@example.test`, `Hopper`, `existing@example.test` or `Existing Again`. S5. **Confirm** integration test with a log capture and string scan.
- **AL-11.2 boundary:** after those runs the application's temporary directory and configured upload paths contain no new file, and the import operation exposes no `GET` that returns a previous result. S1 and file listing. **Confirm** integration test.

### R-12 The admin import page

- **Basis:** request, "Let admins upload a CSV"; AD-6; OG-3, OG-6. The page is the consumer surface of R-1…R-11.
- **Behaviour:** a page reachable by admins only (R-1) that lets the admin choose or drop one file, submit it to the import operation, and read the outcome. Visible states: **idle** (format help listing the two columns, an example row, the rules in PD-1/PD-2 in plain words, the file chooser/drop area, an inactive submit control); **file chosen** (name and size, a way to remove it, submit enabled); **pending** (the control keeps focus and announces "Importing…", no second submit, the chooser is inactive); **created** (the count, a link to the user list, focus moves to the result heading); **rejected** (a heading stating that **nothing was imported**, the count, the file-level messages or a table with columns Row, Line, Field, Problem for each returned error, and "Showing the first 100 of N" when truncated); **forbidden** / **unauthenticated** (a permission message / the sign-in redirect); **failed or unknown** (a message that the result could not be confirmed, to check the user list before importing again, and a way to try again).
- **Boundaries:** the chosen file's name is not sent anywhere except as the upload's own metadata and is not stored (R-11); after any response the file selection is cleared so the same fixed file can be chosen again; nothing is saved in browser storage; a reload drops the result and returns to idle.
- **Error behaviour:** a network failure, a timeout or a response the page cannot read is the `failed or unknown` state, never shown as success.
- **Consumer outcome:** the admin reaches the right next action in each state without reading documentation.
- **Locators:** `GUIDES/behavioral-requirements.md#ui-specific-planning`, `GUIDES/platforms/ui.md`. **Pending:** all checks; stack and components are chosen from the repository (AD-6).
- **AL-12.1 positive:** S0, A, open the page → idle state with the inactive submit control; choose `ok-3` → name `ok-3.csv`, size 107 bytes, submit enabled; submit → pending then **created** state showing "3 users created" and a working link to the user list; the user store then shows 6 users. S2, S3. **Confirm** browser test through role/label queries, with the response held by the test until the pending state is asserted.
- **AL-12.2 failure:** choose `bad-rows`, submit → **rejected** state: the heading says nothing was imported; the table has 5 rows in the order of rows 2, 3, 4, 5, 6, each showing its row number, line, field and a plain-language problem; no cell text from the file appears on the page except the row numbers and codes' words; S3 unchanged. S2, S3.
- **AL-12.3 failure:** choose `bad-101` (with `MAX_ROWS` ≥ 101) → the table shows 100 rows and the text "Showing the first 100 of 101". Session M opening the page → the "not available" message and no file control (AL-1.6). Network failure injected between submit and response (the test aborts the request after the server has committed `ok-3`) → the failed-or-unknown state with the check-the-list advice, **never** the created state; a retry then shows `email_taken` rows. S2.
- **AL-12.4 boundary:** pressing Enter or Space on the submit control twice quickly sends one request (AL-9.2); the file chooser works by keyboard alone (open, choose, submit, reach the result heading); dropping two files at once is refused with the message "Choose one CSV file" and the previous selection is kept (page-level default, not a product decision the request made). S2. **Confirm** browser test.
- **AL-12.5 consumer:** the result region is announced to assistive technology (`status`/`alert` semantics) without moving focus away from the heading; verified with the browser's accessibility tree, as one input to NFR-1's accessibility criteria. S2.

## 5. Non-functional requirements

The request names none, so each is assessed and either given an observable criterion, an unresolved bound, or a justified exclusion. No figure is invented.

| ID | Quality | Requirement | Operating conditions | Verification | Status |
|---|---|---|---|---|---|
| NFR-1 | **Interface quality** (R-12) | A deliberately designed, polished interface, not unstyled scaffolding. **Visual reference and starting appearance:** the light Gemini look with Material 3 Expressive principles from `GUIDES/platforms/ui.md#light-expressive-starting-point` (airy tonal rounded surfaces, friendly precise type, a restrained saturated accent, purposeful transitions), **light first with a dark option**. The product's own established identity, if discovery finds one (OG-3), **takes precedence**; the plan chooses the concrete tokens and records them in an AD. Observable criteria: (a) one visual system: spacing and type scales and a palette defined once, with a light and a dark theme that both render every state; (b) designed idle, file-chosen, pending, created, rejected and failed states (section R-12), including an empty state (idle) with format help, a loading state (pending) and error states with a clear next action; (c) at 360 px and at 1440 px viewport widths, no horizontal page overflow, and the rejected table remains readable (scrolls inside its own region at 360 px); (d) visible keyboard focus on every control; WCAG 2.2 AA contrast (text 4.5:1, large text and UI components 3:1) in both themes; (e) motion only to explain a change (pending → result), turned off under `prefers-reduced-motion`; (f) one icon set. The primary activity (choosing the file and reading the result) has the strongest position and weight. | web browser; supported-browser list unresolved (NFR-6) | rendered check of every state at both widths in both themes with the reduced-motion preference on and off; automated contrast computation for text and controls; keyboard-only walk (AL-12.4); accessibility-tree review (AL-12.5). A screenshot alone does not establish contrast, focus or motion. | accepted criteria; checks pending |
| NFR-2 | Performance / capacity | The import returns its outcome inside the host's request-time limit for a file of exactly `MAX_ROWS` rows at `MAX_BYTES`. **No latency or size number is specified: unresolved (OG-2)**; the missing evidence is the host limits and the chosen limits. | the target environment | AL-3.4 in the target environment (system test at the limits) | **unresolved bound** |
| NFR-3 | Security | Only admins (R-1); authority evaluated per request; cross-site request protection as the product's other admin writes (AL-1.5); no secret or credential involved in the import; cell values are stored as given after trimming and are not interpreted. Neutralising values that begin with `=`, `+`, `-` or `@` when a later feature exports users to CSV is **that feature's** duty and is excluded here with that reason. | all requests | AL-1.2…AL-1.5 | accepted; pending |
| NFR-4 | Privacy | R-11: no retention or logging of uploaded content; audit holds counts only (R-10). Retention of audit records is unresolved (OG-5). | all requests | AL-10.4, AL-11.1, AL-11.2 | accepted; retention unresolved |
| NFR-5 | Reliability / data integrity | All-or-nothing creation; unique emails under concurrency; an unknown outcome is recoverable by reading the user list. | store failure, concurrent writers | AL-6.2, AL-9.1 | accepted; pending |
| NFR-6 | Compatibility | The page works in the product's supported browsers; the file chooser is a native control so it works without drag-and-drop. The supported-browser list is unknown, none is invented. | browsers | cross-browser run of AL-12.1 and AL-12.4 over that list once known | **unresolved list** |
| NFR-7 | Testability / maintainability | Limits are configuration (tests use small values); the store accepts a test fault-injection seam for AL-6.2; the CSV fixtures of section 3 live as files in the repository. No new dependency is required by this spec. | build and test | the cases above | accepted; pending |
| NFR-8 | Operability | Each outcome class increments a count in the ordinary logs/metrics without file content (R-11); no alerting target is specified. | all requests | AL-11.1 reads the log lines for outcome class and counts | accepted; pending |
| — | Availability / throughput under load | **Excluded:** an administrator's occasional bulk action, bounded by `MAX_ROWS`; it adds no sustained workload to size, and contention between imports is a transition rule (R-9), not a load figure. | | | excluded with reason |

## 6. Behavior model

**Actors.** Admin (human, uses the page); the browser page (presentation state only); the import operation (authority for validation and creation); the user store (authoritative domain state); the audit store. No external service.

**F-1 Import a file** (R-1…R-11): admin submits → authorise → size check → decode and parse → header → rows → uniqueness → one transaction (insert users + audit) → respond.

```mermaid
sequenceDiagram
  participant P as Admin (page or API client)
  participant I as Import operation
  participant U as User store
  participant A as Audit store
  P->>I: F-1 POST file
  alt not signed in
    I-->>P: T-1 unauthenticated (401)
  else not an admin now
    I->>A: T-2 audit forbidden
    I-->>P: forbidden (403)
  else admin
    I->>I: T-3 size, encoding, syntax, header, row count
    alt file-level fault
      I->>A: audit rejected
      I-->>P: rejected (422, or 413)
    else
      I->>U: T-4 read existing emails; validate rows
      alt any row error
        I->>A: audit rejected
        I-->>P: rejected + errors (422)
      else
        I->>U: T-5 BEGIN; insert all users; insert audit; COMMIT
        alt unique violation at commit
          I-->>P: T-6 rejected, email_taken (422); rollback
        else store failure
          I-->>P: T-7 failed (500); rollback
        else
          I-->>P: created (201)
        end
      end
    end
  end
```

**F-2 Page flow** (R-12): idle → file chosen → pending → {created | rejected | forbidden | unauthenticated | failed-or-unknown} → (choose another file) → file chosen. A second submission is impossible while pending (R-9).

**State inventory.**

| Entity | States | Owner | Durable | Invariant |
|---|---|---|---|---|
| Import attempt | Received, Authorised, Validated, then terminal: Created, Rejected, Failed, Refused | the request | transient (only its audit record survives) | exactly one terminal state; Created implies all users and the audit record exist; any other terminal state implies no user from this attempt exists |
| User | absent → present (this feature never changes or removes a user) | user store | durable | normalised email unique |
| Page | idle, file chosen, pending, created, rejected, forbidden, unauthenticated, failed-or-unknown | browser memory | transient | at most one request in flight |

**Transition ledger** (before → after; guard; operation; failure/recovery; validation).

| ID | R / F | Before → After | Guard and operation | Observation, failure and recovery | Cases |
|---|---|---|---|---|---|
| T-1 | R-1 / F-1 | Received → Refused | no session | 401, nothing read or written; no audit | AL-1.2, AL-10.2 |
| T-2 | R-1, R-10 / F-1 | Received → Refused | session without current admin authority (also the revoked-since-load case) | 403, audit `forbidden`; store unchanged | AL-1.3, AL-1.4, AL-10.2 |
| T-3 | R-2, R-3 / F-1 | Authorised → Rejected | any file-level fault in the order of R-2 | 422/413 file-level codes; audit `rejected`; store unchanged | AL-2.x, AL-3.x |
| T-4 | R-4, R-5, R-8 / F-1 | Authorised → Rejected or Validated | rows all validated, errors collected, then uniqueness against the file and the store | any error → 422 with the report; audit `rejected`; no errors → Validated | AL-4.x, AL-5.x, AL-8.x |
| T-5 | R-6, R-10 / F-1 | Validated → Created | one transaction: insert every user, insert the audit record, commit | 201 `created_count`; both durable together | AL-6.1, AL-10.1 |
| T-6 | R-5, R-9 / F-1 | Validated → Rejected | unique violation raised at insert or commit | rollback; 422 `email_taken`; audit `rejected` | AL-9.1 |
| T-7 | R-6, R-10 / F-1 | Validated → Failed | any other store failure, including the audit write | rollback; 500; best-effort audit `failed`, logged without content; the admin may repeat the upload | AL-6.2, AL-10.3 |
| T-8 | R-12 / F-2 | page states as in F-2 | one transition per response class; unreadable response or network error → failed-or-unknown | never created without a `created` response | AL-12.1…12.3 |

**Forbidden or ignored events.** A second submit while pending: ignored, no request sent (AL-9.2). A GET on the import route: no result is stored, so none is returned (AL-11.2). A request with more than one file part: `missing_file`-class rejection (AD-2). Event families audited: invalid input (R-2, R-4), unauthorised (R-1), boundary (R-3, R-4), duplicate/idempotent replay (R-5), partial failure (R-6), concurrency (R-9), timeout/unknown outcome (R-6, R-12); timeout/retry **exhaustion, cancellation, expiry and restart** are `n/a: the operation is one synchronous request with no retained work (AD-1)`.

## 7. State and data assessment, information lifecycle, service boundary

**Affected resources and identities.**

| Carrier | Target identity | Change | Before → after invariant | Recovery |
|---|---|---|---|---|
| User records | by normalised email | **inserted** (never updated or deleted by this feature) | n users → n + k (k = rows) when `created`; otherwise n → n | rollback; unknown outcome checked on the user list; no undo (R-6) |
| Audit records | one per attempt by an authenticated user | inserted | m → m + 1 per attempt (in the users' transaction for `created`) | R-10 error behaviour |
| Upload bytes | the request's memory | transient | none persists | discarded at request end |
| Import result | the admin's page memory | transient | none persists | reload returns to idle; the user list is the source of truth |
| Limits `MAX_BYTES`, `MAX_ROWS` | configuration | observed only | set before use (OG-2) | n/a |
| Other users, sessions, roles | | **observed** (role read per request); not changed | unchanged | n/a |

Unknowns: the real schema, store, and whether the store supports transactions and unique constraints (assumed, AD-3; unverified).

**Information lifecycle per piece of state.**

| State | Owner and location | Who may read | Simultaneous changes | Ends when | Quotas met |
|---|---|---|---|---|---|
| Users created | user store (server) | whoever the product already lets read users | unique constraint decides (AD-3) | not ended by this feature | store limits unknown |
| Audit record | audit store (server) | per product audit policy (OG-5) | append-only, no conflict | per product retention (OG-5) | unknown |
| Uploaded file | request memory (server) | nobody; never exposed | none | request end | `MAX_BYTES`, host body limit |
| Parse/validation result | request memory → response | only the uploading admin | none | response sent | `MAX_ROWS`, error cap 100 |
| Selected file, result view | browser memory | the admin at that browser | one in flight (R-9) | reload, new selection, navigation | none |

Personal data: names and emails in the file are shown only back to the uploading admin (as row numbers and codes, not values), stored only as user records of a created import, never logged and never in the audit record, and removed with the user by the product's own user removal (not this feature). Nothing is put in browser storage; there is no sharing, identity or persistence added beyond the user records the request requires.

**Service boundary.** Page → import operation → user store and audit store, all inside the product; no external service, so remote-capability mapping, cache, incremental-state sync, asynchronous completion and event-gap recovery are `n/a: no consequential remote boundary (AD-1)`. **Current authority versus revocation:** the role is read at each request, so a demotion takes effect on the next request (AL-1.4); no cache of roles is introduced by this feature. **Owned observability:** authentication/security-relevant outcome, so R-10 and R-11 define the audit and log events and what they exclude. The acknowledgment of the operation is its final outcome (AD-1); there is no accepted-but-unprocessed state.

## 8. Traceability

| Request outcome | Acceptance lines |
|---|---|
| "admins" (only they can) | R-1: AL-1.1…1.6; R-10 |
| "upload a CSV" (file in, understood or refused) | R-2: AL-2.1…2.5; R-3: AL-3.1…3.4; R-12: AL-12.1, 12.4; R-8 |
| "bulk-create users" (all rows become users) | R-4: AL-4.1…4.5; R-5: AL-5.1…5.3; R-6: AL-6.1…6.4; R-7: AL-7.1; R-9 |
| the admin can act on the result | R-8: AL-8.1, 8.2; R-12: AL-12.2, 12.3, 12.5 |
| consequences the request implies (traceable, not invented scope) | R-10, R-11 (the action is security-relevant and the file is personal data); R-9 (several admins); NFR-1…NFR-8 |

Domain rules the request leaves out, under the R-<n> they bound: R-4 (no roles or other attributes, no other delimiters, no alternative encodings); R-5 (no update or skip of existing users); R-6 (no partial import, no dry run, no undo, no asynchronous import); R-7 (no invitation or credential); R-10 (no audit viewer); R-12 (no template download, no error-report download, no import history).

**Primary requirements** (what the user asked for directly): R-1, R-2, R-6, R-12.

**Prerequisites and open items by R:** R-1 (OG-1), R-3 (OG-2), R-4/R-5/R-6 (OG-1), R-7 (OG-4), R-10 (OG-5), R-12 (OG-3, OG-6), NFR-2 (OG-2), NFR-6 (browser list).

## 9. Replay check and evidence limits

**Walk of the ordered procedure (W-1), from its start.** Start: store S0 (3 users), session A. *Can the actor reach the start?* Yes: A is the admin in S0 and R-1 permits admins (AL-1.1). (a) A uploads `ok-3`: permitted by R-1; the three emails are not in S0 and are distinct (R-5), every field passes R-4 → `created`, S3 = 6 users. (b) A uploads `ok-3` again in the state (a) leaves: R-1 still permits; the three emails now exist → three `email_taken` errors on rows 1, 2, 3 (R-5), `rejected`, S3 stays 6. Recomputed: 201 then 422 with `error_count` 3; users 3 → 6 → 6. (c) From a fresh S0, session M uploads `ok-3`: R-1 refuses → 403, S3 = 3. The expected values in AL-1.x, AL-5.1, AL-6.1 and AL-12.1 follow from this walk. The byte counts were counted by hand: `ok-3` = 11 + 30 + 32 + 34 = 107; `two-rows` = 73.

**Expected results recomputed by hand** for `bad-rows` (AL-4.2: row 2 no `@`; row 3 empty email; row 4 empty name; row 5 `ADA@…` equals row 1 after lowercase; row 6 equals S0's existing user), `colcount`, `bom-crlf-quoted`, `blank-records`, `trim-case`, and the boundary lengths (241 + 13 = 254; 242 + 13 = 255).

**NOT-REPLAYED, so these stay open:** a small reference model of the rules was written at `RUN/scratch/model.py` to recompute the fixtures mechanically, but **running it was not approved in this session, so it was not executed and no exit code or case list exists**; the hand recomputations above are the only recomputation. AL-1.5 (CSRF mechanism), AL-3.4 (production limits, OG-2), AL-9.1 (needs a real store and parallel clients) and AL-12.x (need a browser and the real page) cannot be run at the spec stage. No product, test or documented command exists yet, so no command was run or recorded.

**Weaker-stand-in guard.** Each AL asserts the store read-back (S3) as well as the response, so a hardcoded response cannot pass; AL-5.1 and AL-6.2 assert that a user from the first rows is **absent**, so a partial import cannot pass; AL-8.1 and AL-11.1 assert the absence of named cell text.

**Unchecked claims a decision depends on:** that the store supports transactions and unique constraints (AD-3), that one request fits inside the host's time and body limits at the chosen limits (AD-1, OG-2), and the 254/100 length defaults (PD-5). No primary documentation or probe was available; each is stated as an assumption with its confirming step, not as a fact. An attempt to check the email length against the RFC was not made (outside the working directory and no network approval).

## 10. Retired

None. This is the first specification; no earlier R-<n> existed.

## 11. Submission

**summary:** First spec for "Let admins upload a CSV to bulk-create users", written with no repository, discovery, research or earlier spec, so every requirement (R-1…R-12) is new and the product baseline is unknown. Behaviour: an admin uploads one comma-separated UTF-8 file with columns `email` and `name`; the server validates the whole file and creates every user in one transaction, or creates none and returns a structured per-row error report (R-1…R-9); each attempt is audited without personal data and uploaded content is never kept or logged (R-10, R-11); an admin import page covers idle, chosen, pending, created, rejected, forbidden and unknown-outcome states (R-12). Eight non-functional criteria are assessed (NFR-1…NFR-8): a polished light-first UI with a dark option at the light Gemini / Material 3 Expressive starting point, subordinate to any established product identity. **Assumptions recorded as defaults (confirm those marked in section 2):** all-or-nothing import (PD-1), strict header that rejects extra columns such as `role` (PD-2), an existing email is an error rather than an update (PD-3), emails trimmed and lowercased (PD-4), email ≤ 254 and name ≤ 100 characters (PD-5), at most 100 row errors returned (PD-7), no credential set and no message sent (PD-8), a web admin page exists (OG-3). **Open:** the numeric file limits are unresolved (OG-2), so release is not ready until a person sets them and NFR-2 has no numeric bound; also OG-1 (user model, admin test, uniqueness and validation rules), OG-4 (how new users get access), OG-5 (audit reader and retention), OG-6 (user-list route) and the supported-browser list (NFR-6). Not replayed: the reference model script was not approved to run; expected results were recomputed by hand (section 9); CSRF, production-limit, concurrency and browser cases cannot run at this stage. No material requirement conflict was found. The `backchain-check` step does not exist here and was left out. Decisions on structure are in `KNOWLEDGE/architecture.md` (AD-1…AD-6).

**primary:** R-1, R-2, R-6, R-12

**evidence_refs:** `KNOWLEDGE/spec.md` (sections 1–11 and each of R-1…R-12), `KNOWLEDGE/architecture.md` (AD-1…AD-6), the request of 2026-11-21 recorded at the head of `spec.md`, `GUIDES/behavioral-requirements.md#behavior-model`, `GUIDES/behavioral-requirements.md#traceability-and-review`, `GUIDES/behavioral-requirements.md#actors-channels-and-state-ownership`, `GUIDES/requirements-definition.md` (NFR and state and data sections), `GUIDES/service-discovery.md#verification`, `GUIDES/platforms/ui.md#light-expressive-starting-point`, `GUIDES/current-system-baseline.md#planning-and-review-handoff` (no baseline existed), `GUIDES/project-knowledge.md#maintained-product-requirements`, `RUN/scratch/model.py` (written, not executed).
