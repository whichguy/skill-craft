## Use cases

### U-1: An admin uploads a valid CSV of new people to get all of them created as users in one step
Flow: The signed-in admin opens the user-import page, chooses one CSV file whose first row is `email,name,role` and whose other rows are people who do not yet exist (for example `ann@example.com,Ann Lee,member`), and submits it. The page shows that it is working, then shows a result saying how many users were created (for that file with 1 data row: 1). The admin opens the user list and finds every person from the file.
Source: request

### U-2: An admin learns what the file must look like before uploading
Flow: The admin opens the import page and reads which columns are accepted, which are required, which role values are accepted, and the size and row limits. The admin downloads a sample CSV, fills it in, and uploads it.
Source: implied: "upload a CSV" cannot be done without knowing the columns; the request names none

### U-3: An admin uploads a CSV in which some rows are wrong, finds out exactly which, fixes the file and uploads again
Flow: The admin submits a file in which, for example, row 3 has an empty email and row 7 repeats the email of row 4. The result says that no users were created and lists each problem with its row number, the column and the reason. The admin corrects the file and submits it again; this time all rows are created.
Source: implied: "bulk-create" over many rows makes some bad rows ordinary, and the admin must be able to act on them

### U-4: An admin uploads a file that cannot be processed at all and is told why
Flow: The admin submits no file, an empty file, a header-only file, a file over the size limit, a file with more rows than allowed, a file that is not UTF-8 text (for example an .xlsx), a file with an unrecognised or missing header, or a file with a broken quote. The page shows a message that says which of these it is and what the limit or expectation is. No users are created and the admin stays on the import page.
Source: implied: "upload a CSV" can be given something that is not a usable CSV

### U-5: An admin submits the same file again, double-clicks submit, or two admins import overlapping lists
Flow: The admin submits a file that already succeeded (or presses submit twice, or another admin imports a list containing some of the same people at the same time). The second attempt creates nothing and reports the already-existing emails row by row. The user list never contains two users for one email.
Source: implied: "bulk-create users" from a file that is re-sent, double-submitted or overlapped

### U-6: A person created by import gets in
Flow: A person whose address was in the file receives one email at that address with a link. They open the link, choose a password, and sign in. If the link has expired or never arrived they use the ordinary "forgot password" path on the sign-in page with their email and receive a fresh link.
Source: implied: "create users" is pointless if the new users cannot sign in, and the file carries no passwords

### U-7: Someone who is not an admin, or not signed in, tries to import
Flow: A signed-out visitor opens the import page or sends an upload request and is sent to sign in. A signed-in non-admin opens the import page or sends an upload request directly and is refused. No users are created.
Source: implied: "Let admins" means only admins

### U-8: An operator watches imports, switches the feature off, and recovers from failures
Flow: The operator reads a record of who imported what and with what outcome, finds which users were created by a given import, switches the feature off without a deploy, sees what happened when the database or the mail system failed, and rolls the product back to the version before without losing imported users.
Source: implied: operator's work for any feature that creates accounts in bulk

## Clauses

### C-1: A signed-in admin can open the user-import page
Observable: A signed-in admin who opens the user-import page sees a control to choose one file and a control to submit it.
Source: request

### C-2: The recognised columns are `email`, `name` and `role`
Observable: A file whose header row is `email,name,role` is accepted as to its header, and the values in those columns become the user's email, name and role.
Source: choice: the request names no columns; the admin must be told fixed names (U-2), and these are the least a user account needs

### C-3: A file in which every row is valid creates one user per row
Observable: Uploading a file with a header and 3 valid data rows with distinct new emails results in exactly 3 new users, each with the email, name and role from its row.
Source: request

### C-4: A successful import reports how many users were created
Observable: After the 3-row file of C-3 the result states that 3 users were created. For a file of 1,000 valid rows it states 1,000.
Source: implied: U-1, the admin must be able to tell what happened

### C-5: Created users appear in the user list
Observable: After a successful import the admin opens the user list and each of the file's emails is present.
Source: implied: U-1

### C-6: If any row is invalid, no user is created from that file
Observable: A file of 10 rows of which row 6 has an empty email creates 0 users: the user list is unchanged and the result says that no users were created.
Source: choice: the admin must be able to correct and re-upload without having to work out which rows already went in; all-or-nothing makes a corrected re-upload safe

