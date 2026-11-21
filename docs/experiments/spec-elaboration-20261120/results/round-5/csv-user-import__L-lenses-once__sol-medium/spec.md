## Use cases

### U-1: An authorized admin imports users for the first time
Flow: Open the user-management area for the intended scope. Find the CSV import, read the accepted columns and limits, select one file containing one or more new users, then submit it. See the number created. Find those users through the ordinary user list or search. If the file is invalid, see what to correct and submit a corrected file.
Source: request

### U-2: An authorized admin corrects an empty, unreadable, or invalid upload
Flow: Attempt to submit with no selection, an unreadable selection, an empty file, a headers-only file, an invalid CSV, or a CSV with invalid user data. See why the attempt failed. Replace or correct the file and submit again.
Source: implied: uploading a CSV takes a readable selection with user records, and real input can fail

### U-3: An authorized admin imports a file at the supported limits
Flow: Check the published limits of 1,048,576 file bytes and 1,000 user records. Submit a valid file at either limit, including a file at both limits. A file one byte or one record over its respective limit is refused. Reduce the file to the limits and resubmit it.
Source: implied: bulk upload includes the largest supported input and the first input beyond it

### U-4: An authorized admin repeats an import against existing data
Flow: Upload another file after an earlier import or ordinary user creation. A file of entirely new users succeeds. A file containing a repeated identity or an identity already held in the destination fails. Use the reported rows to correct the file, then submit the intended new users.
Source: implied: bulk-create operates on an account store that may already contain users

### U-5: A person without creation authority tries to import users
Flow: As a signed-out visitor, ordinary user, or admin without creation authority in the selected scope, try to open or invoke the import. The person cannot import there. An authorized admin whose authorization or destination is lost during the attempt sees a refusal if the change takes effect before creation commits.
Source: implied: “Let admins” limits administrative access and applies to user creation

### U-6: Authorized admins encounter overlapping user-management actions
Flow: Submit overlapping imports, or submit an import while another authorized admin creates, changes, or removes a user with a competing identity. Check which operation took effect and which failed. Continue with work that is still valid against the current user store.
Source: implied: imports share user identities with concurrent imports and existing user-management actions

### U-7: An authorized admin recovers after a dependency or connection failure
Flow: Submit a valid file. If the service confirms failure, use the failure guidance and retry when the service is available. If the connection closes before a result arrives, use the ordinary user list or search to check the submitted identities before retrying. A retry cannot create a second account with the same identity.
Source: implied: delivery of the result and creation of the users can fail independently

### U-8: An operator releases, observes, or rolls back the import
Flow: Verify the target host's permissions, account rules, upload capacity, completion behavior, and production prerequisites. Make import available through an ordinary release. Observe import outcomes through the host's operational facilities. If the release is unhealthy, restore the prior version, verify that import is unavailable, and continue using ordinary user management with previously committed users.
Source: implied: the feature must be operable in the host application with existing users and deployment procedures

## Clauses

### C-1: An authorized admin can submit a CSV to bulk-create users.
Observable: From an authorized session, submit one valid CSV with two distinct new user records and find two newly created users.
Source: request

### C-2: The import is discoverable from the destination's user-management area.
Observable: An authorized admin starting at user management can reach the import for that destination.
Source: implied: U-1 requires admins to find the upload in the scope where they manage users

### C-3: The target scope is visible before submission.
Observable: Before submitting, the admin can tell the destination in which the accounts will be created, including when the application has only one destination.
Source: implied: U-1 requires the admin to know where creation will occur

### C-4: Every account created by an import belongs to its authorized destination scope.
Observable: Import into one destination and find the new accounts there. In a host with separate scopes, the upload does not create accounts in any other scope.
Source: implied: U-1 and U-5 require a CSV upload to respect the same destination boundary as ordinary creation

### C-5: An unauthenticated caller cannot submit an import.
Observable: Invoke submission without a valid session. No users are created.
Source: implied: “Let admins” and U-5 require an authenticated admin

