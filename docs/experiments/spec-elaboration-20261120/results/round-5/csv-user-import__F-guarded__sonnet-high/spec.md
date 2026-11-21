# Specification: admin CSV bulk user import

Scope note. The working directory held no product code, so nothing about the existing product (its user fields, roles,
single-user creation, mail, limits) could be read. Rules the existing product already has are therefore stated as
"parity" clauses, each marked as unconfirmed against the existing product. Terms used throughout:
"admin" = a signed-in account that currently holds the admin role and is active; "data row" = any record of the file
after the header record that is not blank; "blank record" = a record whose fields are all empty or only whitespace
(this includes a zero-length line); "rejected" = no user is created from the file.

## Use cases

### U-1: An admin creates many users at once from a CSV file, to avoid creating them one by one
Flow: The admin opens the user-import page in the admin area. They see a file chooser for one file, a submit control, and
text naming the columns the file needs (`email` required, `name` optional) and the limits (1,000 data rows, 1,048,576
bytes). They choose a file whose first record is `email,name` and whose next records are valid rows, then submit. They
see a result stating how many users were created, which equals the number of data rows. The new users then appear in the
existing user listing.
Source: request

### U-2: An admin uploads a file with bad rows, to learn exactly what to fix
Flow: The admin submits a file in which some data rows are invalid (bad email, duplicate, already registered, name too
long, wrong field count). They see that nothing was created, and a list of every invalid row with its row number, the
column, the value found and the reason. The form is shown again so they can choose a corrected file.
Source: implied: "bulk-create users" from a file a person assembled by hand will contain mistakes, and the admin must be able to correct them.

### U-3: An admin uploads a file that cannot be read as a user list at all
Flow: The admin submits a file that is empty, header-only, not UTF-8 text (for example an .xlsx), malformed CSV, larger
than 1,048,576 bytes, over 1,000 data rows, or whose header lacks `email` or has unknown, duplicate or empty column
names. They see that nothing was created and one message naming the problem (and the limit or the offending column
names where relevant). The form is shown again.
Source: implied: "upload a CSV" admits files that are not usable CSVs of users.

### U-4: An admin repeats an import (same file again, or a corrected file after a rejection)
Flow: After a rejection the admin corrects the file and submits it again and sees success with the full count. Or, after
a success, they submit the same file again and see that nothing was created and every row is reported as already
registered. No user is duplicated and no existing user is changed in either case.
Source: implied: people retry; a retry must be safe.

### U-5: A person who is not an admin tries to import
Flow: A signed-in non-admin opens the import page address or posts a file to it and is refused, seeing an
"not permitted" outcome and no form. A person who is not signed in is sent to sign in and sees no import form. No file
is read and no user is created in either case.
Source: implied: "Let admins" means only admins.

### U-6: Two imports (or an import and a single-user creation) overlap in time
Flow: Two admins submit files that share an email address at the same moment, or an admin submits a file while
another admin creates one of its addresses by hand. Exactly one account exists for that address afterwards; the loser of
the race sees a rejection that names the address's row as already registered and nothing from their file is created.
Source: implied: more than one admin exists and acts concurrently.

### U-7: A newly imported person begins to use their account
Flow: A person whose row was imported receives whatever first-access arrangement an individually created user receives
and uses it to reach their account. Their account behaves as an ordinary non-admin user.
Source: implied: "create users" is pointless if the users cannot use the accounts.

### U-8: An admin's upload is interrupted or the system fails during it
Flow: The admin's connection drops, the request times out, or the system fails while the import runs. Afterwards, either
all rows of the file exist as users or none do. The admin can tell which by looking at the user listing or by
submitting the file again, and sees a failure message (not a success message) when the system failed.
Source: implied: unhappy path "a thing it depends on failing".

### U-9: An admin imports the largest permitted file
Flow: The admin submits a file of exactly 1,000 data rows and at most 1,048,576 bytes. They see the result within 30
seconds and all 1,000 users are created.
Source: implied: the largest case of "bulk".

### U-10: A script operator submits a file programmatically with admin credentials
Flow: A non-browser client authenticated as an admin sends the same multipart submission. It receives a status
code that tells success from refusal from rejected content, and the same report of problems in the response body.
Source: implied: "upload" through a web interface can be driven by a client; the outcome must be distinguishable without reading the page.

