## Use cases

### U-1: An administrator uploads a CSV to create several users
Flow: The administrator opens the user administration area, selects a CSV containing several new users, submits it, and sees the completed creation outcome.
Source: request

### U-2: An administrator imports their first user from a CSV
Flow: On the first visit to the import entry point, the administrator learns what to put in the file, selects a CSV with one new user, and sees that user created.
Source: implied: an administrator must be able to use the upload without prior imports

### U-3: An administrator uploads another file to add more users
Flow: After an import succeeds, the administrator submits a fresh CSV of new users and checks that the earlier users are still present.
Source: implied: bulk-create is a repeatable way to add users to an existing directory

### U-4: An administrator submits a CSV with no user records to learn why nothing happened
Flow: The administrator uploads an empty file or a header-only CSV and sees a reason no users were created.
Source: implied: an upload can contain no records to create

### U-5: An administrator uploads the largest permitted file to complete a large import
Flow: The administrator checks the published size and record allowances, submits a valid file at an allowance, and sees the result. A file exceeding either allowance is refused.
Source: implied: a bounded upload needs an understandable boundary

### U-6: An administrator corrects an invalid CSV to create the intended users
Flow: The administrator uploads a CSV with invalid file structure or invalid user data, sees the reason for refusal, corrects the file, and submits it again.
Source: implied: administrators can select files that cannot supply valid users

### U-7: An administrator resolves duplicate users before importing
Flow: The administrator uploads a CSV containing a repeated user identity or an identity already in the directory, identifies the conflict, and submits a corrected file.
Source: implied: creation must coexist with users already present and with repeated entries

### U-8: A caller without administrator access attempts an import and is refused
Flow: A signed-out caller or signed-in non-admin tries to open the import or invoke submission directly. No users are created by the attempted submission.
Source: implied: the request assigns the ability to admins

### U-9: An administrator recovers from an interrupted import to determine what was created
Flow: The upload, directory service, or connection fails. The administrator checks the outcome and, when creation did not occur, tries again.
Source: implied: the upload and creation can be interrupted

### U-10: An operator controls availability to operate or roll back the import feature
Flow: The operator enables the import for administrators, observes active work, pauses admission when necessary, and uses the existing release rollback process while preserving committed users.
Source: implied: the feature must be operable and recoverable

### U-11: An administrator finds the import instructions to prepare a CSV
Flow: The administrator opens the import from user administration and reads the required column, supported CSV syntax, validation rules, and limits before selecting a file.
Source: implied: U-2 requires an administrator to know what the upload accepts

### U-12: A scoped administrator imports into the intended directory
Flow: The administrator enters import from a directory they administer and submits the file. The resulting users can be found in that directory.
Source: implied: U-1 needs a destination where the created users can be found

### U-13: An administrator checks an import after losing the submission response
Flow: The administrator returns to the import area, finds the attempt, and checks whether it is still running or finished. Repeating submission for that attempt gives its existing outcome when finished.
Source: implied: U-9 includes losses after the service may have accepted the upload

### U-14: Two administrators submit overlapping lists while provisioning users
Flow: Two submissions aimed at the same directory include a shared new identity. The administrators see an outcome consistent with a single owner of that identity and can correct any refused file.
Source: implied: U-1 and U-7 can occur concurrently

### U-15: An administrator returns to an import after a change in account access
Flow: An administrator starts an import, then loses authority to create users in the target. The import respects the new authority boundary when creation would take effect.
Source: implied: U-8 can arise after an authorized submission begins

### U-16: An administrator manages imported users through the same user administration workflows
Flow: The administrator finds a successfully created user through the ordinary directory, then performs an allowed operation such as editing or deleting that user.
Source: implied: U-1 creates users that are usable as ordinary directory users

### U-17: A newly created user uses ordinary activation to access their account
Flow: After the administrator's import succeeds, the new user follows the directory's ordinary first-use steps, such as following an activation notice if the directory sends one, to sign in as a standard user.
Source: implied: U-1 creates accounts subject to the ordinary account lifecycle

### U-18: Another account attempts to retrieve an import result and is refused
Flow: An account other than the submitter tries to find or open the attempt. The result and diagnostics remain inaccessible, even if that account is also an administrator in the directory.
Source: implied: U-13 adds a lookup that another caller could try to use

## Clauses

