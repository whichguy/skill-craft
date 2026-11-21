## Use cases

### U-1: An admin imports a CSV to create several users at once
Flow: The admin finds CSV import in user management, checks what the file must contain, and submits one CSV with several eligible user records. The admin sees the result and can find the created accounts through normal user management.
Source: request

### U-2: A first-time importer prepares a CSV their deployment can accept
Flow: Before submitting a file, the admin checks the accepted columns, required values, and file conventions. They use those instructions to prepare a CSV, including a field with a comma in its value when the corresponding user field allows it.
Source: implied: An admin must be able to prepare the CSV the request asks them to upload.

### U-3: A returning admin imports another group without changing earlier accounts
Flow: The admin submits a CSV with new users and sees the additional accounts. If they resubmit the original CSV or include one account that already exists, the import reports the conflict and the original accounts keep their current details.
Source: implied: Repeated bulk creation must coexist with users already present.

### U-4: An admin submits an empty import and learns why nothing happened
Flow: The admin submits without selecting a file, selects a zero-byte file, or submits a supported CSV layout with zero user records. They see why the import could not proceed and no accounts are created.
Source: implied: The upload can contain no user data.

### U-5: An admin checks the upload boundaries to size a batch
Flow: The admin imports a valid file at the applicable row or file size limit. A file beyond either limit is refused with feedback that identifies the exceeded limit.
Source: implied: An admin with a large CSV needs to know which batches the service accepts.

### U-6: An admin corrects a file that cannot be read as a user CSV
Flow: The admin submits a file whose contents are not accepted CSV, a malformed CSV, or a CSV missing required columns. The import reports what prevented it from reading the file and the admin can submit a corrected file.
Source: implied: The upload can be the wrong file or contain structural errors.

### U-7: An admin fixes invalid or conflicting user records
Flow: The admin submits a readable CSV containing a row that fails normal account validation, a disallowed account setting, or two rows for the same user identity. The admin can locate the offending data, fix it, and submit the file again.
Source: implied: Uploaded records must qualify for creation as users.

### U-8: An unauthorized caller attempts an import and is refused
Flow: A signed-out visitor or signed-in non-admin attempts an import, including by submitting directly to the service. An admin attempts to create a user in a scope they cannot manage. Each attempt is denied without creating a user.
Source: implied: The request grants the action to admins subject to their existing user-creation permissions.

### U-9: An admin recovers from a failed or interrupted submission
Flow: The admin encounters a failed upload, a failed account write, or a lost response. They check the outcome where available and can submit again. An interrupted attempt leaves either the full batch of accounts or none of it. If it had already completed, resubmission does not create duplicate accounts.
Source: implied: Uploads and account creation can fail, and admins can retry.

### U-10: Two authorized callers try to create the same account concurrently
Flow: An import overlaps with another import or an ordinary user creation in the same uniqueness scope. At most one creation of that identity succeeds. The losing import gets conflict feedback.
Source: implied: Bulk creation shares user identities with the existing creation paths.

### U-11: An operator deploys and configures the service against existing user data
Flow: The operator starts the updated version with an existing deployment's data and user-management settings. Existing accounts remain accessible. Admins with the applicable permission can import under the configured account policies and see the import limits before submitting.
Source: implied: The new version has to work in the deployments that already create users.

### U-12: An operator restarts the service or returns to the previous version
Flow: The operator restarts the service after a completed import or during a pending import and checks which accounts exist. When the operator returns to the previous version, they can still manage users created before the upgrade and users successfully imported while it was deployed. Those users can still access their accounts under the existing sign-in rules.
Source: implied: Operators may restart or revert a release containing bulk creation.

### U-13: A newly imported user accesses their account
Flow: After a successful import, the recipient follows the deployment's normal account setup process. Their account has the same sign-in eligibility and permissions as an equivalent normally created account.
Source: implied: Bulk creation produces ordinary users.

### U-14: An admin continues to create individual users
Flow: The admin uses the existing single-user creation path before and after using CSV import. They still create a user with the same permissions, inputs, and validation as before.
Source: implied: Bulk creation is an additional way to create users.

## Clauses

### C-1: An authorized admin can upload a CSV for bulk user creation.
Observable: An admin allowed to create users can select and submit a CSV through the application's user-management experience.
Source: request

### C-2: One successful CSV submission creates one user per eligible record.
Observable: An admin submits a CSV containing three valid records for distinct new users and finds three accounts corresponding to those records in normal user management.
Source: request

### C-3: The import explains how to prepare an accepted CSV before submission.
Observable: Before submitting a file, the admin can find the accepted layout, the columns the deployment recognizes, the required values, and the accepted text encoding.
Source: implied: U-2 requires the admin to know which CSV the application can interpret as users.

### C-4: CSV quoting preserves a comma within a field value.
Observable: An otherwise valid record with a quoted comma in an allowed field creates a user with the complete value in that field.
Source: implied: U-2 uses CSV, whose field quoting allows delimiters within values.