### U-11: An operator runs the feature in production
Flow: The operator deploys it, finds out in the logs who ran which import and how it ended without seeing personal
data, sees that a failed import left no partial data to clean up, and, if the feature is rolled back, finds the users it
created still working.
Source: implied: operator's work (observe, recover, carry on with existing data, go back to the version before).

## Clauses

### C-1: The import page is reachable by admins and offers a single-file upload form
Observable: A signed-in admin who goes to the user-import page in the admin area sees a file chooser that takes one
file and a submit control.
Source: request

### C-2: The import page states the accepted format and the limits
Observable: The page text names the column `email` as required, the column `name` as optional, and states the limits
1,000 data rows and 1,048,576 bytes.
Source: choice: with no downloadable template or other documentation, the admin cannot otherwise know the format they must produce.

### C-3: A signed-in account that is not currently an active admin is refused
Observable: Every signed-in account that does not hold the admin role right now (ordinary users, accounts whose
admin role was revoked, deactivated or suspended accounts) is refused with HTTP status 403 and shown no import form;
the file is not read and no user is created.
Source: implied: "Let admins" excludes everyone else.

### C-4: A person who is not signed in cannot import
Observable: A request to the import page or the submission with no valid session gets HTTP status 401 (or is
redirected to sign in); no form is shown, no file is read and no user is created.
Source: implied: admin status cannot be established without signing in.

### C-5: Admin status is checked again immediately before users are created
Observable: If the submitting account stops being an active admin or its session ends after the upload began but before
creation, no user is created and the outcome is the same as in C-3 (403) or C-4 (401).
Source: choice: a long upload can straddle a revocation; the loosest rule that keeps a revoked admin from acting.

### C-6: A submission without a valid anti-forgery proof is refused
Observable: A submission made from another site on behalf of a signed-in admin, or lacking the anti-forgery token the
form carries, is refused with HTTP status 403 and creates no user.
Source: implied: shipping beyond development requires that a state-changing admin action cannot be forged from another site.

### C-7: A submission with no file is refused with a message
Observable: Submitting with no file chosen shows a message that a file is required; no user is created and the form is
shown again.
Source: implied: "upload a CSV" — the empty submission is the first unhappy path.

### C-8: A submission carrying more than one file is refused
Observable: A submission whose body holds two or more files is refused with HTTP status 422 and a message that exactly
one file is expected; no user is created.
Source: choice: the request says "a CSV"; refusing is safer than guessing which file counts.

### C-9: The file is read as CSV in the conventional (RFC 4180) form
Observable: Fields are separated by commas and records end at LF or CRLF; a field wrapped in double quotes may contain
commas and line breaks, and a double quote inside it is written as two. A file `email,name` / `a@x.com,"Smith, Ann"`
yields one data row with name `Smith, Ann`; a semicolon is not a separator.
Source: implied: "CSV" means these conventional rules.

### C-10: A file that is not valid UTF-8 text is rejected
Observable: A file containing a byte sequence that is not valid UTF-8, or containing a NUL byte (an .xlsx or other
binary file, or a Windows-1252 file with accented letters), is rejected with a message that the file is not UTF-8
text; no user is created.
Source: choice: guessing an encoding could store corrupted names; UTF-8 is the one every tool can produce.

### C-11: A leading UTF-8 byte-order mark is ignored
Observable: A file that starts with the bytes EF BB BF is processed exactly as the same file without them; the first
column is recognised as `email`, not as an unknown column.
Source: implied: spreadsheet programs write a byte-order mark when saving "CSV UTF-8".

### C-12: The first record is the header and columns are matched by name, in any order
Observable: A file with header `name,email` is read the same as one with header `email,name`; names are matched
ignoring letter case and surrounding whitespace, so ` Email ` is `email`.
Source: choice: a stated contract for the admin's file; order-independence and case-insensitivity are the loosest rules that avoid failing on harmless variations.

### C-13: The recognised columns are exactly `email` and `name`
Observable: Header names other than `email` and `name` are not accepted (see C-15); no other column sets anything on the
created user.
Source: choice: the request names no fields; email identifies a user and name is the one further field a person supplies; nothing else is invented.