### C-7: Every invalid row is reported with its row number, its column and its reason
Observable: For the file of U-3 the result lists a problem for row 3 naming the `email` column as empty and a problem for row 7 naming the `email` column as a repeat of row 4.
Source: implied: U-3

### C-8: A row with an empty email is invalid
Observable: A data row `,Ann Lee,member` is reported as a problem in the `email` column.
Source: implied: the email is the identity of a user and the file has no other identity column

### C-9: A row whose email repeats an earlier row in the same file is invalid
Observable: If row 4 and row 7 both have `bob@example.com`, row 7 is reported as a repeat of row 4; row 4 is not reported for that reason.
Source: implied: one user per email (U-5)

### C-10: A row whose email already belongs to an existing user is invalid
Observable: A row with `ann@example.com` when a user `ann@example.com` exists is reported in the `email` column as already existing, and the existing user is unchanged.
Source: implied: U-5; the request says create, not update

### C-11: A file with no data rows is rejected
Observable: A 0-byte file, a file with only the header row, and a file with a header and only blank lines are each rejected with a message saying the file contains no users; 0 users are created.
Source: choice: an empty upload is almost certainly a mistake and silence would look like success

### C-12: A file with more than 1,000 data rows is rejected
Observable: A file with 1,001 data rows is rejected whole with a message that states the limit of 1,000; 0 users are created. A file with exactly 1,000 valid data rows is not rejected for its row count. Blank lines are not data rows.
Source: choice: the request gives no size; a number is needed so that the import finishes in one request (see C-60)

### C-13: A file larger than 1 MiB (1,048,576 bytes) is rejected
Observable: A file of 1,048,577 bytes is rejected with a message that states the limit; 0 users are created. A valid file of exactly 1,048,576 bytes is not rejected for its size.
Source: choice: the request gives no size; a bound is needed (see C-60 and C-61)

### C-14: A signed-in non-admin cannot open the import page
Observable: A signed-in user who is not an admin and who opens the import page receives a refusal (HTTP 403) and sees no upload control.
Source: request: "admins"

### C-15: A signed-out visitor who opens the import page is sent to sign in
Observable: A request for the import page with no session is redirected to the sign-in page (or answered HTTP 401 for a non-browser caller); no upload control is shown.
Source: implied: "admins" cannot be known without signing in

### C-16: Each created user is sent one invitation email
Observable: For each user created by an import, a message is delivered to that user's address containing a link by which the person chooses a password. Exactly one such message per created user per import.
Source: implied: U-6

### C-17: A blank or absent `role` gives the default role `member`
Observable: A row `ann@example.com,Ann Lee,` and a file with no `role` column both create users whose role is `member`.
Source: choice: the request gives no role; a user needs a role, and the least privileged one is the safe default

### C-18: A row whose role is not an existing role is invalid
Observable: A row with role `wizard` is reported in the `role` column, naming the value `wizard`, and 0 users are created.
Source: implied: a user can only hold a role that exists

### C-19: The file is read as standard CSV: comma-separated, double-quote quoting, line breaks CRLF or LF
Observable: The row `ann@example.com,"Lee, Ann",member` creates a user named `Lee, Ann`; a quoted name containing `""` creates a name containing one `"`. A file using CRLF line ends and the same file using LF line ends create the same users.
Source: implied: "a CSV"; names contain commas

### C-20: A leading UTF-8 byte-order mark is ignored
Observable: A file that begins with the bytes EF BB BF followed by `email,name,role` has its first header recognised as `email` and is accepted.
Source: implied: spreadsheet programs write a BOM when saving CSV as UTF-8

### C-21: Non-ASCII text in a name is stored exactly
Observable: A row with name `Zoë Müller` and a row with name `李雷` create users whose names display as exactly `Zoë Müller` and `李雷`.
Source: implied: people's names

### C-22: A file that is not valid UTF-8 text is rejected whole
Observable: An .xlsx file, a file containing a NUL byte, or a file with an invalid UTF-8 byte sequence is rejected with a message saying it is not a UTF-8 text CSV; 0 users are created.
Source: implied: "a CSV" is text; a spreadsheet is the likeliest wrong file

