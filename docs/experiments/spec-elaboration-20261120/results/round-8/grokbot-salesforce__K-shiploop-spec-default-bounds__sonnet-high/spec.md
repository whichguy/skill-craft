# Grok Bot for Salesforce: product specification

Living spec. Requirement IDs `R-<n>` are stable; decisions about structure or technology are `AD-<n>` in
`KNOWLEDGE/architecture.md`; assumptions are `A-<n>`, open gaps `G-<n>`, platform facts `PF-<n>`, flows `F-<n>`,
transitions `T-<n>`, all defined in this file.

## Basis and baseline

- **Request (verbatim, 2026-11-21):** "Create a Grok bot in a Salesforce development org."
- **Interpretation (A-1):** the request names no UI, channel or data scope. "Grok" is read as xAI's Grok model
  family reached through xAI's public HTTP API; "bot" as a conversational assistant a Salesforce user chats with;
  "in a Salesforce development org" as: built as Salesforce metadata (Apex, Lightning Web Component, configuration)
  and deployed to a development org, where it is used from the Lightning Experience UI. It is not Einstein Bots,
  Agentforce or a Slack app (see Out of scope).
- **Prior spec / baseline:** none. This is the first spec for the product; no repository, org inventory,
  discovery or research result was available to this run. The target org was not read (the run had no approved
  read of it), so the current org state is **unknown** (G-1, G-5), not "empty". Nothing here is a recovered
  observation; every requirement is new, basis "request 2026-11-21 + the A-/PF- entries cited".
- **Sources used:** the request; the guides named in the stage (Salesforce platform card, requirements definition,
  behavior model, service discovery, UI visual direction); the primary documentation listed under PF-.

## Assumptions (best defaults the request leaves open)

| ID | Assumption (default chosen) | Why |
| --- | --- | --- |
| A-1 | Interpretation above. | Smallest reading that satisfies "Grok bot in a dev org". |
| A-2 | Audience: internal Salesforce users in Lightning Experience on desktop browsers. Salesforce mobile app, Experience Cloud/guest users: out of scope. | Request names none; dev-org use. |
| A-3 | The bot is a general-purpose Grok chat. It does **not** read or write Salesforce records. | Request asks for a Grok bot, not CRM grounding; keeps CRUD/FLS exposure at zero. |
| A-4 | Conversation transcript lives only in the open browser tab's component memory; no Salesforce record, no server session. Reload/navigation ends it. | Request needs no persistence; avoids storing user prompts. |
| A-5 | Max user message: **4,000 characters**. | Generous for a prompt; far below platform payload limits (PF-4). |
| A-6 | Context sent to Grok per turn: the new message plus at most the **20 most recent prior messages** (10 user/assistant pairs). | Bounds cost/latency per turn. |
| A-7 | Per-callout timeout default **60 seconds**. | Half of the hard 120 s platform ceiling (PF-1), allowing slow Grok models. |
| A-8 | Max reply length requested from Grok: **1,024 output tokens**. | Bounds cost and display size. |
| A-9 | Model name, system prompt, timeout, max output tokens, history cap are configuration (custom metadata), not code. The default system prompt: "You are Grok, a helpful assistant inside Salesforce. Answer concisely." | Request leaves them open; config avoids redeploys. |
| A-10 | One shared xAI API key for the whole org (a named principal), not per-user keys; cost accrues to the key's owner. | Simplest credential model for a dev org. |
| A-11 | No per-user rate limit or usage quota in Salesforce; xAI-side spend limits and 429s are the only throttle. | Request gives no quota; inventing one would be an unrequested bound (NFR-5). |
| A-12 | Replies are shown as plain text with line breaks preserved (no Markdown/HTML rendering). | Safe against injected markup; rich rendering is an unrequested feature. |
| A-13 | Replies arrive whole after the call completes (no token streaming). | Keeps one request/response hop; truthful pending state instead of fake streaming. |
| A-14 | Apex test coverage target ≥ 75% per production class, with a mocked callout. | Matches the commonly cited production deploy floor (PF-7, unverified); chosen for portability to other orgs. |

## Open gaps (prerequisites and user decisions)

| ID | Gap | Affects | Owner / due | Safe interim behaviour |
| --- | --- | --- | --- | --- |
| G-1 | Target dev org not identified (alias/username unknown). | R-13, R-1, R-7 | User; before plan names a deploy target | Source, tests and mocks proceed; no deploy. |
| G-2 | xAI API key not available to this run; entering it into the External Credential is a person-only step (secret). | R-6, R-13 | User/admin; before release-verify | Everything except the live Grok call is verifiable with mocks; R-13 stays unverified. |
| G-3 | Exact Grok model name the key may use, and the exact xAI response schema (field holding the text, truncation indicator), are unconfirmed (docs show several names: `grok-4`, `grok-4.3`, `grok-4.7`; no current list found). | R-2, R-5, R-8 | Plan: one authorised read-only `GET /v1/models` probe with the key, or the xAI console | Model is a config value; Apex parses defensively and maps an unparseable 200 to BAD_RESPONSE (R-5). |
| G-4 | Which xAI endpoint to call: docs label Chat Completions "legacy" and Responses preferred (PF-6). Decision is AD-3; the spec behaviour does not depend on it. | R-2 | Plan | None needed. |
| G-5 | Name clashes with existing org metadata (Apex, LWC, tab, app, permission set, custom metadata type, credential) not checked. | R-1, R-6, R-7, R-8 | Plan, via `sf org list metadata` per the platform card | Names in AD-5 are provisional. |
| G-6 | Whether a Named Credential callout needs no Remote Site Setting, and that the External Credential principal permission-set mapping works as designed in this org (PF-5, PF-8). | R-6 | Plan/deploy probe | None needed. |
| G-7 | Dark appearance: whether the org's Lightning theme supplies a dark mode is unverified. | NFR-1 | Plan | Component uses only SLDS tokens so it follows whatever theme the org applies. |