### C-1: An administrator can upload a CSV for bulk user creation
Observable: An administrator can submit a CSV as the input to a bulk user creation action.
Source: request

### C-2: An import can create multiple users
Observable: With a valid CSV containing two distinct new users, one submission creates both users in the directory it targets.
Source: request

### C-3: An administrator can create one user from a CSV
Observable: A valid CSV containing one new user creates one user.
Source: choice: the same entry point serves a one-record file without a special minimum

### C-4: An administrator can submit a later import
Observable: After the first import completes, a valid file containing a distinct new user can be submitted through the same entry point.
Source: implied: U-3

### C-5: An administrator can determine whether a completed import created users
Observable: The outcome shown to the submitting administrator distinguishes a successful creation from an import that created zero users.
Source: implied: U-1 and U-6

### C-6: A file with no user records is refused
Observable: Submitting a zero-byte file or a recognized header with no data records creates zero users and reports that the file contains no users.
Source: choice: a zero-user upload is best treated as a correctable input error

### C-7: The upload size limit is 1,048,576 bytes per file
Observable: A file of exactly 1,048,576 bytes is within the size allowance. A file of 1,048,577 bytes or more is refused for size and creates zero users. The size counts the file itself, including any header, line endings, and byte-order mark.
Source: choice: a 1 MiB allowance supports routine lists while bounding the amount submitted

### C-8: The import record limit is 1,000 user records per file
Observable: A file with exactly 1,000 data records is within the record allowance. A file with 1,001 is refused for record count and creates zero users. The header and ignored blank records do not count.
Source: choice: a 1,000-record allowance supports bulk provisioning while bounding one import

### C-9: An administrator can identify why an invalid submission was refused
Observable: After submitting invalid input, the administrator receives a reason that identifies what needs correction.
Source: implied: U-6 and U-7

### C-10: A signed-out caller cannot use the import
Observable: A signed-out caller attempting to submit an import is required to authenticate. The submission creates zero users.
Source: implied: U-8

### C-11: A signed-in non-admin cannot use the import
Observable: A signed-in non-admin attempting to submit an import is denied. The submission creates zero users.
Source: implied: U-8

### C-12: A failed import can be retried
Observable: When the import confirms it created zero users because of a dependency failure, the administrator can submit the file in a new attempt after the dependency recovers.
Source: implied: U-9

### C-13: An operator can suspend admission of new imports
Observable: While admission is disabled, an administrator trying to open a new attempt or submit a file to a ready attempt is told that import is unavailable. No new attempt is issued and the ready attempt does not advance.
Source: choice: operators need a reversible way to pause imports during incidents or releases

### C-14: The administrator can find the import from user administration
Observable: An administrator with import access can reach the upload entry point from the area used to administer users.
Source: implied: U-2 requires a discoverable way to use the feature

### C-15: The import requirements are available before file selection
Observable: In the import area, the administrator can find the `email` header requirement, UTF-8 encoding, delimiter, quoting and line-break rules, blank-record handling, email and duplicate rules, and the two limits of 1,048,576 bytes and 1,000 data records.
Source: choice: presenting the supported input requirements before the picker lets the administrator prepare a usable file

### C-16: Imported users belong to the target user directory
Observable: A successful import creates its users in the intended directory. In a product with one directory, the product's user directory is the destination.
Source: implied: U-12

### C-17: An administrator needs user-creation authority in the target directory
Observable: A signed-in administrator who can create users in the target directory can submit imports when available. A signed-in administrator who lacks that authority in the target is refused.
Source: choice: the upload should carry the same authority boundary as ordinary user creation

### C-18: Each uploaded file is decoded as UTF-8
Observable: Valid UTF-8 is accepted at the encoding stage. A UTF-8 byte-order mark at the beginning is allowed. Invalid UTF-8 is refused with an encoding reason.
Source: choice: one broadly supported encoding gives the administrator a clear export setting

### C-19: CSV uses commas as field separators
Observable: Outside quoted fields, a comma separates fields. Tab and semicolon separated files qualify only if their content independently satisfies the comma-based format and column rules.
Source: choice: a single delimiter removes the need to infer the dialect

### C-20: CSV accepts LF, CRLF, and CR as record breaks
Observable: Outside quoted fields, LF, CRLF, and CR each end one record. The last record can end at end of file.
Source: choice: common export line endings should work without conversion