### C-23: A file with an unterminated quoted field is rejected whole
Observable: A file in which a `"` opened at row 5 is never closed is rejected with a message that says the CSV is malformed and gives row 5; 0 users are created.
Source: implied: U-4

### C-24: Header names are matched ignoring letter case and surrounding spaces, in any column order
Observable: A header row ` Email , NAME,role ` and a header row `role,email,name` are both accepted, and values are taken from the columns by name.
Source: choice: admins edit these files by hand; order and case are spellings the request leaves open

### C-25: A file with no `email` column is rejected whole
Observable: A header row `name,role` is rejected with a message naming the missing column `email`; 0 users are created.
Source: implied: C-8, a user cannot be created without an identity

### C-26: A file with a column that is not `email`, `name` or `role` is rejected whole
Observable: A header row `email,name,password` is rejected with a message naming the column `password`; 0 users are created.
Source: choice: silently ignoring a misspelt column (for example `rol`) would create users with the default role without telling the admin

### C-27: A file in which the same column name appears twice is rejected whole
Observable: A header row `email,name,email` is rejected with a message naming `email` as repeated; 0 users are created.
Source: implied: U-4; one value cannot come from two columns

### C-28: Blank lines are skipped
Observable: A file with a blank line (no characters, or only spaces) between row 3 and row 5 creates users from the non-blank rows only; the blank line is not reported as a problem. A line `,,` is not blank: it is a row with an empty email and is reported under C-8.
Source: choice: editors leave a trailing or stray blank line and treating it as an error would be hostile

### C-29: Row numbers in messages count the header as row 1 and count blank lines
Observable: In a file whose header is line 1, followed by a blank line, followed by a data row with an empty email, the problem is reported for row 3.
Source: choice: the admin finds the row in a spreadsheet, which numbers the header row 1

### C-30: A row with a different number of fields than the header is invalid
Observable: With a header of 3 columns, the row `ann@example.com,Ann Lee` and the row `ann@example.com,Ann,member,extra` are each reported as having the wrong number of fields; 0 users are created.
Source: choice: guessing which field is missing could assign a wrong role

### C-31: Leading and trailing spaces around every value are removed
Observable: A row `  ann@example.com , Ann Lee , member ` creates a user with email `ann@example.com`, name `Ann Lee`, role `member`; spaces inside a name are kept.
Source: implied: hand-edited files

### C-32: An email must have the shape local@domain with a dot in the domain
Observable: `ann@example.com` and `ann+x@mail.example.co.uk` are accepted. `ann`, `ann@`, `@example.com`, `ann@@example.com`, `ann@localhost`, and `ann lee@example.com` are each reported in the `email` column.
Source: choice: a checkable minimum that an invitation could be delivered to; no stricter rule is required

### C-33: An email longer than 254 characters is invalid
Observable: An email of 255 characters is reported in the `email` column; one of 254 characters is not reported for length.
Source: implied: the longest email address that can exist (254 characters)

### C-34: A name is optional
Observable: A row `ann@example.com,,member` and a file with no `name` column each create users with an empty name and are not reported.
Source: choice: the request names no required field beyond what identifies a user

### C-35: A value containing a control character (including a line break or tab) is invalid
Observable: A quoted name containing a line break is reported in the `name` column; the same applies to the `email` and `role` columns.
Source: choice: such values break lists, mail headers and exports

### C-36: A role is matched against existing role names ignoring letter case
Observable: With roles `member` and `admin` existing, role `Admin` creates a user whose role is `admin`.
Source: choice: hand-typed values

### C-37: Two emails that differ only in letter case are the same email
Observable: `Ann@Example.com` in row 5 after `ann@example.com` in row 2 is reported as a repeat of row 2 (C-9); `Ann@Example.com` in a file when `ann@example.com` is an existing user is reported as already existing (C-10); after an import creating `ann@example.com`, creating a user `ANN@example.com` one at a time is refused as already existing.
Source: implied: people type emails with different capitals and one person must not become two users

### C-38: A deactivated or otherwise non-active existing user still counts as existing
Observable: A row whose email belongs to a deactivated user is reported as already existing; that user stays deactivated.
Source: choice: re-activating or duplicating an account through a bulk file is a surprise nobody asked for

