## Use cases

### U-1: An admin uploads a CSV of people to create all of them as users in one step
Flow: The admin opens the place where they manage users, chooses a CSV file with a header row and one row per person (columns `email` and `name`), and submits it. Every row becomes a user. The admin sees a confirmation stating how many users were created, and the new users are in the user list.
Source: request

### U-2: An admin uses the import for the first time and needs to know what file to prepare
Flow: The admin opens the import page without having seen it before. The page tells them which columns the file needs, that the first line is a header, and the limits (rows and file size). They prepare a file from that and submit it.
Source: implied: "upload a CSV" takes for granted that the admin knows what the CSV must contain; the request does not say.

### U-3: An admin uploads a file in which some rows are wrong, fixes them and uploads again
Flow: The admin submits a file where some rows have a bad email, a blank name, a repeated address, or an address that already belongs to a user. They see that nothing was created and a list of every problem, each naming the line of the file and what is wrong. They correct the file and submit it again; this time all rows are created and the count is shown.
Source: implied: "bulk-create" over many rows means some rows will be wrong; an admin cannot fix a file without knowing where.

### U-4: An admin uploads the same file a second time
Flow: The admin submits a file whose users were already created by an earlier upload (a double click, a retry after a lost page, a rerun). They see that nothing was created and that each row's address already belongs to a user. No user is duplicated or changed.
Source: implied: the repeated time; users must be unique people.

### U-5: An admin uploads a file with no people in it
Flow: The admin submits an empty file, or a file with only a header line, or submits without choosing a file. They see a message that there is nothing to import. Nothing is created.
Source: implied: the empty case.

### U-6: An admin uploads the largest file the import allows
Flow: The admin submits a file with 1,000 people (and up to 1,048,576 bytes). All 1,000 users are created and the admin sees the count 1000, in a reasonable time.
Source: implied: the largest case; a bulk operation needs a stated ceiling.

### U-7: An admin uploads a file over a limit
Flow: The admin submits a file with 1,001 people, or one larger than 1,048,576 bytes. They see a message that names the limit they exceeded. Nothing is created.
Source: implied: a limit reached.

### U-8: An admin uploads something that is not a usable CSV
Flow: The admin submits a spreadsheet binary, a text file in a non-UTF-8 encoding, a file missing the `email` or `name` column, a file with a row that has too many or too few fields, or a file with an unclosed quote. They see a message saying what is wrong and, where it is a row, the line number. Nothing is created.
Source: implied: wrong input.

### U-9: An admin uploads a file exported from a spreadsheet program
Flow: The admin saves from a spreadsheet as CSV and submits it. The file may start with a byte-order mark, use Windows line endings, quote names that contain commas, carry extra columns they did not mean to include, spaces around values, and blank rows at the end. The import accepts it and creates the users from the real rows.
Source: implied: the usual way a CSV for "bulk-create users" is produced.

### U-10: A signed-in user who is not an admin tries to import
Flow: The user does not see the import in their interface; if they send an upload to it anyway, it is refused with a message that they lack permission. Nothing is created.
Source: request ("admins")

### U-11: A visitor who is not signed in, or an admin whose session has ended or whose admin right has been withdrawn, tries to import
Flow: The upload is refused; they are told to sign in or that they lack permission. Nothing is created.
Source: implied: "admins" must hold at the moment of the action, not only when the page was opened.

### U-12: Two admins import overlapping files at once, or one admin submits twice at once
Flow: Both uploads contain the same email address. At most one user with that address results. An upload that loses the race is refused as a whole, with a message naming the address, and creates nothing.
Source: implied: uniqueness of users under concurrent use.

### U-13: A person created by the import starts using the system
Flow: The person receives or is given whatever a user created one at a time by an admin receives or is given, and can sign in and use the product with ordinary (non-admin) rights.
Source: implied: "create users" means users who can then be users.

### U-14: An admin keeps creating and managing users the usual way
Flow: Creating a single user, editing users and viewing the user list work as they did before the import existed; users created before the import are unchanged by it.
Source: implied: where this touches things that already exist.

### U-15: An operator deploys, restarts and rolls back around this feature
Flow: The operator deploys the version with the import onto a system that already has users: every existing user is still present and usable, with no manual data step. The operator restarts the service while an import is running; afterwards the file's users either all exist or none do. The operator goes back to the previous version after imports were done: the users created by the import are still there and can still sign in; only the upload is gone.
Source: implied: start, restart, carry on with existing data, go back.

## Clauses

### C-1: An admin can upload a CSV file from the admin interface to create users
Observable: A signed-in admin finds, where users are managed, a way to choose a CSV file and submit it. After a successful submit, one new user exists per data row of the file.
Source: request

