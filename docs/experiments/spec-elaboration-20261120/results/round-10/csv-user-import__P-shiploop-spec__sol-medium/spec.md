# User Administration Specification

## Scope and source

**Request (2026-11-21, “The incoming request”)** — “Let admins upload a CSV to bulk-create users.”

| Request outcome | Acceptance |
| --- | --- |
| Admins can use the feature within their user-creation scope | R-1 A1–A3 |
| Admins can upload a CSV through the user-management interface | R-2 A1–A4 |
| A single CSV creates multiple actual user records | R-3 A1–A4 |
| Admins can determine the result of the upload and recover from failure | R-4 A1–A4, supporting the requested creation outcome |

The request is the product source. This standalone run supplies no prior spec, accepted baseline, reference system, repository, runtime, discovery or research result. There are no prior IDs or parity commitments to reconcile. References to ordinary user creation describe behavior this feature must preserve where present. Its actual rules remain evidence gaps. The proposed defaults are recorded in Submission. Bulk update, deletion, role assignment, password import, invitation campaigns, saved CSVs and import history are outside this scope.

## Requirements

Acceptance rows describe future checks. Every product check is pending implementation and execution. A case ID identifies a prose verification obligation.

### R-1 — Restrict imports to authorized admins

**Basis and delta.** Request (2026-11-21, “The incoming request”), “Let admins upload”. Add a bulk-create entry point under user management. Preserve ordinary authentication, role and creation-scope rules. The actor names below are logical roles. Their production mappings and the route are unobserved.

| Acceptance | Positive | Failure | Boundary | Surface and confirmation |
| --- | --- | --- | --- | --- |
| A1 | An authenticated admin with create permission for the active account scope can open Import users. | Signed-out users and authenticated users without the required authority see no import controls. Direct entry receives a sign-in or access-denied state as appropriate. | An admin with authority limited to another scope cannot open this one. | TC-1. Visit the actual user-management entry and direct import route under each identity and inspect the rendered controls and response. |
| A2 | A submission is attributed to the current admin and current authorized scope. | Unauthenticated, non-admin, out-of-scope and unresolvable authority requests cannot start a new attempt or create users and disclose no row or result details. | Authority must still permit the operation at the commit boundary. Revocation effective before commit prevents the whole write. | TC-1. Invoke the real submit boundary directly and revoke the actor between validation and commit. Read the authoritative user directory and confirm zero changes. |
| A3 | The initiating admin can retrieve their result while still authorized in the original scope. | Other principals, other scopes and the original admin after revocation receive no status, counts, row details or existence signal. | Logout or scope switch clears displayed import state. An old response cannot populate the replacement context. | TC-7. Use the same attempt reference with the original actor, a second admin and another scope. Switch scope before a delayed response arrives and inspect the actual response and UI. |

**State and boundary.** The existing identity/permission authority owns principals, roles and scope. The UI holds only presentation state for the active context. The import boundary derives the effective principal and target scope from trusted product context and evaluates current authority on entry, submission, commit and result exposure. Positive client state provides no grant. If authority is unavailable, deny. Incremental permission reads and subscription cursors are inapplicable because the contract requires authority for each protected action. The import feature owns import denials under R-5. The identity authority retains ownership of ordinary authentication and role events.

**Open gap.** The product owner and identity owner must identify the actual admin entitlement, scope model, authorization source and how a revocation is ordered against creation. Planning must confirm this against the real route and effective identities before authorization or commit integration. Establish who can provision isolated admin and non-admin fixtures before TC-1/TC-7. Proceed with scope-independent file and UI state design.

### R-2 — Accept a CSV and explain validation failures

**Basis and delta.** Request (2026-11-21, “The incoming request”), “upload a CSV”. Add selection, format instructions, explicit submission and actionable validation feedback. Preserve other user-management journeys and ordinary account field validation. The request supplies neither a schema nor a CSV dialect. The following input contract is the working default.

One file per attempt. UTF-8 with an optional initial byte-order mark, comma delimiter, LF or CRLF record endings, with or without a final record ending. Support double-quoted fields, doubled quotes within quoted fields and quoted record breaks. Validate decoded values against account rules. Ignore completely empty unquoted records after the header. A quoted empty value or whitespace-only value is still a field and is validated. The default header is exactly `email`, case sensitive, with exactly one field per data record. Use the directory's normal email validation and identity normalization. Show the accepted header, required fields and approved upload limits before submission. In diagnostics, number logical CSV records beginning with the header as record 1, including ignored empty records in the numbering. Use a file-level error when a reliable record number cannot be established.

