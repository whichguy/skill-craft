## Use cases

### U-1: A directory admin imports a first batch to create users
Flow: The admin finds CSV import in user management, reads the input requirements, selects a CSV containing new users, submits it, then checks the result and finds the new users in the directory.
Source: request

### U-2: A directory admin repeats an import to finish without duplicating users
Flow: The admin submits the same file again after success, or reconnects after losing the result of the first submission. The admin can recover the attempt from their recent imports and tell which attempt created users.
Source: implied: bulk creation can be repeated or interrupted.

### U-3: A directory admin submits an empty CSV to see why nothing was created
Flow: The admin submits a zero-byte file, a blank file, or a file containing only its header. The admin sees that no user records were supplied.
Source: implied: an upload can contain zero users.

### U-4: A directory admin submits a batch at the supported size to create users in one operation
Flow: The admin reads the byte and record limits, submits a valid file within them, then sees the full result. For a file exceeding either limit, the admin sees the applicable limit and zero creations.
Source: implied: bulk uploads have finite capacity.

### U-5: A directory admin corrects a rejected import to create the intended users
Flow: The admin submits a malformed CSV, a CSV with invalid user data, or a CSV containing duplicate identities. The admin locates the problem in the result, corrects the source file, and submits a new attempt.
Source: implied: the upload can fail input validation.

### U-6: A person without directory-admin access attempts an import to learn whether access is available
Flow: The person opens user management or attempts to submit a CSV or retrieve an import result directly. The service prevents unauthorized access and creates no users from the refused submission.
Source: implied: the request designates admins as the actors.

### U-7: A directory admin recovers from a service failure to determine whether to retry
Flow: The admin loses the upload response, encounters a temporary service error, or sees processing fail. The admin checks the attempt's outcome before retrying.
Source: implied: upload, validation, and account creation depend on a working service.

### U-8: A newly created user accesses their account through ordinary onboarding
Flow: Once the import succeeds, the new user follows the directory's ordinary activation or first-sign-in process. If delivery fails, an admin can use any recovery action offered by ordinary onboarding.
Source: implied: the request creates users in the existing product.

### U-9: An operator enables CSV import to make it available to admins
Flow: The operator checks readiness, enables import, and verifies the import entry point and a successful attempt in the target deployment. A failed readiness check leaves import unavailable.
Source: implied: the feature must be deployed before U-1 can occur.

### U-10: An operator configures CSV import to control batch capacity
Flow: The operator reads or sets the byte and record limits, verifies the effective values, and checks that new attempts use those values. Invalid settings produce feedback.
Source: implied: the operator needs to control the capacity used in U-4.

### U-11: An operator stops imports to prevent further account creation
Flow: The operator disables import globally or stops an individual unfinished attempt. The operator checks whether the stop took effect before the creation commit.
Source: implied: the operator must be able to stop U-1 globally or for one case.

### U-12: An operator investigates a failed attempt to identify what needs attention
Flow: The operator filters recent attempts by outcome or looks up one by reference. The operator sees its lifecycle and the failure category. An unknown or expired reference returns no retained result.
Source: implied: an operator needs to find one unsuccessful import among successful ones.

### U-13: An operator introduces import into a directory with prior data to preserve existing accounts
Flow: The operator enables the feature with existing users present. An admin imports a file containing an existing identity and sees a conflict while the existing user remains intact.
Source: implied: bulk creation runs beside existing user management.

### U-14: An operator remedies a mistaken import to remove its effect on account access
Flow: The operator uses the successful attempt's creation references to identify the affected accounts, then uses ordinary account controls. The operator can tell which accounts were remediated. Ordinary controls report missing accounts, refused access, or failed actions.
Source: implied: someone may need to undo a successful U-1.

### U-15: An operator rolls back the release to remove the import feature safely
Flow: The operator disables import and waits until zero attempts are pending before restoring the prior release. Rollback cannot proceed while import is enabled or an attempt remains pending. The prior release can still manage users already created through import.
Source: implied: the operator may need to return to the version before U-9.

### U-16: Directory admins submit overlapping changes to create each identity at most once
Flow: Two admins submit overlapping files, or an import overlaps ordinary user creation. Each actor sees the outcome for their own operation, with the existing identity rule deciding conflicts.
Source: implied: U-1 can happen alongside another write to the directory.

## Clauses

### C-1: Directory admins can find CSV import in user management.
Observable: A signed-in directory admin eligible to create users can reach the CSV import entry point from user management while import is available.
Source: implied: U-1 requires a discoverable entry point.

### C-2: Directory admins can submit a CSV file for bulk user creation.
Observable: The admin selects a CSV and submits it in a single import action.
Source: request

### C-3: A successful import creates the users represented by its valid new records.
Observable: After a successful submission of a CSV representing two distinct new users, the admin can find both users through ordinary user management. The import creates one account per data record.
Source: request

### C-4: A repeated import creates zero additional users for previously created identities that remain reserved.
Observable: While the earlier users' identities remain reserved, submitting them again under a new reference leaves one account per original identity.
Source: implied: U-2 repeats a create operation for the same identities.

### C-5: An input containing no user records creates zero users.
Observable: A zero-byte, blank-only, or header-only upload leaves the directory unchanged.
Source: implied: U-3 supplies no users to create.

### C-6: The import accepts batches at the documented capacity limits.
Observable: With no other refusal condition present, a valid CSV whose byte count, record count, or both reach the applicable limit is accepted.
Source: choice: an inclusive maximum is straightforward for admins preparing U-4.

### C-7: An oversized file is refused.
Observable: A file above the effective byte limit produces a byte-limit result with zero user creations.
Source: choice: a bounded upload keeps U-4 practical.

### C-8: A file with too many user records is refused.
Observable: A structurally valid file within the byte limit whose data-record count exceeds the effective record limit produces a record-limit result with zero user creations.
Source: choice: bound the amount of work per U-4.