### C-6: A signed-in non-admin cannot submit an import.
Observable: Invoke submission as a signed-in non-admin. No users are created.
Source: implied: “Let admins” and U-5 restrict the action to admins

### C-7: An admin needs ordinary user-creation authority in the destination.
Observable: An admin who lacks ordinary creation authority for the destination receives a refusal when invoking the import there directly.
Source: implied: U-5 requires destination-specific authorization even when the import interface is bypassed

### C-8: The import interface is available only to callers authorized to use it in the current destination.
Observable: A signed-out visitor, a non-admin, or an admin without creation authority in the current destination cannot open the import interface there.
Source: implied: U-5 requires the administrative entry point to respect its authorization boundary

### C-9: An authorization refusal exposes no destination account data.
Observable: An ineligible caller cannot learn from a refusal whether a submitted identity exists or which users were created by an authorized caller's upload.
Source: implied: U-5 requires permission checks to protect the information returned by the import

### C-10: The caller needs valid creation authority when the import takes effect.
Observable: Revoke creation permission, invalidate the session, or remove the caller's authority in the destination before creation commits. The attempt creates zero accounts.
Source: implied: U-5 requires permission changes to apply to uploads already underway

### C-11: The destination must permit ordinary user creation when the import takes effect.
Observable: If the destination has been deleted or put into any host state that blocks ordinary creation before the import commits, the attempt creates zero accounts. The names and membership of those host-specific states are unconfirmed because no host was identified.
Source: implied: U-5 requires changes to the destination to govern pending creation

### C-12: Selecting a file alone creates zero users.
Observable: Choose or replace a file, then leave the import before submitting. No corresponding user appears.
Source: implied: U-1 distinguishes selecting the file from authorizing its submission

### C-13: Each submission accepts exactly one file.
Observable: Submit zero files or attempt to submit more than one file in one operation. The attempt is refused as missing or having too many files, respectively.
Source: choice: a single file is the natural unit of the requested upload

### C-14: An unreadable or incomplete file transfer cannot create users.
Observable: Select an unreadable file or interrupt transfer before the full file arrives. No users are created from the missing bytes or the received prefix.
Source: implied: U-2 requires creation from the submitted CSV rather than from incomplete input

### C-15: The admin can learn the complete accepted column set before uploading.
Observable: Find the exact accepted header names, the column required for the account's primary identity, every other required input, and the rules for populated and blank values before picking a file.
Source: implied: U-1 requires the admin to prepare a file the product can interpret

### C-16: The accepted column set consists of the identity column plus any inputs the host requires the admin to supply for ordinary creation.
Observable: In an email-identified host where ordinary creation requires only email, the file needs one column for email. The only additional supported columns are fields the host requires the admin to supply, with the exception of credentials, privilege assignments, and scope selectors, which the CSV cannot supply. Beyond the identity, required field names, allowed values, and numeric bounds are unconfirmed because the host's ordinary creation contract was not provided.
Source: choice: support the minimum input needed to create ordinary users without expanding the CSV into a general administrative interface

### C-17: The import uses the host's existing primary identity for user creation.
Observable: Supply the identifier that ordinary creation uses to distinguish users, whether that is an email address or another identifier. The field's exact validation and length bounds are those of the host and are unconfirmed here.
Source: implied: U-1 and U-4 require CSV users to participate in the same user-identity model

### C-18: The import accepts UTF-8 CSV text.
Observable: Submit otherwise valid UTF-8 text containing accepted non-ASCII user data. The values reach ordinary validation intact.
Source: choice: one documented encoding makes international data portable

### C-19: A single UTF-8 byte-order mark at the start of the file is optional.
Observable: Import the same valid columns with or without the initial three bytes EF BB BF. The mark never becomes part of the first header.
Source: choice: common CSV producers may emit the mark

### C-20: Invalid UTF-8 is a file error.
Observable: Submit a file with an invalid UTF-8 sequence. See an encoding error instead of creation from substituted characters.
Source: choice: automatic replacement could change account identities or other values

