## Use cases

### U-1: An admin uploads a valid CSV to create many users at once
Flow: The signed-in admin opens the import-users page, chooses a CSV file whose first record is the header `email,name,role` and whose other records each describe one person, and submits it. The page reports how many users were created. Each person in the file now exists as a user.
Source: request

### U-2: An admin learns what the file must look like before uploading
Flow: On the import-users page the admin reads the accepted columns and limits and downloads a template CSV, fills it in, and uploads it.
Source: implied: "upload a CSV" presumes the admin knows what shape of CSV is accepted

### U-3: An admin uploads a file with bad rows, sees what is wrong, fixes it and uploads again
Flow: The admin submits a file in which some rows are invalid. No users are created. The page lists each problem with its row number, column and reason. The admin corrects the file and uploads it again.
Source: implied: "upload a CSV to bulk-create users" has to say what happens to rows that cannot become users

### U-4: An admin uploads something that cannot be read as a user list at all
Flow: The admin submits an empty file, a header-only file, a file that is not text, a file that is too large, or one with too many rows or a wrong header. The page says the file was rejected and why. No users are created.
Source: implied: the empty case, the largest case and wrong input of "upload a CSV"

### U-5: An admin uploads a file that names people who already have accounts, or uploads the same file twice
Flow: The admin submits a file containing an email address that already belongs to an account (active or not), or repeats an email within the file, or submits the file again after it already succeeded. The page lists the clashing rows. No users are created and no existing user changes.
Source: implied: "create users" when users already exist; the repeated time

### U-6: An admin reviews what past imports did
Flow: The admin opens the import history, sees each import with who ran it, when, the file name, and its outcome, and opens one to see its details.
Source: implied: bulk-creating accounts is something an admin must be able to check afterwards

### U-7: An admin finds out that an invitation did not go out and sends it again
Flow: On an import's detail page the admin sees which created users have an invitation that failed (or have not yet accepted), and re-sends the invitation for one of them.
Source: implied: a created user who is never told they have an account is not usefully created; the mail system can fail

### U-8: A person named in an import accepts their invitation and signs in
Flow: The person receives an email, opens the link, sets a password, and is signed in as a user with the role the CSV gave them.
Source: implied: users bulk-created by an admin must be able to start using their accounts without the admin knowing their password

### U-9: A non-admin or signed-out person tries to import
Flow: A person who is not a signed-in admin opens or submits to the import-users page or its upload address. They are refused. No users are created.
Source: implied: "Let admins" means others are not let

### U-10: Two admins, or one admin twice, import overlapping people at the same time
Flow: Two admins submit files that both contain `kim@example.com` within moments of each other, or one admin double-submits one file. One import completes; the other is rejected and lists the clash. Exactly one `kim@example.com` user exists.
Source: implied: the repeated time and two actors meeting on the same data

### U-11: An operator watches an import and recovers when something fails
Flow: The operator sees one log line per import with its outcome and counts. When an import's connection drops, the request times out, the application restarts, or the mail service is down, the operator finds either a complete import or none, and invitations that did not go out are marked failed for the admin to re-send.
Source: implied: the operator's work (observe, recover); a thing it depends on failing

## Clauses

### C-1: A signed-in admin can reach the import-users page
Observable: A signed-in admin who follows the admin area's navigation reaches a page with a file chooser that takes one file, and a control to submit it.
Source: request

### C-2: The import-users page states the file format and what happens to each created user before upload
Observable: The page, before any file is submitted, shows the accepted column names (`email`, `name`, `role`), which of them is required (`email`), the role values accepted (`member`, `admin`), the limits (1,000 data rows, 2 MiB), and that each user created is sent an invitation email.
Source: implied: U-2

### C-3: The admin can download a template CSV
Observable: A control on the import-users page downloads a file whose content is exactly one record, the header `email,name,role`, and no data rows.
Source: implied: U-2

### C-4: A valid file creates exactly one user per data row
Observable: After a file with N valid data rows (1 ≤ N ≤ 1,000) is submitted and accepted, the product's user list contains N new users, one per row, and no others were added by that submission.
Source: request

