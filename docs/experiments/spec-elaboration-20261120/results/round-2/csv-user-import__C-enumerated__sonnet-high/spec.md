## Use cases

### U-1: An admin imports a valid CSV to create many users at once
Flow: The admin, signed in as an active admin, opens the Import users page from user administration. They choose a file `people.csv` whose first line is `email,name,role` and whose next lines are `ann@example.com,Ann Lee,member` and `bo@example.com,Bo Chen,admin`, and submit it. They see a result saying 2 users were created, with an import reference. The user list now shows Ann Lee and Bo Chen as pending invitation, and each of the two addresses receives an invitation email.
Source: request

### U-2: An admin prepares a file before uploading
Flow: The admin opens the Import users page and reads which columns exist, which are required, which roles are allowed and what the size and row limits are. They download a template file containing only the header `email,name,role`, fill it in with a spreadsheet or text editor, and save it as CSV.
Source: implied: "upload a CSV" - an admin cannot produce an acceptable file without being told the format

### U-3: An admin uploads a file with problems in some rows and fixes it
Flow: The admin uploads a file in which, for example, record 3 has the email `not-an-email` and record 5 repeats the email on record 2. They see the import was rejected, that no user was created, and a list naming every problem by record number, column and reason. They correct the file and upload it again; this time it succeeds.
Source: implied: "bulk-create users" - a large file will contain mistakes and the admin must be able to find and correct all of them

### U-4: An admin uploads a file that cannot be used at all
Flow: The admin uploads a file that is empty, is a spreadsheet saved as `.xlsx`, has no `email` column, is not UTF-8, is larger than the size limit, or has more rows than the row limit. They see a refusal that says which of these it is, and nothing is created.
Source: implied: "upload a CSV" - what is uploaded is not always a usable CSV

### U-5: Someone who is not an admin, or is not signed in, tries to import
Flow: A signed-in member does not see the Import users page in navigation, and if they request the page or submit a file directly they are refused. A signed-out visitor who requests it is sent to sign in. Nothing is created in either case.
Source: implied: "Let admins" - only admins may

### U-6: An imported person accepts their invitation and signs in
Flow: The person receives the invitation email at the address in the CSV, opens its link, chooses a password, and is then able to sign in as an active user with the role from the file.
Source: implied: "bulk-create users" - a created user has no usable credentials until someone supplies them

### U-7: An admin reviews past imports and one import's details
Flow: The admin opens Import history and sees recent imports, newest first, each with when it ran, who ran it, the file name, the outcome and the counts. They filter to rejected or failed imports, open one, and see its problems or the status of each created user's invitation. If the connection dropped while they were importing, they look here to learn whether the import happened.
Source: implied: "bulk-create users" - someone must be able to find out what an import did, including when the page never answered

### U-8: An admin undoes an import made by mistake
Flow: The admin opens the details of a succeeded import, chooses Undo import, sees how many users will be removed, confirms, and then sees how many were removed and how many were kept because the person had already accepted their invitation.
Source: implied: "bulk-create users" - a mistaken file of 800 people must be reversible

### U-9: An admin gets invitations to people who did not receive them
Flow: The admin opens the details of an import, sees that three invitations are failed or expired, and resends them, one at a time or all at once.
Source: implied: U-6 - email goes astray and links expire

### U-10: An operator turns the feature on for the first time and checks it works
Flow: The operator makes sure email sending is configured, switches bulk user import on, signs in as an admin, sees the Import users entry, downloads the template, uploads a file of one row for a test address, sees the result and the invitation arrive, and then undoes that import.
Source: implied: Pass 3 - a feature that ships off must be switched on and verified

### U-11: An operator changes the limits
Flow: The operator changes the row limit from 1,000 to 500 and the size limit from 5 MiB to 2 MiB; the next time an admin opens the page they see 500 rows and 2 MiB, and a file of 501 records is refused.
Source: implied: C-50, C-51 - the figures are choices that the operator may need to change

### U-12: An operator switches the feature off, for everyone
Flow: The operator switches bulk user import off; admins no longer see the entry and cannot import, while users already created, past import records and invitation links all keep working.
Source: implied: Pass 3 - turning off must be possible without losing anything

### U-13: An operator finds the one failed import among many
Flow: An admin reports "my import said something went wrong, reference 7F3K". The operator searches logs and import history by that reference, finds the one record, and sees its outcome, the admin, the time, the counts and the reason, without seeing any email address or name from the file.
Source: implied: Pass 3 - watching a feature that mostly works

### U-14: The product is upgraded to include this feature, or rolled back from it
Flow: Existing users, roles, sign-ins and the one-user-at-a-time creation behave exactly as before the upgrade. If the operator rolls the product back to the version before, users already created by imports remain and keep working as ordinary users.
Source: implied: Pass 3 - existing data and the way back

### U-15: Two things that touch the same people happen at once
Flow: Two admins upload files that share some addresses at the same moment; or one admin double-clicks Upload; or someone adds one of the addresses by hand while an import runs; or an admin undoes an import while one of its people is accepting their invitation. Afterwards each address belongs to exactly one user and each result the admins saw matches what is in the user list.
Source: implied: Pass 4 - concurrent use of a feature that creates accounts

### U-16: The connection or the product breaks while an import is in flight
Flow: The admin's network drops during the upload, or after the file arrived but before the result was shown, or the product restarts while processing. The admin opens Import history, sees whether the import happened, and re-uploads if it did not.
Source: implied: Pass 4 - uploads of up to 5 MiB over real networks are interrupted

## Clauses

### C-1: The Import users page offers one file field and one submit control
Observable: An active admin who opens the Import users page from user administration sees a field for choosing a single file and a control to submit it; choosing `people.csv` and submitting starts an import of that file.
Source: request

### C-2: The recognised columns are `email`, `name` and `role`
Observable: A file whose header record is `email,name,role` is accepted by the header check; these three are the only recognised column names.
Source: choice: the request names no fields; email identifies the person, name is what is displayed, role decides what they may do, and nothing else is needed to create a user

### C-3: `email` and `name` are required columns, `role` is optional
Observable: A file with header `email,name` is accepted by the header check; a file with header `email,role` or `name,role` is refused for a missing required column.
Source: choice: an account cannot exist without an address and a display name; a role can be defaulted (C-21)