### C-9: An admin can tell when an import is refused for input problems.
Observable: A file refused for malformed CSV, invalid user data, or a duplicate identity produces a result distinguishable from success.
Source: implied: U-5 needs to know whether correction is required.

### C-10: A person without directory-admin authority cannot start an import.
Observable: A signed-out person or a signed-in person lacking that directory's admin authority is refused when submitting an import, with zero users created.
Source: implied: U-6 follows from “Let admins upload.”

### C-11: A known creation failure has an outcome distinguishable from success.
Observable: When the directory write has failed and its outcome is known, the admin sees that the attempt did not succeed.
Source: implied: U-7 needs to know whether creation happened.

### C-12: Imported users use the directory's ordinary onboarding path.
Observable: A newly imported account is eligible for the same activation or first-sign-in actions as an equivalent ordinarily created account.
Source: implied: U-8 receives an ordinary user account.

### C-13: The operator can enable import for a deployment.
Observable: After the operator enables a ready deployment, the import entry point becomes available to its admins.
Source: choice: use one deployment-wide availability control for U-9.

### C-14: The operator can configure import capacity.
Observable: The operator can set the maximum upload bytes and maximum data records independently.
Source: choice: these two controls address the resource bounds in U-10.

### C-15: The operator can disable import for the deployment.
Observable: While import is disabled, direct submissions are refused for unavailability.
Source: choice: provide a global stop for U-11 through the same availability control used for rollout.

### C-16: The operator can stop one attempt before account creation commits.
Observable: If the attempt-specific stop takes effect before commit, its result is canceled.
Source: choice: give U-11 a targeted stop without requiring a deployment-wide interruption.

### C-17: The operator can retrieve a known attempt by reference.
Observable: Entering an attempt reference in the operator lookup returns the attempt within the applicable retention period.
Source: choice: U-12 needs to isolate a specific attempt.

### C-18: Import leaves preexisting users intact.
Observable: Uploading data for a preexisting user leaves that user's identity, account data, permissions, and access state unchanged by the import.
Source: implied: U-13 creates users rather than modifying existing ones.

### C-19: A successful import identifies the accounts it created.
Observable: An authorized operator viewing the successful attempt can determine the directory account reference for each created record.
Source: choice: U-14 needs a reliable way to target ordinary account controls.

### C-20: Users created by import remain ordinary directory users after release rollback.
Observable: After U-15, each previously committed user that still exists remains visible and manageable through ordinary user management on the prior release.
Source: implied: release rollback in U-15 preserves existing user data.

### C-21: Concurrent imports create at most one account for the same directory identity.
Observable: Two overlapping imports cannot between them create two accounts for that identity in the same directory.
Source: implied: the identity created in U-1 remains the same in U-16.

### C-22: An import targets one directory.
Observable: The submission view identifies the directory being managed. Every row in that attempt targets that directory, even if the admin switches to another directory while processing is underway.
Source: choice: scope the bulk action to the same directory the admin is managing in U-1.

### C-23: CSV import is discoverable only with authority to create users in the target directory.
Observable: The entry point is offered to signed-in admins who can ordinarily create users in that directory when import is enabled. It is absent for signed-out visitors, regular users, read-only admins, and admins authorized only in another directory.
Source: choice: use ordinary directory user-creation authority to distinguish eligible admins in U-1 and U-6.

### C-24: The submission view tells the admin what input it accepts.
Observable: Before selecting a file, an eligible admin can find the required header, CSV conventions, accepted identity values, effective byte and record limits, and the rule that any rejected record prevents creation for the batch.
Source: choice: make every input requirement for U-1, U-3, U-4, and U-5 discoverable at submission.

### C-25: One submission takes one file.
Observable: The admin can submit one selected file per attempt. A call supplying zero files or multiple files is refused with no creations.
Source: choice: one file per attempt is the smallest submission contract for “upload a CSV.”

### C-26: CSV import recognizes UTF-8 text.
Observable: A valid UTF-8 file passes encoding validation with or without one leading UTF-8 byte-order mark. Invalid UTF-8 is rejected as an encoding error. The mark, when present, counts toward the byte limit.
Source: choice: a single encoding with optional leading mark covers common CSV exports.

### C-27: The importer recognizes comma-separated CSV records.
Observable: A comma separates fields outside double quotes. Double quotes may enclose an entire field, doubled double quotes within a quoted field represent one quote, and commas or line breaks in a quoted field belong to that field. Text before an opening quote or after a closing quote other than a delimiter, record terminator, or end of file, an unescaped quote in an unquoted field, and an unclosed quoted field are CSV syntax errors. Outside quotes a line feed or carriage return followed by line feed terminates a record. A lone carriage return outside quotes is a syntax error. The last record may end at end of file.
Source: choice: define the accepted CSV dialect needed for U-1 and U-5.

### C-28: The importer ignores blank records.
Observable: Empty records or records consisting solely of unquoted spaces or tabs are ignored before or after the header. A quoted empty value is a field value that is validated as data. A blank line inside a quoted field stays inside that field.
Source: choice: tolerate incidental blank lines in U-3 without dropping an explicitly empty user value.

### C-29: The CSV header declares exactly one field, email.
Observable: The first nonblank record must contain a single parsed field equal to `email` after trimming surrounding ASCII spaces and tabs and comparing without regard to ASCII letter case. Missing, repeated, and unknown header fields are rejected as a header error. Name, role, status, password, and all other fields are excluded from the CSV surface.
Source: choice: one identity field suffices for U-1 and keeps profile, access, and credential controls in ordinary user management.

### C-30: Each data record supplies one field.
Observable: Every nonblank record after the header must have exactly one field. A record with more than one field is reported as a width error.
Source: choice: keep the data layout aligned with the one-field header.

