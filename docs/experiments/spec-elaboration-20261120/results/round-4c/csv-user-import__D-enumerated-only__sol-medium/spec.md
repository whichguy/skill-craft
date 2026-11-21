## Use cases

### U-1: An admin imports users for the first time to populate a user directory
Flow: The admin opens user management, finds the CSV import action, checks the accepted input, selects a CSV with two new users, and submits it once. The import reports two creations. Both users appear in the directory.
Source: request

### U-2: An admin repeats an import to add another group of users
Flow: The admin submits another CSV of new users. If the admin instead resubmits the previous file while its users still exist, the import reports a conflict and the directory gains no users.
Source: implied: bulk creation can be invoked against a directory that already contains users

### U-3: An admin submits empty or invalid input to learn what to correct
Flow: The admin attempts an import without a file, with a header-only file, with a malformed file, or with an invalid user row. The import reports the applicable problem. The admin corrects the input and submits it again.
Source: implied: uploaded files can omit user records or fail to describe creatable users

### U-4: An admin imports users at the supported capacity
Flow: The admin submits a valid CSV with 1,000 user records and 1,048,576 file bytes. It can be imported. A file above either boundary is refused with the applicable limit.
Source: implied: CSV uploads can vary in size and record count

### U-5: A person without admin access attempts to import users
Flow: A signed-out person or signed-in non-admin attempts to reach or invoke CSV import. They cannot create users through it.
Source: implied: the request grants CSV import to admins

### U-6: An admin recovers the outcome of an interrupted import
Flow: The admin submits a file, then loses the response or encounters a service failure. The admin reopens import activity to determine whether the attempt is Pending, Succeeded, or Failed. If the upload never completed, the admin checks again or retries the same submission. Once there is a Failed result or the original was never admitted and can no longer be admitted, the admin can start a new submission.
Source: implied: an upload or its backing user-creation operation can fail independently of the admin's session

### U-7: An operator starts or stops accepting CSV imports
Flow: The operator enables CSV import for the deployment. When maintenance is needed, the operator disables new submissions, observes accepted imports finish, and can enable submissions again.
Source: implied: the import capability has a deployment and a maintenance lifecycle

### U-8: An operator restores the previous version while preserving users
Flow: The operator stops new imports, observes that accepted imports have finished, and deploys the previous version. Existing users and users created by CSV remain available in ordinary user management.
Source: implied: the user directory outlives an importer release

### U-9: Two admins try to create the same user to provision overlapping groups
Flow: Two admins submit different CSVs that contain the same account identity for the same directory. One batch succeeds if there are no other blockers. The other reports the conflicting record and creates zero users, including any rows unique to its file. The second admin can correct the file and submit a new batch.
Source: implied: different admins can act on the same directory before either sees the other's changes

## Clauses

### C-1: Admins can submit a CSV to create multiple users in one action
Observable: An admin submits one CSV describing two distinct new users and obtains two new accounts in the target user directory.
Source: request

### C-2: An existing user is never updated by a CSV import
Observable: Submitting a CSV that describes an existing user leaves that account's fields unchanged.
Source: implied: the request is for creation

### C-3: CSV import is unavailable to callers without admin authority
Observable: A signed-out caller or a signed-in non-admin attempting submission is refused and gains no ability to create users by CSV.
Source: implied: the request grants CSV import to admins

### C-4: The importer accepts a file of at most 1,048,576 bytes inclusive
Observable: An otherwise valid CSV of 1,048,576 file bytes is eligible. A file of 1,048,577 bytes is refused with the 1,048,576-byte limit.
Source: choice: a bounded upload accommodates ordinary batches and gives admins a usable splitting threshold

### C-5: The importer accepts at most 1,000 user records per file inclusive
Observable: An otherwise valid CSV with 1,000 user records is eligible. A file with 1,001 user records is refused with the 1,000-record limit.
Source: choice: limit the impact of one submission while allowing substantial batches

