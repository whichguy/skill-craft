# Specification: admins upload a CSV to bulk-create users

Terms used throughout. **Admin** = a signed-in user whose role is `admin` and whose status is `active`. **Row** = one data record of the CSV (not the header). **Row number** = the 1-based line number, counting every physical line of the file including blank lines, on which the record starts (the header is normally row 1, the first data row row 2). **Whitespace** = space, tab, and non-breaking space (U+00A0). **Existing user** = a user record in any of the states `invited`, `active`, `deactivated`.

## Use cases

### U-1: An admin uploads a valid CSV to create many users at once
Flow: The admin opens the import page from the admin user-management area, chooses a file `users.csv` with header `email,name,role` and the rows `jane@example.com,Jane Doe,member` and `raj@example.com,Raj Patel,admin`, and submits it. The page shows a new import with status `queued`, then `processing`, then `succeeded` with "2 rows read, 2 users created". The two users appear in the user list with status `invited`, and each of them receives an invitation email.
Source: request

### U-2: An admin downloads a template to see the expected columns
Flow: On the import page the admin chooses to download the template. A file is downloaded whose only line is `email,name,role`.
Source: implied: "upload a CSV" presumes the admin knows which columns the CSV must have.

### U-3: An admin uploads a CSV with bad rows, reads the errors, fixes the file and uploads it again
Flow: The admin uploads a file with 300 rows in which row 17 has the email `not-an-email` and row 42 repeats the email in row 5. The import ends with status `rejected`, "0 users created", and an error list with an entry for row 17 (column `email`, reason `invalid_email`) and an entry for row 42 (column `email`, reason `duplicate_in_file`). Nothing was created. The admin fixes rows 17 and 42 in the file, uploads it again, and the import ends `succeeded` with 299 users created.
Source: implied: a CSV of any size written by hand or exported from elsewhere will contain bad rows (unhappy path of the request).

### U-4: An admin uploads a file that cannot be read as a user CSV at all
Flow: The admin uploads a file (for example an empty file, a spreadsheet saved as `.xlsx`, a file whose header lacks `email`, a file of 5,001 rows, or a file over 5 MiB). The page tells the admin, in a message that names the reason (`empty_file`, `invalid_encoding`, `missing_required_column`, `too_many_rows`, `file_too_large`), that no users were created and what limit or requirement was broken.
Source: implied: unhappy path of the request (wrong input, limit reached).

### U-5: An admin follows an import and later reviews what was imported
Flow: After submitting, the admin leaves the page open and watches the status change without reloading, or closes the page and later opens the import history. The history lists imports newest first. Opening one shows who uploaded it and when, its outcome, and either the full error list (`rejected`), the list of users it created (`succeeded`) or the failure reason (`failed`).
Source: implied: an upload of up to 5,000 rows cannot finish inside one web request, so the admin needs to see progress and outcome afterwards.

### U-6: A newly created user accepts the invitation and signs in
Flow: The user receives an email at the address from the CSV containing a link. They open the link within 7 days, choose a password, and their status becomes `active`; they can then sign in with that email address and password. Before doing so they cannot sign in.
Source: implied: the CSV carries no passwords, yet "create users" must yield people who can use the product.

### U-7: An admin deals with an invitation that was never delivered or has expired
Flow: In the user list or import detail the admin sees a user whose status is `invited` and whose invitation delivery is `failed` (or whose 7 days have passed). The admin chooses to resend the invitation; the user receives a new email whose link works, and the old link no longer works.
Source: implied: invitations are sent by an outside email service, which can fail, and a created user nobody can reach is lost.

### U-8: Someone who is not an admin, or not signed in, tries to use the import
Flow: A signed-in `member` opens the import page address or sends an upload request directly; a signed-out visitor does the same. Neither can import, download the template, or see import history.
Source: implied: the request says "admins".

