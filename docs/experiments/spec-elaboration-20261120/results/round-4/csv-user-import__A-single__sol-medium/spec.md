## Use cases

### U-1: An admin uploads a CSV to create users in bulk
Flow: The admin selects a CSV containing several new users, submits it, and sees the outcome. The new users appear through the product's ordinary user lookup.
Source: request

### U-2: A first-time admin finds the import requirements to prepare a CSV
Flow: The admin opens the import entry point, checks which fields to supply and what the importer accepts, then submits a CSV containing one new user.
Source: implied: an admin needs to prepare a usable file before their first upload

### U-3: An admin imports another batch to add to the users already present
Flow: The admin submits a second file with different users and sees those users alongside existing accounts. A person whose account predates the import continues to use it.
Source: implied: bulk creation adds users to the current user population

### U-4: An admin opens a newly imported account to manage it
Flow: The admin finds the created account using ordinary user management. The imported user follows the product's ordinary account activation or sign-in flow, where one exists.
Source: implied: the request creates users of the product

### U-5: An admin submits an empty import to learn why no users appeared
Flow: The admin attempts to submit without a file, then tries an empty file or a CSV with only a header. The outcome identifies the missing file or the absence of user records, and the admin can submit a populated file.
Source: implied: an upload can contain no user records

### U-6: An admin imports a batch at the supported limits to add as many users as permitted
Flow: The admin checks the limits and submits valid files at the supported boundaries. If a file crosses either boundary, the admin sees which limit applies and can resubmit a smaller file.
Source: implied: a bounded upload needs predictable behavior at its boundaries

### U-7: An admin corrects unreadable CSV data to get a usable upload
Flow: The admin submits unreadable CSV or a file whose columns do not match the import's published contract. The admin sees why it could not be imported, fixes the file, and submits it again.
Source: implied: uploaded content can fail to represent user records

### U-8: An admin corrects invalid user data to finish an import
Flow: The admin submits a readable CSV containing an invalid user entry. The admin uses the reported reason and location to repair the entry and tries again.
Source: implied: a readable CSV can contain a user the product cannot create

### U-9: An admin resolves duplicate identities to create only new accounts
Flow: The admin submits a file that repeats an identity within the file or uses an identity already present. The admin removes or corrects the conflicting entries and can retry.
Source: implied: creation can conflict with the user's existing identity

### U-10: A caller without sufficient access attempts an import and has it refused
Flow: A signed-out caller or a signed-in non-admin attempts submission. An admin whose authority is scoped also attempts a submission outside that scope. No account is created by the refused action.
Source: implied: the request grants the action to admins within their authority

### U-11: An admin retries after a failure or interruption to finish the import
Flow: Submission fails or the admin loses the response. The admin checks existing users or submits the file again. Retrying does not create a second account for the same identity.
Source: implied: uploads may be interrupted before the admin knows the outcome

### U-12: Two admins submit overlapping additions to onboard users
Flow: The admins submit imports that contain the same new identity, or one admin creates that identity through the ordinary creation flow while an import is in progress. Existing identity rules determine the outcome.
Source: implied: imports use the same user population as other creation actions

### U-13: An operator starts or restarts the product to make import available
Flow: The operator starts the upgraded product with its established configuration, then verifies that an admin can use import with the current users present. After a restart, completed imports remain available and admins can submit new files.
Source: implied: the feature must work on start and restart with existing deployment settings

### U-14: An operator returns to the previous release to restore service
Flow: Where a previous release exists, the operator returns to it after a completed import. Existing users and newly imported users remain accessible through its ordinary user flows.
Source: implied: rolling back the feature can happen after users have been created

## Clauses

### C-1: An authorized admin can upload a CSV to initiate bulk user creation
Observable: An admin with user-creation authority submits a CSV file through the product.
Source: request

### C-2: A valid CSV submission creates one user for each supplied user record
Observable: Submitting a valid CSV with multiple distinct new user records creates an account corresponding to each record.
Source: request

### C-3: A CSV containing one valid new user record is eligible for import
Observable: A valid one-record submission creates its user.
Source: implied: U-2, an admin may have just one entry to import

### C-4: The import entry point makes its accepted CSV contract available before submission
Observable: From the import entry point the admin can find the accepted CSV form, the supported columns, which values are required, and the file and record ceilings.
Source: implied: U-2 and U-6, admins need to prepare a file they can submit