### C-14: A header without an `email` column is rejected
Observable: The file is rejected with a message that the required column `email` is missing; no user is created.
Source: implied: a user cannot be created without an identifier.

### C-15: A header containing an unrecognised column name is rejected, naming it
Observable: The file is rejected; the message lists each unrecognised header exactly as found in the file (for example
`email;name` for a semicolon-separated file, or `role`, or `password`); no user is created.
Source: choice: silently ignoring a column would let an admin believe data (such as a role) was applied when it was not.

### C-16: A header naming the same column twice is rejected
Observable: A header such as `email,Email` or `email,name,name` is rejected with a message naming the repeated
column; no user is created.
Source: implied: the value for a repeated column would be ambiguous.

### C-17: A header with an empty column name is rejected
Observable: A header such as `email,name,` (a trailing comma) or `email,,name` is rejected with a message that a
column has no name; no user is created.
Source: choice: simplest unambiguous rule; the message tells the admin to delete the stray empty column.

### C-18: A zero-byte file or a file with only blank records is rejected
Observable: A file of 0 bytes, or one with only blank records, is rejected with a message that the file is empty; no
user is created.
Source: implied: the empty case.

### C-19: A file with a header but no data rows is rejected
Observable: A file whose header is valid but which has no data row is rejected with a message that it contains no
users; the result is not shown as a success and no user is created.
Source: choice: "0 users created" as a success would hide that the admin uploaded the wrong file.

### C-20: Blank records are skipped
Observable: Blank records, whether before the header (the header is then the first non-blank record) or after it
(including a final empty line and rows such as `,` exported by spreadsheets), create no user, are not errors and do
not count toward the 1,000-row limit.
Source: implied: spreadsheet exports routinely end with empty rows.

### C-21: Row numbers count every record, blank ones included, starting at 1 for the first record
Observable: In every report the first record of the file is row 1, the next row 2, and so on, so a row number equals
the row number a spreadsheet program shows for the same file; with the header in the first record, the first data row
is row 2. A record spanning several lines (quoted line break) takes one row number.
Source: choice: the admin must be able to locate a row; this numbering matches what they see in a spreadsheet.

### C-22: Malformed CSV is rejected, naming the row where the fault starts
Observable: A quoted field never closed before the end of the file, text following a closing quote other than a comma
or line end, or a double quote inside an unquoted field, causes rejection with one message giving the row number where
the fault begins; no user is created.
Source: choice: lenient guessing could shift columns and create wrong users; failing early with a location is safest.

### C-23: A file of up to 1,048,576 bytes is accepted and a larger one rejected
Observable: A file of exactly 1,048,576 bytes (otherwise valid) is processed; one of 1,048,577 bytes is rejected with
HTTP status 413 and a message stating the 1,048,576-byte limit; no user is created.
Source: choice: the request gives no size; a typical row is under 100 bytes, so 1,048,576 bytes is far above what 1,000 ordinary rows need; a file of maximal-length multi-byte values can exceed it and is then rejected by this clause.

### C-24: Up to 1,000 data rows are accepted and more are rejected
Observable: A file of exactly 1,000 data rows (otherwise valid) is processed; one of 1,001 data rows is rejected with
HTTP status 422 and a message stating the limit of 1,000; no user is created and no row-level report is produced.
Source: choice: the request gives no limit; 1,000 is large enough for a team or class and small enough to finish synchronously.

### C-25: A file at the maximum size completes within 30 seconds
Observable: Submitting a valid file of 1,000 data rows, against a user store already holding at least 100,000 users,
shows the result within 30 seconds of the upload finishing.
Source: choice: a figure the admin waits for; the 30-second figure is our own and is unconfirmed against the platform's request timeout, which must be at least this.

### C-26: Files up to the size limit reach the application intact
Observable: A valid file of 1,048,576 bytes sent through the production front end (proxy, gateway, upload middleware)
is processed by the application and is never answered with a generic front-end "too large" or timeout page; the exact
front-end limits are unconfirmed and must exceed 1,048,576 bytes plus the multipart envelope.
Source: implied: the runtime's request-body limits (commonly about 1 MiB by default in proxies) would otherwise contradict C-23.