### C-31: The email value is required.
Observable: An empty email, including a quoted empty field or a value empty after trimming surrounding ASCII spaces and tabs, is rejected with a missing-email reason.
Source: choice: email is the identity field in C-29.

### C-32: An import accepts the ordinary directory's allowed email identities.
Observable: After trimming surrounding ASCII spaces and tabs, a nonempty value passes email validation when the ordinary create flow accepts it as an email identity. The rule covers permitted characters, address structure, domain syntax, and length. The ordinary directory's domain allow or deny policies are creation policies under C-85. The exact host-specific syntax and length limits are unconfirmed. C-34 supplies the limits where no ordinary syntax rule exists.
Source: choice: reuse the directory's email eligibility contract for consistency with U-8 and U-16.

### C-33: Import uses the ordinary directory's identity equivalence rule.
Observable: Two parsed emails which the ordinary create flow treats as the same identity conflict in import, whether they occur in one file or in separate writes. Import uses the same case, Unicode, alias, and domain treatment as ordinary creation.
Source: choice: one ordinary identity rule serves bulk creation and preexisting accounts.

### C-34: A directory without an established email validation rule uses the baseline email syntax.
Observable: In that baseline, a valid email has one ASCII local part, one `@`, and a domain of at least two nonempty dot-separated ASCII labels. The local part has 1–64 characters and consists of nonempty dot-separated runs of ASCII letters, digits, or the characters in the set ``!#$%&'*+-/=?^_`{|}~``. Each domain label has 1–63 letters, digits, or hyphens with a letter or digit at each end. The full trimmed value has at most 254 characters.
Source: choice: specify the baseline email syntax for ordinary creation and import where the host supplies none.

### C-35: A batch with no data records is rejected.
Observable: For an empty file, blank-only file, or valid header without nonblank data, the result identifies that no user records were supplied.
Source: choice: make U-3 actionable and distinguish an empty batch from successful creation.

### C-36: A structurally valid batch counts data records toward its row limit.
Observable: The count includes each nonblank logical record after a valid header, including records with invalid fields. The header, ignored blank records, and line breaks within a quoted field add zero to the count.
Source: choice: count the records submitted for processing in U-4.

### C-37: Import rejects a file containing an identity repeated within that file.
Observable: When two or more otherwise valid row identities are equivalent under the target directory rule, the result identifies every occurrence as a duplicate within the file.
Source: choice: avoid silently choosing one occurrence when U-5 needs correction.

### C-38: Import rejects a file containing an identity already reserved in the target directory.
Observable: A row whose identity ordinary creation would reject as already taken reports an existing-identity conflict. If the host defines reservation by account state, import follows that complete rule. Host state names are deliberately left to the ordinary directory contract because no host is identified. C-131 supplies the baseline where no state-based reservation contract exists.
Source: choice: preserve the ordinary identity reservation contract for U-13 and U-16.

### C-39: A rejected batch creates zero accounts.
Observable: An otherwise valid new identity beside a rejected row is absent from the directory after that attempt, unless another operation created it.
Source: choice: an all-or-nothing result lets U-5 correct the file and submit it again intact.

### C-40: The admin can locate a reported row problem in the submitted file.
Observable: Each row problem identifies the one-based physical line where the logical record starts. Counting begins at line 1 and advances by one for every line feed, including a line feed preceded by a carriage return or occurring inside quotes. The header and skipped blank lines count toward line numbering.
Source: choice: use source line numbers to locate faults in U-5.

### C-41: The admin can distinguish the causes of a rejected batch.
Observable: Rejection reasons distinguish missing or multiple files, byte limit, invalid encoding, malformed CSV, bad header, no records, record limit, wrong record width, missing email, invalid email, duplicate in file, existing-identity conflict, and ordinary creation-policy refusal. The last category follows the ordinary create rule in force for the target, including a directory account cap if there is one. For limit reasons the result gives the applicable limit and its unit.
Source: choice: these are the rejection categories the admin can act on in U-3, U-4, and U-5. Authorization, availability, and service failures are separate outcomes.

### C-42: The import reports all detectable row problems after file-level checks pass.
Observable: For an eligible file within both limits, the result reports each width, required-value, email, duplicate, or existing-identity problem found during validation, including multiple applicable reasons for the same row. Checks requiring an email identity run only on rows with a valid identity. A file-level issue may stop evaluation before row diagnostics are available.
Source: choice: allow one correction round for multiple row problems without requiring error recovery from an unreadable or oversized file.

### C-43: File-level rejection has deterministic precedence.
Observable: If several file-level problems coexist, the first applicable is absence or multiplicity of files, byte limit, invalid encoding, CSV syntax, bad header, no records, then record limit. For empty or blank-only content the no-records result applies without a header check.
Source: choice: define the visible result when a file-level problem can prevent diagnosing other problems.

### C-44: Imported users receive the ordinary least-privileged user role for the directory.
Observable: A newly imported user can exercise only the permissions ordinarily granted to a new standard user. A CSV with permission-related headers is refused under the header rule.
Source: choice: U-1 creates user accounts and leaves privilege assignment to ordinary controls.

### C-45: Import uses ordinary account defaults for values outside its CSV schema.
Observable: A newly created account has the ordinary defaults for profile fields, activation state, credentials, membership, and account preferences. If no ordinary creation path predates import, the baseline account has its email identity, an ordinary account reference, standard user designation, an activation state awaiting proof of email, no preassigned password, no extra group membership, and no supplied profile or preference values. It can establish access through the directory's normal proof-of-email onboarding.
Source: choice: use the ordinary account contract for U-8. Profile values, extra memberships, credentials, and preferences are outside the CSV schema.

### C-46: Account provisioning is complete only when ordinary user management can find the new accounts.
Observable: On seeing success, an admin can retrieve every created account by its reference through ordinary user management while that service is available and the account still exists.
Source: choice: make a success result immediately usable in U-1.

