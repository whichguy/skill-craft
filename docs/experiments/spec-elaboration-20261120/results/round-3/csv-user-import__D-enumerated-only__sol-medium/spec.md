## Use cases

### U-1: An admin imports a roster for the first time to create multiple user accounts
Flow: The admin opens user management, finds the CSV import instructions, selects a CSV with an `email` header and two new addresses, then submits it. The result reports 2 users created. Both users appear through normal user lookup.
Source: request

### U-2: An admin imports a later roster to add users alongside existing accounts
Flow: The admin uploads a second CSV containing entirely new addresses. The result reports its own number created. The earlier accounts remain available.
Source: implied: by repeated use of bulk-create after users already exist

### U-3: An admin diagnoses an empty roster to prepare a usable CSV
Flow: The admin submits a zero-byte file or a CSV with only the `email` header. The result explains what is missing. The admin adds the required content and submits again.
Source: implied: by selecting a file with no user data to create

### U-4: An admin corrects malformed or invalid data to complete an import
Flow: The admin submits a file with invalid CSV structure or a row with an invalid address. The result identifies the applicable file or row problem. After correction, the admin submits a new attempt.
Source: implied: by uploading an arbitrary local file for account creation

### U-5: A caller is refused access when attempting an import outside their permissions
Flow: A signed-out caller or a signed-in non-admin attempts to open the import or submit directly. The product refuses access. An admin attempts to submit into a scope they do not administer and is also refused.
Source: implied: by the request limiting the feature to admins

### U-6: An admin submits a large roster to learn whether it fits
Flow: The admin submits a valid roster at the published ceiling and sees it processed. A submission exceeding a ceiling gets a limit error. The admin can reduce the file and try again.
Source: implied: by accepting bulk input of variable size

### U-7: An admin resolves duplicate identities to create only the intended new accounts
Flow: The admin submits a CSV with a repeated address or one matching an existing account. The result locates the conflict. The admin removes conflicting entries and submits the corrected roster.
Source: implied: by creating new users in a product that may already hold users

### U-8: An admin recovers from an interrupted import to learn which accounts were created
Flow: Connectivity drops after submission or the account service becomes unavailable. The admin checks the submission reference when service is available. If there was no acceptance, the admin can retry the original operation. If intake accepted the upload, the admin can use its final result to decide whether a new attempt is needed.
Source: implied: by an upload or account creation dependency failing during use

### U-9: Two authorized admins submit overlapping rosters to add new users safely
Flow: Both submit files that include the same address. At most one attempt creates that user. Each admin gets the outcome for their own attempt.
Source: implied: by more than one admin being able to import into the same user directory

### U-10: An operator opens or closes import intake to control rollout
Flow: The operator enables import for an intended scope, then disables it when intake must stop. An admin in that scope learns whether a submission can start.
Source: implied: by operating and stopping a newly shipped import feature

### U-11: An operator follows import health to recover service
Flow: The operator inspects attempt status and aggregate failure counts. After correcting a service problem, the operator reopens intake if it was closed. An admin can submit a fresh attempt.
Source: implied: by operating and recovering an account creation feature

### U-12: An operator returns to the preceding application version to restore service
Flow: The operator closes intake, allows accepted work to reach final outcomes, then restores the preceding version. Users already created through CSV remain usable through ordinary user management.
Source: implied: by rolling back the feature after it has been used

### U-13: An admin checks a completed attempt to reconcile an earlier submission
Flow: The admin reopens their recent attempts and checks the result for the intended CSV. An expired result is unavailable. The admin can use ordinary user lookup to check an account.
Source: implied: by needing to distinguish an earlier result from a new attempt after leaving the import screen

### U-14: An admin retries after losing the submission response to recover the original outcome
Flow: The admin loses the response for a submitted CSV, resubmits that same operation, then sees whether it was accepted or already finished. Replaying it cannot create a second roster.
Source: implied: by the upload response arriving late or being lost after acceptance

### U-15: A user authorized to manage directory roles revokes an admin's access to stop account creation
Flow: The admin begins an import. The role manager revokes the authority before creation takes effect. The submitter lacks that authority when the import reaches creation. The attempt produces no users. The former admin loses access to import results for that directory.
Source: implied: by admin authority changing during the action limited to admins

### U-16: An admin imports into a selected directory to avoid crossing account boundaries
Flow: An admin who manages directories A and B selects A before submitting. Created users belong to A. If the product reserves identities globally and an address in the file is already reserved outside the admin's visibility, the result shows a row policy refusal without revealing the other account.
Source: implied: by creating users within an existing scoped account system