### C-5: Imported users are visible through ordinary user lookup after successful creation
Observable: After a successful import, an admin can find the new accounts through the same user lookup used for other accounts.
Source: implied: U-1 and U-4, imported users are ordinary product users

### C-6: The admin can determine whether a submission completed successfully
Observable: A completed submission has an outcome available to the admin that distinguishes success from failure.
Source: implied: U-1 and U-11, uploading alone does not tell the admin whether users were created

### C-7: A successful outcome reports the number of accounts created by that submission
Observable: The success outcome for a submission creating three accounts reports three created accounts.
Source: choice: a count lets the admin reconcile the submission with the result without requiring a separate report

### C-8: Import requires an authenticated caller
Observable: A signed-out caller's attempt to submit an otherwise valid CSV is refused.
Source: implied: U-10, an unauthenticated caller cannot establish admin authority

### C-9: Import requires admin authority at submission
Observable: A signed-in non-admin cannot submit a valid CSV successfully, including by invoking the submission action directly.
Source: request

### C-10: Import respects the caller's existing user-creation scope
Observable: Where administrative authority is scoped, an admin cannot use import to create users outside the scope in which they may ordinarily create users.
Source: implied: U-10, an import cannot extend an admin's existing authority

### C-11: A refused submission creates zero users
Observable: After a refused submission, none of its proposed users exist as a result of that submission.
Source: implied: U-10, refusing the action must prevent the requested creation

### C-12: Import requires an uploaded file
Observable: Attempting to submit without a file is blocked with an indication that a file is required.
Source: implied: U-5, the requested operation uses an uploaded CSV as its input

### C-13: Import accepts comma-separated CSV
Observable: A valid file using commas as field delimiters is accepted.
Source: choice: comma separation provides a common interchange form without requiring support for alternate delimiters

### C-14: Import accepts UTF-8 CSV
Observable: A valid UTF-8 file with non-ASCII characters in a field that permits them imports the characters correctly.
Source: choice: one encoding supports international text without requiring encoding detection

### C-15: A UTF-8 byte order mark at the beginning of a file is optional
Observable: Adding a UTF-8 byte order mark to an otherwise valid CSV does not change the first field name or the import outcome.
Source: choice: common CSV exporters may add the mark

### C-16: Import accepts both LF and CRLF record endings
Observable: Equivalent CSV files using LF or CRLF record endings have equivalent outcomes.
Source: choice: CSV exported on different operating systems need not be converted first

### C-17: The last CSV record may omit its record ending
Observable: Removing the final record ending from a valid CSV does not change its outcome.
Source: choice: the last record is unambiguous at end of file

### C-18: Double-quoted CSV fields can contain embedded commas, escaped quotes, or line breaks
Observable: Where such text is valid for a user field, a quoted field containing a comma, a doubled double quote, or a line break imports as one field with the corresponding literal text.
Source: choice: common CSV quoting preserves exported field values

### C-19: The first nonempty record names the upload's columns
Observable: A valid header followed by a user record identifies the fields in that record. A file with user values as its first nonempty record and no header is rejected.
Source: choice: a header identifies fields without imposing a fixed column order

### C-20: Column position does not change field meaning
Observable: Reordering the header and each data record together produces the same field-to-value assignments.
Source: choice: admins can export columns in the order convenient to them

### C-21: A header must identify each column unambiguously
Observable: A header with an empty column name or a repeated column name is rejected.
Source: choice: ambiguous columns give the importer no reliable field assignment

### C-22: A header must identify a supported user-creation field for each column
Observable: A header containing an unrecognized field is rejected.
Source: choice: rejecting unknown columns makes a mistyped field visible before the admin relies on it

### C-23: Where ordinary creation has no established field contract, the import requires an email column
Observable: In a product without an established creation field contract, naming the published email column alone satisfies the required-column check. Omitting that column fails the check.
Source: choice: one stable contact identifier is sufficient to distinguish imported users in the absence of host rules

### C-24: Where there is no existing email validation, a supplied email must contain exactly one @ with nonempty parts on each side and no whitespace
Observable: In that case, `person@example.org` meets the email syntax check. An empty value, `person`, `@example.org`, `person@`, `person@@example.org`, and `first last@example.org` each fail it.
Source: choice: a minimal syntax check catches basic input mistakes without requiring mailbox verification

### C-25: Completely empty lines outside quoted fields are ignored
Observable: Adding an empty line between otherwise valid records changes neither the created users nor the data-record count.
Source: choice: blank separators do not represent people

