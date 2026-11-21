## Use cases

### U-1: An admin uploads a valid CSV to create many users at once
Flow: The admin opens the bulk-import function, chooses a CSV file with a header row and one row per user (for example a header `email,name` and rows such as `ann@example.com,Ann Lee`), and submits it. They see that the import succeeded and how many users were created. The users now exist and appear in the user list.
Source: request

### U-2: An admin using the function for the first time learns what file to prepare
Flow: Before choosing a file, the admin can see on the import function which columns the CSV needs, which are required, and the limits on file size and row count, so they can prepare the file without guessing.
Source: implied: the request says "upload a CSV" but a first-time admin cannot know the expected columns; wrong-input handling depends on the format being knowable

### U-3: An admin uploads a file with bad rows, learns every problem, fixes it, and uploads again
Flow: The admin submits a file in which several rows are wrong (blank email, malformed email, email that already belongs to a user, email repeated in the file, over-long name). They see a report listing the problems, each naming the line of the file and what is wrong. No user from the file has been created. They correct the file and upload it again; this time all rows are created.
Source: implied: "bulk-create users" from a human-prepared file will contain mistakes; a refused action must be explainable and recoverable

### U-4: An admin uploads the same file twice (double click, retry, or forgot it was done)
Flow: The admin submits a file that was already imported successfully. They see that the rows are refused because the users already exist; no duplicate users are created and nothing existing is changed.
Source: implied: the repeated time

### U-5: An admin uploads an empty file, a header-only file, or submits without choosing a file
Flow: The admin submits with no file chosen, or a file with zero bytes, or a file containing only the header row. They see a message saying what is missing; no users are created.
Source: implied: the empty case

### U-6: An admin uploads the largest permitted file
Flow: The admin submits a file with exactly 1,000 data rows (and a size within the file-size limit). All 1,000 users are created and the admin sees the count 1,000 without the request failing or timing out.
Source: implied: the largest case

### U-7: An admin uploads a file beyond a limit
Flow: The admin submits a file with 1,001 data rows, or a file larger than the size limit. They see a message stating the limit that was exceeded; no users are created.
Source: implied: a limit reached

### U-8: An admin uploads something that is not a usable CSV
Flow: The admin submits a file whose columns do not match (no email column, an unrecognised column), a file that is not valid UTF-8 text (for example a spreadsheet saved as .xlsx), or a CSV with an unterminated quoted field. They see a message saying what is wrong with the file; no users are created.
Source: implied: wrong input

### U-9: A person who is not an admin tries to import
Flow: A signed-in non-admin, or someone not signed in, tries to reach the import function or send a file to it. They are refused and no users are created.
Source: implied: the request says "let admins", which also means others cannot

### U-10: Two admins import overlapping files at the same time
Flow: Two admins submit different files that both contain `dup@example.com` at nearly the same moment. Exactly one user with that email exists afterwards; the admin whose import lost sees it refused with the duplicate reported and none of their file's users created.
Source: implied: simultaneous use of a shared user list

### U-11: An operator runs, restarts, upgrades and rolls back the product
Flow: The operator starts the product with users already in it; the import function works with no extra setup. If the product stops or restarts during an import, afterwards the file's users are either all present or none are. After an upgrade that adds the function, users from before are untouched. If the operator goes back to the version before the function existed, users that were created by import are still ordinary working users.
Source: implied: what an operator does — start, restart, carry on with existing data, go back

### U-12: An admin and other users deal with the users created by import and with the existing way of creating users
Flow: An admin adds a single user the way they always could; it works exactly as before. Users created by import behave like users created that way (they appear in the user list, can be set up and used the same way). Importing never alters or removes anyone who already exists.
Source: implied: where this touches things that already exist

## Clauses

### C-1: An admin can upload a CSV file to create users in bulk
Observable: A signed-in admin can choose a CSV file on the import function and submit it; for a valid file, the users in it are created.
Source: request

### C-2: Each valid data row creates exactly one user
Observable: After a successful import of a file with N data rows, exactly N new users exist whose emails are the emails in the rows, and no other user was added.
Source: request

### C-3: A successful import reports how many users were created
Observable: After success the admin sees the number of users created, equal to the number of data rows (for a 1,000-row file, 1,000).
Source: implied: U-1, the admin needs to see that the import did what the file said

### C-4: Only admins can import
Observable: A signed-in user who is not an admin who tries to use the import function (by any means of reaching it) is refused, and no user is created.
Source: implied: "Let admins" — U-9