## Clauses

### C-1: An admin can upload a CSV to bulk-create users.
Observable: An admin supplies one CSV describing two valid new users. One submission can create both accounts.
Source: request

### C-2: An admin can find the import through user management.
Observable: An authorized admin can reach the upload from the area used to manage users.
Source: choice: A discoverable entry point serves first-time admins without requiring a particular menu design.

### C-3: Import submission requires admin authority.
Observable: A signed-out caller or a signed-in caller without admin authority cannot submit an import, including by calling the submission entry point directly.
Source: implied: by the request reserving CSV bulk creation for admins

### C-4: A successful import produces ordinary user accounts.
Observable: The created identities are present as users wherever the product exposes equivalent users.
Source: implied: by the request to create users

### C-5: A later import can create new users in a directory containing existing users.
Observable: After a successful import of A and B, a submission containing only eligible new user C can create C.
Source: implied: by U-2

### C-6: A file with no data rows is refused.
Observable: A zero-byte file or a file containing only records skipped under C-28 receives a missing-header diagnostic. A valid header followed by no data records receives a no-data diagnostic. Each result reports 0 created.
Source: choice: Treat an empty roster as a correctable mistake.

### C-7: An invalid import produces a diagnostic.
Observable: The submitting admin receives a reason identifying the file problem or the offending data row.
Source: choice: Give the admin enough information to correct the submission.

### C-8: The import refuses an attempt whose original file exceeds 5,242,880 bytes.
Observable: A file of 5,242,881 bytes is refused with a file-size reason. A file of 5,242,880 bytes passes this size check. The count includes every byte of the supplied file, including any byte-order mark and line endings, and excludes upload transport overhead.
Source: choice: Bound resource use with room for rosters below the row ceiling.

### C-9: The import refuses an attempt whose file contains more than 10,000 data records.
Observable: Count every nonblank logical record after the header, including wrong-width records and records spanning multiple physical lines. 10,001 countable records exceed the limit. 10,000 pass the count check.
Source: choice: Support substantial rosters while keeping whole-file outcomes practical.

### C-10: An existing account is ineligible for import creation under the same product identity.
Observable: Submitting an address already reserved by a viewable account in the target directory produces an existing-user conflict for that row. C-100 governs conflicts outside the caller’s visibility.
Source: choice: Preserve create-only semantics while respecting the directory's identity rules.

### C-11: A duplicate address inside a file causes a conflict.
Observable: If two valid email rows resolve to the same identity, the result identifies the duplicate rows.
Source: choice: Let the admin resolve ambiguous input.

### C-12: Each attempt creates its entire roster or creates zero users.
Observable: A roster of 3 eligible rows creates 3 users on success. If the attempt ends in rejection or failure, it creates 0 users.
Source: choice: Make correction and resubmission predictable without requiring admins to reconstruct partial results.

### C-13: The result reports the number of accounts created by the attempt.
Observable: A successful two-row import reports 2 users created. An unsuccessful attempt with a final result reports 0.
Source: choice: Give the admin a concise reconciliation outcome.

### C-14: Authorized operators can disable new import intake per user directory.
Observable: With intake disabled in a directory, an otherwise authorized admin receives an unavailable response to a new submission.
Source: choice: Give operators a bounded way to stop incoming work.

### C-15: Authorized operators can enable new import intake per user directory.
Observable: Once the operator enables intake in a directory, an otherwise eligible submission can be accepted.
Source: choice: Provide a controlled start and restart.

### C-16: Accepted attempts have a recoverable result.
Observable: After leaving or losing the connection, the submitting admin can return to their recent attempts to see the current or final outcome.
Source: choice: Allow the admin to resolve an uncertain outcome before retrying.

### C-17: Overlapping submissions cannot both create the same identity.
Observable: When two imports into the same directory include the same eligible new identity, at most one creates it.
Source: choice: Protect uniqueness under concurrent use.

### C-18: Completed imports survive an application rollback.
Observable: After a successful import, the preceding application version can still find and manage those users.
Source: choice: Let operators restore the preceding version without undoing valid account creation.

### C-19: The import acts on exactly one user directory per submission.
Observable: In a scoped product, the admin submits into the directory selected through user management. In a product with one shared directory, that directory is the sole destination.
Source: choice: Use the product's existing account boundary as the destination.

### C-20: The caller must administer the destination directory to submit an import.
Observable: An admin of directory A cannot submit into directory B without admin authority in B.
Source: implied: by U-5 applying the request's admin requirement to the destination

