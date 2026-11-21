# Grok Bot for Salesforce: product specification

Living specification of the Grok Bot, a conversational assistant inside a Salesforce development org that answers
with xAI's Grok model. Requirement IDs are `R-<n>`; structure and technology choices are `AD-<n>` in
[architecture.md](architecture.md) and never appear here as requirements.

Status of this document: **proposed**, written by the spec stage from the request alone. Nothing here has been
built, deployed or run. Every "pending" item below is planned, not evidenced.

## Request, basis and interpretation

- **Request (2026-11-20):** "Create a Grok bot in a Salesforce development org."
- **Basis tag for every R-<n> below:** `REQ-2026-11-20` (the request's words, dated) unless a line cites an `A-<n>`
  assumption or a platform rule `P-<n>`.
- **Baseline:** none. No earlier spec, no repository, no discovery or research result, and no org inspection exist
  (nothing ran before this stage). Everything the org already holds is **unknown**, not absent (see G-3).
  All R-<n> are therefore `add`; nothing is preserved, modified or retired. `## Retired` is empty.
- **Interpretation (A-1):** "Grok" is xAI's model family. A "bot" is an interactive conversational assistant that
  answers typed questions. "In a Salesforce development org" means it is built from deployable Salesforce metadata
  (Apex, Lightning Web Component, Named/External Credential, custom metadata, tab, app, permission set) and
  deployed to a non-production development org the user authorises. The bot is used by Salesforce users inside
  Lightning Experience. Other readings (a Slack/Teams bot, an Agentforce agent, a bot that reads or updates CRM
  records, an inbound webhook bot) are **out of scope** unless the user says otherwise.
- **Request outcomes (O-n) and where they are accepted:**

| Outcome | Meaning | Accepted by |
|---|---|---|
| O-1 | A bot exists in the dev org as deployed metadata, reachable by an authorised user | R-1, R-12, R-13 |
| O-2 | It is a Grok bot: replies come from xAI Grok, not canned text | R-2, R-7, R-8 |
| O-3 | A user can hold a conversation with it | R-2, R-3, R-4, R-5, R-6, R-10 |
| O-4 | It is safe to leave in a dev org (key, data, access) | R-7, R-9, R-11 |

## Assumptions (defaults taken unattended; each is the user's to overturn)

- **A-1** Interpretation above.
- **A-2** Chat only: the bot sends the user's typed text (plus the conversation so far) to Grok. It sends **no
  Salesforce record data** and has no tools or record actions. Grounding on CRM data is a separate future request.
- **A-3** Conversation history lives only in the browser component (memory). Nothing is stored in the org. A page
  refresh or navigation away ends the conversation.
- **A-4** Defaults held as admin-editable configuration (R-8): `MaxInputChars` = 4000, `MaxHistoryMessages` = 20,
  `MaxOutputTokens` = 1024, `TimeoutSeconds` = 60. They are product defaults, not measured; they sit inside the hard
  platform bounds P-3/P-4. The user may change them.
- **A-5** No automatic retry of a failed Grok call (a retry would silently spend a second paid call). The user
  retries by hand.
- **A-6** No streaming. Replies appear whole when complete (reason: P-2/AD-3).
- **A-7** English-language UI strings; the model answers in whatever language the user writes.
- **A-8** One shared xAI API key for the org (a named principal), billed to whoever owns the key. Per-user keys are
  out of scope.
- **A-9** Users who may use the bot are whoever an admin assigns the permission set `Grok_Bot_User`. No other
  sharing model is added.

## Platform rules the behaviour cannot escape (P-n; source in `evidence_refs`)

| ID | Rule | Forced behaviour |
|---|---|---|
| P-1 | An Apex transaction may make at most 100 callouts. | The bot makes exactly one callout per user turn (R-2, R-5). |
| P-2 | A single callout timeout is 1 ms to 120,000 ms (default 10 s); cumulative callout time per transaction is at most 120 s. Apex callouts are synchronous request/response. | R-8 timeout must lie in 1..120 s and default 60 s; no streaming (A-6); a slow Grok is a timeout error (R-6). |
| P-3 | Synchronous Apex heap is 6 MB (asynchronous 12 MB); sync CPU 10 s. Values come from an older docs version and are **to re-verify** against the org's API version. | Reply size is bounded by `MaxOutputTokens` (R-8); an oversized body is the "unreadable reply" error (R-6), not a crash. |
| P-4 | Callouts need an endpoint registered in the org (Named Credential or Remote Site) and are not made in Apex tests; tests must use `Test.setMock`. | R-7 uses a Named Credential; Apex tests never touch xAI (NFR-8). |
| P-5 | A secret in an External Credential is stored by the platform and is not returned by metadata retrieve. | The key cannot ship in source; entering it is a person-only step (G-1, R-7). |
| P-6 | Apex class, LWC and tab API names are org-wide (LWC in namespace `c`); a tab or app is visible only through a profile or permission set that names it. | R-1, R-13: names are checked against the org before use; visibility is granted by permission set, not assumed. |
| P-7 | Apex classes `with sharing` do not by themselves enforce CRUD/FLS; an `@AuraEnabled` class is callable only by users granted access to the class. | R-11: sharing, object CRUD, FLS are stated separately; here no record is read, so class access is the gate. |
| P-8 | Deploys to production-type orgs require Apex test coverage (75% org-wide, per-deploy rule); applicability to a developer-edition org is **unverified**. | NFR-8 targets at least 75% on the bot's Apex regardless; whether the org gate applies is checked at release (G-5). |
| P-9 | No DML may precede a callout in the same transaction (older docs; a newer version relaxes it). | The controller performs no DML at all (R-9), so the rule cannot be hit. |

## Requirements

Acceptance-line format: **P** positive, **F** failure, **B** boundary; `Surface` is where it is observed; `Confirm`
is how. `n/a: reason` where a kind adds nothing. "Mock" means an Apex `HttpCalloutMock` / Jest stub; "Live" means the
real xAI endpoint with the real key (blocked until G-1 is resolved, so every Live line is **NOT-REPLAYED** today).

### R-1 Entry and access
**Behaviour.** An authorised user finds a tab "Grok Bot" in Lightning Experience (App Launcher, and the direct path
`/lightning/n/Grok_Bot` once names are confirmed free, G-3) and sees the chat component. A user without permission
set `Grok_Bot_User` (A-9) has no tab, and cannot call the bot's Apex even by crafting a request.
**Basis:** REQ-2026-11-20 "Create a Grok bot", O-1; A-9; P-6, P-7. **Change:** add. **Source locators:**
`GUIDES/platforms/salesforce.md#service-discovery`, `#consumer-entry-access-read-only-probe`.
**Evidence limit:** org users, profiles and existing permission sets are unknown (G-2).
**Pending:** tab, app and permission-set metadata; access check at release.
- **P1** Setup: user U1 has `Grok_Bot_User`; U2 has none. U1 opens `/lightning/n/Grok_Bot`: the chat renders with an
  enabled composer. Surface: Lightning UI as U1. Confirm: browser check at release-verify (org-dependent; pending).
- **F1** U2 opens the same path: page does not exist / tab absent in App Launcher. U2 invoking the controller
  (anonymous Apex or direct Aura call as U2) is refused with an access error and **no callout is made**.
  Surface: UI as U2; Apex test `System.runAs(U2)`. Confirm: Apex test (mock asserts zero callouts) plus a read-only
  `SetupEntityAccess` probe.
- **B1** Permission set unassigned from U1 while the tab is open: the next send fails with an access error shown in
  the UI (R-6 category `ACCESS`); no stale access persists. Surface: UI then Apex. Confirm: Apex test (runAs a user
  after removal) and manual step.

### R-2 Ask Grok and read the answer (primary)
**Behaviour.** The user types a message and sends it (button or Enter); the component calls the controller, which
makes one callout to Grok and returns the assistant text; the component appends the user message and then the reply to
the visible transcript, in that order.
**Basis:** REQ-2026-11-20 O-2, O-3. **Change:** add. **Locators:** AD-1, AD-2. **Evidence limit:** the live xAI
request/response schema and model name are only documented, not probed (G-1, G-4).
**Pending:** controller, component, mock tests.
- **P1** Mock returns the xAI-shaped reply `"Paris."` for input `What is the capital of France?`: transcript shows
  two entries, user then assistant, assistant text exactly `Paris.`. Surface: Jest on the component with the Apex
  method stubbed; Apex test asserting the parsed return value from a mocked HTTP 200 body. Confirm: both tests.
- **P2 (Live)** With the real key and the same input, a non-empty reply arrives and is shown. Surface: deployed tab.
  Confirm: browser check; **NOT-REPLAYED** (key, G-1).
- **F1** The callout returns an error: no assistant entry is appended; R-6 governs the message.
- **B1** Reply with `finish_reason` meaning length-truncated: the reply is shown and marked "(reply was cut off)".
  Confirm: Apex test with a mocked truncated body; Jest on the marker.
- **B2** Reply content empty string/absent: treated as the R-6 `BAD_REPLY` error, not an empty bubble.

### R-3 Multi-turn context
**Behaviour.** Each send includes the preceding conversation (completed user/assistant turns, oldest first, capped to
the newest `MaxHistoryMessages`, A-4) so Grok can answer follow-ups. The system prompt (R-8) is prepended and is not
counted against the cap. Failed turns (R-6) are not part of history.
**Basis:** O-3; A-3, A-4. **Change:** add. **Evidence limit:** how xAI tokenises/limits context is not probed.
**Pending:** history builder, tests.
- **P1** Turn 1 `My name is Sam.` → reply `Hi Sam.`; turn 2 `What is my name?`. The turn-2 request body's messages,
  in order, are: system prompt, user `My name is Sam.`, assistant `Hi Sam.`, user `What is my name?` (4 messages).
  Surface: Apex test inspecting the captured request in the mock. Confirm: Apex test.
- **B1** Cap: with `MaxHistoryMessages`=20 and a conversation of 25 completed messages plus the new one, the body
  contains the system prompt, the newest 20 history messages and the new message (22); the oldest 5 are dropped. The
  visible transcript still shows all 25 (cap affects the request, not the display). Confirm: Apex + Jest.
- **B2** Cap = 0: only system prompt and the new message are sent (stateless mode).
- **F1** A failed turn 2 (R-6) followed by a successful turn 3: turn 3's history contains turn 1 only (turn 2's
  user text was not answered; it is not sent as an orphan). The user's failed text stays visible, flagged "not sent"
  with a retry action, and retry resends it as the new message. Confirm: Jest + Apex.

