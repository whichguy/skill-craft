## Use cases

### U-1: An admin finds CSV import to prepare a first upload
Flow: The admin opens user management, finds CSV import, and checks what user information the file must contain before selecting it.
Source: implied: an admin must be able to find and use the upload in the request

### U-2: An admin uploads a CSV to create several users
Flow: The admin selects a CSV containing several new users, submits it, observes the creation outcome, then finds the new users through ordinary user management.
Source: request

### U-3: An admin uploads a one-user or empty CSV to check what it does
Flow: The admin submits a file with one valid user and sees that user created. On a separate attempt, a zero-byte file or a file with just a valid header reports that it contained no user records.
Source: implied: a CSV can contain one user or no users

### U-4: An admin uploads a large CSV to import as many users as the deployment supports
Flow: The admin checks the applicable limits, submits a valid file at a limit, and sees it processed. An upload over a limit is refused with the applicable limit identified.
Source: implied: a bulk upload can reach or exceed the upload boundary

### U-5: An admin corrects a CSV to recover from input errors
Flow: The admin submits a file with an unreadable CSV structure or invalid user data, sees where the problem is when it can be located, corrects the file, and submits it again.
Source: implied: uploaded files can contain mistakes

### U-6: An admin imports into a populated user directory to add new users
Flow: The admin submits a file containing an identity already in the directory or more than once in the file, learns which input conflicts, and can submit a corrected file containing new users.
Source: implied: bulk-create adds users to a directory that can already contain users

### U-7: A visitor or non-admin attempts an import and is refused
Flow: A signed-out visitor or signed-in non-admin attempts to reach or submit an import and cannot create users through it.
Source: implied: the request gives the operation to admins

### U-8: An admin checks an interrupted upload to determine whether to retry
Flow: The admin loses the connection or encounters a service interruption. After reconnecting, the admin checks the original attempt until it is resolved. If it ended without creating users, the admin can start a new attempt.
Source: implied: an upload or user creation can fail or lose its response

### U-9: An operator enables or pauses CSV imports to manage availability
Flow: The operator configures the deployment's import limits, enables imports when the prerequisites are met, and can stop intake during maintenance without discarding a committed batch.
Source: implied: an operator must be able to put the requested feature into service and manage interruptions

### U-10: An operator checks or rolls back a deployment to recover service
Flow: The operator checks the outcomes of affected imports, restores service or reverts the release, and checks that existing and successfully imported users remain available under ordinary account operations.
Source: implied: this feature runs against durable user data that must survive service recovery

### U-11: Two admins submit overlapping batches to add users
Flow: Two valid uploads compete for an identity governed by the same uniqueness rule. One batch creates that identity. The other sees a conflict and can correct its file.
Source: implied: admins can use the same user directory concurrently

### U-12: An admin checks a finished import after losing the response
Flow: The admin reconnects, finds the earlier attempt, checks what committed, and avoids repeating a successful submission. If the result is still pending, the admin can check it again.
Source: implied: account creation can finish even when its response does not reach the uploader

### U-13: An imported user follows ordinary account setup to gain access
Flow: The new user follows ordinary account setup for the destination. If setup fails, the user or admin follows the ordinary recovery path where one is available.
Source: implied: U-2 creates user accounts the destination can use

### U-14: An admin leaves file selection without submitting to avoid an unintended upload
Flow: The admin opens the file selection action, dismisses it or changes the selection, and returns to user management. No users are created until the admin submits the intended file.
Source: implied: U-2 requires the admin to choose what to upload

### U-15: An admin resubmits a previously imported CSV to understand what is still needed
Flow: After a successful import, the admin submits the same CSV as a new attempt. The result reports a conflict for an identity still reserved by the destination. The admin can use a corrected file to create only users who are still new.
Source: implied: the same input can be submitted again after a successful run

## Clauses

### C-1: An authorized admin can submit a CSV for user creation
Observable: An authorized admin provides a CSV file to the import action for user creation.
Source: request

### C-2: A CSV import can create multiple users in one submission
Observable: Submit one valid file for two distinct new identities and find two corresponding newly created user accounts.
Source: request

### C-3: The import accepts a file containing one valid new user
Observable: Submit a valid CSV with exactly one user record and confirm that one account is created.
Source: choice: a smaller batch uses the same workflow as a larger one

### C-4: A CSV with no user records creates zero users
Observable: Submit a header-only CSV and observe zero new accounts attributable to the submission.
Source: implied: U-3's empty input supplies no users to create

### C-5: An otherwise valid input with zero user records reports that it is empty
Observable: Submit a zero-byte file or a file with just a valid header and see that no user records were supplied.
Source: choice: explicit empty-file feedback helps the admin distinguish an empty file from a completed creation

### C-6: An upload over an effective import limit is refused
Observable: Submit a file that exceeds one active import limit while satisfying the other limits and see it refused.
Source: choice: U-4 needs a bounded upload with a predictable boundary

### C-7: A valid upload exactly at an effective import limit qualifies under that limit
Observable: Submit a valid file at an advertised byte or record ceiling with every other prerequisite met and see it accepted.
Source: choice: an advertised maximum is inclusive