### C-5: CSV quoting preserves an escaped quote within a field value.
Observable: An otherwise valid record with a doubled quote within a quoted field creates a user with one literal quote at that position.
Source: implied: U-2 uses CSV, whose field quoting represents a literal quote with a doubled quote.

### C-6: A line break within a quoted CSV field does not start a new user record.
Observable: A quoted field containing a line break is treated as part of one record, subject to the existing validation of that field.
Source: implied: U-2 uses CSV, whose field quoting allows a record to span multiple lines.

### C-7: Anonymous callers cannot submit an import.
Observable: A signed-out caller attempts a direct submission and is denied without creating users.
Source: implied: The request specifies admins.

### C-8: Signed-in non-admins cannot submit an import.
Observable: A signed-in non-admin attempts a direct submission and is denied without creating users.
Source: implied: The request specifies admins.

### C-9: Import honors existing restrictions on where an admin may create users.
Observable: An admin with limited user-management scope attempts to create a user outside that scope and is denied.
Source: implied: U-8 applies existing user-creation authority to a second entry point.

### C-10: Import applies existing required-field rules to each user.
Observable: A record missing a value required for normal creation under the same settings is rejected for the missing value.
Source: implied: U-7 creates users subject to the deployment's existing requirements.

### C-11: Import applies existing field validation to each user.
Observable: A record containing a value the normal creation path rejects for its format, length, or allowed values is rejected on the same basis.
Source: implied: U-7 must create the same kind of account as normal creation.

### C-12: Import preserves existing rules for deriving the stored values of supplied fields.
Observable: For equivalent valid inputs, an imported account has the same stored field values as a normally created account after any existing normalization.
Source: implied: U-7 and U-13 use the existing meaning of account fields.

### C-13: Import applies existing account defaults.
Observable: When an optional field with an existing default is omitted, the created account receives the same default as an equivalent normally created account.
Source: implied: U-11 and U-13 rely on deployment settings for new users.

### C-14: Import enforces existing restrictions on which account settings the caller may assign.
Observable: A caller supplies a role, permission, or other account setting they cannot assign through normal creation and the import refuses that assignment.
Source: implied: U-7 and U-8 must respect existing limits on administrative access.

### C-15: Import enforces existing user-creation quotas where they apply.
Observable: In a deployment with a user quota, an import cannot make the resulting user count exceed the configured quota.
Source: implied: U-5 and U-11 operate within the deployment's account policies.

### C-16: Import uses the existing user identity uniqueness rules.
Observable: When a record matches an existing account under the deployment's normal identity comparison and scope, it cannot create another account with that identity.
Source: implied: U-3 and U-10 share one population of users with ordinary creation.

### C-17: Import leaves existing accounts untouched.
Observable: After submitting a file that supplies changed values for an existing user, the admin sees that user's prior values in user management.
Source: implied: The request calls for creation, as illustrated by U-3.

### C-18: An import containing duplicate user identities is rejected.
Observable: The admin submits two otherwise valid records for the same new identity in the same uniqueness scope and sees a duplicate conflict.
Source: choice: Rejecting ambiguous input lets the admin decide which record to keep.

### C-19: Concurrent creation cannot produce duplicate user identities.
Observable: When valid concurrent submissions contend for the same identity in the same uniqueness scope, at most one account is created, whether the submissions use import or normal creation.
Source: implied: U-10 requires uniqueness under overlapping submissions.

### C-20: The service refuses submission without a file.
Observable: An admin attempts to submit without selecting a file and is told that a CSV is required.
Source: implied: U-4 requires a CSV upload to supply the user data.

### C-21: The service refuses a CSV with zero user records.
Observable: A zero-byte file or a file containing only non-record content allowed by the accepted layout produces feedback that there are no users to import.
Source: implied: U-4 supplies no users to create.

### C-22: The service refuses content that cannot be parsed in an accepted CSV format.
Observable: A file with invalid CSV quoting or content that cannot be read in the accepted format is rejected with feedback about the file, even if its name ends in .csv.
Source: implied: U-6 supplies an unreadable CSV or a different file type.

### C-23: The service refuses a CSV whose layout lacks a required user column.
Observable: An otherwise readable CSV omitting a required column is rejected with feedback identifying the missing column.
Source: implied: U-6 needs to distinguish a layout problem from invalid data within a record.

### C-24: Empty lines between records do not create user records.
Observable: An otherwise valid two-record CSV with a completely empty line between its records is treated as containing two user records.
Source: choice: An empty line between records can be ignored because it supplies no account data.

### C-25: The import accepts up to 1,000 user records per file when other requirements are met.
Observable: A file with exactly 1,000 valid user records can be imported when it satisfies the other requirements. A file with 1,001 otherwise valid user records is refused.
Source: choice: A 1,000-record ceiling allows substantial batches with a bounded submission size.

### C-26: The import accepts files up to 5,242,880 bytes when other requirements are met.
Observable: A valid CSV of exactly 5,242,880 bytes can be imported when it satisfies the other requirements. A CSV of 5,242,881 bytes is refused. Only the CSV file itself counts toward its size.
Source: choice: A 5 MiB ceiling bounds upload size even when individual records are large.