### C-21: Only a signed-in admin of the destination directory can open its import interface.
Observable: A signed-out visitor, an ordinary user, or an admin of a different directory cannot open the destination's import interface, including through a direct link.
Source: choice: Apply the submission authority boundary to the import surface.

### C-22: The import presents its input requirements before submission.
Observable: Before selecting a file, the admin can find the required `email` column, the use of UTF-8 and comma separation, the 5,242,880-byte maximum, the 10,000-data-record maximum, and the all-or-zero creation policy.
Source: choice: Make costly corrections avoidable without prescribing instructional wording.

### C-23: Each submission takes one CSV file.
Observable: The admin can submit one file. A submission with zero files or multiple files is refused for file count.
Source: choice: Give every attempt a single roster and a single source of row positions.

### C-24: Eligibility by file type depends on the file's CSV content.
Observable: Valid roster bytes pass the type check with an arbitrary filename or browser media-type label. A misleading filename or media-type label cannot make invalid roster bytes eligible.
Source: choice: Treat filenames and media-type labels as unreliable hints.

### C-25: The file must decode as UTF-8.
Observable: UTF-8 with or without one leading byte-order mark is accepted at decoding. The leading mark is ignored for parsing. A file with invalid UTF-8 gets an encoding diagnostic.
Source: choice: Support portable text exports with one explicit encoding.

### C-26: The import reads comma-separated records with CSV quoting.
Observable: Unquoted fields cannot contain commas, double quotes, CR, or LF. A double quote at the start of a field opens a quoted field. Inside it, commas and line breaks are literal, two consecutive double quotes represent one literal double quote, and a closing double quote must be followed by a comma, record end, or end of file. An unclosed field, stray double quote, or extra character after a closing quote is a CSV syntax error.
Source: choice: Accept ordinary spreadsheet quoting without guessing alternative CSV dialects.

### C-27: Records may end with LF or CRLF outside quotes.
Observable: LF and CRLF can delimit records in the same file. A final record can end at end of file. An unquoted lone CR is a CSV syntax error.
Source: choice: Accept common line endings with a clear rule for lone CR characters.

### C-28: Blank records are ignored.
Observable: An unquoted record with no characters or only ASCII spaces or tabs is skipped before header selection and data counting. A quoted empty value or a line containing a comma is a record subject to validation.
Source: choice: Allow incidental blank lines without silently dropping explicit field values.

### C-29: The first nonblank record must consist of the single decoded field `email`.
Observable: `email` and `"email"` are valid headers. `Email`, ` email`, `address`, `email,email`, and `email,role` cause a header diagnostic.
Source: choice: A single documented header identifies the input and excludes fields with no established contract.

### C-30: Each nonblank data record must have exactly one field.
Observable: A row with an extra comma outside quotes has the wrong field count even if the extra field is empty.
Source: choice: Detect shifted or unintended values without inferring their meaning.

### C-31: A data field's surrounding ASCII spaces and tabs are ignored.
Observable: `  a@example.com  ` is interpreted as `a@example.com`, including when the spaces are inside a quoted field.
Source: choice: Accommodate incidental whitespace in common roster exports.

### C-32: An empty email field is refused.
Observable: A quoted empty field or a quoted field containing only ASCII spaces or tabs receives a missing-email diagnostic.
Source: choice: A data record must supply the account identifier.

### C-33: Imported addresses must satisfy the ordinary email-based creation policy.
Observable: Where the product has an email-based creation policy, the same trimmed address passes or fails email validation in both paths, including any local address restrictions.
Source: choice: Keep CSV from becoming a second policy for which email values are eligible.

### C-34: The fallback email policy accepts bounded ASCII mailbox addresses.
Observable: In the absence of an existing email policy, an accepted value has exactly one @ and at most 254 ASCII characters. The local part has 1 to 64 characters and contains only ASCII letters, digits, dots, or the characters listed here. `` ! # $ % & ' * + - / = ? ^ _ ` { | } ~ ``. A dot cannot be first, last, or adjacent to another dot. The domain has at least two dot-separated labels of 1 to 63 characters, each containing only ASCII letters, digits, or hyphens, with a letter or digit at both ends. The check uses syntax alone.
Source: choice: Give a product with no prior email policy a deterministic baseline without introducing a mail-delivery prerequisite.

### C-35: Duplicate detection uses the ordinary account identity equivalence rule where one exists.
Observable: Two trimmed addresses that ordinary account management treats as the same identity conflict in CSV, both within one file and against an existing identity.
Source: choice: Keep uniqueness consistent across creation paths.