No material requirement conflict was found.

## Platform facts relied on (item 10 sources)

| ID | Fact | Source | Status |
| --- | --- | --- | --- |
| PF-1 | Cumulative callout timeout per Apex transaction is 120 s; a per-callout timeout may be set from 1 ms to 120,000 ms. | Apex Developer Guide, "Callout Limits and Limitations" (developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexref/apex_callouts_timeouts.htm) | Confirmed by search 2026-11-21 |
| PF-2 | At most 100 callouts per transaction. | same page | Confirmed |
| PF-3 | A callout cannot follow pending operations (DML, async work, email) in the same transaction. | same page | Confirmed |
| PF-4 | Total heap is 6 MB synchronous / 12 MB asynchronous; request/response callout size row not confirmed from current docs. | Apex "Execution Governors and Limits" | Heap confirmed only in archived versions; **recheck current page at plan**. Spec bounds (A-5/A-6/A-8) are orders of magnitude lower, so no requirement depends on the exact value. |
| PF-5 | An External Credential with a named principal applies one shared credential to all users whose permission set grants that principal; an API key can be sent as a custom auth header whose value is a formula. | Metadata API `ExternalCredential` reference; Named Credentials guide | Confirmed |
| PF-6 | xAI inference base is `https://api.x.ai`, Bearer API key; `POST /v1/chat/completions` is labelled legacy; `POST /v1/responses` is preferred and supports `previous_response_id`; stored responses are retained 30 days server-side. | docs.x.ai (API reference, Chat Completions page, Responses reference) | Confirmed by search; model list and `store` default not confirmed (G-3) |
| PF-7 | 75% Apex coverage is required to deploy to production. | Salesforce docs | **Unverified** in this run; not relied on (A-14 is a chosen default). |
| PF-8 | Callouts through a Named Credential need no Remote Site Setting. | Salesforce docs | **Unverified** (G-6). |
| PF-9 | Apex HTTP callouts return the whole body (no streaming). | Apex docs | **Unverified**; A-13 is a product choice that does not depend on it. |

## Flows

- **F-1 Send and answer (primary):** User (Lightning page) types a message → component validates (R-4) → shows the
  message and a pending indicator (T-1) → imperative Apex call (one transaction) → Apex validates again, builds the
  request from config + bounded history, makes **one** callout to xAI through the Named Credential → xAI replies →
  Apex returns a structured outcome → component appends the reply (T-2) or the error (T-3).
- **F-2 Retry:** User activates Retry on a failed message → same as F-1 with that message as the new one (T-4).
- **F-3 Reset:** User activates New chat → transcript, history and any pending result are discarded (T-5, T-7).
- **F-4 Access:** Admin assigns the permission set → user opens the Grok Bot tab from the App Launcher.
- **F-5 Credential setup (person-only):** Admin stores the xAI key in the External Credential principal → grants
  the principal to the permission set (G-2).

## State inventory and transitions

| State | Owner / location | Who may read | Lifetime | Concurrency | Durable? |
| --- | --- | --- | --- | --- | --- |
| Transcript + history + pending flag | LWC memory of one tab | That user only; never sent to another client | Until New chat, reload, navigation | Single writer (one tab); two tabs are independent transcripts | No |
| xAI API key | External Credential principal (Salesforce-held secret) | Callout runtime only; never Apex/LWC code, never config, never records, never logs | Until admin rotates/removes | Admin edits; next call uses new value | Yes |
| Config values (A-5..A-9) | Custom metadata record | Apex runtime; admins | Until edited | Last edit wins; effective next turn | Yes |
| Access grant | Permission-set assignment | Admins | Until unassigned | n/a | Yes |

Component states: **Empty** (no messages), **Idle** (≥1 completed turn, no pending), **Pending** (one request in
flight), **Failed** (last message unanswered, Retry offered). Message states: sent-answered, failed (unanswered).

| T | Before → After | Trigger / guard | Effect, error and recovery | R |
| --- | --- | --- | --- | --- |
| T-1 | Empty/Idle/Failed → Pending | Send; message valid (R-4); no request in flight | Message appended; pending indicator; Send disabled | R-2, R-9 |
| T-2 | Pending → Idle | Apex outcome ok and request still current | Reply appended; Send re-enabled; focus returns to composer | R-2 |
| T-3 | Pending → Failed | Outcome is an error category, or the call itself rejects | Error appended against the message; message stays in transcript, excluded from history; Retry offered | R-5 |
| T-4 | Failed → Pending | Retry | The failed message becomes the new message; prior valid history sent | R-5 |
| T-5 | any → Empty | New chat | Transcript, history, errors cleared; pending request marked superseded | R-3 |
| T-6 | any → unchanged | Send while Pending, or invalid input | Rejected; no Apex call; transcript unchanged; validation message shown (invalid input) or Send disabled (pending) | R-4, R-9 |
| T-7 | Empty → Empty | Result of a superseded request arrives after New chat | Ignored: not displayed, not stored (the server effect, i.e. the xAI call, cannot be undone) | R-9 |

## Requirements