### U-9: Two uploads collide (double submission, or two admins at once)
Flow: An admin double-clicks the submit button, or submits the same file again from a second tab while the first import is still `queued`; or two admins upload files that share an email address at the same moment. At most one user per email address results, no duplicate user is created, and every admin sees a clear outcome for their own import.
Source: implied: uploads are slow enough for people to repeat them; two admins can act at once.

### U-10: The system fails or restarts while an import is running
Flow: The database becomes unavailable, or the application restarts, while an import is `processing`. The admin returns, sees the import in a final state (`failed`), sees that no users were created, and uploads the same file again; it succeeds without producing duplicates.
Source: implied: "a thing it depends on failing" for a long operation that writes thousands of records.

### U-11: An operator runs and maintains the feature
Flow: The operator deploys the application so that a 5 MiB upload reaches it through the public address over HTTPS, background processing and the email service are running, and the server logs hold no uploaded personal data. If the background processing or email service is down, admins see imports that end `failed` (reason `timeout`) or invitations with delivery `failed`, rather than data loss. Imports and invitations older than their retention periods disappear on their own.
Source: implied: the operator's work (start, configure, observe, recover) for a feature that processes personal data in bulk.

## Clauses

### C-1: Active admins can use the import page and submit a CSV
Observable: A signed-in user with role `admin` and status `active` can open the import page, see a single-file chooser and a submit control, and submit a file; on acceptance an import record is created (see import lifecycle clauses).
Source: request

### C-2: Everyone else is refused with HTTP 403 on every import-related request
Observable: A signed-in user whose role is `member`, or whose status is `deactivated`, receives HTTP 403 and no content when requesting the import page, the template download, the import history, an import's detail, the upload, or an invitation resend; this holds also when the request is sent directly rather than through the page. No import record and no user is created by such a request.
Source: implied: U-8, "admins" in the request.

### C-3: Signed-out visitors are sent to sign in
Observable: A request from a visitor who is not signed in to any import-related page address is redirected to the sign-in page; a non-page (upload, resend) request receives HTTP 401. No import record and no user is created.
Source: implied: U-8.

### C-4: An upload sent from another site on an admin's behalf is refused
Observable: An upload request that lacks a valid anti-forgery token, or that is sent by a page on another origin using the admin's session cookie, receives HTTP 403 and creates no import record. This is the rule of the browser's cookie model (the browser attaches the session cookie to cross-site requests), which forces the check.
Source: implied: a bulk-create action authorized by session cookie (runtime rule of browsers).

### C-5: Admin rights are checked again when the users are about to be created
Observable: If the uploading admin has been demoted to `member` or has been set to `deactivated` after the upload was accepted and before the users are created, the import ends with status `failed`, reason `uploader_not_authorized`, and no user from the file exists.
Source: implied: U-5 (import runs after the request), "admins" in the request.

### C-6: The template download is a one-line CSV
Observable: The template download is a UTF-8 text file with exactly one line, `email,name,role`, and no data rows. Uploading it unchanged ends `rejected` with file-level reason `no_data_rows` and creates no user.
Source: implied: U-2.

### C-7: A file must be UTF-8
Observable: A file that is valid UTF-8 is read. A file that is not valid UTF-8 (for example UTF-16, or a binary image renamed `users.csv`) ends `rejected` with file-level reason `invalid_encoding`, and the message says the file must be UTF-8.
Source: choice: Excel and other tools can emit other encodings; refusing silently-garbled names protects the user, UTF-8 is the one encoding every tool can produce.

### C-8: The delimiter is a comma and quoting follows RFC 4180
Observable: Fields are separated by commas; a field wrapped in double quotes may contain commas, doubled double quotes (`""` for one `"`) and line breaks. Records end with LF or CRLF, and a final line terminator is optional: a file with and a file without a trailing line break give the same result.
Source: request: "CSV".

### C-9: Semicolon- or tab-separated files are not converted
Observable: A file whose header line is `email;name;role` (or tab-separated) has no comma, so it is read as one column named `email;name;role` and ends `rejected` with file-level reason `missing_required_column` naming `email` and `name`.
Source: choice: guessing delimiters risks reading the wrong column as the email; refusing is safer and the message tells the admin what was missing.