### C-47: Import preserves the directory's normal onboarding delivery policy.
Observable: A directory configured to send an invitation for ordinary creation uses its ordinary invitation policy for each committed imported user. A directory with no such policy sends no unsolicited import-specific communication. The ordinary delivery outcome remains observable through ordinary onboarding controls.
Source: choice: avoid creating a second invitation policy for U-8.

### C-48: An admin can retrieve their own attempt outcome.
Observable: The initiating admin can retrieve an attempt by its reference while still authorized for its directory and while it is within retention.
Source: choice: U-2 and U-7 need a result that survives loss of the original response.

### C-49: An attempt result has a defined set of states.
Observable: Within retention an attempt is pending, succeeded, rejected, failed, or canceled. Pending means no terminal outcome has been established. Succeeded means every account was committed. Rejected means a defined input or ordinary creation policy refused the batch. Failed means processing, upload completion, or a dependency prevented creation. Canceled means global disable, an operator stop, or a loss of creation authority prevented commit. Every terminal state except succeeded has zero creations.
Source: choice: give U-1 through U-7 and U-11 through U-12 an unambiguous result vocabulary.

### C-50: The visible result summarizes the attempt.
Observable: The initiating admin sees the attempt reference, target directory, current state, and terminal creation count. The result supplies the data-record count when known, the applicable reason for a terminal nonsuccess, the available row diagnostics for rejection, and the created account references for success. An unknown data-record count is distinguishable from zero.
Source: choice: expose what U-1, U-5, and U-7 need to reconcile the attempt.

### C-51: Import is disabled by default on a deployment's first release with the feature.
Observable: Before the operator enables the feature, directory admins cannot start an import.
Source: choice: let the operator verify readiness before U-9 exposes user creation.

### C-52: Enabling import requires readiness.
Observable: An enable request is refused with the unmet check identified if any of these is unavailable: ordinary directory role enforcement, standard-user creation from email alone with whole-batch commit, ordinary account lookup, an ordinary onboarding path, an ordinary access-revocation action, attempt outcome lookup, or upload capacity for the effective limits. The operator sees the feature remain disabled.
Source: choice: U-9 should expose import only where an admin can authorize, complete, and reconcile a batch.

### C-53: The operator can read the effective import settings.
Observable: The settings view gives the enabled or disabled state, effective byte limit in bytes, and effective record limit in records.
Source: choice: these are the import settings the operator needs to verify for U-9 and U-10. Notifications, account defaults, and role assignment stay under ordinary directory controls.

### C-54: The upload-byte setting defaults to 5,242,880 bytes.
Observable: A deployment with no byte override displays and enforces 5,242,880 bytes.
Source: choice: 5 MiB leaves room for the default number of email records in U-4.

### C-55: The data-record setting defaults to 1,000 records.
Observable: A deployment with no record override displays and enforces 1,000 data records.
Source: choice: 1,000 is a practical baseline for U-4 and for reporting validation errors.

### C-56: The upload-byte setting accepts integer values from 1,024 through 5,242,880 bytes.
Observable: The operator can save either endpoint. A noninteger, a value below 1,024, or a value above 5,242,880 is refused with the permitted range shown.
Source: choice: let deployments reduce capacity while leaving room for ordinary one-record files.

### C-57: The data-record setting accepts integer values from 1 through 1,000 records.
Observable: The operator can save either endpoint. A noninteger, a value below 1, or a value above 1,000 is refused with the permitted range shown.
Source: choice: allow a lower deployment capacity without increasing the supported ceiling.

### C-58: A refused settings update preserves the effective settings.
Observable: After an update with any invalid value or a refused enable request, reloading the settings shows the same availability state, byte limit, and record limit as immediately before the request.
Source: choice: prevent an operator from unintentionally applying part of a rejected change.

### C-59: Capacity edits apply to attempts started after the edit takes effect.
Observable: An attempt started before a capacity change keeps its original byte and record limits. An attempt started after it uses the new values.
Source: choice: U-10 should change future submissions without retroactively refusing work already started.

### C-60: A directory admin without operator authority cannot use import operations controls.
Observable: Direct attempts by a nonoperator to enable, disable, change limits, stop another attempt, or read operator records are refused. A signed-in directory admin retains only their own authorized submission and result access.
Source: choice: separate deployment administration from bulk user creation.

### C-61: A deployment operator can filter import attempts by state.
Observable: During the 30 days after an attempt reaches a terminal state, the operator can find it by its state or by its reference. Pending attempts appear while pending. The available state filters are pending, succeeded, rejected, failed, and canceled.
Source: choice: U-12 needs a repeatable way to find failures and in-flight attempts.

### C-62: The operator can inspect the attempt's progress history.
Observable: Within retention, the operator sees the attempt reference, target directory, initiating account reference, start time, current state, terminal time when available, effective byte and record limits, submitted file byte count when known, data-record count when known, creation count when terminal, and terminal reason category when applicable. The history identifies the time of upload admission, validation start, and terminal outcome for events that have occurred. It includes created account references on success.
Source: choice: expose the data needed to diagnose U-7 and U-12 without recording CSV contents for the operator.

### C-63: The operator can attribute import control changes.
Observable: For an accepted control change, the operator can see who made it, its time, its type, and its effect until 30 elapsed days after the change. At that boundary the import control history stops returning the entry. The types are enable, disable, capacity change, and attempt stop. The effect is the resulting availability state, the resulting limits, or the stopped attempt reference, as applicable.
Source: choice: U-9 through U-12 need a record of which operator action took effect.

### C-64: Terminal attempt details are available for 30 days after the terminal transition.
Observable: An authorized admin or operator can retrieve a terminal result before 30 elapsed days have passed. At 30 elapsed days, lookup no longer returns the attempt details.
Source: choice: give U-7, U-12, and U-14 a bounded period to reconcile or investigate work.