### C-8: An attempted import with unreadable CSV structure reports an input error
Observable: Submit a file with an unterminated quoted field and see a CSV structure error.
Source: choice: U-5 needs to distinguish unreadable structure from invalid user data

### C-9: An unauthenticated caller cannot submit an import
Observable: Attempt to submit without credentials and see an access refusal.
Source: implied: the request gives the action to admins and an unauthenticated caller has no demonstrated admin authority

### C-10: A signed-in non-admin cannot submit an import
Observable: Submit to the import action as a signed-in non-admin and see an access refusal.
Source: implied: the request restricts U-2 to admins

### C-11: An import never changes the attributes of an account already occupying the submitted identity
Observable: Submit a record containing an existing identity and a different value for an editable field. The existing account retains its original value.
Source: implied: bulk-create is an addition to the directory

### C-12: An import that completes reports its creation outcome
Observable: After a submission reaches an outcome, the admin can tell whether the requested user creation took effect.
Source: choice: U-2 needs a reliable way to distinguish creation from refusal or failure

### C-13: Failure of required account storage is visible to the admin
Observable: Interrupt durable account storage during an accepted import, restore access to the import outcome, and see a service failure if the batch could not commit.
Source: choice: U-8 needs to distinguish service failure from invalid input

### C-14: An operator can stop acceptance of new imports
Observable: Pause import intake and see a new otherwise eligible submission refused while intake is paused.
Source: choice: U-9 needs maintenance control over new work

### C-15: An operator can resume import intake when the feature is ready
Observable: Resume intake after maintenance and see a new otherwise eligible submission accepted.
Source: choice: U-9 needs to restore the feature after a pause

### C-16: Committed imports remain committed after a service restart
Observable: Complete an import, restart the application, and find its accounts in the user directory.
Source: implied: U-10's created users are ordinary durable accounts

### C-17: Rolling back the import feature preserves committed users
Observable: Revert the import release and look up an account created by a completed import using the previous release's ordinary user management.
Source: choice: U-10 needs a way to reverse a feature deployment while keeping completed account creation

### C-18: An admin with user-creation authority can discover CSV import from user management
Observable: With intake enabled, open user management as an eligible admin and find a way to start a CSV import.
Source: choice: U-1 needs a discoverable entry point in the area responsible for users

### C-19: An admin can learn the accepted column names before submission
Observable: Open import guidance before choosing a file and identify the names the upload recognizes.
Source: choice: C-1 presupposes a way to prepare an acceptable file

### C-20: The import determines which user a record describes from the destination's account identity rule
Observable: Use the same account identity in a CSV and in ordinary user management and observe that both refer to the same identity under the destination's rules.
Source: choice: C-2 needs an account identity model and reusing the destination's model resolves ambiguity without inventing a new identifier

### C-21: CSV column positions may vary when the header identifies the fields
Observable: Move a recognized header and its corresponding data cells to a different position in a valid file and see the same account values created.
Source: choice: C-19 gives admins a named schema without requiring a fixed column order

### C-22: The import rejects a CSV with user records when its header omits a required column
Observable: Submit a CSV with data records but without a required header and see which required column is missing.
Source: choice: C-19 makes required columns enforceable before creation

### C-23: The import rejects a header that maps more than one column to the same account field
Observable: Submit a CSV with a repeated recognized header and see the ambiguous field identified.
Source: choice: C-19 must assign each writable value unambiguously

### C-24: The import rejects an unrecognized header
Observable: Add an unrecognized column to a valid file and see the unsupported column identified.
Source: choice: silently dropping a mistyped optional header could lose data the admin intended to import

### C-25: Each user record has the same number of fields as the header
Observable: Submit a data record with one field fewer or one field more than its header and see a record structure error.
Source: choice: C-19 needs unambiguous mapping from cells to fields

### C-26: The import accepts UTF-8 CSV text
Observable: Submit a CSV encoded in UTF-8 with a character outside ASCII in a field that permits it and find that character in the resulting account.
Source: choice: C-1 needs a portable baseline that can represent international user data

### C-27: A leading UTF-8 byte-order mark does not change the first header
Observable: Add a UTF-8 byte-order mark to an otherwise valid file and see that its first column still maps to the same field.
Source: choice: common CSV exporters add this mark

### C-28: The import recognizes comma-separated CSV fields
Observable: Submit a valid CSV with multiple recognized fields separated by commas and find the values in the corresponding account fields.
Source: choice: comma separation supplies a portable baseline without excluding documented additional dialects

### C-29: A quoted field can contain a comma
Observable: Use a quoted value containing a comma in a field that allows it and find one field value including the comma in the created account.
Source: choice: C-28 needs a way to represent a literal comma

### C-30: A doubled quote inside a quoted field represents one literal quote
Observable: Use a quoted value containing a doubled quote in a field that allows it and find one quote at that position in the created account.
Source: choice: C-29 needs a way to represent the quoting character itself

### C-31: A line break inside a quoted field belongs to that field
Observable: Submit one logical user record containing a quoted line break. The import handles it as one record, whether the destination accepts the field value or rejects it during account validation.
Source: choice: C-25 counts logical records and a quoted line break cannot begin a second user

### C-32: A CSV with LF record endings is supported
Observable: Submit a valid file with LF record endings and see user creation succeed.
Source: choice: this is a common CSV export convention