### C-21: CSV records use a comma as the field separator.
Observable: An unquoted comma separates two fields. A file using tabs or semicolons in place of the required separators does not gain another interpretation.
Source: choice: a single published delimiter removes ambiguity about what CSV the upload accepts

### C-22: The import accepts LF and CRLF as record separators.
Observable: A file using either line ending outside quoted fields works, including when the final record has no line terminator. A bare CR outside a quoted field does not separate records.
Source: choice: accept common platform line endings without guessing record boundaries

### C-23: Double-quoted CSV fields follow a single quoting rule.
Observable: A field may be enclosed from its first to its last character in double quotes. Inside the enclosing quotes, a comma, LF, or CRLF is part of the value and two double quotes give one literal double quote. Ordinary field validation still applies to the decoded value.
Source: choice: support the escaping needed to carry CSV field values without losing content

### C-24: Malformed CSV quoting is a file error.
Observable: An unclosed quoted field, a bare double quote in an unquoted field, or any character between a closing quote and the next separator, record ending, or end of file is reported as malformed CSV.
Source: choice: refuse ambiguous quoting so the importer cannot misread record boundaries

### C-25: A physically empty line outside a quoted field is ignored.
Observable: Insert lines with zero characters before the header, between records, or after the last record. They count toward the byte limit and consume zero user records. A line containing spaces, separators, or quotes is a record.
Source: choice: tolerate empty lines without treating partially supplied user input as blank

### C-26: The first record contains the headers.
Observable: Submit the published headers as the first record after any ignored empty lines. The headers produce zero user accounts.
Source: choice: headers make the column mapping explicit

### C-27: Each required header appears exactly once.
Observable: Omit a required header or include it twice. The file is refused with the missing or repeated header identified.
Source: choice: each required input needs a unique mapping

### C-28: Unrecognized headers are refused.
Observable: Add a blank header, a misspelled header, or a column outside the published accepted set. The file is refused with the offending column identified.
Source: choice: ignoring columns could hide a typo or silently discard data the admin expected to use

### C-29: The header determines field mapping independently of column order.
Observable: Reorder valid headers and their matching values together. Each value still reaches the field named by its header.
Source: choice: a fixed order would add a requirement without changing the import's intent

### C-30: Header comparison uses the published names exactly.
Observable: Changing a published header's case or adding surrounding whitespace makes it unrecognized unless that exact token itself is published.
Source: choice: a published token defines a unique mapping without implicit aliases

### C-31: Each user record contains exactly as many fields as the header.
Observable: A data record with too few or too many fields is identified as invalid. A separator intended to represent an empty field still counts that field.
Source: choice: field counts prevent accidental column shifts and make missing cells distinguishable from empty cells

### C-32: A submission must contain at least one user record.
Observable: Upload a zero-byte file, a file with only a mark or ignored lines, or a valid header with no user records. The attempt is refused as having no user records.
Source: implied: U-2 and “bulk-create users” require user data from which to create an account

### C-33: A CSV of exactly one valid user record can be imported.
Observable: Submit valid headers followed by one eligible record. One user is created.
Source: choice: an admin should be able to retry a single corrected row using the same workflow

### C-34: The file size limit is 1,048,576 bytes inclusive.
Observable: An otherwise valid file of 1,048,576 bytes is within the limit. At 1,048,577 bytes, the admin sees a file-size refusal or the host's equivalent upload-size refusal. The measured bytes are the complete file contents, including the mark, line endings, headers, and ignored lines.
Source: choice: a 1 MiB cap provides a predictable boundary for a bounded administrative upload

### C-35: The record limit is 1,000 user records inclusive.
Observable: An otherwise valid file with 1,000 data records is within the limit. At 1,001, it is refused. The header and ignored empty lines count as zero user records. A multi-line quoted record counts once. A parsed data record counts even if its values are invalid.
Source: choice: bound the number of attempted creations independently of the byte limit