### C-65: The operator remediates mistaken creations through ordinary account controls.
Observable: The operator can take a created account reference from the retained success result to ordinary user management and use its ordinary access-revocation action, such as suspension or deactivation where available, if authorized for that action. The directory shows the resulting access state for each affected account.
Source: choice: U-14 can revoke mistaken access through the same controls used for other users.

### C-66: Import exposes zero bulk account-undo actions.
Observable: The completed attempt offers no action to reverse its account creations. Deletion, reactivation, access revocation, and handling user-owned records follow ordinary account controls.
Source: choice: avoid destructive rollback of accounts that may already have signed in or acquired related records.

### C-67: Release rollback has a quiescence check.
Observable: After disabling import, the operator can verify that zero attempts are pending before starting release rollback. Completed results identify the accounts that committed before disable.
Source: choice: U-15 needs a clear point at which outstanding import work has settled.

### C-68: A supported rollback retains eligible attempt history for a subsequent return to import.
Observable: If the import release is restored before the 30-day retention ends, authorized lookup still returns earlier retained outcomes. During the prior release, import-specific controls and history access may be absent.
Source: choice: preserve reconciliation across U-15 while avoiding new interface requirements on the prior release.

### C-69: The operator can verify a first successful import end to end.
Observable: After U-9, the operator can use an authorized admin account or an authorized admin's attempt reference to confirm a successful terminal result for a fresh standard user and confirm that ordinary management finds that user.
Source: choice: verify the deployed capability through its ordinary entry point without requiring a separate verification feature.

### C-70: The admin receives a stable attempt reference before the file transfer starts.
Observable: Once the service accepts the start of a submission, the admin can see or recover the attempt reference from the submitting session before the file is transmitted. That reference identifies the attempt as pending until its terminal outcome.
Source: choice: U-2 and U-7 need an identifier even when the file-transfer response is lost.

### C-71: An uncertain file transfer can be retried under its original attempt reference.
Observable: An admin with an authorized, pending attempt whose file transfer never completed can resend the whole file under the same reference while admission is still open. Incomplete bytes alone create zero users.
Source: choice: let U-7 recover from a broken connection without requiring resumable transfer.

### C-72: Only the first file submission decided for a reference can affect that attempt.
Observable: Once a file submission is admitted or definitively refused, later transfers for the same reference return the same attempt's current outcome even if their contents differ. A corrected submission requires a fresh reference.
Source: choice: make retries safe when U-2 and U-7 cannot tell whether the first file arrived.

### C-73: Retry takes no creation action for an unrecognized or expired reference.
Observable: Replaying a transfer with an unknown or expired reference is refused. Starting a new import is a separate explicit action.
Source: choice: late requests cannot recreate old attempts after their history expires.

### C-74: An attempt has a 15-minute window to commit.
Observable: The elapsed window starts when the attempt reference is established. A pending attempt may commit only before 15 elapsed minutes. A commit already decided within the window keeps its outcome.
Source: choice: bound the time an accepted U-7 attempt can still cause account creation.

### C-75: A disconnected client does not stop an admitted attempt.
Observable: Closing the submitting view or losing the connection after admission leaves the attempt eligible to finish. The admin can check the same reference when connected again.
Source: choice: distinguish connection loss from an explicit stop in U-7 and U-11.

### C-76: A temporary inability to check an outcome is reported as lookup unavailability.
Observable: When the outcome service cannot answer, the admin sees a temporary availability problem or a failed connection. After recovery, the same reference returns the authoritative state, subject to retention.
Source: choice: distinguish an unavailable reply from a failed attempt in U-7.

### C-77: An attempt's terminal outcome is final.
Observable: Reopening a terminal result or replaying its submission returns the same outcome, reason, and counts while retained. A later disable, stop, delivery error, suspension, or ordinary deletion does not revise the original outcome.
Source: choice: let operators and admins reconcile recorded creation separately from later account actions.

### C-78: A committed batch cannot have a failed, rejected, or canceled outcome.
Observable: If the service restarts or loses a reply at the point of account creation, a later successful lookup records the committed batch as succeeded. If no commit occurred, zero accounts are attributed to that attempt.
Source: choice: preserve one authoritative outcome across the failure boundary in U-7.

### C-79: An attempt checks the initiating admin's current creation authority before commit.
Observable: If the initiating account is disabled, deleted, or has lost creation authority for the target directory when the commit is decided, no users are created and the attempt is canceled for lost authority. Ordinary session expiry alone does not cancel an admitted attempt for an otherwise authorized account.
Source: choice: honor effective account authority while allowing background work to survive a disconnected session.

### C-80: Global disable prevents pending attempts from committing.
Observable: After a successful disable, attempts still pending at that decision are canceled for global disable. An attempt that committed first retains success. Re-enabling creates no new work from a canceled attempt.
Source: choice: give U-11 a clear boundary for in-flight work.

### C-81: An attempt-specific stop is decided against commit.
Observable: A stop that takes effect first produces zero creations for that attempt. If the attempt already has a terminal decision, including cancellation, the stop returns that existing terminal result.
Source: choice: resolve a stop and a commit reaching the same attempt in U-11.

### C-82: Existing terminal results remain readable while new imports are disabled.
Observable: An authorized admin or operator can retrieve a retained result after the operator disables import.
Source: choice: reconcile U-11 and prepare U-15 while intake is stopped.

### C-83: Overlapping creation operations resolve against the current directory identity rule.
Observable: If an ordinary create or another import commits a conflicting identity first, the later import rejects the entire batch for an existing-identity conflict. If the import commits first, a later ordinary create sees the ordinary conflict result. Disjoint valid batches may both succeed.
Source: choice: apply one directory conflict boundary in U-16 without specifying which concurrent request wins.