### C-5: The success result states how many users were created
Observable: After a successful import the page shows a count equal to the number of data rows in the file.
Source: implied: U-1 ("what they see")

### C-6: Columns accepted, and which are required
Observable: The header may contain only the columns `email`, `name` and `role`. `email` must be present. `name` and `role` may be absent. Columns may appear in any order. Header names are matched ignoring upper/lower case and ignoring leading and trailing whitespace.
Source: choice: the request does not say what columns exist; email is the only field without which a user cannot be created or invited, so it is the only required one

### C-7: A header containing any other column rejects the file
Observable: A file whose header contains a name other than `email`, `name`, `role` is rejected with no users created, and the message names each unrecognised column. A header cell that is empty (as in `email,,role`) counts as an unrecognised column.
Source: choice: silently ignoring a mistyped column (for example `rol`) would create users with the wrong role without telling the admin

### C-8: A header without an `email` column rejects the file
Observable: A file whose header lacks `email` is rejected, no users are created, and the message says the `email` column is missing.
Source: implied: C-6

### C-9: A header naming the same column twice rejects the file
Observable: A file whose header contains the same column name twice (after case and whitespace are ignored) is rejected, no users are created, and the message names the repeated column.
Source: implied: C-6 — with two columns of one name, which value applies is a guess

### C-10: An email value must be a valid address
Observable: In each data row the `email` value, after trimming, is accepted if it has exactly one `@`, a non-empty part before it, and after it a domain with at least one `.` and no whitespace, and is at most 254 characters long. `ada@example.com` is accepted. `ada`, `ada@`, `@example.com`, `ada@@example.com`, `ada@example` and `ada lovelace@example.com` each make that row an error naming column `email`. An empty `email` also makes the row an error naming column `email`.
Source: implied: "create users" by email; the unhappy path of wrong input; choice: the dot-in-domain and 254-character rules, as the loosest checks that keep out values no mail service can deliver to

### C-11: The name value is optional, at most 100 characters, with no control characters
Observable: A `name` of up to 100 characters after trimming is accepted. A `name` of 101 characters makes the row an error naming column `name`. A `name` containing a control character (including a line break or tab) makes the row an error naming column `name`. An absent or empty `name` is accepted and the user is created with no name.
Source: choice: the request gives no name rule; a bound is needed so the value is storable and displayable, and optional is the loosest rule that still creates a user

### C-12: The role value is `member` or `admin`, ignoring case
Observable: A `role` of `member`, `admin`, or either in any capitalisation (for example `Admin`) is accepted. Any other non-empty value (for example `owner`) makes the row an error naming column `role`.
Source: choice: the request names no roles; two is the loosest set that lets the admin create ordinary users and other admins

### C-13: An empty or absent role creates a `member`
Observable: A data row whose `role` is empty, or a file with no `role` column, creates users whose role is `member`.
Source: choice: defaulting to the lower-privilege role means an omission never grants admin rights

### C-14: A row with the wrong number of fields is an error
Observable: A data row with more or fewer fields than the header has columns makes that row an error, naming the row, with the reason that the field count is wrong.
Source: implied: U-3 (wrong input)

### C-15: An email already belonging to an account makes the row an error
Observable: A data row whose email equals, ignoring case, the email of any existing account — including accounts that are deactivated or still awaiting invitation acceptance — is an error naming column `email`. No existing account changes.
Source: implied: U-5; choice: deactivated accounts count because their email remains taken

### C-16: A repeated email within the file makes the later rows errors
Observable: When the same email (ignoring case) appears in several data rows, the first occurrence is judged on its own merits and every later occurrence is an error naming column `email` and the row number of the first occurrence.
Source: implied: U-5

### C-17: Emails are compared and stored in lower case
Observable: A row `Ada@Example.COM` creates a user whose email is shown as `ada@example.com`, and a later upload of `ADA@example.com` is an already-exists error.
Source: choice: email addresses are treated as one identity regardless of capitalisation so a person cannot be created twice by changing case

### C-18: If any row is an error, no users are created
Observable: A file in which at least one row is an error, or which is rejected as a whole, leaves the user list exactly as it was before the submission.
Source: choice: with no bulk undo, a partly applied file leaves the admin to work out which rows landed; all-or-nothing lets them fix the file and upload it again whole