### C-33: A CSV with CRLF record endings is supported
Observable: Submit a valid file with CRLF record endings and see user creation succeed.
Source: choice: this is a common CSV export convention

### C-34: The last CSV record can end at the end of the file
Observable: Remove the line ending after the last complete data record in a valid file and see the last user created.
Source: choice: a final line ending is unnecessary to identify a complete final record

### C-35: A physically empty line outside a quoted field is skipped
Observable: Add completely empty lines before the header, between user records, or after the final record and see the same accounts created.
Source: choice: incidental empty lines carry no user data

### C-36: The import rejects text that cannot be decoded in a supported encoding
Observable: Submit a file whose bytes are invalid under the deployment's supported encodings and see an encoding error.
Source: choice: replacing undecodable user data can change account values or identities

### C-37: A blank required field fails validation when ordinary creation requires a value
Observable: Leave a required account value empty in one record and see the missing value identified at that record.
Source: choice: C-22 guarantees a column exists and each record still needs a usable value

### C-38: A blank optional field takes the ordinary account-creation default for an omitted value
Observable: Import a record with an empty optional field and compare the resulting field with an otherwise equivalent account created with that field omitted.
Source: choice: C-19 needs consistent handling of empty optional cells

### C-39: A reported record error identifies its location in the source file
Observable: Put one invalid value in a file with several user records and use the result's record location to find that record in the source file, including when a preceding value contains an embedded line break.
Source: choice: U-5 needs a location the admin can map back to the source without requiring a numbering convention

### C-40: The outcome identifies the invalid field when a rejection can be attributed to one field
Observable: Submit a record with an invalid value in one field and see which field needs correction.
Source: choice: C-39 identifies a record and U-5 needs to know what to fix there

### C-41: The import applies the destination's account value rules
Observable: Try a value that ordinary account creation rejects for a field and see the same value rejected through import.
Source: choice: U-2 creates ordinary accounts whose accepted values must follow the destination's account policy

### C-42: Imported values follow ordinary account normalization
Observable: Import a field value whose spelling or whitespace the destination normally normalizes and find the value after the same normalization.
Source: choice: C-20 and C-41 need stable identity and value interpretation across creation paths

### C-43: The import reports an existing identity as a conflict
Observable: Submit an identity already reserved by an account under the destination's identity rule and see a conflict associated with the submitted record.
Source: choice: C-11 permits several possible conflict policies and a refusal gives the admin a clear correction path

### C-44: The import reports a repeated identity within one file as a conflict
Observable: Submit two records that resolve to the same account identity and see the data conflict with enough record locations to find the duplicates.
Source: choice: C-20 must resolve repeated identities without silently choosing a winning record

### C-45: The import rejects the entire batch when any user record is invalid
Observable: Submit one valid new user alongside one record that fails account validation and find zero accounts created by the submission.
Source: choice: a batch the admin can correct and resubmit needs one predictable creation outcome

### C-46: The admin can determine the effective file byte ceiling before uploading
Observable: Open import guidance and find the current maximum file size in bytes.
Source: choice: C-6 and C-7 need measurable limits before the admin prepares a file

### C-47: The file byte ceiling measures the submitted file's bytes
Observable: Submit a file whose own size equals the advertised byte ceiling. The byte check passes even though the upload request is larger than the file.
Source: choice: an admin can measure the local file size directly

### C-48: The user-record ceiling counts logical user records
Observable: Submit a file at the record ceiling with a header, physically empty lines, or embedded quoted line breaks and see the record limit accept it.
Source: choice: U-4's user-record limit must count users consistently with CSV parsing

### C-49: An over-limit refusal identifies the applicable ceiling
Observable: Exceed only the byte ceiling or only the user-record ceiling and see the kind of limit exceeded plus its effective value.
Source: choice: U-4 needs enough information to reduce the next file

### C-50: A deployment cannot enable import with a record ceiling below two
Observable: Set the record ceiling to one and try to enable intake. Intake remains unavailable.
Source: choice: C-2 requires capacity for at least two users in one submission

### C-51: The operator can establish effective import limits before enabling intake
Observable: Set the deployment's import limits, enable intake, and see the active limits reflected in the import guidance.
Source: choice: the workspace supplies no universal byte or row budget and the operator must publish the capacity the deployment can support

### C-52: An import publishes the batch's new accounts as a unit
Observable: Observe the destination's authoritative account view during a multi-user import without concurrent account changes. The batch contributes either zero accounts or its full set.
Source: choice: C-45's rejection outcome must also hold at the durable creation boundary

### C-53: An existing-identity conflict leaves the whole batch uncreated
Observable: Submit a batch with one new identity and one existing identity and verify the new identity was not created by that submission.
Source: choice: C-43 follows the same all-or-nothing rule as account validation

### C-54: A within-file identity conflict leaves the whole batch uncreated
Observable: Submit a file containing a repeated identity and an unrelated new one and verify that the import created zero accounts.
Source: choice: C-44 follows the same all-or-nothing rule as account validation

### C-55: The account identity rule holds across simultaneous creation paths
Observable: Race two otherwise valid imports for an identity under the same uniqueness rule, or race an import against ordinary creation for that identity. At most one account is created for the identity.
Source: choice: U-11 must preserve destination identity semantics across all writers