### C-84: Changes to identity reservation are reflected at the import commit decision.
Observable: An email change, deletion, or restoration committed before the import's creation decision has its ordinary effect on reservation. A newly reserved identity is rejected. A released identity no longer blocks a later attempt. A terminal rejection remains final if the identity is later released.
Source: choice: prevent stale validation from silently creating accounts that conflict with current directory state.

### C-85: Commit respects all ordinary directory creation policies in force at that point.
Observable: If an ordinary policy such as a user cap or allowed-domain policy would refuse any account or the whole aggregate increase at commit, the import rejects the batch with zero creations.
Source: choice: enforce U-16 against current conditions and preserve the directory selected in U-1.

### C-86: An onboarding delivery problem leaves the account creation outcome intact.
Observable: A standard onboarding delivery refusal or delay after commit leaves the account present and its import succeeded. Any ordinary resend or recovery action remains available for that account.
Source: choice: separate U-8 delivery recovery from retrying account creation.

### C-87: The service reports a closed set of terminal cancellation reasons.
Observable: A canceled result identifies the first effective cancellation cause as global disable, operator stop, or lost directory-admin authority.
Source: choice: distinguish operator and authorization causes in U-7, U-11, and U-12.

### C-88: The service reports a closed set of terminal processing failure reasons.
Observable: A failed result distinguishes upload incomplete, processing deadline, target unavailable, or processing dependency failure. Processing dependency failure covers an unrecoverable storage, processing, or account-write failure before commit. Failure confirmed after a recovery still has zero creations.
Source: choice: make service failures distinguishable from correctable input problems and deliberate stops.

### C-89: Failed remediation of one account remains visible through ordinary controls.
Observable: If an account was already removed, an operator lacks ordinary account-edit authority, or the ordinary remediation action fails, ordinary user management shows the applicable missing-account, access refusal, or action-failure outcome. That remediation leaves the attempt's original account references intact.
Source: choice: U-14 must distinguish a successful access change from an unavailable or failed one.

### C-90: Import checks directory state without blocking ordinary remediation of committed accounts.
Observable: If a user created in an earlier batch is suspended while a later batch containing that identity runs, the suspension takes effect according to ordinary controls. The later batch treats the identity as reserved if suspension ordinarily reserves it.
Source: choice: allow U-14 to proceed independently of U-16 using the ordinary directory rule.

### C-91: The browser upload works without access to the file's local directory path.
Observable: An admin can pick a local file and import its contents without supplying its absolute path. The upload view does not ask for or display that path.
Source: choice: provide the browser entry point for U-1. The [HTML File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file)) supplies selected files without local path components.

### C-92: File-picker type hints do not determine the success of an upload.
Observable: An authorized caller who supplies file contents that meet C-26 through C-43 can proceed when the declared type is missing or generic or the filename has a different suffix. A CSV suffix or media type on invalid content does not make it acceptable.
Source: choice: use the CSV contract at submission because the [HTML File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file)) treats the picker type restriction as a hint.

### C-93: Production import is available only where the end-to-end upload path supports its effective byte limit.
Observable: The operator can verify that a file of exactly the advertised byte limit passes upload admission including any envelope overhead. If the serving path cannot carry that size, readiness refuses enablement at that setting. The specific server, proxy, gateway, and browser hard upload byte ceilings are unconfirmed.
Source: choice: require the serving path to support C-6 because upstream request-size limits can refuse a request before CSV validation. No hosting runtime is identified in the workspace.

### C-94: Any request-duration boundary preserves outcome reconciliation.
Observable: When the upload has been admitted and the original request times out, an authorized caller can look up the outcome separately by reference. The server request-duration limit, proxy or gateway idle timeout, and background execution deadline are unconfirmed. These figures are separate from the 15-minute product commit window.
Source: choice: meet U-7 on a serving path that can close a client request before an import has a terminal outcome. No backend execution runtime is identified in the workspace.

### C-95: Platform capacity rejection cannot be reported as successful creation.
Observable: If an upload or execution is refused by a hosting quota before commit, the caller sees a refusal, an incomplete upload, or temporary unavailability pending reconciliation. A later authoritative result records zero creations for the refused work. Hosting concurrency, queue, execution-memory, and storage quota figures are unconfirmed.
Source: choice: define the result of a runtime refusal in U-7 without assuming a vendor or quota.

### C-96: Production file submission requires a secure connection.
Observable: In a deployment outside development, the browser uses a secure connection for selecting a target or reading a result and for transferring a CSV. An insecure direct submission is refused before accepting its contents for import.
Source: choice: production handling of identity data requires transport protection. The hosting service's certificate provisioning and production network requirements are unconfirmed.

### C-97: Production rollout verifies ordinary account creation before granting import access.
Observable: Before enabling in production, the operator can verify readiness using the same directory authorization, account lookup, and onboarding policies that production will use. The infrastructure prerequisites for production routing, identity-provider setup, and onboarding delivery are unconfirmed because the deployment is unidentified.
Source: choice: U-9 needs a readiness result that applies to the environment being enabled.

### C-98: Ordinary user creation remains available independently of import availability.
Observable: An authorized admin can still create an eligible user through ordinary user management when import is disabled or rejects a file.
Source: implied: “Let admins upload” adds an entry point alongside the ordinary flow.

### C-99: Ordinary user management keeps its existing authorization rules.
Observable: Creating, listing, viewing, editing, suspending, restoring, or deleting an ordinary or imported account through the existing controls requires the same permission each action required before import.
Source: implied: the request changes how users can be created.

### C-100: Ordinary user edits keep their existing effect on account data.
Observable: Changing a profile value, email, group membership, or role through an existing edit action has the ordinary effect for an imported account where that action is available.
Source: implied: the accounts in U-1 are ordinary managed users.

### C-101: Ordinary account lifecycle actions keep their existing effect on access.
Observable: Existing activation, suspension, restoration, deletion, and recovery actions have their ordinary access effect for accounts created before or after import becomes available. Ordinary rules determine which of these actions the directory offers.
Source: implied: U-8 and U-14 use ordinary directory accounts.