### C-21: CSV accepts double-quoted fields
Observable: A field may be wrapped in double quotes. Inside a quoted field, commas and line breaks are field content, and two consecutive double quotes represent one literal double quote.
Source: choice: common CSV exporters use these quoting rules

### C-22: Malformed CSV quoting is refused
Observable: A double quote within an unquoted field, an unclosed quoted field, or any character between a closing quote and the next delimiter, record break, or end of file causes a file-format refusal.
Source: choice: malformed quoting cannot reliably identify the intended records

### C-23: Empty records outside quoted fields are ignored
Observable: A record made of zero characters is ignored, including before the header and between data records. A line containing whitespace, a delimiter, or a quoted empty field remains a record.
Source: choice: empty lines are common in exports and absence of data can be distinguished from an empty supplied value

### C-24: The first nonempty record must contain the single `email` header
Observable: In a file with a nonempty record, the first such record must parse to exactly one field whose value is `email`, with matching case and no surrounding whitespace. Any other first nonempty record is a header error.
Source: choice: a single published column is sufficient to identify a user without inventing optional account attributes

### C-25: Each data record must have exactly one field
Observable: A data record with other than one parsed field is refused with a row reason.
Source: choice: the row must match the one-column header so extra values cannot silently affect creation

### C-26: Outer spaces and tabs are removed from submitted email values
Observable: After CSV decoding, leading and trailing ASCII spaces and tabs are removed from the `email` field. Validation, identity matching, and account creation use the resulting value subject to ordinary directory normalization.
Source: choice: ordinary spreadsheet padding should not change which user is created

### C-27: Every imported email must pass the ordinary user-creation email validation
Observable: An email value that would be refused by ordinary user creation for that directory is refused at import. The same validation applies after trimming, including when the value is empty.
Source: choice: importing should respect existing eligibility for an account email

### C-28: A deployment without established email validation uses the baseline validation rules
Observable: The trimmed value contains one `@` separating a local part and a domain. The local part is 1–64 ASCII characters drawn from letters, digits, period, underscore, plus, and hyphen, with no leading, trailing, or adjacent periods. The domain has at least two period-separated labels, each 1–63 ASCII letters, digits, or hyphens, with no leading or trailing hyphen. The entire value is at most 254 ASCII characters. Values outside this profile are refused as invalid email.
Source: choice: a deployment with no inherited rule needs a concrete profile for common account email addresses

### C-29: Duplicate detection uses the directory's existing user identity rule
Observable: Two email values that ordinary user creation treats as the same identity are treated as the same identity by import, within a file and against existing users in the target directory.
Source: choice: duplicate detection must agree with the directory it writes to

### C-30: A deployment without an established identity rule compares email case-insensitively
Observable: In a directory with no existing identity rule, trimmed email values that differ only in ASCII letter case identify the same user. Comparisons cover the full address within the target directory. Periods and plus suffixes remain significant.
Source: choice: case variants are a common source of duplicate account creation

### C-31: An existing identity is refused as a conflict
Observable: A record matching an identity that the target directory treats as reserved is refused as an existing-user conflict. The directory's full list of states that reserve identities is deliberately left to its ordinary user-creation policy because no directory is supplied. In the baseline, a current user reserves an identity in every account state. A removed record with no retained reservation does not reserve it.
Source: choice: the existing directory is authoritative about which users reserve an identity

### C-32: Repeated identities within one file are refused as a conflict
Observable: A CSV with two data records referring to the same identity is refused with a duplicate-in-file reason.
Source: choice: one attempt should describe each user once so the administrator can correct duplicates explicitly

### C-33: A reported row error identifies its source line
Observable: A row error includes the physical line number where the CSV record begins, counting from 1 at the start of the file. Each LF, CRLF, or CR advances one line, including inside quoted fields and on ignored blank lines.
Source: choice: a file-relative position lets administrators correct the original CSV without reproducing its contents

### C-34: The result reports the number of users created by the attempt
Observable: A successful attempt reports its number of created users as the number of data records accepted. A completed refusal or confirmed failure reports zero created users.
Source: choice: the administrator needs a count to reconcile an uploaded list

### C-35: An operator can resume admission of new imports
Observable: Once the operator enables admission and user creation is available, an eligible administrator can submit files again through the same entry point.
Source: choice: pausing imports must be reversible