| Acceptance | Positive | Failure | Boundary | Surface and confirmation |
| --- | --- | --- | --- | --- |
| A1 | Import users offers a labeled single-file chooser, format instructions, selected filename and an explicit Import action. | An unreadable or incomplete upload receives a corrective message and creates zero users. | Choosing, replacing or clearing a selection before Import creates zero users. With no selection, Import is unavailable. | TC-2. In the admin UI choose, replace and clear files, then submit a truncated upload and compare the directory before and after. |
| A2 | A well-formed file with the expected header and at least one valid data row reaches creation. | Reject invalid encoding, malformed quoting, incorrect headers, unequal field counts and files with no data. Identify the file-level issue or record when determinable and create zero users. | Accept the supported BOM, line endings and quoted forms. Check the actual content even when the filename suggests CSV. | TC-3. Upload GS, GQ, GE, GH, GQX, GM, GB and GT from the fixtures. Observe the validation results and check directory state for each upload. |
| A3 | Data fields follow the directory's account validation rules. | For a parseable file with the expected header and field count, identify each invalid field by record number and field, with correction guidance. Reject the batch before any user is created. | Empty, whitespace-only and absent required values are invalid. An ignored empty record cannot shift subsequent reported record numbers. | TC-3. Upload GV and GF and assert the exact failing input locations and zero creates, including for the valid record. |
| A4 | Files within the approved byte and data-record limits can proceed if otherwise valid. | Enforce each limit on the authoritative boundary, reject the whole file with the applicable limit and permit a smaller replacement. | Valid input exactly at either limit is eligible. Input one unit over is rejected with zero writes. | TC-9. Generate boundary fixtures against confirmed bounds, holding the other dimension within range, and compare the response and authoritative state. NOT-REPLAYED: bounds and feasible independent boundary fixtures are open. |

**State and data.** The selected file and filename belong to the initiating admin's active UI context. Replace/clear/navigation/sign-out/scope switch drops the selection. Submission binds the selected content to that attempt. The importer temporarily handles bytes and decoded values only while resolving the request, then removes its processing copies on success, rejection or when the authoritative request is abandoned. Raw bytes, filenames and row values stay out of operation status, diagnostic telemetry and durable import storage. The active form may show the selected filename and row-number/field/reason diagnostics. A later correction uses a fresh selection. The original local file remains under the admin's control. Runtime facilities and physical limits are unobserved.

**Open gap.** Product and directory owners confirm required columns, validation and normalization, supported exports/dialects and example copy before schema-dependent work. Runtime owner establishes byte/row, parsing time, transient storage/memory and concurrent work limits before admission criteria or boundary fixtures are finalized. Until confirmation, the default above supports design and logical cases only.

### R-3 — Create the batch without modifying existing users

**Basis and delta.** Request (2026-11-21, “The incoming request”), “bulk-create users”. Add creation of new users from one valid CSV. Preserve existing user records, entitlements, and ordinary account-creation invariants. Atomic creation and rejection on conflict are proposed defaults. No actual directory or lifecycle was supplied.