### R-4 Input validation
**Behaviour.** Empty or whitespace-only input cannot be sent; input longer than `MaxInputChars` is rejected before any
callout, with a message stating the limit. The server re-validates (the client is not trusted).
**Basis:** A-4; the request leaves input rules unsaid. **Change:** add.
- **P1** `Hi` (2 chars) is accepted.
- **F1** `""` and `"   \n "`: send control disabled in UI; direct controller call returns `INVALID_INPUT`, zero callouts.
- **B1** Exactly 4000 chars accepted; 4001 rejected with "Message is too long (limit 4000 characters)", composer
  text retained so the user can shorten it, zero callouts. Surface: Jest + Apex test. Confirm: both.
- **B2** Characters are counted as the platform counts UTF-16 code units in Apex `String.length()`; a message of
  4000 emoji exceeds the limit if its code-unit length exceeds 4000. The UI count and server count must agree (same
  definition) so the UI never accepts what the server rejects. Confirm: test with a 2001-emoji string (4002 units) is
  rejected on both sides.

### R-5 Pending state, repeats and supersession
**Behaviour.** While a request is in flight the composer's send is disabled and a visible, announced "Grok is
thinking" state shows. At most one request is in flight per open component. **Clear conversation** is available at all
times; if used mid-flight, the late reply is discarded and never appended to the new empty conversation.
**Basis:** O-3; `GUIDES/platforms/ui.md` (superseded results must not replace the latest state). **Change:** add.
**Evidence limit:** server-side the controller does not de-duplicate (a crafted double call makes two callouts; the
only guard is the UI and the per-user permission set); accepted, recorded in G-6.
- **P1** Click send then immediately press Enter: exactly one controller call occurs. Jest asserts call count 1.
- **F1** Clear during flight, then the original reply resolves: transcript remains empty; no error toast either.
  Jest with a deferred promise.