### C-36: The fallback identity comparison folds ASCII letter case across the address.
Observable: Without an existing account identity rule, `Ada@Example.com` and `ada@example.com` denote one identity. `ada+tag@example.com`, `a.da@example.com`, and `ada@example.com` denote three distinct identities.
Source: choice: Provide predictable comparison without guessing provider-specific alias rules.

### C-37: A CSV-created account gets the ordinary creation defaults for its email.
Observable: For the same directory and address, an imported user has the ordinary creation path's default profile values, access level, and initial account state. System-assigned identifiers and timestamps are generated for the actual creation. Particular field names and default values are left to the established creation policy because the host user model is unconfirmed.
Source: choice: Reuse product defaults without adding CSV columns for profile, roles, account status, or credentials.

### C-38: An imported account receives the ordinary onboarding treatment for an equivalent email-based creation.
Observable: Where ordinary creation sends an invitation, requires activation, or has neither behavior, the imported account follows the same onboarding policy. A product without an existing onboarding path gains no new notification or credential-delivery feature from CSV.
Source: choice: Create ordinary accounts without adding a separate onboarding system.

### C-39: A row diagnostic identifies the record's starting physical line.
Observable: The first physical line is line 1. If an invalid record starts on line 4 and spans lines 4 and 5, its position is reported as line 4. Each LF or CRLF advances the line number once even inside quotes or in a skipped record. An isolated CR inside quotes is data and does not advance the line number.
Source: choice: Give an admin a location they can find even when CSV quoting spans multiple lines.

### C-40: A syntax diagnostic locates the malformed record when its starting line is known.
Observable: An unterminated quote starting in a record on line 3 produces a CSV syntax reason locating line 3. An encoding error can be reported at file level.
Source: choice: Locate correctable CSV syntax without requiring row recovery from invalid bytes.

### C-41: Row diagnostics cover the independently established causes of row rejection.
Observable: On a structurally parseable file within both limits and with a valid header, each rejected row has its starting line and each applicable reason. Reasons are wrong field count, missing email, invalid email, duplicate within file, existing identity subject to C-100, or refusal under the ordinary account creation policy. Email syntax is checked on each one-field row with a nonempty value. Identity and email-dependent creation-policy checks apply only if that value is a valid email. If service failure leaves checks incomplete, the result identifies that the diagnostic set may be incomplete.
Source: choice: Support correction in one pass while avoiding inferred errors for data that could not be checked.

### C-42: An attempt becomes accepted only after intake admits a complete upload.
Observable: An interrupted transfer, a submission that fails authorization or intake admission, a submission with the wrong file count, one without an admissible reference, or one over the byte limit creates no accepted attempt. A fully received upload admitted by these checks can appear as an accepted attempt before its roster is validated.
Source: choice: Give admins a clear boundary between transferring a file and asking the product to create accounts.

### C-43: An accepted attempt has exactly one current status.
Observable: Its status is processing while the outcome is pending, succeeded when all users were created, rejected when the input or a creation rule prevents creation, or failed when a service fault or processing deadline prevents creation. The display wording can vary.
Source: choice: Distinguish what the admin must fix from what the service must recover.

### C-44: Accepted processing continues independently of the originating connection.
Observable: Navigating away or losing the upload response after acceptance does not itself cancel the attempt. The admin can later check its status.
Source: choice: Let admins recover after disconnecting at an uncertain point.

### C-45: A final attempt result never changes.
Observable: Reopening a succeeded, rejected, or failed attempt yields its original disposition and created count even if accounts or directory policy change later.
Source: choice: Keep the recorded result usable for reconciliation.

### C-46: The admin can identify the operation before the file transfer begins.
Observable: The upload has a reference available before transfer. An interrupted submission can be checked or replayed using that reference.
Source: choice: Make an accepted submission recoverable when its first response never reaches the admin.

### C-47: A submission reference is valid only for its issuing admin and destination directory.
Observable: Reusing a reference with another admin identity or another directory is refused without disclosing whether an attempt exists for it.
Source: choice: Prevent cross-account or cross-directory lookup and replay.

### C-48: Replaying an accepted submission with the same reference and file returns the original attempt.
Observable: Sending the same file bytes with the same reference again, serially or concurrently, leads to one accepted attempt and returns its current or final status. Filename or media-type changes alone do not create a new attempt.
Source: choice: Make retry safe after uncertain network outcomes.

