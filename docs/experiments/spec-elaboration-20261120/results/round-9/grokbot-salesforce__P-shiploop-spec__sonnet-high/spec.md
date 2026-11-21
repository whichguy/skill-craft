# Grok Bot for Salesforce: product specification

Living specification of what the product must do. How it is built is in `architecture.md` (AD-<n>). Requirement IDs are
`R-<n>`; flows `F-<n>`; transitions `T-<n>`; cases `TC-<n>`; open gaps `G-<n>`; product assumptions `A-<n>`.

## Status of this document

- First specification. No earlier spec, discovery or research result, repository, or org inspection existed when this
  was written. Baseline: **greenfield for the product**; the target org's current contents are **unknown**
  (not probed: no org alias, no authorized session and no xAI key were available to this stage). Absence of probe
  evidence is not evidence that an object, name or permission is absent (G-1, G-2).
- Verification status of every acceptance line below: **planned, not run**. Nothing here claims an execution.
- Sources used: the request text; Salesforce Apex Developer Guide "Callout Limits and Limitations"; Salesforce Named
  Credentials Glossary and External Credential Metadata/Tooling API references; xAI docs (REST API reference, Chat
  Completions legacy page, Responses API migration notes, rate-limits page) as surfaced by web search on 2026-11-21;
  ShipLoop `platforms/salesforce.md`, `platforms/ui.md`, `service-discovery.md`, `behavioral-requirements.md`,
  `requirements-definition.md`. xAI facts come from search snippets of docs.x.ai and third-party pages, not from an
  authorized API call; they are marked where a decision depends on them.

## Request, interpretation and basis

Request (2026-11-21, verbatim): "Create a Grok bot in a Salesforce development org."

The request is short and ambiguous. Interpretation adopted (each point is a recorded assumption, not user text):

- **A-1 "Grok"** means xAI's Grok models, reached through xAI's public HTTPS API.
- **A-2 "Bot"** means a conversational assistant: a signed-in org user types messages and receives Grok's replies in a
  multi-turn chat. It is not an autonomous agent, not a record-updating automation, and not a Slack/Teams bot.
- **A-3 "In a Salesforce development org"** means the product is delivered as metadata deployed to one development org
  (a Developer Edition org, sandbox or scratch org) and used there through a Lightning Experience entry point. The org
  is not named in the request; it is an open prerequisite (G-1).
- **A-4 Grounding:** v1 sends Grok only what the user typed (plus admin-configured instructions and earlier turns of
  the same chat). It does **not** read or send Salesforce records. Reason: nothing in the request asks for CRM data, and
  sending customer data to a third party is a consequential decision a person has not made.
- **A-5 Persistence:** no stored transcripts (R-9). Reason: not requested; adds PII retention duty.
- **A-6 Users:** any org user who holds the product's permission set; no per-user quota, billing or role logic.
- **A-7 Language/format:** UI in English; replies shown as plain text (no markdown rendering) in v1.
- **A-8 Defaults** for configurable values (R-7): history window 20 messages, max input 4,000 characters, callout
  timeout 60,000 ms. They are product defaults chosen to sit inside the platform's hard limits, not xAI-mandated
  numbers; an admin can change them. Marked as assumptions for the user to confirm.

## Scope

In scope: chat UI entry in the org; sending a message to Grok and showing the reply; in-session multi-turn context;
clear/new conversation; input validation; error mapping; admin configuration; access control and secret custody;
deployability to a development org with Apex tests.

Out of scope for this version (each bounds the R-<n> named): Salesforce-record grounding or tool/function calling
(R-1); streaming token-by-token output, because a synchronous Apex callout returns one complete response (R-1);
markdown/HTML rendering of replies (R-1); stored transcripts, history across refresh or devices, export (R-9); file or
image input, voice (R-1); per-user usage metering, cost caps, or billing (R-4); automatic retry or fail-over to another
model/provider (R-4); Agentforce/Einstein integration, Slack/Experience Cloud/mobile-specific surfaces (R-8);
moderation beyond what xAI itself returns (R-1); production/managed-package release (R-11).

## Requirements

Each acceptance block gives: **Positive**, **Failure**, **Boundary** (each only where it adds something, else
`n/a: reason`), **Surface** (where observed) and **Confirm** (how). Surface key: *UI* = the chat page opened through the
Lightning entry as the named test user, in a browser; *Apex* = Apex tests run in the org with a mocked callout
(`HttpCalloutMock`); *Org* = metadata/permission queries with `sf` against the target org; *Live* = a real call to xAI
with a real key (needs G-2).

### R-1 Send a message and receive Grok's reply

- Basis: request words "Grok bot" (2026-11-21), A-1, A-2. Added; nothing preserved (greenfield). Limits: no live xAI
  observation exists yet (G-2, G-4).
- Behaviour: a user with access opens the chat, types a message, sends it (Send button or Enter; Shift+Enter inserts a
  newline), and the product shows the user's message, an in-progress indicator, then Grok's reply as a distinct bot
  message. The reply text shown is exactly the assistant text xAI returned for that request, unmodified except for
  surrounding whitespace trim.
- Boundary: the admin-configured system prompt (R-7) is sent as the system instruction on every request and is never
  shown as a chat message. The model used is the configured model. Only text is exchanged. Replies are displayed as
  text, never interpreted as HTML (see NFR-4).