| Acceptance | Positive | Failure | Boundary | Surface and confirmation |
| --- | --- | --- | --- | --- |
| A1 | Submitting a valid batch creates one durable user per data record within the authorized scope, with the imported identity and ordinary new-user defaults. | Any validation rejection creates zero users and leaves existing accounts unchanged. | Both one-row and multi-row files are valid. CSV input cannot assign privilege or override account lifecycle defaults. | TC-4. Submit GS and GQ on isolated baselines. Reload ordinary user management and independently read authoritative records for exact new identities, scope, assigned role/state and untouched baseline. |
| A2 | Distinct, available identities may be created in the batch. | Repeated identities in the file or identities that already exist in the directory's uniqueness scope reject the entire batch. Report affected logical records without disclosing protected directory details. | Equivalence uses the directory's actual uniqueness rule, including any normalization and reservations. | TC-5. Submit GD and GX. Assert conflict locations, zero new identities and unchanged existing records. Add an equivalence pair when the policy is confirmed. |
| A3 | Nonconflicting concurrent imports may both commit. | If another creation wins a contested identity, the losing import creates zero of its rows and reports a conflict. | Simultaneous imports and ordinary user creations share the authoritative uniqueness constraint. The first successful commit wins. | TC-6. Order the commits explicitly at the actual write boundary, then reverse their order on a fresh baseline. Exercise both import vs. import and import vs. ordinary creation. Read the exact final identity set. |
| A4 | A successful result corresponds to a fully committed batch. | An authoritative abort after some rows have been staged leaves zero visible or durable users from the attempt and no orphaned required account records. | Failed delivery of the response after commit leaves the committed batch intact. R-4 governs recovery. | TC-8. Induce an abort after the first staged record of GS, and separately lose the response after both commit. Inspect the authoritative directory, required companion records and recovered result. |

**State and data.** The user authority owns persisted users and any required companion records. The import targets only new identities in the authorized scope. Before commit they are uncreated and existing users retain their attributes. At successful commit the whole authorized set is available through ordinary user management. At abort the directory is unchanged by that attempt. Import and ordinary writers share a single conflict rule. Created users follow normal user-data access, retention and deletion policy. Correct a failed batch and resubmit. An already committed batch is managed through normal account administration.

**User authority boundary.** Validate current account rules and uniqueness at the authoritative write boundary. Preserve unrelated fields, users and configuration. Ordinary admin read-back confirms commit and respects current read permissions. R-4 distinguishes pending, confirmed and ambiguous outcomes. Independent replication/cursor reconciliation is inapplicable to this contract unless a real dependency is discovered. R-5 owns import outcomes. Ordinary account events retain their existing owner.

**Open gap.** The directory owner must establish required attributes, uniqueness scope, archived/reserved identities, default role and account state, onboarding effects such as existing invite behavior, companion records, normal retention and whether the actual creation boundary can honor the proposed atomic contract. Confirm through primary platform documentation or an authorized isolated check before dependent planning. If normal creation has irreversible effects or the boundary cannot meet atomicity, reconcile the product policy with its owner before affected work. Normal defaults and effects have no imported override.

### R-4 — Report completion and recover an interrupted attempt

**Basis and delta.** Request (2026-11-21, “The incoming request”), “upload a CSV to bulk-create users”. Add feedback that distinguishes a selected file, submission, confirmed creation, confirmed rejection and an unknown outcome. Preserve ordinary account visibility and recovery. Attempt lifetime and recovery capability are unobserved.

| Acceptance | Positive | Failure | Boundary | Surface and confirmation |
| --- | --- | --- | --- | --- |
| A1 | Selecting a file shows Ready. Import shows Submitting with an accessible status, blocks repeat clicks and reports Created with the exact committed count upon confirmation. | A definitive rejection says no users were created and keeps the applicable correction visible. | A receipt of the request, a timer or a progress cue cannot produce Created. A definitive rejection may be followed by a fresh corrected attempt. | TC-4, TC-8. Hold the actual outcome, inspect the pending UI, then release success or confirmed abort and reconcile the message with directory state. |
| A2 | On timeout or disconnect after submission, show Outcome unknown and offer Check result when reachable. A refresh within the same authorized tab context can recover the original attempt reference and check it. | A status outage, missing receipt or pending work remains unknown unless the authority proves a final disposition. | Confirmed commit recovers its original count. A confirmed abort recovers zero. For an authorized originator, an expired reference reports that the original outcome can no longer be confirmed from that reference and directs the admin to ordinary user management. | TC-8. Drop the success response, refresh, check during an outage and again after recovery. Repeat with a confirmed abort and an expired reference. |
| A3 | Replaying the same valid attempt and same payload returns its authoritative outcome or pending state without a second batch. | Changing the payload under the same reference causes rejection without another write or change to the original result. | At most one commit per reference. An expired reference cannot start or commit work. After expiry the admin may start a fresh attempt, which still obeys R-3 uniqueness. | TC-8. Repeat the request while pending and after completion, change its payload, then replay after expiration and verify exact durable identities and outcomes. |
| A4 | The active form can clear or replace an unsubmitted selection. After submission, it may be left and recovered as above. | Leaving, closing or losing the response never produces a confirmation of cancellation or zero writes. | No post-submit cancel or promised unattended processing. Once a terminal result is confirmed it cannot regress because a delayed response arrives. | TC-2, TC-8. Clear before submit, navigate away after submit, restore the authorized context and deliver an old pending response after terminal confirmation. Inspect the directory and latest visible status. |