### C-36: An import is all-or-nothing
Observable: An import creates every listed user or zero users. If any record is invalid or conflicts, or the directory cannot complete the entire creation, no user from the attempt becomes visible, even temporarily.
Source: choice: an administrator can correct and resubmit a whole file without tracking partial creation

### C-37: An accepted attempt is identifiable before its upload can create users
Observable: The administrator can identify the attempt before submitting its file. The identifier can be used from the same authorized account to recover the result after losing the submission response.
Source: choice: identification before creation resolves uncertainty when the response disappears

### C-38: An administrator can recover an attempt through the import area
Observable: On returning to import in the same directory, an authorized owner can find all their unexpired ready, processing, and completed attempts by identifier and issuance time, with each state visible, without their original file or response.
Source: choice: practical recovery must work when the browser or connection that submitted the file is gone

### C-39: An attempt has one observable state at a time
Observable: An unexpired attempt is ready until a complete file is accepted or a submission is rejected for size, processing after acceptance of a complete file until it completes, succeeded after all users are created, rejected after an input, conflict, or creation-authorization refusal, or failed after an accepted upload ends with zero users created due to an operational cause. An oversized file can go directly from ready to rejected. Refusing the request before admission for authentication, access, file selection, or a pause leaves an otherwise valid ready attempt ready. No other in-product attempt states are required.
Source: choice: these states distinguish waiting for a file, active creation, and the three outcomes that call for different next actions

### C-40: An incomplete upload cannot create users
Observable: Interrupting a transfer before the complete file is received creates zero users from the incomplete file.
Source: implied: U-9 requires the entire CSV to be received before it can be used

### C-41: No import creates a user before the administrator submits its file
Observable: Opening import, reviewing instructions, or selecting a file leaves the directory unchanged until an explicit submission is accepted.
Source: choice: selecting a file alone should not change user accounts

### C-42: A single attempt accepts at most one effective submission
Observable: After the attempt accepts a complete file or rejects a submission as oversized, any repeat submission for that attempt returns the current processing state or original outcome. Even different file contents cannot replace the first effective submission.
Source: choice: repeat submissions for one attempt must be safe after a lost response or double click

### C-43: A ready attempt expires 24 hours after it is issued
Observable: A ready attempt can accept a submission before 24 hours have elapsed since issuance, subject to admission and authorization, unless rollback has invalidated it. At or after that boundary the ready attempt is unavailable. An attempt that leaves ready before the boundary follows the processing and result windows instead.
Source: choice: an unused attempt should not remain usable indefinitely

### C-44: An administrator can retrieve a completed result for 24 hours
Observable: For 24 hours from transition to succeeded, rejected, or failed, the result is available to its submitting administrator while authorized in the target directory and the import interface is reachable. A pause in admission alone does not interrupt that window.
Source: choice: a fixed recovery window covers ordinary interruptions without requiring permanent import history

### C-45: An expired attempt identifier cannot be used for creation
Observable: At or after the ready expiration or completion retention boundary, an authorized owner using the expired identifier gets an unavailable attempt response and creates zero additional users.
Source: choice: a stale request must not resume or replay a past import

### C-46: A completed result is stable while it is available
Observable: Reading or resubmitting a succeeded, rejected, or failed attempt returns its original result, even after an imported user is edited or deleted or a conflict is removed.
Source: choice: the result describes what that attempt did at the time

### C-47: A corrected file is submitted as a new attempt
Observable: After a refusal, an administrator can open a new attempt to submit a corrected file. Resubmission of the rejected attempt returns its existing refusal.
Source: choice: corrected input needs an independent outcome without weakening replay protection

### C-48: An operational failure can be retried through a new attempt
Observable: After a failed outcome is confirmed, the administrator can submit the same file as a new attempt. The new attempt uses current directory data, permissions, and limits.
Source: choice: known failure is safe to retry without resetting the original attempt

### C-49: An attempt has a 120-second processing deadline
Observable: If the attempt is still processing at 120 seconds after complete file acceptance, it ends as failed for the deadline with zero users created. Recovery of a dependency at or after that boundary cannot complete creation for that attempt.
Source: choice: an administrator needs a bounded processing outcome before deciding when to retry

### C-50: An interrupted connection does not cancel an accepted attempt
Observable: If the administrator closes the page or loses the connection after file acceptance, processing can reach its ordinary outcome. Returning while it is processing shows that work is in progress if the import service is reachable.
Source: choice: creation should not depend on the client remaining connected

