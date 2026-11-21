## Use cases

### U-1: An admin creates a first batch of users
Flow: An admin opens user management, finds the CSV import, selects one CSV containing multiple new users and submits it. The admin sees the creation result and finds those users in the ordinary user list.
Source: request

### U-2: An admin chooses a file before submitting
Flow: An admin opens the import with no file selected, chooses a file, then replaces or removes it. The admin can leave before submitting without creating users.
Source: implied: uploading a CSV requires choosing what to submit

### U-3: An admin imports one user or fills a batch to its limit
Flow: An admin uploads a file containing one new user or a batch at the documented limit. The admin sees the number actually created.
Source: implied: a bulk operation needs a defined lower and upper boundary

### U-4: An admin corrects a CSV that cannot be imported
Flow: An admin submits an empty, unreadable, malformed, oversized or otherwise invalid file. The admin sees why the import was rejected, corrects the file and submits it again.
Source: implied: a selected file can fail before any user can be created

### U-5: An admin imports into a directory that already contains users
Flow: An admin uploads rows that overlap with existing users or repeat an identity in the file. The admin sees the conflict and can remove conflicting rows before trying again.
Source: implied: bulk-create applies to a directory with existing users

### U-6: A caller without import permission encounters an access refusal
Flow: A signed-out caller or a signed-in caller without admin permission tries to open the import or submit directly. No users are created, and the caller sees the application's access refusal.
Source: implied: the request grants the operation to admins

### U-7: An admin recovers after an import is interrupted
Flow: An admin submits a file and the request or user store fails. The admin sees a failure when it can be confirmed, or checks the ordinary user list if the outcome is unknown, then retries as needed.
Source: implied: a submitted batch can fail or lose its response

### U-8: Two admins import at the same time
Flow: Two admins submit overlapping or disjoint files. Each sees the outcome of their own batch and can inspect the resulting accounts within their authorized scope.
Source: implied: multiple admins can use user management at once

### U-9: An admin retries an already submitted file
Flow: After repeat submission or a lost response, an admin selects the same file again. Existing identities are reported as conflicts and each identity still has at most one account where uniqueness applies.
Source: implied: an admin can submit again after the first attempt

### U-10: An operator enables or withdraws the feature during a release
Flow: An operator deploys the release using the ordinary user-management deployment, observes it through existing operational channels, and can withdraw it. Admins still use the ordinary user-management flow for existing and previously imported accounts.
Source: implied: the feature must coexist with deployment, recovery and existing user data

### U-11: An admin handles a batch containing both valid and invalid rows
Flow: The admin submits a file with new users and an invalid row. The result identifies the invalid row. The admin corrects it and retries using the result to determine which records to include.
Source: implied: U-4 can occur in a file with multiple records

### U-12: An admin encounters a permission change during import
Flow: The admin submits from an authorized destination. Another authorized operator removes the admin's create authority before the batch takes effect. The import is refused, with zero new accounts.
Source: implied: U-6 also applies when authority changes during U-1

### U-13: An admin creates a user while an import is pending
Flow: An admin uses ordinary creation for an identity that another admin has submitted for import. Both callers get outcomes consistent with one creation for that identity.
Source: implied: U-5 and U-8 share the directory with ordinary creation

## Clauses

### C-1: The product accepts CSV uploads for bulk user creation
Observable: An admin submits one CSV with multiple valid new users and can find every resulting account in user management.
Source: request

### C-2: Admins can discover the CSV import within user management
Observable: An admin opens user management and can find the action for uploading a CSV.
Source: implied: U-1

### C-3: Selecting a file creates zero users before submission
Observable: An admin selects a file and checks the user list before submitting. The list contains zero users attributable to the selection.
Source: implied: U-2

### C-4: One valid user record is a valid batch
Observable: An otherwise valid file with exactly one new user record creates one user.
Source: choice: support the smallest nonempty file so corrections can be submitted even when a single record remains

### C-5: An upload with zero user records is refused
Observable: A zero-byte file or a valid header with zero user records creates zero users and yields an input error.
Source: choice: an empty upload cannot fulfill a creation request

### C-6: A file exceeding 1,048,576 bytes is refused
Observable: A file of 1,048,577 bytes is refused with a file-size error. A file of exactly 1,048,576 bytes passes the file-size check. The count covers the complete file before decoding, including the header, line endings and any byte-order mark, and excludes the enclosing upload request.
Source: choice: a 1 MiB file allowance bounds the upload while supporting interactive bulk creation