**State and boundary.** Before sending the CSV the active admin context obtains an attempt reference tied to authorization scope. That context retains only the reference needed for a same-tab refresh and clears it on dismissal, expiry, sign-out, scope switch or tab close. The authority binds the reference to one payload and serializes repeats. Authority-owned status contains the scope, owner, reference, minimal binding and outcome metadata. A confirmed Created result agrees durably with the user commit. A confirmed rejection means the attempt cannot subsequently commit. Status may retain a count or safe failure category. Detailed row diagnostics belong to the response of the active validation interaction and are cleared on dismissal, replacement or context change. If that response is lost, a confirmed rejection can direct the admin to submit a fresh file for details. At expiry existing users survive, the reference cannot authorize further processing or disclose a result, and the authority purges expired status under the confirmed policy. An authority failure fails safe without claiming zero. Current authorization applies again before sending any protected result.

**Open gap.** The runtime and directory owners must establish the request/commit boundary, how final results agree with writes across interruption or restart, and the validity period, purge deadline, retry window and per-context capacity. Verify using the actual runtime before dependent recovery or durability work. Until then the UI contract can distinguish unknown outcomes and provide a recovery affordance, with no claim of a verified recovery mechanism.

### R-5 — Protect import data and record safe operational outcomes

**Basis and delta.** Request (2026-11-21, “The incoming request”) introduces personal data handling and privileged writes. Add only import-specific diagnostic coverage and lifecycle controls. Preserve ordinary authentication logs, directory policy and account visibility. The actual logging and retention facilities have not been inspected.

| Acceptance | Positive | Failure | Boundary | Surface and confirmation |
| --- | --- | --- | --- | --- |
| A1 | Authorized operators can correlate import authorization denials, confirmed rejections and commits, and authority/recovery failures using the import attempt reference or a safe correlation identifier. Each definitive outcome is attributable to the import authority. | Diagnostic sink failure preserves the original business disposition and never fabricates a commit or zero count. | A replay does not emit a second committed-batch outcome. Login coverage stays with the identity owner. | TC-10. Retrieve each event from the selected operational surface under an authorized operator, exercise a replay and a sink failure, and reconcile the event types and correlation with the independently observed business result. |
| A2 | User identity data is confined to the selected file and its active selection display, authorized processing and ordinary user records, subject to R-2 through R-4. | No raw CSV, file name, email or row value, password, token or session secret enters logs or durable import status. Other admins cannot access private attempt details. | Delete transient processing artifacts on terminal handling or authoritative abandonment. Expire and purge attempt status and operational records under their applicable policies. | TC-10, TC-7. Upload GV using its known values and file name, compare UI and directory visibility, inspect selected destinations and state using authorized fixture access, and verify cleanup after the agreed lifetime. |

**State and boundary.** The import authority emits restricted operational events with event category, scoped actor reference where known, safe correlation, time and aggregate outcome where applicable. Operators can read only under the existing operational authorization. Event data follows the selected facility's access, retention and deletion controls. Reuse verified existing coverage and extend it only for distinct import outcomes. A sink does not hold user or attempt authority, supply progress, or require a cache or incremental product read. Diagnostics cannot modify a business outcome. Audit requirements that would change this behavior need reconciliation before selecting the boundary.

**Open gap.** Operations/privacy owners must inspect actual event ownership and destination, access, mandatory audit rules, retention, deletion, event capacity and sink-failure visibility. Confirm redaction and retrieval in an isolated environment before the operational check. An access gap does not establish that existing coverage is absent.

## Non-functional requirements