- **B1** The server answers after the user navigated away: the component is gone; nothing is stored (A-3); the
  callout cost is still incurred (cancellation does not undo a server effect). Documented, not testable beyond Jest
  unmount without error.
- **B2** Two browser tabs open: each has an independent conversation and independent in-flight state.

### R-6 Error behaviour (what the user sees when something fails)
**Behaviour.** Every failure ends the pending state, keeps the transcript, shows a message in the conversation area
(not only a transient toast) and offers retry. Error categories and user text; none shows a secret, a stack trace,
raw xAI body or the key; each carries a short correlation ID (R-12):

| Category | Trigger | User message |
|---|---|---|
| `DISABLED` | kill switch off (R-8) | "Grok Bot is turned off by your administrator." |
| `ACCESS` | no class access / permission revoked | "You don't have access to Grok Bot." |
| `INVALID_INPUT` | R-4 | the R-4 messages |
| `NOT_CONFIGURED` | credential missing/unauthorised (callout cannot start), bad config (R-8) | "Grok Bot isn't set up yet. Contact your administrator. (ref abc123)" |
| `AUTH` | xAI 401/403 | same text as `NOT_CONFIGURED` (user cannot fix it), admin sees the category in the log |
| `RATE_LIMIT` | xAI 429 | "Grok is busy right now. Try again in a moment." |
| `TIMEOUT` | callout exceeds `TimeoutSeconds` / `CalloutException` read timeout | "Grok took too long to answer. Try again." |
| `UPSTREAM` | xAI 5xx or network failure | "Grok is unavailable right now. Try again." |
| `BAD_REPLY` | 200 with unparsable/empty body, or body above heap-safe size | "Grok sent a reply I couldn't read. Try again." |
| `BLOCKED` | xAI 4xx other than 401/403/429 (e.g. 400 bad model, 413 too large) | "That request couldn't be processed. (ref abc123)" |