### C-102: Import admission enforces the same requirements regardless of submission surface.
Observable: A direct file submission is refused for the same missing authority, disabled availability, file count, byte count, record count, invalid input, or policy conflict that would refuse the same attempt from user management.
Source: choice: apply one acceptance contract whether the caller uses user management or submits directly.

### C-103: A reference alone grants zero access to an import result.
Observable: A signed-out person, regular user, former initiating admin without current authority, another admin without operator authority, or admin from another directory obtains no outcome, diagnostics, account references, or confirmation that the result exists. An authorized deployment operator can use the operator lookup within that deployment.
Source: choice: keep attempt disclosure within the initiating admin's current authority and the operator's deployment scope.

### C-104: A submission cannot retarget an established import.
Observable: Changing the requested directory in a direct call cannot bypass ordinary target authorization or retarget an existing reference.
Source: implied: U-6 requires authority over the accounts being created.

### C-105: Import diagnostics omit submitted field values.
Observable: Admin and operator diagnostics identify problems with reason categories and, for row problems visible to the admin, source line numbers. Diagnostics expose zero raw cells, submitted email addresses, filenames, matched account identifiers, or submitted credential values. The successful creation references in C-19 and C-50 remain available to authorized readers.
Source: choice: provide corrective information without republishing submitted identity or credential data.

### C-106: A completed attempt stops providing access to its source file.
Observable: Once an attempt becomes terminal, neither its admin result nor operator controls offer the CSV or its filename. A retry under that reference provides the retained outcome only.
Source: choice: U-2, U-7, and U-12 need outcome records without a copy of the upload.

### C-107: The import service removes working copies of submitted CSV data within 24 hours of terminal outcome.
Observable: By 24 elapsed hours after the terminal transition, the operator's authorized data inventory contains no import working copy of the CSV or uncommitted row values. Ordinary email data on users created by a successful import follows normal directory retention. Backup expiration follows the deployment's ordinary backup policy, whose duration is unconfirmed.
Source: choice: bound the lifetime of temporary identity data while retaining only the attempt facts needed for U-12.

### C-108: The service treats uploaded values as inert data.
Observable: A filename, header, or cell containing formula, markup, or script text cannot execute when the admin or operator views any import surface. No diagnostics download containing submitted cells is offered.
Source: choice: prevent CSV content from gaining executable meaning on a user-facing result surface.

### C-109: Uncommitted import records have no account or onboarding effects.
Observable: During validation and after a nonsuccess result, candidate records from that attempt are absent from ordinary management and cannot sign in or trigger invitations, group membership, or role grants.
Source: choice: make the all-or-nothing creation boundary visible to admins and prospective users.

### C-110: Successful import uses ordinary onboarding only once per account creation.
Observable: Replaying a successful attempt, looking up its outcome, or resubmitting identities that are still reserved creates no new invitation from import for the original accounts. Ordinary resend and recovery actions may send their usual communications.
Source: choice: a retry of U-2 should neither reprovision an account nor repeat its automatic onboarding.

### C-111: Creation references continue to identify the originally created accounts.
Observable: If an imported account is deleted and the same email is reused, following its retained creation reference returns the original account if ordinarily retrievable or an unavailable account result. It never resolves to the replacement account.
Source: choice: U-14 must avoid applying remediation to a different user.

### C-112: Browser-based import actions require an authorized submission from the product.
Observable: A different website cannot use an admin's or operator's existing session to start an attempt, transfer a file under an existing reference, stop an attempt, change limits, enable import, or disable import through a background browser request.
Source: choice: a signed-in session alone cannot establish that the admin or operator intended the action.

### C-113: The baseline directory compares email identities using ASCII case folding.
Observable: When no ordinary identity equivalence rule exists, two emails that differ only in ASCII letter case conflict within the same directory. The directory preserves distinctions caused by dots or plus tags in the local part.
Source: choice: supply one fallback identity-equivalence rule independently of email syntax.

### C-114: The byte limit applies to the contents of the supplied file.
Observable: Only the raw file content bytes count toward C-56. Request metadata, filename, and transport framing count zero. Admission can refuse as soon as a file exceeds the limit, without requiring the remaining bytes.
Source: choice: the limit in U-4 should be ascertainable from the source file.

### C-115: An attempt exceeding its commit window finishes with a deadline-specific outcome.
Observable: If the deadline is reached before any terminal decision, the outcome is failed for upload incomplete if no complete file was admitted or failed for processing deadline if one was admitted. If the service is unavailable at the deadline, it reports the authoritative outcome when it recovers without permitting a late commit.
Source: choice: close the pending state in U-7 even if the incoming connection or hosting service fails.

### C-116: The initiating admin can find their retained attempts without a reference.
Observable: In user management the authorized admin can find their own pending and retained terminal attempts for the selected directory, with each attempt's reference, state, and start time. Attempts of other admins and other directories are excluded.
Source: choice: U-7 also covers a lost response before the submitting session obtained the reference.

### C-117: An authorized lookup of an unknown or expired reference returns no retained result.
Observable: A lookup within the caller's authorized import surface returns the same unavailable-result response for a nonexistent reference and for one beyond retention.
Source: choice: distinguish a missing retained record from temporary lookup unavailability without preserving expired records.

### C-118: Start refusal is distinguishable from rejection of an accepted attempt.
Observable: Before an attempt is established the caller can distinguish a request requiring sign-in, a refused target authorization, disabled import for an authorized target, and temporary service unavailability when a response is available. No result reference is issued for a definitive start refusal.
Source: choice: let U-6 and U-7 distinguish lack of access or capability from a failed accepted batch.

