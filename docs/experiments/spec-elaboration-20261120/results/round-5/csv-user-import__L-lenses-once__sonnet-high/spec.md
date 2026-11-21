## Use cases

### U-1: An admin uploads a valid CSV to create many users at once
Flow: The admin opens the bulk-import page, picks a CSV file whose header row is `email,name,role` and whose rows are all valid (for example `ann@example.com,Ann Lee,member` and `bo@example.com,Bo Ray,admin`), and submits it. The page shows that the import succeeded, how many users were created, and the email address of each. Each new user receives an invitation email to set a password.
Source: request

### U-2: An admin uploads a CSV where some rows are invalid and learns every problem
Flow: The admin submits a file in which, for example, row 3 has a malformed email, row 5 has an empty name and row 9 repeats the email of row 4. The page shows that nothing was created and lists every problem with its row number, column and reason. The admin corrects the file and uploads it again.
Source: implied: "bulk-create users" from a file written by a person means some rows will be wrong

### U-3: An admin uploads a file that cannot be used at all
Flow: The admin submits an empty file, a file over the size limit, a file with more than the allowed number of rows, a file that is not valid UTF-8 text (for example an .xlsx workbook), a file with no header row or missing required columns, or submits the form with no file chosen. The page shows one clear reason for the refusal, and nothing is created.
Source: implied: "upload a CSV" - not every upload is a usable CSV

### U-4: The same file, or overlapping files, are submitted more than once
Flow: The admin double-clicks Submit, re-uploads a file that already succeeded, or two admins upload files containing the same email at the same moment. Each email ends up with exactly one account; the upload that cannot create an account for some email is refused as a whole with the reason "already exists" for that row.
Source: implied: users are unique by email, and uploads are repeated and concurrent in real use

### U-5: Someone who is not an admin tries to use the import
Flow: A signed-in non-admin user, or a person who is not signed in, requests the import page or sends an upload directly. They are refused, they are shown nothing about the import, and no user is created.
Source: implied: "Let admins" - everyone who is not an admin is excluded

### U-6: An admin finds out what format the file must have before uploading
Flow: On the import page, the admin reads the column names, which are required, the allowed role values, the size and row limits, and an example, then prepares the file.
Source: implied: "upload a CSV" - the admin cannot produce an acceptable CSV without knowing its columns

### U-7: A newly created user gets access
Flow: The new user receives an email, opens the link in it, chooses a password, and is then able to sign in with their email and that password. If the link is used a second time or is older than 7 days, they are told it is no longer valid.
Source: implied: users created in bulk must be able to sign in, and the CSV carries no passwords

### U-8: An admin checks what imports have been done
Flow: The admin opens the list of imports, sees each attempt with who ran it, when, the file name and the outcome, opens one, and sees the users it created or the errors it produced.
Source: implied: bulk creation of accounts by an admin is a security-relevant action that must be accountable

### U-9: An operator takes the feature beyond a development environment
Flow: The operator serves the application over HTTPS, configures the outgoing email sender, and confirms that an upload of the largest allowed file completes within the platform's request time limit.
Source: implied: the feature handles personal data and sends email, and runs inside a web request

## Clauses

### C-1: An admin can reach the import page and upload form
Observable: A signed-in user whose role is `admin` can open the bulk-import page and sees a form with a file-choice control and a submit control.
Source: request

### C-2: A signed-in user who is not an admin is refused
Observable: A signed-in user whose role is not `admin` who requests the import page or sends an upload receives HTTP status 403, is not shown the form, and no user is created. No link to the import appears in what they see.
Source: implied: U-5, "Let admins"

### C-3: A person who is not signed in is refused
Observable: A request for the import page without a signed-in session is redirected to the sign-in page; an upload sent without a signed-in session receives HTTP status 401. In both cases no user is created.
Source: implied: U-5