**Basis:** O-3; A-5; P-2, P-3. **Change:** add. **Evidence limit:** the exact xAI error bodies are documented only
partly; mapping is by HTTP status, never by parsing messages.
- **P1** Not applicable as positive path: see R-2. n/a: R-2 covers success.
- **F1** For each row, a mock returns the trigger (status 401, 429, 500, 400, 200 with body `{}`, a
  `CalloutException` "Read timed out"): the controller returns the stated category and the component shows the text.
  Confirm: Apex test per category; Jest per message.
- **F2** Sink check: no returned value, debug line or UI text contains the string of the API key used in the mock
  (`test-key-12345`). Confirm: Apex test asserting absence in returned message and captured log text.
- **B1** The correlation ID appears in the user text only for `NOT_CONFIGURED`, `AUTH`, `BLOCKED`, `UPSTREAM`.
- **B2** After any error the next send works without a reload (state not wedged). Jest.

### R-7 Credential and callout route
**Behaviour.** The API key is held by the platform (External Credential; Named Credential `Grok_API` pointing at
the xAI API host); Apex addresses the endpoint only as `callout:Grok_API/...`. The key is never in source,
custom metadata, custom settings, the browser, or logs, and a user can never read it. Which Salesforce users may use the
credential is limited by the External Credential principal's permission-set mapping to `Grok_Bot_User`.
**Basis:** O-2, O-4; P-4, P-5; A-8. **Change:** add. **Evidence limit:** the exact way to express an
`Authorization: Bearer <key>` header through the External Credential (custom header parameter vs. other protocol) is
documented for custom headers but not probed (G-4). The key itself is a person-only item (G-1).
**Pending:** credential metadata (without secret), person step to enter the key.
- **P1** With the principal mapped and a key entered, the `callout:` request carries the Authorization header
  (confirmed by Live P2 only; **NOT-REPLAYED**).
- **F1** Without the key (fresh deploy), a send yields `NOT_CONFIGURED`, no exception reaches the UI, and the log
  names the missing credential, not a value. Apex test with the credential-missing exception path mocked.
- **F2** Repo scan: no string matching the xAI key pattern (`xai-` prefix plus ≥20 alphanumerics) and no `.json`
  credential file in the source tree. Confirm: a repository grep check in the test suite.
- **B1** A user who has `Grok_Bot_User` but whose principal mapping is missing gets `NOT_CONFIGURED`, not `ACCESS`.

### R-8 Administrator configuration and turn-off
**Behaviour.** One custom-metadata record `Grok_Bot_Config.Default` holds: `Enabled__c` (checkbox, default true),
`Model__c`, `SystemPrompt__c`, `MaxInputChars__c`, `MaxHistoryMessages__c`, `MaxOutputTokens__c`,
`TimeoutSeconds__c` (defaults in A-4; model default unresolved, G-4). Admins edit it in Setup or by deploy; a change
applies to the **next** request (an in-flight request keeps the values it started with). **Dimension note:** these
are all the fields; a per-user toggle is **left out** (turn off for one user = unassign permission set, R-1/R-12).
Invalid values (non-numeric, ≤0, `TimeoutSeconds` outside 1..120, `MaxInputChars` above a documented ceiling set at
plan so request stays within P-3) fail closed to `NOT_CONFIGURED` rather than silently clamp.
**Basis:** A-4; P-2; the request leaves "how it is switched off" unsaid. **Change:** add.
- **P1** `Enabled__c=true`, defaults: bot works (R-2).
- **F1** `Enabled__c=false`: send returns `DISABLED` with **zero callouts**; the tab still opens and shows the
  disabled message at load (a status probe method, no callout).