### C-19: Errors name row number, column and reason
Observable: Each row error shows the row number, the column, and a reason.
Source: implied: U-3 ("lists each problem")

### C-89: Row numbers are the record's position from the top of the file, counting empty lines
Observable: In a file whose header is the first record, followed by an empty line and then a record with a bad email, the error names row 3. A record with a line break inside a quoted field counts once. Empty lines before the header are skipped as in C-25 and still count toward row numbers, so a header after one empty line is row 2.
Source: choice: numbering that matches what a spreadsheet shows for the same file lets the admin find the row without counting

### C-91: With no imports yet, the history says so
Observable: An admin who opens the import history before any import has been submitted sees a message that there are none, not an error and not a blank page.
Source: implied: U-6 (the first time)

### C-92: Every entry within the retention period can be reached from the history
Observable: With 120 entries in the history, an admin can reach all 120 from the history page, across pages if it pages.
Source: implied: U-6 (the largest case)

### C-93: Every created user of an import can be reached from its detail page
Observable: For an import that created 1,000 users, an admin can reach all 1,000 emails with their invitation states from the detail page, across pages if it pages.
Source: implied: U-7 (the largest case)

### C-94: A detail page for an import that does not exist says so
Observable: Opening a detail address for an identifier no import has shows a not-found response, not an error and not another import's detail.
Source: implied: U-6 (wrong input)

### C-20: Every invalid field is reported, up to 100 errors
Observable: When a file has up to 100 field errors, every one is listed. When it has more, at least the first 100 are listed and the page states the total number of errors.
Source: choice: listing every problem at once avoids repeated upload cycles; the cap of 100 bounds the page size

### C-21: An empty file is rejected
Observable: A zero-byte file is rejected, no users are created, and the message says the file is empty.
Source: implied: U-4 (the empty case)

### C-22: A file with a header and no data rows is rejected
Observable: A file containing only the header record (or the header and blank records) is rejected, no users are created, and the message says the file has no users in it.
Source: implied: U-4 (the empty case)

### C-23: The CSV format read is comma-separated records with double-quote quoting
Observable: Fields are separated by commas. A field wrapped in double quotes may contain commas and line breaks, and `""` inside it means one double quote. Records end with LF or CRLF; a final record without a line ending is read. `"Lovelace, Ada"` in the `name` column creates a user named `Lovelace, Ada`.
Source: implied: "a CSV" has a meaning that spreadsheets and exporters follow

### C-24: A file with malformed quoting is rejected
Observable: A file in which a double-quoted field is never closed, or a closing quote is followed by something other than a comma or line end, is rejected as a whole, no users are created, and the message gives the row number where the malformed field begins.
Source: implied: U-4 (wrong input)

### C-25: Records that are completely empty are skipped
Observable: A record with no characters (an empty line) between or after data rows is ignored: it creates no user, is not an error, and does not count toward the 1,000-row limit. A record of commas only (`,,`) is not skipped and is an error because `email` is empty.
Source: choice: trailing newlines and spacer lines are common in files saved from spreadsheets and should not fail an otherwise good file

### C-26: Leading and trailing whitespace is trimmed from every value
Observable: A row `  ada@example.com , Ada Lovelace ,member` creates a user with email `ada@example.com` and name `Ada Lovelace`.
Source: choice: hand-edited files have stray spaces that the admin cannot see

### C-27: The file must be UTF-8 text
Observable: A file that is valid UTF-8, with or without a leading byte-order mark, is read, and a `name` of `José` or `李雷` is stored and shown as written. A file containing bytes that are not valid UTF-8 (for example one saved as Windows-1252, or a spreadsheet `.xlsx` renamed) is rejected, no users are created, and the message says the file must be UTF-8 text.
Source: implied: "a CSV" with names in them; U-4 (not text)

### C-28: At most 1,000 data rows
Observable: A file with 1,000 data rows (not counting the header or skipped empty records) is accepted if otherwise valid. A file with 1,001 is rejected, no users are created, and the message states the limit of 1,000.
Source: choice: the request gives no limit; 1,000 fits a synchronous request and is larger than a typical team onboarding