### C-6: A submission with no file is rejected
Observable: Submitting without a file creates zero users.
Source: implied: the request creates users using an uploaded CSV

### C-7: A CSV with no user records is rejected
Observable: Submitting a CSV containing only the supported header produces feedback that at least one user record is required.
Source: choice: treating an empty batch as an input problem helps the admin detect a missing export

### C-8: Invalid CSV input produces corrective feedback
Observable: An admin who submits malformed CSV or an invalid user record receives a reason the input needs correction.
Source: choice: U-3 needs enough feedback for the admin to correct the file

### C-9: A batch that fails creates zero users
Observable: When one row in a file is invalid or a required write fails before successful completion, none of the users described by that attempt is created.
Source: choice: admins can correct and retry a whole file without reconstructing which rows succeeded

### C-10: A successful submission reports the number of users it created
Observable: A file that creates two users reports a created count of 2.
Source: choice: the admin can reconcile the batch against the source file

### C-11: An admin can recover the outcome of their accepted import after a lost response
Observable: After losing the response, the submitting admin can reopen import activity and find that attempt's current status.
Source: choice: durable outcome visibility makes uncertain submissions recoverable

### C-12: An operator can disable admission of new imports
Observable: After an operator disables import admission, a new submission is refused as unavailable.
Source: choice: operators need to stop new work for maintenance or rollback

### C-13: An operator can enable admission of new imports
Observable: Once the operator enables import admission, a new otherwise eligible submission can be accepted.
Source: choice: operators need a way to start or restore the capability

### C-14: Created users survive a rollback of the importer release
Observable: After pending imports finish and the previous version is deployed, users created by completed imports remain present in ordinary user management.
Source: choice: rolling back the importer must preserve the user directory

### C-15: An authorized admin can find CSV import from user management
Observable: An admin with import admission enabled can reach the submission action from the user-management area.
Source: choice: user management is where admins already work with accounts

### C-16: Each submission targets one user directory
Observable: Before submitting, the admin can identify the target as the directory currently selected in user management, or as the application's sole directory where there is no selector. The file has no field for selecting another directory.
Source: choice: use the existing directory context and prevent cross-directory batches

### C-17: Import authority follows the target directory's admin permission
Observable: An admin of directory A with no admin authority for directory B is refused when attempting to submit to B. Where the application has one directory, its existing admin permission governs import.
Source: choice: use the same boundary that grants admin authority over the selected directory

### C-18: The submission action exposes its input requirements before selection
Observable: An admin can find the required header, the supported encoding and CSV syntax, the account field rules, the file-byte limit, the user-record limit, and the behavior when any record fails before selecting a file.
Source: choice: admins need enough information to prepare a usable file without trial submissions

### C-19: One submission takes exactly one file
Observable: Supplying two files in one submission produces a file-count error.
Source: choice: the request describes one uploaded CSV per action

### C-20: Import accepts UTF-8 CSV
Observable: An otherwise valid UTF-8 file is eligible with or without one leading UTF-8 byte-order mark. A file that cannot be decoded as UTF-8 is refused with an encoding error.
Source: choice: support common exports while making the decoding rule predictable

### C-21: The field separator is a comma
Observable: Below a valid header, a line containing `ada@example.com,` fails for extra fields. A semicolon or tab inside the email field goes to ordinary email validation as field content.
Source: choice: define CSV in the ordinary comma-separated sense

### C-22: Record boundaries are LF or CRLF outside quoted fields
Observable: An otherwise valid file can use LF, CRLF, or both between records. Its final record may end at end-of-file. A bare CR outside a quoted field is refused as malformed.
Source: choice: support common line endings without making a trailing newline significant

### C-23: A quoted CSV field uses double quotes
Observable: A file with `"email"` as its header and `"ada@example.com"` as its only data record is eligible when the address itself is eligible.
Source: choice: support ordinary quoted CSV exports