### C-5: Someone not signed in cannot import
Observable: A request to import without being signed in is refused (not treated as an admin), and no user is created.
Source: implied: U-9

### C-6: The first row of the file is a header row naming the columns
Observable: The first non-empty line is read as column names, not as a user. Names are matched without regard to letter case and ignoring spaces around them, and columns may appear in any order. A file whose data rows come with a header such as ` Email , NAME ` is read the same as `email,name`.
Source: choice: a header makes columns self-describing, so files exported from spreadsheets with columns in any order work; loosest rule that still avoids guessing which column is which

### C-7: A column named `email` is required
Observable: A file whose header has no `email` column is refused with a message naming the missing column `email`; no user is created.
Source: implied: U-8; a user cannot be created without a way to identify them

### C-8: A column named `name` is optional
Observable: A file with an `email` column and no `name` column is accepted; each user is created without a name from the file. A file with a `name` column creates each user with the name from the row (an empty cell means no name).
Source: choice: the request names no fields; email identifies the user and name is the least additional data a user list needs; every other field is out of scope

### C-9: A column other than `email` and `name` is refused
Observable: A file whose header contains any other column name is refused with a message naming that column; no user is created.
Source: choice: silently ignoring a misspelled optional column would lose the admin's data without telling them

### C-10: Standard CSV syntax is read correctly
Observable: Fields are separated by commas; a field may be wrapped in double quotes and then may contain commas, line breaks, and doubled quotes (`""` is one quote character); lines end with LF or CRLF; a leading UTF-8 byte-order mark is ignored; a final line break is optional; lines that are completely empty are skipped. With header `email,name`, the row `ann@example.com,"Lee, Ann"` yields the name `Lee, Ann`.
Source: implied: U-1; files come from spreadsheet programs and contain names with commas

### C-11: Whitespace around each cell value is ignored
Observable: A row with ` ann@example.com ` and ` Ann Lee ` creates the user with email `ann@example.com` and name `Ann Lee`.
Source: choice: hand-prepared files commonly have stray spaces; trimming avoids refusing otherwise valid rows

### C-12: A file that is not valid UTF-8 text or has malformed quoting is refused as a whole
Observable: A file containing bytes that are not valid UTF-8, or a quoted field that is never closed, is refused with a message saying the file cannot be read as CSV (for an unclosed quote, the message contains the line number where the field started); no user is created.
Source: implied: U-8

### C-13: Every data row needs an email
Observable: A row whose email cell is empty is reported as an error on that row's line, naming the email column; no user is created.
Source: implied: U-3

### C-14: Emails must be well formed
Observable: A row whose email is not of the form `local@domain` — exactly one `@`, non-empty text on both sides, no spaces, and a domain containing at least one `.` with text on both sides — or is longer than 254 characters is reported as an error on that row's line naming the email column; no user is created. If the product already has a stricter or different rule for the email of a user created one at a time, that same rule applies instead (see C-31).
Source: choice: the request does not define a valid email; this is the loosest shape that still catches typos such as `ann@` or `ann.example.com`

### C-15: Names are at most 200 characters
Observable: A row with a name longer than 200 characters (after trimming) is reported as an error on that row's line naming the name column; a name of exactly 200 characters is accepted.
Source: choice: some bound is needed so one cell cannot hold unbounded text; 200 is generous for a person's name

### C-16: A row whose email already belongs to an existing user is refused
Observable: A row whose email equals the email of a user who already exists is reported as an error on that row's line saying the user already exists. The comparison ignores letter case (`Ann@Example.com` matches `ann@example.com`). The existing user is not changed, and no user from the file is created.
Source: implied: U-3, U-4; users are identified by email, so two users cannot share one, and "create" does not mean "update"

### C-17: A repeated email within one file is refused
Observable: When the same email (compared ignoring letter case) appears on more than one data row, every occurrence after the first is reported as an error on its own line, and the message contains the line number of the first occurrence; no user from the file is created.
Source: implied: U-3; the same rule as C-16 applied within the file

### C-18: An import is all-or-nothing
Observable: If any problem is found in the file (file-level or any row), no user from that file exists afterwards; if no problem is found, every row's user exists afterwards. There is never a state after an import request finishes in which only part of the file was created.
Source: choice: partial imports force admins to work out which rows are in and which are out before re-uploading; all-or-nothing makes fixing and retrying one step