- Error behaviour: R-3 (invalid input) and R-4 (upstream failure).
- Consumer outcome: the user sees a readable answer in the chat within the timeout of R-7, or a defined error (R-4).
- Acceptance:
  - R-1.a Positive: with the Apex callout mocked to return success text `Hello from Grok`, calling the chat method
    with message `Hi` returns reply `Hello from Grok`; the captured outbound request carries the configured model ID,
    the configured system prompt first, then user `Hi`, and an `Authorization` header supplied by the credential layer
    (not by Apex code). Surface: Apex. Confirm: Apex test asserting on the captured `HttpRequest` and the returned
    value (TC-1).
  - R-1.b Positive: in the UI as GrokBot Test User, typing `Reply with exactly the single word: pong` and pressing
    Enter shows the user bubble, then a bot bubble whose text contains `pong` (case-insensitive). Surface: UI + Live.
    Confirm: browser run with a real key; screenshot of the bot bubble (TC-2). Model output is nondeterministic, so the
    assertion is containment, not equality.
  - R-1.c Boundary: Shift+Enter inserts a newline and sends nothing; Enter on a composer holding `Hi` sends once.
    Surface: UI. Confirm: browser interaction with a stubbed Apex method or the live path (TC-3).
  - R-1.d Failure: n/a here; covered by R-3 and R-4 lines.
  - R-1.e Boundary: a reply containing the literal text `<img src=x onerror=alert(1)>` (mock body) renders as that
    visible text and executes nothing. Surface: UI with Apex stubbed to return it. Confirm: rendered-DOM assertion that
    the text is a text node and no `img` element exists inside the message (TC-4).

### R-2 Multi-turn conversation within a session, and Clear

- Basis: request words "bot" (conversation implied), A-2. Added. Limits: how xAI uses history is only observable Live.
- Behaviour: within one open chat the product keeps the transcript and sends the most recent history with each new
  message so Grok can answer in context. A **Clear** control (labelled "New chat") empties the transcript and the
  context immediately.
- Boundary (history window, default 20 non-system messages, configurable, R-7): each request carries the system prompt
  plus the most recent messages of the transcript, including the new user message, trimmed from the oldest end until
  the count is <= the window and the first retained message is a `user` message. The visible transcript is never
  trimmed; when messages fell outside the window a short note says earlier messages are no longer sent to Grok.
  Messages that failed (R-4) are shown but excluded from the history sent.
- Error behaviour: Clear while a request is in flight: see R-10.
- Consumer outcome: follow-up questions work; after New chat, Grok has no memory of the earlier chat.
- Acceptance:
  - R-2.a Positive (deterministic): mock returns `A1` then `A2`. Send `turn 1`, then `turn 2`. The second captured
    request has messages, in order: system prompt, user `turn 1`, assistant `A1`, user `turn 2`. Surface: Apex via the
    client-supplied history parameter, plus UI interaction asserting the UI sends that history. Confirm: Apex test on
    the request body; Jest test on the component's call arguments (TC-5).
  - R-2.b Positive (live): send `My favourite number is 42. Reply with OK.`, then
    `What is my favourite number? Reply with only the number.` The second reply contains `42`. Surface: UI + Live.
    Confirm: browser run (TC-6). Nondeterministic: assertion is containment.
  - R-2.c Boundary (window), exact: script messages `turn 1` .. `turn 12` with mock reply `ok n` after each, so before
    sending `turn 12` the transcript has 22 messages. The 12th request carries the system prompt plus exactly 19
    non-system messages, the first being user `turn 3`, the last user `turn 12`; the UI transcript still shows all 23
    messages after the reply and shows the "no longer sent" note. Walk: 22 + 1 = 23 messages; trimming from the oldest
    until <= 20 drops messages 1-3 (user 1, assistant 1, user 2) leaving 20 starting with assistant 2; first must be
    `user`, so assistant 2 is also dropped: 19 remain, starting at user `turn 3` (message 5 of 23). Surface: Apex
    (history param of 23 messages) and UI. Confirm: Apex test and Jest test (TC-7).
  - R-2.d Positive: after New chat the transcript is empty, the next request carries only the system prompt and the new
    user message. Surface: UI + Apex. Confirm: Jest + Apex (TC-8).
  - R-2.e Failure: history supplied with a role other than `user`/`assistant` (e.g. `system`) is rejected, nothing
    sent to xAI (the client is not trusted to inject instructions, AD-4). Surface: Apex. Confirm: Apex test calling
    the method directly with a `system` role entry, expecting code `INVALID_INPUT` and zero callouts (TC-9).

### R-3 Input validation

- Basis: A-8 bounds; standard defensive behaviour. Added.
- Behaviour: the message is trimmed of leading/trailing whitespace first. A message that is empty after trimming, or
  longer than the configured maximum (default 4,000 characters, counted after trim), is rejected before any call to
  xAI, with an inline message; the composer text is kept so the user can fix it; no transcript entry is added.
  Validation is enforced on the server too (the UI check is a convenience).