### C-4: Admin status is checked when the upload is processed
Observable: If a user's `admin` role is removed, or their session ends, after the form was displayed but before the upload is submitted, the submitted upload is refused (403 or 401 as in C-2 and C-3) and no user is created.
Source: implied: U-5, a page loaded earlier can outlive the permission that allowed it

### C-5: An upload forged from another website is refused
Observable: An upload request made by a page on a different origin using an admin's browser session, without the application's anti-forgery token, receives HTTP status 403 and creates no user.
Source: implied: a browser-submitted state-changing action by an admin must not be triggerable by third parties

### C-6: The import is served only over HTTPS outside development
Observable: In a non-development deployment, a request to the import page or upload endpoint over plain HTTP is redirected to HTTPS or refused, and no file content is accepted over plain HTTP.
Source: implied: U-9, the upload contains personal data and is made by an admin session

### C-7: The import page states the file format
Observable: The page shows, in text: the column names `email`, `name`, `role`; that `email` and `name` are required and `role` is optional; the allowed role values `member` and `admin` and that a blank role means `member`; the limits "1 MiB" and "1,000 rows"; that the file must be UTF-8; and one example file of a header plus two rows.
Source: implied: U-6

### C-8: Exactly one file is accepted per upload
Observable: A submission with no file is refused with a message saying that no file was chosen; a submission with two or more files is refused with a message saying that exactly one file is allowed; in both cases nothing is created and the form is shown again.
Source: implied: "upload a CSV" - one CSV, and the case of none

### C-9: A file larger than 1,048,576 bytes is refused
Observable: A file of 1,048,577 bytes or more is refused with a message that states the limit "1 MiB"; for an API caller the status is 413. A file of exactly 1,048,576 bytes is not refused for its size. Nothing is created. This holds whether or not the client declares the size in advance.
Source: choice: the request gives no size; a limit is required because the upload is read into one request, and 1 MiB is many times what 1,000 rows need

### C-10: An empty file is refused
Observable: A file of zero bytes, or one containing only whitespace and line breaks, is refused with a message saying the file is empty; nothing is created.
Source: implied: U-3, the empty case

### C-11: The file is read as UTF-8, with an optional byte-order mark ignored
Observable: A file starting with the UTF-8 byte-order mark (EF BB BF) is read as if the mark were absent, so its first column is named `email`, not `﻿email`. A file containing a byte sequence that is not valid UTF-8 is refused with a message saying the file is not valid UTF-8; nothing is created. Non-ASCII text such as `Zoë Müller` and `李雷` in a valid file is stored exactly as written.
Source: implied: spreadsheet programs export CSV with a byte-order mark; names contain non-ASCII characters

### C-12: The file is judged by its content, not by its name or declared type
Observable: A valid CSV named `users.txt` or uploaded with content type `text/plain` is accepted; a binary file named `users.csv` (for example an .xlsx workbook) is refused with the not-valid-UTF-8 message of C-11 or the malformed-CSV message of C-14.
Source: choice: file names and declared types are set by the client and vary by operating system; the content is what decides

### C-13: The file is parsed as comma-separated values in the standard quoting form
Observable: The delimiter is the comma. A field wrapped in double quotes may contain commas, line breaks, and doubled double quotes (`""` is one `"`), and is read as a single field with those characters. Records end with LF, CRLF or CR. A final record without a trailing line break is read. A file using semicolons or tabs as delimiters is read as one-column rows and is refused by C-15.
Source: implied: "CSV"

### C-14: A file with broken quoting is refused as a whole
Observable: A file with a double quote opened and never closed, or with text directly after a closing quote within a field, is refused with a message that says the CSV is malformed and gives the row number where the problem starts; nothing is created.
Source: implied: U-3, a CSV can be malformed

### C-15: The header row must contain the required columns
Observable: The first record that is not blank is the header row. If it has no `email` column, or no `name` column, the file is refused with a message naming each missing column; nothing is created.
Source: implied: columns must be identifiable to read a CSV into users; U-3