### C-2: Each row creates a user with that row's name and email
Observable: After a successful import, the user list shows, for each data row, a user whose email is that row's email and whose name is that row's name.
Source: request

### C-3: Imported users are ordinary users, never admins
Observable: Every user created by an import has no admin rights, whatever the file contains; the file has no way to grant them.
Source: choice: a file carrying a privilege level would let a malformed or tampered file mint admins; the request asks only to create users.

### C-4: An imported user is in the same state as a user an admin creates one at a time
Observable: An imported user gets the same defaults, the same notifications or invitations, and the same way of first signing in as a user an admin creates individually, and can sign in by that way.
Source: implied: U-13, "create users"

### C-5: A row the system would refuse to create as a single user is refused in the import
Observable: Any rule that makes the system refuse to create a user individually (including any cap on the number of users) also makes the import refuse that row or the file, with a message, creating nothing.
Source: implied: U-14; the import must not be a way around existing rules.

### C-6: A successful import tells the admin how many users were created
Observable: After success the admin sees a message that contains the number of users created, equal to the number of data rows.
Source: implied: U-1; the admin needs to know the outcome.

### C-7: The import page states the file format and the limits
Observable: The page where the file is chosen names the required columns `email` and `name`, says the first line is a header, and states the limits of 1,000 rows and 1,048,576 bytes.
Source: implied: U-2

### C-8: The first line is a header, and columns are found by name
Observable: The first line of the file names the columns. The columns `email` and `name` are used wherever they stand, so a file with `name,email` and a file with `email,name` give the same result. Header names match regardless of letter case and surrounding spaces.
Source: choice: the request gives no columns; at least one identifier and a display name are needed to create a person, and matching by name is the loosest way a file can be correct.

### C-9: A file missing a required column is refused
Observable: If the header lacks `email` or `name`, the admin sees a message naming each missing column, and nothing is created.
Source: implied: U-8

### C-10: A file with a repeated column name is refused
Observable: If `email` or `name` appears more than once in the header, the admin sees a message naming that column, and nothing is created.
Source: choice: two values for one field would force a guess about which one the admin meant.

### C-11: Columns other than `email` and `name` are ignored
Observable: A file with extra columns is accepted, and the extra values are not stored on any user.
Source: choice: U-9; spreadsheet exports commonly carry extra columns, and refusing them serves no one.

### C-12: Values may be quoted in the usual CSV way
Observable: A value in double quotes may contain commas, line breaks and a doubled `""` for a double quote; a name such as `"Smith, Jo"` becomes the name `Smith, Jo`.
Source: implied: U-9; the normal meaning of "CSV".

### C-13: Both Unix and Windows line endings are accepted
Observable: A file whose lines end in LF and the same file with lines ending in CRLF create the same users.
Source: implied: U-9

### C-14: UTF-8 text is accepted with or without a byte-order mark, and other content is refused
Observable: A UTF-8 file, with or without a leading byte-order mark, is read correctly, so a name such as `Zoë` is kept as written and the first column is found despite the mark. A file that is not valid UTF-8 text is refused with a message saying so, and nothing is created.
Source: implied: U-8, U-9

### C-15: Spaces around values are ignored
Observable: A row `  Jo Smith , jo@example.com ` creates a user with name `Jo Smith` and email `jo@example.com`.
Source: choice: U-9; padded values are a common accident of hand-edited files, and the padding is never meant.

### C-16: Blank lines and rows with no values are skipped
Observable: A line with nothing on it, or a row whose every field is empty after trimming, creates no user and is not an error. Such lines still count toward line numbers.
Source: choice: U-9; spreadsheet exports often end in empty rows.

### C-17: Line numbers count the file's lines from 1 at the header
Observable: Wherever a message names a line, the header is line 1, the next line is line 2, and so on, counting every line of the file including skipped ones. A record that spans several lines is named by the line on which it starts.
Source: implied: "an admin cannot fix a file without knowing where" (U-3); the number must match what an editor shows.

### C-18: Each row needs a valid email
Observable: A row whose email is empty, contains spaces, lacks the `@`, has nothing before or after the `@`, or has no `.` after the `@` is reported as a problem on its line, naming the email field.
Source: choice: a minimal shape check that catches typos without refusing real addresses.

### C-19: An email is at most 254 characters
Observable: A row with an email of 254 characters is accepted; one with 255 is reported as a problem on its line naming the email field.
Source: choice: the practical maximum length of an email address; the request is silent.

### C-20: Each row needs a name
Observable: A row whose name is empty after trimming is reported as a problem on its line, naming the name field.
Source: choice: a user with no name cannot be told apart in a user list.

### C-21: A name is at most 100 characters
Observable: A row with a name of 100 characters is accepted; one with 101 is reported as a problem on its line, naming the name field.
Source: choice: a ceiling so one row cannot carry an unbounded value; the request is silent.

