## Use cases

### U-1: An admin imports a CSV for the first time to create users in bulk
Flow: The admin finds the upload action, checks which columns are accepted, prepares a CSV with two eligible new users, and submits the file once. The result confirms that two users were created. Both users appear in the ordinary user list.
Source: request

### U-2: An admin imports another CSV to add more users
Flow: After an earlier import succeeds, the admin uploads a file with one eligible new user. The result confirms that one user was created. The users from the earlier import are still present.
Source: implied: the upload may be used repeatedly, including for a file with one user

### U-3: An admin replays a file to resolve uncertainty about a previous submission
Flow: The admin submits the same file again after losing the response to the first submission. If the users were created, the replay reports an identity conflict. If the first submission created zero users and the rows are still eligible, the replay can create them.
Source: implied: a repeat submission can follow an uncertain outcome

### U-4: An admin submits an empty CSV to find out whether there is anything to import
Flow: The admin submits a zero-byte file or a file containing only the header and blank lines. The result reports that there are zero user records. Zero users are created.
Source: implied: the file can contain zero user records

### U-5: An admin uploads a large CSV to create users up to the import limit
Flow: The admin can submit 10,000 eligible user records if the file stays within 10,485,760 bytes. An otherwise eligible file of exactly 10,485,760 bytes can also be submitted. A file with 10,001 records or 10,485,761 bytes exceeds the applicable limit. The result identifies the exceeded limit.
Source: implied: the upload has a largest supported input

### U-6: An admin corrects an invalid CSV to complete the import
Flow: The admin submits a file with an unreadable CSV structure, an invalid header, or a row that fails account validation. The result explains a blocking problem and identifies the affected record for a row-level error. Zero users are created. The admin corrects the file and submits it again.
Source: implied: uploaded files may be invalid

### U-7: An admin resolves an account conflict to create eligible new users
Flow: The admin uploads a CSV with a repeated account identity or an identity already in use, including a file that also contains eligible new users. The result identifies the conflict. The existing user stays as they were and zero users are created from the file. The admin can remove or correct conflicting rows and submit again.
Source: implied: bulk creation meets duplicate rows and users already present in the application

### U-8: A caller without permission encounters the upload to learn that the action is refused
Flow: A signed-out caller, a signed-in non-admin, or an admin without create permission in the destination tries to submit a CSV directly. The application refuses the submission. A signed-in admin with the required permission can submit to that destination.
Source: implied: the request grants the action to admins and the application may already restrict where they can create users

### U-9: An admin reaches an existing account limit while importing users
Flow: In a destination with room for one more account under its existing policy, the admin submits two eligible new users. The result identifies the account limit. The admin can submit one eligible new user.
Source: implied: imported users consume capacity under existing account policies

### U-10: Two admins submit overlapping creates to add users without creating duplicate accounts
Flow: Two authorized admins submit otherwise eligible files containing the same new account identity in the same destination. The submissions are resolved with one account for that identity. The unsuccessful submission reports a conflict. The same identity check applies if one admin creates the user through the ordinary create action while the other imports.
Source: implied: imports can run concurrently with each other or with ordinary creation

### U-11: An imported user follows ordinary onboarding to use their account
Flow: After the import succeeds, the user receives or completes the onboarding that applies to ordinary creation in that application. The account has the ordinary default privileges and is available through the same user-facing account flows at the same lifecycle stage as an individually created account.
Source: implied: bulk creation produces users of the existing product

### U-12: An operator deploys or configures the application to make bulk creation available
Flow: The operator starts the updated application with its existing supported configuration and data. An authorized admin can import into the existing destination. The import follows that destination’s account creation policy. Existing accounts continue to work.
Source: implied: an operator must be able to start the updated application and carry on with existing data and settings

### U-13: An operator restarts the application during an import so admins can continue
Flow: The application stops while an otherwise eligible import is in flight. Once it is available again, the admin finds either the full batch or zero users from it. The admin can retry an unapplied batch or start a new import after recovery.
Source: implied: an import may be interrupted by a restart or a service failure

### U-14: An operator returns to the previous version to continue using existing accounts
Flow: The operator restores the previous version using the application’s supported rollback procedure, where one exists. Users created before the upgrade and users created by a completed import remain usable through that version’s ordinary account flows.
Source: implied: an operator may need to return to the version before bulk import