### C-36: Both limits are visible before submission.
Observable: Read the file limit of 1,048,576 bytes and the data limit of 1,000 user records in the import guidance before selecting a file.
Source: implied: U-3 requires the admin to know whether a file is within the supported range

### C-37: Content determines CSV validity.
Observable: A valid file can be processed even if a client supplies an empty or generic file type. A filename ending in .csv or a CSV file type cannot make invalid content pass.
Source: choice: file metadata varies by client and gives no guarantee about the file's contents

### C-38: User field values follow ordinary creation's required-value rules.
Observable: For each supported required field, a blank or whitespace-only value is accepted only if the identical value can produce an account through ordinary creation without additional input. The required fields without supplied defaults are the identity plus any mandatory host inputs described in C-16.
Source: implied: U-2 requires validation of missing data under the same rules as ordinary creation

### C-39: User field values follow ordinary creation's remaining validation rules.
Observable: Give the same supplied field value to ordinary creation and CSV import. Apart from CSV syntax and batch-level rules, both make the same decision about its allowed characters, format, length, allowable values, and dependencies on other fields. Exact host rules and bounds for each field are unconfirmed because no host contract was provided.
Source: implied: U-2 requires the import to preserve ordinary field admissibility

### C-40: User field values undergo ordinary creation's normalization.
Observable: Compare equivalent ordinary and imported inputs in the resulting user records or identity lookup. Case, whitespace, Unicode, and any other identity equivalences are determined by the host's existing normalization, whose exact rules are unconfirmed.
Source: implied: U-4 requires ordinary creation and import to agree on which identities are equivalent

### C-41: A batch containing a repeated identity is refused.
Observable: Put the same host-equivalent identity in two or more records of one file. No account is created for that identity, and the result points to its occurrences.
Source: choice: refusing intra-file duplicates lets the admin resolve competing values for the same user

### C-42: A batch containing an identity unavailable under ordinary creation is refused.
Observable: Include an identity already held by a user created manually or in an earlier import. Apply the host's ordinary rules for active, pending, disabled, archived, or deleted identities wherever those states exist. The record is refused if ordinary creation cannot claim that identity in the destination. Exact identity scope and any other reservation states are unconfirmed because the host is unspecified.
Source: implied: U-4 requires bulk creation to respect existing identity ownership

### C-43: The import leaves existing users unmodified.
Observable: Submit an existing user's identity with differing data. Their profile, access, account state, credentials, and destination membership retain their previous values.
Source: implied: “bulk-create” and U-4 grant creation only

### C-44: The import commits either every user record or zero user records.
Observable: In a file with valid records alongside a record that fails any applicable check, none of the valid records become visible as users. For a committed file of N records, find N created users.
Source: choice: one all-or-nothing result makes a corrected file safe to submit again after a confirmed rejection

### C-45: The import reports an actionable reason for rejection.
Observable: For a known rejection, see a reason distinguishing missing or unreadable file, encoding, CSV syntax, headers, no data, file size, record count, invalid user data, identity conflict, access or destination refusal, or service failure, as applicable. The host may show a generic access refusal when more detail would reveal protected information.
Source: implied: U-2 through U-7 require an admin to distinguish corrections from access or service problems

### C-46: Record-level errors identify their location in the submitted CSV.
Observable: For an invalid record, identify its starting physical line using line 1 as the first line of the file. CRLF counts as one line break and ignored lines still count. Identify the column for field-specific errors and the involved line numbers for duplicates within the file.
Source: choice: source locations make corrections practical even when cells contain newlines or the file includes empty lines

### C-47: A rejection may stop at a blocking error.
Observable: A rejected file has at least one applicable actionable error. The admin can correct the reported problem and resubmit even if additional errors become visible on the next attempt.
Source: choice: allow useful feedback without requiring exhaustive diagnostics or mandating an order among independent errors