### C-24: Invalid quote placement fails the file
Observable: An unclosed quoted field, a double quote inside an unquoted field, or any character between a closing quote and the next separator, record boundary, or end-of-file produces a malformed CSV error.
Source: choice: reject ambiguous CSV instead of guessing the intended account data

### C-25: Blank records are ignored
Observable: A record consisting only of zero or more ASCII spaces or tabs, outside quotes, is ignored before or after the header. A record containing a delimiter or a quoted field is evaluated even if every field decodes to an empty value.
Source: choice: tolerate blank export lines without hiding missing field values in explicit records

### C-26: The first nonblank record identifies the sole supported column
Observable: The first nonblank record must contain exactly one field whose decoded value, after trimming ASCII spaces and tabs at both ends, is `email` under ASCII case-insensitive comparison. A missing, unknown, extra, or repeated column produces a header error.
Source: choice: email is sufficient input for this scope and unexpected columns must not be silently dropped

### C-27: Each user record contains exactly one field
Observable: After the header, a nonblank record with an extra field produces a column-count error, even if the extra field is empty.
Source: choice: keep the data records aligned with the one supported column

### C-28: The email field is evaluated after trimming ASCII spaces and tabs at its ends
Observable: A data field containing `  ada@example.com  ` is evaluated as `ada@example.com`. A field that becomes empty is refused as missing email.
Source: choice: tolerate padding while making absent email distinguishable from invalid email

### C-29: Imported emails must satisfy ordinary directory account creation rules
Observable: Given the same directory and email, an email rejected by ordinary administrator account creation for address validity is also rejected by CSV import. The host's exact accepted address syntax and length limits are unconfirmed.
Source: choice: preserve the directory's accepted addresses without specifying an unconfirmed account model

### C-30: CSV import creates the directory's ordinary least-privileged account type
Observable: The created account receives the least-privileged role available for an ordinary newly provisioned user in that directory. A CSV cannot supply a role, password, name, status, identifier, or other account attribute.
Source: choice: support bulk creation without granting CSV control over permissions or credentials

### C-31: Account attributes outside the CSV follow ordinary provisioning defaults
Observable: Aside from the email and the least-privileged role, an imported account receives the same generated identifier, default state, profile defaults, access scope, and credential or onboarding state as an ordinary account provisioned with email alone in that directory. Other host-specific attributes are deliberately delegated to that provisioning path because the workspace supplies no account model.
Source: choice: keep imported accounts compatible with the rest of the product

### C-32: An accepted attempt has a distinct reference
Observable: An admin can distinguish two accepted attempts even when both came from files of the same name.
Source: choice: the admin needs to recover a specific submission after leaving the original view

### C-33: Import activity reports a defined set of states
Observable: An accepted attempt is Pending while it has no final result, Succeeded when its users have been durably created, or Failed when it has ended with zero creations. These are the meanings of the states, regardless of label wording.
Source: choice: show whether a submission should be waited on, reconciled, or retried

### C-34: Import results are visible only to their submitting admin in the target directory
Observable: The submitting admin can view the attempt only while currently authorized as an admin for the target directory. Another admin, a non-admin, or someone from another directory cannot view its result by browsing activity or using its reference.
Source: choice: limit access to uploaded user information during recovery

### C-35: A terminal import result is available for seven days
Observable: Terminal status remains retrievable until 168 hours have elapsed from completion. At that age the result no longer appears in the import activity view or opens by reference.
Source: choice: give admins time to recover an outcome without indefinite result retention

### C-36: The operator can see whether accepted work is still in progress
Observable: Operators can observe the count of Pending attempts for the deployment, including a count of 0.
Source: choice: U-7 and U-8 require an observable condition for drained maintenance

### C-37: An admitted attempt remains bound to its original file
Observable: Replacing the selected file, navigating away, refreshing, or signing out after admission leaves the admitted attempt processing the bytes originally received.
Source: choice: a change in the upload view must not alter work that the service already accepted