### C-7: An administrator can see whether a completed import succeeded
Observable: After a confirmed success, the submitting admin sees a success result for that upload.
Source: implied: U-1

### C-8: A failure identifies the failed input or operation
Observable: An admin sees an error describing an input problem, an access refusal, a conflict or an operational failure as applicable.
Source: implied: U-4, U-5, U-6 and U-7

### C-9: Import cannot be used without administrator authority to create users in the destination
Observable: A signed-out or unauthorized caller attempting to submit an import creates zero users.
Source: implied: 'Let admins'

### C-10: Import cannot create a new duplicate identity
Observable: After one submission creates an identity, a repeat or concurrent submission cannot create another account for that identity while it remains reserved in the applicable uniqueness scope.
Source: implied: U-8 and U-9 use the ordinary user directory

### C-11: Imported accounts remain available through ordinary user management after feature withdrawal
Observable: After withdrawing the import feature, an admin can find previously created accounts in the ordinary user list.
Source: implied: U-10

### C-12: The CSV import is visible only to a caller authorized to import into the destination
Observable: An authorized admin can open the import in the destination. A signed-out caller, a signed-in non-admin or an admin without create authority in that destination cannot open it.
Source: implied: U-1 and U-6

### C-13: An import uses the directory in which the admin submitted it
Observable: An admin who can create users in directories A and B submits from A. The new accounts appear only in A. If the application has only one directory, that directory is the destination.
Source: implied: created users belong to the user management context in U-1

### C-14: Each submission contains exactly one file
Observable: A submission with zero files or two or more files receives a selection error for the file count. A submission with one file passes the file count check.
Source: choice: one file gives the admin one batch and one outcome to interpret

### C-15: An admin can replace the selected file before submitting
Observable: The admin selects A then selects B. Submitting uses only B.
Source: implied: U-2

### C-16: An admin can remove the selected file before submitting
Observable: The admin removes the selection. The import has no file ready to submit.
Source: implied: U-2

### C-17: An import screen describes the accepted input before submission
Observable: Before choosing a file the admin can find the accepted encoding, separator, required headers, file size limit and record limit in the import flow.
Source: implied: U-1 and U-4 require enough information to prepare a file

### C-18: File content determines whether a file is CSV
Observable: The same otherwise valid CSV bytes pass the file-type check with or without a .csv suffix or a CSV media-type label. A .csv filename does not make invalid content acceptable.
Source: choice: CSV exports may have generic file metadata

### C-19: The file must be UTF-8 text
Observable: The import accepts valid UTF-8 with no byte-order mark or with one UTF-8 byte-order mark at the beginning. Invalid UTF-8 is refused with an encoding error.
Source: choice: UTF-8 supports international text and a leading mark accommodates common spreadsheet exports

### C-20: The import recognizes comma as the field separator
Observable: A comma between unquoted fields separates columns. Tabs and semicolon characters outside quotes are field content.
Source: choice: comma is the ordinary CSV separator and a single separator avoids ambiguous files

### C-21: The import accepts LF and CRLF as record endings
Observable: Otherwise valid files using LF, CRLF or a mixture pass the line-ending check. The final record may end at end of file. A bare CR outside a quoted value fails the check.
Source: choice: accept common Unix and Windows exports with or without a trailing newline

### C-22: A double-quoted CSV field can contain separators, line breaks or literal double quotes
Observable: A field enclosed in double quotes treats commas and LF or CRLF as part of the value. Two consecutive double quotes inside that field decode to one literal double quote.
Source: choice: preserve ordinary CSV quoting for field values

### C-23: Malformed field quoting invalidates the file
Observable: An unterminated quoted field, a double quote in an unquoted field or any character between a closing quote and the next delimiter, record ending or end of file yields a CSV syntax error. Only a double quote at the beginning of a field starts a quoted field.
Source: choice: malformed quoting makes record boundaries or values ambiguous

### C-24: Physically empty lines outside quoted fields are ignored
Observable: A zero-character line before the header, between user records or at the end contributes zero records. A line containing spaces, tabs, delimiters or quotes is subject to normal record validation. An empty line inside a quoted field remains part of the value.
Source: choice: harmless empty lines in export files should not create records

### C-25: The first nonempty CSV record is the header
Observable: The first record after any ignored empty lines is read as column labels. An upload with only ignored lines or a byte-order mark has zero user records.
Source: choice: a named header prevents positional guessing