### C-56: An import losing an identity race reports a conflict
Observable: Race an import with another successful creation of a shared identity and see the losing import report an identity conflict.
Source: choice: U-11 needs the same correction path for a concurrent conflict as for a pre-existing one

### C-57: An import uses the current identity reservation at creation
Observable: Remove or restore a competing account during an import and see the import outcome follow the destination's reservation rule at the point creation is decided.
Source: choice: U-6 and U-11 need the same treatment of reserved identities, including retired identities where the destination reserves them

### C-58: Reuploading a successful file as a new attempt follows current identity rules
Observable: Resubmit the same file as a new attempt while its accounts still occupy those identities and see an existing-identity conflict.
Source: choice: a deliberate new submission uses present directory state

### C-59: An admin can identify an attempt before it can create users
Observable: Start a submission and lose the connection after the file is sent. Use the attempt available before creation could occur to check its outcome later.
Source: choice: U-12 needs a way to match a lost response to the submission that caused it

### C-60: A replay of the same submission cannot create users a second time
Observable: Deliver the same already completed submission again, including after deleting one of its created accounts, and verify that the replay creates zero additional accounts.
Source: choice: repeated delivery in U-12 is one intent even if the directory changes later

### C-61: A concurrent replay refers to the same attempt
Observable: Deliver the same unresolved submission twice at once and check that both deliveries resolve to one attempt with one outcome.
Source: choice: C-60 also applies when a retry arrives before the first response

### C-62: An attempt associated with a complete file cannot be reused for different file contents
Observable: Once a complete file has been accepted for an attempt, reuse its reference with different file contents and observe a mismatch refusal for the new delivery.
Source: choice: C-59 must keep its meaning when a retry carries different data

### C-63: A terminal result records what that attempt did
Observable: Complete an import, later change or delete an account it created, and check the result again within the recovery window. It still conveys the original creation outcome.
Source: choice: U-12 needs the submission's outcome rather than a reconstruction from current directory contents

### C-64: An unresolved attempt is distinguishable from a completed attempt
Observable: Delay an accepted import and check its result before creation is resolved. It is reported as unresolved.
Source: choice: U-8 needs to avoid starting a replacement import while the first can still commit

### C-65: A submitted attempt reaches a terminal outcome once recovery is possible
Observable: Interrupt processing after acceptance, restore the required services, and observe the same attempt eventually report success or non-creation without a replacement submission.
Source: choice: C-64 needs an end state that lets the admin make a retry decision

### C-66: A terminal non-creation outcome rules out later creation by that attempt
Observable: Observe a terminal refusal or failure, then restore services or deliver a delayed replay. No account is subsequently created by that attempt.
Source: choice: U-8 needs a terminal failure to be safe to act on

### C-67: A committed batch has a recoverable success outcome
Observable: Drop the response immediately after accounts commit, then recover the attempt within its recovery window and see success.
Source: choice: C-63 and C-66 require the response to reflect committed effects even after a connection failure

### C-68: Success reports the number of users created by the batch
Observable: Import a valid CSV with two new identities and see a created-user count of two.
Source: choice: U-2 needs a way to compare the outcome with the submitted batch

### C-69: An eligible admin can recover their own result within the advertised recovery window
Observable: Leave the import view after a terminal result and return within the stated window as the submitting admin with current access. Retrieve the same result.
Source: choice: U-12 needs a bounded period to recover a lost result

### C-70: The result recovery window is disclosed before submission
Observable: Before choosing to submit, determine how long a terminal result will remain available and which event starts that period.
Source: choice: C-69 needs a usable recovery bound without imposing a universal retention period

### C-71: An unresolved accepted attempt remains recoverable
Observable: Check an accepted attempt after the nominal terminal-result retention duration has elapsed while it is still unresolved and see its current state.
Source: choice: the recovery window in C-69 starts when the attempt reaches its terminal outcome

### C-72: An expired attempt does not behave like a new upload
Observable: Replay a submission after its result recovery window ends and verify that the replay cannot create users.
Source: choice: C-60 must survive expiry of the visible result

### C-73: Import intake pause lets accepted attempts resolve
Observable: Pause intake while an accepted attempt is pending and see that attempt continue under its normal completion rules.
Source: choice: C-14 stops new work with a well-defined disposition for work already accepted

### C-74: An accepted attempt uses the import ceilings in force at acceptance
Observable: Accept a file under the current ceilings, lower one ceiling before processing completes, and see the already accepted attempt retain the original ceiling.
Source: choice: C-51 needs a predictable cutoff for configuration changes

### C-75: Account creation requires the submitting admin's current authority
Observable: Revoke the submitting admin's creation authority before the accepted batch reaches creation and see that the batch creates no users.
Source: choice: the access restriction in C-10 applies even after intake

### C-76: Lost upload connectivity before receipt of the complete file creates no users
Observable: Disconnect before the service receives the complete file and verify no accounts are created from the partially transferred file.
Source: choice: C-52 makes a completely received file the unit of creation