### C-38: An admitted attempt remains bound to its original target directory
Observable: Switching from directory A to directory B after admission cannot cause the attempt to create users in B.
Source: choice: preserve the scope selected for the submission

### C-39: Import checks admin authority again before making accounts visible
Observable: If the submitting admin no longer has admin authority for the target directory at the point the batch would commit, the batch fails for lost authority.
Source: choice: queued work must not exercise authority the caller has lost

### C-40: Incomplete transport does not admit an attempt
Observable: If the upload stops before the service has received the whole file and its submission information, the interrupted transfer does not appear in activity as an accepted attempt. Account creation cannot start from a partial file.
Source: implied: U-6 and the request require a submitted CSV before it can be used to create users

### C-41: Repeating delivery of one submission creates at most one attempt
Observable: A duplicate delivery from a double click, connection retry, or replay of the same submission reference resolves to the same accepted attempt and its current outcome, if any. This holds when the deliveries overlap.
Source: choice: an uncertain response must not turn a single deliberate action into multiple attempts

### C-42: An explicit new submission is a new attempt
Observable: Starting another import with the same file after an earlier attempt succeeds or fails produces a new attempt reference when the new submission is admitted.
Source: choice: support deliberate retries without confusing them with repeated delivery

### C-43: A batch with duplicate account identities is rejected
Observable: Two rows whose emails identify the same account under ordinary directory creation rules cause a duplicate-in-file failure. The result identifies the later record and the earlier record it duplicates.
Source: choice: report duplicated source data instead of choosing a winning row

### C-44: Existing account identities cause a batch conflict
Observable: If an imported email would conflict with a retained identity under ordinary account creation in that directory, the batch fails with an existing-account conflict. Account states that retain an identity are deliberately delegated to ordinary account creation because the workspace does not establish the directory's lifecycle.
Source: choice: apply the same reservation behavior to bulk and individual creation

### C-45: Concurrent account creation respects ordinary uniqueness
Observable: If two eligible imports try to claim an initially free identity in the same directory, at most one succeeds. The same applies if one attempt is ordinary single-user creation. An import that loses the claim reports an existing-account conflict.
Source: choice: uphold ordinary identity uniqueness when prechecks overlap

### C-46: An import uses the account and directory rules in effect when its creation takes effect
Observable: If the target directory becomes unavailable for provisioning, an email identity becomes occupied, the admission ceiling for accounts is reached, or the imported account ceases to be valid under ordinary rules while an attempt is pending, the batch fails if that condition would block ordinary creation at commit. Other host-specific provisioning rules are deliberately delegated to ordinary provisioning. The host's numeric account ceiling, including whether it has one, is unconfirmed.
Source: choice: keep delayed creation subject to the same rules as current directory operations

### C-47: Disabling admission lets already accepted work finish
Observable: For a file received while admission is being disabled, the attempt is either admitted before the switch takes effect and allowed to finish, or refused as unavailable.
Source: choice: give maintenance a clear boundary without interrupting in-flight transactions

### C-48: Accepted imports have a five-minute completion deadline
Observable: At five minutes after admission a still-uncommitted attempt can no longer create users and has a Failed outcome with a timeout reason. An outcome temporarily inaccessible during an outage is visible on recovery if still within its retention period.
Source: choice: bound how long an admin or operator must wait for an attempt to settle

### C-49: A terminal outcome is stable
Observable: Once an attempt reports Succeeded or Failed, refreshing, replaying a delivery, or receiving delayed processing cannot change that outcome. Normal edits or deletion of the created users do not rewrite the original result.
Source: choice: terminal results need to be reliable during recovery and reconciliation

### C-50: A lost success response does not undo an import
Observable: If the connection ends after the accounts are durably created, the users remain created and the recorded result is Succeeded with the original created count.
Source: choice: the outcome follows account creation even when the response fails to reach its caller