### C-26: The default import schema requires the email header
Observable: For a product whose ordinary creation needs no other caller-supplied profile field, the complete supported header set is `email`. An empty header field or header with no `email` yields a header error. `email` matches after trimming surrounding ASCII spaces and tabs and folding ASCII letter case.
Source: choice: use a single named identity field as the working contract where no existing target schema has been identified

### C-27: Additional required profile data follows the destination's ordinary create contract
Observable: If the target already requires other caller-supplied profile fields to create ordinary users, the import lists each such field with its published header, accepted values and limits before submission. Those additional field names, value sets and limits are unconfirmed because the application is unidentified. Optional profile fields stay outside the import contract to keep it limited to creation inputs the product requires.
Source: choice: preserve existing mandatory profile data without adding optional bulk editing

### C-28: A header cannot repeat a column
Observable: A header containing the same supported column twice, including differently cased or padded spellings of `email`, yields a duplicate header error.
Source: choice: each input field has exactly one source per row

### C-29: The import refuses unsupported headers
Observable: A file with headers beyond the supported required fields yields an error identifying the unsupported headers. In the default schema `name`, `role`, `password`, `id`, `tenant`, `status` and `permissions` are unsupported, as is any other header besides `email`. System-controlled fields remain unsupported when additional profile fields apply.
Source: choice: rejecting unmapped columns avoids silently discarding data or accepting account controls

### C-30: Each user record has the header's column count
Observable: A record with fewer or more fields than the header yields a row error, including when a trailing comma creates an extra empty field.
Source: choice: a column-count check prevents misinterpreting incomplete or shifted data

### C-31: A file with more than 1,000 user records is refused
Observable: A file with 1,000 user records passes the record-count check. A file with 1,001 user records yields a record-count error. The header and ignored empty lines count as zero. Each parsed logical record after the header counts once even if it spans multiple lines or would fail field validation.
Source: choice: a bounded batch remains practical to validate and correct

### C-32: Each user record must provide a nonempty email address
Observable: An empty parsed email field or one containing only ASCII spaces and tabs yields an email-required error.
Source: implied: each row must identify a user under C-26

### C-33: An email value is subject to the destination's existing ordinary email rules
Observable: For a destination that already validates email, the same parsed address passes or fails the email check in either creation path. The target's allowed forms and exact length bounds are unconfirmed.
Source: implied: importing a user into the ordinary directory preserves its creation rules

### C-34: The fallback email check accepts an ASCII dot-atom mailbox with a DNS-style domain
Observable: When the product has no existing email validator, a valid address has exactly one `@`, a local part of 1 to 64 ASCII characters and at most 254 ASCII characters total after trimming surrounding ASCII spaces and tabs. The local part contains letters, digits or the printable symbols in the code span `!#$%&'*+-/=?^_{|}~` or the grave accent. Dots may appear only between nonempty runs of those characters. The domain has at least two dot-separated labels of 1 to 63 ASCII characters each, using letters, digits or hyphens, with each label starting and ending in a letter or digit. This fallback refuses other forms, including display names, quoted local parts, address literals and raw Unicode addresses.
Source: choice: establish a concrete baseline for a product without a known validator

### C-35: A successful import reports the number of accounts created
Observable: An admin who submits three valid distinct new users sees that three accounts were created.
Source: implied: U-1 and U-3 need to distinguish complete creation from an incomplete outcome

### C-36: An import rejects repeated identities within the same file
Observable: Two rows resolving to the same uniqueness key cause a file conflict. The result identifies the records involved.
Source: choice: repeated rows indicate an ambiguous batch and the admin can resolve it before creating users

### C-37: An import rejects an identity that already exists under ordinary uniqueness rules
Observable: When a submitted identity conflicts with an account reserved under the destination's ordinary uniqueness policy, the affected record gets a conflict error. The existing policy determines which lifecycle states reserve identities and whether the scope is one directory or wider. The actual target scope and state list are unconfirmed.
Source: implied: U-5 creates new users under the same identity rules as ordinary creation

### C-38: Fallback uniqueness treats email addresses as case-insensitive within the destination
Observable: If the destination has no existing identity uniqueness rule, ` Ada@Example.COM ` and `ada@example.com` resolve to the same identity within the destination. The fallback compares the trimmed value with ASCII letters lowercased. A different destination has a separate uniqueness scope if the product has more than one directory.
Source: choice: a case or edge-space change must not let a retry create another account under the fallback identity rule

### C-39: Fallback identity comparison leaves provider-specific address variants distinct
Observable: Under the fallback rule, `ada+team@example.com` and `ada@example.com` are distinct, as are `a.da@example.com` and `ada@example.com`.
Source: choice: provider alias behavior is outside the importer's knowledge