### C-29: At most 2 MiB per file
Observable: A file of 2,097,152 bytes is accepted if otherwise valid. A file of 2,097,153 bytes is rejected, no users are created, and the message states the limit of 2 MiB.
Source: choice: the request gives no limit; far above the size 1,000 valid rows can reach (about 0.4 MB) while bounding what the server must read

### C-30: A file is judged by its content, not by its name or declared type
Observable: A valid CSV named `people.txt`, or sent with the content type `application/vnd.ms-excel` (which some operating systems label CSV files with), is accepted exactly as the same content named `people.csv`.
Source: implied: U-1; "a CSV" is identified by what is in it

### C-31: Submitting with no file chosen creates nothing
Observable: Submitting the form with no file chosen shows a message that a file is required and creates no users and no import record.
Source: implied: U-4 (the empty case of the form)

### C-32: A signed-in non-admin is refused
Observable: A signed-in user whose role is not `admin` who opens the import-users page, downloads the template, opens the import history or an import's detail, requests an invitation re-send, or submits a file to the upload address, receives an access-denied response (HTTP 403) showing none of the page's content, and no users are created.
Source: request ("admins")

### C-33: A signed-out visitor is refused
Observable: A request without a signed-in session to the import-users page, the template download, the history, a detail page, the re-send action or the upload address does not show their content and creates no users; the visitor is sent to sign in.
Source: implied: U-9

### C-34: Admin rights are checked when the file is submitted
Observable: An admin who is demoted to `member` or deactivated, or whose session has ended, after opening the page and before submitting, is refused on submission as in C-32 or C-33, and no users are created.
Source: implied: U-9 (the page can sit open while rights change)

### C-35: Each created user is sent one invitation email
Observable: For each user created by an import, an email arrives at that user's address containing a link for setting a password. A message the mail service has accepted for a user is not sent to that user again by the import.
Source: implied: U-8; the request creates accounts and gives no passwords

### C-36: The invitation link works once and for 7 days
Observable: The link in an invitation can be used to set a password within 7 days of the email's creation. After a password has been set through it, opening it again does not allow setting a password. After 7 days it does not allow setting a password, and shows that it has expired.
Source: choice: a link that never dies is a standing credential in a mailbox; 7 days allows for a person on leave

### C-37: Until the invitation is accepted the user cannot sign in
Observable: A created user who has not set a password cannot sign in; attempts show the same failure as a wrong password.
Source: implied: U-8

### C-38: Accepting the invitation activates the account with the CSV's role
Observable: A person who sets a password through a valid link is signed in, and their account is active with the role `member` or `admin` the CSV row gave and the name from the row.
Source: implied: U-8

### C-39: The password set through an invitation follows the password rules used everywhere else in the product
Observable: A password the product rejects when set anywhere else is rejected here with the same message, and the invitation link stays usable.
Source: implied: U-8

### C-40: An invitation that could not be delivered is shown as failed
Observable: When the mail service refuses or fails 3 consecutive delivery attempts for a user's invitation, that invitation is shown as failed on the import's detail page; the user still exists.
Source: choice: 3 attempts bounds how long an invitation sits unresolved; failure of the mail dependency must not undo accounts

### C-41: An admin can re-send the invitation of a created user who is not yet active
Observable: On an import's detail page each created user who has not yet set a password has a control that sends them a fresh invitation email.
Source: implied: U-7

### C-42: A re-sent invitation replaces earlier ones
Observable: After a re-send, the link in any earlier invitation to that user no longer allows setting a password, and the new link does (for 7 days).
Source: implied: U-7; two live credentials for one person is not wanted

### C-43: Re-sending is refused for a user who is active, deactivated or deleted
Observable: For a created user who has already set a password, or who has been deactivated, or who has been deleted, the detail page shows no re-send control, and a re-send request for them is refused and sends no email.
Source: implied: U-7

### C-44: Every upload by an admin leaves an import record
Observable: After an authorised admin submits a form that contains a file — whether the import completes or the file is rejected for any reason, including being over the size limit — the import history has a new entry. An upload refused for lack of rights (C-32 to C-34) or submitted with no file (C-31) leaves no entry.
Source: implied: U-6