### C-77: Closing the import view after acceptance does not cancel the attempt
Observable: Close the view after acceptance and recover the same attempt to see its eventual outcome.
Source: choice: U-12 needs durable submission behavior independent of the original view

### C-78: A terminal write failure leaves the import with zero created accounts
Observable: Cause a failure during durable creation that the service reports as terminal failure and verify the batch added zero users.
Source: choice: C-52 applies even when an attempt fails during creation

### C-79: Imported users follow ordinary account activation rules
Observable: Compare the initial activation state and setup requirements of an imported user with those for an equivalent account ordinarily created in the same destination.
Source: choice: U-13 needs normal setup semantics without assuming an email or invitation provider

### C-80: Import never starts user-facing account setup for an uncommitted account
Observable: Submit a batch that fails after account values have been accepted for validation and verify that prospective users receive no setup communication attributable to it.
Source: choice: C-52 would be misleading if people were invited to accounts that were never committed

### C-81: Replaying an import does not trigger a new account setup for a user already created by that import
Observable: Replay a successful attempt after its setup has started and observe that the replay starts no separate setup for those users.
Source: choice: C-60 protects the normal consequences of account creation as well as account state

### C-82: A post-creation setup failure does not change the batch's committed creation result
Observable: Where ordinary setup uses a downstream service, make it fail after the accounts commit and verify the import still reports those accounts as created.
Source: choice: U-13's downstream setup is a distinct operation from durable account creation

### C-83: Setup failures for imported users use the destination's ordinary setup recovery
Observable: Where setup can fail after creation, use the same status and recovery operations available for an equivalent ordinarily created account.
Source: choice: U-13 needs a recovery path after C-82 without recreating users

### C-84: The upload is available in the destination's browser-based administration
Observable: Open the deployment's administration in a supported browser and reach the CSV file selection action as an authorized admin.
Source: choice: no application runtime is supplied and a browser is the assumed admin surface for the file upload

### C-85: The browser upload accepts a file made available by the admin
Observable: Supply a local CSV through the browser's file-selection flow and see that file available for submission.
Source: choice: C-84 adopts a browser surface whose HTML File Upload rule uses the files selected by the user. [WHATWG HTML File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file))

### C-86: The browser upload does not depend on the file's original local directory
Observable: Select otherwise identical CSVs with the same name from two different local folders and see the same validation behavior for each.
Source: choice: C-84 adopts a browser surface whose HTML File Upload rule excludes local path components from filenames. [WHATWG HTML File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file))

### C-87: The advertised file ceiling fits the deployment's full request-body allowance
Observable: Send an ordinary upload at the advertised file size through the deployed request path and verify that the request is not blocked by an intermediary's size limit. The actual host or gateway body allowance is unconfirmed until deployment.
Source: choice: U-4 must fit the hosting runtime's request-body rule after upload overhead, and no hosting provider or gateway is specified

### C-88: Hitting a request deadline does not resolve an accepted import by itself
Observable: On a deployment with a request deadline, delay the original response past it after the attempt is accepted. Check the same attempt and see its true creation state. The actual host or gateway deadline is unconfirmed until deployment.
Source: choice: U-12 must remain usable when a hosting runtime enforces a response deadline shorter than the time needed to determine the outcome

### C-89: Hitting an execution deadline cannot leave an accepted import permanently unresolved
Observable: On a deployment with a hard execution limit, interrupt processing at that limit and restore the service. See the same attempt resolve even though its original execution has ended. The actual execution limit is unconfirmed until deployment.
Source: choice: C-65 must hold when the hosting runtime terminates work at its execution limit

### C-90: Live deployments receive CSV uploads over HTTPS
Observable: Access the live administration over an unencrypted connection and verify the file is submitted only after moving to an HTTPS connection or is refused.
Source: choice: the CSV may contain personal account information and needs protection in transit outside development

### C-91: Intake stays unavailable until the deployment has an authorized account creation destination
Observable: Try to enable intake before the destination's identity, writable fields, access policy, and account setup rules are established. Observe that import remains unavailable.
Source: choice: C-19, C-20, C-41, and C-79 rely on product policies that are absent from the workspace and must be available before launch

### C-92: Ordinary user creation remains available under its existing policy
Observable: Create a user through the existing non-import path with intake enabled, then pause intake and use that same path under the same permissions.
Source: implied: the request adds a bulk creation path to whatever ordinary creation already exists

### C-93: Existing accounts retain their normal access after import is enabled
Observable: Use an account that existed before enabling imports and observe the same permitted sign-in or access as before.
Source: implied: the request creates new users and does not alter access for existing users

### C-94: Imported accounts participate in ordinary user management
Observable: Find an imported account with ordinary user lookup and use the applicable existing account management actions under their usual permission rules.
Source: implied: U-2 creates users in the same destination as other user accounts

### C-95: An administrator cannot import into a destination outside their user administration scope
Observable: Where the product has multiple destinations or scoped admins, submit into a destination outside the caller's user administration scope and see access refused.
Source: implied: the request grants the operation to admins within their admin authority

### C-96: One CSV submission targets one authorized destination
Observable: In a multi-destination product, start an import for one authorized destination and see newly committed accounts associated with that destination.
Source: choice: U-2 needs an unambiguous destination for a batch