### C-4: Header names are matched ignoring letter case and surrounding spaces, in any order
Observable: A header ` Name , EMAIL ` is accepted and treated as `name,email`, with each record's fields read in that order.
Source: choice: spreadsheet exports vary in case and spacing; refusing them would not help the admin

### C-5: A header containing an unrecognised column name refuses the whole file
Observable: A file with header `email,name,password` is refused, the refusal names the column `password`, and no user is created. A header cell that is empty (as in `email,name,`) counts as an unrecognised column, and the refusal says a column has no name.
Source: choice: silently ignoring a column would let an admin believe a password or another value was applied when it was not

### C-6: A header naming the same column twice refuses the whole file
Observable: A file with header `email,name,Email` is refused, the refusal names the repeated column `email`, and no user is created. Names are compared by the rule in C-4.
Source: choice: with two candidate columns there is no way to know which holds the address

### C-7: A header lacking a required column refuses the whole file
Observable: A file with header `email,role` is refused, the refusal names the missing column `name`, and no user is created.
Source: implied: U-4 and C-3

### C-8: The file is read as comma-separated values with double-quote quoting
Observable: The record `cy@example.com,"Lee, Cy",member` yields the name `Lee, Cy`. A quoted field may contain a line break, so a name written over two lines inside quotes is one name. Inside quotes, `""` is one literal double quote. Records end at LF or CRLF.
Source: implied: "CSV" - the common convention (RFC 4180) is what spreadsheets write

### C-9: UTF-8 text is accepted, with or without a leading byte-order mark
Observable: A file saved by a spreadsheet as "CSV UTF-8" (with a byte-order mark) has its first column recognised as `email`, not as an unrecognised column; the same file without the mark is accepted equally.
Source: implied: "upload a CSV" - the commonest source of CSV files writes a byte-order mark

### C-10: A file with no NUL byte that is not valid UTF-8 refuses the whole file
Observable: A file in Windows-1252 containing the byte `0xE9` on its own is refused with a reason saying the file must be UTF-8, and no user is created.
Source: choice: guessing another encoding would store scrambled names; the admin can re-save as UTF-8

### C-11: A file containing a NUL byte refuses the whole file as not being text
Observable: Any file containing a NUL byte, including an `.xlsx`, other binary file renamed `.csv`, or a UTF-16 file, is refused with a reason saying it is not a text CSV file, and no user is created.
Source: implied: U-4 - binary files uploaded by mistake must not be parsed

### C-12: A file with malformed quoting refuses the whole file and names the record where the problem starts
Observable: Quoting is malformed in exactly two ways: a field opens with `"` and the file ends before the closing `"`, or characters other than `,` or a line end follow a closing `"` (as in `"Ann"x,`). A file with either is refused, the refusal names the record number (C-27) where that field began, and no user is created.
Source: implied: U-3 - quoting errors would otherwise merge records silently

### C-13: Records with no content are skipped
Observable: A record that is empty, or whose every field is empty or only spaces or tabs (such as `,,`), is not an error, creates no user and does not count toward the row limit; a file with such a record between two valid ones creates exactly the two valid users.
Source: implied: spreadsheets write trailing empty rows as `,,`

### C-14: A file with a header and no non-empty data records is refused
Observable: The template file unchanged (header only), and a file of header plus only empty records, are each refused with a reason saying there are no rows to import, and no user is created.
Source: implied: U-4 - the empty case

### C-15: Leading and trailing spaces and tabs are removed from every field before it is checked or stored
Observable: The record `  ann@example.com  ,  Ann Lee  ,member` creates a user with email `ann@example.com` and name `Ann Lee`.
Source: choice: padding is invisible to the admin in a spreadsheet and is never intended

### C-16: `email` must be a plausible address
Observable: A value is accepted only if it has exactly one `@`, at least one character before it, a domain after it containing at least one `.` with characters on both sides, and no spaces or control characters. `ann@example.com` is accepted; `not-an-email`, `a@b`, `a b@example.com` and `a@@example.com` each give an invalid-address row error.
Source: choice: deliverability cannot be proved at upload, so only the plainly malformed are refused

### C-17: `email` may be at most 254 characters
Observable: An email of 254 characters is accepted when otherwise valid; one of 255 characters gives a too-long row error.
Source: choice: 254 is the standard maximum length of an address

### C-18: `name` is required and must be 1 to 100 characters after trimming
Observable: A name of 1 character is accepted; an empty name gives a missing-value row error; a name of 100 characters is accepted; one of 101 characters gives a too-long row error. Characters are counted as Unicode code points.
Source: choice: the request gives no name rule; 100 is generous for a display name and bounds the stored size

### C-19: `name` may not contain control characters or line breaks
Observable: A name written over two lines inside quotes (C-8) gives an invalid-characters row error; a name containing a tab character gives the same error.
Source: choice: a display name containing line breaks breaks lists and emails

### C-20: `role` must name a role the product defines, ignoring letter case
Observable: `member`, `Member` and `ADMIN` are accepted; `superuser` gives an invalid-role row error whose reason lists the allowed roles. The allowed roles at this specification are `member` and `admin`; if the product defines further user roles, each of those is also allowed (the full role list of the product is unconfirmed).
Source: choice: the request names no roles; accepting a role the product does not define would create an account that cannot work

### C-21: A blank `role`, or no `role` column, gives the role `member`
Observable: The record `ann@example.com,Ann Lee,` and the same record in a file with header `email,name` each create Ann Lee with role `member`.
Source: choice: the least-privileged role is the safe default when the file says nothing

### C-22: A record whose number of fields differs from the header's gives a row error
Observable: With header `email,name,role`, the record `ann@example.com,Ann Lee` and the record `ann@example.com,Ann Lee,member,x` each give a wrong-field-count row error.
Source: implied: C-8 - a short or long record cannot be mapped to columns

### C-23: An email repeated within the file gives a row error on every later occurrence
Observable: If records 2 and 5 both hold `ann@example.com` (or `Ann@Example.com`), record 5 gets a duplicate-in-file row error naming record 2, and record 2 has no error for that reason. Addresses are compared ignoring letter case, and only records whose address passed C-16 and C-17 take part: two records both holding `bad` get the invalid-address error each and no duplicate-in-file error.
Source: implied: U-3 - one person cannot be created twice