### C-49: An accepted reference cannot be repurposed for different file bytes.
Observable: Submitting changed file bytes under an accepted reference is refused as a reference conflict. The original attempt can still be checked or replayed.
Source: choice: Separate a correction from redelivery of the same operation.

### C-50: An unused submission reference expires after 24 hours.
Observable: A reference that has never been accepted is eligible to reach acceptance for less than 24 hours from issuance. At the 24-hour boundary, the admin needs a fresh reference.
Source: choice: Bound inactive submissions while allowing an interrupted upload to be retried.

### C-51: A new reference starts a separate submission.
Observable: The admin can submit a corrected or replacement file with a fresh reference. A fresh reference carrying an already successfully imported roster is checked against current account state. An address still reserved by a viewable account generates an existing-user conflict.
Source: choice: Distinguish a deliberately repeated submission from a replay of an earlier operation.

### C-52: A finished result is available for 30 days.
Observable: Its submitting admin can retrieve it for less than 30 days after the final outcome, subject to current authority. At 30 days it no longer appears in history and its reference cannot start a new attempt.
Source: choice: Give admins time to reconcile recent imports without permanent import history.

### C-53: History is restricted to the submitting admin with current directory admin authority.
Observable: A different admin, a signed-out caller, a non-admin, or a former admin cannot view the submitter's attempts or diagnostics, including through direct reference lookup. If the submitter regains authority before expiration, their retained results are accessible again.
Source: choice: Limit access to roster-derived information.

### C-54: Admin history identifies accepted imports within the selected directory.
Observable: The submitter can distinguish accepted attempts by reference, acceptance time, status, and created count once final. Rejected attempts expose their applicable file, row, or attempt-level reasons. Failed attempts identify a service failure or a processing timeout and expose any available input diagnostics. The original file is not available for download.
Source: choice: Make attempts distinguishable without keeping a downloadable roster.

### C-55: Closing intake does not cancel already accepted work.
Observable: A transfer that reaches admission while intake is closed is refused. An attempt accepted before closure continues under the normal processing rules.
Source: choice: Let operators close the door to new work while accepted work drains to a known outcome.

### C-56: Intake closure preserves authorized access to accepted results.
Observable: The submitter can look up or safely replay an accepted reference while intake is disabled. Replaying a reference that was never accepted is subject to the intake gate.
Source: choice: Allow outcome recovery during a service pause.

### C-57: Creation requires the submitter to be authorized when the roster takes effect.
Observable: If directory admin authority is absent at the moment creation would take effect, the attempt is rejected with 0 users created. Revocation after creation takes effect does not undo created users.
Source: choice: Apply current authority at the account-changing event.

### C-58: Accepted work cannot create users in a directory that ceases to exist.
Observable: If the destination is removed before creation takes effect, the attempt creates 0 users and reaches a rejected outcome. It cannot be redirected into a replacement directory.
Source: choice: Keep a queued roster bound to its original destination.

### C-59: Concurrent account creation through other entry points respects the same identity reservation.
Observable: If ordinary creation and an import compete for the same identity in the same directory, at most one creates it. If the ordinary creation wins, the import creates 0 users and identifies the conflict subject to C-100.
Source: choice: Protect account uniqueness across creation paths.

### C-60: Account rules at the time of creation can prevent an import from taking effect.
Observable: A change to directory account creation rules or identity reservations after initial validation can still cause the attempt to be rejected with 0 created if the final creation would violate the current rules.
Source: choice: Prevent a stale eligibility check from overriding the rules in force when users would be added.

### C-61: Success is reported only once all accounts are durable.
Observable: A success result remains accurate after a service restart. Durable roster creation establishes the success outcome even if the status service is unavailable at that instant. If service interruption precedes durable creation, recovery either completes the whole roster under the same attempt or finalizes it with 0 created.
Source: choice: Keep the reported outcome aligned with actual account creation.

### C-62: The processing deadline is 15 minutes from acceptance.
Observable: At the 15-minute boundary, an attempt still processing reaches a failed outcome with a timeout reason and 0 created. It cannot create users later. An outcome fixed before the boundary remains final even if the status service was temporarily unavailable.
Source: choice: Give every accepted operation a finite resolution point.

### C-63: Accepted attempts have no per-attempt cancellation control.
Observable: An admin checking a processing attempt is offered no action to cancel that attempt.
Source: choice: Keep each accepted attempt governed by the same outcome rules.

### C-64: Onboarding starts only for successfully created accounts.
Observable: When the ordinary path sends invitations or starts activation, a rejected or failed attempt never initiates either for its rows.
Source: choice: Avoid sending account communications for users the import did not create.