## Clauses

### C-1: An authorized admin can upload a CSV containing multiple new users in one submission.
Observable: An authorized admin submits one CSV containing two eligible new-user records in a single upload.
Source: request

### C-2: A successful bulk import creates one user for each eligible record in the submitted batch.
Observable: After a successful submission of two eligible records, the ordinary user list contains one newly created account for each record.
Source: request

### C-3: The bulk upload action is discoverable from the admin user-management flow.
Observable: An authorized admin can find the action while managing users.
Source: choice: the user-management flow is where admins already do this work

### C-4: The import makes the accepted CSV input requirements available before submission.
Observable: An admin can determine the accepted columns and their requiredness before preparing a file.
Source: implied: U-1

### C-5: A valid CSV with exactly one eligible user record is accepted.
Observable: An authorized admin submits a CSV containing one eligible user record and sees the new account in the ordinary user list.
Source: implied: U-2

### C-6: Bulk creation remains available after a completed import.
Observable: After a successful import, an authorized admin can submit another eligible CSV through the same upload action.
Source: implied: U-2

### C-7: Each submitted import has a caller-visible outcome when the result can be delivered.
Observable: An admin who receives the result can tell whether the import completed or was refused.
Source: implied: U-1 and U-6

### C-8: A successful import result reports how many users it created.
Observable: The result of successfully importing two records says that two users were created.
Source: choice: a count lets admins reconcile the result with the size of their batch

### C-9: A signed-out caller cannot run a bulk import.
Observable: A signed-out caller who submits a valid file directly is refused.
Source: implied: the request assigns the action to admins

### C-10: A signed-in non-admin cannot run a bulk import.
Observable: A signed-in non-admin who submits a valid file directly is refused.
Source: implied: the request assigns the action to admins

### C-11: An admin must have ordinary user-create permission in the destination to import there.
Observable: An admin whose authority excludes user creation in a destination is refused when submitting a valid file to that destination.
Source: implied: U-8

### C-12: A permission refusal does not disclose account-validation details.
Observable: A caller who lacks permission receives a refusal that does not reveal whether an identity in the submitted file already exists.
Source: choice: a refused upload should not become a way to check which accounts exist

### C-13: An imported account belongs to the destination in which the admin is authorized to create it.
Observable: An import for one destination yields accounts in that destination under the same scoping rules as individually created accounts.
Source: implied: U-8 and U-12

### C-14: An imported account is subject to the ordinary rules that determine whether its account field values are valid.
Observable: A CSV row with a field value that would be refused during ordinary creation in the same destination is refused for that account validation problem.
Source: implied: U-6 and U-12

### C-15: Imported accounts use the ordinary defaults for omitted profile fields.
Observable: A permitted profile field omitted from the CSV takes the same default as it would if omitted during ordinary creation.
Source: implied: U-1 and U-11

### C-16: Imported accounts receive the default privileges for ordinary account creation in their destination.
Observable: A user imported into a destination has the same initial access as a user created there with default privileges.
Source: choice: imposing default privileges keeps the import focused on creating users without adding bulk permission management

### C-17: Imported accounts follow ordinary onboarding.
Observable: An imported user faces the same invitation or activation prerequisites as an equivalent user created individually, where the application has such prerequisites.
Source: implied: U-11

### C-18: An imported account is usable through ordinary account flows.
Observable: At the same lifecycle stage, an imported user can use the same account flows as an equivalent user created individually.
Source: implied: U-11

### C-19: An imported account is subject to account capacity rules already in force in its destination.
Observable: If the destination has capacity for one additional account, a two-user CSV cannot exceed that capacity.
Source: implied: U-9

### C-20: An otherwise eligible batch within the destination’s remaining capacity can use all that capacity.
Observable: If exactly one account slot remains, an otherwise eligible one-user CSV can fill it.
Source: implied: U-9

### C-21: Imports use a header record to map CSV columns to account fields.
Observable: An admin can change the order of the documented columns by reordering both the header and the corresponding values. The resulting account field values are unchanged.
Source: choice: named columns let admins map a file to the account model without relying on column positions