### C-48: A confirmed successful import reports its committed creation count.
Observable: Submit a valid file of N eligible user records. A confirmed result reports exactly N users created.
Source: implied: U-1 requires the admin to know whether the requested accounts were created

### C-49: A committed user is available through ordinary user management.
Observable: After success, an authorized admin can find the new account through the destination's ordinary user listing or lookup under the same visibility rules and timing as an ordinarily created account.
Source: implied: U-1 requires the resulting accounts to be usable through existing user management

### C-50: CSV values cannot grant account privileges.
Observable: Attempt to include a role, permission, administrative flag, or privileged membership assignment in a header or field. The supplied data cannot give a user administrative access or change ordinary account privileges.
Source: choice: importing ordinary users requires no separate bulk privilege-granting operation

### C-51: Imported users receive the ordinary default permissions for newly created users.
Observable: Compare access for an imported user with an otherwise equivalent user created through the ordinary default creation path. Their default scope membership, role, and permissions match. Exact default grants are unconfirmed because the host is unspecified.
Source: implied: U-1 creates ordinary users subject to the same access model

### C-52: Imported users start in the ordinary initial account state.
Observable: Compare account status and sign-in eligibility with equivalent ordinary creation, including pending activation, disabled status, or immediate eligibility where applicable. The host's initial status and allowed transitions are unconfirmed.
Source: implied: U-1 requires users created in bulk to obey the existing account lifecycle

### C-53: The import accepts no credentials as CSV inputs.
Observable: A password, access token, recovery code, or other credential column is outside the accepted column set. No CSV cell becomes a credential.
Source: choice: use existing onboarding so the upload does not become a credential-distribution channel

### C-54: Imported users go through ordinary onboarding.
Observable: An imported user can use the same account claim, activation, or initial sign-in steps as an equivalent ordinarily created user. The exact supported steps, lifetime of any activation artifact, and any host retry limits are unconfirmed.
Source: implied: U-1 requires the accounts to be usable through the existing onboarding contract

### C-55: The import cannot bypass verification.
Observable: A CSV value does not mark an email, identifier, or other claim as verified where ordinary creation requires the user or the host to verify it.
Source: implied: U-1 requires ordinary trust rules to apply equally to an imported user

### C-56: Required creation notices are emitted only for committed users.
Observable: If equivalent ordinary creation triggers an invitation, activation message, or administrative creation notice, a rejected import triggers none of those creation notices for its rows. A committed import triggers the ordinary notices under their ordinary timing and delivery rules.
Source: choice: preserve the host's creation side effects without inviting users whose accounts do not exist

### C-57: Creation confirmation describes account persistence.
Observable: If a post-creation notice is delayed or fails after the accounts commit, the import result still reports the committed account count. It does not assert that any post-creation notice was delivered.
Source: choice: a failed notification must not lead an admin to infer that the accounts can be created again

### C-58: Data in CSV fields has no executable effect.
Observable: Formula-like text, markup, and URLs in a field are processed only as candidate account data. Uploading or viewing the result cannot execute or fetch them merely because of their contents.
Source: implied: U-2 submits user data, and entering user data does not authorize a separate action

### C-59: The result exposes only the account information the caller may view.
Observable: An authorized importer receives its own attempt's result. A different admin without access to that destination, a non-admin, or a now-revoked caller cannot retrieve protected account details through the import result.
Source: implied: U-5 requires result visibility to respect the same boundary as submission

### C-60: The import does not keep a retrievable copy of the uploaded file after processing ends.
Observable: After success, rejection, or failure, the raw upload is unavailable as an import download or history item. If the admin needs to submit the file again, they use their own copy.
Source: choice: the request requires creation and an outcome, with no need to maintain a second copy of the source file

### C-61: Import-specific operational records exclude raw uploaded contents.
Observable: Inspect import diagnostics after a file with user values or a rejected credential column. The raw CSV, cell values, and rejected credential values do not appear in import-specific operational records. Existing account records and the host's ordinary account audit data follow their existing access rules.
Source: choice: operators can diagnose import outcomes without retaining another source of user data