### C-119: Increasing a capacity setting on an enabled deployment must pass readiness.
Observable: An update that would advertise an effective byte or record limit the serving path cannot support is refused for that readiness check. The prior effective settings still apply.
Source: choice: keep the capacity shown in U-4 true after U-10 changes it.

### C-120: Import release rollback requires the deployment to remain quiescent.
Observable: The rollback action is refused while import is enabled or any attempt is pending. Import cannot be re-enabled once rollback has started. If the import release is later restored, it starts disabled pending operator enablement.
Source: choice: preserve the stop boundary of U-15 until operators can verify readiness again.

### C-121: A commit-time row conflict identifies the newly conflicting record.
Observable: If an ordinary concurrent change reserves a valid row's identity after initial checks, the terminal existing-identity rejection identifies the starting line of each conflicting row found at the commit check.
Source: choice: U-5 needs equally actionable diagnostics when U-16 causes the conflict.

### C-122: An import awaiting a file can be abandoned by the initiating admin.
Observable: Canceling the file picker or leaving before starting sends no file for import. Once a reference has been established, abandoning the view without admission leaves only the pending window in C-74 and creates no users unless an authorized later transfer is admitted under that reference.
Source: choice: separate a canceled local selection from a started attempt during U-1 and U-7.

### C-123: Successful batch creation is visible as one directory change.
Observable: Other ordinary directory operations may observe the directory before the import or after it, with no observable intermediate state in which only some of the batch's accounts have been committed.
Source: choice: apply the whole-batch decision consistently to the readers and writers in U-16.

### C-124: The submitting admin sees the limit that applies to their attempt.
Observable: If the limits displayed before file selection differ from the effective limits at submission start, the attempt shows the limits that apply to it in any resulting limit rejection, in bytes or data records as applicable.
Source: choice: give U-4 actionable feedback when U-10 changes capacity between opening the form and submitting.

### C-125: One deliberate start action establishes at most one attempt.
Observable: Repeating delivery of the same start action while its result is uncertain returns the same reference if an attempt was already established. A caller choosing to start again explicitly gets a new reference. A late copy of an earlier start action cannot establish an attempt after the original reference has expired.
Source: choice: preserve the distinction between retry and a new import in U-2 and U-7.

### C-126: A removed or unavailable target prevents creation in the attempt.
Observable: If the attempt reaches its creation decision and its original directory is gone or unavailable, the attempt reports failed for target unavailable. The service creates zero accounts in the original directory or any replacement directory.
Source: choice: handle directory deletion or loss during U-7 without retargeting the attempt in U-1.

### C-127: A malformed CSV result locates the first syntax problem.
Observable: If malformed CSV is the selected refusal reason, the result identifies the physical line containing the first syntax error in file order, or the starting line of a quoted field still open at end of file. Line numbering follows C-40.
Source: choice: let U-5 find malformed input without requiring recovery of later records from the defective CSV.

### C-128: A failed release rollback leaves import disabled.
Observable: If rollback fails, no new imports become eligible. The operator can end the failed rollback and perform a fresh readiness check before enabling again.
Source: choice: give the stopped deployment in U-15 an explicit recovery path.

### C-129: An operator can verify that temporary import data was removed.
Observable: For a retained attempt, the operator can determine whether any active working copy of the CSV or uncommitted row values remains after the cleanup deadline in C-107. The verification exposes zero submitted values.
Source: choice: make the cleanup deadline operationally observable in U-12.

### C-130: The earliest effective terminal decision determines the outcome of a race.
Observable: Validation rejection, cancellation, confirmed failure, deadline expiration, or successful commit can decide an attempt while it is pending. Once one takes effect, any other event returns or leaves the same outcome. If no event was recorded before the 15-minute cutoff, a successful commit is no longer possible.
Source: choice: give U-7, U-11, and U-16 a common precedence rule without choosing a winner in advance.

### C-131: The baseline directory reserves an identity until permanent account removal.
Observable: Where the host has no ordinary reservation rule, an account awaiting activation, an active account, a suspended or deactivated account, or a deleted account still retained by the directory reserves its email identity. An identity with no remaining account after permanent removal is available for ordinary creation or import.
Source: choice: make baseline identity conflicts predictable for U-13 and U-16 without requiring any particular account-management action from the host.

### C-132: Commit-time refusals have a defined precedence before the batch can create accounts.
Observable: For an otherwise pending attempt, an unavailable target takes precedence over loss of authority for that target. With a target available, loss of authority takes precedence over row or policy checks. With authority confirmed, the result reports any identity conflicts before a directory-wide creation-policy refusal. A refusal decided earlier remains final.
Source: choice: resolve simultaneous failures at the creation decision in U-7 and U-16.

### C-133: The operator can inspect readiness before enabling import.
Observable: While import is disabled, the operator can determine whether each readiness check in C-52 passes and identify each unmet check without enabling intake.
Source: choice: allow U-9 to verify preconditions before granting admins access.

### C-134: Pending status tells the initiating admin whether file admission occurred.
Observable: When looking up a pending attempt, the initiating admin can tell whether it is awaiting an admitted file or processing an admitted file.
Source: choice: U-7 needs to distinguish an available transfer retry from processing already in progress.

### C-135: Import support records omit uploaded contents.
Observable: Import-generated support logs and telemetry contain zero raw CSV bytes, submitted field values, filenames, or submitted credential values, including after encoding, parsing, and processing failures. The attempt reference and the outcome category can be used to correlate an event with the authorized operator record.
Source: choice: preserve the result privacy in U-6 while supporting the diagnosis in U-12.

### C-136: Import operator authority is deployment-scoped.
Observable: An account assigned operations authority for a deployment can use the import operator controls only for that deployment. An ordinary directory admin gains that authority only through the deployment's operator assignment. Any existing deployment operator authorization applies to the import controls.
Source: choice: identify who may use the controls in U-9 through U-15 without requiring a product-specific role name.