### C-40: A failed batch creates zero accounts
Observable: A file with one invalid record alongside valid records, or a write failure confirmed before the batch took effect, creates zero accounts attributable to that upload.
Source: choice: whole-batch failure lets the admin correct the file or retry without reconstructing which rows took effect

### C-41: A reported row error locates the logical record
Observable: A row error identifies the record by its 1-based logical record number with the header as record 1. Ignored empty lines do not advance the number and a quoted multiline record advances it once.
Source: choice: locate corrections reliably even in a file with multiline records

### C-42: An unreadable record structure yields a file-level error
Observable: When malformed quoting prevents determining user record boundaries, the result describes the quoting problem without assigning an unreliable record number.
Source: choice: give the admin an actionable problem even when rows cannot yet be identified

### C-43: An invalid submission surfaces at least one reason that prevents creation
Observable: If several checks fail, the result identifies at least one blocking input error. Error ordering and the number of further errors are left open.
Source: choice: actionable feedback is required while exhaustive diagnostics are optional

### C-44: Success is reported only when the whole batch has taken effect
Observable: An admin who receives confirmation can find every account from the batch in the ordinary directory without waiting for further import processing.
Source: implied: U-1 and U-11 distinguish created accounts from accepted input

### C-45: Concurrent imports competing for one identity cannot both succeed
Observable: With otherwise valid overlapping batches in the same uniqueness scope, one can win the competing creation. If both attempts reach creation while the winning identity remains reserved, the losing batch reports a conflict and creates zero accounts, including its nonoverlapping rows.
Source: implied: U-8, C-10 and C-40

### C-46: Noncompeting imports may each succeed independently
Observable: Two otherwise valid concurrent uploads with disjoint identities and available destination capacity can both succeed. Neither is refused merely because the other is processing.
Source: choice: an import does not give its submitting admin exclusive use of the directory

### C-47: Ordinary creation and import share the same uniqueness decision
Observable: When ordinary creation and import race for one identity in the same uniqueness scope, the operation whose creation takes effect first reserves that identity under the ordinary policy. A losing import reports conflict and adds zero accounts. A losing ordinary create uses its normal conflict response.
Source: implied: U-13 and C-10

### C-48: Identity conflicts are decided against the directory at creation time
Observable: An identity freed by ordinary account management before the batch takes effect may be created if ordinary creation now permits it. If the identity remains reserved at that point, the import reports conflict even if the prior lookup showed it as available.
Source: implied: U-5 and U-13 use the directory's current identity state

### C-49: Import authority must still hold when creation takes effect
Observable: A previously authorized submission creates zero accounts if, before creation takes effect, the submitter account no longer allows admin access, the session expires or is invalidated through sign-out or revocation, the submitter loses admin or destination create permission, or the destination no longer exists or accepts creation. Any additional target-specific access conditions are unconfirmed. The refusal uses the ordinary behavior for the applicable condition.
Source: implied: U-6 and U-12 require authority for the creation itself

### C-50: A completed import survives a later change to the submitter's authority
Observable: Removing import authority after the batch took effect leaves the created accounts in the directory.
Source: implied: U-10 and U-12 concern a creation completed under then-current authority

### C-51: Repeating a successfully imported file is subject to ordinary creation rules
Observable: If the identities in the original file are still reserved, resubmitting it yields conflicts and creates zero accounts. If the identities are later freed through ordinary lifecycle rules, submitting again evaluates the file against the directory at that time.
Source: choice: repeat submissions are fresh creates with current identity checks

### C-52: An in-progress submission is distinguishable from confirmed success
Observable: While the result is pending and the admin stays in the flow, the import shows that the submission is still being processed.
Source: implied: U-7 requires the admin to know whether the operation finished

### C-53: The submitting screen suppresses another submission of the pending file
Observable: Activating the same submit control twice or repeatedly while its first submission is pending does not send another batch from that screen. Independent submissions remain subject to ordinary conflict checks.
Source: choice: prevent accidental repeat actions and keep the current result unambiguous

### C-54: An interrupted transfer that never delivers a complete file creates zero accounts
Observable: If the transfer ends before the product receives the entire file, the directory gains zero accounts from that submission.
Source: implied: U-7 and the complete-file validation required for U-4

### C-55: A confirmed operational failure reports zero accounts created
Observable: If the service can confirm the batch did not take effect after a storage or request-handling error, the admin sees an operation failure with zero accounts created.
Source: implied: U-7