### C-51: A failed dependency is reported distinctly from a bad file
Observable: If a required service fails before commit and the attempt reaches a terminal failure before its deadline, the result identifies service failure. The admin can make a new submission after recovery.
Source: choice: revising the CSV would not resolve this failure

### C-52: An accepted import has no user-facing cancellation control
Observable: An admin cannot cancel a Pending attempt from import activity or the submission view. Closing a tab or disconnecting is not an instruction to cancel an accepted import.
Source: choice: a bounded all-or-nothing operation can finish without defining a second kind of rollback

### C-53: Operators can recover admission after a routine restart
Observable: Restarting the service does not change whether new submissions are enabled or disabled.
Source: choice: maintenance must remain in effect through ordinary service restarts

### C-54: A service restart does not reset an accepted attempt
Observable: After a restart an accepted attempt retains its reference, original deadline, and any committed outcome. An uncommitted attempt can still complete before that deadline or end in failure.
Source: choice: preserve a reliable account and result record across interruptions

### C-55: The deployment must allow a complete supported upload to reach the importer
Observable: A production admin can submit a supported 1,048,576-byte file through the normal entry point, including the surrounding request metadata. The hosting runtime and upload gateway are unconfirmed in this workspace, so their exact request-body caps are unconfirmed.
Source: choice: preserve the C-4 ceiling across ingress request-size rules, under which the lowest enforced body cap applies to the entire request

### C-56: An upload that exceeds a transport deadline creates zero users if its attempt was never admitted
Observable: If the delivery deadline ends before the full submission is admitted, the admin sees an upload failure or connection interruption. There is no accepted attempt for that delivery. The hosting runtime and ingress are unconfirmed, so their exact request and idle timeouts are unconfirmed.
Source: implied: U-6 and the transport rule that a prematurely closed connection may deliver only part of a request

### C-57: An admitted import can be recovered after the original request lifetime ends
Observable: If the hosting layer closes the original connection after admission, an authorized admin can retrieve the attempt through a subsequent connection. The hosting runtime is unconfirmed, so its exact maximum request lifetime and any platform restriction on synchronous work are unconfirmed.
Source: choice: accept the request-lifetime rule that connection closure can occur independently of durable account creation

### C-58: Production import requires the application's authenticated user-management connection
Observable: An admin can submit files and inspect outcomes through the ordinary authenticated user-management connection. Credentials accepted only in a development environment do not grant production import access. The runtime and production authentication settings are unconfirmed.
Source: implied: U-5 and the deployment's existing production authentication rule must govern access to production accounts

### C-59: Production admission is enabled only where the supported batch can be created atomically
Observable: At production readiness, a representative 1,000-record import can commit as a unit and an equivalent import forced to fail partway exposes zero created accounts. The backing user store is unconfirmed, so its transaction-size and transaction-duration ceilings are unconfirmed.
Source: choice: honor the backing store's all-or-nothing commit boundary and verify that it can support the chosen product limits

### C-60: The ordinary production provisioning path must support email-only input for least-privileged users
Observable: Before admission is enabled, an admin can provision an ordinary least-privileged account in the target deployment using an email with defaults for all other required attributes. If email alone cannot produce a valid account under the host's provisioning rules, admission stays disabled there.
Source: choice: enforce the host's required account fields without silently inventing input values or opening extra CSV columns

### C-61: Ordinary single-user provisioning remains available independently of CSV admission
Observable: With import enabled, disabled, or unable to accept uploads, an authorized caller can still use the ordinary single-user creation action subject to its existing availability and validation rules.
Source: implied: U-1 adds bulk creation alongside existing user management where it exists

### C-62: Imported users participate in ordinary user management
Observable: An authorized user can find an imported account using ordinary directory listing and lookup. Viewing, editing, status changes, and removal are available on the same terms as for equivalent ordinary accounts where those actions exist. Host-specific management actions are deliberately left to ordinary user management because their set is unconfirmed.
Source: implied: U-1 creates users in the directory used by the rest of the product