- **F2** `TimeoutSeconds__c=0` and `=121`: `NOT_CONFIGURED`, zero callouts. `=1` and `=120` accepted (B).
- **B1** Config record missing entirely (e.g. deleted): `NOT_CONFIGURED`, not a null-pointer crash. Apex test.
- **B2** `Model__c` empty: `NOT_CONFIGURED` (no model, no default invented in code).
- **B3** Config edited between two turns of one conversation: turn 2 uses new values; history already shown unchanged.

### R-9 Data handling and privacy
**Behaviour.** Sent to xAI: system prompt, the user's typed messages, prior assistant replies (capped), and the
configured model/limits; **nothing else** (no user name, email, org ID, or record data). Stored in the org: none
(A-3): no transcript object, no DML (P-9). Logged: only metadata per request (timestamp, user Id, category, HTTP
status, latency ms, request/response character counts, correlation ID), never message text or the key. The component
shows, once and permanently visible near the composer, "Messages are sent to xAI."
**Basis:** O-4; A-2, A-3. **Change:** add. **Evidence limit:** xAI's own retention of API data and any
data-processing terms are **not assessed** here (G-7, owner: the user/org admin; matters before production use,
not for a disposable dev org holding no customer data).
- **P1** Request body fields (captured in mock) are exactly: `model`, `messages`, `max_tokens`-equivalent. No extra
  keys carrying identity. Apex test asserts the key set.
- **F1** Log capture shows the metadata fields and does not contain the input text `My name is Sam.`.
- **B1** Refresh: transcript gone, nothing recoverable (Jest unmount; org has no object to query: schema check shows no
  new custom object).
- **B2** The disclosure text is present in the rendered component in disabled and error states too.

### R-10 Message rendering safety and display limits
**Behaviour.** User and assistant text are rendered as plain text, escaped, newlines preserved, long unbroken tokens
wrapped; assistant output is never interpreted as HTML or script (Markdown rendering is out of scope, A-2 scope). Long
transcripts scroll; new content scrolls into view unless the user has scrolled up.
**Basis:** O-3, O-4. **Change:** add.
- **P1** Reply `Use <b>bold</b>` displays the literal characters `<b>bold</b>`, no bold element. Jest DOM assertion.
- **F1** Reply `<img src=x onerror=alert(1)>` creates no element and fires no handler. Jest.
- **B1** A 10,000-character unbroken reply causes no horizontal overflow at 320 px width. Browser check.
- **B2** 200 turns render and scroll without error (no virtualisation required; performance not bounded, see NFR-2).

### R-11 Sharing, object and field access
**Behaviour.** The controller reads and writes **no** Salesforce records, so sharing, object CRUD and FLS have no
data to protect; they are stated separately so a later change cannot inherit a false assurance: **sharing**: class is
`with sharing`; **object CRUD**: n/a (no object touched); **FLS**: n/a (no field touched); **who may call**: class
access via `Grok_Bot_User` (R-1). Any future record grounding (out of scope, A-2) needs its own requirement.
**Basis:** P-7, A-2. **Change:** add.
- **P1** Static check: controller source contains no SOQL/DML keywords. Test: a source-scan assertion.
- **F1** Caller without class access refused (R-1 F1).
- **B1** n/a: no records, no boundary.

### R-12 Operability: enable, observe, undo
**Behaviour.** An admin can (a) deploy additively, (b) verify it worked, (c) see why a request failed, (d) turn it off
for everyone (R-8) or one user (unassign), (e) remove it.
(a) Deploy adds metadata only and changes no existing org component (R-13).
(b) A documented post-deploy checklist: names present (`sf org list metadata`), tab visible to the assigned user,
a status probe says enabled and credential present, one Live prompt answered (**NOT-REPLAYED**, G-1).
(c) Each failed request writes one log line (R-9 fields) retrievable in Setup debug logs for the running user;
the same correlation ID is in the UI text (R-6).
(d) see R-8/R-1. (e) Undo: unassign the permission set, set `Enabled__c=false`, then a destructive deploy listing
exactly the bot's components; the key entry in the External Credential is deleted by the admin by hand.
**Basis:** the request leaves operation unsaid; Salesforce practice. **Change:** add.
**Evidence limit:** debug-log retrieval needs a trace flag set by an admin; durable audit is **not** provided (A-3,
G-6).
- **P1** Checklist (b) steps all return the expected result on a deployed org (pending; NOT-REPLAYED).
- **F1** After removal (e), a metadata listing contains none of the bot's names, and existing components are
  untouched (listing diff). Surface: org metadata listing before/after. Confirm: release-check.
