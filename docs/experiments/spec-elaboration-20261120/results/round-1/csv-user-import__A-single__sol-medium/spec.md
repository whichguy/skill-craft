## Use cases

### U-1: An admin uploads a CSV for the first time to create multiple users
Flow: The admin opens the bulk-create action, finds the required CSV fields and limits, selects a file containing multiple new users, and submits it. The admin sees the result and finds the created users through normal user management.
Source: request

### U-2: An admin submits another batch to create additional users
Flow: The admin uploads a new file after an earlier import. New users appear alongside the existing users. If the admin resubmits the earlier file to a directory with unique identities, the already-created identities are identified as conflicts.
Source: implied: bulk creation can be used repeatedly against the same user directory

### U-3: An admin submits an empty input to learn why no users were created
Flow: The admin submits without selecting a file, selects a zero-byte file, or uploads a file with column headings but no data records. The admin gets feedback for the missing input or records and can supply a populated file.
Source: implied: an upload can provide no user records

### U-4: An admin imports the largest supported batch to stay within the upload limits
Flow: The admin checks the limits, submits an otherwise valid file of 1,048,576 bytes or with 1,000 data records, and sees it accepted. A file of 1,048,577 bytes or a file with 1,001 data records is refused for exceeding its respective limit.
Source: implied: bulk uploads need a supported size boundary

### U-5: An admin corrects an unreadable or incomplete CSV to submit usable records
Flow: The admin submits a file that cannot be read as CSV, has malformed records, or lacks required column headings. The admin sees where or why the file is unusable and submits a corrected file.
Source: implied: admins can select a wrong file or produce an invalid CSV

### U-6: An admin corrects invalid user data to complete an import
Flow: The admin submits a well-formed file with an invalid user value, a repeated identity, or an identity already in use. The admin locates a problem in the file, corrects it, and retries.
Source: implied: CSV records can violate user-creation rules

### U-7: A caller without the required access attempts an upload and is refused
Flow: A signed-out caller, a signed-in non-admin, or an admin outside the applicable scope attempts to submit a file. The attempt is denied without creating users.
Source: implied: the upload is for admins

### U-8: An admin checks the result of an interrupted import to decide whether to retry
Flow: The admin loses the connection or encounters a service interruption during an import. After access returns, the admin checks the affected users through normal user management. If the batch did not take effect, the admin retries the file. If it did, any existing uniqueness rule still applies to replay.
Source: implied: an upload can be interrupted before the admin sees its result

### U-9: Admins submit overlapping files to create users in the same directory
Flow: Two admins submit files containing the same identity in a directory that requires unique identities. At most one creates that identity. The admin whose attempt conflicts can revise the file and try again.
Source: implied: multiple admins can use the same creation action at the same time

### U-10: An imported user follows the normal account entry path to use the product
Flow: The user follows the existing account setup or sign-in path for an account created with the supplied values. Any existing activation or verification requirement still applies.
Source: implied: bulk-created users are user accounts in the existing product

### U-11: An operator enables the feature for a new or populated installation
Flow: The operator starts the updated product with its ordinary user-management configuration. An authorized admin can import into an empty directory or an existing one. Accounts already in the directory remain usable.
Source: implied: the feature must work at first startup and with existing data

### U-12: An operator restarts the product to resume user administration
Flow: The operator restarts the product after a completed or interrupted import. The admin can find completed accounts and submit another file after normal service resumes.
Source: implied: operators may restart the product while carrying forward its user data

### U-13: An operator reverts the product version to resume ordinary user administration
Flow: The operator returns to the immediately previous version. The admin uses that version's existing user-management functions with the user data carried forward, including accounts created by a completed import.
Source: implied: operators need to go back to the version before the feature

### U-14: An admin continues creating users individually through the existing workflow
Flow: The admin follows the ordinary single-user creation path before or after running a CSV import. The existing path keeps its input requirements and account outcomes.
Source: implied: the request adds a bulk path to user creation