### C-45: The import history lists the entries with who, when, file name and outcome
Observable: Each history entry shows the uploading admin, the submission time, the file name as sent, an outcome of `completed` or `rejected`, and the number of users created (0 for `rejected`).
Source: implied: U-6

### C-46: All admins see all imports
Observable: Any signed-in admin sees every entry in the history, including entries made by other admins.
Source: choice: imports create accounts for the whole organisation, so any admin accountable for those accounts needs to see how they got there

### C-47: An import's detail page shows its contents
Observable: The detail page shows the history fields of C-45, the count of data rows read, and: for a `rejected` import, the error list (or the whole-file reason); for a `completed` import, the email of each created user with its invitation state (`queued`, `sent` or `failed`) and whether the user has since set a password.
Source: implied: U-6, U-7

### C-48: Created users appear in the product's user list with email, name, role and state
Observable: After a completed import, each created user appears in the admin user list with their lower-cased email, their name (empty if none was given), their role, and an account state meaning "invited, not yet active".
Source: implied: U-1 ("now exists as a user")

### C-49: The success result links to the import's detail page
Observable: The page shown after a completed import contains a link that opens that import's detail page.
Source: implied: U-1 and U-7 — the admin must get from the result to the invitation states

### C-50: An account that has been deleted no longer holds its email
Observable: If the product deletes an account outright (as opposed to deactivating it), a later import row with that email is not an already-exists error and creates a user.
Source: choice: only accounts that still exist can clash; the import record still names the earlier creation

### C-51: The file name in the history and detail is shown as sent, up to 255 characters
Observable: A file named with 300 characters shows its first 255 characters; a shorter name shows in full.
Source: choice: the request gives no bound; 255 is the common file-system name limit, so real names are never cut

### C-52: The invitation email contains the set-password link and states that it expires in 7 days
Observable: The email sent to a created user contains a link that opens the page for setting a password, and says the link expires after 7 days. It contains no password.
Source: implied: U-8; C-36

### C-53: Invitation states are `queued`, `sent` and `failed`
Observable: An invitation is `queued` from creation (or from a re-send) until the mail service has accepted the message (then `sent`) or 3 consecutive attempts have been refused or have failed (then `failed`). No other state is shown.
Source: choice: three states are the fewest the admin needs to know what to do

### C-54: Queued invitations are handed to the mail service within 15 minutes when it is healthy
Observable: When the mail service is accepting messages, an invitation is `sent` within 15 minutes of the import completing or of a re-send.
Source: choice: 1,000 messages may be rate-limited by the mail service, so delivery cannot be tied to the upload request; 15 minutes is the longest an admin should wait before being suspicious