### C-56: A lost or indeterminate response is not represented as confirmed success or failure
Observable: If a connection loss, timeout or interrupted dependency leaves the outcome unknown and the flow remains reachable, it reports that the outcome could not be confirmed.
Source: choice: the admin must be able to recover without treating transport failure as proof of zero writes

### C-57: Leaving the import after submission does not provide a cancellation guarantee
Observable: After an admin closes or navigates away from the import during submission, the directory may show a completed batch when the admin returns.
Source: choice: the requested upload does not require a cancellation operation

### C-58: Retry after a failed submission is available from the import flow
Observable: An authorized admin can submit again after a rejected, failed or indeterminate result. Re-selecting the same file is sufficient where the original selection was cleared.
Source: implied: U-4, U-5 and U-7

### C-59: A subsequent attempt does not reuse a previous result
Observable: After the result for file A and submission of file B from the same screen, the pending or completed result for B refers to B.
Source: implied: U-2 and U-9 distinguish which file is being submitted

### C-60: The standard browser file picker supplies the filename without its local path
Observable: If the import uses an HTML file picker, an admin can choose a file from a nested local directory and submit it without providing its local path.
Source: implied: the HTML File Upload state excludes local path components from selected filenames. [WHATWG HTML](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file))

### C-61: A host upload refusal may occur before the application receives the file
Observable: On an HTTP deployment, an upstream 413 response is a size refusal for the full request. The host may instead terminate the transfer. The exact host request-body limit in bytes is unconfirmed because the deployment is unidentified.
Source: implied: HTTP 413 permits refusing or terminating an oversized request. [RFC 9110 §15.5.14](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.14)

### C-62: The deployed upload path accommodates the documented file limit
Observable: An admin in the deployed environment can submit an otherwise valid 1,048,576-byte file through the ordinary import interface without a host size rejection. The total transport allowance, including applicable request overhead, is unconfirmed until the host and request transport are known.
Source: choice: the advertised file allowance must be usable through the deployed upload path

### C-63: A gateway timeout does not establish that the batch failed
Observable: If an HTTP gateway returns 504 and there is no definitive creation result, the product treats the result as unconfirmed. The gateway response deadline in seconds is unconfirmed.
Source: implied: HTTP 504 reports that a gateway did not receive a timely upstream response. [RFC 9110 §15.6.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.5)

### C-64: A supported deployment can complete a batch at the published record limit
Observable: In a supported deployed environment with working dependencies and sufficient directory capacity, a valid 1,000-record batch within the file limit can reach a definitive result. The host's receive, execution and response ceilings, the account store's operation and transaction ceilings, and any requirement to continue work outside the request are unconfirmed. The product promises no separate completion-time figure.
Source: choice: the published batch limit must be usable even though the target host and store have not been identified

### C-65: A deployed import requires the ordinary account creation dependencies to be available to it
Observable: If the destination store or any existing mandatory identity service cannot accept account creation, the admin receives the confirmed-failure or unconfirmed-outcome behavior appropriate to what completed. The runtime, account store, any mandatory identity service and their production prerequisites are unconfirmed. No separate provider is part of the import contract.
Source: implied: U-7 and U-10 require the product's actual user creation dependencies

### C-66: A recovery restart preserves a fully applied import
Observable: After a successful batch, an ordinary recovery restart of the user directory leaves the complete batch available to authorized admins.
Source: implied: U-7 and U-10 create ordinary durable accounts

### C-67: Withdrawing the import feature prevents new imports
Observable: After the release withdrawal takes effect, starting a new import is unavailable, including a direct submission from an already open screen.
Source: implied: U-10

### C-68: Withdrawing the feature leaves an in-flight import with a whole-batch outcome
Observable: If withdrawal interrupts an already submitted import, the directory eventually shows either all its newly created accounts or zero accounts from it. An admin with no definitive response uses the unconfirmed-outcome behavior.
Source: implied: U-10 and C-40

### C-69: Ordinary operational channels expose import outcomes to operators
Observable: Where the application has an operational monitoring channel, its authorized operators can distinguish confirmed success, confirmed rejection, confirmed service failure and unconfirmed outcome. The channel, deployment controls and release requirements outside development are unconfirmed.
Source: choice: reuse the application's operational access for triage and release withdrawal

### C-70: Ordinary single-user creation keeps its existing input contract
Observable: An admin can still use the ordinary create action with the same fields, requiredness, accepted values and limits as before release. Those product-specific members and figures are unconfirmed.
Source: implied: the request adds a bulk creation path to U-1