| Quality and conditions | Observable criterion or open bound | Verification |
| --- | --- | --- |
| Interface quality and accessibility (R-1, R-2, R-4) | Use a consistent spacing and type scale, coordinated light and dark palettes and one icon set. Design empty, ready, submitting, success, unknown and error states. At a narrow and a wide supported viewport the flow has no horizontal overflow, keeps Import or the recovery action reachable and wraps long filenames/errors. Visible keyboard focus and text/control contrast satisfy applicable WCAG 2.2 AA success criteria 1.4.3, 1.4.11 and 2.4.7. Use motion only to clarify a change and honor reduced motion. | TC-11. Render all states and both themes, inspect layout with long content including keyboard-only operation, measure contrast, and repeat the transition with reduced motion. Confirm actual supported viewports during planning. |
| Capacity, latency and resource use (R-2 through R-5) | Bound file bytes, data records, field/processing resources, concurrent attempts, time to authoritative resolution and retained state. Establish supported workload and product bounds inside verified runtime limits. Unresolved. Oversize and capacity rejections must be legible and side-effect free. | TC-9. Check below, at and above approved admission bounds and exercise expected concurrent workload and timeout/recovery under the selected target. |
| Reliability and integrity (R-1, R-3, R-4) | At the real commit boundary, concurrent or retried requests preserve identity uniqueness and the batch invariant. A lost response cannot yield a false final result. | TC-6, TC-8. Use controlled ordering and interruption, then compare authoritative records to the reported outcome. |
| Security, privacy and operability (R-1, R-5) | Authority and isolation remain effective during scope change, revocation and outage. Verify safe event coverage and removal at agreed deadlines. Retention deadlines, regulatory applicability and any mandatory audit behavior are unresolved. | TC-1, TC-7, TC-10. Check the actual permission boundary, authorized event retrieval, redaction and purge. |
| Compatibility and service targets | CSV interoperability is the R-2 contract pending schema confirmation. The actual admin client, supported browsers/devices and runtime remain open. A separate public API, offline operation, migration, cost budget and availability SLA have no basis in this request. | Confirm supported admin surfaces and run consumer cases there. No standalone SLA, offline or migration check is required for this scope. |