## Clauses

### C-1: An admin can submit a CSV for bulk user creation.
Observable: An admin with user-creation access can upload a CSV file through the product.
Source: request

### C-2: A successful upload can create multiple users from one CSV.
Observable: An admin submits one valid CSV describing multiple distinct new users and finds each created account through normal user management.
Source: request

### C-3: A signed-out caller is refused when submitting a user import.
Observable: A caller without a valid session or equivalent authentication receives an access denial for the upload attempt.
Source: implied: U-7 restricts the action to admins

### C-4: A signed-in non-admin is refused when submitting a user import.
Observable: A signed-in non-admin receives an access denial even when submitting directly to the upload action.
Source: implied: U-7 restricts the action to admins

### C-5: Import honors the existing permission to create users.
Observable: An admin denied ordinary user creation by the product's permission rules receives an access denial when attempting the same creation by CSV.
Source: implied: U-7 uses bulk creation within the existing access rules

### C-6: Import honors the existing boundary on which directory an admin can manage.
Observable: An admin attempting to create users in a directory outside their authorized scope is refused under the same scope rule that governs ordinary creation, where the product has scoped directories.
Source: implied: U-7 includes admins outside the applicable scope

### C-7: An access denial leaves the user directory unchanged.
Observable: After a refused upload, the user directory contains zero accounts created by that attempt.
Source: implied: U-7 refuses the creation action

### C-8: The admin can find the accepted columns before submitting a file.
Observable: Before uploading, an admin can determine which column labels are accepted, which are required, and which values each supported field takes.
Source: implied: U-1 requires an admin to prepare a usable input file

### C-9: A CSV data record describes one proposed user.
Observable: A valid file describing one new user in each of three data records creates three users on success.
Source: implied: U-1 turns a tabular list of users into accounts

### C-10: The first CSV record identifies fields by column heading.
Observable: A file whose first record contains the documented required headings can supply those fields in a different column order, with values still assigned by heading.
Source: choice: a heading record communicates the field mapping without requiring a fixed column order

### C-11: A missing required column heading causes file rejection.
Observable: Submitting a file with a required heading omitted yields a rejection reason that identifies the missing field.
Source: choice: identifying the missing field lets the admin repair the input without guessing

### C-12: An ambiguous duplicate column heading causes file rejection.
Observable: A file repeating a supported heading yields a rejection reason identifying the ambiguous field.
Source: choice: rejecting ambiguity avoids silently choosing between values for the same field

### C-13: Additional uniquely named columns can be present in an otherwise valid file.
Observable: Adding a uniquely named column outside the supported field set to a valid CSV leaves the file eligible for import.
Source: choice: spreadsheet exports can carry extra columns without forcing the admin to edit them out

### C-14: An unsupported column has no effect on an account.
Observable: Placing a value under an unrecognized heading leaves the resulting accounts as they would be if that column were omitted.
Source: choice: only documented import fields can influence account creation

### C-15: Import accepts UTF-8 CSV text.
Observable: A valid UTF-8 file containing non-ASCII characters in a field that ordinarily accepts them creates the account with those characters intact.
Source: choice: UTF-8 supports names and other user values across languages

### C-16: An optional UTF-8 byte order mark is accepted.
Observable: A valid UTF-8 file beginning with the three bytes EF BB BF is accepted with the same field mapping as the corresponding file without those bytes.
Source: choice: spreadsheet exports may include the mark

### C-17: Import accepts both LF and CRLF record endings.
Observable: Equivalent valid files using LF or CRLF line endings are each accepted.
Source: choice: these endings support ordinary exports across platforms

### C-18: A delimiter inside a quoted CSV field belongs to that field's value.
Observable: A quoted value containing a comma is interpreted as one value with the comma intact when its destination field accepts it.
Source: implied: U-1 accepts CSV records with quoted field values