- Boundary: 4,000 characters accepted; 4,001 rejected.
- Acceptance:
  - R-3.a Failure: message `   ` (three spaces) → code `INVALID_INPUT`, zero callouts; UI shows "Enter a message" and
    no new bubble. Surface: Apex + UI. Confirm: Apex test (callout count 0 via the mock's invocation count) and Jest
    (TC-10).
  - R-3.b Boundary: a message of exactly 4,000 characters (`a` repeated) is sent; one of 4,001 is rejected with
    `INVALID_INPUT` and the UI displays the limit. Surface: Apex + UI. Confirm: Apex tests with both lengths; Jest on
    the character counter state (TC-11).
  - R-3.c Boundary: `"  hi  "` is sent as `hi`. Surface: Apex. Confirm: captured request (TC-12).
  - R-3.d Positive: n/a: the valid path is R-1.

### R-4 Upstream and platform failures are mapped to clear, safe errors

- Basis: any callout can fail; A-3. Added. Limits: real xAI error bodies and the exact way a missing credential
  principal surfaces in Apex are unverified (G-4, G-5).
- Behaviour: every failure of the call yields a stable error code and a fixed, user-readable message; the raw xAI error
  body, the API key, request body and stack traces are never shown. The user's message stays in the transcript marked
  "not answered" with a **Retry** control; the product does not retry automatically.
- Mapping (the code is a contract, the sentence text is not):

  | Condition | Code | User sees (gist) |
  | --- | --- | --- |
  | HTTP 401 or 403 | `CREDENTIALS_REJECTED` | Grok rejected the credentials; ask an admin |
  | HTTP 429 | `RATE_LIMITED` | Grok is busy or the key's limit is reached; try again shortly |
  | Other HTTP 4xx (e.g. 400, 404 unknown model) | `REQUEST_REJECTED` | Grok could not accept the request; ask an admin to check the model setting |
  | HTTP 5xx | `UPSTREAM_ERROR` | Grok is having trouble; try again |
  | Callout timeout (`CalloutException` read timeout) | `TIMEOUT` | Grok did not answer in time |
  | 2xx but no assistant text parseable | `BAD_RESPONSE` | Grok returned something unreadable |
  | Other `CalloutException` (named credential missing, endpoint not authorized, principal access missing) | `CALLOUT_FAILED` | The connection to Grok is not set up for you; ask an admin |
  | Configuration invalid or missing (R-7) | `NOT_CONFIGURED` | The bot is not configured; ask an admin |
  | Input rejected (R-2.e, R-3) | `INVALID_INPUT` | specific input message |

- Acceptance:
  - R-4.a Failure: mock status 401 → `CREDENTIALS_REJECTED`; 429 → `RATE_LIMITED`; 400 → `REQUEST_REJECTED`; 500 →
    `UPSTREAM_ERROR`; a thrown `CalloutException('Read timed out')` → `TIMEOUT`; status 200 with body `{}` →
    `BAD_RESPONSE`; other `CalloutException('Unauthorized endpoint')` → `CALLOUT_FAILED`. Surface: Apex. Confirm: one
    parametrised Apex test per row asserting the code (TC-13).
  - R-4.b Failure (safety): for status 401 with mock body containing the sentinel `SECRET-SENTINEL-123`, neither the
    returned error, the UI text nor any debug log line produced by the product contains that sentinel or the string
    `Bearer`. Surface: Apex + UI. Confirm: assert on the returned DTO; assert no `System.debug` content from product
    classes contains the sentinel by running the test with a log-capturing check where available, else by review of
    all log statements (TC-14).
  - R-4.c Positive (recovery): after a `RATE_LIMITED` failure the transcript shows `turn 1` marked "not answered" and
    Retry; pressing Retry re-sends the same text, and on success shows exactly one user bubble and one bot bubble for
    it (no duplicate). Surface: UI with stubbed Apex failing then succeeding. Confirm: Jest (TC-15).
  - R-4.d Boundary: a user who instead types a new message after a failure sends history that excludes the failed
    message (R-2). Surface: Apex/Jest. Confirm: request-capture assertion (TC-16).
  - R-4.e Failure (live, access): with the xAI key deliberately set to an invalid value, a real send shows
    `CREDENTIALS_REJECTED`'s message. Surface: UI + Live. Confirm: browser run; the key is restored afterwards. Owner
    of the key change: the org admin (G-2). Status: **cannot run here** (TC-17).
  - R-4.f Domain rule the request leaves out: no automatic retry, no secondary provider, no cost cap. Bounds R-4.

### R-5 Access is limited to users granted the product's permission set

- Basis: Salesforce platform conventions (`platforms/salesforce.md`: sharing, CRUD, FLS and tab/class/credential
  access are separate); A-6. Added. Limits: effective access of a given user is only observable with an org (G-1).
- Behaviour: one permission set (name per AD-6) is the only way to (a) see the chat app/tab, (b) call the product's
  server methods, (c) use the xAI credential principal. A user without it cannot open the chat page (the tab URL
  answers "Page does not exist" / the app is absent from App Launcher), cannot invoke the server method, and the
  callout is not authorized for them. Nothing in the product reads Salesforce records on the user's behalf (A-4), so
  there is no sharing/CRUD/FLS exposure to evaluate beyond reading the configuration; this is recorded as the sharing,
  object and field assessment: **sharing: n/a (no record access); object CRUD: n/a; FLS: n/a; configuration read is by
  trusted system code**.
- Acceptance:
  - R-5.a Positive: GrokBot Test User, assigned the permission set, opens `/lightning/n/GrokBot` and sees the chat.
    Surface: UI. Confirm: browser as that user + `sf data query` for the `PermissionSetAssignment` row (TC-18).
  - R-5.b Failure: GrokBot Blocked User (same profile, **no** permission set) opening the same URL does not see the
    chat; the app is absent from App Launcher; Org query shows no `SetupEntityAccess` row for the Apex class or tab for
    their permission sets. Surface: UI + Org. Confirm: browser + the read-only probes in `platforms/salesforce.md`
    "Consumer entry access" (TC-19).
  - R-5.c Failure: calling the server method as the blocked user (anonymous Apex run as that user, or a UI call) is
    denied by platform class access. Surface: Apex/Org. Confirm: Apex test using `System.runAs` with a user lacking the
    permission set expects an exception/denial rather than a reply (TC-20). Whether `runAs` plus mocked callout
    faithfully tests class-access denial is unverified; if not, replace with an Org probe on `SetupEntityAccess`.
  - R-5.d Boundary: the permission set grants nothing beyond the class, tab, app and credential principal (no object or
    field permissions, no "Modify All Data"). Surface: Org. Confirm: read the deployed permission set metadata (TC-21).
  - Open gap: who may assign the permission set and the identity of the two test users (G-6).

### R-6 The xAI API key is held only by the platform's credential store

- Basis: secret handling duty; AD-3. Added. Limits: key value is never read; only presence/absence of configuration is
  observable.
- Behaviour: the key is stored only in the org's external-credential facility, entered by an admin after deploy. It
  never appears in source files, repository history, configuration records, Apex or LWC code, test fixtures, run
  notes, logs, browser payloads or the UI. The browser never receives it and never calls xAI directly. A fresh deploy
  into an org without the key configured leaves the bot working up to the point of the call and failing with
  `CALLOUT_FAILED` or `CREDENTIALS_REJECTED` (R-4), not with a crash.
- Acceptance:
  - R-6.a Positive: a recursive text search of the deliverable's source tree finds no string matching an xAI key
    pattern (prefix `xai-`) and no literal `Bearer ` followed by a non-placeholder. Surface: repository. Confirm:
    `grep` with exit code recorded (TC-22).
  - R-6.b Boundary: in the browser's network log for one real send, the only product request goes to the Salesforce
    origin (the Apex/Aura endpoint) and no request goes to `api.x.ai`. Surface: UI + Live. Confirm: devtools network
    capture (TC-23).
  - R-6.c Failure: with the principal's key unset, a send yields code `CALLOUT_FAILED` or `CREDENTIALS_REJECTED`, whichever
    the org's behaviour produces (G-5), with the safe message. Surface: UI. Confirm: browser run before key entry
    (TC-24).
  - Pending prerequisite: an admin enters the key (person-only step, G-2). The run must never be handed the key value.

### R-7 Admin configuration

- Basis: A-8. Added.
- Behaviour: an org admin can change, in Setup and without a code deploy: the Grok model ID, the system prompt, the
  callout timeout, the maximum input length, and the history window. The deployed defaults are: system prompt "You are
  Grok, a helpful assistant inside Salesforce. Answer concisely." (assumption), timeout 60,000 ms, max input 4,000,
  window 20, model ID per G-3. Validation: timeout must be 1..120,000 ms (platform hard limit per-callout; cumulative
  120 s per transaction, one callout per transaction here); max input and window are positive integers; model and system
  prompt non-blank. Invalid or missing configuration yields `NOT_CONFIGURED` for the user and nothing is sent.
- Acceptance:
  - R-7.a Positive: change the model ID record value to `test-model-x`; the next captured request carries
    `test-model-x`. Surface: Apex (config injectable/test-settable) and Org. Confirm: Apex test (TC-25).
  - R-7.b Failure: timeout = 0 or 120,001, window = 0 or max input = -5 → `NOT_CONFIGURED`, zero callouts.
    Surface: Apex. Confirm: parametrised Apex test (TC-26).
  - R-7.c Boundary: timeout values 1 and 120,000 are accepted (no `NOT_CONFIGURED`) and the request is sent with that
    timeout. Surface: Apex. Confirm: the "accepted" half by Apex test (callout count 1); the "sent with that timeout"
    half by asserting the timeout on the captured request if the API exposes it, else by code inspection. It stays
    `NOT-REPLAYED` until G-7 settles whether the timeout is observable (TC-27a).
  - R-7.d Positive: a blank system prompt is rejected (not silently sent empty). Surface: Apex. Confirm: Apex test (TC-27).

### R-8 Consumer entry: Lightning app and tab

- Basis: request "Salesforce development org" (2026-11-21); `platforms/salesforce.md` (a component is not reachable until
  a tab/app exist and are granted). Added.
- Behaviour: after deployment and permission assignment, a user finds "Grok Bot" in App Launcher, opens the app, and
  lands on the chat page whose URL path is `/lightning/n/<TabApiName>` (name per AD-6). The page works inside the
  standard Lightning shell on a desktop browser; the page is also usable at phone width (NFR-4).
- Out of scope: Experience Cloud, Salesforce mobile app specifics, utility-bar or record-page embedding.
- Acceptance:
  - R-8.a Positive: `sf org list metadata --metadata-type CustomTab --target-org <alias>` lists the tab; the same for
    `CustomApplication` and `LightningComponentBundle`. Surface: Org. Confirm: command output at release-check (TC-28).
  - R-8.b Positive: as GrokBot Test User, App Launcher search `Grok` lists the app; opening it shows the chat page at
    the tab URL. Surface: UI. Confirm: browser with the final URL and screenshot (TC-29).
  - R-8.c Failure: before the permission set is assigned the same path says "Page does not exist" (R-5.b); this is the
    expected state, not a defect.

### R-9 Data handling: no stored conversation, disclosed third-party transfer

- Basis: A-4, A-5. Added.
- State owner and location: the transcript exists only in the open page's memory (AD-4); lifetime = until New chat,
  page reload, or navigating away from the page. Nothing is written to org records, files, cache or logs.
- Who may read: only the person at that browser. No other user, admin or process can read it from the org by design.
  Limitation (unverified, G-8): a Salesforce debug log with a trace flag may capture callout request/response bodies;
  the product itself must not write message text to logs, and the admin handbook (README) must say so.
- Behaviour: the UI shows, before the first message, a one-line notice that messages are sent to xAI and must not
  contain information the org's policy forbids sharing with xAI. Message text is sent to xAI only on an explicit Send.
  Nothing is sent on page load or while typing.
- Acceptance:
  - R-9.a Positive: opening the page produces zero callouts and shows the notice. Surface: Apex invocation count + UI.
    Confirm: Apex/Jest assertion that no server call occurs on load; screenshot (TC-30).
  - R-9.b Positive: the deliverable's source contains no custom object, custom field, Platform Cache partition, file
    or DML statement that stores conversation text, so no query of stored messages is possible. Surface: repository.
    Confirm: source inspection plus a grep for `insert`/`update`/`upsert` DML in product Apex with exit code recorded
    (TC-31).
  - R-9.c Boundary: reload the page; the transcript is empty. Surface: UI. Confirm: browser (TC-32).
  - R-9.d Failure: grep of product Apex for `System.debug` shows none that print message text, reply text, request or
    response bodies. Surface: repository. Confirm: grep exit code and reviewed list (TC-33).

### R-10 Concurrency: one request at a time per chat; stale replies are ignored

- Basis: state-ownership assessment (behavior-model guidance). Added.
- Behaviour: while a request is in flight the Send control and Enter-to-send are disabled and the indicator is shown, so
  a double click or Enter-Enter sends one request. Pressing New chat during flight clears the transcript immediately;
  when the in-flight reply later arrives it is discarded and not shown in the new chat (the call to xAI cannot be
  cancelled; it may still be billed, a stated limitation). The same applies to a late failure.
- Different users or different open tabs of one user are independent chats; they share only xAI's per-key rate limit
  (R-4 `RATE_LIMITED`).
- Acceptance:
  - R-10.a Boundary: double-clicking Send on `Hi` results in exactly one Apex invocation. Surface: UI (Jest with a
    stub whose promise stays pending). Confirm: invocation count = 1 (TC-34).
  - R-10.b Failure/stale: with the stub's promise pending, press New chat, then resolve the promise with `late reply`;
    the transcript stays empty. Same with a rejected promise: no error banner appears. Surface: UI. Confirm: Jest
    (TC-35).
  - R-10.c Positive: with two simultaneous chats from two users, each sees only their own transcript. Surface: Apex
    (stateless: no static/shared mutable state between invocations). Confirm: Apex test invoking twice with different
    histories and checking each request contains only its own history; review for absence of `static` mutable state
    (TC-36).

### R-11 Deliverable is deployable to a development org and tested

- Basis: request "in a Salesforce development org". Added.
- Behaviour: the product is a Salesforce DX source-format project. `sf project deploy validate` (dry run) then deploy to
  the named development org succeeds from a clean checkout; re-deploying is safe and does not erase the admin-entered
  key or admin-edited configuration beyond what the metadata deploy semantically replaces (see G-9). Apex unit tests
  cover R-1..R-4, R-7, R-9.d and R-10.c with a mocked callout; LWC Jest tests cover the UI behaviours of R-1.c/e, R-2,
  R-3, R-4.c-d, R-9.a/c, R-10.a-b. No test makes a live xAI call; Live checks are separate (TC-2, 6, 17, 23, 24).
- Acceptance:
  - R-11.a Positive: `sf project deploy validate --target-org <alias>` exits 0 with the deliverable. Surface: Org.
    Confirm: command, exit code, validated component count (TC-37).
  - R-11.b Positive: after deploy, `sf apex run test --target-org <alias> --class-names GrokBotController_Test
    --synchronous --result-format tap` prints only `ok` lines for all methods and none `not ok`. Surface: Org.
    Confirm: TAP output (TC-38). Apex coverage target: 75% org-wide is the platform deploy gate for production; for a
    development org the gate may not apply, and the product's own target is 85% on the product's classes (assumption
    A-9).
  - R-11.c Positive: LWC Jest suite exits 0 and runs the cases listed above. Surface: local. Confirm: `npm test` exit
    code and case list (TC-39).
  - R-11.d Failure: a name clash with an existing org component (G-1) is detected before deploy by the metadata
    listing, and the clashing name is changed. Surface: Org. Confirm: listing output (TC-40).
  - R-11.e Boundary: the project's `.gitignore` contains `.sf/` and `.sfdx/` (tool state) (TC-41).
  - A-9 Coverage target 85% on product classes is an assumption; no requirement of the request.

## Behaviour model

Actors: **User** (end user in browser), **UI** (the chat page), **Server** (the product's server method, stateless),
**Config** (admin configuration), **Credential** (platform credential layer), **xAI** (external), **Admin**.

### Flows

- **F-1 Send and reply** (R-1, R-2, R-3, R-4, R-10). User → UI: Send. UI: validate locally (T-6 on fail); append user
  message, set Pending, disable Send (T-1). UI → Server: message + windowed history. Server: validate role/size
  (reject → `INVALID_INPUT`), read Config (invalid → `NOT_CONFIGURED`), build request (system prompt + history +
  message, model, timeout). Server → Credential → xAI: HTTPS call (synchronous). xAI → Server: status+body. Server:
  map per R-4 table; on success return reply text. UI: if its request token is still current, append bot message,
  clear Pending (T-2) else discard (T-5). On failure: mark user message "not answered", show error, clear Pending (T-3).
- **F-2 Retry** (R-4.c): User → UI Retry on a failed message → same as F-1 for that text without appending a second user
  bubble (T-8).
- **F-3 New chat** (R-2.d, R-10): User → UI: New chat → transcript empty, token invalidated (T-4 from Idle/Empty, T-5
  from Pending).
- **F-4 Admin setup** (R-5, R-6, R-7): Deployer deploys metadata → Admin enters key in Setup → Admin assigns the
  permission set to users → User opens app (R-8).

### State inventory

| Entity | States | Owner / durability |
| --- | --- | --- |
| Chat (one per open page) | Empty, Idle (has messages), Pending (request in flight) | UI memory; transient (lost on reload) |
| Message (in transcript) | Sent-answered, Not-answered (failed, retry offered), Bot reply | UI memory; transient |
| Request token | current / superseded | UI memory; transient |
| Configuration | valid / invalid | org metadata record; durable; Admin-edited |
| xAI key | configured / not configured | credential store; durable; Admin-owned; never read back |
| Permission assignment | assigned / not assigned | org; durable; Admin-owned |

No state is shared between users. Simultaneous changes: a single chat is single-writer (its own user); the guard
"Pending disables Send" removes double submission; New chat during Pending resolves by token supersession (last user
action wins). Config edited mid-request: the in-flight request uses the values read at its start; later requests use
the new ones.

### Transition ledger

| ID | R / F | Before | Trigger & guard | After & observation | Failure / recovery | Cases |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | R-1, R-10 / F-1 | Empty or Idle | Send; message valid after trim | Pending; user bubble added; Send disabled; callout starts | Server failure → T-3 | TC-1,2,3,34 |
| T-2 | R-1 / F-1 | Pending | success, token current | Idle; bot bubble appended | n/a | TC-1,2,5 |
| T-3 | R-4 / F-1 | Pending | failure, token current | Idle; user message marked not-answered; error shown; Retry offered | user retries (T-8) or continues | TC-13,15 |
| T-4 | R-2 / F-3 | Empty or Idle | New chat | Empty; history cleared | n/a | TC-8 |
| T-5 | R-10 / F-3 | Pending | New chat (or late result with stale token) | Empty; late success/failure discarded silently; xAI effect not undone | accepted limitation | TC-35 |
| T-6 | R-3 / F-1 | Empty or Idle | Send; empty or too long after trim | unchanged transcript; composer kept; inline message; no callout | n/a | TC-10,11 |
| T-7 | R-10 / F-1 | Pending | Send or Enter | ignored; no second request | n/a | TC-34 |
| T-8 | R-4 / F-2 | Idle with a not-answered message | Retry | Pending; same text re-sent; no duplicate bubble; on success message becomes answered | failure → T-3 again | TC-15 |

Invalid event classes audited: Send while Pending (T-7); New chat while Pending (T-5); Retry on an answered message
(control not offered); empty/over-length (T-6); duplicate Enter (T-7); timeout/exhaustion (T-3 via `TIMEOUT`, no auto
retry); cancellation (not offered, T-5 discards only); restart/resumption (page reload resets to Empty, R-9.c);
partial effect (xAI processed but response lost: shown as failure, the user may retry and may be billed twice, stated
limitation); stale callbacks (token, T-5); concurrent actors (independent chats); expiry (none: no stored state).
Excluded with reason: stored-data migration/deletion (no stored data); bulk DML (no DML).

## Traceability: request outcomes to acceptance lines

| Request outcome | Requirement | Acceptance lines |
| --- | --- | --- |
| "Grok": talks to xAI's Grok | R-1, R-6, R-7 | R-1.a, R-1.b, R-6.a-c, R-7.a |
| "bot": multi-turn conversation | R-2 | R-2.a-e |
| bot behaves safely on bad input / failure | R-3, R-4 | R-3.a-c, R-4.a-e |
| "in a Salesforce ... org": reachable inside the org | R-8, R-5 | R-8.a-c, R-5.a-d |
| "development org": deployable, testable | R-11 | R-11.a-e |
| (implied) privacy / no stored data | R-9 | R-9.a-d |
| (implied) no double submit / stale replies | R-10 | R-10.a-c |

Every request outcome has at least one acceptance line. No modelled feature lacks a request or documented-assumption
origin (A-1..A-9).

## Service boundary: xAI API (the only external boundary)

- Authority: xAI owns generation; the org owns the key's custody and the chat's display. Reuse (platform callout +
  credential facility), configure (Named/External Credential, config record), extend (Apex adapter); no new
  component.
- Current authority per request: every call is made at user action time with the credential principal of the running
  user's permission set; there is no cached authorization. Revoking the permission set (or the key) takes effect on the
  next callout: freshness = every call. No cache of replies or tokens exists (A-5): **cache: n/a**.
- Incremental state / async: the call is synchronous inside the user's request; there is no background job, queue or
  webhook. Unknown outcome (timeout after xAI may have processed): shown as `TIMEOUT`; the user may retry; duplicate
  billing possible; exactly-once is not promised. Idempotency: none; xAI is not asked to dedupe.
- Recovery owner: the user (Retry) and the Admin (key/config/permissions). Worker crash: n/a (no worker).
- Owned event coverage: no audit trail of conversations (A-5). Failure outcomes are observable to the user by code.
  Operator visibility into failures is **unresolved**: whether to log a sanitized code-only line (error code, no
  content) and where is an open user decision (G-10); default: the product writes no log lines, and R-9.d/R-4.b stay
  satisfied either way.
- xAI limits: per-team, per-model request and token rate limits apply across all org users sharing one key
  (docs.x.ai rate-limits page via search; values per account in the xAI console, not asserted here).
- Apex limits (Apex Developer Guide, "Callout Limits and Limitations"): <=100 callouts/transaction (this product uses
  1), <=120 s cumulative (default timeout 60 s leaves headroom), no callout after uncommitted work (product has no DML).

## Non-functional requirements

- **NFR-1 Latency and timeout (observable bound):** the user sees a result (reply or error) no later than the configured
  callout timeout plus platform overhead. Bound: callout timeout <= 120,000 ms, the Apex hard limit; default 60,000 ms.
  Verification: Apex test sets timeout, mock throws a timeout; Live check records elapsed time for one send (TC-2).
  No latency target for xAI itself is invented; model speed varies by model.
- **NFR-2 Capacity:** per transaction one callout, no DML, no SOQL on user data; synchronous governor use is therefore
  minimal. Throughput across users is bounded by the xAI key's rate limit (unresolved number, G-4). No load test
  planned; justified exclusion: user-initiated, low-volume interactive chat in a development org. Revisit if the
  product leaves a development org.
- **NFR-3 Security and privacy:** R-5, R-6, R-9. Plus: model output untrusted (rendered as text, AD-8; TC-4); server
  validates client-supplied history roles and sizes (TC-9); system prompt is never taken from the client; error
  responses never echo xAI bodies (TC-14). Data sent to xAI is only the user's typed text, history and configured
  prompt (A-4). Retention: nothing retained by the product; xAI's own retention is outside this spec and is an
  unresolved policy matter for the org owner (G-8).
- **NFR-4 Interface quality (deliverable has a UI).** Visual reference: platform conventions take precedence (the chat
  lives inside the Lightning Experience shell), so the interface uses Salesforce Lightning Design System components and
  styling hooks/tokens. Starting appearance for unspecified choices, from the ShipLoop light expressive profile adapted
  inside SLDS: airy light canvas, tonal rounded message surfaces, one restrained saturated accent, confident type
  hierarchy, short purposeful motion; the primary activity (readable message groups and a reachable composer) gets the
  strongest position. Signature element: distinct, rounded bot vs user message bubbles with an integrated "Grok is
  thinking" indicator. Observable criteria:
  - NFR-4.a consistent visual system from tokens (spacing and type scales, palette) in one place, with no raw hex
    colors in component CSS outside token definitions. Check: CSS inspection.
  - NFR-4.b light theme by default with dark support by inheriting the org/user theme through styling hooks and not
    hard-coded colors (whether the org offers a dark theme is unverified, G-11). Check: render in light; if dark is
    available render in dark; no unreadable text.
  - NFR-4.c designed empty (welcome text, notice from R-9, suggested nothing-to-send state), loading (thinking
    indicator, disabled Send, `aria-busy`/live region), error (code-specific message with Retry) and "earlier messages
    not sent" states. Check: render each state, screenshot (TC-42).
  - NFR-4.d layout works at 360 px and 1440 px widths with no horizontal scroll, composer reachable at both. Check:
    browser at both widths (TC-43).
  - NFR-4.e keyboard: Tab order reaches the transcript, composer, Send, New chat; visible focus ring on each; Enter sends,
    Shift+Enter newline; WCAG 2.1 AA contrast for text and controls; accessible names on icon buttons; new bot replies
    announced via a polite live region. Check: keyboard walkthrough, automated axe-style check where available (TC-44).
  - NFR-4.f motion only to explain change (appearance of a bubble, indicator) and disabled under `prefers-reduced-motion`.
    Check: media-emulation run (TC-45).
  - NFR-4.g one icon set (SLDS utility icons). Check: inspection.
  - NFR-4.h the transcript scrolls to the newest message after each append without trapping focus. Check: browser.
- **NFR-5 Compatibility:** latest Chrome and Safari desktop and a phone-width viewport inside Lightning Experience; API
  version = the target org's current supported version (read at plan, G-7). Salesforce mobile app, Experience Cloud
  excluded (R-8).
- **NFR-6 Operability:** deploy is repeatable (R-11); post-deploy admin steps (key entry, permission assignment) are
  documented in the product README as an ordered runbook with who performs each. Observability of failures per the
  service-boundary section (G-10). Rollback: metadata can be removed by deleting the app, tab, permission set,
  credentials and Apex via destructive deploy; no data to recover. Deleting happens only on explicit user decision.
- **NFR-7 Maintainability / testability:** Apex callout code isolated in one service class with the callout mockable; all
  Apex tests use `HttpCalloutMock`, none hit the network (no `seeAllData`). Bulk safety: n/a, no DML and a single-call
  entry point; justified, not a collection-based entry point.

## State and data assessment

| Resource | Target identity | Changed / observed / out of scope | Invariant before → after | Recovery | Check |
| --- | --- | --- | --- | --- | --- |
| Transcript | the open page, per user | created and destroyed in browser memory | empty → N messages → empty on New chat/reload | none needed | TC-8, 32 |
| Org records (any object) | any | **out of scope**, never read or written | unchanged | n/a | TC-31 |
| Product metadata (class, LWC, tab, app, perm set, credentials, config record) | the dev org (G-1) | created/updated by deploy | absent → present; redeploy preserves unrelated org state | destructive deploy (user decision) | TC-28, 37 |
| xAI key | principal of the external credential | changed by Admin only | unset → set; never read back | Admin re-enters | TC-24, 17 |
| Permission assignments | named test users | changed by Admin only | none → assigned | Admin unassigns | TC-18, 19 |

Deploy of a changed permission set or credential metadata could reset assignments or a principal's stored value;
whether a redeploy preserves the entered key is unresolved (G-9, AD-3); until known, the runbook says re-check the key
after each deploy. Release/promotion containment: development org only; stop condition = `deploy validate` non-zero.

## Interaction-design assumptions (state lifecycle in proportion)

Owner/location, readers, concurrency, lifetime and quotas are in the state inventory and R-9/R-10. Personal data: the
user's typed text is shown in their browser, sent to xAI, and not stored, logged (by the product) or retained; removal
= close/reload/New chat. No identity, sharing or persistence is added beyond the org's own login (A-6). Truthful async
feedback: the UI shows "thinking" only while a request is truly in flight, and never shows a reply as delivered if the
call failed; a failed message is labelled "not answered", not silently dropped.

## Open gaps (each keeps only the dependent work unready)

- **G-1 Target org** (R-5, R-8, R-11): which development org/alias, its API version, installed packages, existing names.
  Owner: user. Confirm: `sf org list` (alias only) and metadata listings (`LightningComponentBundle`, `CustomTab`,
  `CustomApplication`, `ApexClass`, `PermissionSet`). Blocks: deploy and every Org/UI/Live case. Metadata and Apex work
  can be built and unit-tested without it.
- **G-2 xAI API key and who enters it** (R-1.b, R-2.b, R-4.e, R-6, TC-2/6/17/23/24): person-only step by the Admin; the
  run is never given the value. Until done, Live cases are **unverified** with owner Admin, due phase release-verify.
- **G-3 Current Grok model ID** (R-7 default): read from docs.x.ai/developers/models or the xAI console; search results
  disagree (grok-4.3 ... grok-4.7). Interim: the deliverable ships a placeholder default that research replaces; a bad
  model yields `REQUEST_REJECTED` (R-4).
- **G-4 xAI wire shape and error bodies** (AD-2; R-1.a, R-4): Responses vs Chat Completions, success and error JSON.
  Confirm by one authorized probe per endpoint. Affects only the request builder, parser and mock bodies.
- **G-5 How a missing credential principal surfaces in Apex** (R-4, R-6.c): exception type/message unknown. Confirm in
  the org by calling with no principal access. Interim: any non-HTTP `CalloutException` maps to `CALLOUT_FAILED`.
- **G-6 Test users and permission assignment** (R-5): usernames for GrokBot Test User and GrokBot Blocked User and who
  creates them; creating users/assigning is Admin authority, not a step to take unasked.
- **G-7 API-level facts** (R-7.c, NFR-5): whether `HttpRequest` exposes the timeout for assertion; org API version.
- **G-8 Third-party data policy** (R-9, NFR-3): whether the org owner permits sending text to xAI, xAI retention terms,
  and whether debug logs capture callout bodies. Owner: user/org owner.
- **G-9 Redeploy behaviour for credential/permission metadata** (R-11, AD-3).
- **G-10 Failure logging destination** (service boundary): none by default; decision for the user if wanted.
- **G-11 Dark theme availability in the target org** (NFR-4.b).
- **User decisions to confirm (assumptions, defaults taken):** A-3, A-4 (no CRM data), A-5 (no transcripts), A-7 (plain
  text), A-8 (20 / 4,000 / 60,000 ms), A-9 (85%).

## Retired

None. (First specification; no earlier R-<n> existed.)

## Replay and verification record (duty 10)

No case could be replayed: there is no org, key or app code. Each is `NOT-REPLAYED: no target org (G-1)` or
`NOT-REPLAYED: no xAI key (G-2)` unless noted. Walks done on paper:
- R-2.c windowing: recomputed above (23 messages, 19 retained, first `turn 3`); this arithmetic is the oracle the Apex
  and Jest tests must reproduce; it is derived from the trim rule in R-2, not from running code.
- R-5.b/R-8.c: start state reachable only after the Admin creates the blocked user (G-6); the "Page does not exist"
  result is documented in `platforms/salesforce.md` (Consumer entry access), not observed.
- R-7.c: the oracle may not be observable through the mock (G-7), so it stays open.
- Weak stand-ins ruled out: R-1.a asserts request content, not just a non-null return; R-4.a asserts a distinct code
  per row; R-3 asserts zero callouts (not just an error); R-10.a asserts invocation count = 1, not UI text.
- Claims about platform capability with sources: callout limits (Apex Developer Guide, fetched via search 2026-11-21);
  Named/External Credential principal-to-permission-set model (Salesforce docs via search); xAI endpoint, Bearer auth,
  legacy status of Chat Completions (docs.x.ai via search). Not verified by probe: Apex `callout:` URL syntax detail
  (taken from general knowledge, flagged), debug-log capture of callout bodies (G-8), `runAs` class-access test (R-5.c).
- Documented commands (`sf project deploy validate`, `sf apex run test ... --result-format tap`) were **not run**: the
  `sf` CLI exists on this machine but no org target is chosen and running org commands needs the user's approval; no
  exit code is claimed.

## Submission

- `summary`: First specification of a Grok chat bot delivered as Lightning web component + Apex callout to xAI inside
  a Salesforce development org: 11 requirements (R-1..R-11), flows F-1..F-4, transitions T-1..T-8, 45 planned cases
  (TC-1..TC-45), NFRs 1-7 including a UI quality NFR, decisions AD-1..AD-8 in `architecture.md`. Open: the request is
  ambiguous, so interpretations A-1..A-9 are recorded as assumptions to confirm (no CRM data, no stored transcripts,
  plain-text replies, defaults 20 messages / 4,000 chars / 60 s); G-1 target org and G-2 xAI key are person-only
  prerequisites that keep deploy and all Live cases unready; G-3/G-4 (model ID, xAI wire shape) keep only the request
  builder/mock bodies unready. No material requirement conflict. Nothing was executed or probed; every acceptance line
  is planned, not run.
- `primary`: R-1, R-2, R-8, R-11 (also R-6, which is needed for R-1 to work against real Grok).
- `evidence_refs`: KNOWLEDGE/spec.md (all `### R-` sections, Behaviour model, NFRs, State and data assessment, Open
  gaps), KNOWLEDGE/architecture.md (AD-1..AD-8), GUIDES/platforms/salesforce.md, GUIDES/platforms/ui.md#light-expressive-starting-point,
  GUIDES/service-discovery.md, GUIDES/behavioral-requirements.md, GUIDES/requirements-definition.md; external:
  Salesforce Apex Developer Guide "Callout Limits and Limitations"
  (developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_callouts_timeouts.htm), Salesforce Named
  Credentials Glossary
  (developer.salesforce.com/docs/platform/named-credentials/references/named-credentials-reference/nc-glossary.html),
  Salesforce ExternalCredential Metadata API reference, xAI docs (docs.x.ai REST API reference, Chat Completions legacy
  page, rate-limits page). No `backchain-check` receipt (command not available in this run; duty 11 omitted).