### C-24: An email that already belongs to an existing user gives a row error
Observable: If a user with `ann@example.com` already exists, whether active, pending invitation, deactivated or locked, a record with `ann@example.com` or `ANN@example.com` gives an email-in-use row error. The error says only that the address is in use, and never the existing user's name, role, status or organisation.
Source: implied: "bulk-create" - existing accounts must not be duplicated or overwritten

### C-25: If any problem is found, no user is created
Observable: A file of 50 records with a single invalid email, or any file refused under C-5 to C-14, leaves the user list exactly as it was and shows the import as rejected.
Source: choice: partial imports leave the admin unable to tell who was created and make a corrected re-upload collide with the first one

### C-26: If there is no problem, exactly one user is created for each non-empty data record
Observable: A file with 3 valid non-empty data records and 2 empty records creates 3 users, and the result states 3 created.
Source: request

### C-27: Record numbers count from the header as record 1 and include empty records
Observable: Every record number in a message counts the header as 1, the first data record as 2, and counts empty records, so the number equals the row number a spreadsheet shows for that row, and a record containing quoted line breaks is still one record.
Source: implied: U-3 - the admin must find the same row in their spreadsheet

### C-28: Every problem in the file is reported, not just the first
Observable: A file with invalid emails in records 3 and 9 and an invalid role in record 12 shows three row errors; correcting only record 3 does not hide the other two.
Source: implied: U-3 - one error per upload would force many round trips

### C-29: Each row error states the record number, the column and the reason
Observable: Each row error shows a record number, the column name (`email`, `name`, `role`) or, for a wrong field count, no column, and a reason. A record with two problems shows two errors.
Source: implied: U-3

### C-30: Row error reasons are exactly these distinct reasons
Observable: A row error is one of: a required value is missing; the email is not a plausible address; a value is too long (email over 254 or name over 100 characters); the name contains disallowed characters; the role is not allowed; the record has the wrong number of fields; the email repeats an earlier record in the file; the email is already in use; the email or other value is refused by a rule the product applies when an admin creates one user by hand (C-70). Each reason is distinguishable from the others to the reader; the wording is not fixed.
Source: implied: C-16 to C-24 and C-70

### C-31: File-level refusal reasons are exactly these distinct reasons
Observable: A refusal of the whole file is one of: no file was attached; more than one file was attached; the file is empty (zero bytes, C-125); the file is not UTF-8 text (C-10, C-11); quoting is malformed (C-12); the header is missing (C-126); the header has an unrecognised column (C-5); the header repeats a column (C-6); the header lacks a required column (C-7); there are no rows to import (C-14); the file exceeds the size limit (C-50); there are more data records than the row limit (C-51); the import would exceed the product's user limit (C-72); imports are switched off (C-76); imports are unavailable because email sending is not configured (C-78); the admin has made too many imports recently (C-56). Each is distinguishable from the others; the wording is not fixed.
Source: implied: U-4

### C-32: Only an active user with the role `admin` may import
Observable: A user who is signed in, whose status is active and whose role is `admin` can open the page and submit. A user with role `admin` whose status is pending invitation, deactivated or locked is refused as in C-34; so is any active user with another role.
Source: implied: "Let admins" - the states in which an admin account does not count as an admin are listed because an account in them cannot act

### C-33: The Import users entry is not shown to anyone who may not import
Observable: A signed-in member looking at user administration (or anywhere else in navigation) sees no Import users entry.
Source: implied: U-5

### C-34: A submission or page request from a signed-in user who may not import is refused with a forbidden response
Observable: A member who requests the Import users page, the template download, an import's details or an undo, or who submits a file, receives a forbidden response; no file content is read and no user is created.
Source: implied: U-5 - hiding the entry is not enforcement

### C-35: A signed-out request is not served
Observable: A signed-out visitor who requests the Import users page is sent to sign in; a signed-out submission of a file is refused as unauthenticated, nothing is created, and after signing in as an admin the file is not submitted on their behalf.
Source: implied: U-5

### C-36: Eligibility is checked when the file is received, not only when the page was opened
Observable: An admin who opens the page, is then demoted to member or deactivated by another admin, and then submits the file is refused as in C-34, and no user is created.
Source: implied: C-32 - the page can stay open for hours

### C-37: Imported users are created in the importing admin's own organisation
Observable: Users imported by an admin of organisation A appear in A's user list and in no other organisation's. If the product has a single organisation, they appear in that one.
Source: implied: "bulk-create users" - an admin's authority reaches only their own organisation; the product's organisation model is unconfirmed

### C-38: A created user holds these fields from the file and from the import
Observable: Each created user has: the email, the name, the role (C-20, C-21), the status pending invitation, the time of creation, and a reference to the import that created it and to the admin who ran that import. A user list or user detail view shows the email, name, role, status and the import reference.
Source: implied: "bulk-create users" and the need to trace a user to its import (C-83)

### C-39: A newly created user cannot sign in, and has no password
Observable: Immediately after an import, attempting to sign in as `ann@example.com` with any password, including an empty one and the email itself, fails. Nothing in the product, the result page, the logs or any email contains a password for that user.
Source: implied: U-6 - credentials are set by the person, never issued by the admin

### C-40: Created users are visible in the user list as soon as the result is shown
Observable: The moment the success result appears, loading the user list shows every user it reports as created.
Source: implied: U-1

### C-41: A successful import shows how many users were created
Observable: After the import of U-1 the result shows the number 2 as the count of users created.
Source: implied: U-1 - the admin needs confirmation of what happened

### C-42: A rejected import shows that it was rejected, that nothing was created, and the problems
Observable: After the upload of U-3 the result states the import was rejected, states that 0 users were created, and shows the problems.
Source: implied: U-3, C-25

### C-43: The page lists at most the first 100 row errors and states the total
Observable: A file with 250 row errors shows 100 of them in file order and states that there are 250 in total; a file with 3 shows all 3 and the total 3.
Source: choice: a page of 1,000 errors is unreadable; 100 fits on a screen or two

### C-44: The full list of row errors can be downloaded as a CSV file
Observable: From a rejected result the admin can download a CSV whose header is `record,column,reason` and which has one line per row error, all of them (250 lines for the file in C-43).
Source: choice: the admin needs every error to fix a large file; the column names are fixed so the file can be opened in a spreadsheet