### C-63: CSV import never deletes an existing account
Observable: Submitting a file that omits existing users leaves those users in the directory.
Source: implied: the request is for creation

### C-64: Toggling admission itself never changes existing accounts
Observable: Turning admission on or off leaves the directory population and every existing account's data untouched.
Source: implied: U-7 changes availability of the import action

### C-65: Accounts from a Pending import are invisible to ordinary user management
Observable: Before the attempt succeeds, ordinary directory listing and lookup expose zero accounts from that attempt. Once it succeeds, all created accounts are available under the directory's ordinary visibility rules.
Source: choice: expose the batch as one creation outcome

### C-66: Imported accounts follow the ordinary post-creation onboarding policy
Observable: Committed accounts receive the ordinary onboarding effects configured for equivalent accounts in that directory. If ordinary provisioning initiates email, an invitation, or account activation, the equivalent import can initiate it only after the corresponding account is committed. Other downstream effects are delegated to ordinary provisioning because no integrations are supplied.
Source: choice: preserve access policy and keep external effects from announcing accounts that never existed

### C-67: Repeated delivery cannot initiate onboarding again for the same creation
Observable: Replaying the same accepted submission does not produce a second import-triggered initial invitation or activation for an account. A separately authorized resend follows ordinary user management.
Source: choice: outcome recovery must not notify users twice for one creation

### C-68: Post-creation delivery problems do not reverse account creation
Observable: If the deployment sends onboarding messages and delivery fails after commit, the import still reports Succeeded with the number of accounts created. The ordinary onboarding recovery behavior applies to delivery problems.
Source: choice: the result measures durable account creation and can remain truthful during messaging outages

### C-69: Import results never expose raw file content
Observable: Import activity, failure details, and operator import views do not display or offer downloads of uploaded bytes, source filenames, or email values from the file. Newly created account data continues to follow ordinary directory visibility.
Source: choice: references and record locations suffice for recovery without exposing source data

### C-70: Raw input ceases to be retained by the importer when the attempt ends
Observable: A retention inspection of the importer after a terminal outcome finds no original upload or separate row-value copy retained for import processing, diagnostics, or activity. Ordinary stored account records and the C-35 result metadata follow their own retention rules. Hosting infrastructure retention outside the importer is unconfirmed.
Source: choice: the importer needs source data only while it is processing an attempt

### C-71: Access refusals disclose no protected import information
Observable: A caller without authority to access a reference under C-34 and C-83 receives the same kind of access refusal whether the reference exists, has expired, or was never issued. The response contains no file validation detail, target account status, or outcome.
Source: choice: direct attempts to open references must not reveal another admin's activity or directory data

### C-72: CSV import follows ordinary authenticated mutation safeguards
Observable: A submission made with a signed-in admin's credentials through a request that the product would refuse for an ordinary user-management mutation is also refused for CSV import. The host's exact session and request-authenticity rules are unconfirmed.
Source: implied: U-5 and the request grant the action to admins acting with valid authority

### C-73: A pair of consecutive quotes inside a quoted field represents one literal double quote
Observable: A file with `"em""ail"` as the header produces an invalid-header error because the decoded field is `em"ail`.
Source: choice: allow CSV-escaped quotes without interpreting them as field boundaries

### C-74: Delimiters and line breaks inside quotes remain field content
Observable: A quoted value containing a comma or line break is processed as one field in one record. If the decoded email is rejected, the result identifies a user-record problem rather than an extra column or extra user record.
Source: choice: apply account validation to the field value after CSV parsing

### C-75: The importer identifies a row-specific failure by its starting line
Observable: A row conflict, invalid field, or field-count error names the physical line where the record started, counting the first physical line as 1 and each LF or CRLF as one line break. Blank lines count for this diagnostic. A duplicate-in-file result gives both record start lines.
Source: choice: admins can locate a bad record even when quoted values span multiple lines