### C-55: No invitation stays `queued` for more than 1 hour
Observable: One hour after an import completes (or a re-send), every invitation from it is `sent` or `failed`, including when the mail service has been down throughout. (The 1-hour figure is a choice; the platform's mail provider limits are unconfirmed.)
Source: choice: "queued" must end, so an admin can tell waiting from broken

### C-56: Neither the admin nor anyone else can see an invitation link in the product
Observable: No page of the product (result, history, detail, user list) shows or lets anyone copy an invitation link or token; it is present only in the email to the invited person.
Source: implied: C-36; an admin who could read the link could set the new user's password and act as them

### C-57: Whole-file rejection reasons are exactly nine
Observable: A file is rejected as a whole, with no users created, for exactly these reasons, each shown with a message: the file is empty (C-21); it has no data rows (C-22); its header lacks `email` (C-8); its header has an unrecognised column (C-7); its header repeats a column (C-9); it is not valid UTF-8 (C-27); it is over 2 MiB (C-29); it has more than 1,000 data rows (C-28); its quoting is malformed (C-24). When more than one applies, the message states at least one of them.
Source: implied: U-4; the request leaves open which wrong inputs stop the whole file and which only a row

### C-58: Row errors need not be shown when the file cannot be read as rows
Observable: When a whole-file reason from C-57 other than "no data rows" applies, the page need not list row errors; if it does list them they are correct for the rows that could be read.
Source: choice: a broken header or encoding makes row values meaningless; requiring a full row-error list there would force guesses

### C-59: "Admin" means an active account whose role is `admin`
Observable: An account that is deactivated, or whose role is `member`, or that has not yet accepted its invitation, cannot use any import page or action; an active account with role `admin` can.
Source: implied: "Let admins" presumes a definition of admin

### C-60: History keeps the uploading admin's identity after they leave
Observable: An import entry made by an admin who has since been deactivated or deleted still shows that admin's name and email as they were at submission time.
Source: choice: an audit trail that loses who did it when the person leaves is not an audit trail

### C-61: The page shows that an upload is in progress
Observable: From submission until the response arrives, the page shows an indication that the file is being processed.
Source: implied: U-1; a synchronous upload of 1,000 rows is not instantaneous and a second click must not be taken for a retry

### C-62: Two creations of the same email at once yield one user
Observable: When two imports, or an import and any other way of creating a user, contain the same email (ignoring case) at the same time, exactly one user with that email results. An import that loses is rejected as a whole as in C-18, no users are created by it, and its error list names the clashing row as already existing.
Source: implied: U-10; "duplicate" in the never-twice sense

### C-63: Submitting the same file twice in quick succession creates each user once
Observable: After one file of N valid rows is submitted twice, within a second of each other, exactly N users exist from it, one import entry is `completed` and the other is `rejected`.
Source: implied: U-10; a double-click or a browser retry

### C-64: Admin rights are checked once, when the submission is accepted
Observable: An admin who is demoted or deactivated after their submission was accepted and while it is processing still has that import completed or rejected on its own merits, and the history entry shows them as the uploader.
Source: choice: re-checking mid-way would produce partial states, which C-18 forbids

### C-65: Other admins never see a part of an import
Observable: An admin viewing the user list while an import is in progress sees either none of the users it creates or all of them.
Source: implied: C-18 holds for observers as well as for the data

### C-66: The history entry and the created users appear together
Observable: A `completed` entry exists in the history exactly when the users it lists exist as created by it; no entry is shown for an import that is still being processed.
Source: implied: U-6; a history that disagrees with the user list cannot be audited

### C-67: An interrupted import leaves either all or nothing
Observable: If the connection drops, the request times out, or the application restarts while a submission is processed, then afterwards either every user in the file exists with a `completed` entry, or no user from it exists and there is no `completed` entry for it. An admin who did not see the response can tell which by opening the history.
Source: implied: U-11; the platform can end a request at any moment

### C-68: Queued invitations survive an application restart
Observable: Invitations that are `queued` when the application restarts are still `queued` afterwards and reach `sent` or `failed` within the bound of C-55 counted from the original import.
Source: implied: U-11

### C-69: A retried invitation sends the same link
Observable: When an invitation is attempted again after a refused attempt, the email that finally arrives holds the same link a previous attempt would have held, so one live link per invitation exists.
Source: choice: a retry that mints a new link makes an email that arrives late harmless only by luck

### C-70: No link allows setting a password for an active user
Observable: For a user who has already set a password, opening any invitation link (original or re-sent) shows that the link is no longer valid and changes nothing.
Source: implied: U-7; a re-send racing with acceptance

### C-71: At most one invitation link is live per user at any moment
Observable: Where two admins re-send to the same user at nearly the same time, exactly one of the two links works afterwards, and the user's detail shows one invitation.
Source: implied: C-42 under concurrency

### C-72: An invitation link does not work for a deactivated or deleted account
Observable: Opening the link for an account that has since been deactivated or deleted shows that the link is not valid and no password is set.
Source: implied: U-8; an account taken away between invitation and acceptance

### C-73: The detail page keeps listing created users who have since been deleted
Observable: A user created by the import and since deleted is listed on its detail page with their email as imported and a "deleted" marker.
Source: choice: the audit trail keeps naming who was created; unconfirmed whether privacy rules would require erasing the email, which would have to override this

### C-74: A file over the size limit gets the product's message, not a gateway error
Observable: A file of 2,097,153 bytes, and one of 50 MiB, each produce the C-29 message on the import-users page, never a raw error page from a proxy or server.
Source: implied: the web platform's request-body limit (a default of about 1 MB on common reverse proxies) and the form's own overhead would otherwise reject files the product promised to accept

### C-75: A valid 1,000-row file shows its result within 30 seconds
Observable: Under normal load a valid file of 1,000 rows (and each smaller valid file) shows its completed result within 30 seconds of submission. The 30-second figure is a choice below the platform's request timeout, whose exact value is unconfirmed.
Source: choice: the import is answered in the same request, so it must finish within what a web request is allowed

### C-76: The import pages and upload are served only over HTTPS
Observable: A request over plain HTTP to any import page or action is redirected to HTTPS before any content is returned or any file is accepted.
Source: implied: the file holds people's email addresses and names; what must be true before it can go beyond a development environment

### C-77: An upload not carrying the product's anti-forgery token is refused
Observable: A submission to the upload address from another website's page (without the product's anti-forgery token) creates no users and no import entry and shows an error. The same holds for the re-send action.
Source: implied: U-9; a signed-in admin's browser must not be usable by another site to create accounts