### C-39: Names are displayed as literal text
Observable: A name `<b>Ann</b> & Co` is displayed in the user list and everywhere else as the characters `<b>Ann</b> & Co`, with no bold text and no script run.
Source: implied: file contents are untrusted input to whoever displays them

### C-40: The file's name and declared type do not decide whether it is accepted
Observable: A valid CSV saved as `users.txt`, or sent with the type `application/octet-stream`, is accepted; a file named `users.csv` that is not UTF-8 text is rejected under C-22.
Source: choice: browsers and operating systems label CSV inconsistently

### C-41: Submitting with no file chosen shows a message and does nothing
Observable: The admin submits the form with no file; the page asks for a file to be chosen; 0 users are created.
Source: implied: U-4

### C-42: An upload request carrying more than one file is refused
Observable: A request with two file parts is refused with a message that one file is allowed; 0 users are created.
Source: implied: "a CSV"; a caller other than the page can send more

### C-43: The import page offers a sample CSV that has the header row and no data rows
Observable: The admin follows a link on the import page and receives a file whose only line is `email,name,role`.
Source: choice: U-2; a header-only file avoids creating example people if uploaded unchanged

### C-44: The import page states the columns, which are required, the accepted role values, and the limits
Observable: The import page shows: `email` required; `name` and `role` optional; the names of the existing roles; the default role `member`; the limit of 1,000 data rows; the limit of 1 MiB.
Source: implied: U-2

### C-45: A user created by import cannot sign in until the person has chosen a password
Observable: Immediately after import, a sign-in attempt with the new user's email and any password, including an empty one, the email itself, or the name, fails.
Source: implied: the file carries no passwords, so no password exists until the person sets one

### C-46: The invitation email contains no password
Observable: The invitation message body contains a link and no password for the account.
Source: implied: U-6

### C-47: An invitation link works once
Observable: After the person has chosen a password with a link, opening the same link again shows that the link is no longer valid and does not change the password.
Source: implied: links that can set a password are credentials

### C-48: An invitation link expires 7 days after the import
Observable: A link opened 7 days and 1 minute after the import shows that the link has expired and sets no password; a link opened after 6 days works.
Source: choice: a bound is needed; 7 days is long enough for a person on leave to act

### C-49: A person whose invitation expired, was used up, or never arrived can get a fresh link through the sign-in page's forgot-password path
Observable: Submitting the user's email on the forgot-password form results in a new message to that address with a link that lets them choose a password.
Source: implied: U-6; without this a lost email strands the account

### C-50: The invitation emails are sent after the result is shown, and the result says so
Observable: The result page that states the number created also states that invitations are sent separately; the result does not wait for delivery of any email.
Source: implied: the invitations for 1,000 users cannot all be delivered inside the request (C-60)

### C-51: The result of a rejected file leaves the admin on the import page, ready to choose another file
Observable: After a rejection the page shows the problems and still shows the file chooser and the submit control.
Source: implied: U-3

### C-52: Submitting a file whose emails were already imported creates nothing
Observable: Submitting the same 3-row file a second time after it succeeded reports each of the 3 rows as already existing; the user list still has exactly 3 users from that file and no second invitation is sent to any of them.
Source: implied: U-5, the repeated time

### C-53: While an import is in progress the page shows that it is working and the submit control cannot be pressed again
Observable: After the admin presses submit, a progress indication appears and the submit control is disabled until the result is shown.
Source: implied: U-5, the double click

### C-54: Two imports at the same time that share an email yield one user for that email, and the import that did not win creates no users
Observable: Admin A and admin B submit different files at the same moment, both containing `ann@example.com`. Afterwards exactly one user has that email; one admin's result says that N users were created; the other admin's result says that 0 users were created and reports `ann@example.com` as already existing.
Source: implied: U-5, two things at once

### C-55: An import at the same time as a one-at-a-time creation of the same email yields one user for that email
Observable: While an import containing `ann@example.com` runs, another admin creates `ann@example.com` through the single-user form. Afterwards exactly one user has that email; either the import creates 0 users and reports the email as already existing, or the single creation is refused as already existing.
Source: implied: pass 3, import meeting an existing feature