### C-19: A doubled quote inside a quoted CSV field represents a single quote character.
Observable: A quoted value containing two consecutive double quotes is supplied to the destination field with one double quote at that position.
Source: implied: U-1 accepts CSV records with escaped quote characters

### C-20: A line break inside a quoted CSV field belongs to that field's value.
Observable: A quoted field containing a line break is interpreted as part of one data record, subject to ordinary validation of that field's value.
Source: implied: U-1 accepts CSV records whose quoted values span lines

### C-21: Completely blank lines after the header are ignored.
Observable: Inserting blank lines between data records or after the last record creates zero extra proposed users.
Source: choice: blank separator lines carry no account data

### C-22: Submission requires a file.
Observable: Attempting to submit with zero files selected produces feedback that a file is required.
Source: implied: U-3 has no upload to process

### C-23: A CSV with zero data records yields an empty-input rejection.
Observable: A zero-byte file or a file containing only the header is refused with feedback that there are no user records.
Source: choice: an explicit empty-input rejection makes an accidental empty export visible

### C-24: A CSV that cannot be read is refused.
Observable: Submitting content the product cannot read as CSV yields a file-level failure reason.
Source: implied: U-5 requires readable user records

### C-25: Malformed CSV quoting is refused.
Observable: A file with an unclosed quoted field yields a CSV syntax error.
Source: implied: U-5 includes a file whose records cannot be interpreted reliably

### C-26: A nonblank data record with a different field count from its header is refused.
Observable: A file declaring three columns and containing a nonblank record with two or four fields yields a record error.
Source: choice: refusing a mismatched record avoids guessing which values belong to which fields

### C-27: The import file size limit is 1,048,576 bytes inclusive.
Observable: An otherwise acceptable file of exactly 1,048,576 bytes is accepted. A file of 1,048,577 bytes is rejected with feedback identifying the file-size limit.
Source: choice: a 1 MiB limit gives administrators room for ordinary user fields while bounding the upload

### C-28: The import data record limit is 1,000 inclusive.
Observable: An otherwise acceptable file with exactly 1,000 user records is accepted. A file with 1,001 user records is rejected with feedback identifying the record limit.
Source: choice: 1,000 users supports bulk work while bounding each submission

### C-29: The admin can find the upload limits before submitting a file.
Observable: An admin preparing a file can find the file size and data record limits.
Source: implied: U-4 requires an admin to prepare a supported batch

### C-30: Each imported user satisfies the existing rules for required creation values.
Observable: Omitting a value that is required for ordinary user creation in the same context produces a validation failure for the proposed account.
Source: implied: U-6 creates the same kind of account as ordinary creation

### C-31: Each supplied user value is subject to the existing field-validation rules.
Observable: A value invalid for the equivalent ordinary creation field, including any existing length or allowed-value boundary, is refused in an import.
Source: implied: U-6 must honor the same validation as ordinary creation

### C-32: Each imported user is subject to the existing identity comparison rules.
Observable: Two identities that ordinary creation treats as equivalent are treated as the same identity during import.
Source: implied: U-2 and U-6 use the existing directory's account identities

### C-33: An identity already present in the target directory is refused when ordinary creation would treat it as a duplicate.
Observable: When an admin uploads a record for an account that ordinary creation would reject as a duplicate, the import reports an identity conflict.
Source: implied: U-2 adds new users under the directory's existing uniqueness rules

### C-34: Repeated identities within one CSV are refused when they would conflict under the existing uniqueness rule.
Observable: An admin uploads two records for the same new identity and receives a conflict when that identity must be unique in the target directory.
Source: implied: U-6 is subject to the same uniqueness rules within a batch

### C-35: A CSV import cannot modify existing user accounts.
Observable: An admin uploads the identity of an existing user with a different profile value and the existing account retains its original value.
Source: implied: the request authorizes creating users