### C-62: Operator-visible outcomes distinguish completed creation, confirmed refusal, and unresolved completion.
Observable: Using the host's ordinary operational facilities, distinguish a committed batch with its created count, a known rejection or failure with its reason category, and an attempt whose outcome could not be determined at the time observed. Operator visibility covers the attempt time and destination when known, the outcome, and the count on success. The facility and its retention limit are unconfirmed.
Source: choice: these details let operators diagnose a failed release or interrupted import without a new management console

### C-63: Repeating an upload cannot recreate an identity created by the previous attempt.
Observable: Submit the same valid file again after it commits, including by repeating a timed-out submission or double-submitting it. At most one account per identity exists while those identities remain claimed under ordinary creation rules.
Source: implied: U-4 and U-7 require retry safety without overriding ordinary identity ownership

### C-64: Competing creations of the same identity respect ordinary uniqueness at commitment.
Observable: Race two imports, or race an import against ordinary creation or an identity change. If a competing operation has already claimed the identity when the import would commit, the full import is refused. The identity is held by at most one user in its ordinary uniqueness scope.
Source: implied: U-6 requires the same account uniqueness across concurrent entry points

### C-65: A concurrent removal releases an identity only as ordinary creation permits.
Observable: Race import against deletion, deactivation, or a change away from the incoming identity. At the import's commitment point, its decision reflects whether the host's ordinary rules have made the identity available. The exact rules for reuse and any waiting period are unconfirmed.
Source: implied: U-6 requires import to share the ordinary lifecycle of claimed identities

### C-66: Independent eligible imports can both succeed.
Observable: Submit two valid files with disjoint identities in an authorized destination. When the host has capacity for both, each can commit its own users without combining records or counts with the other.
Source: implied: U-6 requires distinct authorized submissions to keep distinct effects and results

### C-67: A competing operation cannot bypass an ordinary creation quota.
Observable: If the host limits users by scope, license, or another ordinary quota, race arrivals near that limit. The import commits only if the whole batch fits under the applicable quota at commitment. Quota membership and numeric limits are unconfirmed because no host was identified.
Source: implied: U-6 requires shared admission rules to hold even when creations overlap

### C-68: A confirmed pre-commit service failure leaves zero created users.
Observable: Make an account-validation or persistence dependency unavailable before commitment. On confirmed failure, none of the batch's accounts appear, including any processed before the failure.
Source: implied: U-7 and the all-or-nothing result require a service outage to leave no partial batch

### C-69: An unconfirmed result is not presented as a confirmed outcome.
Observable: If the client loses the result after upload or the service cannot determine whether creation committed, any status it can show says the outcome could not be confirmed. It does not report a definitive count or claim a confirmed failure.
Source: implied: U-7 requires the admin to distinguish a lost response from a failed creation

### C-70: A committed import survives client departure.
Observable: Close the browser, lose the connection, or navigate elsewhere after commitment. Reopen ordinary user management and find the accounts subject to ordinary visibility rules.
Source: implied: U-7 distinguishes the lifetime of created accounts from the lifetime of the upload interface

### C-71: Closing the interface gives no cancellation guarantee after submission.
Observable: Leave the page during a submitted import. On returning, the batch may have committed or may have stopped before commitment. Use ordinary user lookup to confirm what exists.
Source: choice: the requested upload needs clear outcome semantics without adding a cancellation feature

### C-72: An admin can submit again after a failed attempt.
Observable: After a known rejection, restore the dependency or correct the file as directed. Submit again through the same import entry point and receive the result for that attempt.
Source: implied: U-2 and U-7 require failure to end the attempt without locking out future imports

### C-73: The production upload path must admit the published maximum file.
Observable: In the target deployment, an authorized admin can deliver all 1,048,576 file bytes plus required request framing. The request-size ceilings of the host and any intermediary, including how they count framing, are unconfirmed. Any such ceiling must permit this observable.
Source: implied: U-3 and U-8 require the chosen product limit to fit the host's inbound request-size rules