**Visual starting point.** Follow [Light expressive starting point](../GUIDES/platforms/ui.md#light-expressive-starting-point), which names the light Google Gemini look and feel and Material 3 Expressive principles. Assume a web admin surface. For a new web screen start light with a dark option. Inherit established product identity, appearance policy and platform conventions if identified. Favor an airy composition, tonal layers and a clear primary action, adapting the reference to User Administration. Confirm host tokens, available primitives and viewport conventions before choosing the concrete visual treatment.

**Interaction and components.** The file chooser, format guidance, primary Import action, inline issue list and persistent outcome/recovery panel are the working components. Keep the live status accessible without moving focus on every update. Error summaries lead to actionable issues, and a keyboard user can reach the chooser and recovery action in reading order. Keep selection and result associated with the active attempt so a late update cannot replace a newer draft. An unresolved attempt occupies the current form until it resolves, expires or the admin leaves that context. The panel gives the current task and next action visual priority. Status and errors use text as well as color.

## Behavior model and verification evidence

### Flows and transitions

| Flow | Ordered interaction and outcome |
| --- | --- |
| F-1 — Open and prepare (R-1, R-2) | The admin opens the user-management import entry. The authority grants access or denies entry (T-1). The admin chooses, replaces or clears a file in the form (T-2). |
| F-2 — Submit and create (R-1–R-5) | The admin presses Import. The scope and attempt are checked before the file is evaluated (T-3). The authority accepts one complete, eligible file for validation, rejects invalid content (T-4), then either commits the complete user set and confirms it (T-5) or definitively rejects it (T-4). The UI waits for a confirmed result. An interrupted response enters F-3. |
| F-3 — Resolve ambiguity (R-1, R-3–R-5) | The originating authorized admin checks the attempt after uncertainty or refresh (T-6). An identical submission remains bound to that attempt (T-7). Expiry closes the attempt and UI context loss clears protected presentation state (T-8). |

| Transition | Before, trigger and guard | After, observation and recovery | Cases |
| --- | --- | --- | --- |
| T-1 / F-1 / R-1 | Admin requests access with current authority for the selected scope. | Open empty form. Unauthorized entry is denied without import state or writes. | TC-1 |
| T-2 / F-1 / R-2, R-4 | Authorized form is empty or ready and no submission has started. Admin chooses, replaces or clears. | Ready with current filename, or empty with Import unavailable. Directory is unchanged. | TC-2 |
| T-3 / F-2 / R-1, R-2, R-4 | Ready context explicitly submits with a valid scoped attempt and current authority. | Submitting while the authority resolves the request. A repeat click has no new effect. Missing permission is denied without writes. Interrupted delivery is resolved by T-6 when definitive response is unavailable. | TC-1, TC-2, TC-8 |
| T-4 / F-2 / R-2–R-5 | Authority can prove invalid input, revocation, conflict or abort and prevent future commit of this attempt. | Terminal rejection with zero creates. The authorized admin can start a new attempt. Denied actors receive no protected details. If final disposition is uncertain use T-6. | TC-3, TC-5, TC-6, TC-8, TC-9, TC-10 |
| T-5 / F-2 / R-1, R-3–R-5 | Complete valid input, live attempt, current authority and available identities at the write boundary. | Commit full batch and matching durable outcome. Report exact count on confirmation. A lost response goes through T-6. | TC-4, TC-6, TC-8, TC-10 |
| T-6 / F-3 / R-1, R-4 | Response missing or interrupted, or admin checks an available reference in the original authorized context. | Unknown until an authoritative final result is available. Once final, no stale reply may regress it. Denied actors learn no result. | TC-7, TC-8 |
| T-7 / F-3 / R-3, R-4 | Submission repeated against a live attempt bound to the original payload. | Same payload converges on the original outcome. A different payload is rejected without mutation. | TC-8 |
| T-8 / F-3 / R-1, R-4, R-5 | Context closes or changes, or attempt reaches its expiry. | UI clears old protected state. Expired attempt cannot write or reveal results. Committed users persist under normal rules. | TC-7, TC-8, TC-10 |

Only unsubmitted selection can be cleared as cancellation. A submitted attempt can complete, abort, or be unresolved to the consumer until check or expiry. No import-specific migration, undo, ongoing synchronization or subscription lifecycle is required. Changes to external account lifecycle and audit behavior depend on the open findings in R-3 and R-5.

### Concrete fixtures

Fixture contents use `\n` for LF, `\r\n` for CRLF, `[BOM]` for bytes EF BB BF and `[FF]` for a single hex FF byte. All other characters inside the code spans are literal. Name each file with the fixture ID and `.csv` unless a case says otherwise.

| File | Contents |
| --- | --- |
| GS | `email\nada@example.com\nbea@example.com\n` |
| GQ | `[BOM]"email"\r\n"cy@example.com"` |
| GE | `email\n\n` |
| GH | `email,role\nada@example.com,admin\n` |
| GQX | `email\n"ada@example.com\n` |
| GM | `email\nada@example.com,extra\n` |
| GB | `email\n[FF]\n` |
| GV | `email\nada@example.com\n\nnot-an-email\n""\n   \n` |
| GF | `email\nada@example.com\n""\n` |
| GD | `email\nada@example.com\nada@example.com\n` |
| GX | `email\nold@example.com\nbea@example.com\n` |
| GY | `email\nbea@example.com\ndev@example.com\n` |
| GT | `email\n"ada@example.com""x"\n"bea@example.com\ncontinued"\n` |

For each independent scenario, start with a fresh logical directory. Scope Alpha contains `old@example.com` with display label `Original` and ordinary role. The identities in GS, GQ and GY are unallocated within the applicable uniqueness scope. Admin `alex` may create/read users in Alpha. Admin `pat` has the same Alpha permissions, admin `lee` has them only in Beta, member `sam` may sign in to Alpha without admin/create permission, and an anonymous reader has no session. Fixtures assume the working email-only schema and ordinary account rules that accept the simple example addresses and reject GV/GT values. For TC-7 and TC-8 call the attempt for GS `I-100`, an abstract label for the reference issued per scenario. Pat observes Alpha through ordinary user management or its authoritative directory-view check, including when Alex no longer has permission. The authorized administrator or a controlled identity fixture supplies revocation. The actual revocation route and exerciser are open under R-1. No actual test identities or runtime are available here.

### Spec replay and remaining checks

This is a manual rule walk through the stated logical fixtures. It checks actor reachability, guards, state change and the consumer's expected observation. Product behavior is unverified. Unless a case states otherwise, Alex opens the authorized Alpha entry (T-1), selects the specified file (T-2), then presses Import (T-3). Start with a fresh fixture for each independent branch.

| Case and method | Recomputed expected observation and evidence limit |
| --- | --- |
| TC-1 — Walk admin entry, direct entry/submit by Sam, Lee-in-Alpha and anonymous, and revoke Alex after GS validation but before the write guard. | Alex can reach the authorized form. Others cannot establish authorized Alpha entry or submit. For Alex's revoked request, the T-5 current-authority guard fails. T-4 leaves only Old for Pat to observe. Alex cannot read protected results after revocation. Check the actual role mapping and ordering before running. |
| TC-2 — Select GS, replace with GQ, clear it, then select GS again. Press Import and interrupt upload immediately after the bytes `email\nada@example.com\n` of GS, before message completion. The prefix would be a valid one-row file if delivered as a complete upload. | Before pressing Import, T-2 changes only the displayed selection, then disables Import at clear. T-3 cannot treat the incomplete stream as a full file. If the response is delivered, it gives an upload failure. If the response is lost, the UI shows unknown. Neither branch creates a user. |
| TC-3 — Decode each fixture and apply syntax, header, row and field guards. | GS has two valid data records. GQ has one. GE has zero. GH fails the header, GQX quoting, GM record width at 2, GB encoding, even with its .csv filename. GV yields invalid email at records 4–6, with empty record 3 skipped, and GF fails record 3. GT decodes to ada@example.com"x at record 2 and bea@example.com followed by LF and continued at record 3. Both fail field validation. Negative files reach T-4 with zero creates. |
| TC-4 — Walk GS and GQ independently, hold the response before T-5 completes and read Alpha after confirmation. | GS adds Ada and Bea for a count of 2. GQ adds Cy for a count of 1. Old remains Original with its original role in both cases. Submitting persists until confirmation. Account companion fields and defaults require the actual directory contract. |
| TC-5 — Walk GD and GX separately. Compare with Alpha before and after. | GD conflicts at records 2 and 3. GX conflicts at record 2 against Old. T-4 leaves Alpha with only Old. In GX, Bea must be absent despite being a valid row. Normalization-equivalence case NOT-REPLAYED: canonicalization rules are open. |
| TC-6 — In two Alpha contexts Alex and Pat submit GS and GY before either has committed. Let one commit first, then allow the second final guard. Repeat in reverse. | GS first leaves Old, Ada and Bea. GY first leaves Old, Bea and Dev. In both orders the second operation hits T-4 and none of its exclusive rows appear. The ordinary-create contention case is NOT-REPLAYED: the ordinary create entry and setup are absent. Verify nonconflicting concurrency using GS and GQ, which by T-5 can leave Old, Ada, Bea and Cy. |
| TC-7 — Alex completes GS. Check I-100 first as Alex, then as Pat, Lee and Alex after revocation. In a fresh authorized flow delay the result while Alex signs out or switches context. | A currently authorized Alex receives count 2. Pat, Lee and revoked Alex receive no result or existence signal. The old response cannot populate the replacement context. The actual scope switch fixture is NOT-REPLAYED: its product entry point is unknown. |
| TC-8 — For GS, repeat I-100 with GS while pending. Let T-5 commit and drop the original response. Navigate away, return and refresh within the same authorized tab. Interrupt the first Check result, restore authority reachability, then check again. Repeat I-100 with GS and with GQ, whose identity is still available. In a fresh run without refresh, interrupt the submit reply to enter Outcome unknown. Hold the pending reply to Check result, allow T-5 to commit, obtain the confirmed result through a subsequent check and release the older reply. On a separate fixture, stage Ada, interrupt the submit reply and check result before a final receipt exists. Then trigger an authoritative abort and check again. | Pending and the interrupted check cannot report a final result. Recovery returns 2 and Alpha contains Old, Ada and Bea. Identical replay has no new effect. GQ under I-100 receives an attempt-payload mismatch, the original result remains 2, and Cy remains absent. Terminal confirmation does not regress. Before the staged abort, the check with no final receipt remains unknown. After the definitive abort only Old exists and the confirmed count is zero. Expiration and restart scheduling are NOT-REPLAYED: the runtime, expiry parameters and controlled observation route are absent. |
| TC-9 — Check the independent upload limit boundaries. | NOT-REPLAYED: runtime and accepted bounds must be known to construct the fixtures. |
| TC-10 — Inspect safe event coverage, redaction, retrieval, suppression of duplicate business outcomes, sink failure and purge. Use denied Sam submission, rejected GV and successful GS in isolated scenarios. | The spec predicts denial, rejection and commit respectively, with no raw fixture data or filename in an event and no second committed-batch outcome on identical replay. Event retrieval, sink failure and deletion are NOT-REPLAYED: no destination, operator route or retention policy was supplied. |
| TC-11 — Inspect the rendered flow across states and themes with keyboard and reduced motion. | NOT-REPLAYED: the rendered surface and supported client range are absent. |

The future checks compare exact identities, role/scope and durable state against independently chosen fixtures. UI labels, attempted writes and count-only assertions do not establish creation. A failure check must establish that valid companion rows were also excluded and the original record retained its attributes. A setup observation becomes stale if identities, permissions, fixtures or the environment change. The standalone stage uses no runtime capability claim, executable command or product check result as evidence.

## Submission

### summary

Proposed behavior for admin CSV upload and durable bulk user creation is specified. Working defaults are an admin user-management web entry, an explicit Import action, an email-only UTF-8 CSV, an all-or-nothing batch with duplicate rejection, the ordinary low-privilege new-user defaults, and scoped attempt recovery without saved uploads or an import-history feature. These defaults are assumptions, with the actual creation policy and runtime open.

Open prerequisites under R-1 through R-5 affect authorization integration, the schema, commit and account side effects, attempt recovery, retention and operational coverage. Work independent of those gaps can proceed. No material conflict is established. A conflict between normal account side effects or runtime capabilities and atomic creation, or between mandatory audit policy and diagnostic failure behavior, requires owner resolution before dependent work.

All product checks are pending. The implementation owner establishes runtime and fixture access before dependent planning. The system-test owner exercises the actual boundaries and UI at system test once supplied. Product acceptance may leave one primary outcome unverified only with a passed lower-layer test supporting that outcome. If any verification is person-only, record the named responsible person and keep it open and unverified, due at handoff or the stage its external effect gates. Reconcile incompatible later findings through the existing spec correction route and carry forward unaffected clauses.

### primary

- R-1 — authorized admin access
- R-2 — upload a CSV
- R-3 — create users in bulk

### evidence_refs

- [KNOWLEDGE/spec.md](spec.md), especially [scope and source](#scope-and-source), [non-functional requirements](#non-functional-requirements) and [spec replay](#spec-replay-and-remaining-checks).
- R-1 — `KNOWLEDGE/spec.md#r-1--restrict-imports-to-authorized-admins`, A1–A3.
- R-2 — `KNOWLEDGE/spec.md#r-2--accept-a-csv-and-explain-validation-failures`, A1–A4.
- R-3 — `KNOWLEDGE/spec.md#r-3--create-the-batch-without-modifying-existing-users`, A1–A4.
- R-4 — `KNOWLEDGE/spec.md#r-4--report-completion-and-recover-an-interrupted-attempt`, A1–A4.
- R-5 — `KNOWLEDGE/spec.md#r-5--protect-import-data-and-record-safe-operational-outcomes`, A1–A2.
- User request dated 2026-11-21, “The incoming request”, quoted under [Scope and source](#scope-and-source).
- [Guide map](../GUIDES/README.md), [Current-system baseline handoff](../GUIDES/current-system-baseline.md#planning-and-review-handoff), [Requirements definition and state/data assessment](../GUIDES/requirements-definition.md).
- [Behavior model](../GUIDES/behavioral-requirements.md#behavior-model), [Traceability and review](../GUIDES/behavioral-requirements.md#traceability-and-review), [Interaction design](../GUIDES/behavioral-requirements.md#actors-channels-and-state-ownership).
- [Service discovery](../GUIDES/service-discovery.md#verification), [Stage readiness and unverified obligations](../GUIDES/testing-and-documentation.md#stage-readiness-and-completion).
- [UI visual direction](../GUIDES/platforms/ui.md#light-expressive-starting-point), [WCAG 2.2](https://www.w3.org/TR/WCAG22/).
- [Architecture decisions](architecture.md#decisions), covering unresolved runtime choices.