### C-45: Row errors never repeat the values from the file
Observable: A row error for the email `secret@example.com` in record 4 shows record 4, the column `email` and a reason, and does not contain `secret@example.com` anywhere on the page, in the downloaded error list, or in logs.
Source: choice: the file holds personal data; the record number is enough to find the cell

### C-46: A header name shown in a refusal is shown as literal text
Observable: An unrecognised header name (C-5) appears in the refusal on the page as plain characters, so a header named `<script>alert(1)</script>` shows those characters and runs nothing.
Source: implied: C-5 - header names are admin-supplied and echoed, so they reach a page

### C-47: Names, emails and file names from an upload are always displayed as plain text
Observable: A user imported with the name `<b>x</b>` shows the characters `<b>x</b>` in the user list, the result, the import details and the invitation email, and no formatting or script is applied; an import of a file named `<i>x</i>.csv` shows that name literally in Import history.
Source: implied: C-18 - the name rule does not exclude markup characters

### C-48: A template file can be downloaded
Observable: The page offers a download whose content is exactly the one line `email,name,role` (followed by a line break), and uploading it unchanged is refused as in C-14.
Source: choice: gives the admin a correct starting point; with no example row nothing can be imported by mistake

### C-49: The page states the format and the limits currently in force
Observable: The page names the columns `email`, `name` and `role`, says which are required, lists the allowed roles, and states the current size limit and row limit as numbers (5 MiB and 1,000 rows at defaults); after an operator changes a limit (C-79), the next page load shows the new number.
Source: implied: U-2

### C-50: A file larger than the size limit is refused before it is read as CSV
Observable: At the default limit of 5 MiB (5,242,880 bytes), a file of exactly 5,242,880 bytes passes the size check and one of 5,242,881 bytes is refused with a too-large reason that states the limit; no user is created.
Source: choice: the request gives no size; 5 MiB is far above 1,000 ordinary rows (about 100 KB) and keeps memory use bounded

### C-51: A file with more than the row limit of non-empty data records is refused
Observable: At the default limit of 1,000, a file with 1,000 non-empty data records passes the row-count check and one with 1,001 is refused with a too-many-rows reason that states the limit and the count found; no user is created and no row errors are reported for it.
Source: choice: the import runs while the admin waits (C-86), so it must be bounded; 1,000 covers a typical team or class

### C-52: Submitting with no file chosen is refused
Observable: Pressing submit with no file chosen, or with a file field that arrives empty of a file part, shows a no-file-attached refusal and creates no user.
Source: implied: C-1

### C-53: Submitting more than one file is refused
Observable: A request carrying two files shows a more-than-one-file refusal, neither is read, and no user is created.
Source: implied: "upload a CSV" - singular; merging two files has no defined meaning

### C-54: A file is judged by its content, not by its name or declared type
Observable: A valid CSV named `people.txt`, `people` or `PEOPLE.CSV`, and sent with any declared media type, is accepted; a binary file named `people.csv` is refused under C-11.
Source: choice: operating systems and browsers label CSV files inconsistently

### C-55: When the whole file is refused, no row errors are shown
Observable: A file with an unrecognised column and also an invalid email in record 3 shows the unrecognised-column refusal and no row error for record 3.
Source: choice: rows cannot be mapped to columns when the header is wrong, so row errors would mislead

### C-56: An admin may submit at most 30 imports in any rolling hour
Observable: A submission counts from the moment it is accepted for processing, that is, when it will produce an import record (C-83). An admin whose 30 most recent counted submissions all fall within the last 60 minutes and who submits a 31st is refused with a too-many-imports reason that says when they may try again; nothing is created. A submission refused for this reason does not itself count, so waiting always ends the refusal.
Source: choice: bounds abuse and runaway scripts; 30 leaves ample room for fix-and-retry on a bad file

### C-57: An invitation email is sent to each created user after the import succeeds
Observable: After the import of U-1, `ann@example.com` and `bo@example.com` each receive one invitation email, addressed to that address only.
Source: implied: U-6, C-39 - the only way in for a person with no password

### C-58: No invitation email is sent for an import that created nothing
Observable: After a rejected import (U-3) or one that fails with an internal error (C-84), no email goes to any address in the file.
Source: implied: C-25 - an invitation to an account that does not exist would be a dead end and a leak

### C-59: The invitation contains a single-use link to set a password and no password
Observable: The email contains one link; opening it shows a form for choosing a password. The email's text contains no password for the user.
Source: implied: C-39

### C-60: An invitation link works for 7 days after it was issued
Observable: A link issued at 10:00 on day 0 works at 09:59 on day 7 and is refused at 10:01 on day 7. A resend (C-68) issues a link with its own 7 days.
Source: choice: long enough to survive a weekend or leave, short enough to limit a leaked email's risk

### C-61: Each created user's invitation has exactly one of these statuses: queued, sent, failed, expired, accepted
Observable: In the import details each created user shows one of: queued (not yet handed to the mail system), sent (handed over without error and the link still within 7 days), failed (all attempts in C-62 refused), expired (sent but 7 days have passed without acceptance), accepted (the person has set a password).
Source: implied: U-1 - the admin must be able to tell who still needs a nudge

### C-62: A failed send is retried so that each send of an invitation (the first, and each resend) is attempted at most 3 times in all
Observable: With the mail system refusing every message, a user's invitation status goes from queued to failed after the third refused attempt, and not before; with a refusal on the first attempt and success on the second, the status is sent and exactly one email is delivered.
Source: choice: absorbs brief mail outages without retrying forever

### C-63: A failed invitation never removes or changes the created user
Observable: With the mail system down, the import still shows as succeeded, the users still appear pending invitation in the user list, and the failures show as failed invitations in the import details.
Source: implied: C-25 - creation and delivery are separate outcomes

### C-64: The import result does not wait for invitation emails to be delivered
Observable: With the mail system taking 60 seconds per message, the result of a 1,000-row import still appears within the time in C-86, with invitations shown as queued.
Source: implied: C-86 - a slow mail system must not break the wait

### C-65: A person who follows a valid invitation link and sets a password becomes an active user with the imported role
Observable: Ann opens her link, enters a password the product's existing password rules accept, submits, and can then sign in as `ann@example.com` with that password; her status shows active, her role is the one from the file, and her invitation status shows accepted.
Source: implied: U-6

### C-66: An invitation link can be used once
Observable: After Ann has set her password, opening the same link again shows that it is no longer valid and does not change her password.
Source: implied: C-59 - links in email are forwarded and kept