- **B1** Re-deploy of the same source onto an org that already has it is idempotent: no change, no duplicate.
- **B2** Deploy where the External Credential already holds a key: the key is **not** overwritten or cleared.

### R-13 Naming, packaging and org targeting
**Behaviour.** All components use the prefix `Grok_Bot`/`grokBot` (Apex `GrokBotController`, LWC `grokBotChat`, tab
`Grok_Bot`, app `Grok_Bot_App`, permission set `Grok_Bot_User`, named credential `Grok_API`, custom metadata type
`Grok_Bot_Config__mdt`). Before first deploy, the org's existing metadata is listed and any clash is resolved by a
suffix; nothing existing is overwritten. The bot deploys only to the user-authorised development org alias
(unknown, G-2); nothing is deployed to any other org. No namespace/package (unmanaged source).
**Basis:** O-1; P-6; `GUIDES/platforms/salesforce.md#service-discovery`. **Change:** add.
- **P1** Metadata listing of `ApexClass`, `LightningComponentBundle`, `CustomTab`, `CustomApplication`,
  `PermissionSet`, `NamedCredential`, `CustomObject` (for `__mdt`) shows no pre-existing name equal to the above
  before deploy (NOT-REPLAYED: org access, G-2).
- **F1** A clash is found: the run records it and stops that component; it does not overwrite.
- **B1** Deploy validate (dry-run) is run before the real deploy and its result is read back (terminal status, not just
  an accepted job id).

## Non-functional requirements

Format: ID, operating condition, bound or criterion, verification, status. No bound is invented; where the platform
fixes one it is cited.