### C-51: A lost response is distinct from a confirmed failure
Observable: After the client loses contact without a terminal result, it cannot show that zero users were created. Once the service is reachable, reading that attempt within the recovery window returns its actual state or outcome.
Source: choice: reporting a false retry signal could cause confusion or duplicate work

### C-52: Concurrent writes preserve the target directory's ordinary identity uniqueness
Observable: When multiple imports or an import and ordinary creation or editing contend for the same identity, the directory has at most one registration reserving it. An import denied by the conflict reports a conflict and creates zero users.
Source: choice: the conflict rule must apply at creation, including to changes made after the file was submitted

### C-53: Existing identity conflicts follow effective directory write order
Observable: An identity freed before the import's conflict decision is eligible under the ordinary reservation rule. An identity reserved before import creates its users can still cause refusal. A later change cannot reopen a terminal conflict.
Source: choice: directory changes must affect unresolved work without reopening an already reported result

### C-54: An import keeps its original destination
Observable: The target is the directory in which the attempt was issued. Switching the active directory or changing anything in the file cannot redirect the attempt, even if its original destination is later unavailable.
Source: choice: directory navigation must not move account creation across an authority boundary

### C-55: Import creation requires current authorization when accounts would become visible
Observable: If the submitting account is no longer an administrator with creation authority in the target directory at the point where creation would take effect, the attempt is rejected for authorization with zero users created. A later grant cannot resume that refusal.
Source: choice: prior submission cannot authorize a write after access is revoked

### C-56: Disabling admission allows already accepted attempts to finish
Observable: When admission is paused after a complete file was accepted, that processing attempt can reach its usual outcome. While paused, a transfer begun earlier cannot move a ready attempt forward, even if enough bytes have arrived for acceptance or a size refusal.
Source: choice: a pause has an observable boundary and does not imply cancellation

### C-57: Administrators cannot cancel an accepted attempt
Observable: An accepted attempt offers no cancellation control. Administrators can recover its state or outcome while it remains available.
Source: choice: a bounded attempt has a simpler recovery contract without promising undo during creation

### C-58: The upload is available in the browser-based user administration area
Observable: An administrator can select and submit a CSV in a browser supported by the product's user administration area.
Source: choice: use the normal browser-based administration surface as the delivery context because no other interface was supplied

### C-59: Local file selection is mediated by the browser
Observable: The administrator chooses the file through the browser's file upload control. Dismissing the picker creates no new selection. Typing a local path into the page cannot give the import access to a file.
Source: implied: the [HTML Standard File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file)) only exposes selected files and does not accept a nonempty path set by page script

### C-60: One attempt accepts exactly one file
Observable: The browser offers up to one selected file per submission. A submission with no selected file or with more than one file receives a file-selection reason and creates zero users.
Source: choice: one file corresponds to one attempt and one outcome

### C-61: The production administration interface uses HTTPS for import data
Observable: The production interface sends uploaded CSV bytes over HTTPS. Import results are returned only over HTTPS.
Source: choice: uploaded account data and results need the protection of the production admin connection

### C-62: An enabled deployment admits valid files through the full 1,048,576-byte allowance
Observable: A valid file within the product byte allowance reaches import despite the request bytes surrounding the file. The production ingress platform and its body and header caps are unconfirmed, as is the numerical overhead allowance. A deployment whose ingress cannot admit a valid file at the bound cannot enable the feature.
Source: choice: the published file size must describe what actually reaches import even when the ingress limit counts other request bytes

### C-63: An interrupted upload can recover regardless of the host's request timeout
Observable: If the host ends a request before file acceptance, the directory receives zero users from that request. If the host ends the request after acceptance, the administrator can recover the attempt under the existing processing and retention rules. The host's upload time limit, synchronous response deadline, and execution limit are unconfirmed.
Source: choice: host deadlines must preserve recoverability without replacing the product's 120-second processing deadline

### C-64: A deployment enables import only when its directory supports the import contract
Observable: Until the target directory can accept email-based creation with ordinary default account settings, keep identity uniqueness across writers, and expose all-or-nothing creation with a recoverable outcome, the operator keeps import unavailable. The directory provider and any provider batch size, write quota, or account-capacity figure are unconfirmed.
Source: choice: an enabled feature must be able to keep the creation and recovery promises