### C-16: Header names are matched without regard to case, surrounding spaces or order
Observable: A header of ` Name , EMAIL ,Role` is read as the columns `name`, `email`, `role` in that order, and rows are read according to that order.
Source: choice: files made by hand or by spreadsheets vary in capitalisation and spacing; fixing them would only cause refusals

### C-17: A header that names the same column twice is refused
Observable: A header such as `email,name,Email` is refused with a message naming the repeated column; nothing is created.
Source: choice: with two columns of the same meaning there is no way to know which value is intended

### C-18: Columns other than `email`, `name` and `role` are ignored and reported
Observable: Values in other columns are not stored anywhere and have no effect, and the page's result (success or refusal) lists the names of the ignored columns, for example "Ignored columns: phone, password".
Source: choice: the request names no columns; ignoring but reporting avoids both refusing harmless files and silent loss

### C-19: A file with a header but no data rows is refused
Observable: A file whose only non-blank record is the header row, or whose data rows are all ignored under C-21, is refused with a message saying that there are no rows to import; nothing is created.
Source: implied: U-3, the empty case after the header

### C-20: A file with more than 1,000 data rows is refused
Observable: A file with 1,001 or more data rows (not counting the header or ignored rows of C-21) is refused with a message that states the limit "1,000 rows" and the number of rows found; nothing is created. A file with exactly 1,000 data rows is not refused for its row count.
Source: choice: the request gives no count; a bound is required because the import runs inside one web request and must finish in time (C-53)

### C-21: Rows with no content are ignored
Observable: A record in which every field is empty after trimming (a blank line, or a line such as `,,`) is skipped: it creates no user, produces no error, and does not count toward the 1,000-row limit.
Source: choice: spreadsheets leave trailing empty rows; refusing them would only annoy

### C-22: Row numbers match the position in the file
Observable: Wherever a row number is shown, the header is row 1, the first record after it is row 2, and every record (including ignored empty ones and records spanning several lines) counts as one row, so the number equals the row number shown when the file is opened in a spreadsheet.
Source: choice: the request gives no numbering; this is the numbering an admin editing the file sees

### C-23: Values are trimmed before they are checked or stored
Observable: Spaces and tabs at the start and end of each value are removed: ` ann@example.com ` is stored as `ann@example.com`, `  Ann Lee ` as `Ann Lee`. Spaces inside a value are kept.
Source: implied: hand-made files contain stray spaces

### C-24: A row with a different number of values than the header is invalid
Observable: A row with more or fewer fields than the header has columns produces an error for that row with the reason "wrong number of fields" and the counts found and expected.
Source: implied: a row that does not line up with the header cannot be read reliably

### C-25: An email must satisfy these rules
Observable: A row is invalid with an error on column `email` if the email, after trimming: is empty; is longer than 254 characters; contains whitespace; does not contain exactly one `@`; has an empty part before or after the `@`; or has no `.` in the part after the `@`. `ann@example.com` is valid; `ann@example`, `ann.example.com`, `@example.com` and `a@b@c.com` are invalid.
Source: choice: the request gives no email rule; a basic structural check that rejects obvious typos without refusing real addresses

### C-26: A name is required and at most 200 characters
Observable: A row is invalid with an error on column `name` if the name, after trimming, is empty or longer than 200 characters. A name of exactly 200 characters is valid. Any other characters are allowed, including apostrophes, hyphens, non-ASCII letters and a leading `=`.
Source: choice: a user needs something to be called by; the length cap prevents unusable records

### C-27: A role must be `member` or `admin`
Observable: A role value, compared without regard to case (`Member`, `ADMIN`), that is neither `member` nor `admin` makes the row invalid with an error on column `role` listing the two allowed values. The stored role is the lower-case form.
Source: choice: the request names no roles; `member` and `admin` are the least set that lets an admin create both ordinary and administrative users