### C-71: Ordinary single-user creation keeps its existing access policy
Observable: A caller using ordinary creation has the same permission decision as before release for the same identity, role and destination. The target's exact role and destination rules are unconfirmed.
Source: implied: the request grants permission for an import without altering ordinary creation

### C-72: Ordinary single-user creation keeps its existing result behavior
Observable: The same ordinary create submission still returns its usual success, input failure, permission refusal, identity conflict or service failure. Exact target response formats are unconfirmed.
Source: implied: the request adds a bulk creation path to U-1

### C-73: Existing account values are unaffected by an import
Observable: After a new, conflicting or failed import, existing accounts retain their profile data, identity, roles, permissions, credentials, status and directory membership except for changes made by independent ordinary actions. Any additional target-specific account attributes also remain unchanged, with their names unconfirmed.
Source: implied: 'create users' covers new accounts

### C-74: Imported accounts receive the ordinary generated account identity
Observable: Each imported user has the same kind of system-assigned identifier as an ordinary new user. CSV values cannot select it. The identifier format and generation rules are unconfirmed.
Source: implied: U-1 creates users of the same kind as ordinary creation

### C-75: Imported accounts receive the ordinary initial account state
Observable: An imported user starts in the state ordinary creation assigns to the corresponding user. The state names and default are unconfirmed. A CSV cannot directly set account status.
Source: implied: U-1 adds a path to the ordinary account lifecycle

### C-76: Imported accounts receive ordinary baseline privileges
Observable: An imported user receives the roles, permissions and group memberships that ordinary creation assigns to a new standard user when no elevations are requested. The exact default sets are unconfirmed. CSV submission itself cannot grant elevated privileges.
Source: implied: the request grants upload authority to the submitting admin, not administrative status to imported users

### C-77: Imported accounts follow ordinary credential initialization
Observable: An imported user's credential setup and sign-in eligibility follow the ordinary new-user policy. Credential types and initial eligibility conditions are unconfirmed. No CSV field is used as a credential.
Source: implied: U-1 adds a creation path into the same account system

### C-78: Imported accounts follow ordinary onboarding notification rules
Observable: If ordinary creation sends a notification for a corresponding new user, an imported user gets that same notification under the same conditions after the account exists. If ordinary creation sends none, import sends none. Notification channels, triggers and delivery rules are unconfirmed.
Source: implied: U-1 creates ordinary accounts with their established onboarding behavior

### C-79: A failed import causes no onboarding notifications for its rows
Observable: Submitting a confirmed rejected or failed batch causes zero invitations or onboarding messages attributable to that batch.
Source: implied: C-40 creates zero accounts and C-78 ties notifications to created accounts

### C-80: A duplicate submission causes no extra onboarding notification for an already reserved identity
Observable: Re-uploading a successful batch while the original identities remain reserved generates zero additional notifications for those accounts.
Source: implied: U-9 and C-78

### C-81: Ordinary account visibility rules apply to an imported account
Observable: A caller can see and find an imported account in the ordinary list, search or details only when the caller could see an equivalent ordinarily created account. The product's exact visibility policy and available views are unconfirmed.
Source: implied: U-1 creates accounts in ordinary user management

### C-82: Ordinary profile editing remains available for an imported account
Observable: An authorized admin can edit an imported account using the same fields and rules available for an ordinarily created account in the same state. The exact editable fields and conditions are unconfirmed.
Source: implied: U-10 carries on with ordinary accounts after import

### C-83: Ordinary account lifecycle actions remain available for an imported account
Observable: An authorized admin can use the product's existing account disable, re-enable or delete actions on an imported account wherever those actions exist and would be allowed for an equivalent ordinary account. Other target lifecycle actions and their applicability are unconfirmed.
Source: implied: U-10 carries on with ordinary accounts after import

### C-84: Ordinary account capacity limits also apply to an import
Observable: A batch that would exceed an existing capacity or creation quota for its destination gets a capacity or quota refusal and creates zero accounts. A batch reaching exactly the allowed capacity passes that check. Exact quota types, values and measurement periods are unconfirmed.
Source: implied: a new entry point into U-1 cannot bypass the ordinary directory's limits

### C-85: A batch is visible atomically through ordinary user management
Observable: While a valid import takes effect, a directory view able to display the complete batch can see zero or all its accounts, with no intermediate subset attributable to the import. Ordinary pagination, filters, visibility policy and separate lifecycle actions can still affect what the viewer sees.
Source: implied: the chosen whole-batch behavior in C-40 applies to the observable directory state