### C-22: An import is refused when a required column is missing.
Observable: A file whose header omits an account field required for import is refused.
Source: implied: U-6 and the need to supply all required creation data

### C-23: An import is refused when a column does not map to a supported account field.
Observable: A file with an extra column that the import does not accept is refused with a diagnostic identifying that column.
Source: choice: reporting an unrecognized field prevents an admin from believing its values were applied

### C-24: An import is refused when more than one column maps to the same account field.
Observable: A file that supplies the same accepted column twice is refused with a diagnostic identifying the ambiguous field.
Source: choice: two CSV values for the same field would leave the intended value ambiguous

### C-25: The import accepts comma-separated UTF-8 CSV.
Observable: An otherwise eligible comma-separated file encoded in UTF-8 can create an account with a valid non-ASCII field value.
Source: choice: a common encoding makes the input portable across spreadsheet editors

### C-26: The import accepts a UTF-8 byte order mark at the start of the file.
Observable: Adding a UTF-8 byte order mark to an otherwise eligible CSV leaves the first header field usable.
Source: choice: some spreadsheet editors emit this marker when exporting UTF-8 CSV

### C-27: The import accepts LF or CRLF CSV record endings.
Observable: An otherwise eligible CSV imports with LF endings or with CRLF endings.
Source: choice: support exports from common operating systems

### C-28: The final CSV record may end at the end of the file.
Observable: Removing the final record ending from an otherwise eligible CSV still allows its last record to be imported.
Source: choice: CSV producers vary in whether they write a final record ending

### C-29: A quoted field may contain a comma.
Observable: A user imported with the otherwise eligible field `"Smith, Jane"` has the value `Smith, Jane` in that account field.
Source: choice: names and other text values can contain the field separator

### C-30: A doubled quote inside a quoted field represents one literal quote.
Observable: A user imported with the otherwise eligible field `"Jane ""JJ"" Smith"` has the value `Jane "JJ" Smith` in that account field.
Source: choice: quotes in text values need a representation that spreadsheet exports can produce

### C-31: A line break inside a quoted field belongs to that field.
Observable: A data record containing a quoted line break is treated as one record. Its field value is evaluated under the ordinary rules for that field.
Source: choice: a multiline CSV value must be distinguished from a new user record

### C-32: Empty lines outside quoted fields are ignored.
Observable: Adding an empty line before, between, or after data records leaves the number of user records unchanged.
Source: choice: a blank line can be a byproduct of editing or exporting a file

### C-33: An import with zero user records is refused.
Observable: A zero-byte file or a file with a valid header followed by zero user records reports that there are no user records to import.
Source: choice: an explicit empty result helps the admin detect the wrong export

### C-34: Input that cannot be read as supported CSV is refused.
Observable: A non-CSV file with a `.csv` filename, invalid UTF-8, or a CSV with an unclosed quoted field produces a file diagnostic.
Source: implied: U-6 and the requirement for actual CSV input

### C-35: Each data record must contain the number of fields described by its header.
Observable: A row with one field too many or one field too few produces a record-level diagnostic about the mismatch.
Source: choice: the header defines where each value belongs and how to distinguish a missing cell from an empty one

### C-36: A diagnostic for a row-level problem identifies the affected record.
Observable: Given a CSV with an invalid value in its third user record, the diagnostic lets the admin locate that record without guessing which record failed.
Source: choice: locating the record lets an admin correct the file when several records look similar

### C-37: A refused import identifies at least one reason the submission cannot proceed.
Observable: On an ordinary refusal, the result gives the admin a reason they can act on, such as a malformed file, an invalid value, a conflict, or an exceeded limit. A caller refused for permissions sees the permission reason.
Source: implied: U-6 through U-9

### C-38: An otherwise eligible file at or below 10,485,760 bytes meets the import byte limit.
Observable: An otherwise eligible CSV with exactly 10,485,760 uploaded file bytes is accepted. A file of 10,485,761 bytes is refused for exceeding the byte limit.
Source: choice: 10 MiB gives admins room for large exports while bounding the size of one upload