### C-27: A data row must have as many fields as the header
Observable: A row with more or fewer fields than the header is reported with its row number and the reason "wrong
number of fields", naming the found and the expected count; no user is created from the file.
Source: choice: guessing which field is missing could put an email in the name field.

### C-28: Each value is trimmed of surrounding whitespace before it is checked or stored
Observable: A row `  a@x.com  , Ann ` creates a user whose email is shown as `a@x.com` and whose name is shown as
`Ann`. Whitespace means any Unicode White_Space character (space, tab, no-break space and so on).
Source: implied: hand-edited files carry stray spaces and tab characters; the whitespace is never meaningful.

### C-29: A row with an empty email is invalid
Observable: A data row whose email is empty after trimming is reported with its row number, column `email` and the reason
"email missing".
Source: implied: email is required (C-14).

### C-30: An email must have the basic shape of an address
Observable: An email is valid only if it has exactly one `@` with at least one character before it, a domain after it
containing at least one `.`, the domain neither beginning nor ending with `.` and containing no `..`, and no whitespace or
control characters (U+0000–U+001F, U+007F). `ann@x.com` is valid; `ann`, `ann@x`, `@x.com`, `a@@x.com`, `a b@x.com`
are each reported with the reason "email invalid".
Source: choice: the loosest shape that catches typos without fixing a full address grammar; stricter single-user rules are covered by C-40.

### C-31: An email longer than 254 characters is invalid
Observable: A trimmed email of 254 characters (otherwise valid) is accepted; one of 255 is reported with the reason
"email too long".
Source: choice: 254 is the conventional maximum length of an email address.

### C-32: A name is optional; an empty name means no name
Observable: A row whose name is empty after trimming, or a file with no `name` column, creates the user with no name;
the user listing shows the user by email with an empty name.
Source: choice: the request supplies no field list; making name optional is the loosest rule.

### C-33: A name longer than 200 characters is invalid
Observable: A trimmed name of 200 Unicode code points is accepted; one of 201 is reported with its row number, column
`name` and the reason "name too long".
Source: choice: the request gives no bound; 200 is generous for a personal name.

### C-34: A name containing a control character is invalid
Observable: A name containing any character in U+0000–U+001F or U+007F (including a line break inside a quoted field) is
reported with the reason "name has invalid characters".
Source: choice: control characters in a name can break displays and logs; all other characters, including `=`, `<`, quotes and non-Latin letters, are accepted verbatim.

### C-35: A repeated email within the file is invalid on its later occurrences
Observable: When the same address (compared ignoring letter case, after trimming) occurs in several rows, the first
is judged on its own merits and every later row is reported with the reason "duplicate of row N", where N is the row
number of the first occurrence. Rows reported under C-27 (wrong number of fields) are left out of this comparison,
neither counting as a first occurrence nor as a duplicate.
Source: implied: one person cannot have two accounts for the same address; choice: a row whose fields cannot be told apart has no reliable email to compare.

### C-36: An email that already belongs to an existing account is invalid
Observable: A row whose address (compared ignoring letter case) belongs to any existing user, whatever its state
(active, deactivated or suspended, invited but not yet accepted, locked), is reported with the reason "already
registered"; that user is not changed.
Source: implied: the existing rule that an address identifies one account must hold for imported rows.

### C-37: Every problem is reported at once, for every invalid row
Observable: When rows are invalid, the report lists every invalid row (up to the 1,000-row limit, with no shorter
cap and no "and N more"), not just the first; a row with several problems appears at least once with at least one reason.
Source: implied: U-2, the admin corrects the whole file in one pass.

### C-38: Each reported problem carries a row number, a column, the value found and a reason
Observable: Each entry in the report shows: the row number (C-21); the column (`email`, `name` or, for field-count
problems, no column); the value found, cut to its first 100 characters; and the reason, one of: email missing, email
invalid, email too long, name too long, name has invalid characters, wrong number of fields, duplicate of row N,
already registered, or the reason the existing single-user rule gives (C-40). Different reasons read differently.
Source: implied: U-2; choice: the 100-character cut keeps one oversized value from flooding the page; the wording of each reason is left to the product.

### C-39: File-level problems are reported alone, without row validation
Observable: When the file is rejected for a file-level reason (C-10, C-14 to C-19, C-22, C-23 or C-24), the response
gives at least one such reason (more than one when several apply) and no row-level entries.
Source: choice: rows cannot be interpreted reliably when the file or header is unusable.