### C-27: Admins can see the applicable import limits before submitting a file.
Observable: An admin preparing an upload can find the record count limit and the file size limit before submission.
Source: implied: U-5 and U-11 require callers to size a batch against the service they use.

### C-28: An import rejection identifies the reason the service refused it.
Observable: When the service rejects a submission, the admin can distinguish the reason, such as invalid data, an account conflict, an exceeded limit, or a policy restriction.
Source: implied: U-3, U-6, U-7 and U-10 require a caller to know why a submission failed.

### C-29: Feedback identifies the offending record for a record-specific rejection.
Observable: An admin told that a record failed validation can locate it in the submitted file from the feedback.
Source: choice: A record reference makes a reported error actionable in a bulk file.

### C-30: Import commits account creation for a file as a single outcome.
Observable: After a file is rejected or an account write fails, the admin finds no accounts created by that submission, even if some records were eligible. If processing is interrupted before the admin learns the outcome, the admin later finds either every account from that submission or none.
Source: choice: One outcome per file lets an admin correct a failed submission and retry the same batch.

### C-31: An incomplete upload creates no accounts.
Observable: The transfer stops before the entire file is received. After recovery, the admin sees no users created from that submission.
Source: implied: U-9 submits a file whose full contents may never reach the service.

### C-32: The import reports success only after its accounts are saved.
Observable: After the service reports success, the admin can open user management in a new session and find the created accounts.
Source: implied: U-1 and U-9 rely on success to determine whether another submission is needed.

### C-33: A successful import reports how many users it created.
Observable: After a successful import of three users, the result communicates that three accounts were created.
Source: choice: A count lets the admin verify the result against the expected batch size.

### C-34: A completed import survives a service restart.
Observable: After restarting the updated service following a successful import, the operator finds the same imported accounts.
Source: implied: U-12 treats created accounts as persistent users.

### C-35: A valid corrected file can be submitted after a failed attempt.
Observable: After the admin resolves the cause of a prior rejection, they can submit an eligible CSV using the same import entry point.
Source: implied: U-6, U-7 and U-9 require recovery from a failed attempt.

### C-36: Deployment preserves access to accounts created before the update.
Observable: An operator starts the updated release against existing user data and can find and manage the same accounts with their existing details.
Source: implied: U-11 continues to use existing account data.

### C-37: Upgrading preserves existing accounts' sign-in eligibility.
Observable: A user who could sign in before the upgrade can do so with the same account after deployment when their account conditions are unchanged.
Source: implied: U-11 continues to serve the deployment's existing users.

### C-38: Import is available under the deployment's existing configuration.
Observable: An operator starts the updated service with a working user-management configuration. An eligible admin can use import without the operator supplying new configuration.
Source: choice: The existing configuration is enough to make bulk creation available.

### C-39: Reverting to the previous version preserves access to pre-upgrade accounts.
Observable: After version rollback, an operator can find and manage users that existed before the upgrade with their existing account details.
Source: implied: U-12 returns a live deployment to the previous release.

### C-40: Version rollback preserves pre-upgrade accounts' sign-in eligibility.
Observable: A user who could sign in before the upgrade can still sign in after rollback when their account conditions are unchanged.
Source: implied: U-12 keeps existing users able to use their accounts after a version rollback.

### C-41: Reverting to the previous version preserves access to successfully imported accounts.
Observable: After version rollback, an operator can find and manage successfully imported users as ordinary accounts in the previous release.
Source: implied: U-12 rolls back the version while carrying forward user data.

### C-42: Version rollback preserves imported accounts' sign-in eligibility.
Observable: A successfully imported user who could sign in before rollback can do so with the same account in the previous release when their account conditions are unchanged.
Source: implied: U-12 carries forward newly created users.

### C-43: Imported users follow the deployment's ordinary account setup process.
Observable: An imported account enters the same setup state as an equivalent normally created account, including any existing activation or verification requirement.
Source: implied: U-13 needs to access the imported account under existing account rules.

### C-44: Imported users receive the deployment's normal new-account communications where applicable.
Observable: If ordinary creation under the same settings sends an invitation or other new-account communication to a user, that user receives the corresponding communication after a successful import.
Source: implied: U-13 relies on communications that are already part of creating an account.

### C-45: Imported accounts follow existing sign-in eligibility rules.
Observable: An imported user can sign in under the same account conditions as an equivalent normally created user.
Source: implied: U-13 creates an account that can be used through the normal sign-in path.

### C-46: Imported accounts have the same effective access as equivalent normally created accounts.
Observable: An imported account with the same attributes as a normally created account is allowed and denied the same actions.
Source: implied: U-13 uses existing account permissions.

### C-47: Import preserves existing audit behavior for user creation.
Observable: Where normal user creation emits an audit record, the operator can find a corresponding creation record for an imported account with the information normally captured for that action.
Source: implied: U-11 continues to operate under the deployment's existing user-management policies.

### C-48: Ordinary single-user creation retains its existing behavior.
Observable: Existing callers submitting their usual single-user creation inputs continue to get the same results under the same permissions and settings.
Source: implied: U-14 uses the creation path that the request supplements.