### C-97: A CSV cell cannot override the batch's destination
Observable: Submit a file attempting to assign a record to a different destination and verify that the file cannot create an account there.
Source: choice: C-96 makes scope a property of the authorized submission

### C-98: CSV values cannot grant privileged access
Observable: Supply an admin role or equivalent privilege as CSV data and verify that the submission cannot produce a privileged account.
Source: choice: ordinary account creation is the minimum needed to fulfill U-2 without extending privilege management to files

### C-99: The CSV cannot supply sign-in secrets
Observable: Add a column for passwords or other sign-in secrets and see that the import rejects the column.
Source: choice: U-13 uses the normal secure account setup path instead of shared files for credentials

### C-100: An unauthorized caller cannot retrieve an import result
Observable: As a signed-out caller, a non-admin, or a caller without current authority for the destination, try to read an import result and see access refused.
Source: choice: U-7's access restriction also protects result data

### C-101: An admin cannot recover a different uploader's result through personal result recovery
Observable: As another admin in the same destination, use the first admin's attempt reference in the personal recovery path and see access refused.
Source: choice: U-12 needs the submitter's outcome and operators have a separate need for operational summaries

### C-102: An identity conflict does not expose a competing account
Observable: Submit a value that conflicts under a uniqueness rule spanning destinations and observe a conflict without seeing the competing account's attributes or destination.
Source: choice: C-43 can identify the submitted record without disclosing someone else's account

### C-103: A request initiated from outside the authorized admin interaction cannot use the admin's session to submit a file
Observable: While signed in as an admin, open an unrelated site that attempts to start an import using that session and verify that it cannot create users.
Source: choice: the admin's authority needs to accompany an intended import in the assumed browser runtime

### C-104: Uploaded content stays inert in any import feedback
Observable: Submit markup as an invalid field or header and view the resulting diagnostics as an admin. The supplied markup cannot execute there.
Source: choice: C-39 exposes feedback derived from untrusted CSV data

### C-105: Import results omit uploaded field values
Observable: Submit a file containing a distinctive private field value and inspect the result for location and cause without that raw value.
Source: choice: C-39 and C-40 supply sufficient diagnostics without republishing personal data

### C-106: Operators can inspect an attempt's creation outcome
Observable: With operator authorization, look up the affected attempt by reference and see its creation outcome.
Source: choice: U-10 needs enough metadata to investigate and reconcile imports

### C-107: Operator summaries omit uploaded user values
Observable: As an operator, open an import summary for a file containing a distinctive private value and verify that the value is absent.
Source: choice: U-10 requires operational evidence but does not require a copy of user data

### C-108: Routine import diagnostics omit raw CSV contents
Observable: Inspect routine operator diagnostics following an invalid upload and verify that they do not contain the submitted file contents.
Source: choice: troubleshooting intake should not turn logs into an additional copy of user data

### C-109: Changing import limits requires operator authority
Observable: Try to change limits with an account lacking the applicable operator authority and see access refused.
Source: choice: U-9 and U-10 operate on service controls beyond submitting a CSV

### C-110: A terminal attempt does not offer a source file for download
Observable: After a successful, failed, or refused attempt, open its result and verify that the raw uploaded file cannot be retrieved through the import feature.
Source: choice: recovering the result in U-12 does not require persistent access to the uploaded file

### C-111: Temporary upload data expires under a bounded retention policy
Observable: After the attempt becomes terminal, verify through authorized operational inspection that its temporary upload data expires within the deployment's declared retention period.
Source: choice: temporary user data needs a defined end even when an upload is abandoned

### C-112: Feature rollback resolves accepted attempts before removing their processing capability
Observable: Begin rollback while an accepted attempt is unresolved and verify that it reaches a known terminal outcome before the release serving it is withdrawn.
Source: choice: C-17 and C-65 must both hold during explicit rollback

### C-113: Feature rollback preserves users who existed before import
Observable: Roll back the feature and verify that an account predating the release is still available through the previous release's usual account lookup.
Source: implied: U-10 rolls back the import feature without undoing pre-existing user data

### C-114: The admin can learn which columns are required before submission
Observable: Open the import guidance and identify the required columns separately from optional ones.
Source: choice: C-22 is actionable only if the admin can tell what the destination requires

### C-115: The admin can learn how to supply accepted account values before submission
Observable: Open the schema guidance and determine the expected kinds of values in each supported column, including the allowed choices for a field with a fixed set of values.
Source: choice: C-41 needs user-facing field guidance without fixing destination-specific values

### C-116: The admin can determine the effective user-record ceiling before uploading
Observable: Open import guidance and find the maximum number of user records per file.
Source: choice: C-48 needs a discoverable boundary independent of the byte ceiling

### C-117: The first CSV record remaining after empty-line handling is the header
Observable: Place the published column names in the first record after any leading empty lines. The import uses those names as the header.
Source: choice: C-21 needs a predictable location for the named columns

### C-118: The import requires a selected file to start creation
Observable: Activate the submission action without selecting any file and observe that the admin must supply a file before proceeding.
Source: choice: U-14 distinguishes missing file selection from a present empty file

### C-119: Selecting a file alone does not create users
Observable: Select a valid CSV, then leave before submitting it. The selection produces zero created users.
Source: choice: U-14 needs an explicit point at which the admin requests creation