### C-86: An unauthorized import attempt reveals no validation or account information
Observable: For submissions that reach the import service, a caller without authority over the destination receives the ordinary access refusal whether the file is valid, invalid, empty, conflicting or absent. The result contains no row diagnostics or indication that a submitted identity exists.
Source: implied: U-6 cannot use import as a user lookup

### C-87: Import diagnostics respect the ordinary visibility of conflicting accounts
Observable: If an identity conflicts with an account the submitting admin may not view, the import can report that the submitted identity is unavailable. The result contains no conflicting account identifier, directory membership, profile data or account state.
Source: implied: U-5 and U-6 preserve directory access boundaries

### C-88: Import results are private to the submitting admin while authorized
Observable: Another admin opening the import, or the submitter after losing destination access, cannot retrieve that upload's file contents or row diagnostics from the import flow. Ordinary access to created user records follows C-81.
Source: choice: keep per-upload feedback private without adding shared import history

### C-89: Operational import reporting omits uploaded content
Observable: An operator checking import outcomes sees no raw file, submitted cell values or original filename in import-specific operational output. Existing account audit records continue to follow the ordinary creation audit policy.
Source: choice: operators need outcome information for triage without a second copy of the roster

### C-90: The import provides no uploaded-file retrieval after resolution
Observable: After success or confirmed failure, returning to the application offers no way to retrieve the uploaded file. Once an unconfirmed attempt resolves on the service, the same rule applies. Ordinary created accounts remain available under their existing rules.
Source: choice: bulk creation needs the upload as input for one attempt

### C-91: CSV data has no effect as executable content
Observable: An admin submitting a filename, header or value containing markup or formula-like text sees it rejected under the applicable rule or handled as inert text. Uploading it triggers no execution or unintended external request.
Source: implied: the CSV supplies user data

### C-92: The import has no effect on pre-existing administrator sessions
Observable: An admin already signed in can continue using ordinary user management under the same session rules after an unrelated import. The target's exact session lifetime and renewal rules are unconfirmed.
Source: implied: U-8 can occur during ordinary concurrent user-management activity

### C-93: Import preserves ordinary auditing for account creation
Observable: If ordinary account creation records an audit event, each account created by import is observable through the same audit policy with the submitting admin attributed as the initiator where ordinary events record one. Event fields and retention limits are unconfirmed.
Source: implied: a batch creates ordinary accounts on behalf of its submitting admin

### C-94: The submitter can identify the file currently selected
Observable: After selecting A and replacing it with B, the import identifies B as the file ready to submit. After removal, it indicates that there is no selection.
Source: implied: U-2 requires knowing which file the action will send

### C-95: Closing the picker without choosing a replacement preserves the selection
Observable: An admin with file A selected opens the chooser and dismisses it without choosing a file. A remains selected.
Source: choice: keep an explicit selection until the admin replaces or removes it

### C-96: A file that cannot be read produces an upload error
Observable: If a selected file becomes unreadable before the full file reaches the product, the admin sees that the upload could not be completed when the flow remains reachable.
Source: implied: U-4 and U-7 distinguish a transfer error from invalid CSV

### C-97: A submission's input is fixed once the admin submits it
Observable: After submitting file A, interacting with the selection for an eventual next attempt cannot replace A for the in-progress attempt.
Source: implied: U-1 submits the file selected at the time of submission

### C-98: Late feedback from an earlier attempt cannot replace the result for a newer attempt
Observable: If the flow has reported A as unconfirmed and the admin submits B, a delayed response for A does not change the pending or completed result shown for B.
Source: implied: C-59 must hold when responses arrive out of order

### C-99: An attempt eventually stops creating accounts
Observable: An attempt that reached processing resolves to either the full batch or zero accounts once the service can complete recovery. After the outcome is final, the same attempt creates no further accounts. The recovery deadline is unconfirmed.
Source: implied: C-40 and U-7 require an end to the attempt even if the submitting client disconnects

### C-100: A reported field error identifies the field
Observable: An error specific to an input field identifies that field to the admin.
Source: implied: U-4 requires enough information to correct the reported row error

### C-101: Fallback email validation makes no deliverability decision
Observable: Under the fallback syntax-only rule, a syntactically valid email with a domain that cannot receive mail still passes the email check.
Source: choice: creating an account does not require proving delivery when there is no existing validator

### C-102: A file containing a NUL character is refused
Observable: A file that decodes as UTF-8 but contains U+0000 in a header, data value or quoted field yields an input error.
Source: choice: NUL is outside the text input contract for account records