### C-56: Two imports at the same time with no email in common both succeed
Observable: Admin A's 5-row file and admin B's 7-row file with no shared emails, submitted at the same moment, create 5 and 7 users and each result says so.
Source: implied: pass 3; one admin's import must not block another's

### C-57: The uploading admin's admin rights are checked at the moment the users would be created
Observable: If the admin is demoted, deactivated or signed out after the file was sent and before the users are created, 0 users are created, no invitation is sent, and the admin is shown the sign-in page or a refusal rather than a success result.
Source: implied: "Let admins"; a slow import must not outlive the right to import

### C-58: Other people never see part of an import
Observable: An admin who reloads the user list repeatedly while a 1,000-row import runs sees either none of its users or all 1,000, never a number in between.
Source: implied: C-6 (all-or-nothing) as seen from outside the importing page

### C-59: If the connection or the request fails part way, either all of the file's users exist afterwards or none do
Observable: The admin closes the browser tab 1 second after pressing submit. Later the admin submits the same file again: either 0 users from it existed (and all are now created) or all existed (and every row is reported as already existing). The user list never holds some but not all of the file's users.
Source: implied: pass 3, partial completion

### C-60: The result of a 1,000-row valid file is shown within 30 seconds
Observable: Under normal load, from pressing submit with 1,000 valid rows to seeing the result takes no more than 30 seconds, and the result is a normal page, not a timeout error.
Source: implied: the import is done inside one web request and web request timeouts (commonly 30 to 60 seconds, exact figure unconfirmed for this deployment) forbid longer; this is the reason for the limits in C-12 and C-13

### C-61: An oversized upload is refused without being processed and without harming other requests
Observable: Uploading a 100 MiB file returns the message of C-13 (HTTP 413); while it is being refused, other admins' pages keep loading in the ordinary time.
Source: implied: the web server's own request-body limit (exact figure unconfirmed) can refuse before the application sees the file; and a refusal must not require reading the whole body

### C-62: If the database is unavailable, the import fails with a message and creates nothing
Observable: With the database down, submitting a valid file shows a message that the import failed and that no users were created, and says to try again later; no invitation is sent.
Source: implied: U-8, a thing it depends on failing

### C-63: If the mail system fails, the users are still created and the failure is recorded
Observable: With mail delivery down, a valid 3-row file still creates 3 users and shows the result of C-4; each undelivered invitation is recorded for the operator with the user's id and the reason, not with the user's email or name.
Source: implied: U-8; invitation delivery is outside the all-or-nothing of C-6, which is about rows

### C-64: Every invitation of a successful import is delivered or recorded as failed within 1 hour
Observable: For a 1,000-row import, one hour after the result, each of the 1,000 people has received an invitation or the operator's record holds a failure entry for that user.
Source: implied: mail providers limit sending rates (exact figure unconfirmed), so 1,000 messages may take time; a bound is needed so that nothing is waiting forever

### C-65: The import page and the upload are served only over HTTPS in production
Observable: A request to the import page or the upload over plain HTTP in production is redirected to HTTPS or refused; the file contents are never sent in clear text.
Source: implied: the file holds people's names and email addresses, and the signed-in admin's session must not be exposed

### C-66: An upload request not made from the product's own import page is refused
Observable: A form post to the upload address from another website, using the admin's session but without the page's request token, is refused (HTTP 403); 0 users are created.
Source: implied: "Let admins"; a web page must not be able to make a signed-in admin create users

### C-67: The uploaded file is not kept after the request, and its contents are not written to logs
Observable: After an import, searching the server's stored files and logs for an email or name from the file finds none of them outside the user records, the invitation mail, and the result shown to the admin.
Source: choice: the file holds personal data; keeping a copy serves no stated need

### C-68: Every import attempt leaves an audit record
Observable: After any attempt (created, rejected for rows, rejected whole, failed), the operator can read a record with the admin's identity, the time, the number of data rows, the number of users created (0 when rejected), and the outcome. It holds no names or emails from the file.
Source: implied: U-8; bulk creation of accounts is a security-relevant act

### C-69: Each user created by import records which import and which admin created it
Observable: For any user created by import, the operator can find the audit record of C-68 that created it, and from that record list every user created by that import.
Source: implied: U-8; without it a mistaken import cannot be found and cleaned up