### C-10: The first non-blank record is the header, and header names are matched loosely
Observable: The first record that is not blank is the header. Each header name is compared to `email`, `name` and `role` after removing leading and trailing whitespace and ignoring letter case, so ` Email `, `NAME` and `Role` are recognised; column order is free, so `name,role,email` works.
Source: choice: spreadsheets produce capitalised, padded headers; the request does not say how columns are identified.

### C-11: `email` and `name` columns are required
Observable: If, after matching, the header lacks `email` or lacks `name` (or lacks both), the import ends `rejected` with file-level reason `missing_required_column`, the message names every missing column, and no row is checked or created.
Source: implied: a user cannot be created without an email address to invite and a name to show.

### C-12: The `role` column is optional
Observable: A file whose header is only `email,name` is accepted and every user in it gets role `member`.
Source: choice: the request does not say what a user has besides identity; an optional column gives admins the choice without making simple files harder.

### C-13: Unrecognised columns are ignored and reported
Observable: Columns whose names are not `email`, `name` or `role` are not stored anywhere; a header `email,name,phone` imports successfully, and the import's detail lists `phone` as an ignored column. Each ignored column is listed once, by the header text as written.
Source: choice: exports from other systems carry extra columns; refusing them would make files harder to reuse, silently dropping them would hide data loss.

### C-14: Two columns that match the same recognised name are refused
Observable: A header in which two or more columns match the same one of `email`, `name`, `role` (for example `email,Email,name`) ends `rejected` with file-level reason `duplicate_column` naming that column, and no user is created.
Source: implied: with two candidate columns the system cannot know which holds the address.

### C-15: Blank lines are skipped
Observable: A line that has no characters or only whitespace is skipped wherever it occurs (before the header, between rows, after the last row). It is not counted among the data rows, and it still counts in row numbering of later rows.
Source: choice: hand-edited and exported files commonly contain blank lines; skipping is harmless and the row number stays equal to the line number in a text editor.

### C-16: A row with a different number of fields than the header is an error
Observable: A row that has more or fewer fields than the header has columns gets one error entry with column left empty and reason `wrong_field_count`; no per-column checks are reported for that row.
Source: implied: with the wrong number of fields the columns cannot be assigned.

### C-17: A malformed quote refuses the whole file
Observable: A double quote that is opened and never closed before the end of the file, or a double quote inside an unquoted field, ends the import `rejected` with file-level reason `malformed_csv`, and the message gives the row number at which the problem was found. No users are created.
Source: choice: a broken quote can swallow following rows into one field; per-row reporting would be unreliable.

### C-18: An empty file is refused
Observable: A file of zero bytes, or one containing only blank lines, ends `rejected` with file-level reason `empty_file`.
Source: implied: U-4.

### C-19: A header without data is refused
Observable: A file that has a header and no data rows ends `rejected` with file-level reason `no_data_rows`, and "0 users created" is shown.
Source: implied: U-4; a "successful" import of nothing would hide a mistaken file.

### C-20: Files larger than 5 MiB are refused, by the server as well as the page
Observable: A file of 5,242,880 bytes (5 MiB) is accepted; a file of 5,242,881 bytes or more is refused with file-level reason `file_too_large`, naming the 5 MiB limit, in the application's own message (not a generic server error page), and no import record is created. A request that bypasses the page and sends such a file is refused in the same way.
Source: choice: 5,000 rows of the longest allowed values is under 2 MiB, so 5 MiB leaves room for quoting and extra columns; the request gives no limit.

### C-21: Files with more than 5,000 data rows are refused
Observable: A file with 5,000 data rows is accepted for validation; a file with 5,001 or more data rows ends `rejected` with file-level reason `too_many_rows`, the message names the limit 5,000, and no row is checked. Blank lines are not counted.
Source: choice: the request gives no limit; 5,000 keeps one import's single all-or-nothing write and the invitation volume within what the runtime handles in about a minute, and larger directories can be split into several files.

