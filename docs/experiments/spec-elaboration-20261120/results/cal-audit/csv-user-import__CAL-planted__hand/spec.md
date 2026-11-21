## Use cases

### U-1: An admin uploads a CSV to create many users at once
Flow: The admin chooses a file, uploads it, and sees which users were created and which rows were not.
Source: request

## Clauses

### C-1: An admin can upload a CSV file to create users
Observable: An admin chooses a CSV file and submits it; users named in the file exist afterwards.
Source: request

### C-2: One upload can create more than one user
Observable: A file with three valid rows results in three new users.
Source: request

### C-3: A person who is not an admin cannot upload
Observable: A signed-in user without the admin role who submits the same file is refused and no user is created.
Source: implied: the request gives this to admins

### C-4: A row missing a required value creates no user
Observable: A row with no email address creates no user, and the result names that row and the missing value.
Source: implied: a user cannot be created without what identifies them

### C-5: A row matching a user who already exists does not create a second user
Observable: A row whose email address belongs to an existing user leaves exactly one user with that address.
Source: implied: by U-1

### C-6: After an upload the admin sees how many users were created and which rows were not
Observable: The result shows the count of users created and lists each row that created none, with its reason.
Source: implied: by U-1

### C-7: Rows are handled independently of one another
Observable: In a file of five rows where row 3 is invalid, rows 1, 2, 4 and 5 create users and row 3 is reported.
Source: choice: the request does not say whether one bad row stops the rest

### C-8: The first row of the file names the columns, and columns are matched by name
Observable: A file whose columns are in a different order, with the same header names, creates the same users.
Source: choice: the request does not say how a column is recognised

### C-9: A file holds at most 5,000 rows
Observable: A file of 5,001 rows is refused before any user is created, with a message stating the 5,000-row limit.
Source: choice: an upload needs a bound and the request gives none

### C-10: A created user starts inactive until they accept an invitation sent to their email address
Observable: A newly created user cannot sign in until they follow the link in the invitation message.
Source: choice: the request does not say how a created user first gets in

### C-11: An admin can schedule an uploaded file to be imported at a later date and time
Observable: The admin picks a date and time when uploading; the users are created at that time, not at upload.
Source: choice: convenient for planned onboarding

### C-12: Each import posts a summary message to a Slack channel chosen in settings
Observable: After an import finishes, the chosen Slack channel receives a message with the created and failed counts.
Source: choice: keeps the team informed

### C-13: A dashboard charts the number of imports per week over the last 12 months
Observable: The dashboard page shows a bar chart with one bar per week for the last 52 weeks.
Source: choice: lets admins see usage over time

### C-14: Users created by import are enrolled in a welcome course of five weekly email messages
Observable: Each imported user receives one welcome message a week for five weeks after creation.
Source: choice: improves onboarding

### C-15: The upload is subject to appropriate limits
Observable: An upload that exceeds a limit is handled according to the limit that applies.
Source: implied: by U-1

### C-16: Errors are handled in a user-friendly way
Observable: When something goes wrong the admin sees a helpful message.
Source: implied: by U-1

### C-17: A file of 6,000 rows is accepted and processed in the background
Observable: Uploading a 6,000-row file returns at once and the users appear within a few minutes.
Source: choice: large files should not block the admin

### C-18: A row that fails validation stops the import and no user from the file is created
Observable: In a file of five rows where row 3 is invalid, no user is created.
Source: choice: keeps the data consistent