- **NFR-1 Latency.** Grok's own latency is outside this product's control; **no p95 target is set** (unresolved,
  needs the user's tolerance and a measured baseline, G-8). Hard bound: a reply wait never exceeds `TimeoutSeconds`
  (default 60 s, ≤120 s, P-2). The UI shows the pending state **before** the network call returns (same event tick).
  Verify: Jest (pending state synchronous after click), Apex timeout test.
- **NFR-2 Capacity/scale.** Concurrent users and request volume are not specified; limits come from the xAI account
  rate limit (unknown tier, G-8) and per-transaction governor limits (P-1..P-3; one callout per transaction). Excluded:
  load testing (dev org, no volume stated). Reopen if a user count is given.
- **NFR-3 Reliability.** Every failure class in R-6 degrades to a message with retry; no failure leaves the UI
  stuck pending (R-6 B2). No retries (A-5). Verify: Jest + Apex per category.
- **NFR-4 Security.** Key custody per R-7; escaped rendering per R-10; no record access (R-11); access only by
  permission set (R-1). No secret in logs (R-6 F2, R-9). Verify: Apex tests, repo scan, Jest.
- **NFR-5 Privacy/retention.** Nothing retained in the org (R-9); retention at xAI unassessed (G-7).
- **NFR-6 Accessibility.** WCAG 2.x AA contrast for all text and controls in both themes; composer and send reachable
  by keyboard; Enter sends, Shift+Enter inserts a newline; new reply announced through an `aria-live="polite"` region;
  pending and error states announced; focus returns to the composer after send and after Clear. Verify: Jest
  (roles/labels/live regions), browser keyboard walk, a contrast check of the token pairs.
- **NFR-7 Compatibility.** Lightning Experience in current evergreen browsers; works at 320 px and 1440 px with no
  horizontal page scroll. The API version of the metadata is set at plan to the org's current supported version (G-2).
  Verify: browser check at both widths.
- **NFR-8 Testability.** Apex tests use `HttpCalloutMock` and cover every R-6 category, R-3 history building, R-4 and
  R-8 boundaries; target ≥75% coverage of the bot's Apex (P-8); LWC Jest tests cover R-2/R-5/R-10 and NFR-6 semantics.
  A test passing proves only its own surface: org behaviour and the Live path need the deployed checks.
- **NFR-9 Operability.** R-12; correlation ID in UI text and log line.
- **NFR-10 Maintainability.** Config in custom metadata (R-8), no hard-coded model name or limits in Apex/JS;
  endpoint/API path isolated in one place (AD-2) so a provider API change touches one class.
- **NFR-11 UI quality (the deliverable has a UI).** Reference: **light Google Gemini look and Material 3 Expressive
  principles** from `GUIDES/platforms/ui.md#light-expressive-starting-point`, adapted to Salesforce: platform
  conventions (Lightning Design System, SLDS styling hooks) take precedence over the reference where they conflict.
  Starting appearance: light, with a dark variant that follows the org/OS theme. Observable criteria:
  1. One visual system: spacing and type scales and a palette defined once as tokens with light and dark values;
     distinct tonal surfaces for the transcript, user bubbles, assistant bubbles and composer; one restrained accent.
  2. One icon set (SLDS utility icons); no emoji as icons.
  3. Designed empty state (greeting plus 3 example prompts the user can click to fill the composer), loading
     ("Grok is thinking" with an animated indicator), error (R-6 messages inline with retry) and disabled/not-configured
     states.
  4. Primary activity strongest: readable message groups and a composer that stays reachable; narrow (320 px) and wide
     layouts, no horizontal overflow.
  5. Visible keyboard focus on every control; AA contrast (NFR-6).
  6. Motion only to explain change (message entry, pending indicator); `prefers-reduced-motion` removes it.
  7. One memorable signature element chosen at plan (recorded in the UI AD), e.g. a luminous accent edge on the
     assistant bubble.
  Verify: rendered browser check at 320/1440 px in both themes against the recorded choices; Jest for states;
  reduced-motion media query test. Status: pending. UI premises (components, interaction, skin) are carried to the UI
  AD at plan.

## State and data assessment

| State | Owner / location | Who may read | Simultaneous change | Ends / removed by | Quota |
|---|---|---|---|---|---|
| Conversation transcript and in-flight flag | LWC component memory in the user's browser tab (R-3, R-5) | that user only; sent to xAI per turn | two tabs independent; Clear supersedes in-flight | refresh, navigation, Clear | none in org; per-request size bounded by R-4/R-8 |
| Configuration `Grok_Bot_Config.Default` | org custom metadata (R-8) | admins edit; Apex reads | last save wins; applies to next request | admin delete (then `NOT_CONFIGURED`) | CMDT limits not binding |
| API key | External Credential, platform-held (R-7) | no user; Apex callout merges header only | admin re-entry replaces it | admin deletion | n/a |
| Permission set assignment | org (R-1) | admins | n/a | admin unassign | n/a |
| Request log line | Apex debug log (R-12) | admin/trace-flagged user | n/a | platform log retention | debug log size limits; durable audit absent (G-6) |

Resources touched by the bot at runtime: none changed beyond the above (no records). Target identities: dev org alias
unknown (G-2), user = authorised org user. Before/after invariant: org record data identical before and after any
conversation (R-9 B1). Recovery: no data to recover; undo path in R-12. Unknowns: existing org automation named
`Grok*` (G-3).

## Service boundary: xAI API (service-discovery contract)

- **Current authority:** the xAI account behind the key decides access; revocation takes effect on the next call
  (no cache, so freshness-versus-revocation is immediate; cache: **not applicable**, none introduced).
- **Incremental state:** none held at xAI by design: stateless per-turn requests with history supplied by the
  caller (xAI storage of requests: unverified, G-7).
- **Async completion/recovery:** synchronous call; no job, queue or polling (A-6). Unknown outcome (timeout after xAI
  processed the request) is surfaced as `TIMEOUT` and may have been billed; no reconciliation (A-5).
- **Owned event coverage:** one debug-log line per request with R-9 fields; provider-side usage lives in the xAI
  console (not owned here).
- **Evidence limit:** endpoint path, schema, model names and rate limits were read from xAI's public docs (search,
  not a probe). xAI marks the OpenAI-style Chat Completions route "legacy" and recommends a Responses route (AD-2);
  the live probe must settle this (G-4).

## Replay walk (item 10)