### C-22: The file's content decides, not its name or declared type
Observable: A valid CSV named `users.txt`, or sent with a media type other than `text/csv`, is accepted; a file named `users.csv` that is not a CSV of the required form is refused by the reasons above.
Source: choice: operating systems label CSVs inconsistently (for example `application/vnd.ms-excel`).

### C-23: Submitting with no file chosen creates nothing
Observable: Submitting with no file chosen shows a message that a file is required (reason `no_file`) and creates no import record.
Source: implied: U-4.

### C-24: Every field is trimmed before it is checked or stored
Observable: Leading and trailing whitespace is removed from each field, so ` jane@example.com ` is read as `jane@example.com` and `  Jane Doe ` is stored as `Jane Doe`; whitespace inside a value is kept.
Source: choice: padding from hand-editing should not turn a valid row into an error.

### C-25: An empty `email` or `name` is an error
Observable: A row whose `email` or `name` is empty after trimming gets an error entry for that column with reason `missing_required_value`.
Source: implied: C-11, a user needs both.

### C-26: Email addresses must have a valid shape
Observable: After trimming, an email is valid only if all hold: it contains exactly one `@`; the part before it has 1 to 64 characters; the part after it has at least one `.`, no empty dot-separated section (so no leading, trailing or doubled dot) and no `@`; it contains no whitespace and no control character (U+0000–U+001F, U+007F–U+009F); its total length is at most 254 characters. Otherwise the row gets an error for column `email` with reason `invalid_email`. `a@b.co` is valid; `a@b`, `a@@b.co`, `a b@c.co`, `a@b..co` and a 255-character address are not.
Source: choice: the request does not define "valid"; this is the loosest shape that still prevents unusable invitations.

### C-27: Names are 1 to 100 characters
Observable: After trimming, a name of 1 to 100 Unicode characters (code points) is valid; a name of 101 or more gets an error for column `name` with reason `name_too_long`. Names in any script are valid: `Zoë Müller`, `李雷` and `O'Brien-Smith` are accepted.
Source: choice: the request gives no length; 100 is generous for a person's name and bounds display layouts.

### C-28: Names must not contain control characters
Observable: A name containing any control character (U+0000–U+001F, which includes tab and line break, or U+007F–U+009F) gets an error for column `name` with reason `invalid_name_character`, including a name that came from a quoted field with an embedded line break.
Source: choice: control characters in a display name break lists and emails and are never intended.

### C-29: Roles are `member` or `admin`; empty means `member`
Observable: After trimming and ignoring letter case, a `role` value of `member` or `admin` is valid; an empty `role` (or an absent column) gives `member`; any other value (for example `owner`) gets an error for column `role` with reason `invalid_role`. These are the only two roles an import can assign.
Source: choice: the request does not name roles; these are the two the feature needs (ordinary user, and admin to bring in co-administrators), and `member` is the least-privilege default.

### C-30: An email repeated within the file is an error on every later occurrence
Observable: Emails are compared after trimming and ignoring letter case, and no other change (so `a+1@x.co` and `a@x.co` are different, as are dots in the local part). The first row with an address is not flagged for duplication; every later row with the same address gets an error for column `email` with reason `duplicate_in_file`, and the message names the row number of the first occurrence.
Source: implied: U-3; one address means one user.

### C-31: An email that belongs to an existing user is an error
Observable: A row whose email, compared ignoring letter case, equals that of any existing user, in state `invited`, `active` or `deactivated`, gets an error for column `email` with reason `already_exists`. The existing user is not changed.
Source: implied: U-9, "create" means new users; deactivated users keep their address reserved so the address cannot be taken twice.

### C-32: The row-level reason codes are exactly these eight
Observable: Row-level error entries use only: `missing_required_value`, `invalid_email`, `name_too_long`, `invalid_name_character`, `invalid_role`, `duplicate_in_file`, `already_exists`, `wrong_field_count`.
Source: choice: a fixed list lets admins, support and tests refer to errors unambiguously.