### C-65: Onboarding delivery failure does not reverse successful account creation.
Observable: If a created account's invitation fails to deliver, its import result still reports that account created. Any delivery status and remedial action follow the ordinary onboarding path.
Source: choice: Keep the created count tied to account existence while using existing onboarding remedies.

### C-66: A browser upload requires the admin to supply the local file.
Observable: A browser page cannot select a file by restoring a saved local path. If the browser no longer has the file selection, replay that needs the file requires the admin to select it again.
Source: choice: Use the admin's web browser for interactive upload. The [HTML File Upload state](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file)) forbids setting the picker to a nonempty path.

### C-67: Production import traffic uses the secure admin origin.
Observable: In a production environment, an admin can select a CSV for upload and retrieve its result through the product's HTTPS admin experience. An insecure connection cannot submit a CSV or retrieve an import result.
Source: choice: Protect roster contents and session credentials in transit.

### C-68: Enabled deployments can transport a file at the advertised byte limit.
Observable: In an enabled deployment, a 5,242,880-byte file sent through the normal admin workflow can reach intake, including the upload request's overhead. The hosting platform and its total request-body cap are unconfirmed.
Source: choice: A gateway's request-body rule applies to the entire upload request, so the production path must support the published file ceiling.

### C-69: A request time limit cannot decide whether accepted work creates users.
Observable: If an upstream timeout interrupts an incomplete transfer, that transfer cannot create users. If the timeout only interrupts the reply after a complete transfer, the admin can check or replay the reference to resolve whether intake accepted it. The hosting platform and its request timeout are unconfirmed.
Source: choice: An upstream request-lifetime rule can close the connection before an acceptance response arrives.

### C-70: Production intake can open only where the accepted-work deadline is supported.
Observable: A deployment that cannot complete or durably resolve accepted work independently of the upload connection stays closed to production imports. The account service, execution runtime, and their operation and execution limits are unconfirmed.
Source: choice: Execution and account-service limits can outlast or terminate an individual invocation. Enabled production environments must support durable resolution within the 15-minute product deadline.

### C-71: The ordinary user creation entry point remains available independently of import intake.
Observable: An authorized caller can still create an eligible user through the established single-user workflow with import enabled, with import disabled, or after rolling back the feature.
Source: choice: Keep CSV intake controls from changing the existing creation workflow.

### C-72: The ordinary account modification policy applies to imported users.
Observable: Where ordinary users can be edited, deactivated, reactivated, or deleted, the same authorized actions are available for imported users under the same rules.
Source: choice: Keep account management independent of how a user was created.

### C-73: An import cannot modify an account it did not create.
Observable: An existing user's account values, access level, activation state, and credentials are unchanged by an import containing their address.
Source: implied: by the request to create users

### C-74: A pending import exposes no provisional user accounts.
Observable: Before durable creation of the roster, ordinary user lookup, sign-in, and account management cannot access provisional accounts from it.
Source: choice: Keep uncommitted work from becoming usable through other product surfaces.

### C-75: A CSV value cannot assign access privileges.
Observable: An added role column is refused as an invalid header. The import provides no CSV field whose value specifies a role, permission, or activation state.
Source: choice: Exclude privilege assignment from roster intake.

### C-76: Cross-site actions cannot use an admin's active session to operate the import without authorization.
Observable: An unrelated site cannot use a signed-in admin's session to start an import, change intake, or read attempt details.
Source: choice: Preserve the browser session's authority boundary for the new surfaces.

### C-77: Import feedback treats file-derived content as data.
Observable: If a selected filename or a malformed field contains markup or script syntax, it cannot execute in an import screen or change the actions taken there.
Source: choice: Allow safe handling of arbitrary filenames and CSV bytes.

### C-78: Import observability exposes only operational metadata to authorized operators.
Observable: For each accepted attempt, an operator for the destination can see its reference, destination, submitting admin's account identifier, acceptance time, final time when available, status, created count when final, and applicable failure categories from C-41 and C-84 or the categories authorization lost, destination removed, directory quota, service failure, and processing deadline. This access does not expose the file, filename, email values from rows, or row-level diagnostics.
Source: choice: Give operators enough information to locate failures, watch completion, and reconcile a report from an admin.

### C-79: Operators can observe pre-acceptance refusal categories without seeing submitted data.
Observable: Authorized operators can distinguish access refusal, intake disabled, destination unavailable, wrong file count, oversized upload, interrupted upload when detectable, expired or unusable reference, reference conflict, and service unavailability before acceptance. This visibility does not expose an uploaded roster or its email values.
Source: choice: Give operators evidence of traffic that never reached accepted-attempt history.