### C-36: Import honors the existing account-capacity rules.
Observable: In a directory with a user quota, importing enough users to exceed the remaining capacity is refused for that reason.
Source: implied: U-4 reaches existing user-creation limits when they apply

### C-37: Import honors the existing rules governing assignable privileges.
Observable: A requested account privilege that the submitting admin cannot assign through ordinary user creation cannot be granted by CSV.
Source: implied: U-7 includes actions outside the admin's authority

### C-38: Import applies the existing default account privileges.
Observable: A valid record that leaves assignable privileges unspecified gives the new account the same default privileges as equivalent ordinary creation.
Source: implied: U-10 uses the normal account access rules

### C-39: Import applies existing defaults for omitted optional user values.
Observable: Omitting a supported optional profile value produces the same default as ordinary user creation with that value omitted.
Source: implied: U-10 uses the ordinary account behavior

### C-40: Imported users follow the existing onboarding notification rules.
Observable: Where equivalent ordinary creation sends an onboarding notification, a successfully imported account receives that notification under the same conditions.
Source: implied: U-10 requires the ordinary account entry path

### C-41: Imported users follow the existing activation rules.
Observable: If an equivalent individually created account requires activation before sign-in, a newly imported account cannot sign in before satisfying that requirement.
Source: implied: U-10 preserves the existing activation rules

### C-42: Imported users follow the existing verification rules.
Observable: If an equivalent individually created account must verify a value before accessing a feature, a newly imported account faces the same condition.
Source: implied: U-10 preserves existing verification requirements

### C-43: Imported users follow the existing credential rules.
Observable: An imported user uses the same credential setup and authentication rules as an equivalent individually created account.
Source: implied: U-10 uses the existing sign-in path

### C-44: An import creates its batch as a single all-or-none outcome.
Observable: After a batch attempt has settled, either every proposed user in the batch was created or zero were created by that attempt. A batch containing valid records alongside a record that cannot be created leaves zero new users from that batch.
Source: choice: one outcome for the file lets an admin correct or retry a failed upload without tracking partially created rows

### C-45: The admin can distinguish completed creation from refusal.
Observable: The import workflow communicates a successful outcome for a completed batch or a failure outcome for a refused batch.
Source: implied: U-1 and U-6 require the admin to know whether creation succeeded

### C-46: A completed import reports how many users it created.
Observable: A CSV that successfully creates three users yields a success result with a created count of 3.
Source: choice: a total lets the admin reconcile the result with the size of the file

### C-47: A record-level rejection identifies an affected record's location.
Observable: A rejection caused by a user record reports a line or record number that lets the admin locate at least one offending record in the submitted file.
Source: choice: a location makes correction practical in a large batch without fixing the reporting format

### C-48: A record-level rejection identifies the reason the record was refused.
Observable: A result for an invalid user record indicates the problem, such as the invalid field or the identity conflict.
Source: implied: U-6 requires enough information to correct the input

### C-49: An admin can submit a corrected file after a refused attempt.
Observable: After a file is refused, the admin fixes its input and can submit the otherwise eligible file through the same workflow.
Source: implied: U-5 and U-6 recover by submitting corrected input

### C-50: Concurrent creation preserves the existing uniqueness of user identities.
Observable: When two simultaneous imports propose an identity that must be unique in the same directory, at most one account with that identity exists after both attempts settle.
Source: implied: U-9 applies the existing uniqueness rule to simultaneous requests

### C-51: A completed import survives the loss of its response.
Observable: If the connection closes after the import completes but before the result reaches the admin, the completed accounts are visible in normal user management when the admin reconnects.
Source: implied: U-8 can determine whether creation took effect

### C-52: A service interruption permits a new submission once normal service resumes.
Observable: After an interrupted import has settled with zero users created, an eligible admin can resubmit the same valid file when the product is available again.
Source: implied: U-8 recovers from an interrupted attempt