### C-28: A blank or absent role means `member`
Observable: If the file has no `role` column, or a row's role is empty after trimming, the user is created with role `member`.
Source: choice: the request gives no role; the least-privileged value is the safe default

### C-29: Emails are the same account regardless of letter case
Observable: `Ann@Example.com` and `ann@example.COM` are treated as the same email in every comparison in this feature (against existing users and within the file). The stored email, when read back, compares equal to either spelling.
Source: implied: users are unique by email, and addresses are typed with varying case

### C-30: A row whose email already belongs to an existing user is invalid
Observable: If any existing user has the same email (C-29), regardless of that user's role or whether the account is active, deactivated or still waiting for its first sign-in, the row is invalid with an error on column `email` and the reason "already exists". The existing user is not changed.
Source: implied: U-4, uniqueness; the request says "create", not "update"

### C-31: A repeated email within the file is invalid on its second and later occurrences
Observable: When the same email (C-29) appears in several rows, the first occurrence is checked normally; each later occurrence is invalid with an error on column `email` whose reason names the row number of the first occurrence, for example "duplicate of row 4".
Source: implied: U-2, uniqueness within a single file

### C-32: Every invalid row is reported, with no cut-off
Observable: When a file has N rows with problems, the refusal lists at least one error for each of those N rows, with no cap on the number of errors listed (up to the 1,000-row maximum). A file with 40 bad rows shows 40 or more entries.
Source: implied: U-2, an admin fixes the file once rather than one error per upload

### C-33: Each reported error carries a row number, a column and a reason
Observable: Each error entry shows the row number (C-22), the column name (`email`, `name` or `role`, or "row" when the error concerns the whole row as in C-24), and a reason in words that a person can act on.
Source: implied: U-2

### C-34: One invalid row means no user is created
Observable: If a file passes the checks of C-8 to C-20 but any row is invalid, then after the response the set of users is exactly what it was before the upload, and the response is a refusal listing the errors of C-32. Valid rows in the same file are not created.
Source: choice: all-or-nothing, because an admin who fixes and re-uploads a partly imported file would otherwise hit "already exists" on rows that had succeeded

### C-35: A fully valid file creates exactly one user per row
Observable: After a file whose rows are all valid, for each row there is exactly one user with the row's trimmed email, trimmed name and role (C-27, C-28), in the active state, and the number of users has grown by the number of rows (not counting ignored rows of C-21).
Source: request

### C-36: A successful import shows its result
Observable: The response states the number of users created, for example "2 users created", and lists the email of each created user. If the file had ignored columns (C-18) they are listed too.
Source: implied: U-1, the admin needs confirmation of what was done

### C-37: A failure while saving leaves nothing created
Observable: If the data store fails or becomes unavailable while the users are being saved, the response says the import failed and nothing was created (not a partial count), the set of users is as before, no invitation is sent, and the admin can upload the same file again.
Source: implied: U-1, partial completion

### C-38: Two imports that contain the same email never produce two accounts
Observable: When two uploads containing the same email run at the same time, or an upload runs while that email is registered through any other path, afterwards exactly one user has that email. The upload that did not obtain the account creates no user at all, and its admin is shown a refusal with the "already exists" reason for that email (or a message that the import conflicted and may be retried).
Source: implied: U-4, two things at once

### C-39: An import never changes an existing user
Observable: Whether the import succeeds or is refused, every existing user's email, name, role, active state, password and sessions are the same after it as before. No existing user is updated, deactivated or deleted by an import.
Source: implied: "bulk-create" means create only; what must not change

### C-40: No password is taken from the file, and new users cannot sign in until they set one
Observable: A `password` column in the file is treated as an unknown column (C-18): its values are not stored, logged or usable. Right after an import, signing in as a new user with any password, including one given in the file, fails.
Source: choice: the request gives no way to set passwords; plaintext passwords in files is a known hazard, and not taking them also keeps the import fast (C-53)

