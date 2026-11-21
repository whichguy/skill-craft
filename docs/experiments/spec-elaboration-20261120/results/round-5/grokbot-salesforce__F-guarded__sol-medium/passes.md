## Pass 1 — The ground

Identified the Salesforce user, guest, administrator and provider. Wrote nine flows covering first and repeated use, input boundaries, service failure, access, initial setup, stop and recovery, diagnosis and backout. Added the first fourteen clauses. Found no project source, org baseline, named target or existing bot in the workspace.

## Pass 2 — Prerequisites and meaning

Traced the request and C-1 through C-14 through org selection, discoverability, access, provider setup, input validation and the meaning of repeated use. Fixed the minimum viable edition, initial availability, text boundary and context window as choices. Found no basis for a named org, an account-specific model ID, a public channel or a required design.

## Pass 3 — Interactions

Walked the bot view, prompt, pending attempt, terminal result, grant, session, enabled state, credential, selected model, provider and active revision through their relevant overlaps. Added repeat and late-result handling, separate views, departure, access changes during a request, rotation and failed lifecycle changes. Found no scheduled work, record hooks or persisted history with which to coordinate these events.

## Pass 4 — Runtime rules

Checked official Salesforce and xAI references. Added outbound authorization, provider authentication, conditional Apex entry and credential rules, platform callout and transaction limits, provider context and rate limits, retention and the conditional production release gates. Marked team- and model-specific values unconfirmed. Found no synchronous-only requirement or requirement to ship beyond development.

## Pass 5 — Existing behavior and invariants

Added preservation clauses for records, access, sign-in policies, automation, navigation and integrations. Checked what can leave the org, what can run, where credentials can appear and what survives a conversation. Found no named org customization, historical transcript or prior bot data format to migrate.

## Pass 6 — Builder review

Found decisions missing from the first full reading. Added the wait, transcript and display bounds, completion rules, malformed input handling, failure classification, recovery actions and a live verification criterion. Fixed a billing reference and spelled out the whitespace character set. Found no need for exact message wording or ordering of unrelated interface controls.

## Pass 7 — Lifecycle and remaining interactions

Separated update rollback from removal. Specified the fate of grants, settings, open views and pending replies after backout or replacement. Clarified who may see validation feedback, which refusals create no transcript entry, and what happens when a browser reconnects or the selected model goes away. Found no existing external channel, shared transcript or cross-org deployment to preserve.

## Pass 8 — Cross-clause review

Found gaps in context timing at eviction, administrative readback, failed setting edits and the precedence of overlapping admission failures. Added those decisions, the derived outbound text bound, the absence of a separate product quota and the conditional relevant-tests release gate. Clarified the outcome after browser connection loss and the scope of internal user access. Found no reason to specify a separate setup UI, quota system or public API.

## Pass 9 — Backout and acceptance review

Found that keeping access and provider settings on rollback did not yet cover a successful update, and that restoring a revision could be read as reactivating old views. Covered both. Moved the derived outbound text bound to its own clause and removed arbitrary ordering among simultaneous non-access blockers. Found no additional role or settings migration after removal.

## Pass 10 — Submission and context review

Closed two ambiguities. The bot includes every eligible pair up to the four-pair window, and delivery of the same submission twice is distinct from a fresh Send of identical text. Found no new requirement for a shared queue, cancellation at xAI or conversation recovery after leaving the view.

## Pass 11 — Final full pass

Read from the first user flow through the final clause. Checked first use and follow-up context, zero and maximum text, overlapping sends and failures, access changes, provider limits, admin recovery, updates and rollback, existing org behavior and data boundaries. Checked for hidden choices, unobservable acceptance conditions, missing numeric bounds, unclear state endings and broken references. Verified sequential numbering and the required fields for every entry. This pass found no further behavior a builder needed to infer or correct.