### C-33: The file-level reason codes are exactly these
Observable: File-level errors (the whole file is refused) use only: `no_file`, `file_too_large`, `empty_file`, `invalid_encoding`, `malformed_csv`, `missing_required_column`, `duplicate_column`, `no_data_rows`, `too_many_rows`.
Source: choice: same reason as C-32.

### C-34: All errors of all rows are reported, not only the first
Observable: Every error of every row is reported: a row with a bad email and a bad role yields two entries; a file with errors in rows 17 and 42 yields entries for both; a row that is both a duplicate within the file and an existing user yields both entries. The displayed list contains as many entries as the stated total number of errors, with none omitted or merged.
Source: implied: U-3; one pass to fix a file avoids repeated uploads.

### C-35: Each error entry says where and why
Observable: Each entry shows the row number, the column (`email`, `name` or `role`; empty for whole-row errors), the reason code, and a human-readable message. It does not repeat the cell's value.
Source: implied: U-3; choice on omitting the value so that error lists do not spread personal data further.

### C-36: One error means no user is created
Observable: If the import ends `rejected` for any file-level or row-level error, no user from that file exists, including the rows that were valid; the outcome shows "0 users created".
Source: choice: all-or-nothing makes re-uploading a corrected file safe, since it can never meet rows created by an earlier attempt.

### C-37: A clean file creates exactly one user per data row
Observable: When no error exists, the number of users created equals the number of data rows read, each row producing exactly one user, and the import's detail shows that number and ends `succeeded`.
Source: request

### C-38: A created user holds the row's values and starts as `invited`
Observable: Each created user shows, in the user list and the import detail, the email (equal to the CSV value after trimming, ignoring letter case), the name after trimming, the role (`member` or `admin`), the status `invited`, a created-at time, and the import that created them (by import id and uploading admin).
Source: request; implied: U-6.

### C-39: No passwords are taken from the file
Observable: The CSV has no password column: a column named `password` is treated as unrecognised, ignored, and its values are stored nowhere.
Source: implied: U-6; storing passwords from a file would put credentials in spreadsheets.

### C-40: The users of one import appear all together or not at all
Observable: At no moment does the user list show only some of an import's users: before the import reaches `succeeded` none of them is listed, and once it does all are.
Source: implied: C-36; U-5.

### C-41: Cell contents are stored and shown as plain text
Observable: A name such as `=HYPERLINK("http://x")` or `<script>alert(1)</script>` is stored exactly as given and shown literally in every page: no script runs and no markup is interpreted.
Source: implied: file contents are untrusted input.

### C-42: An accepted upload creates an import in status `queued`
Observable: An upload that passes the access, anti-forgery, size and active-import checks creates an import record with a unique id, the file name, the uploading admin and the upload time, shown on the page at once with status `queued`.
Source: implied: U-5; the upload must not depend on a single web request lasting as long as processing.

### C-43: An import's status is exactly one of five values
Observable: An import's status is one of: `queued` (accepted, not started), `processing` (being checked or its users being created), `succeeded` (all users created), `rejected` (file or row errors, nothing created), `failed` (could not be completed for a reason other than the file, nothing created). `succeeded`, `rejected` and `failed` are final and never change afterwards.
Source: choice: a fixed list of states lets the page and tests agree on what is shown.

### C-44: The `failed` reasons are exactly three
Observable: A `failed` import shows one of the reasons `system_error`, `uploader_not_authorized`, `timeout`, together with the statement that no users were created.
Source: choice: same reason as C-32.

### C-45: The open page updates itself
Observable: While the import page or an import's detail is open on an import whose status is not final, the shown status is refreshed without the admin reloading, at intervals of 5 seconds or less, until a final status is shown.
Source: implied: U-5.

### C-46: A maximum-size valid file reaches a final status within 60 seconds
Observable: Under normal load, an import of 5,000 valid rows goes from upload to `succeeded` within 60 seconds. This figure is the target and is unconfirmed against the final deployment.
Source: choice: gives admins a wait they can rely on; the request gives none.