### C-26: Each data record must have the same field count as the header
Observable: A data record with fewer or more fields than its header is rejected.
Source: choice: a field-count mismatch can indicate displaced or missing data

### C-27: Content that cannot be read as the supported CSV is rejected
Observable: A file containing an unterminated quoted field or unreadable text bytes fails import.
Source: implied: U-7, unreadable content cannot supply a reliable set of users

### C-28: A CSV submission must contain at least one user record
Observable: A zero-byte file, a file containing only empty lines, and a header-only file each fail with an outcome indicating the absence of user records.
Source: choice: an explicit no-data outcome makes an accidental empty upload visible

### C-29: An uploaded file may contain at most 1,048,576 bytes
Observable: A valid file of exactly 1,048,576 bytes passes the byte-size check. A file of 1,048,577 bytes fails it.
Source: choice: a 1 MiB file ceiling bounds the upload while leaving room for a substantial batch

### C-30: A submission may contain at most 1,000 user records
Observable: A valid file with 1,000 user records below the byte ceiling passes the record-count check. A file with 1,001 user records below the byte ceiling fails that check. The header is excluded from the count.
Source: choice: 1,000 users is a practical batch while bounding the number of accounts affected by one submission

### C-31: A rejection communicates the reason for failure
Observable: An admin can distinguish a file-size rejection, a record-count rejection, an unreadable CSV rejection, a header rejection, a user-data rejection, and an operational failure by the outcome presented.
Source: implied: U-6 through U-8 and U-11, recovery depends on knowing why the upload failed

### C-32: A limit rejection communicates the applicable maximum
Observable: A limit rejection tells the admin the maximum for the exceeded measurement.
Source: choice: admins can size a new submission using the limit reported with the rejection

### C-33: A record-specific rejection identifies the affected source line
Observable: If a reported data-record error concerns a record starting on physical line 5, the error contains the number 5. The first physical line is line 1, including when the file begins with a header.
Source: choice: a physical line number lets the admin locate the record in the source file, including after a multiline field

### C-34: Import uses the ordinary required-field rules for user creation where they exist
Observable: An import cannot create a user missing a value that ordinary creation requires the admin to supply.
Source: implied: U-4 and U-8, creating users in bulk does not waive required user information

### C-35: Import uses ordinary user-field validation where it exists
Observable: A supplied user-field value rejected by ordinary creation validation is also rejected for import.
Source: implied: U-4 and U-8, imported accounts must meet existing user-data rules

### C-36: Omitted user values receive the ordinary creation defaults where they exist
Observable: An imported account whose optional value is omitted receives the same default as a comparable ordinarily created account.
Source: implied: U-4, imported users follow existing defaulting rules

### C-37: Imported users receive the ordinary permissions available to the creating admin
Observable: An admin cannot assign rights through import that ordinary user creation would prohibit that admin from assigning.
Source: implied: U-4 and U-10, upload does not grant additional powers

### C-38: Imported accounts follow the product's existing initial account state rules
Observable: A newly imported user starts in the same initial account state as a comparable ordinarily created user, where the product defines that state.
Source: implied: U-4, imported accounts use the ordinary account lifecycle

### C-39: Imported users follow the product's ordinary account activation requirements
Observable: Where an activation step is required for a comparable ordinarily created account, the imported user must complete that step before gaining access.
Source: implied: U-4, import does not bypass activation

### C-40: Imported users are eligible for ordinary sign-in
Observable: An imported user who satisfies the existing sign-in requirements can sign in through the ordinary user flow, where one exists.
Source: implied: U-4, bulk creation produces accounts eligible for ordinary access

### C-41: Imported users receive any onboarding notification required by ordinary user creation
Observable: If ordinary creation requires an onboarding notification for an account in the same state, the imported user receives the corresponding notification after the account is created.
Source: implied: U-4, import preserves the existing onboarding path

### C-42: Import preserves any existing audit requirements for user creation
Observable: If ordinary user creation is required to produce an audit record, a reviewer can find the required audit information for a user created by import.
Source: implied: U-4 and U-10, the creation rules still apply to the bulk entry point

### C-43: Import uses the existing identity comparison rule where one exists
Observable: Two values treated as the same user identity by ordinary creation also match for CSV import, within the same identity scope.
Source: implied: U-9 and U-12, all creation paths refer to the same users