### C-76: Failure feedback describes at least one actual blocker
Observable: A rejection identifies a reason from the applicable refusal conditions in this specification. If several conditions apply, reporting any one is sufficient. Content errors may identify only a file-level issue for undecodable input, malformed CSV, missing or invalid header, or a file or record limit violation. Row-specific failures identify the affected record under C-75.
Source: choice: give actionable feedback without promising error ordering or exhaustive validation

### C-77: Disabling admission leaves authorized recovery accessible
Observable: An admin can open their Pending, Succeeded, and Failed attempts during maintenance while they retain directory admin authority and the import activity feature is deployed.
Source: choice: admins need to reconcile accepted work while new submissions are paused

### C-78: Import activity shows the information needed to identify a result
Observable: Each entry shows its attempt reference, admission time, and current state. A Succeeded entry also shows the created count. A Failed entry also shows its failure reason and any required record location. The admission time is the time the service accepted the attempt, with no required display format.
Source: choice: the submitter can locate the expected entry without retaining the source filename or contents

### C-79: Format validation applies to a fully admitted file
Observable: Under normal service availability, the first eligible complete delivery for a current reference with one file within the byte limit, valid submission authority, and enabled admission carries its reference into activity, even if it later fails on encoding, CSV grammar, header, record count, or row contents. Missing files, multiple files, excessive file bytes, incomplete delivery, invalid authority, expired references, and disabled admission are refused before acceptance.
Source: choice: give recoverable results for file contents and distinguish them from failures to submit

### C-80: File eligibility is determined by the submitted bytes
Observable: A valid file is eligible with any filename extension and any declared media type. Giving other content a CSV extension does not make its contents valid.
Source: choice: accept equivalent CSV exports without depending on filenames or client metadata

### C-81: A submission reference has a 15-minute first admission window
Observable: A reference becomes eligible when the admin initiates a new submission, before its file is delivered. A delivery first reaching admission at or after 15 minutes from that point is refused as expired. An already accepted reference remains recoverable under C-35.
Source: choice: bound how long an unaccepted delivery can turn into work

### C-82: A delivery replay cannot change the file associated with an accepted reference
Observable: Sending different bytes with the same accepted submission reference leaves the original attempt and outcome in place. Opening a new submission is required to send a replacement file.
Source: choice: recovering a submission cannot silently substitute input

### C-83: A reference is scoped to its submitting admin and directory
Observable: A submission reference issued to an admin in directory A cannot be used to initiate or recover an attempt as another admin or in directory B.
Source: choice: a replay must never move work or disclose its result across authority boundaries

### C-84: An expired terminal result cannot be replayed into new work
Observable: Repeating delivery after the attempt's 168-hour result retention expires is refused. The directory remains unchanged even if the originally created user has since been removed.
Source: choice: a late retry is still the old action after its result is gone

### C-85: A new submission can provision a previously used email when ordinary creation permits it
Observable: After an account is removed or its email changes, an explicitly new submission for the old email is eligible if that identity is available under current ordinary provisioning rules.
Source: choice: an earlier import does not permanently reserve an email on its own

### C-86: A file with zero bytes has a missing-header failure
Observable: Submitting a zero-byte file creates an admitted failure for missing header under otherwise valid submission conditions. A file containing only a byte-order mark, ignored blank records, or both has the same failure.
Source: choice: distinguish the absence of a selected file, the absence of a header, and a valid header with no records

### C-87: Blank records and the header do not count toward the user-record ceiling
Observable: A file with 1,000 user records, one header, and additional ignored blank records remains within the record ceiling when it meets the byte ceiling. Quoted line breaks do not increment the record count.
Source: choice: the ceiling bounds user records, including records that later prove invalid