### C-120: A submission uses the file selected when the admin submits
Observable: Select a file, replace it with a different valid file, then submit. The resulting accounts come from the replacement file.
Source: choice: U-14 requires the selection used for creation to be the admin's current one

### C-121: Each submitted attempt accepts one CSV file
Observable: Try to attach two CSV files to one attempt and see that the attempt requires a single file.
Source: choice: C-59 needs an unambiguous input for checking or replaying one submission

### C-122: The upload validates CSV content independently of the file label
Observable: Submit non-CSV contents under a CSV filename with a CSV media label and see an input refusal.
Source: choice: C-8 must hold even when file metadata appears valid

### C-123: Refused input can be corrected in a fresh attempt
Observable: Correct the file after a terminal input refusal and submit it again as a new attempt without changing the directory or obtaining operator help.
Source: choice: U-5 can complete once the admin fixes the input

### C-124: Import acceptance requires receipt of the complete file
Observable: Begin an upload and pause transmission before all file bytes are sent. No accepted status is reported for that attempt.
Source: choice: C-73 and C-76 need a predictable boundary between a transfer in progress and work accepted for processing

### C-125: Starting rollback closes intake before unresolved attempts are drained
Observable: Start rollback with a pending accepted attempt and submit another eligible file while the operator is draining the earlier work. The new upload is refused.
Source: choice: C-112 needs pending work to stop accumulating while rollback is prepared

### C-126: An incomplete transfer eventually ends as a non-creation attempt
Observable: Abandon a transfer whose attempt reference has already been issued, then inspect the attempt after the deployment's stated transfer timeout. The attempt has ended without creation.
Source: choice: U-8 needs a known retry point even when the full upload never arrives. The hosting transfer timeout is unconfirmed until deployment

### C-127: The admin can determine when an unfinished upload will expire
Observable: Before submission, find the applicable unfinished-upload timeout and what starts or resets it.
Source: choice: C-126 needs an observable boundary without imposing one timeout across hosting environments

### C-128: An import attempt is bound to its original destination
Observable: Try to reuse an attempt for a different destination to which the same admin has access and see the reuse refused.
Source: choice: C-62 and C-96 require a retry to preserve the original creation scope

### C-129: A different actor cannot resume an import attempt
Observable: As a second admin in the same destination, try to submit using the first admin's attempt reference and see the reuse refused.
Source: choice: C-59 must preserve who requested creation as well as what was submitted

### C-130: Ending the browser session does not revoke durable admin authority by itself
Observable: Let the submitting admin's session expire after acceptance while their account still has creation authority. The attempt can complete without that original session.
Source: choice: C-75 checks current authority and U-12 allows the admin to leave the original session

### C-131: An import honors the destination's account-capacity rule at creation
Observable: Where the destination limits its user count, submit a batch larger than its remaining capacity and see it refused as a capacity conflict.
Source: choice: C-52 must coexist with the destination's limits on account creation

### C-132: Imported users receive the ordinary non-privileged access default
Observable: Import a file containing only the required columns and inspect a new user's initial permissions against the destination's standard non-privileged account.
Source: choice: C-98 requires a safe ordinary-account default for files that supply no access-related value

### C-133: Account setup uses currently valid account state
Observable: Where ordinary setup can run after creation, deactivate or remove an imported account before setup completes and verify that setup cannot enable access beyond what the destination currently permits.
Source: choice: U-13 must honor ordinary revocation rules even when setup arrives late

### C-134: Pausing imports requires operator authority
Observable: Try to pause intake with an account lacking the applicable operator authority and see access refused.
Source: choice: U-9's ability to stop service needs the same authorization boundary as changing service limits

### C-135: Operational import summaries require operator authority
Observable: Try to look up an operational import summary with an account lacking the applicable operator authority and see access refused.
Source: choice: C-106 exposes submission metadata beyond a caller's personal result

### C-136: Operational import summaries have a stated retention period
Observable: Find the operational history duration and its starting event through the operator's controls or guidance.
Source: choice: U-10 needs a predictable period in which attempts can be investigated

### C-137: Operational history remains accessible through its stated retention period after rollback
Observable: Roll back the feature after an import reaches a terminal outcome and use the authorized operational path to retrieve its summary within the retention period.
Source: choice: U-10 still needs evidence for reconciliation even after the upload surface is removed

### C-138: Rollback leaves terminal outcomes recoverable during their advertised window
Observable: Lose the final response, then roll back the feature. Within the original recovery window, recover what happened as the authorized submitter through the available recovery path.
Source: choice: C-69's advertised recovery promise applies to imports already accepted when rollback begins

### C-139: Invalid file-level input creates zero users
Observable: Submit a valid-looking prefix followed by unreadable CSV structure and verify that zero accounts were created by the submission.
Source: choice: C-52 covers the whole input, including when a parse error occurs after valid user records

### C-140: A file over either import ceiling creates zero users
Observable: Submit an otherwise valid batch over an advertised limit and verify that it creates no accounts.
Source: choice: C-6 is a refusal of the whole upload

### C-141: Provisioning refusal before account creation creates zero users
Observable: Where a required account policy service refuses creation, inspect the destination and see zero users created by that attempt.
Source: choice: C-52 applies to required checks before durable creation as well as failures during it