### C-40: Every rule single-user creation applies to an email or name also applies to each row
Observable: A value that the existing single-user creation refuses (for example a banned email domain or a name
format) is reported for its row as invalid, with a reason; a value it accepts but C-30 to C-34 refuse is still
refused. Unconfirmed: the existing rules could not be read when this was written.
Source: implied: bulk creation must not become a way around rules of normal creation.

### C-41: A cap on the number of accounts, if the product has one, applies to the whole import
Observable: Where the product limits total accounts (unconfirmed whether it does), an import that would take the total
above the cap is rejected whole with a message stating how many accounts may still be added; no user is created.
Source: implied: an existing limit must not be bypassed by bulk creation.

### C-42: Any invalid row or file-level problem means no user is created
Observable: When a file contains one or more invalid rows or a file-level problem, the user listing before and after the
submission is identical (same users, same count, same details).
Source: choice: all-or-nothing makes a retry after correction safe — a file that was partly applied would make the corrected re-upload fail on its own earlier rows.

### C-43: A fully valid file creates exactly one user per data row
Observable: After a file of N valid data rows is submitted, the user listing holds N more users than before, one for each
address in the file.
Source: request

### C-44: The success result states the number created
Observable: The page shown after success states the count of users created, equal to the number of data rows (blank
records not counted); the HTTP status is 200.
Source: implied: the admin needs confirmation of the outcome of a bulk action.

### C-45: A created user holds the trimmed email and name from its row
Observable: The listing shows each created user with the email and name as given in the file after trimming (C-28);
a name containing `=`, `<script>` or non-Latin letters appears exactly as written.
Source: implied: the request's purpose is that the file's data becomes the users.

### C-46: Imported users get the default non-admin role and importing cannot make admins
Observable: Every created user holds the role a user created individually holds by default and is not an admin; no
file content can change this.
Source: choice: lets a file grant privileges only if an admin writes that into it; refusing is the safe, loosest rule that serves "create users".

### C-47: Imported users receive the same first-access arrangement as individually created users
Observable: Each imported user goes through the same first-access step (an invitation, a set-password message or
whatever an individually created user goes through; unconfirmed what that is) and ends up with the same means of first
access; the file contains no password and the result page and the logs never show a credential.
Source: choice: the request does not say how new users get in; reusing the one existing mechanism avoids a second credential path.

### C-48: First-access messages are sent only after the import has been fully applied
Observable: A rejected or failed import sends no message to any address in the file; an applied import sends one per
created user, which may arrive after the result page is shown.
Source: implied: telling people they have an account that was never created would be wrong; sending 1,000 messages inside the request would break C-25.

### C-49: A failure to send a first-access message does not undo the import
Observable: When a message cannot be sent, the user it was for still exists and the result still states success.
Source: choice: the account creation is the committed fact; sending is retried or handled by the existing mechanism (unconfirmed).

### C-50: The new users become visible together
Observable: At no moment does the user listing show some but not all of the file's users: it shows none of them before
the import completes and all of them after.
Source: implied: C-42 and C-43 together require atomic effect.

### C-51: A system failure during creation leaves no users and says so
Observable: If the store or another dependency fails while users are being created, the admin sees a failure message
distinct from a row report and from a success, the HTTP status is 5xx, no user from the file exists, and the form is
shown again.
Source: implied: unhappy path "a thing it depends on failing".

### C-52: An upload interrupted before the server has the whole file creates nothing
Observable: When the connection drops before the whole request body has been received, no user is created.
Source: implied: U-8.

### C-53: After a timeout or dropped connection during processing the file is either fully applied or not at all
Observable: When the admin sees no response, the listing holds either all of the file's users or none; submitting the
file again then either succeeds in full or reports every row as already registered.
Source: implied: U-8 and C-42.

### C-54: Submitting the same file again after a success changes nothing
Observable: A second submission of a file already applied is rejected with every data row reported as "already
registered" and the user listing unchanged.
Source: implied: U-4; repeated submission must not duplicate.

### C-55: Overlapping imports never create two accounts for one address
Observable: When two imports (or an import and an individual creation) contain the same address at the same time, one
account exists for it afterwards; the import that did not create it creates none of its users and reports that row as
"already registered".
Source: implied: U-6; the uniqueness rule of C-36 holds under concurrency.