### C-80: Raw uploaded content is retained only for pending processing.
Observable: An authorized data-handling review finds no raw file or filename in terminal attempt history, operator records, or import logs. Raw contents required by a processing attempt are inaccessible to users and operators outside the upload itself and are discarded at finalization. Incomplete or refused transfers are discarded when the transfer is resolved.
Source: choice: Minimize retention of contact data while allowing accepted work to survive a disconnect.

### C-81: Import intake is closed until explicitly enabled in a directory.
Observable: Before an operator enables a new installation or directory, admins can discover the import's unavailable state, but new uploads cannot be accepted.
Source: choice: Make rollout deliberate in environments with different operational capabilities.

### C-82: Operator access is governed by the product's operational authority for the directory.
Observable: The operator controls for a directory are enabling intake, disabling intake, and viewing the operational information in C-78 and C-79. Only a caller authorized to operate that directory can use them. Directory admin status alone confers no added operator permission.
Source: choice: Keep operational control scoped and avoid creating a new privilege assignment workflow.

### C-83: The product's existing account access policy governs users after they are created.
Observable: An imported user has the same eligibility to sign in, activate, or access ordinary product features as a user created with equivalent values through the established path.
Source: choice: Preserve the product's established access rules for every user.

### C-84: File-level rejection identifies at least one established file-level cause.
Observable: The possible file-level input diagnostics for an accepted attempt are invalid UTF-8, malformed CSV quoting or line ending, missing header, invalid header, no data records after the header, and more than 10,000 data records. If independent file errors coexist, reporting one applicable cause is sufficient. Too many bytes is an intake refusal under C-8.
Source: choice: Tell the admin what prevents validation without promising recovery from malformed files.

### C-85: An unavailable status lookup does not report an attempt as failed.
Observable: When the service cannot establish the current result, the admin sees that the lookup is unavailable and can retry it. An authorized admin checking their own unexpired, unused reference sees that no upload has been accepted under it. An expired or unknown reference yields an unavailable-reference response. An attempt is shown as failed only after a final failed outcome is established.
Source: choice: Prevent a temporary lookup fault from prompting the admin to treat an accepted roster as unsuccessful.