### C-70: The operator can switch the import feature off without deploying
Observable: With the feature switched off, the import page says that import is unavailable, a direct upload request is refused (HTTP 403 or 503), 0 users are created, and the rest of the product is unaffected.
Source: choice: the operator's way to stop a bad import path quickly; request is silent

### C-71: An import never changes any user who existed before it
Observable: Before and after an import, every existing user (including those whose emails are rows in the file, and including the importing admin) has the same name, role, status, password and open sessions.
Source: implied: the request says create, not update; C-10

### C-72: A row whose values the single-user form would refuse is invalid for import
Observable: Any email, name or role that the single-user form refuses (for example an email that does not meet that form's rules) is reported in the row's column when it appears in a file, in addition to the rules in this specification.
Source: implied: a rule enforced in one path and not the other would let the import bypass it

### C-73: Creating a user one at a time is unchanged by the existence of import
Observable: The single-user form creates a user with the same fields, the same checks and the same result as before the import feature existed.
Source: implied: pass 5, behaviour that must not change

### C-74: Users created by import stay valid if the import feature is switched off or rolled back
Observable: After the feature is switched off (C-70) or the product is returned to a version without it, an imported user who has chosen a password can sign in and appears in the user list, and a user who has not yet chosen a password can still be given a link through C-49.
Source: implied: U-8, going back to the version before

### C-75: A rejected or failed import sends no email and creates no password link
Observable: After an import that reports 0 users created, none of the addresses that were only in that file has received any message from the product.
Source: implied: C-6; an invitation for a user that does not exist would be a link to nothing

### C-76: At most 100 invalid rows are listed, and the total number of invalid rows is stated
Observable: A file of 500 rows each with an empty email lists rows 2 to 101 in row order and states that 500 rows are invalid.
Source: implied: the result page of a file with 1,000 bad rows must stay readable; 100 is a choice

### C-77: A row with several problems is listed with at least one of them
Observable: A row with a 201-character name and the unknown role `wizard` is listed with the `name` problem, the `role` problem, or both.
Source: choice: listing every problem of every row is not required, so long as the row is listed (C-7)

### C-78: The import page and its result can be used with a keyboard and a screen reader
Observable: The file control and submit control can be reached and operated with the keyboard alone; the control has a text label; the result and the problem list are real text in the page (not images) and are announced when they appear.
Source: implied: the page is used by admins of any ability

### C-79: Any admin may assign any existing role, including `admin`, in a row
Observable: A signed-in admin's file with a row `new@example.com,New Admin,admin` creates a user whose role is `admin`.
Source: choice: only admins reach the import and admins can already create admins one at a time (C-72); recorded in C-69 so it can be reviewed

### C-80: Users created by import are active
Observable: A user created by import, once they have chosen a password, can sign in and use the product as a user of their role.
Source: implied: U-6

### C-81: A name longer than 200 characters is invalid
Observable: A row with a 201-character name is reported in the `name` column; a 200-character name is accepted.
Source: choice: a bound for storage and display; the request gives none

### C-82: A file with more than one whole-file problem is rejected with at least one of them named
Observable: A file with header `email,password` and 1,001 data rows is rejected with a message naming the `password` column, the row limit, or both; 0 users are created. When the header is rejected, the data rows are not checked or reported.
Source: choice: the admin only needs to learn one thing to fix next

### C-83: An upload request from a signed-in non-admin is refused
Observable: A non-admin's upload request sent directly (not through the page) receives HTTP 403; 0 users are created and no invitation is sent.
Source: request: "admins"; the page's refusal (C-14) is not enough on its own

### C-84: An upload request with no session is refused
Observable: An upload request carrying no session receives HTTP 401 or a redirect to sign-in; 0 users are created and the file is not read.
Source: implied: "admins"; same reason as C-83

### C-85: A name is stored as given after trimming, even when it begins with `=`, `+`, `-` or `@`
Observable: A row with name `=SUM(A1)` creates a user whose name reads exactly `=SUM(A1)`.
Source: choice: altering what the admin supplied would be a silent change; neutralising such values belongs to whatever later exports them