### C-19: Row problems are reported with the line number of the row and the reason
Observable: Each reported row problem shows the line number of the file where that row begins (the header is line 1) and a description of what is wrong, including which column; one response reports the problems of all rows that have them, not only the first.
Source: implied: U-3; the admin must be able to find and fix every bad row in one pass

### C-20: At most 100 row problems are listed, and the total is stated
Observable: If a file has more than 100 row problems, the report lists the first 100 in file order and states the total number of problems; if it has 100 or fewer it lists all of them.
Source: choice: keeps the report readable for a file that is wholly wrong, while still telling the admin the true size of the problem

### C-21: A file without data rows is refused
Observable: A zero-byte file, a file with only blank lines, or a file with only a header row is refused with a message saying there are no users to import; no user is created.
Source: implied: U-5; the empty case

### C-22: Submitting without choosing a file is refused
Observable: Submitting the import with no file selected shows a message asking for a file; no user is created.
Source: implied: U-5

### C-23: A file may have at most 1,000 data rows
Observable: A file with 1,000 data rows is accepted (when otherwise valid); a file with 1,001 data rows is refused with a message stating the limit of 1,000; no user is created. Blank lines and the header do not count as data rows.
Source: choice: the request gives no size; 1,000 covers a typical organisation onboarding in one file while keeping an all-or-nothing import quick and its report reviewable

### C-24: A file may be at most 2 MB
Observable: A file of 2 MB (2,097,152 bytes) or smaller is accepted for processing; a larger file is refused with a message stating the size limit; no user is created.
Source: choice: a bound is needed so an oversized upload cannot exhaust the system; 2 MB is far above what 1,000 rows of valid data need

### C-25: A 1,000-row import completes in reasonable time
Observable: Submitting a valid 1,000-row file shows its success (or its error report) within 30 seconds.
Source: choice: U-6; the request implies the admin waits for a result, so a bound on waiting is needed

### C-26: The import function tells the admin what file to prepare
Observable: The import function shows, without the admin having to submit anything, the column names (`email` required, `name` optional), the 1,000-row limit and the 2 MB limit.
Source: implied: U-2

### C-27: Uploading a file that was already imported creates nothing new
Observable: Submitting again a file that was imported successfully is refused with every row reported as an already-existing user (per C-16); the number of users is unchanged.
Source: implied: U-4

### C-28: Overlapping imports never produce two users with the same email
Observable: When two imports containing the same email run at the same time, exactly one user with that email exists afterwards; the other import is refused with that row reported as a duplicate and creates none of its file's users.
Source: implied: U-10

### C-29: An interrupted import leaves all of its users or none
Observable: If the product is stopped, restarted or fails while an import is running, then after it is running again either every user from that file exists or none does.
Source: implied: U-11; restart is something an operator does, and C-18 must hold across it

### C-30: Users created by import are ordinary users
Observable: A user created by import appears in the user list straight after the import succeeds and can be viewed, set up, signed in, edited, and removed exactly as a user an admin created individually with the same email and name; they receive the same default role and the same account setup steps (for example any invitation or first-sign-in step) as that user would.
Source: implied: U-12; the request says "create users", i.e. the same users the product already has

### C-31: The rules for creating a user one at a time still hold and are unchanged
Observable: Creating a single user through the existing means behaves exactly as before this feature, and every validation that already applies to a created user (such as a valid, unique email) applies equally to each imported row.
Source: implied: U-12; existing rules must keep

### C-32: Import never changes or removes existing users
Observable: After any import, success or failure, every user who existed before it has the same email, name, role, and status as before, and no one has been deleted.
Source: implied: U-4, U-12; the request says "create", not "update" or "replace"

### C-33: The import function works on a running product with existing users, with no setup
Observable: After the product starts with users already present, a signed-in admin can import without any additional configuration or manual data conversion, and the existing users keep working.
Source: implied: U-11; carry on with the data that exists today

### C-34: Users created by import remain valid if the product goes back to the version before this feature
Observable: After going back to the version without the import function, every user created by import is still present and works as an ordinary user, and no step is needed to repair or convert them.
Source: implied: U-11; go back to the version before

### C-35: Importing does not sign out, lock out or otherwise affect other people's sessions
Observable: While an import runs and after it finishes, other signed-in users, including the importing admin, stay signed in and can continue using the product.
Source: implied: U-12; the feature must not disturb what exists