### C-44: Where no existing identity comparison rule applies, email identifies users without regard to letter case
Observable: In that case, `person@example.org` and `Person@Example.org` identify the same user.
Source: choice: case-only differences are easy to introduce across exported lists

### C-45: A data record whose identity already belongs to a user is a conflict
Observable: Submitting a record with an identity already present in the applicable scope reports a conflict for that record, even if other supplied values match the existing account.
Source: choice: a conflict distinguishes creation from updating or silently skipping an existing account

### C-46: A repeated identity within a single file is a conflict
Observable: Submitting two records with the same new identity reports a conflict within the file.
Source: choice: an admin should resolve which source record represents the person before creation

### C-47: Import preserves existing accounts
Observable: After any import outcome, accounts that existed before the submission retain their user data.
Source: implied: U-3 and the request's use of “create”

### C-48: An invalid submission creates zero users
Observable: A CSV containing one otherwise valid new record and one invalid record creates neither account.
Source: choice: rejecting the whole batch lets the admin correct and resubmit the same file

### C-49: A submission that fails during creation leaves zero users created by that submission
Observable: If an operational failure prevents a submission from completing after creation work has begun, none of its proposed users remain from that attempt.
Source: choice: the same whole-batch outcome applies to operational failures so the same file can be retried safely

### C-50: A failed submission produces no account-creation notifications for its proposed users
Observable: If a submission fails in a product that sends onboarding notifications on user creation, its proposed users receive no such notifications from that submission.
Source: implied: U-4 and U-11, a creation notification should refer to an account the recipient can use

### C-51: A success outcome is available only after the whole submission has taken effect
Observable: While any account creation in the submission is still pending, the admin sees no success outcome for that submission.
Source: implied: U-1 and U-11, success means users have been created

### C-52: Submitting a previously completed file again creates zero additional users
Observable: The admin resubmits a file whose accounts are all still present. No second account is created for any of those identities.
Source: implied: U-3 and U-11, repeating an upload must not duplicate users

### C-53: The admin can resubmit a valid file after an unsuccessful attempt
Observable: Once the failure is resolved, an authorized admin can submit a valid file with new identities and get a successful result.
Source: implied: U-7, U-8, and U-11, a failed attempt must not prevent a subsequent import

### C-54: Concurrent creation attempts cannot create multiple users for the same identity
Observable: Overlapping requests proposing one previously unused identity leave at most one account for it, including when one submission uses ordinary creation.
Source: implied: U-12, an identity conflict can arise while creation is in progress

### C-55: Ordinary user creation remains available under its existing rules
Observable: Where the product already supports single-user creation, an admin can still use it after import is introduced with the same permissions, inputs, and outcomes.
Source: implied: U-3 and U-12, bulk creation adds a way to create users

### C-56: Import is available on normal startup with existing deployment configuration
Observable: An operator starts the release with a working pre-upgrade product configuration and an admin can submit an import without supplying import-specific configuration.
Source: choice: fixed supported limits avoid a setup prerequisite for routine use

### C-57: Introducing import requires no operator conversion of existing user data
Observable: After upgrading with existing user data, the existing accounts are accessible without exporting, modifying, or reimporting them.
Source: implied: U-3 and U-13, users already present must carry forward

### C-58: Completed imports survive an ordinary restart
Observable: After restart, accounts from a completed import remain available through ordinary user lookup.
Source: implied: U-13, created users are durable product data

### C-59: A restart during submission leaves the affected batch either complete or absent
Observable: After restarting during an import, ordinary user lookup shows either the full set created by the submission or zero accounts created by it.
Source: choice: preserving the whole-batch outcome across a restart lets the admin reconcile the attempt with a single lookup of the proposed batch

### C-60: Import is usable after an ordinary restart
Observable: After the restarted product is ready for ordinary user operations, an authorized admin can submit a new valid batch.
Source: implied: U-13, a restart must restore the feature's availability

### C-61: Where an earlier release exists, release rollback preserves access to completed imports
Observable: After returning to the earlier release following completion of an import, accounts created by that import remain accessible through the earlier release's ordinary user flows.
Source: choice: a release rollback should not undo account creation that has already completed

### C-62: Release rollback preserves access to accounts that predate the upgrade
Observable: Where an earlier release exists, accounts present before the upgrade remain accessible after returning to that release.
Source: implied: U-14, adding an import path must preserve existing accounts when the operator returns to the earlier release