### C-67: An expired or replaced link is refused and tells the person to ask their admin
Observable: Opening a link after 7 days, or a link replaced by a resend, shows a message that the link is no longer valid and that they should ask an administrator to send a new invitation; the account is unchanged.
Source: implied: C-60, C-68

### C-68: An admin can resend the invitation to a created user who is still pending
Observable: From the import details, the admin chooses Resend for a user whose invitation status is queued, sent, failed or expired; a new email with a new link is sent, the status shows queued, then sent, the new email gets its own 3 attempts (C-62), and the previous link stops working.
Source: implied: C-60, C-61 - someone will lose or miss the email

### C-69: Resend is not available for a user who has accepted, or whose import was undone
Observable: In the import details, a user with status accepted shows no Resend control, and a resend request for such a user, or for a user removed by an undo (C-71), is refused and sends no email.
Source: implied: C-68

### C-70: Every rule the product applies when an admin creates one user by hand also applies to each record
Observable: A value the one-user form refuses (for example an email outside an allowed domain list, an email on a blocklist, or a name that form's rules refuse) gives the row error "refused by a product rule" (C-30); where the one-user form's rule for email, name or role is stricter than C-16 to C-20, the stricter rule applies to imports. A value the one-user form accepts and C-16 to C-20 accept is not refused for a product-rule reason. The one-user form's rules are unconfirmed at this specification.
Source: implied: "bulk-create users" - a rule enforced on one path and not the other would be a loophole

### C-71: An admin can undo a succeeded import, which removes the users it created who are still pending invitation
Observable: From the details of a succeeded import, any active admin of the same organisation (not only the one who ran it) can choose Undo import. After it, each user of that import whose status was pending invitation at that moment is gone from every user list, their email address can be imported or created again, their invitation links no longer work, and invitation emails still queued for them are not sent.
Source: implied: U-8, "undo something it did by mistake"; choice: any admin of the organisation may undo, not only the one who ran it, because that admin may be away

### C-72: An import that would take the organisation over its user limit is refused whole
Observable: Where the product limits the number of users an organisation may have, a file whose creation would exceed that limit is refused with a user-limit reason stating how many more users may be added; no user is created. Where the product has no such limit this clause has no effect (whether the product has one is unconfirmed).
Source: implied: "bulk-create users" - a limit that holds for one-at-a-time creation holds in bulk

### C-73: Undo asks for confirmation first, showing how many users it will remove
Observable: Choosing Undo import shows a screen stating the number of users that would be removed now (the count still pending invitation) and has Confirm and Cancel; leaving the screen or choosing Cancel removes no one.
Source: implied: U-8 - removal is destructive

### C-74: Undo never removes a user whose status is not pending invitation
Observable: If Bo accepted his invitation before the undo, Bo is still in the user list, still active, with his role, after the undo; the same holds for any user of the import now deactivated or locked. The outcome states the number removed and the number kept.
Source: implied: U-8 - a person who has set a password may already have data and sessions

### C-75: Repeating an undo is harmless
Observable: Confirming Undo import a second time, or in two browser windows at once, removes no one further, shows no error, and states 0 removed; no user is removed twice and none is kept that the first undo removed.
Source: implied: Pass 4 - double submission

### C-76: The operator can switch bulk user import off, and while it is off nothing that creates, undoes or invites is possible
Observable: With the switch off, the Import users entry is not shown, and a request for the page, the template, a submission, an undo or a resend is refused with the imports-switched-off reason (C-31); no user is created, removed or emailed. Import history and import details stay viewable.
Source: implied: U-12 - a feature that creates accounts in bulk must be stoppable without losing anything

### C-77: A change of the switch applies to the next request, with no restart
Observable: After the operator saves the switch as on, the next page load by an admin shows the Import users entry; after saving it as off, the next submission is refused. An import already being processed when the switch turns off finishes under the setting it started with.
Source: implied: U-10, U-12 - the operator must see the configuration take effect

### C-78: Imports are unavailable while email sending is not configured
Observable: With the switch on but no way to send email configured, the page shows that imports are unavailable and why (the email-not-configured reason of C-31); submissions are refused, and no user is created.
Source: implied: C-39 - users created without any means of invitation can never sign in

### C-79: The operator can set the row limit and the size limit
Observable: The row limit defaults to 1,000 and the size limit to 5 MiB. After the operator saves 500 and 2 MiB, the next page load shows 500 and 2 MiB (C-49), a file of 501 records is refused under C-51 and a file of 2 MiB plus 1 byte under C-50.
Source: implied: U-11, C-50, C-51

### C-80: A limit outside its allowed range is refused when saved and the previous value stays
Observable: The row limit must be from 1 to 10,000 and the size limit from 1 KiB to 10 MiB (10,485,760 bytes). Saving 0 or 10,001 rows, or 20 MiB, shows an error naming the allowed range, and the page continues to show the previous values.
Source: choice: the import is synchronous (C-86); the ceilings keep it within its time bound

### C-81: Import history lists recent imports, newest first, filterable by outcome
Observable: Any active admin of the organisation sees imports whose records still exist (C-88), newest first, in pages so that every record is reachable, each row showing: when it finished (with its time zone), the admin who ran it, the file name, the outcome, the number of records, the number created and the number of errors. The list can be limited to one outcome (succeeded, rejected or failed) and can be searched by import reference.
Source: implied: U-7, U-13

### C-82: Import details show everything the admin needs to act
Observable: An import's details show its reference, admin, time, file name, outcome and undo state. For a succeeded import, they list every created user (in pages) with email, name, role, user status and invitation status, with Resend (C-68) and Undo (C-71) controls. For a rejected import, they show the file-level reason, or the row errors as in C-43 and C-44. For a failed import, they show that it failed and the reference.
Source: implied: U-7, U-8, U-9

### C-83: Each import leaves a record with these fields and one of these outcomes
Observable: The record holds: the reference; the admin; the organisation; the finish time; the file name as sent, cut to 255 characters; the file size in bytes; the outcome, exactly one of succeeded (users created), rejected (the file or rows were refused and nothing was created) or failed (an internal error and nothing was created); the number of non-empty data records read; the number created; the number of errors; for a rejected import its file-level reason or its row errors (record, column, reason, never values); the undo state, exactly one of not undone, undone (every created user removed) or partly undone (at least one kept); the identity of the users it created, each with its record number in the file; the time and admin of an undo; and the time, admin and user of each resend.
Source: implied: U-7 - audit and diagnosis

### C-84: An internal error leaves nothing created, shows a reference, and is recorded as failed
Observable: If the product fails during an import (the database becomes unreachable, for example), the admin sees a message that something went wrong, that no users were created, and a reference; the user list is unchanged; no invitation is sent; the import appears in history as failed when the product is able to record it.
Source: implied: C-25 - atomicity holds when the product itself breaks

### C-85: The uploaded file's contents are not kept after the request ends
Observable: Once the response has been sent, the file's contents (emails, names) exist nowhere in the product except as the users created from them: not in the import record, not in logs, not in temporary storage on the server.
Source: choice: the file is personal data and nothing needs it afterwards (C-83 keeps counts and error positions)

### C-86: An import of a file at the limits answers within 30 seconds
Observable: With the default limits, and equally with the largest limits C-80 allows (10,000 records, 10 MiB), an admin submitting a file at the limit is shown its result (success or rejection) within 30 seconds of the upload finishing, and the page shows the import is in progress meanwhile. The platform's own request timeout is unconfirmed; 30 seconds is a choice under the 60 seconds common for web proxies.
Source: choice: the request does not say whether the admin waits; waiting is simpler for the admin than polling, and the limits make it possible

### C-87: Each import writes one structured log line giving its outcome and counts, never its contents
Observable: When an import finishes, the product's log gets one entry carrying the reference, the admin's identifier, the outcome, the numbers of records, created users and errors, and the duration in milliseconds. It contains no email address, no name and no cell value from the file.
Source: implied: U-13 - the operator watching a running feature

### C-88: Import records are kept for 90 days and then deleted
Observable: An import record, its error list and its details become unavailable 90 days after the import finished; the users it created are unaffected, and in their detail the import reference shows that the record has expired. Undo (C-71) for that import is no longer possible after that.
Source: choice: gives all state an end; 90 days covers the time in which a mistaken import is noticed

### C-89: Each failed invitation attempt is logged without the address
Observable: A refused attempt (C-62) writes a log entry with the import reference, the user's identifier, the attempt number (1, 2 or 3) and the mail system's error category; the entry does not contain the email address.
Source: implied: U-13 - to find out why invitations failed

### C-90: The operator can see how many imports ended in each outcome and how long they took
Observable: Through the product's existing operational monitoring (its surface is unconfirmed), for any chosen period the operator can read the number of imports that were succeeded, rejected and failed, and the median and longest duration, and can alert on failed imports.
Source: implied: U-13 - a rise in failed imports is the signal that something broke

### C-91: The upgrade changes nothing about users that exist before it
Observable: After the upgrade, every pre-existing user has the same email, name, role, status, password and sessions as before, signs in as before, and shows no import reference (shown as not created by import).
Source: implied: U-14 - carrying on with existing data

### C-92: Creating one user by hand behaves as before the upgrade
Observable: The existing one-user form accepts and refuses the same inputs with the same messages as before, and a user it creates shows no import reference.
Source: implied: U-14

### C-93: Switching the feature off removes nothing and breaks nothing
Observable: After switching off, every created user is still in the user list, every import record is still listed, and invitation links already issued still work and activate the account; invitation emails queued before the switch-off are still delivered.
Source: implied: U-12

### C-94: Rolling the product back to the version before leaves imported users in place
Observable: After rollback, the user list loads without error, shows the imported users, and invitation links already sent still let the person set a password and sign in. The imported users' status is shown by whatever the earlier version calls an account without a password (its exact display is unconfirmed). Import records are kept so a later re-upgrade shows them again.
Source: implied: U-14 - the way back

### C-95: The operator has exactly three controls: the switch, the row limit and the size limit
Observable: The settings area offers the switch (C-76), the row limit and the size limit (C-79). It offers no separate control for the invitation lifetime (7 days), the invitation attempts (3), the hourly submission limit (30), the retention period (90 days) or the number of errors shown (100); those are fixed values in this specification. It has no switch for one admin alone: an admin loses the ability only by losing eligibility (C-32).
Source: choice: each extra control is another thing to misconfigure; the fixed values are listed so none is silently assumed configurable

### C-96: When two imports contain the same address at once, the address is created once and the other import is rejected whole
Observable: Admins X and Y submit files at the same moment, both containing `ann@example.com`. Afterwards exactly one `ann@example.com` user exists; the import that created it shows succeeded; the other shows rejected with an email-in-use row error on its record for that address and created none of its other users. Both results appear within the time in C-86.
Source: implied: Pass 4 - C-24 and C-25 must hold when the existing user appears while the import runs

### C-97: Submitting the same file twice creates each user once
Observable: After an admin submits `people.csv` successfully and then submits it again (by double-clicking, reloading the result page and accepting the resubmission, or later), the second import is rejected with an email-in-use row error on every record, and the user list holds exactly one user per address.
Source: implied: Pass 4 - repetition

### C-98: The form cannot be submitted again while its submission is in progress
Observable: After the admin presses submit, the submit control is disabled and the page shows that the import is in progress until the result arrives; a second press sends no second request.
Source: implied: C-86, C-97 - the wait can be tens of seconds

### C-99: When an import and the one-user form add the same address at once, exactly one user results
Observable: While an import containing `ann@example.com` is running, an admin adds `ann@example.com` with the one-user form: afterwards there is exactly one such user; if the form's user was created first, the import is rejected whole with an email-in-use row error on that record; if the import's was first, the form refuses the address as already in use.
Source: implied: Pass 4 - two paths to the same state

### C-100: An email address can belong to only one user in the whole product
Observable: If `ann@example.com` is a user of organisation B, an admin of organisation A importing `ann@example.com` gets an email-in-use row error that, as in C-24, reveals nothing about that user or organisation.
Source: choice: sign-in is by address, so one address cannot be two accounts; the product's organisation model is unconfirmed

### C-101: An undo and an acceptance of the same invitation at once end in one consistent state
Observable: Bo opens his link and submits his password at the same moment an admin confirms Undo import. Afterwards either Bo is removed, his link is refused and he cannot sign in, or Bo is active, kept, can sign in with his new password and is counted as kept in the undo's outcome. He is never both gone and able to sign in, and never active but absent from the user list.
Source: implied: Pass 4 - C-74 and C-65 meeting

### C-102: Two simultaneous uses of one invitation link set the password once
Observable: Two submissions of the password form from the same link at the same moment: exactly one is accepted and its password is the one that works to sign in; the other shows the link is no longer valid.
Source: implied: C-66 under concurrency

### C-103: Resending to the same user more than once within one minute sends one email
Observable: Pressing Resend for Ann twice within 60 seconds, or Resend-all twice, results in one invitation email to Ann carrying the newest link; the second request shows that an invitation was just sent.
Source: choice: protects a person's inbox from repeated clicks; the figure of one minute is a decision

### C-104: Invitation statuses change only by these transitions
Observable: queued becomes sent when handed to the mail system; queued becomes failed after the third refused attempt (C-62); sent becomes accepted when the person sets a password; sent becomes expired when 7 days pass (C-60); failed and expired each become queued by a resend; sent and queued each become queued by a resend (C-68). accepted is final. No other change occurs; a user's status in the import details never shows a value outside the five of C-61.
Source: implied: C-61 - the dimension of states is listed with every way out of each

### C-105: The hourly limit holds when submissions arrive together
Observable: When an admin with 29 accepted submissions in the last hour sends 5 submissions in the same instant, at most 1 is accepted for processing and the other 4 are refused under C-56.
Source: implied: C-56 under concurrency

### C-106: An import runs under the limits in force when its file was received
Observable: If the operator lowers the row limit from 1,000 to 500 while a 900-record file is being processed, that import completes under 1,000; the next 900-record file is refused under C-51.
Source: implied: C-77, C-79

### C-107: An admin losing eligibility after the file was received does not stop that import
Observable: An admin demoted or deactivated after the file arrived and before processing ends still has the import completed and recorded under their name; they cannot start another (C-36).
Source: choice: aborting halfway would need a rollback path of its own; the import is already atomic and the admin was eligible when it began, and any admin can undo it (C-71)

### C-108: A connection lost before the whole file has arrived creates nothing and leaves no record
Observable: If the upload is cut off at 60% of the file, no user is created, no invitation is sent, no import record appears in history, and re-uploading the whole file is safe.
Source: implied: U-16

### C-109: A file that has fully arrived is carried to its outcome even if the admin is no longer there
Observable: If the admin closes the page or loses connection after the file arrived, the import still ends as succeeded, rejected or failed, and appears in Import history with that outcome within 60 seconds of the file arriving; when it succeeded, the invitations are sent as in C-57.
Source: implied: U-16 - so the admin can learn from history what happened; 60 seconds is the 30-second bound of C-86 with margin

### C-110: A product restart during an import leaves nothing created
Observable: If the product stops or restarts while an import is processing, afterwards no user from that file exists, no invitation went out, and the file can be uploaded again and is treated as a first upload; the import may be absent from history.
Source: implied: U-16, C-25 - atomicity across a crash

### C-111: A created user who no longer exists is shown in the import details as removed, without their data
Observable: In the details of a succeeded import, a user removed by undo or deleted later by other means appears as removed, with their record number in the file (C-27) and no email or name; users still existing show the data of C-82.
Source: choice: the admin needs to see who was removed to correct the file, and the file's row number is enough; keeping a deleted person's address and name would defeat their removal

### C-112: The page, the file upload, the downloads and the invitation links are served only over HTTPS
Observable: A request to any of them over plain HTTP is redirected to HTTPS or refused, and the file's contents are never sent unencrypted. This is a condition for use outside a development environment.
Source: implied: the file and the links are personal data and credentials; Pass 5

### C-113: A submission, undo or resend that did not come from the product's own page is refused
Observable: A form on another website that posts a file, an undo confirmation or a resend to the product while an admin is signed in is refused, and no user is created, removed or emailed.
Source: implied: Pass 5 - a browser sends the admin's session with cross-site requests

### C-114: A file between the configured size limit and the deployment's request limit still gets the product's own too-large reason
Observable: With the default 5 MiB limit, a file of 5 MiB plus 1 byte shows the too-large reason of C-50 and not a bare gateway or server error page. The deployment's request-body limit must therefore be at least the configured size limit plus 1 MiB; the deployment's actual limit is unconfirmed (some proxies default to 1 MiB and would block files above that before the product sees them). In U-10 the operator proves this by uploading a file of exactly the limit and getting past the size check.
Source: implied: C-50 - the product's own limit is meaningless if a layer in front cuts in earlier

### C-115: Every invitation of a full import is handed to the mail system within 60 minutes of the import finishing
Observable: After a succeeded import of 1,000 users, with a mail system that accepts messages, all 1,000 invitations show sent within 60 minutes of the import's finish time, and after a succeeded import of 10,000 users all of them within 6 hours. Sends are paced to stay inside the mail system's own sending rate, whose figure is unconfirmed.
Source: implied: C-64 - invitations are sent after the response, so they need a bound

### C-116: Retries of a failed invitation are spaced
Observable: The second attempt for a user happens no sooner than 1 minute after the first refused attempt, and the third no sooner than 5 minutes after the second.
Source: choice: attempts spaced so a brief outage is ridden out; the figures are decisions

### C-117: Invitation emails come from the sender address the product already uses for its other emails
Observable: The From address of an invitation is the same address as in the product's existing account emails, such as password resets.
Source: choice: recipients and their mail filters already trust that address

### C-118: Pages and downloads that show data from the file are not stored by browsers or shared caches
Observable: After the admin signs out, pressing Back in the browser does not show the import result, the import details or an error list; a shared cache holds none of them.
Source: implied: the data is personal and the admin may use a shared computer

### C-119: The upload form can be used with the keyboard alone and its file field has a label
Observable: Using only Tab, Space and Enter, an admin can reach the file field, choose a file, submit and reach the result; a screen reader announces the file field with its label.
Source: implied: Pass 5 - accessibility of any admin page

### C-120: Results and errors are announced and are not shown by colour alone
Observable: When the result appears, a screen reader announces whether the import succeeded, was rejected or failed; each error and refusal is conveyed in words, not only by a red colour or an icon.
Source: implied: Pass 5 - accessibility

### C-121: Import records and their details are visible only to admins of the same organisation
Observable: An admin of organisation B who opens, searches or downloads from an import of organisation A (by reference or by guessing its address) is refused or told it does not exist, and sees nothing of it; a member of organisation A sees nothing either.
Source: implied: Pass 6 - someone seeing what they may not

### C-122: An import never changes a user that already exists
Observable: A record whose address belongs to an existing user gives a row error (C-24) and the existing user's name, role, status, password and sessions are the same afterwards, whatever the record's name and role say.
Source: implied: Pass 6 - an import creates and does not update

### C-123: An undo removes only the users the import created
Observable: Undoing import I removes none of the users created by hand or by other imports, even if they were created at the same time or have the same name, and removes none of the people from I's file who were already users before I (those were rejected, C-24).
Source: implied: Pass 6 - data lost on the way

### C-124: No existing role gains or loses a permission, and no existing sign-in or password flow changes
Observable: After the upgrade, the one new permission set (importing, undoing, resending, viewing history, downloading the template and error lists) is held by active admins only; members and every other existing role can do everything they could before and nothing more; sign-in and the product's existing password-reset flow behave as before.
Source: implied: Pass 6 - what must not change

### C-125: A zero-byte file is refused as empty
Observable: Submitting a file of 0 bytes shows the empty-file refusal and creates no user.
Source: implied: U-4

### C-126: A file whose first record is blank is refused as having no header
Observable: A file whose first record is empty or has only empty fields (for example a first line of `,,` or a blank line before `email,name`) is refused with the missing-header reason, and nothing is created.
Source: choice: guessing which later line is the header could map columns wrongly

### C-127: Undo is offered only for succeeded imports
Observable: The details of a rejected or failed import show no Undo control, and an undo request for one is refused and changes nothing; the same holds for an import whose record has expired (C-88).
Source: implied: C-71 - a rejected or failed import created nothing to undo

### C-128: A created user who never accepts stays pending until an admin removes them
Observable: A user still pending invitation 30, 90 or 365 days after the import remains in the user list; nothing removes them automatically. After the import record expires (C-88), Resend and Undo through the import are no longer available, and the admin can still remove such a user with the product's ordinary user removal (unconfirmed) and import the address again.
Source: choice: automatic deletion could remove a person who is merely slow, and the request gives no expiry for accounts

### C-129: Each import has a unique reference an admin can read aloud and type
Observable: The reference consists of letters and digits only, is at most 12 characters, differs from the reference of every other import in the product, and is never given to another import later, even after the record expires.
Source: choice: the reference is quoted to an operator (U-13), so its length and alphabet are limited; the figures are decisions

### C-130: A successful import states how many users were created with each role
Observable: After a file creating 3 members and 2 admins, the result shows 5 created, with 3 as `member` and 2 as `admin`; a role with none is shown as 0 or omitted.
Source: implied: C-20 - an admin can mistakenly hand out admin rights to a whole file and should be shown it

### C-131: A double quote inside an unquoted field is kept as an ordinary character
Observable: With the field written without opening quote, `Ann "AJ" Lee` is the name `Ann "AJ" Lee`, and is not a malformed-quoting refusal.
Source: choice: some spreadsheets write such fields; refusing them gains nothing

### C-132: The invitation email states when its link expires
Observable: The email says the link works for 7 days, or gives the date and time it stops working with its time zone.
Source: implied: C-60 - the recipient needs to know how long they have

### C-133: An empty history, and a search that finds nothing, show that plainly
Observable: Before any import has been made, Import history shows a message saying there are none, and not an error; searching for a reference that matches no import in the organisation (or one belonging to another organisation) shows that no import was found, and nothing else.
Source: implied: U-7, U-13 - the first time and the empty case

### C-134: A submission refused before processing starts leaves no import record
Observable: A submission refused for the reasons in C-34, C-35, C-52, C-53, C-56, C-76, C-78 or C-113 does not appear in Import history and has no reference.
Source: choice: these refusals created or examined nothing; listing them would let a flood of refused requests bury the real imports

### C-135: The address of a user who no longer exists can be used again
Observable: After a user is deleted or removed by an undo, a record with that address is accepted and creates a new user, with no row error.
Source: choice: a deleted user is gone; refusing the address would make an undo useless for correcting a file

### C-136: Bulk user import is switched off until an operator switches it on
Observable: On a product that has just received the upgrade, with no operator action, no admin sees the Import users entry and a submission is refused with the imports-switched-off reason (C-76).
Source: choice: a feature that creates accounts in bulk should not appear by surprise

### C-137: In a downloaded error list, a cell that a spreadsheet could evaluate is made inert
Observable: In the file of C-44, a cell that starts with `=`, `+`, `-` or `@` or a tab or carriage return character is written with a single quote `'` before it; the header cells `record`, `column` and `reason` are unchanged.
Source: implied: C-5 - an echoed header name such as `=HYPERLINK(...)` would otherwise be evaluated in the admin's spreadsheet

### C-138: A header name shown in a refusal is cut to its first 100 characters
Observable: An unrecognised header name of 300 characters appears in the refusal as its first 100 characters.
Source: choice: bounds what an uploaded file can put on the page

### C-139: Every result and every import's details show the import reference, and a successful result links to the details
Observable: After a succeeded, rejected or failed import, the result shows the import's reference; a succeeded result also links to that import's details (C-82), which show the same reference.
Source: implied: U-13 - the admin quotes the reference when something goes wrong

### C-140: A password the product's rules refuse leaves the invitation link usable
Observable: Ann submits a password the product's existing rules refuse; she sees the same message as elsewhere in the product, her account is still pending, and the same link still works for a new attempt within its 7 days.
Source: implied: C-65

### C-141: An admin can resend all of an import's resendable invitations in one action
Observable: From the import details, one action resends to every user of that import whose invitation status is queued, sent, failed or expired, and to no one else; users who accepted get nothing.
Source: implied: U-9 - three or three hundred people may need it

### C-142: Names are stored with exactly the characters in the file
Observable: A record with the name `Zoë 李` is created with the name `Zoë 李`, shown identically in the user list, with no characters replaced or dropped.
Source: implied: C-9 - names are not all ASCII

### C-143: A password-reset request for the address of a pending user neither activates the user nor reveals the account
Observable: Requesting a password reset for `ann@example.com` while Ann is pending invitation gives the same response as for an address with no account, leaves her status pending, and gives her no usable password; only the invitation link (C-65) activates her.
Source: implied: C-39 - the product's existing reset flow is a second way to reach an account that must not become a way around the invitation