### C-65: Production import availability depends on the deployment's release requirements
Observable: The operator can enable import in production only after the environment permits use of authenticated user administration and writes to the production directory. No host-specific release approval, service prerequisite, or quota is confirmed.
Source: choice: the workspace does not establish a production host or its release rules

### C-66: An imported user appears through ordinary directory reads after creation
Observable: After an import succeeds, an administrator with ordinary read access can find the created users using the directory's existing listing and search behavior, where available. Normal visibility, filters, and scope rules apply.
Source: implied: U-16

### C-67: An imported user can be managed through ordinary user operations
Observable: An administrator can view details, edit, change status, or delete an imported user under the same conditions as an individually created user wherever the operation exists. The full set of existing operations is left to the host because no administration feature inventory is supplied.
Source: implied: U-16

### C-68: Ordinary single-user creation remains available independently of import availability
Observable: An authorized administrator can use the ordinary single-user creation path where it already exists under its existing conditions, whether import is enabled, paused, or absent after rollback.
Source: implied: the request adds bulk creation to existing user administration

### C-69: An import never modifies an existing user
Observable: When a submitted email matches an existing identity, the import leaves that user's attributes, roles, credentials, and account state as they were. An import also leaves users whose identities are absent from the file alone.
Source: implied: U-3 and U-7 involve creation only

### C-70: An imported user receives the ordinary default account fields
Observable: The imported email is the only account field provided by the CSV. Every other field required for a new user takes the ordinary value for creation without administrator overrides. The complete field list is host-specific and unconfirmed because no user schema is supplied.
Source: choice: existing ordinary defaults determine account data beyond the upload's single input field

### C-71: An import grants only ordinary standard-user permissions
Observable: The created user has the permissions of an ordinary newly provisioned standard user in the target directory. CSV input cannot grant administrative permission or extra group membership.
Source: choice: provisioning a bulk list should not introduce privilege assignment

### C-72: An imported user follows the ordinary account activation policy
Observable: Starting from the ordinary initial state for a newly provisioned standard user, the imported user can sign in only after the same applicable activation and credential requirements as that user. Existing activation states and sign-in prerequisites are host-specific and unconfirmed.
Source: choice: account creation should not invent a separate sign-in or credential lifecycle

### C-73: An import triggers ordinary provisioning notices only for committed users
Observable: If ordinary standard-user provisioning sends an invitation or activation notice, a committed imported user is eligible for the same notice. A rejected or failed attempt sends zero notices from the account creation. No import-specific outbound notice is required.
Source: choice: a notice should describe an account that exists and follow the host's ordinary provisioning policy

### C-74: A provisioning notice failure does not reverse a successful creation
Observable: In a directory that sends provisioning notices, a failure to deliver one leaves the imported account created. The ordinary notice recovery behavior applies where available.
Source: choice: import success measures durable account creation rather than delivery by another service

### C-75: Attempt recovery requires ownership of the attempt
Observable: A different account, including another administrator of the same directory, cannot list, retrieve, or resubmit an attempt it did not start. A foreign attempt identifier gives the same unavailable response as an unknown identifier.
Source: choice: bulk results can disclose provisioning activity and are scoped to the submitter

### C-76: Attempt recovery requires current authorized administrator access
Observable: The submitting account can list, retrieve, or resubmit its attempt only while signed in as an administrator with creation authority in the original directory. Regaining access permits recovery again if the recovery window remains open.
Source: choice: earlier access must not let a former administrator access results

### C-77: The import does not expose uploaded contents through its results
Observable: The result provides an attempt identifier, issuance time, state, created-user count if terminal, and any applicable reason and row position. It does not return the raw file, filename, submitted email values, or existing user details.
Source: choice: statuses and locations are sufficient to repair a file without turning results into a copy of user data

### C-78: Import content cannot execute in administration screens
Observable: An administrator viewing the upload or its results cannot trigger script execution or navigation via a filename or cell value. Such inputs are handled as data.
Source: choice: a selected file must have no ability to control the administration session

### C-79: An unrelated site cannot start an import using the administrator's session
Observable: With an administrator signed in, a submission initiated by an unrelated site under that session is refused before account creation.
Source: choice: possession of a browser session alone must not permit another site to make user changes