### C-39: An otherwise eligible file at or below 10,000 user records meets the import record limit.
Observable: An otherwise eligible file with exactly 10,000 data records passes the record limit. One with 10,001 data records is refused for exceeding it.
Source: choice: 10,000 records permits large batches while bounding account creation in one submission

### C-40: An import cannot create an account that conflicts with an existing account’s identity under the ordinary creation rules.
Observable: Submitting a row for an identity already in use in the relevant scope leaves a single account for that identity.
Source: implied: U-3 and U-7

### C-41: An import is refused when two user records conflict under the ordinary identity uniqueness rules.
Observable: With two rows carrying the same otherwise unused identity in a scope where the identity must be unique, the result identifies the repeated identity as the cause of refusal.
Source: choice: reporting the conflict lets the admin choose which record to keep

### C-42: The ordinary account identity uniqueness rule holds across concurrent creation attempts.
Observable: In a scope requiring a unique identity, two otherwise eligible creates for the same new identity leave one account for that identity. This holds for two imports or an import overlapping ordinary creation.
Source: implied: U-10

### C-43: Bulk creation leaves pre-existing accounts unchanged.
Observable: An existing account has the same stored account details after a batch attempts to use its identity, even if the row supplies different details.
Source: implied: the request is to create users

### C-44: A refused batch creates zero users.
Observable: A valid new-user row submitted alongside an invalid or conflicting row does not appear as a new account after the batch is refused.
Source: choice: whole-batch refusal lets the admin correct and resubmit the file without reconciling partially applied rows

### C-45: An interrupted import settles with a complete batch or zero users from that batch after recovery.
Observable: When the application stops during an otherwise eligible import, after recovery the admin finds either every new account from the file or zero new accounts from it.
Source: choice: a whole-batch outcome keeps recovery consistent with correction and retry

### C-46: An unapplied batch can be submitted after recovery.
Observable: If an interrupted batch created zero users, an authorized admin can resubmit the same still-eligible CSV once service is restored.
Source: implied: U-3 and U-13

### C-47: Ordinary user creation remains available alongside bulk creation.
Observable: An admin who could create a user individually before the update can do so through the same flow after the update.
Source: implied: U-10 and the request adds a creation path

### C-48: Existing accounts remain usable after deployment.
Observable: A user who could use their account before the update can use it after the update under the same account rules, without account recreation.
Source: implied: U-12

### C-49: Bulk creation is available on an updated application started with a previously supported configuration.
Observable: An operator starts the updated application with the same supported configuration and destination settings. An admin with permission can submit an eligible CSV.
Source: choice: admins should be able to use the requested feature on upgrade without an import-specific setup step

### C-50: Completed imports remain durable across application restarts.
Observable: Users from a completed import are present after stopping and starting the application.
Source: implied: U-13 and successful creation produces ordinary persisted users

### C-51: A supported application rollback preserves access to accounts that existed before the update.
Observable: After returning to the previous version using its supported rollback procedure, pre-update accounts remain available through their ordinary account flows.
Source: implied: U-14

### C-52: A supported application rollback preserves accounts created by a completed import.
Observable: After returning to the previous version using its supported rollback procedure, accounts from a completed import remain available at their applicable lifecycle stage through the previous version’s ordinary account flows.
Source: choice: a completed create gives the admin an account they can rely on through a version rollback

### C-53: An import is refused when a row conflicts with an existing account under the ordinary identity uniqueness rules.
Observable: A file containing an identity already in use in the relevant scope is refused with an identity conflict, including when the admin replays a previously successful import.
Source: choice: a conflict makes it clear that the file requests an account that already exists

### C-54: A diagnostic for a missing required column identifies the missing account field.
Observable: When a file is refused because a required column is absent, the result identifies the required field the admin needs to supply.
Source: choice: naming the field lets the admin fix the header

### C-55: An imported account produces any audit record already required for ordinary account creation.
Observable: Where the application already exposes account creation to an authorized audit viewer, the viewer can see that the imported account was created.
Source: implied: U-11 and U-12, where existing account creation rules include auditing

### C-56: A refused batch does not initiate onboarding for its submitted users.
Observable: In an application that normally sends invitations on account creation, submitting an otherwise eligible row in a refused batch generates no invitation for that row.
Source: choice: onboarding people from a refused batch would give them an invitation without an account