### R-1 Grok Bot is reachable from Lightning Experience
- **Basis:** request 2026-11-21 ("Create a Grok bot in a Salesforce development org"), A-1, A-2. **Change:** add. **Preserve:** nothing existed. **Locators:** Salesforce platform card "Service discovery" (consumer entry is source metadata). **Evidence limit:** org not read (G-1, G-5). **Pending:** implementation and deploy.
- **Behaviour:** a Lightning app named "Grok Bot" containing one tab "Grok Bot" that renders the chat component. Source metadata includes the component, a custom tab, the app, and the permission-set visibility for both. A user holding the Grok Bot permission set (R-7) sees the app in App Launcher and the tab opens at `/lightning/n/<TabApiName>`.
- **Boundaries:** a user without the permission set sees no app and the URL answers "Page does not exist"; that is correct, not a defect.
- **Consumer outcome:** the user opens the tab and sees the empty chat (R-2 Empty state).
- **AC R-1/1 (positive):** with the permission set assigned, the tab opens and shows composer + empty-state prompt. Surface: Lightning UI, org. Confirm: browser check as the test user, plus `sf org list metadata --metadata-type CustomTab` shows the tab.
- **AC R-1/2 (failure):** a user without the permission set cannot open the tab. Surface: org UI + read-only `PermissionSetTabSetting` query. Confirm: query returns no row for that user's permission sets.
- **AC R-1/3 (boundary):** n/a: one tab, one app; no countable limit.
- **Out of scope bounded here:** Salesforce mobile app, Experience Cloud/guest, Utility-bar/Lightning Home placement, Slack (A-2).

### R-2 A user chats with Grok and sees its reply
- **Basis:** request 2026-11-21 ("a Grok bot"), A-1, A-3, A-12, A-13. **Change:** add. **Evidence limit:** xAI response schema unconfirmed (G-3). **Pending:** implementation; live check needs G-2.
- **Behaviour:** the user submits text; the component shows it right-aligned as the user's message and, once Grok answers, shows the reply left-aligned as plain text, newlines preserved, in order. Replies are never interpreted as HTML or markup. Composer: Enter sends, Shift+Enter inserts a newline, a Send button is the pointer path.
- **Error behaviour:** see R-5. **Consumer outcome:** a readable question/answer thread.
- **AC R-2/1 (positive, deterministic):** with the xAI callout mocked to return the text `Paris.` for the input `What is the capital of France?`, the component shows both messages in that order, and the reply text equals `Paris.`. Surface: Apex test (request built, reply parsed) + Jest (render order). Confirm: assertions on the mock-captured request body (contains the input string) and on rendered text.
- **AC R-2/2 (positive, live):** against real Grok, the same input yields a non-empty reply containing `Paris`. Surface: Lightning UI in the dev org with the real key. Confirm: browser check. Probabilistic model output: a miss is retried once and recorded, not assumed a defect. Blocked by G-2.
- **AC R-2/3 (failure):** reply text containing `<img src=x onerror=alert(1)>` renders as that literal text; no element is created. Surface: Jest. Confirm: DOM has no `img`, text node equals the string.
- **AC R-2/4 (boundary):** a reply of 1,024 tokens' worth of multi-paragraph text displays fully with scrolling inside the thread; the page itself does not grow horizontally. Surface: Jest with a 5,000-character multi-line reply fixture. Confirm: all text present, no horizontal overflow at 360 px.
- **Out of scope bounded here:** record grounding, tool/function calling, web search, image or file input, voice, streaming, Markdown rendering (A-3, A-12, A-13).