### C-103: A quoted bare CR is passed to field validation as data
Observable: A CR inside a quoted field does not end the record. The matching field's validation decides whether it can hold that character.
Source: choice: retain quoted content under the same value rules as other characters

### C-104: Import enforces the ordinary protection against unintentional cross-site account creation
Observable: If the target is a browser application using ambient sign-in credentials, another site cannot cause a batch to be created merely by inducing the signed-in admin's browser to submit it. The deployed request protections are unconfirmed.
Source: implied: U-2 and U-6 require an authorized admin submission

### C-105: Concurrent operations cannot overfill the destination
Observable: If concurrent imports or ordinary creates compete for the same remaining capacity, the accounts created never exceed the ordinary bound. An import unable to fit its entire batch receives a capacity refusal. The target's quota values are unconfirmed.
Source: implied: C-40 and C-84 also hold during U-8 and U-13

### C-106: The fallback stored email preserves submitted casing
Observable: Where the product has no ordinary email storage conversion, the account's address preserves the characters supplied after trimming surrounding ASCII spaces and tabs. The case-insensitive comparison in C-38 does not change the address stored for the account.
Source: choice: preserve the admin's supplied address spelling while comparing identities consistently

### C-107: Import carries the submitted email into the ordinary account
Observable: After success, ordinary user management shows the imported user's submitted address with the same email normalization that ordinary creation applies.
Source: implied: U-1 creates the account identified by the input email

### C-108: The import starts with no file selected
Observable: Opening a fresh import shows an empty selection before the admin chooses a file.
Source: implied: U-2 submits a file the admin has selected for this import

### C-109: Every field required by the import schema must have a header
Observable: If the target requires more than email under C-27, omitting any published required header yields a header error identifying at least one missing required field. The target-specific additions to the default schema are unconfirmed.
Source: choice: a header omission should be correctable before any account is created

### C-110: Fields are matched by header when the schema has multiple fields
Observable: If additional fields are required under C-27, a CSV with the same supported headers and corresponding values in a different order passes the same checks and supplies the same account values.
Source: choice: header names identify data without prescribing an order for the admin's export

### C-111: A confirmed input rejection reports that zero accounts were created
Observable: After a confirmed validation or identity conflict rejection, the submitter can tell from the result that the upload created zero accounts.
Source: choice: whole-batch rejection should tell the admin which part of the file needs resubmission

### C-112: A host size refusal is explained as a size failure when it reaches the import flow
Observable: If the flow receives an explicit oversized-request refusal from the host, it identifies size as the cause and creates zero accounts for that refused upload. The host threshold is unconfirmed.
Source: implied: U-4 requires an actionable explanation for a known upload refusal

### C-113: An onboarding delivery failure after creation leaves the created account available
Observable: If ordinary onboarding includes a delivery step after the account exists, a delivery failure after the batch took effect does not remove any of the created accounts. Any delivery retry follows the ordinary notification policy, whose limits are unconfirmed.
Source: implied: U-1 confirms account creation and C-78 follows ordinary notification behavior

### C-114: Withdrawing the import release preserves ordinary creation
Observable: After withdrawal, an authorized admin can still create an ordinary user in the same destination with the pre-release input and access rules.
Source: implied: U-10 continues ordinary user management after release withdrawal

### C-115: Checking the ordinary directory is available after an unconfirmed attempt
Observable: After an unconfirmed attempt or interrupted client session, an admin with current directory access can reopen ordinary user management to check which submitted identities are present. The check shows current accounts subject to ordinary visibility.
Source: implied: U-7 and U-9 recover using the ordinary directory

### C-116: Import confirmation is independent of post-creation invitation delivery
Observable: In a product that delivers invitations after creating accounts, a successful creation result can be confirmed while invitation delivery is pending.
Source: implied: U-1 confirms user creation and C-78 permits separate post-creation delivery

### C-117: Under fallback uniqueness an existing account reserves its email until permanently removed
Observable: When C-38 applies, an account record still present in the destination reserves its email in every state, including enabled, pending, disabled and soft-deleted states wherever the product has them. Permanent removal releases the address if no other account record reserves it. The product's actual lifecycle state names are unconfirmed.
Source: choice: keep identity reservation tied to retained account records where no ordinary rule defines it

### C-118: A pre-existing duplicate identity remains untouched by a conflicting upload
Observable: If legacy data already contains two or more records with the same uniqueness key, uploading that key reports a conflict without changing, merging or removing the existing records.
Source: implied: U-5 and C-73 preserve accounts already in the directory