### C-142: The selected file's size can be checked against the byte ceiling before transfer
Observable: Select a file larger than the current advertised byte ceiling and attempt to submit it. See the size refusal before transfer starts.
Source: choice: a host may reject oversized requests before the application can provide the limit feedback in C-49

### C-143: A transfer still in progress at intake pause is not accepted during the pause
Observable: Begin transferring a file, pause intake before the full file arrives, and complete the transfer while intake remains paused. No acceptance occurs.
Source: choice: C-14 and C-124 place the pause boundary at acceptance

### C-144: Intake pause is distinguishable from invalid input
Observable: While intake is paused, try to import an otherwise valid file and see that import is temporarily unavailable.
Source: choice: U-9's maintenance should give an admin a reason to wait without having to edit a valid file

### C-145: A provided record with empty fields is still a user record
Observable: In a file with valid headers, supply a data record consisting of empty cells, such as a quoted empty cell in a one-column file. The import treats it as a record subject to normal account validation.
Source: choice: C-35 skips physical empty lines and must not silently drop explicitly provided cells

### C-146: The import schema supports creation with every required account input satisfied
Observable: Using the published schema, import an ordinary user whose required account inputs are satisfied by supported columns or by established destination defaults or setup.
Source: choice: C-19 and C-99 need a usable account creation path even when some required setup inputs cannot appear in a file

### C-147: The result gives a reason for terminal non-creation
Observable: As an authorized submitter, inspect a terminal non-creation result and find a reason usable to decide whether to correct input, restore access, or wait for service.
Source: choice: U-8 needs more than a generic failure indication before the admin can act

### C-148: A destination capacity refusal creates zero accounts
Observable: Where a user quota leaves room for one account, submit a two-user file and see that the submission does not fill the remaining slot.
Source: choice: C-131 must obey the same whole-batch boundary as C-52

### C-149: Resuming import intake requires operator authority
Observable: Try to resume intake with an account lacking the applicable operator authority and see access refused.
Source: choice: U-9's maintenance pause must remain enforceable

### C-150: An operational summary identifies the submitting actor
Observable: Look up an attempt with operator authorization and determine which admin submitted it.
Source: choice: U-10 needs a way to reconcile the attempt with the uploader

### C-151: An operational summary identifies the destination
Observable: In a multi-destination deployment, look up an attempt with operator authorization and determine which destination it targeted.
Source: choice: U-10 needs to know which directory could have changed

### C-152: An operational summary reports the number of users created by a terminal attempt
Observable: With operator authorization, compare the creation count in the operational summary for a finished batch with the number of accounts that batch created.
Source: choice: U-10 needs enough information to reconcile a terminal batch without retrieving its file

### C-153: A shorter recovery policy does not reduce an already accepted attempt's promised window
Observable: Accept an attempt, shorten the policy for later attempts, then retrieve the original result within its originally advertised recovery window.
Source: choice: C-69 supplies a recovery promise the admin can rely on after losing the response

### C-154: A terminal result is unavailable after its personal recovery window
Observable: After the advertised window passes, look up the attempt as its submitter and see that the saved result is no longer available.
Source: choice: C-69 defines a bounded period for personal result retrieval

### C-155: An operational summary expires after its operational retention period
Observable: Look up an attempt as an operator after the applicable operational history period has passed and verify the saved summary is no longer available.
Source: choice: C-136 defines the end of operational access to submission metadata

### C-156: An unresolved storage outcome remains unresolved in the result
Observable: Lose contact with account storage at the commit boundary and check the attempt while its effects are indeterminate. The result remains unresolved.
Source: choice: C-64 and C-66 prohibit guessing whether users were created

### C-157: A reconnecting admin can find an attempt without its original response
Observable: Lose the response after submission, close the original view, and return as the submitting admin with current access. Find the earlier attempt through the supported recovery path while it is unresolved or within its recovery window.
Source: choice: U-12 cannot depend on the response that was lost

### C-158: Rollback cannot leave an unfinished transfer able to create users
Observable: Begin a transfer, start rollback before acceptance, then deliver the rest of the upload after the older release is in service. No users are created by the unfinished transfer.
Source: choice: C-125 closes intake before rollback and late file bytes cannot reopen that attempt

### C-159: An accepted file keeps its account-field mapping during a schema change
Observable: Accept a file under one published mapping and change a header's mapping before the batch reaches creation. If the batch commits, its values go to the original intended fields.
Source: choice: C-19 lets the admin rely on the meaning of the file accepted for that attempt

### C-160: An in-flight batch must satisfy the destination's current validation rules at creation
Observable: Tighten an account value rule after acceptance but before creation. An accepted file containing a value that is newly prohibited cannot create users with that value.
Source: choice: C-41 applies the destination's account invariants when users are actually created

### C-161: Rolling back intake gives unfinished transfers a terminal non-creation outcome
Observable: Start rollback while a transfer with an attempt reference is unfinished. Recover that attempt and observe a terminal non-creation outcome within the advertised recovery window.
Source: choice: C-126 and C-138 still need to resolve a transfer when rollback removes intake before it would otherwise expire