### C-74: At-limit uploads must be able to reach a result under the host's execution rules.
Observable: In a healthy target deployment, a valid file at both limits can reach a definitive result. Host request deadlines, processing deadlines, and whether work may continue after a request ends are unconfirmed. If the host ends the client request before a result is known, the admin gets an unconfirmed outcome when status is available.
Source: implied: U-3, U-7, and U-8 require the host's request and execution rules to preserve the supported workflow

### C-75: Abandoned processing reaches an end.
Observable: After the host's request or processing deadline, an uncommitted attempt eventually ends or completes under the host's rules. Operators can distinguish a committed result from a confirmed failure or unresolved outcome. The exact deadlines and the availability of completion after disconnection are unconfirmed.
Source: implied: U-7 and U-8 require interrupted attempts to stop occupying the processing path indefinitely

### C-76: Production availability requires compatibility with ordinary account creation.
Observable: Before making upload available beyond development, verify that the deployed host supports authorized account creation, required inputs under C-16, ordinary default permissions, onboarding, and the advertised import boundaries. Any further production prerequisites imposed by the actual host are unconfirmed because no application, platform, or service was supplied.
Source: implied: U-8 requires import to run under the deployed host's account and admission rules

### C-77: The import becomes available through the host's ordinary release procedure.
Observable: After deploying and enabling the feature for a destination where ordinary creation is available, an eligible admin can use the import. The names and permitted values of any existing deployment controls are unconfirmed.
Source: choice: use the existing operational controls, with no separate import configuration surface required

### C-78: Withdrawing import availability prevents new imports.
Observable: After withdrawal or rollback has taken effect, attempts to start an import are refused or the entry point is absent in the restored version.
Source: implied: U-8 requires the operator to stop accepting new batches

### C-79: Withdrawal handles accepted but unfinished imports as whole batches.
Observable: Begin an import, then withdraw the feature before it commits. The accepted attempt can finish with all rows committed or end with zero created users. A call arriving after withdrawal does not start an import.
Source: choice: withdrawal need not forcibly cancel work already accepted if the whole-batch outcome is preserved

### C-80: Rolling back the release preserves committed users.
Observable: Create users in an import, then restore the prior product version. Those users remain available to authorized users through prior-version user management.
Source: implied: U-8 requires committed user data to survive withdrawal of the upload workflow

### C-81: Existing single-user creation retains its normal behavior.
Observable: An authorized admin can still create one user through the ordinary entry point with the same accepted fields, validation, defaults, and outcome as before the import release.
Source: implied: the request adds an entry point to creation

### C-82: Existing user lookup retains its normal behavior.
Observable: Find users created before the import release through the same ordinary listing and search behavior, under the same permissions.
Source: implied: U-8 requires continued operation with existing user data

### C-83: Existing user editing retains its normal behavior.
Observable: Make the same authorized permitted edit to an existing or imported account as to an ordinarily created account. The ordinary edit rules still apply.
Source: implied: the request changes how users can be created, and U-6 requires imports to coexist with user changes

### C-84: Existing user removal retains its normal behavior.
Observable: Apply the host's ordinary user-removal action to an existing or imported account wherever that action is supported. The same permissions, resulting state, and identity reuse rules apply.
Source: implied: U-6 and U-8 require existing removal to coexist with the import

### C-85: Existing users retain their account and sign-in state across import availability changes.
Observable: Release or withdraw the import without operating on an existing user. The user's status, credentials, verification status, and ability to sign in still follow their previous account state and policies.
Source: implied: the request adds creation for new users without changing the lifecycle of existing ones

### C-86: The import provides a create operation only.
Observable: The upload entry point offers creation and its result. It exposes no bulk update, deletion, role assignment, invitation resend, user export, scheduled import, or undo operation.
Source: implied: “upload a CSV to bulk-create users” defines the scope of the new operation