### C-86: A canceled file selection submits no roster.
Observable: Closing the browser's file chooser without choosing a file does not submit a roster. A browser form's empty selection placeholder counts as zero selected files. Selecting a real zero-byte file counts as one selected file.
Source: choice: Distinguish the otherwise ambiguous empty states. The [HTML form entry-list rule](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#constructing-the-entry-list) can serialize an empty selection as an empty file entry.

### C-87: An import uses the ordinary account reservation policy for existing user states.
Observable: An address reserved for an active, invited, activation-pending, suspended, deactivated, or retained deleted user conflicts if ordinary creation treats that address as still reserved. A hard-deleted user's address is available if ordinary creation releases it. Product-specific state names and reusable-state exceptions are left to the ordinary creation policy because the host's states are unconfirmed. With no host reservation policy, every retained account reserves its email and a permanently removed account releases it.
Source: choice: Match existing decisions about identity reuse across account states.

### C-88: An import reports when ordinary creation needs input unavailable in the roster.
Observable: If a directory's ordinary creation policy requires information beyond the supplied email that cannot be supplied by ordinary defaults, the attempt reports a creation-policy refusal for the affected rows and creates 0 users.
Source: choice: Avoid guessing required user attributes or silently bypassing those requirements.

### C-89: Import respects existing directory-wide account quotas.
Observable: If concurrent ordinary creates or imports would exceed an existing directory limit, creations cannot collectively take the directory over that limit. An import that cannot fit reports a creation-policy refusal with the directory quota as its cause and creates 0 users. Host quotas and their figures are unconfirmed. There is no additional import-specific directory lifetime quota.
Source: choice: Apply the same capacity rules to imported users and ordinary users.

### C-90: Import diagnostics do not retain or disclose CSV field values.
Observable: An admin can diagnose a rejected row from its starting line and reason. Attempt results, operator views, and import logs omit email values copied from the input, raw content, filenames, credentials, and session secrets. Successfully created accounts still expose their ordinary fields under existing permissions.
Source: choice: Make diagnostics useful without creating an additional place to find personal data or secrets.

### C-91: Operator attempt metadata expires with the associated result.
Observable: Individual attempt metadata ceases to be available to operators 30 days after the final outcome.
Source: choice: Align individual operational history with the reconciliation window.

### C-92: Rollback begins only after intake is closed and accepted attempts are final.
Observable: Before restoring the previous version, the operator can observe intake closed and zero processing attempts across the affected directories.
Source: choice: Let each accepted operation reach a known outcome while its processing feature is available.

### C-93: Restoring the feature after rollback leaves intake closed until explicitly reopened.
Observable: After the import-capable version is restored, new submissions remain unavailable until an authorized operator enables intake again.
Source: choice: Prevent a recovery deployment from accepting new work before the operator is ready.

### C-94: A retained result remains recoverable when the import-capable version is restored.
Observable: An admin can recover their unexpired result on the restored import-capable version under the normal history rules. Viewing import history in the preceding version is deliberately excluded because that version predates the feature.
Source: choice: Preserve reconciliation when the import is temporarily removed.

### C-95: The import does not confirm acceptance when it cannot establish a recoverable attempt.
Observable: If the service knows intake failed, the submission reports a pre-acceptance failure and no users are created. If the caller cannot determine whether acceptance occurred, the operation can be checked or replayed under its original reference.
Source: choice: Avoid treating a lost reply or service interruption as proof of either acceptance or refusal.

### C-96: All occurrences of a repeated valid identity are marked as duplicates.
Observable: When the same valid identity appears on lines 2, 5, and 9, the within-file conflict identifies all three starting lines, even if that identity also conflicts with an existing account.
Source: choice: Make it possible to resolve a repeat without guessing which records collided.

### C-97: The admin can review which local file is selected before submitting it.
Observable: Selecting a file shows its filename in the current upload interface. The admin can replace or clear the selection before submission without creating an attempt.
Source: choice: Prevent accidental submission of the wrong roster without keeping filenames in attempt records.

### C-98: An accepted attempt does not need the original browser session to remain signed in.
Observable: If the submitter signs out or their session expires after acceptance, the attempt can still succeed if the submitter's account retains directory admin authority when creation takes effect.
Source: choice: Distinguish session lifetime from the account's ongoing authority over an accepted operation.

### C-99: CSV creation respects the ordinary identity scope across directories.
Observable: If ordinary creation reserves an address only within each directory, an address elsewhere does not cause a conflict in the selected directory. If ordinary creation reserves it globally, the import does not create a second user under that identity or attach the existing user to the selected directory.
Source: choice: Respect the product's ownership boundary without changing creation into a membership operation.

### C-100: A conflict with an account outside the caller's visibility is redacted.
Observable: An admin whose row conflicts with a reserved identity they cannot view receives a creation-policy reason for the row without confirmation that another account or directory exists. Operator categories for the attempt also use the redacted reason.
Source: choice: Keep the ordinary account visibility boundary intact in error messages.

### C-101: Operators can see aggregate counts for import outcomes in their operational scope.
Observable: An operator can see counts by the statuses in C-43 and the failure categories in C-78 and C-79. Processing counts describe work currently pending. Terminal and pre-acceptance counts cover the preceding 30 days by outcome time. Requests with no established directory are excluded from directory-level counts because they cannot safely be attributed to a directory.
Source: choice: Surface rollout problems without requiring operators to tally individual attempts.

### C-102: Replay does not repeat onboarding.
Observable: Replaying an accepted reference or recovering the same attempt after a service interruption does not initiate a second onboarding action for the same created user. Any delivery retry allowed by ordinary onboarding remains governed by that policy.
Source: choice: Recover the creation outcome without issuing duplicate onboarding requests.

### C-103: An expired unused reference cannot admit an in-flight upload.
Observable: If a transfer starts just before its unused reference reaches 24 hours and reaches intake after that point, it is refused as expired and creates 0 users. An incomplete upload under an unused reference can no longer proceed when that reference expires. Any earlier transport timeout is subject to C-69.
Source: choice: Keep incomplete intake bounded without choosing a second product deadline.

### C-104: With no prior creation path, an import creates a basic user record.
Observable: Each resulting record has a distinct system-assigned user identifier, the trimmed email address, and ordinary user access without an administrator role. Profile fields, passwords, and an onboarding status are deliberately unspecified because this feature supplies none of those values and no prior product contract requires them.
Source: choice: Define the minimum ordinary record when there is no existing user-creation contract.

### C-105: A roster may contain a single data record.
Observable: An otherwise eligible file with its header and exactly 1 valid new address creates 1 user.
Source: choice: Permit a small roster without making an admin switch workflows.