### C-88: A submission is within the byte ceiling based on the complete file as uploaded
Observable: The 1,048,576-byte measurement includes the file's byte-order mark, header, line endings, quotes, ignored blank records, and data. Surrounding request metadata is outside the file measurement.
Source: choice: admins can compare the file size they see with the actual upload boundary

### C-89: Admission is disabled when the feature is first installed
Observable: On the first deployment that includes CSV import, new submissions are unavailable until an operator enables them after applicable production prerequisites are met.
Source: choice: let the operator confirm production prerequisites before receiving user data

### C-90: Signing out does not by itself revoke directory admin authority for work already accepted
Observable: If the submitter signs out while Pending and their directory admin authority remains in effect, the attempt may still complete. Retrieval requires the admin to sign in again.
Source: choice: separate the live connection from the authority checked at commit

### C-91: The rollback procedure has an observable drain point
Observable: After admission is disabled and the Pending count is 0, the operator can deploy the previous release without leaving any accepted attempt unfinished.
Source: choice: make the safe rollback point observable without requiring cancellation

### C-92: Only a deployment operator can change import admission
Observable: An admin without the deployment's existing operator authority cannot enable or disable admission. A person with that authority can do so without having user-directory admin authority.
Source: choice: separate maintenance rights from permission to create or inspect user accounts

### C-93: An unavailable result read is reported as unavailable
Observable: When activity cannot be read because the service is unavailable, an authorized admin sees an unavailable outcome lookup or a connection failure. The feature does not show an empty history, an unknown reference, or a failed import as if the lookup succeeded.
Source: choice: a read failure must not be mistaken for proof that a submission can be safely replaced

### C-94: Unaccepted uploads do not remain available to the importer
Observable: After the service refuses a delivery or its first admission window expires without acceptance, the importer retains no bytes from that unaccepted delivery for processing, diagnostics, or activity. Hosting infrastructure retention outside the importer is unconfirmed.
Source: choice: close the lifetime of input that never became an accepted attempt

### C-95: An admission acknowledgement identifies the attempt
Observable: If an acceptance response reaches the admin, it identifies the attempt reference and gives the current state or a way to read that state.
Source: choice: an admin receiving confirmation should be able to open the corresponding result

### C-96: A rollback does not reset the lifetime of retained outcomes
Observable: If the previous version has no import activity, the feature may be unavailable during rollback. After the importer is redeployed, the authorized submitter can retrieve retained outcomes that are still younger than 168 hours from completion.
Source: choice: keep the same recovery lifetime through compatible rollback and redeployment

### C-97: User management shows the submission action only to authorized admins
Observable: Signed-out users and signed-in callers without current admin authority for the selected directory are not offered the CSV submission action in user management.
Source: choice: hide an action that these callers cannot use while retaining the direct-submission authority check in C-3

### C-98: An unauthorized submission is refused before content validation
Observable: A caller without submission authority receives an access refusal whether the submitted CSV is valid, malformed, or contains an existing account identity.
Source: choice: unauthorized callers must not gain access to validation or account existence information

### C-99: A known failure to accept a complete submission is reported as an admission failure
Observable: If the service receives a complete upload but cannot durably accept it, an acknowledgement that reaches the authorized admin reports non-acceptance. An intake outage can make the acknowledgement unavailable. Repeating delivery with the same current reference remains eligible for admission if no attempt was accepted.
Source: choice: a temporary intake outage should permit recovery without inventing a Pending or Failed result for work the service never accepted

### C-100: Selecting a file by itself does not submit an import
Observable: An admin can select or replace a file without starting an upload or creating an attempt. The explicit submission acts on the file and directory selected at that action.
Source: choice: let the admin confirm the input before initiating account creation

### C-101: An unreadable pending count cannot signal a completed drain
Observable: If the operator cannot read the current Pending count, the drain status is unavailable. A missing or stale count does not report that work has drained.
Source: choice: the operator must be able to distinguish a completed drain from an outage before rollback