### C-47: An import that does not finish in 10 minutes fails
Observable: An import still `queued` or `processing` 10 minutes after upload (for example because background processing is not running) becomes `failed` with reason `timeout` and no user from it exists. If the end of processing and this timeout coincide, the import ends either `succeeded` with all its users or `failed` with none, never anything between.
Source: choice: no state without an end; 10 minutes is far above C-46's 60 seconds.

### C-48: A system error undoes the whole import
Observable: If the database or another dependency fails while users are being created, the import ends `failed` with reason `system_error`, no user from it exists, and no invitation is sent; uploading the same file again afterwards can end `succeeded` and produces exactly one user per row.
Source: implied: U-10.

### C-49: A restart during processing never duplicates users
Observable: If the application or its background processing restarts while an import is `processing`, the import still reaches a final status (`succeeded` after being run again, or `failed`), and in either case each email of the file belongs to at most one user.
Source: implied: U-10; the runtime restarts processes on deployment.

### C-50: A status always tells the truth about the users
Observable: Whenever an import shows `succeeded`, all its users exist; whenever it shows `rejected` or `failed`, none of its users exist; at no time does the displayed status, the created count and the user list disagree.
Source: implied: "data lost on the way" and "done twice" must never happen.

### C-51: An admin can have only one active import at a time
Observable: While an admin has an import in status `queued` or `processing`, a further upload by the same admin is refused with reason `import_in_progress`, the message names the active import, and no import record is created.
Source: implied: U-9.

### C-52: Different admins can import at the same time
Observable: Two admins each with an active import of their own are both accepted and both proceed; neither is refused for the other's.
Source: choice: the loosest rule that still prevents repeat submissions.

### C-53: Overlapping emails between simultaneous imports never produce two users
Observable: If two imports (by different admins) contain the same email and are processed at the same moment, afterwards exactly one user has that email, one import is `succeeded`, and the other is `rejected` with an `already_exists` error on that row and has created none of its users. Neither import ends `failed` because of this.
Source: implied: U-9.

### C-54: Creating a user by another route during an import never produces a duplicate either
Observable: If a user with an email in the file is created by any other route (for example by hand in user management) after the file was accepted and before its users are created, the import ends `rejected` with `already_exists` on that row, and the user created by the other route is unchanged.
Source: implied: U-9; a uniqueness rule that is checked in only one path.

### C-55: Uploading the same file again after success changes nothing
Observable: Uploading a file whose users were created by an earlier import ends `rejected` with `already_exists` on every row, "0 users created", and no invitation email is sent.
Source: implied: U-9, U-10; "a thing done twice that should happen once".

### C-56: The uploaded file is not kept after processing
Observable: Once an import reaches a final status, no page or address offers the original uploaded file for download.
Source: implied: the file holds personal data in bulk.

### C-57: The import history lists imports newest first
Observable: The history page lists imports of all admins, newest upload first, at most 25 per page with paging to all older ones within the retention period. Each entry shows the file name, the uploading admin (still shown by name if that admin has since been demoted or deactivated), the upload time, the status, the number of rows read (when the file could be read), the number of users created and the number of errors. With no imports at all, the page says there are none. File names are shown as plain text, truncated to 255 characters.
Source: implied: U-5.