### C-41: Each new user receives exactly one invitation email
Observable: For each created user, one email arrives at the user's address, containing a link for setting a password, naming the application. A user created by an import receives one such email from that import; refused imports send none.
Source: choice: the request does not say how users get access; an emailed set-password link is the least that makes created users usable

### C-42: Invitations are sent after the users are saved and do not delay or undo the import
Observable: The success response of C-36 is shown without waiting for the emails to be delivered. If an email cannot be sent, the user it was for still exists, the other invitations are still sent, and the import still reports success.
Source: implied: U-9, email delivery depends on an outside system that can fail or be slow, and cannot be rolled back

### C-43: A set-password link works once and for 7 days
Observable: The link in an invitation lets its user set a password exactly once; after that, or more than 7 days (168 hours) after the email was sent, opening it does not allow setting a password. A link whose text has been altered does not work. The 7 days is a choice.
Source: choice: the request gives no lifetime; single-use and a bounded lifetime limit the damage of a forwarded or leaked email

### C-44: A used or expired link says so and changes nothing
Observable: Opening a used or expired link shows a message that the link is no longer valid, and no password is set or changed; the user is not signed in by it.
Source: implied: U-7, the unhappy path of C-43

### C-45: The password a new user sets follows the system's password rules
Observable: A password the system's existing rules for passwords refuse is refused here with the same message. Where the system has no such rules, a password shorter than 12 characters is refused. After a valid password is set, the user can sign in with their email and that password, and has the role from the file.
Source: implied: U-7, existing password rules must hold on every path that sets a password; choice: 12 where the system is silent

### C-46: A failed invitation is recorded for the admin
Observable: When an invitation email could not be sent, the detail page of that import (C-50) lists the user's email as "invitation not sent".
Source: implied: U-8, C-42 makes the failure invisible in the response, so it must be visible somewhere

### C-47: Text from the file is shown as text
Observable: A name such as `<script>alert(1)</script>` or `<b>x</b>` is stored as written and is displayed on the result page, the error list, the import record and any other page of the application as the literal characters; no script runs and no formatting is applied.
Source: implied: file contents are untrusted input shown to admins

### C-48: The file contents and invitation links are not kept or logged
Observable: After the response, the uploaded file is not available anywhere in the application (not retrievable by any URL, not stored in the import record). The server logs and the import records contain neither the rows of the file nor any set-password link.
Source: implied: the file holds personal data, and a link in a log is a working credential

### C-49: Each import attempt that reaches authorization is recorded
Observable: Every attempt by an admin (success or refusal, including refusals under C-8 to C-20) produces one import record with: the admin who made it, the time (UTC), the original file name (empty if no file), the outcome ("created" or "refused"), the number of rows found, the number of users created and the number of errors. Attempts by non-admins or signed-out persons produce no import record.
Source: implied: U-8

### C-50: An import record lists the users it created
Observable: The detail page of an import record shows, for a successful import, the emails of the users it created; for a refused import, the reason or the list of errors of C-32. The detail page of a created user can be traced back to the import that created it, by the import record's identifier or time.
Source: implied: U-8, accountability for accounts created in bulk

### C-51: Only admins can see the import records, and they are listed newest first
Observable: An admin sees a list of import records with the most recent first, each showing the fields of C-49. A non-admin or signed-out person requesting that list or a record receives 403 or 401 respectively.
Source: implied: U-8, U-5

### C-52: Import records are not deleted automatically
Observable: An import record is still shown after any amount of time; no import removes or edits another's record.
Source: choice: with no retention rule given, keeping them is the safe default for an audit trail

### C-53: A valid 1,000-row import completes within 30 seconds
Observable: Uploading a valid file of 1,000 rows (each with email, name and role, at most 1 MiB) shows the success result of C-36 in no more than 30 seconds, without a gateway or server timeout error. The 30 seconds is below the request time limit of common web hosts, whose exact figure for this deployment is unconfirmed.
Source: implied: U-9, the processing runs inside a single web request and the host will end a request that runs too long