### C-53: Import is available for an empty user directory.
Observable: With an authorized admin already able to manage an empty target directory, a valid import can create its first users.
Source: implied: U-11 covers the first use of an empty directory

### C-54: Import is available for an already populated user directory.
Observable: After an upgrade, an authorized admin can import new identities into a directory that contains accounts from before the upgrade.
Source: implied: U-11 carries forward existing data

### C-55: Enabling import preserves the usability of existing accounts.
Observable: After the feature becomes available, an account created before the upgrade can still use the same account access it had immediately beforehand.
Source: implied: U-11 carries forward existing data

### C-56: The import works with the installation's existing user-management configuration.
Observable: An operator starts the updated product with the prior user-management settings and an admin can submit a valid CSV without entering import-specific settings.
Source: choice: the feature should be usable with defaults wherever ordinary user creation is already enabled

### C-57: Completed imports persist across a normal service restart.
Observable: After the service restarts with its existing user data, all accounts from a completed import still appear in normal user management.
Source: implied: U-12 carries forward completed user data

### C-58: The import action is available after normal service restart.
Observable: An authorized admin can submit a new valid file once service resumes.
Source: implied: U-12 resumes user administration after restart

### C-59: Completed imported accounts remain usable on the immediately previous version after rollback.
Observable: After reverting the product version with its user data retained, a previously imported account can use the prior version's normal account access subject to the ordinary account rules.
Source: implied: U-13 reverts software while carrying forward existing user data

### C-60: Existing accounts remain usable on the immediately previous version after rollback.
Observable: After reverting the product version with its user data retained, an account predating the feature can use the prior version's normal account access subject to the ordinary account rules.
Source: implied: U-13 preserves the data the installation already had

### C-61: The existing individual user-creation path remains available.
Observable: An admin with the existing creation permission can still create one user through the ordinary path without uploading a file.
Source: implied: U-14 continues alongside the bulk action

### C-62: The individual path retains its existing input rules.
Observable: The ordinary creation path still accepts previously valid input and refuses previously invalid input under the same account-creation rules.
Source: implied: U-14 retains the existing creation contract

### C-63: The individual path retains its existing account defaults.
Observable: A user created through the existing path receives the same account defaults that equivalent creation produced before the feature.
Source: implied: U-14 preserves the account outcomes of individual creation

### C-64: The individual path retains its existing onboarding behavior.
Observable: A user created through the existing path goes through the same onboarding that equivalent creation triggered before the feature.
Source: implied: U-14 preserves the account outcomes of individual creation

### C-65: The CSV can supply the values ordinarily required to create a user.
Observable: For the target directory, an admin can map each required user-creation value that ordinary creation asks them to supply to a documented CSV field.
Source: implied: U-1 creates the same kind of account as ordinary creation

### C-66: Import preserves the existing user-creation audit policy.
Observable: Where ordinary user creation is auditable, an authorized reviewer can find equivalent audit information for a completed import's account creations.
Source: implied: U-1 creates accounts under the existing user-management rules

### C-67: The previous version can manage completed imported accounts after rollback.
Observable: After reverting the product version with its user data retained, an admin can find the imported accounts through the previous version's ordinary user-management workflow.
Source: implied: U-13 resumes ordinary user administration

### C-68: Concurrent import preserves uniqueness against ordinary user creation.
Observable: When a simultaneous upload and ordinary creation attempt propose the same identity in a directory that requires unique identities, at most one account with that identity exists after both attempts settle.
Source: implied: U-9 and U-14 create users in the same directory

### C-69: A created account reflects the supplied values under the ordinary creation rules.
Observable: When two valid records provide different values for the same user field, each account shows its corresponding value as it would through ordinary creation.
Source: implied: U-1 creates the users described by the CSV

### C-70: Import leaves users absent from the file in the directory.
Observable: An admin imports a file of new users into a populated directory and can still find the accounts whose identities were absent from the file.
Source: implied: U-2 adds users to the directory