Case: R-3 P1 plus R-1 reachability. Actor U1 holds `Grok_Bot_User` (R-1: required start; the permission set is created
by this product and assigned by an admin, so the start is reachable only after that admin step, G-2). Action 1: U1
sends `My name is Sam.` (state: enabled, config valid, ≤4000 chars → permitted by R-4, R-8). Mock returns `Hi Sam.`.
History = [user, assistant] (2). Action 2: U1 sends `What is my name?` (permitted: not in flight, R-5; 2 ≤ cap 20).
Recomputed request messages = [system, user "My name is Sam.", assistant "Hi Sam.", user "What is my name?"] = 4,
matching R-3 P1. Observer: the Apex mock's captured request (visible to a test, not to the user). **Method: paper walk
against the rules above; no execution.** Any test or Live run is `NOT-REPLAYED` (no code, no key, no org access).
No command in this document was run; no `backchain-check` exists here (duty 11 omitted).

## Open gaps (G-n)

- **G-1** xAI API key: a person-only prerequisite (owner: the user; due before any Live check and release-verify).
  Until then all Live lines stay unverified; mock-based work proceeds.
- **G-2** Target dev org: alias, API version, whether the authenticating CLI session exists, the permission-set and
  user situation, and any existing names. Owner: user to authorise org access; due before deploy. Unauthorised
  access is not evidence of absence.
- **G-3** Name-clash check against the org's metadata (R-13); due at plan/release-plan.
- **G-4** Live probe of xAI: confirm endpoint (Responses vs. Chat Completions), request/response schema, a valid
  default model name for `Model__c`, how the Authorization header is expressed through External Credential. Owner:
  research/plan with the key; blocks `Model__c` default and R-7 P1 only.
- **G-5** Whether the Apex coverage deploy gate applies to this org type (P-8); checked at validate dry-run.
- **G-6** Server-side de-duplication and durable audit are intentionally absent; the user may ask for them.
- **G-7** xAI data retention/terms and approval to send org users' typed text to xAI. Owner: the user/org admin; a
  non-blocking item for a disposable dev org, blocking for production or customer data.
- **G-8** Latency target, expected users and xAI rate-limit tier unspecified; no number is invented.
- **G-9** Confirm the A-4 defaults (4000/20/1024/60) and the `MaxInputChars` ceiling needed to keep the request inside
  P-3.

## Retired

None. (First specification; no earlier R-<n>.)

## Submission

**summary:** Spec for an in-org Grok chat bot: LWC chat tab, an Apex controller that makes one synchronous callout per
turn to xAI via a Named/External Credential, admin config and kill switch in custom metadata, access by permission
set `Grok_Bot_User`, no data stored in the org. 13 requirements (R-1..R-13), 11 NFRs, 9 open gaps. Open material items:
xAI key (G-1), org access (G-2), live API probe (G-4), data-sharing approval (G-7). No requirement conflict found.
Assumptions recorded as defaults: A-1..A-9 (interpretation, chat-only without CRM data, in-memory history, defaults
4000/20/1024/60, no auto-retry, no streaming, shared key, permission-set access). Dependent work that needs the key or
org stays unready; mock-based Apex/Jest work is ready.

**primary:** R-1, R-2, R-3, R-7, R-8 (R-2 and R-7 carry the direct ask: a working Grok-backed bot; R-1 and R-3 make it
usable; R-8 makes it controllable). Lower-layer tests (Apex mock, Jest) may close R-2 P1 and R-3; R-2 P2 (Live) needs
the key.

**evidence_refs:**
- KNOWLEDGE/spec.md (this file), KNOWLEDGE/architecture.md
- GUIDES/platforms/salesforce.md (service discovery, consumer entry, testing)
- GUIDES/behavioral-requirements.md (behavior model, traceability, actors/channels/state)
- GUIDES/requirements-definition.md (state/data assessment, NFR)
- GUIDES/service-discovery.md (verification, runtime state placement)
- GUIDES/platforms/ui.md (light expressive starting point)
- xAI docs: https://docs.x.ai/developers/rest-api-reference, https://docs.x.ai/developers/model-capabilities/legacy/chat-completions.md (search result, not probed)
- Salesforce Apex callout limits: https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexref/apex_callouts_timeouts.htm
- Salesforce governor limits (older version page, re-verify): https://developer.salesforce.com/docs/atlas.en-us.248.0.apexcode.meta/pages/apex_gov_limits.htm
- Salesforce External Credential metadata: https://developer.salesforce.com/docs/atlas.en-us.262.0.api_meta.meta/api_meta/meta_externalcredential.htm
- Named Credentials guide: https://developer.salesforce.com/docs/platform/named-credentials/guide/get-started.html