### C-58: An import's detail shows the outcome in full
Observable: The detail page shows everything in the history entry plus: for `rejected`, the total number of errors and every error entry (row, column, reason code, message); for `succeeded`, the list of the users created (email, name, role, and each one's invitation delivery); for `failed`, the reason (`system_error`, `uploader_not_authorized` or `timeout`); and for every import whose header was read, the ignored columns.
Source: implied: U-5.

### C-59: Import records expire after 90 days
Observable: 90 days after upload the import record, its error list and its entry in the history are removed; its detail address then shows a "not found" message. The users it created remain, unchanged, and still show the id of the import that created them, which no longer opens.
Source: choice: no state without an end; 90 days covers a quarter's investigations without keeping error data forever.

### C-60: One invitation email per created user, sent only after success
Observable: When an import becomes `succeeded`, each of its users is sent one email at the address in the file, not before the users exist and never for `rejected` or `failed` imports.
Source: implied: U-6.

### C-61: The invitation email carries a set-password link and no password
Observable: The email contains a link to a page where the recipient sets their own password; it contains no password, and no data about any other person.
Source: implied: U-6, C-39.

### C-62: The invitation link works once, for 7 days, for that user only
Observable: A link opens the set-password page for 7 days after it was sent, for the user it was sent to, and stops working after a password has been set with it. A link used after that time, or a second time, or for a user who has since been set to `deactivated`, shows a message that the link is no longer valid and offers no way to set a password.
Source: choice: 7 days is a common window long enough for holidays and short enough to limit exposure.

### C-63: Setting a password makes the user `active` and able to sign in
Observable: After a valid password is set through the link, the user's status becomes `active` and they can sign in with their email (in any letter case) and that password.
Source: implied: U-6.

### C-64: Invitation delivery has one of three states, shown to admins
Observable: Each created user shows an invitation delivery of exactly one of `queued` (not yet handed to the email service), `sent` (accepted by the email service; delivery to the inbox is not known) or `failed` (all attempts refused). Admins see it in the user list and import detail.
Source: implied: U-7.

### C-65: A refused send is retried, 3 attempts in all
Observable: If the email service refuses or cannot be reached, sending is tried again automatically until 3 attempts in all have been made; after the third failure the delivery is `failed`.
Source: choice: bounds the effort and gives a state with an end; the figure depends on the provider.

### C-66: A failed email does not undo or alter the import
Observable: If the email service is not configured or is down, the import is still `succeeded`, its users still exist with status `invited`, and their invitation delivery becomes `failed`.
Source: implied: U-7, U-11.

### C-67: An admin can resend an invitation to a user who is still `invited`
Observable: For a user with status `invited`, whatever the delivery state, an admin can request a resend; a new email is sent with a new link valid 7 days, the delivery shows `queued` then `sent` or `failed` (with up to 3 attempts in all), and the earlier link stops working at once. For a user with status `active` or `deactivated` the resend is refused with a message that the user is not awaiting an invitation, and no email is sent.
Source: implied: U-7.

### C-68: The import limits are fixed
Observable: The values 5 MiB, 5,000 rows, 100-character names, 254-character emails, 10 minutes, 90 days, 7 days and 3 attempts cannot be changed by admins in the application; changing them means a new release of the application.
Source: choice: the request gives no controls, and an admin-editable limit would let one admin enlarge the load for all.

### C-69: A maximum-size upload works through the public address
Observable: Through the address admins use in production, a 5,242,880-byte upload reaches the application and is accepted, as the proxies and gateways in front of it permit request bodies of at least 5 MiB plus form overhead (default limits of 1 MiB and under are common and must be raised). A body over their limit would otherwise give a generic error instead of the application's own `file_too_large` message.
Source: implied: runtime rule of web servers and proxies (request-body caps).

### C-70: Uploads and invitation links travel only over HTTPS in production
Observable: In production, a request to the import pages, the upload or the invitation link over plain HTTP is redirected to HTTPS and carries no file contents or token; invitation links in emails begin with `https://`.
Source: implied: personal data and tokens in transit.

### C-71: Server logs and error reports contain no uploaded personal data
Observable: After importing a file containing the address `canary-7f3a@example.com` and the name `Canary Seven`, searching the application's logs and its error reporting for either string finds nothing; they may contain the import id, counts, reason codes and the uploading admin's identifier.
Source: implied: personal data in bulk; U-11.

### C-72: An import does not hold up the rest of the product
Observable: While an import of 5,000 rows is `processing`, other users can sign in, other pages respond, and the user list can be viewed, each as quickly as when no import runs (no longer than 2 seconds for the user list).
Source: implied: runtime rule: a long write must not lock others out; choice on the 2-second figure.

### C-73: An import never changes an existing user
Observable: No import changes, deactivates, re-roles, renames, re-invites or deletes any user who existed when it was accepted, including a user whose email appears in a row with an `already_exists` error. Every field of such a user, as seen before and after, is identical.
Source: implied: "bulk-create".

### C-74: Every route that creates users applies the same rules
Observable: Wherever else the product lets a user be created (by hand or any other route), the same rules decide validity of email (shape, 254 characters at most), of name (1 to 100 characters, no control characters) and of role (`member` or `admin`), and the same uniqueness rule (ignoring letter case, against all existing users) applies: a value that this import refuses is refused there too, and a value accepted there is accepted here.
Source: implied: "a rule enforced in one path and not another".

### C-75: Import and its users are visible only to admins
Observable: Import history, import detail, error lists and the user lists of imports are visible only to admins; a `member` cannot see them by any address, search or export.
Source: implied: personal data of other people.

### C-76: There is no bulk undo
Observable: The import detail offers no action that deletes, deactivates or reverts all the users of an import; users created by mistake are handled one at a time with the product's existing user management, found through the import detail's user list.
Source: choice: the request asks only for creation; a bulk-delete action is a separate, riskier feature.

### C-77: The import page is usable without a mouse and by screen readers
Observable: The file chooser, submit control, template link, status, error list and resend control can all be reached and operated by keyboard alone; a change of status, and any file-level or row-level error message, is announced by screen readers without the admin having to move focus.
Source: implied: a page used by every kind of admin.

### C-78: A leading byte-order mark is ignored
Observable: A UTF-8 file that starts with the byte-order mark EF BB BF is read as if the mark were absent, so a first header `email` is recognised as `email`.
Source: implied: U-1; Excel's "CSV UTF-8" output starts with one.

### C-79: A user who is still `invited` cannot sign in
Observable: Signing in with the email of a user whose status is `invited`, and any password, is refused with the same message and response as signing in with an address that has no user.
Source: implied: U-6; the refusal must not reveal which addresses were imported.

### C-80: CSV exports of user data neutralise spreadsheet formulas
Observable: If the product produces a CSV export containing user names or emails, a value that starts with `=`, `+`, `-` or `@` is written so that spreadsheet programs treat it as text (for example with a leading apostrophe), so that opening the export does not run a formula. This applies only where such an export exists; this feature does not add one.
Source: implied: file contents are untrusted input.

### C-81: The submit control is disabled while an upload is in flight
Observable: From the moment the admin submits until the upload's response arrives, the submit control cannot be activated again, so a double-click sends exactly one upload.
Source: implied: U-9.

### C-82: Invitation sending does not hold up the import's status
Observable: An import shows `succeeded` as soon as its users exist, even while some of their invitation deliveries are still `queued`.
Source: implied: U-5, U-7; sending through an outside email service is slow and can fail.

### C-83: Invitation links cannot be guessed
Observable: The secret part of an invitation link is random, at least 128 bits (at least 22 base64url characters), and cannot be derived from the user's email, name or id; two links issued to the same user differ.
Source: implied: U-6; a guessable link would allow taking over an account.

### C-84: Invitation passwords follow the product's password rules
Observable: A password chosen through an invitation link that does not satisfy the rules applied to any other password-setting in the product is refused with a message, the user stays `invited`, and the link stays valid.
Source: implied: U-6; a weaker rule in one path would be a hole.

### C-85: Invitation emails of an import all settle within 1 hour
Observable: Under normal operation each invitation of an import reaches delivery `sent` or `failed` within 1 hour of the import becoming `succeeded`. The figure is a target and is unconfirmed against the email provider's sending limits.
Source: choice: gives the state an end; the actual figure depends on the provider.

### C-86: A file with several file-level problems is still refused, naming at least one
Observable: A file that has more than one file-level problem (for example more than 5,000 rows and a missing `email` column) ends `rejected`, no user is created, and the message names at least one of the problems that apply.
Source: choice: which problem is named first is of no consequence to the admin, who fixes and re-uploads.