### C-56: The submit control cannot be used twice while an upload is in progress
Observable: After the admin presses submit, the control is disabled and an in-progress indication is shown until the
result arrives.
Source: choice: prevents accidental duplicate submissions from a slow upload; the server still stays safe without it (C-54).

### C-57: After a rejected or failed import the form is available again and nothing is left behind
Observable: The result page includes the form; the failed attempt leaves no pending or partial user, record or
message other than the log entry of C-61.
Source: implied: U-2, U-3 — "go back, fix and retry".

### C-58: Outcomes are told apart by HTTP status for non-browser callers
Observable: Success returns 200; a person not signed in 401; not an admin or a forged submission 403; a file over
1,048,576 bytes 413; any other rejection of the content (no file, a second file, a file-level problem or invalid rows) 422; a system
failure 5xx; the body carries the same report as the page.
Source: choice: callers must tell success from refusal; the exact codes are conventional values fixed here so a script can rely on them.

### C-59: The uploaded file is not kept after the response
Observable: After the response is sent, the file's contents are not stored anywhere readable by admins or operators,
other than the users it created.
Source: choice: the file is personal data; nothing in the request calls for keeping it.

### C-60: Values echoed in the report are shown as plain text
Observable: A value such as `<img src=x onerror=alert(1)>` found in a rejected row appears in the report as those
literal characters and runs nothing.
Source: implied: the report repeats attacker-influenced text on an admin's page.

### C-61: Every import attempt is logged for the operator, without personal data
Observable: For each attempt the operator can find, in the product's logs, the admin's identity, the time, the file's
name, the outcome (created, rejected rows, rejected file, refused, failed), the number of users created and the number
of invalid rows; the log contains no email address, no name and no file content from the file.
Source: choice: a bulk admin action must be traceable; the file's personal data is not wanted in logs.

### C-62: A file name cannot forge or break a log entry
Observable: A file named with a line break or control characters is logged as a single entry; the characters do not
start a new line.
Source: implied: C-61 logs text chosen by the uploader.

### C-63: The import form and the report can be used without a mouse or colour
Observable: The file chooser and submit control are reachable and operable by keyboard; every report entry is text, not
conveyed by colour alone.
Source: implied: the page is part of the admin area that people with accessibility needs use.

### C-64: The import does not change, deactivate or delete existing users
Observable: After any import, every user that existed before it has the same fields, role and state as before.
Source: implied: the import only creates; "what must not change".

### C-65: Creating a user individually behaves as it did before this feature
Observable: Every action and every outcome of single-user creation, including its fields, validation and first-access
messages, is the same with the feature present as without it.
Source: implied: existing behaviour that must be kept.

### C-66: Imported users stay usable if the feature is rolled back
Observable: After the import feature is removed or the product is rolled back to the version without it, every user it
created still exists and signs in and is listed like any other user.
Source: implied: operator "go back to the version before".

### C-67: The import works against users that existed before the feature
Observable: An import into a store already holding users created by other means (earlier versions, single creation)
detects their addresses as "already registered" and leaves them intact.
Source: implied: "carry on with data that already exists".

### C-68: Letter case of an address does not make it a different address
Observable: `Ann@X.com` in the file, when `ann@x.com` already exists (or occurs in an earlier row), is reported
"already registered" (or "duplicate of row N").
Source: implied: C-35 and C-36 hold for the real-world way addresses are typed.

### C-69: The way to the import page is shown only to admins
Observable: A link or menu entry to the import page appears in the admin area for an admin and in no page shown to a
non-admin or to a person not signed in.
Source: implied: "Let admins" — offering the action to others would invite the refusals of C-3 and C-4.

### C-70: The file is judged by its content, not by its name or declared type
Observable: A valid CSV named `users.txt`, or with no extension, or sent with the content type
`application/vnd.ms-excel` (what Excel sends for CSV files) or `application/octet-stream`, is processed exactly as the
same content named `users.csv`; a file that is not UTF-8 text is rejected by C-10 whatever its name.
Source: implied: "upload a CSV" from real browsers and spreadsheet programs, which label CSV files inconsistently.