### C-80: Operators can check whether import admission is enabled
Observable: An authorized operator can observe whether the feature is admitting new attempts or paused.
Source: choice: an operator needs to confirm the availability change before responding to an incident

### C-81: Operators can see how many accepted attempts are still processing
Observable: An authorized operator can observe the current number of processing attempts, including during an admission pause.
Source: choice: the operator must know when in-flight creation has settled

### C-82: Operator import status does not disclose uploaded user data
Observable: The import status used to operate the feature contains the admission state and active attempt count. It exposes no filenames, CSV contents, email values, or row diagnostics.
Source: choice: operating admission does not require being able to inspect lists of users

### C-83: Import availability controls require operator authority
Observable: An account without existing release or service operation authority cannot change the admission setting or view the operator status, even if it can create users.
Source: choice: creating accounts and shutting off their import are distinct authorities

### C-84: Pausing admission leaves authorized result recovery available
Observable: While import is paused, current authorized owners can continue to retrieve the state of previously submitted attempts within their recovery windows.
Source: choice: disabling new input should leave a way to settle outstanding outcomes

### C-85: A release rollback preserves committed users
Observable: After reverting to the previous feature version, committed imported users remain in the directory and continue through the ordinary account lifecycle. The previous version can omit import and its result interface.
Source: implied: U-10 must preserve data already created

### C-86: The operator drains accepted imports before release rollback
Observable: The operator pauses admission and waits until the processing count is zero before reverting to a version without the import.
Source: choice: rolling back after accepted work settles prevents unfinished work across cutover

### C-87: Retained outcomes can be recovered after restoration within the original recovery window
Observable: If a release rollback removes import access and the feature is restored before an outcome expires, its authorized owner can recover the original result until the original 24-hour boundary.
Source: choice: restoration should not replace the result or restart its retention clock

### C-88: An upload's contents determine CSV acceptance
Observable: A file whose bytes satisfy the input contract is eligible even when its name lacks a `.csv` suffix or its browser-reported media type differs from the usual CSV type.
Source: choice: browsers and spreadsheets can label the same bytes differently

### C-89: An oversized transfer can be refused before its remaining bytes are received
Observable: The import can report the file-size refusal once it has confirmed more than 1,048,576 file bytes. That refusal is terminal if made for an eligible ready attempt while admission is enabled.
Source: choice: receiving bytes beyond the allowed size has no value once the limit is exceeded

### C-90: File-level diagnostics distinguish the file errors an administrator can correct
Observable: When a file-level error is the reason reported, the administrator can distinguish invalid file selection, excessive file size, invalid UTF-8, malformed quoting, invalid header, no data records, and excess data records.
Source: choice: distinct diagnostics tell the administrator which part of the upload to correct

### C-91: Row diagnostics distinguish the row errors an administrator can correct
Observable: When a row error is the reason reported, the administrator can distinguish wrong field count, invalid email, duplicate identity within the file, and identity already reserved in the target directory.
Source: choice: administrators need different corrections for data shape, validity, and identity conflicts

### C-92: A rejection with multiple input errors reports at least one applicable error
Observable: If a submission violates multiple file or row rules, its rejection identifies at least one violation that applies to that submission. Which to show first and whether to show additional errors are left open so rejection does not require an exhaustive scan.
Source: choice: a single actionable correction is sufficient to explain refusal

### C-93: Operational failure diagnostics distinguish the applicable retry conditions
Observable: An authorized owner viewing a failed result can distinguish a missed processing deadline, an unavailable target directory, current authority that could not be verified, a directory write that could not complete for another operational reason such as capacity, or another import-service failure before creation. The result indicates that zero users were created.
Source: choice: restart decisions differ when a directory is missing, work timed out, or writes are unavailable

### C-94: A missing target prevents a successful import
Observable: If an accepted import's original directory has been removed or the attempt ends with the target inaccessible, the import fails for an unavailable target and creates zero users. If the 120-second deadline is reached while still processing, the deadline reason applies.
Source: choice: an operationally unavailable target is a failure distinct from a validation conflict

### C-95: A successful result is consistent with durable user creation
Observable: When the result first says succeeded, all users counted by that result have been durably created. If creation took effect before the deadline and the status response is interrupted, recovery returns success within the recovery window even when service returns after the processing deadline.
Source: choice: a status delay cannot turn a committed write into an apparent retryable failure