### C-78: Invitation emails come from a sender that passes SPF and DKIM
Observable: Before the feature is released beyond development, an invitation received at a standard mailbox provider shows SPF and DKIM as passing for the sender's domain.
Source: implied: what ships beyond development: unauthenticated mail from bulk invitations is filtered as spam and the invitations never arrive

### C-79: Times in the history and detail are unambiguous about their time zone
Observable: Each time shown includes date and time to the minute and either states its time zone or is in UTC.
Source: choice: admins in different zones read the same history; which zone is left open

### C-80: The uploaded file cannot be retrieved afterwards
Observable: After processing, no page or action of the product returns the uploaded file or any value from it other than those C-47 lists (the created users' emails, row errors and counts).
Source: choice: the file is personal data and holding it serves no use the record does not

### C-81: Import records are kept for at least 365 days
Observable: An import entry and its detail remain viewable for 365 days after its submission time.
Source: choice: long enough to cover an annual access review

### C-82: The operator can see one log line per import with its outcome and counts
Observable: For each import (completed or rejected) the application's log has a line carrying the import's identifier, the uploading admin's account identifier, the outcome, the number of data rows read, and the number of users created.
Source: implied: U-11 (observe)

### C-83: The application's logs hold no email addresses, names or file content from an import
Observable: Searching the application's logs after an import for any email address or name in the file, or for any other cell value, finds nothing.
Source: choice: logs travel to more places than the database and carry no access control per admin

### C-84: Imports do not change any user that existed before them
Observable: For every account that existed before the submission, including the uploading admin's own, the email, name, role, state, password, and signed-in sessions are the same afterwards, whatever the file contained.
Source: implied: "bulk-create": only creating is asked for; U-5

### C-85: A row the product would refuse as an individually created user is refused
Observable: Any value the product refuses when an admin creates a user one at a time (an email form, a name, a role) is also an error in an import row.
Source: implied: a rule enforced in one path and not another

### C-86: Text from the file is shown as text, never as markup or script
Observable: A `name` of `<script>alert(1)</script>` is stored as written and appears literally on the user list, import detail, error messages and the invitation email, and no script runs. Text from the file placed in an error message (an unrecognised column name) is shown the same way.
Source: implied: a file from outside the admin's control is rendered back to admins

### C-87: Users created by an import can be changed and removed like any other user
Observable: An admin can edit, deactivate or delete a user created by an import through the ordinary user management, with no extra restriction; there is no action that undoes a whole import.
Source: choice: bulk undo is a separate feature the request does not ask for; each wrong user can be removed individually

### C-88: Putting the feature in place, or rolling it back, leaves existing data and sign-in unchanged
Observable: After the feature is released, every user who could sign in before still can, with unchanged details. After the application is rolled back to the version before, users created by earlier imports and the import entries are still in the data and the users can still sign in.
Source: implied: the operator's work (carry on with existing data, go back to the version before)

### C-90: The submit control cannot be used again while an upload is in progress
Observable: From submission until the response arrives, activating the submit control a second time sends nothing.
Source: implied: C-61, C-63; a second click must not be taken for a retry