### R-3 The bot keeps conversational context within a session
- **Basis:** request ("bot" read as conversational), A-4, A-6. **Change:** add. **Pending:** implementation.
- **Behaviour:** each turn sends Grok the new message plus up to the 20 most recent prior **answered** messages (user and assistant, in order). Failed/unanswered messages are not sent as history. New chat clears everything. Nothing persists past the tab.
- **Boundary walk (recomputed by hand against these rules; NOT-REPLAYED in an org):** prior messages before turn n = 2·(n−1). Turn 1: 0 prior, payload 1 message. Turn 11: 20 prior, payload 21 messages (all of turns 1–10 plus turn 11). Turn 12: 22 prior → oldest 2 (turn 1's pair) dropped, payload 21 messages starting at turn 2's user message. Failure case: turn 3's reply fails, user sends a new message instead of Retry → turn 3's message is excluded; the payload's prior messages are turn 1–2 pairs only.
- **AC R-3/1 (positive):** turn 1 `Remember the code word PELICAN-42.` answered `OK.` (mock); turn 2 `What was the code word?` → the captured turn-2 request contains both turn-1 messages before the turn-2 message, in order. Surface: Apex test with `HttpCalloutMock` capturing bodies. Confirm: assertion on message order/content (not on the model's wording). Live smoke (G-2): the real reply contains `PELICAN-42`.
- **AC R-3/2 (boundary):** after 11 answered exchanges, the 12th request has exactly 21 messages and its first message is turn 2's user text; the 11th request had 21 including turn 1's. Surface: Apex test. Confirm: count and first-element assertions. A client that sends 30 prior messages is trimmed server-side to 20 (the server, not the browser, enforces the cap).
- **AC R-3/3 (failure):** per the walk above, an unanswered message is absent from the next payload. Surface: Apex + Jest. Confirm: payload assertion.
- **AC R-3/4 (positive):** New chat empties the transcript and the next request carries 1 message. Surface: Jest + Apex. Confirm: rendered state and payload.
- **Out of scope bounded here:** saved/resumable conversations, cross-session memory, transcript export, per-user history in Salesforce (A-4).

### R-4 Input validation
- **Basis:** A-5. **Change:** add. **Pending:** implementation.
- **Behaviour:** a message is valid when, after trimming leading and trailing whitespace, it has 1 to 4,000 characters. Invalid input makes no Apex call and no callout and leaves the transcript unchanged; the component shows an inline message (`Enter a message.` or `Messages are limited to 4,000 characters.`). The server revalidates and refuses an invalid message with category INVALID_INPUT and no callout, so a hand-made Apex call cannot bypass it.
- **AC R-4/1 (failure):** input `   ` plus a newline is rejected, 0 callouts. Surface: Jest (no Apex invocation) + Apex test (INVALID_INPUT, mock invocation count 0).
- **AC R-4/2 (boundary, accepted):** 4,000 `a` characters are accepted and sent in full. Surface: Apex test; request body contains 4,000 consecutive `a`.
- **AC R-4/3 (boundary, rejected):** 4,001 `a` characters are rejected, 0 callouts. Surface: Jest + Apex.
- **AC R-4/4 (boundary, trimming):** `  hi  ` is sent as `hi`; 4,000 characters plus 5 trailing spaces is accepted (the bound applies after trimming). Surface: Apex test.
- **AC R-4/5 (positive):** n/a: covered by R-2/1.
- **Partitions:** empty/whitespace-only; 1–4,000; >4,000. Characters are counted as Apex `String.length()` (UTF-16 code units); an emoji counts as 2. Exclusion: no content filtering or profanity policy is requested.

### R-5 Failures are reported clearly and recoverably
- **Basis:** request (a working bot implies handling a failing remote), PF-1, A-7. **Change:** add. **Evidence limit:** real xAI error payloads unobserved (G-2, G-3). **Pending:** implementation.
- **Behaviour:** every outcome of the xAI call maps to exactly one category. The user sees the category's fixed message, never the raw xAI body, a header, a stack trace or the key. The failed message stays in the transcript marked unanswered with a Retry action; the rest of the conversation is intact and usable.

| Group (distinct observable behaviour) | Trigger | Category | User message |
| --- | --- | --- | --- |
| Invalid input | R-4 violation at the server | INVALID_INPUT | Message not sent; see R-4 text |
| Authentication/authorisation | HTTP 401 or 403 | AUTH | "Grok rejected the credentials. Ask an administrator to check the API key." |
| Not found / config | HTTP 404 | CONFIG | "The configured Grok model was not found. Ask an administrator." |
| Request rejected | other HTTP 4xx except 429 | BAD_REQUEST | "Grok could not process that request." |
| Throttled | HTTP 429 | RATE_LIMIT | "Grok is busy or a usage limit was reached. Try again shortly." |
| Upstream failure | HTTP 5xx | UPSTREAM | "Grok is temporarily unavailable. Try again." |
| Timeout | no response within the configured timeout (60 s default) | TIMEOUT | "Grok took too long to answer. Try again." (unknown outcome: the call may have completed and been billed) |
| Network/setup | any other callout exception (DNS, TLS, credential not usable by the user) | NETWORK | "Could not reach Grok. Try again or ask an administrator." |
| Bad response | HTTP 200 with a body that is not valid JSON or has no non-empty reply text | BAD_RESPONSE | "Grok returned an unreadable answer. Try again." |
| No access | the user lacks Apex class access | NO_ACCESS | "You do not have access to Grok Bot." |

- **AC R-5/1 (failure):** for each row above except NO_ACCESS, a mock returning that status (or throwing the corresponding callout exception; 200 with body `{}` and with body `not json`) yields exactly that category and message; the message text never contains the mock's body marker string `SECRET-BODY-MARKER` or the API-key marker. Surface: Apex test (category) + Jest (rendered message). Confirm: equality assertions per row.
- **AC R-5/2 (boundary):** HTTP 399/400/401/403/404/428/429/499/500/599 each map to the row shown (a status table test); 200 with empty text `""` → BAD_RESPONSE. Surface: Apex test.
- **AC R-5/3 (positive recovery):** after a failure, Retry resends and, with the mock now succeeding, the reply appears and the message is no longer marked unanswered. Surface: Jest + Apex. Confirm: transcript state and payload history (R-3 rules).
- **AC R-5/4 (failure, access):** a user without class access gets NO_ACCESS and no callout occurs. Surface: org UI as a user with the tab but without class access, or Apex `System.runAs` test. Confirm: message and callout count 0.
- **AC R-5/5 (failure, retry limit):** n/a: Retry is user-driven; there is no automatic retry (a retried timeout can duplicate cost; automatic retry is not requested).
- **Idempotency:** no idempotency key is sent; duplicate calls are possible after TIMEOUT (stated in the table).

### R-6 The xAI API key is held only by Salesforce credential facilities
- **Basis:** A-10, PF-5, Salesforce platform card ("Keep configuration in custom metadata… never secrets in records"; service-discovery credential custody). **Change:** add. **Pending:** implementation; secret entry is person-only (G-2).
- **Behaviour:** the key is stored in an External Credential (named principal) and used through a Named Credential that points at the xAI base URL; Apex addresses the endpoint with the `callout:` form only. The key never appears in source control, Apex, LWC, custom metadata, records, debug logs, error messages or this spec. The deployed metadata contains no key value; the principal exists without a stored secret until an admin supplies one.
- **AC R-6/1 (positive):** a repository search of the deliverable for the key's prefix pattern and for the literal `Bearer ` followed by a value finds nothing; Apex endpoint strings begin `callout:`. Surface: source scan. Confirm: scan exit code and a negative-control string planted in a scratch copy is found (so the scan can fail).
- **AC R-6/2 (failure):** with the key absent or wrong, the user gets AUTH or NETWORK (R-5), never the key. Surface: org UI / Apex mock. Confirm: message equality.
- **AC R-6/3 (positive, live):** with a valid key entered by the admin, a call succeeds (R-13). Surface: org. Blocked by G-2.
- **AC R-6/4 (boundary):** rotation: after an admin replaces the key, the next turn uses it without redeploy. Surface: org, person-assisted. Confirm: success after rotation; failure with the old key at xAI. Marked unverified until G-2.

### R-7 Access is limited by a Grok Bot permission set
- **Basis:** Salesforce platform card (record sharing, object permissions and field permissions as separate requirements), A-2, A-3, A-10. **Change:** add. **Pending:** implementation, assignment (admin).
- **Behaviour (three separate concerns):**
  1. *Feature access:* a permission set (name provisional, AD-5) grants the Grok Bot app and tab visibility, access to the Apex class(es) the component calls, and the External Credential principal. Only users it is assigned to can use the bot or spend the key.
  2. *Sharing/CRUD/FLS:* the bot reads and writes no standard or custom records (A-3), so no object or field permission is granted. It reads its own custom-metadata configuration only. Apex is declared `with sharing`; since no record data is involved this is hygiene, and is **not** claimed as CRUD/FLS enforcement.
  3. *Assignment:* the deliverable creates the permission set but assigns it to nobody; assignment is a separate, named administrator step at release-plan (G-1 for who).
- **AC R-7/1 (positive):** a test user with the permission set can open the tab and complete a turn. Surface: org UI. Confirm: browser check.
- **AC R-7/2 (failure):** a user without it cannot open the tab (R-1/2) and a direct Apex call is refused (R-5/4).
- **AC R-7/3 (boundary):** permission set grants no object/field permissions: its metadata contains no `objectPermissions` or `fieldPermissions` element. Surface: source inspection. Confirm: grep returns zero.
- **AC R-7/4 (read-only probe):** `PermissionSetTabSetting`, `SetupEntityAccess` (TabSet, ApexClass) rows show the grants for the test user's permission sets at release-check. Surface: org read.
- **Out of scope bounded here:** per-user keys, row-level data access, profile-based grants (a permission set is the one route).

### R-8 Behaviour settings are configuration, not code
- **Basis:** A-5..A-9, Salesforce platform card (configuration in custom metadata). **Change:** add. **Pending:** implementation.
- **Behaviour:** model name, system prompt, per-callout timeout (ms), max output tokens, and history cap are read from one custom-metadata record at each turn; defaults ship in the deployed record: system prompt per A-9, timeout 60,000 ms, max output tokens 1,024, history cap 20, model per G-3. An admin edit takes effect on the next turn. The message cap (4,000) is a fixed constant, not configuration.
- **Boundaries:** the timeout is accepted from 1,000 to 120,000 ms (the platform's per-callout ceiling is 120,000 ms, PF-1); a value outside the range, a non-numeric or missing value falls back to the shipped default and the turn proceeds. History cap accepted 0 to 50; outside → default 20. Max output tokens accepted 1 to 8,192; outside → default 1,024. (Accepted ranges are chosen defaults, A-7/A-8/A-6, not xAI limits.)
- **AC R-8/1 (positive):** changing the history cap to 4 in a test config changes the number of prior messages sent to 4. Surface: Apex test (config injected through a testable seam). Confirm: payload count.
- **AC R-8/2 (boundary):** timeout 0, 120,001, `abc` and null all yield the effective timeout 60,000 ms; 1,000 and 120,000 are used as given. Surface: Apex test on the resolver. Confirm: resolved value equality.
- **AC R-8/3 (failure):** config record missing → defaults used, turn proceeds. Surface: Apex test.
- **AC R-8/4 (positive):** the system prompt is sent as the first instruction of every request and is not displayed in the transcript. Surface: Apex payload + Jest.
- **Drift note:** a later deploy of the same-named record overwrites admin edits; the plan must make config deploys additive/explicit (preserve org edits).

### R-9 Truthful in-flight feedback and one request at a time
- **Basis:** UI visual guide; behavior model (async completion, stale results). **Change:** add. **Pending:** implementation.
- **Behaviour:** while a request is Pending, the thread shows a pending indicator ("Grok is thinking…") announced politely to assistive tech, Send is disabled and a second send is ignored (T-6); the typed draft in the composer is kept. If New chat is activated while Pending, the late result is discarded (T-7). A result appears only for the request that is still current. The pending indicator never claims progress it cannot know (no percentage, no fake streaming).
- **AC R-9/1 (positive):** with a controllable deferred mock, the pending indicator and disabled Send are visible until completion, then replaced by the reply. Surface: Jest with controlled promise. Confirm: DOM queries before/after resolve (no sleeps).
- **AC R-9/2 (failure):** Send pressed twice (and Enter held) during Pending results in exactly one Apex invocation. Surface: Jest. Confirm: invocation count 1.
- **AC R-9/3 (boundary, race):** New chat during Pending, then the old request resolves: the transcript stays empty. Surface: Jest. Confirm: DOM and no stored state.
- **AC R-9/4:** reduced motion: with `prefers-reduced-motion: reduce` the indicator has no animation. Surface: Jest/CSS or browser emulation.

### R-10 User prompts and replies are handled as personal data
- **Basis:** the request's data flow (prompts leave Salesforce to xAI); system rules on personal/secret data. **Change:** add. **Evidence limit:** xAI retention is outside this product's control (PF-6: stored responses up to 30 days if the Responses endpoint stores them; `store` default unconfirmed, G-3). **Pending:** implementation, disclosure wording.
- **Behaviour:** (a) a short notice in the empty state says messages are sent to xAI to be answered, and not to enter data the org may not share externally; (b) prompts and replies are shown only in the user's tab, stored nowhere in Salesforce (A-4), not written to debug logs, platform events, custom objects or error messages; (c) logs record only category, HTTP status and timing; (d) the request asks xAI not to retain the conversation where the chosen endpoint supports it (AD-3); retention on xAI's side is stated, not promised.
- **AC R-10/1 (positive):** the empty state shows the notice text. Surface: Jest/UI. Confirm: text present.
- **AC R-10/2 (failure):** with a marker message `LOGCHECK-7731` sent through a mocked call and a mocked failure, the captured Apex debug/log output contains no occurrence of the marker or reply text. Surface: Apex test using a log-capture seam, or `sf apex tail`/log retrieval in the org. Confirm: string search finds zero. (Verifies absence only for the exercised paths.)
- **AC R-10/3 (boundary):** after New chat or reload, no earlier message is recoverable from the page. Surface: Jest/UI.
- **Excluded:** field-level redaction/DLP of prompts (not requested; open risk recorded in NFR-2).

### R-11 The source deploys to a development org as additive metadata
- **Basis:** request ("in a Salesforce development org"), platform card (API version, name clashes, additive change, separate visibility steps). **Change:** add. **Evidence limit:** org unread (G-1, G-5). **Pending:** project scaffold, deploy.
- **Behaviour:** the deliverable is a source-format Salesforce DX project that creates only new metadata (Apex classes + tests, LWC, tab, app, permission set, custom metadata type + default record, External/Named Credential with no secret) with an API version chosen at plan from what the target org supports (not copied from memory). Names are checked against the org before use (G-5). The deploy does not modify, delete or overwrite any metadata it does not own. Deploy, permission-set assignment and credential-secret entry are three separate steps, each named at release-plan. `.sf/` and `.sfdx/` are git-ignored.
- **AC R-11/1 (positive):** `sf project deploy validate` (dry-run) then deploy to the target org succeeds and the terminal status is read back as Succeeded with the component list matching the project. Surface: `sf` CLI against the dev org. Confirm: terminal deploy status, not just accepted job id. Blocked by G-1.
- **AC R-11/2 (failure/preserve):** the deployed component list contains no pre-existing metadata not in the project; a pre-existing same-name component, if found at the G-5 inventory, stops the plan instead of overwriting. Surface: metadata listing before and after.
- **AC R-11/3 (boundary):** `.gitignore` lists `.sf/` and `.sfdx/`. Surface: file check.

### R-12 Automated checks cover the logic without the live service
- **Basis:** platform card (Testing), A-14. **Change:** add. **Pending:** tests authored later.
- **Behaviour:** Apex tests use an `HttpCalloutMock` (no real network) and cover R-3, R-4, R-5, R-8 and R-10; LWC Jest tests cover R-2, R-3, R-9 rendering and state; coverage ≥ 75% per production Apex class (A-14). Apex tests are remote tests (they run in the org) and must be recorded with a `--result-format tap` command.
- **AC R-12/1 (positive):** `sf apex run test --class-names <TestClass> --synchronous --result-format tap --target-org <alias>` prints `ok` lines for each case and the coverage report shows ≥ 75% per class. Surface: org. Confirm: TAP output + coverage numbers. Blocked by G-1.
- **AC R-12/2 (failure, stand-in guard):** each Apex test asserts on the captured request body or on the returned category; a test that only asserts "no exception" does not count. Confirm: review of assertions at test-spec.
- **AC R-12/3:** Jest suite runs locally with exit code 0 and the listed cases execute. Surface: local.

### R-13 The deployed bot answers a real question from Grok in the dev org
- **Basis:** request ("Create a Grok bot in a Salesforce development org"). **Change:** add. **Evidence limit:** needs the target org (G-1), the xAI key (G-2) and the model name (G-3); none is available to this run. **Pending:** everything.
- **Behaviour:** end to end, the assigned test user opens the tab in the target org, sends `What is the capital of France?` and a real Grok reply containing `Paris` appears; then sends `Remember the code word PELICAN-42.` followed by `What was the code word?` and the reply contains `PELICAN-42`.
- **Replayability:** the start state needs G-1 (target), G-2 (key stored by a person) and the permission-set assignment (admin). Until these hold the case is `NOT-REPLAYED: no org target and no key available to the spec stage`, so it is open, not passed. A local mock pass does not satisfy it.
- **AC R-13/1 (positive):** the two interactions above succeed. Surface: Lightning UI, deployed. Confirm: browser run as the test user with screenshot evidence; deploy status read-back (R-11/1).
- **AC R-13/2 (failure):** n/a here: failure behaviour is R-5; live failure is exercised with a deliberately wrong key only if an admin agrees (a person step, optional).
- **AC R-13/3 (boundary):** n/a: bounds are R-3/R-4 through mocks; the live check does not add a distinct bound.

## Non-functional requirements

- **NFR-1 Interface quality (applies: the component is a UI).** Basis: stage rule 6; UI visual-direction guide, light expressive starting point, adapted to platform conventions. **Named visual reference:** the light Google Gemini chat look with Material 3 Expressive principles (airy, tonal rounded message surfaces, confident primary Send action), **constrained by Salesforce Lightning Design System** because it is the platform convention and takes precedence: SLDS styling hooks/tokens only (no hard-coded palette), one icon set (SLDS utility icons), the org's Lightning theme. **Starting appearance:** light; a dark appearance only through the org's theme (G-7), never a custom theme. Observable criteria: (a) spacing and type come from SLDS scales only; user and Grok messages are visually distinct tonal surfaces; the thread and composer are the focal point and the composer is always reachable; (b) designed Empty (prompt + data notice), Pending (R-9), Error (R-5, with Retry) states; (c) usable at 360 px and at 1,440 px page width with no horizontal scrolling of the page, and with long unbroken text (a 200-character no-space string) wrapped, not overflowing; (d) every control keyboard-reachable, visible focus, accessible names, new replies announced in a polite live region, text contrast ≥ 4.5:1 (WCAG AA); (e) motion only for the pending indicator and message arrival, off under reduced motion; (f) one icon set. Verification: Jest for DOM/aria/names/states; browser run in the org at both widths with a contrast check; a rendered-result review against these choices. Status: planned; concrete tokens in the plan's UI direction (AD-6).
- **NFR-2 Security and privacy.** R-6, R-7, R-10 plus: no injection into HTML (R-2/3); Apex does not build the endpoint from user input (fixed `callout:` target). Residual risk recorded, not solved: users can paste sensitive Salesforce data into a prompt, which goes to xAI; mitigation is the R-10 notice and permission-set gating only (DLP excluded, not requested).
- **NFR-3 Platform limits and bulk safety.** Each turn is one synchronous Apex transaction with **exactly one callout and zero DML**, within PF-1..PF-3 (limits: 1 of 100 callouts; timeout ≤ 120 s; no pending DML before the callout). The entry point takes one message plus a list of history messages (collection-shaped input), not per-record loops. AC: Apex test asserts mock invocation count = 1 per successful turn and 0 for INVALID_INPUT, and `Limits.getDmlStatements()` = 0. Surface: Apex test.
- **NFR-4 Latency/throughput.** No numeric reply-time SLA is set (reply time is Grok's); the only bound is the configured timeout (A-7, R-5 TIMEOUT). Unresolved by design: a latency target would need a measured baseline from the live service (G-2).
- **NFR-5 Capacity and cost.** Per-turn cost is bounded by A-5, A-6, A-8; there is no per-user quota (A-11). Unresolved: an org-wide monthly spend cap is an xAI-console setting owned by the key holder; not verifiable from Salesforce.
- **NFR-6 Reliability and recovery.** No retained server state (A-4), so there is nothing to recover but config and credential; the user recovers a failed turn by Retry (R-5); admin recovers by editing config or re-entering the key. No availability target is set (depends on xAI; none requested).
- **NFR-7 Observability.** Failures log category, HTTP status and elapsed time at error level without content (R-10). A custom log object, event stream or dashboard is excluded (not requested; would store prompt-adjacent data).
- **NFR-8 Compatibility.** Lightning Experience in current evergreen desktop Chrome/Edge/Safari/Firefox; the exact API version is chosen at plan from the org (R-11); not verified on Salesforce mobile (A-2).
- **NFR-9 Maintainability/testability.** Apex service logic separated from the controller so mocks reach it (AD-2); R-12 coverage.
- **NFR-10 Operability/rollback.** Rollback = unassign the permission set (instantly hides the bot) and optionally delete the project's metadata by name; the key is removed from the External Credential by the admin. Containment for a bad release: deploy to the dev org only; promotion beyond it is out of scope.

## State and data assessment

| Resource | Target identity | Change | Before → after invariant | Recovery | Check / unknown |
| --- | --- | --- | --- | --- | --- |
| Apex classes, LWC, tab, app, permission set, custom metadata type + record, Named/External Credential | target dev org (G-1, alias unknown) | create (additive) | Before: none of these names exist (**unknown**, G-5); after: exactly the project's components, no pre-existing metadata altered | delete by name; unassign permission set | R-11/1, R-11/2 |
| xAI API key | External Credential principal in target org | set by a person | Before: principal without secret; after: secret held by Salesforce, never readable from repo/config | admin overwrites/removes | R-6/1, R-6/3 |
| Permission-set assignment | named test user (unknown, G-1) | assign (separate step) | Before: user cannot see tab; after: can | unassign | R-7/1, R-7/4 |
| Config record | target org | create default; admin may edit | values within accepted ranges or defaults used | redeploy default / edit | R-8 |
| Transcript | user's tab | transient | exists only in memory | n/a | R-3, R-10/3 |
| Salesforce business records | none | **intentionally unchanged and unread** | zero DML | n/a | NFR-3 |
| Existing org automation/components | target org | **intentionally untouched** | preserved | n/a | R-11/2 |

Unknowns: current org inventory, target user/profile, API version. Partial failure: a deploy that succeeds without the permission set assignment leaves a built-but-hidden bot (safe); credential present without permission-set principal grant gives NETWORK (R-5), not data exposure.

## Service boundary contracts (service discovery)

- **Boundary:** Salesforce Apex runtime (caller) → Named Credential → xAI public API (authority for answers). A development MCP/CLI deploys the project but is **not** part of the runtime path.
- **Current authority:** xAI authorises each call by the API key; Salesforce authorises users by permission set. Both checked on every turn.
- **Freshness vs revocation:** no caching of replies or authorisation anywhere (the Apex call is non-cacheable and is a POST), so a revoked permission set or rotated/revoked key takes effect on the next turn (R-6/4, R-7/2). No cache means no invalidation plumbing.
- **Incremental state:** none; the browser holds the history and resends the bounded window each turn.
- **Async completion/recovery:** synchronous per turn; acceptance of the call is not completion: the user sees the reply or an error only on the terminal outcome; timeout is an unknown outcome (R-5 TIMEOUT) and retry may duplicate cost. No background jobs, no polling.
- **Owned event coverage:** only failure logs without content (NFR-7); login/audit coverage of the org is the platform's, unchanged. Inapplicable: queue/broker, webhook, schema migration, query/pagination, incremental sync.
- **Runtime identity:** the callout runs as the running user for authorisation of principal access and as the named principal's key for xAI; deployment identity (the `sf` login) does not establish either.

## Request-outcome traceability

| Request outcome | Acceptance lines |
| --- | --- |
| "a Grok bot": converses | R-2/1–4, R-3/1–4, R-9/1–4 |
| "a Grok bot": talks to Grok securely | R-6/1–4, R-5/1–5, R-10/1–3 |
| "in a Salesforce … org": a place to use it | R-1/1–2, R-7/1–4 |
| "in a Salesforce … org": it is built there | R-11/1–3, R-12/1–3, R-8/1–4 |
| Works end to end for real | R-13/1 |
| Interface quality (UI deliverable) | NFR-1, R-9 |

## Out of scope (domain rules the request leaves out, by requirement)

- R-1: Salesforce mobile, Experience Cloud/guest users, Lightning Home/utility-bar placement, Slack.
- R-2: CRM-record grounding, function/tool calling, web or code tools, image/file/voice input, streaming, Markdown rendering, Einstein Bots/Agentforce integration.
- R-3: persisted or resumable conversations, cross-session memory, transcript export.
- R-6/R-7: per-user API keys or OAuth, profile-based access, record-level security.
- R-5: automatic retry, fallback to a second model, offline queueing.
- NFR-2/NFR-7: DLP/redaction of prompts, usage analytics or audit objects, per-user quotas.

## Replay record (item 10)

| Case | Method | Recomputed result | Status |
| --- | --- | --- | --- |
| History window at turns 1, 11, 12 and after a failed turn (R-3) | Hand walk against R-3 rules, checking each send is permitted by T-1 (needs a valid message and no request in flight) | 1, 21, 21 messages; failed message absent | Recomputed by hand; not executed (no product exists; a test must assert it) |
| Config boundary resolution (R-8) | Hand walk of the accepted-range rule | 0→60,000; 1,000→1,000; 120,000→120,000; 120,001→60,000; `abc`/null→60,000 | Recomputed by hand; not executed |
| Live Grok cases (R-13, R-2/2, R-3/1 live) | Start requires G-1, G-2, assignment | n/a | `NOT-REPLAYED: no org target, key or assigned user available to this stage` (open) |
| Org deploy/read-back (R-11/1, R-7/4) | Needs G-1 | n/a | `NOT-REPLAYED: org not identified` (open) |
| Documented commands | The `sf` and `jest` commands named here were **not run** (no project exists; `sf` use against an org was not authorised for this stage) | n/a | Exit codes unrecorded; run at plan/test |

Probes performed: web documentation searches only (PF-1..PF-6); no org, API or credential was touched.

## Retired

None. First spec of the product.

## Submission

- **summary:** First spec for the Grok bot (Salesforce dev org): 13 requirements (R-1..R-13) plus NFR-1..NFR-10, service-boundary contracts, state assessment and a request-outcome traceability table; decisions are AD-1..AD-6 in `KNOWLEDGE/architecture.md`. The request was open-ended, so assumptions A-1..A-14 are recorded: Grok via xAI's API through a Named/External Credential, chat LWC in a Lightning app tab, Apex callout, transcript only in browser memory, 4,000-character message cap, 20-message history window, 60 s timeout, 1,024 output tokens, plain-text replies, org-wide shared key, no per-user quota, no CRM data access. **Open (block only dependent work):** G-1 target dev org and test user unidentified (blocks deploy and live checks); G-2 xAI API key must be entered by a person (blocks R-13, live parts of R-2/R-3/R-6); G-3 Grok model name and response schema unconfirmed (plan probe); G-4 endpoint choice (AD-3); G-5 org name-clash inventory; G-6 Named Credential/Remote Site and principal-mapping probe; G-7 dark theme availability. PF-4, PF-7, PF-8, PF-9 are unverified platform claims, not relied on. No material requirement conflict. `backchain-check` not applicable (no graph written, duty 11 left out). Nothing was executed: replay cases are recomputed by hand or marked `NOT-REPLAYED`.
- **primary:** R-1, R-2, R-3, R-13 (also load-bearing for them: R-6, R-7, R-11).
- **evidence_refs:** `KNOWLEDGE/spec.md` (this file: Requirements R-1..R-13, Non-functional requirements, State and data assessment, Service boundary contracts, Platform facts PF-1..PF-9); `KNOWLEDGE/architecture.md` (AD-1..AD-6); GUIDES: `platforms/salesforce.md`, `requirements-definition.md`, `behavioral-requirements.md#behavior-model`, `service-discovery.md`, `platforms/ui.md#light-expressive-starting-point`; web sources: Salesforce Apex "Callout Limits and Limitations", Metadata API `ExternalCredential`, Named Credentials guide, docs.x.ai API reference/Chat Completions/Responses pages (searched 2026-11-21).