### C-96: Signing out after acceptance does not itself cancel an attempt
Observable: Signing out or letting a browser session expire after file acceptance does not affect processing if the account remains an administrator with creation authority in the target directory. Reading its result requires another authenticated session for that account.
Source: choice: account authority governs accepted work while an authenticated session governs access to the result

### C-97: Requests with no authorized directory cannot create an attempt
Observable: A caller who lacks the required administrator authority in a directory cannot open a ready attempt there, even by requesting it directly.
Source: choice: preparing an attempt is restricted to the same scope as using one

### C-98: An unavailable result does not imply zero users were created
Observable: If an authorized administrator looks for an expired or unknown attempt, the response communicates that the attempt cannot be retrieved without claiming its user count.
Source: choice: expired information cannot serve as evidence that no accounts were created

### C-99: The import retains upload content only for the attempt's work
Observable: Raw file bytes and filenames are absent from live import storage after the attempt reaches an outcome or a ready attempt expires. Normal platform backup retention is left to the host because its policy and duration are unconfirmed.
Source: choice: the recovery window needs outcome information without keeping a second live copy of the uploaded list

### C-100: Ordinary operational logs omit the uploaded user list
Observable: The import adds no raw CSV, filenames, or submitted email values to operator logs. Ordinary directory records and their existing audit behavior remain subject to the directory's access policy.
Source: choice: diagnosing an import should not create a new source of user-list exposure

### C-101: Repeat submission does not trigger a second provisioning notice
Observable: Resubmitting a succeeded attempt or a new file that is refused for an already reserved identity does not initiate a second invitation or activation from import for that user.
Source: choice: repeat requests should not repeat provisioning side effects

### C-102: Import admission is initially paused in a new deployment
Observable: Before an operator first enables import in a deployment, administrators see the unavailable outcome when trying to open an attempt.
Source: choice: newly deployed import should be enabled deliberately after its prerequisites are in place

### C-103: Admission is controlled for the deployment as a whole
Observable: Changing admission to enabled or paused applies to new import work in every directory served by the deployment.
Source: choice: an operator needs a single cutover boundary without having to configure each directory

### C-104: A rollback invalidates attempts that are still ready
Observable: An unsubmitted ready attempt issued before rollback cannot submit a file after import is restored. The administrator can open a new attempt when admission is enabled.
Source: choice: restoration should not allow a stale pre-release submission to take effect

### C-105: An unavailable processing count cannot be used to verify a drained release
Observable: If operator status cannot establish the current processing count, it indicates the count is unavailable rather than giving zero.
Source: choice: loss of status visibility is not evidence that a rollback can proceed

### C-106: Completion retention starts when the attempt takes effect or is definitively refused or failed
Observable: If the response is lost, the 24-hour recovery window still starts at the terminal outcome. For success it begins when the new users become visible as a committed creation. Late reads or resubmissions do not extend the window.
Source: choice: result recovery needs a single clock independent of client behavior

### C-107: A result lookup with an unavailable service communicates uncertainty
Observable: When the service cannot be reached or cannot establish an attempt's state, the administrator is told the result cannot currently be determined. The missing read is not treated as a failed creation or as an unknown identifier.
Source: choice: status outages should not encourage duplicate attempts or falsely imply expiration

### C-108: Imported users have the ordinary user-creation audit visibility
Observable: If the directory already exposes an audit record for creating a user, a committed imported user is visible through its ordinary user-creation audit activity under the same access rules. The host's audit fields and retention are unconfirmed.
Source: choice: existing account oversight should cover the bulk entry point without requiring a new audit format

### C-109: Import uses the ordinary account policy in effect at creation
Observable: If the directory changes its ordinary email eligibility or standard-user defaults while an attempt is processing, newly created users satisfy the policy in effect at the point creation takes effect. A file that has become invalid is rejected.
Source: choice: import cannot use an earlier policy to create users that ordinary creation would now refuse

### C-110: An import creates zero users if current authorization cannot be verified
Observable: If the permission service cannot establish current authorization when needed before creation, the import can continue processing while it can still meet the deadline. If it ends before the deadline without establishing authorization, it reports that current authority could not be verified, with zero users created. An attempt still processing at the deadline follows the deadline rule. A known lack of authority follows the authorization rejection rule.
Source: choice: an unavailable authority check must never be substituted for permission