### C-22: A row with the wrong number of fields is reported
Observable: A row with more or fewer fields than the header has is reported as a problem on its line.
Source: implied: U-8

### C-23: Malformed quoting is reported
Observable: A quoted value that is never closed, or a stray quote inside an unquoted value, is reported as a problem naming the line on which the broken record starts, and nothing is created.
Source: implied: U-8

### C-24: Email addresses are compared without regard to letter case
Observable: `Jo@Example.com` and `jo@example.com` are the same address wherever this specification compares addresses.
Source: choice: people write addresses in either case but a mailbox is one; treating them as different would create two users for one person.

### C-25: An address repeated within the file is reported
Observable: When the same address appears on several rows, every row after the first is reported as a problem on its line, saying the address repeats and naming the line of its first appearance.
Source: implied: U-3; users must be unique.

### C-26: An address that already belongs to a user is reported
Observable: A row whose address already belongs to a user is reported as a problem on its line saying the user already exists.
Source: implied: U-4; users must be unique.

### C-27: The import never changes an existing user
Observable: After any import, success or refusal, every user who existed before it has the same name, email, rights and state as before.
Source: implied: U-4; the request says "create", not update.

### C-28: The import is all or nothing
Observable: If any problem is found in the file, no user from the file is created, and the user list is exactly as before. If there is no problem, every row's user is created.
Source: choice: with partial creation a corrected file cannot be uploaded again, because the rows already created would be refused as existing (U-3, U-4).

### C-29: Every problem in the file is reported, not just the first
Observable: When a file has problems on several rows, the admin sees one entry per problem row (more if a row has several problems), each containing the line number and a description of the problem; rows without problems are not listed.
Source: implied: U-3; one pass per error would make fixing a 1,000-row file impractical.

### C-30: A file may have at most 1,000 data rows
Observable: A file with 1,000 data rows (not counting the header or skipped lines) is accepted; a file with 1,001 is refused with a message that states the limit of 1,000, and nothing is created.
Source: choice: a ceiling is needed so one request cannot create an unbounded number of users; 1,000 is large enough for a whole organisation's onboarding batch.

### C-31: A file may be at most 1,048,576 bytes
Observable: A file of exactly 1,048,576 bytes is not refused for size; one of 1,048,577 bytes is refused with a message that states the limit, and nothing is created.
Source: choice: bounds the work and memory of one upload; it comfortably holds 1,000 rows at the field maximums.

### C-32: A file with no data rows is refused
Observable: An empty file, or one with only a header line (and blank lines), is refused with a message saying there are no users to import, and nothing is created.
Source: implied: U-5

### C-33: Submitting without choosing a file is refused
Observable: Submitting with no file chosen shows a message asking for a file, and nothing is created.
Source: implied: U-5

### C-34: A signed-in non-admin cannot import
Observable: A signed-in user without admin rights who sends an upload is refused with a message that they lack permission, and no user is created. They are not shown the import in their interface.
Source: request ("admins")

### C-35: A visitor who is not signed in cannot import
Observable: An upload from someone not signed in is refused, with a prompt to sign in, and no user is created.
Source: implied: U-11

### C-36: Admin rights are checked when the upload is submitted
Observable: An upload submitted after the person's session ended, or after their admin rights were withdrawn, is refused as in C-34 or C-35 even if the import page was opened while they were admin.
Source: implied: U-11

### C-37: No two users end up with the same address, even under concurrent uploads
Observable: When two uploads containing the same address run at once, afterwards exactly one user has that address. The upload that loses is refused as a whole with a message naming the address, and creates no user.
Source: implied: U-12; C-26 and C-28 must hold under concurrency.

### C-38: A file of 1,000 rows finishes within 60 seconds
Observable: From submit to seeing the result, a valid 1,000-row file takes at most 60 seconds on an ordinary deployment.
Source: choice: U-6; the admin should not be left without an answer; the request gives no time.

### C-39: Creating a single user and the other user management are unchanged
Observable: Creating one user by hand, editing a user and viewing the list behave as they did before the import existed.
Source: implied: U-14

### C-40: Deploying the import keeps existing users and needs no manual data step
Observable: After the version with the import replaces the one before, every user from before is present and can sign in, and the import works without the operator doing anything beyond deploying.
Source: implied: U-15

### C-41: A restart during an import leaves all or none of the file's users
Observable: If the service is stopped and restarted while an import runs, then afterwards either every row of that file has a user or none does.
Source: implied: U-15; follows from C-28.

### C-42: Going back to the previous version keeps imported users
Observable: After the previous version is put back, the users created by earlier imports are still in the user list and can still sign in.
Source: implied: U-15
