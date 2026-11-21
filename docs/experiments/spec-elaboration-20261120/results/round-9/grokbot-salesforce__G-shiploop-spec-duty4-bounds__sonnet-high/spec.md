# Grok Bot for Salesforce — Product Specification

Status: draft for planning. No product code, tests, org inspection or live xAI call existed when this was written
(spec stage run on its own; see "Evidence limits"). Technology and structure choices live in
`KNOWLEDGE/architecture.md` as AD-<n>; this file holds product requirements only.

## Request and interpretation

Source S-1 (user request, 2026-11-21): "Create a Grok bot in a Salesforce development org."

The request names a product (a Grok bot), a host (a Salesforce development org) and nothing else. Interpretation
A-1 (assumption, see `## Submission`): a **conversational assistant inside the org, answered by xAI's Grok model**,
used by a signed-in Salesforce user in a chat panel opened from the Lightning App Launcher. It is not Salesforce's own
Einstein/Agentforce bot, not a Slack/Messaging-channel bot, and does not read or write Salesforce records.
This reading is reversible: if the user meant another bot type, R-1..R-3 are the clauses to revisit.

Actors: **Chat user** (a Salesforce user holding the Grok Bot access grant), **Org admin** (deploys, grants access,
enters the xAI API key), **xAI Grok service** (external; sole authority for reply content).
Entities: chat panel session (transcript, context), bot configuration, xAI API key, access grant.

## Requirements

Each requirement lists: behaviour, boundaries, error behaviour, consumer outcome; then acceptance lines (AC). An AC says
what is expected (positive / failure / boundary, each only where it adds something), the surface where it is observed
and how it is confirmed. Surfaces: **Apex test** = Apex test run in the dev org with a mocked HTTP callout that
captures the outgoing request (remote test, TAP result); **Jest** = LWC unit tests; **Browser** = the Lightning tab in the
dev org as the intended user; **Live** = one real call to xAI with the person-supplied key; **Metadata** = read-back of
deployed metadata/permission state from the org.
Each R also carries: Basis (source that stays true), Preserved/changed (all `add`: no prior product), Locators,
Evidence limits, Pending (implementation and checks, all not yet done).

### R-1 Chat panel is reachable by assigned users — PRIMARY
- **Behaviour:** an assigned user opens a "Grok Bot" entry from the Lightning App Launcher and sees a chat panel: transcript
  area, message composer, send control, "New chat" control and a one-line notice that messages are sent to xAI Grok.
- **Boundaries:** one panel per open tab; no other entry point (record pages, mobile app, Experience Cloud) is in scope.
- **Error behaviour:** a user without the grant sees "Page does not exist"/no App Launcher entry; they get no
  partial panel (see R-9).
- **Consumer outcome:** the user reaches the panel by URL path `/lightning/n/<tab API name>` and by App Launcher search.
- **AC R-1.1** positive — as the verification user (grant assigned), App Launcher lists the Grok Bot entry; opening it
  renders composer, send, New chat and the egress notice. Surface: Browser. Confirmed by: browser check at the tab path
  recorded in release-plan.
- **AC R-1.2** failure — as a user with no grant, the tab path answers "Page does not exist" and App Launcher does not list
  the entry. Surface: Browser; Metadata (`PermissionSetTabSetting` has no row for that user). Confirmed by: both.
- **AC R-1.3** boundary — n/a: the panel has no numeric boundary at the entry.
- Basis: S-1. Locators: `GUIDES/platforms/salesforce.md` "Service discovery" (consumer entry is metadata, grant is separate).
  Evidence limits: no org read yet. Pending: tab/app/permission-set metadata, browser check.

### R-2 A message gets a Grok reply — PRIMARY
- **Behaviour:** when the user submits a valid message (R-4), the panel shows it in the transcript, shows pending
  feedback (R-11), calls xAI once, and appends Grok's reply as a plain-text assistant message.
- **Boundaries:** exactly one xAI request per submission; no automatic retry (R-7); reply text is rendered as plain text
  (no HTML, no Markdown rendering) with line breaks preserved; token streaming is out of scope (reply appears whole).
- **Error behaviour:** see R-7. **Consumer outcome:** the reply is visible below the user's message and the composer is usable again.
- **AC R-2.1** positive — with the live key, submitting `Reply with exactly the word: pong` yields a non-empty assistant
  message (content is model-dependent and is NOT asserted beyond non-empty). Surface: Browser + Live. Confirmed by: browser check
  during release-verify; the exact reply text is recorded as an observation, not an oracle.
- **AC R-2.2** positive (deterministic) — with the xAI response mocked as an assistant message `pong`, the transcript shows
  user `ping` then assistant `pong`, and the captured outgoing request carries `ping` as the final user input, the configured
  model id and the output cap (R-6). A hardcoded reply would fail because the mock reply is varied per case (`pong`, `pong2`).
  Surface: Apex test (request capture + returned DTO) and Jest (render). Confirmed by: TAP `ok` lines + Jest run.
- **AC R-2.3** boundary — a reply containing `<img src=x onerror=alert(1)>` is shown as literal text and no element is created.
  Surface: Jest (DOM query) and Browser. Confirmed by: both.
- **AC R-2.4** failure — n/a here: all failure outcomes are R-7.
- Basis: S-1. Locators: xAI inference API reference (`docs.x.ai/developers/rest-api-reference/inference/responses`, `.../chat-completions`).
  Evidence limits: request/response field names are from documentation search snippets, not a probe (G-4). Pending: all.

### R-3 The bot keeps context within one chat session — PRIMARY
- **Behaviour:** replies take earlier completed exchanges of the same session into account. A completed exchange is a
  user message that received an assistant reply. "New chat" empties transcript and context.
- **Boundaries:** context lives only in the open panel (browser memory); reload, navigating away or closing the tab
  ends it; nothing is stored in the org (see R-8). Context sent per request is bounded by R-5.
- **Error behaviour:** a user message whose request failed is shown in the transcript marked failed but is excluded from
  context. **Consumer outcome:** follow-up questions work; a fresh chat starts blank.
- **AC R-3.1** positive — after `My name is Ada.` → reply, then `What is my name?`, the second outgoing request lists, in order:
  user `My name is Ada.`, assistant (the first reply), user `What is my name?`. Surface: Apex test (request capture); Jest
  (what the component passes to Apex). Live: the reply to the second message is observed to mention Ada (observation only).
- **AC R-3.2** failure — user message `u2` fails (R-7); next message `u3` is sent with context `[u1, a1, u3]` (does not contain `u2`);
  transcript still shows `u2` marked failed. See walk W-3. Surface: Jest + Apex test.
- **AC R-3.3** boundary — "New chat" while idle clears transcript and context and returns to the empty state; the next request
  carries only the new message. "New chat" is disabled while a request is pending (W-4). Surface: Jest + Browser.
- **AC R-3.4** boundary — reload of the tab shows an empty panel (no stored transcript). Surface: Browser.
- Basis: S-1 ("bot"); A-1; decision: no persistence (default D-persist, `## Submission`). Evidence limits: none beyond R-2.
  Pending: all.

### R-4 Message input validation
- **Behaviour:** leading and trailing whitespace is trimmed; the trimmed message must be 1..Max_Message_Chars characters.
  Length is counted in UTF-16 code units (`String.length()` in both Apex and JavaScript, so an emoji counts 2).
- **Boundaries (default, see Bounds table):** Max_Message_Chars = **4,000**. Exactly 4,000 accepted; 4,001 rejected.
- **Error behaviour:** rejected input makes no xAI call, adds nothing to the transcript, leaves the composer text in place and
  shows an inline message (`Message is empty` / `Message is longer than 4,000 characters`). The same rule is enforced again
  in Apex, so a caller bypassing the UI gets the same rejection and no callout.
- **Consumer outcome:** a character counter appears as the composer approaches the limit; send is disabled for invalid input.
- **AC R-4.1** boundary — inputs `""`, `"   "` rejected (empty); `"a"` accepted; 4,000×`a` accepted; 4,001×`a` rejected;
  `"  "+4,000×a+"  "` accepted (trimmed to 4,000). Walk W-1. Surface: Apex test (direct call, assert no callout made for
  rejects) and Jest (send disabled, no Apex call).
- **AC R-4.2** failure — direct Apex call with 4,001 chars throws/returns the defined validation error and the mock records
  zero callouts. Surface: Apex test.
- Basis: S-1; the cap is a functional safety default (Bounds table B-1). Evidence limits: the 4,000 value has no external source.
  Pending: all.

### R-5 Context sent to Grok is bounded and trusted only after validation
- **Behaviour:** per request the Apex side assembles the context from the client-supplied completed exchanges plus the new
  message. Rule: keep at most **20** messages (Max_History_Messages, including the new message) and at most **100,000**
  characters total (Max_Context_Chars); drop the **oldest whole exchange** repeatedly until both hold, so the first retained
  message is always a user message. The new message is never dropped.
- **Boundaries:** 20 messages exactly is kept; 21 triggers a drop of one exchange (leaving 19). 100,000 characters exactly is
  kept; 100,001 drops the oldest exchange. The transcript on screen still shows dropped messages, with a divider
  "Earlier messages are no longer used as context".
- **Error behaviour (client-supplied history is untrusted):** history entries with a role other than `user`/`assistant`
  (e.g. `system`), a non-alternating order, or blank content cause the request to be rejected with the defined validation
  error and no callout. The system instruction comes only from configuration (R-10).
- **Consumer outcome:** long conversations keep working; the user is told when the context is trimmed.
- **AC R-5.1** boundary — walk W-2: after 10 exchanges (u1/a1…u10/a10), sending `u11` yields a 19-message request starting at
  `u2` and ending at `u11`. Surface: Apex test (request capture); Jest (divider shown).
- **AC R-5.2** boundary — walk W-5/W-6: character bound at 100,000 kept, 100,001 trims one exchange; with the count raised to 40
  and 8,000-char assistant replies, the request holds 17 messages totalling exactly 100,000 characters. Surface: Apex test.
- **AC R-5.3** failure — a request whose history contains a `system` entry, or two consecutive `user` entries, is rejected
  with zero callouts. Surface: Apex test.
- Basis: S-1 ("bot" needs bounded context to run safely); Bounds table B-2, B-3. Evidence limits: the xAI model's context window
  is unverified; 100,000 characters (~25k tokens at ~4 chars/token, an estimate) is assumed to fit. Pending: all.

### R-6 Reply bounds: output cap, time limit, response handling
- **Behaviour:** each xAI request asks for at most **1,024** output tokens (Max_Output_Tokens) and the callout waits at most
  **60 seconds** (Timeout_Seconds). The bot makes exactly one callout per submission (platform ceiling: 100 callouts per
  transaction, 120 s cumulative).
- **Boundaries:** a reply cut off by the cap is shown with the visible note "Reply was cut off at the length limit"
  when xAI reports the response as incomplete (the exact incompleteness field is unverified, G-4; if xAI gives no such
  signal the note cannot be shown and the gap is recorded). A reply arriving at 60 s or later is not shown (R-7 timeout).
  Callout payloads stay far below the 6 MB synchronous request/response limit (worst case request ≈ 100,000 chars ≈ 0.4 MB UTF-8).
- **Error behaviour:** response body that is not parseable, or contains no assistant text, is an error (R-7), never an
  empty assistant bubble.
- **AC R-6.1** positive — captured outgoing request contains the configured model id and `max_output_tokens`-equivalent =
  1,024 and a callout timeout of 60 s. Surface: Apex test (request capture; the timeout is observed through a test seam that records the
  value passed to the request, since an Apex getter for it is unverified).
- **AC R-6.2** boundary — mock returns incomplete-status response → assistant message shown with the cut-off note; mock returns
  complete → no note. Surface: Apex test (DTO flag) + Jest. Marked unverified against the real API until G-4 is closed.
- **AC R-6.3** failure — mock returns `200` with body `{}` → defined "empty reply" error; mock returns non-JSON → "unreadable
  reply" error; neither adds an assistant message. Surface: Apex test.
- Basis: S-1; Bounds table B-4, B-5. Evidence: Salesforce callout docs (default timeout 10 s, max 120 s per callout and 120 s
  cumulative, 100 callouts, 6 MB sync payload). Pending: all.

### R-7 Failure behaviour is visible, specific and non-destructive
- **Behaviour:** each failure class produces a distinct inline error under the failed user message, with a **Retry** action
  that resubmits that text as a new request (not a replay of the old one), and never shows the API key, a stack trace or
  the raw upstream body.
- **Boundaries — failure classes and messages:**

  | Class | Trigger | User-visible message |
  | --- | --- | --- |
  | not-configured | no API key stored, or config invalid (R-10) | "Grok Bot isn't set up yet. Ask your admin." — no callout is attempted when config is invalid |
  | auth | xAI HTTP 401 or 403 | "Grok rejected the credentials. Ask your admin to check the API key." |
  | rate-limited | xAI HTTP 429 | "Grok is rate-limited right now. Wait a moment and try again." |
  | upstream | xAI HTTP 5xx | "Grok is unavailable (error <status>). Try again." |
  | timeout | no response within Timeout_Seconds (60 s) | "Grok did not answer in 60 seconds. It may still have processed your message; try again." |
  | unreadable | R-6.3 cases | "Grok sent a reply that could not be read." |
  | other-4xx | any other 4xx | "Grok could not process this request (error <status>)." |
  | denied | caller lacks access (R-9) | "You don't have access to Grok Bot." |

- **Error behaviour:** no automatic retry (a second 60 s attempt would exhaust the 120 s cumulative callout budget and
  doubles cost); the outcome of a timed-out request is **unknown** (xAI may have completed it) and the message says so.
  The failure never clears the transcript and the composer becomes usable again.
- **Consumer outcome:** the user can tell which class occurred and what to do next.
- **AC R-7.1** failure — for each of the eight rows, mock the trigger (status 401, 403, 429, 500, 503, 418, timeout via
  `CalloutException` read-timeout, `{}` body, key missing) and assert the class and message text; 401 and 403 map to `auth`,
  418 to `other-4xx`. Surface: Apex test (class returned) + Jest (message rendered). Confirmed by: TAP + Jest.
- **AC R-7.2** failure — the rendered error, the Apex return value and the debug log lines contain neither the key value nor the
  raw response body for any case. Surface: Apex test (assert on strings), Browser (DOM text). Confirmed by: both.
- **AC R-7.3** boundary — Retry after a failure sends one new request with the same text and context per R-3.2; exactly one
  callout is made. Surface: Jest + Apex test.
- **AC R-7.4** failure — real 401 observed once with a deliberately wrong key to confirm status mapping against the
  real service (G-2). Surface: Live. Confirmed by: person-supplied key; otherwise remains unverified.
- Basis: S-1; platform behaviour of callout timeouts. Pending: all; Live check waits on G-2.

### R-8 Secret and conversation data handling
- **Behaviour:** the xAI API key exists only in the org's secret-credential facility (AD-3): never in source, metadata
  files, custom settings, the browser, Apex return values, debug logs or the transcript. Chat content is not stored in the org
  and not written to logs; the debug log records only outcome class, HTTP status, latency in ms and message counts.
  Requests ask xAI not to store the exchange (default; unverified until G-4); xAI's own retention policy applies beyond that (G-7).
- **Boundaries:** egress is disclosed in the panel (R-1). No Salesforce record data is read or sent; only text the user types
  and the configured system instruction leave the org.
- **Error behaviour:** if logging would require content, it is omitted. **Consumer outcome:** admin can rotate the key by
  editing the credential, with no code change or redeploy.
- **AC R-8.1** positive — repository scan of the deliverable (all source and metadata files) finds no string matching the
  xAI key format and no key literal; the credential metadata has a placeholder, not a value. Surface: repo grep (local) +
  Metadata. Confirmed by: grep result recorded.
- **AC R-8.2** positive — Apex test sends message `SECRET-MARKER-123` and asserts the marker appears in no debug log line it
  captures (`System.debug` output is read via test log capture or a logging seam). Surface: Apex test.
- **AC R-8.3** boundary — after rotating the key (admin edits the credential value), the next request uses the new key
  without redeploy. Surface: Live (person-owned). Else unverified.
- Basis: S-1; platform guide security cards. Evidence limits: xAI data-retention terms not read (G-7). Pending: all.

### R-9 Access control
- **Behaviour:** only users granted the access grant (a permission set deployed with the product) can open the panel and invoke
  the server-side operation; the check is enforced on the server operation, not only by hiding the tab.
- **Boundaries:** the grant covers the tab, the app, the Apex class(es) and use of the xAI credential. Sharing, object CRUD
  and field-level security are **not applicable** because the product reads and writes no org records (recorded as an
  exclusion with this reason; if a later feature reads records, each of the three becomes its own requirement).
  Assigning the grant to a user is a separate authorization from deploying it.
- **Error behaviour:** a caller without the grant invoking the operation directly gets the `denied` class (R-7) and no callout.
- **AC R-9.1** failure — Apex test runs the operation as a user without the permission set → denied, zero callouts.
  Surface: Apex test (`System.runAs`). **AC R-9.2** positive — same as a user with the permission set → proceeds to the
  mock callout. **AC R-9.3** boundary — Metadata: after the permission set is removed from the verification user, the tab is
  no longer visible (R-1.2). Surface: Metadata + Browser.
- Basis: S-1; `GUIDES/platforms/salesforce.md` (separate sharing/CRUD/FLS requirements; consumer entry access probe).
  Open: who assigns the grant to which user (G-6). Pending: all.

### R-10 Bot configuration
- **Behaviour:** these values are deployed with the product as configuration and changed without code change: model id,
  system instruction, Max_Message_Chars, Max_History_Messages, Max_Context_Chars, Max_Output_Tokens, Timeout_Seconds
  (defaults in the Bounds table). Default system instruction: `You are Grok, a helpful assistant answering inside Salesforce. Be concise.`
- **Boundaries:** permitted ranges: Timeout_Seconds 1..120 (platform ceiling), Max_History_Messages ≥ 1 (R-5 handles
  odd and even values), all counts/chars/tokens ≥ 1, system instruction 1..2,000 characters.
- **Error behaviour:** a value outside its range makes the bot answer `not-configured` (R-7) and make no callout; it is not
  silently clamped, because silent clamping hides a mis-set cap.
- **AC R-10.1** boundary — Timeout_Seconds 120 accepted, 121 and 0 → not-configured, zero callouts. **AC R-10.2** failure —
  Max_Output_Tokens 0 → not-configured. **AC R-10.3** positive — changing Max_Message_Chars to 2,000 in a test config
  makes 2,001 chars rejected (R-4) without any code edit. Surface: Apex test with config injected through the test seam; Metadata
  for the deployed default values.
- Basis: S-1; Bounds table. Evidence: Salesforce callout timeout range 1 ms–120,000 ms. Pending: all.

### R-11 One request at a time, with truthful pending feedback
- **Behaviour:** while a request is pending the panel shows a visible "Grok is thinking…" state, announces it to assistive
  technology, disables send and New chat, and keeps the composer text editable. Pending clears only when the Apex call
  settles (reply or failure), never on a timer.
- **Boundaries:** at most one in-flight request per panel; a second panel in another tab is independent (no shared state).
  If the user reloads while pending, the late result is discarded; the server-side effect (xAI may have processed it) is unknown.
- **Error behaviour:** a submit attempt while pending (Enter key) is ignored and sends nothing.
- **AC R-11.1** failure/boundary — send then Enter again while the mock is unresolved: exactly one Apex call; New chat disabled;
  after the call resolves, both re-enabled. Surface: Jest (deferred promise controlled by the test). **AC R-11.2** positive — the
  pending indicator is present in the DOM and exposed through a live region while pending and absent after. Surface: Jest + Browser.
- Basis: S-1; interaction design guide. Pending: all.

### R-12 Deployment and consumer entry in the development org
- **Behaviour:** the product deploys additively to the chosen dev org with the Salesforce CLI; it adds only its own components
  (tab, app or tab-in-existing-app, permission set, Apex, web component, configuration, credential shell) and changes no existing
  org metadata. Component names are chosen after listing what the org holds (naming clash check) and carry a `GrokBot` prefix.
- **Boundaries:** deploy, permission-set assignment and entering the key are three separate steps, each with its own authorization.
- **Error behaviour:** a failed or partial deploy is reported with its terminal status and read-back; a name clash blocks deploy.
- **AC R-12.1** positive — `sf project deploy validate` (dry run) then deploy; Metadata read-back lists the tab, app and
  permission set by API name; the tab is listed via `sf org list metadata --metadata-type CustomTab`. **AC R-12.2** boundary —
  before/after listing of the org's Apex classes, tabs and LWC bundles differs only by the added names. **AC R-12.3** failure —
  validate against an org that already holds a clashing name is refused before deploy (recorded as the naming check).
  Surface: Metadata (CLI). Confirmed by: command output with exit codes.
- Basis: S-1 ("in a Salesforce development org"). Open: target org (G-1). Pending: all.

### R-13 Usage and spend limits — OPEN
- **Behaviour (interim, safe):** no per-user message quota or spend cap is built by this product until the owner decides one.
  Interim containment: (a) access only for users given the grant (R-9), (b) one in-flight request per panel (R-11),
  (c) 429 is surfaced, never retried (R-7), (d) output cap per reply (R-6). Spend is bounded outside the org by the xAI team's
  billing limits, which the person owns.
- **Open decision:** a per-user or per-org rate cap and a spend budget. Basis missing: xAI account tier (rate limits scale with
  tier), number of users and budget are unknown. No value is invented. Smallest confirming observation: owner states expected
  users and budget; then research reads the model's tier limits at docs.x.ai/developers/rate-limits. Affected work: only a
  future throttle item; everything else proceeds.
- **AC R-13.1** failure — n/a until decided: the interim containment is verified by R-7.1 (429 row), R-9.1, R-11.1. Recorded as open.
- Basis: S-1 silent on usage limits. Pending: owner decision G-3.

## Bounds table (functional limits the request leaves unstated)

All are defaults, held as configuration (R-10) and therefore reversible without code change. "Evidence" separates what a
documented platform limit supports from what is a product choice. None is a requirement the user gave.

| ID | Bound | Default | Basis | Alternatives | Revalidate when | At / beyond the bound |
| --- | --- | --- | --- | --- | --- | --- |
| B-1 | Max_Message_Chars | 4,000 | Product choice: unbounded input would reach the 6 MB callout limit and unbounded cost. Platform limits only give an upper ceiling; no source fixes 4,000 | 2,000; 8,000 | users hit it, or model context window confirmed | 4,000 accepted; 4,001 rejected, no callout (R-4) |
| B-2 | Max_History_Messages | 20 (incl. new) | Product choice sized so a full context ≈ 100,000 chars, far below 6 MB | 10; 40 | cost review; context window confirmed | 20 kept; 21 drops oldest exchange (R-5) |
| B-3 | Max_Context_Chars | 100,000 | = 20 × 5,000; ≈ 25k tokens (estimate), 1.7% of the 6 MB sync callout limit | 50,000; 200,000 | model context window confirmed | 100,000 kept; 100,001 drops oldest exchange (R-5) |
| B-4 | Max_Output_Tokens | 1,024 | Keeps reply ≈ 4 KB, well within 6 MB and the timeout; product choice for length | 512; 2,048 | replies often cut off | cap reached → incomplete note (R-6) |
| B-5 | Timeout_Seconds | 60 | Runtime-derived: Salesforce default 10 s is too short for an LLM; max 120 s per callout and cumulative; one callout per request, no retry, so 60 s leaves headroom | 30; 120 | measured p95 latency for the chosen model | answer at 59 s shown; ≥60 s → timeout class (R-7) |
| B-6 | Callouts per submission | 1 | Runtime ceiling 100; no tool loop | — | tool use added | exactly 1 |
| B-7 | Per-user/org quota, spend cap | none (OPEN) | basis missing, see R-13 | — | owner decision | not applicable |

## Out of scope (domain rules the request leaves out), bound to the R they limit

- R-1: no record-page, Experience Cloud, Salesforce mobile app, Slack or Messaging-channel entry points.
- R-2: no token streaming (Apex callouts return the whole body; inference, confirm at plan), no Markdown rendering, no
  attachments/images/voice, no web or X search tools, no function calling.
- R-3: no saved or shareable conversations, no history across sessions, no multi-user chat.
- R-8/R-9: no grounding on Salesforce records, no CRUD/FLS-governed data access.
- R-13: no built-in throttle or billing UI.

## Flows (behaviour model)

F-1 Send a message (R-2,3,4,5,6,7,11): User → panel: submit text. Panel validates (T-1 or T-6). Panel → server operation:
{message, completed exchanges}. Server checks access (R-9), config (R-10), validation and context assembly (R-4,R-5), makes one
callout to xAI with the stored credential (R-8), maps the outcome (R-6,R-7) and returns {reply | error class}. Panel renders it
(T-2 or T-3). Alternative branches: not-configured, denied, auth, rate-limited, upstream, timeout, unreadable, other-4xx.
F-2 New chat (R-3): User → panel: New chat when idle (T-5); refused while pending (T-4b).
F-3 Reload/leave (R-3, R-11): any state → Empty; pending result discarded (T-7).

State inventory — chat panel (owner: browser component; transient; initial Empty; no terminal):

| State | Meaning / invariant |
| --- | --- |
| Empty | no messages; composer enabled; New chat disabled or no-op |
| Idle | ≥1 message, no request pending; context = completed exchanges |
| Pending | exactly one request in flight; send and New chat disabled |

Transition ledger:

| ID | R / F | Before → trigger/guard → After | Operation and observation | Failure/recovery | Case |
| --- | --- | --- | --- | --- | --- |
| T-1 | R-2,4 / F-1 | Empty or Idle → submit, text valid → Pending | message appended; pending shown; one Apex call | — | R-2.2 |
| T-2 | R-2,3 / F-1 | Pending → reply ok → Idle | assistant message appended; exchange added to context | — | R-2.2, R-3.1 |
| T-3 | R-7 / F-1 | Pending → failure → Idle | user message marked failed; error + Retry; context unchanged | Retry = T-1 | R-7.1, R-3.2 |
| T-4 | R-11 / F-1 | Pending → submit → Pending | ignored; nothing sent | — | R-11.1 |
| T-4b | R-11 / F-2 | Pending → New chat → Pending | refused (control disabled) | — | R-3.3 |
| T-5 | R-3 / F-2 | Idle → New chat → Empty | transcript and context cleared | — | R-3.3 |
| T-6 | R-4 / F-1 | Empty or Idle → submit, text invalid → unchanged | inline message; composer text kept; no call | — | R-4.1 |
| T-7 | R-3,11 / F-3 | any → reload → Empty | all state lost; pending server effect unknown | user resends | R-3.4 |

## Walks (replay of ordered cases)

Method: each walk starts from an empty panel, applies only events the ledger permits in the preceding state (T-4/T-4b show
refused events), and the expected result is recomputed from rules R-4/R-5. `RUN/scratch/sim.py` encodes the same rules as a
state machine that refuses unpermitted events, but **it was not executed** (execution approval was not granted in this run),
so every value below is **hand-computed**, marked `NOT-REPLAYED: sim not executed`. The cases stay open until the sim or
the Apex/Jest tests produce the same values.

- W-1 (R-4): `""`→reject empty; `"   "`→reject empty; `a`→ok(1); 4,000×a→ok; 4,001×a→reject too-long; `"  "+4000×a+"  "`→ok(4,000). NOT-REPLAYED.
- W-2 (R-5): u1/a1…u10/a10 completed (20 messages). Send u11: count = 20+1 = 21 > 20 → drop (u1,a1) → 19 ≤ 20. Payload first=`u2`, last=`u11`, n=19. NOT-REPLAYED.
- W-3 (R-3): u1 ok/a1; u2 sent (Pending) → failure (T-3) → Idle; u3 sent. Context = [u1, a1, u3] (n=3); transcript = u1 ok, a1, u2 failed, u3. NOT-REPLAYED.
- W-4 (R-11): send `hello` → Pending; second send → refused (T-4); New chat → refused (T-4b); transcript length 1; reply `hi` → Idle; New chat → Empty. NOT-REPLAYED.
- W-5 (R-5, count raised to 40): 10 exchanges of 4,000 + 8,000 = 12,000 chars each = 120,000; + new 4,000 = 124,000 > 100,000 → drop one: 112,000 → drop another: 100,000 ≤ 100,000, stop. Retained: 8 exchanges + new = 17 messages, 100,000 chars. NOT-REPLAYED.
- W-6 (R-5 edge): one exchange (49,999 + 49,999) + new `xx` = 100,000 → kept (3 messages); (50,000 + 49,999) + 2 = 100,001 → dropped (1 message); 100,002 → dropped (1). NOT-REPLAYED.

Reachability: every start is a signed-in user holding the grant in a deployed org with the key entered. That start is currently **unreachable by this
run** (no org, no key): recorded as open prerequisites G-1, G-2, G-6. Live-dependent cases (R-2.1, R-7.4, R-8.3) stay unverified until then;
mocked cases do not need them.

## Non-functional requirements

- **NFR-1 Latency/freshness:** no numeric Grok latency target is invented (not controllable). Bound: Timeout_Seconds = 60 (B-5);
  observable: pending state is visible from the moment of submit until the call settles (R-11.2). Verification: Jest + Browser.
  Measured p95 latency of the chosen model is an open measurement (revalidates B-5).
- **NFR-2 Security:** key custody (R-8), server-side validation and role allow-list (R-4, R-5), server-enforced access (R-9), plain-text
  rendering (R-2.3). Verification: Apex test, Jest, repo grep. Excluded: CRUD/FLS (no records, see R-9).
- **NFR-3 Privacy:** user text leaves the org to xAI; the panel discloses it (R-1.1); no content stored or logged in the org (R-8);
  xAI retention beyond a no-store request is outside the product and unresolved (G-7, person-owned).
- **NFR-4 Reliability/recovery:** no durable state to corrupt; any failure leaves transcript intact and the composer usable (R-7);
  deployment is additive so rollback is removal of the added components (destructive change) plus deleting the credential.
- **NFR-5 Capacity/cost:** request size ≤ 100,000 chars + message (≈0.4 MB), far below 6 MB; Apex heap (10 MB sync per the Winter '27 limits table, 6 MB in older docs) is
  not binding for ≈1 MB of strings. Cost/quota target: unresolved (R-13, G-3).
- **NFR-6 Compatibility:** Lightning Experience in a desktop browser; verification in the current Chrome. Other browsers and the mobile app are
  out of scope (default). Salesforce API version: that of the target org, read at plan (G-1), not guessed.
- **NFR-7 Operability/observability:** per request one debug-log line: outcome class, HTTP status, latency ms, message counts, no content (R-8).
  A persistent audit/log object is excluded: a development org used by one or a few admins, and content logging would conflict with R-8.
- **NFR-8 Testability:** Apex tests (mocked callout) for R-2..R-10 server rules; Jest for panel behaviour; browser check for R-1, R-11, UI.
  Apex coverage rule follows the org's effective deploy test level, read at plan (not assumed).
- **NFR-9 Accessibility and interface quality (UI deliverable):**
  - Visual reference and starting appearance: the light Google Gemini look with Material 3 Expressive principles (airy, tonal rounded
    surfaces, humanist sans, confident primary action, one restrained luminous accent), **adapted inside Lightning**: platform conventions
    take precedence, so the component uses SLDS styling hooks/tokens and Lightning fonts rather than a custom palette or imported fonts.
    Light first; dark option: tokens, no hard-coded colours, so the panel follows the org's theme (whether the org offers dark mode is
    unverified, G-8; if absent, the dark palette is verified by a token-level contrast check).
  - Focal point: the transcript and composer, with the composer docked at the bottom and the primary send action strongest; user and assistant
    messages in visibly distinct tonal bubbles; supporting text (notice, counter, divider) quieter but AA contrast.
  - States designed: empty (short greeting with three example prompts), loading (pending indicator, R-11), error (inline, Retry, R-7),
    not-configured, denied; trimmed-context divider.
  - Layout: works at 320 px and 1440 px wide with no horizontal overflow (long unbroken text wraps).
  - Keyboard: Enter sends, Shift+Enter inserts a newline; visible focus ring on every control; focus returns to the composer after a reply or error.
  - Contrast: WCAG AA for text and controls in both themes. Motion: only a short fade/slide for a new message and a pending pulse; disabled under
    `prefers-reduced-motion`. One icon set: SLDS utility icons only. New messages announced via a polite live region.
  - Verification: Jest (roles/names/states), Browser at the two widths, keyboard run-through, contrast check. A screenshot alone does not close focus or reduced-motion.

## State and data assessment

| Resource | Owner / location | Change | Before / after invariant | Recovery | Check |
| --- | --- | --- | --- | --- | --- |
| Transcript and context | browser component memory | created per session | after reload empty; never persisted (R-3, R-8) | none needed | R-3.4 |
| xAI API key | org credential facility (AD-3) | person enters once | key never in source/logs/client | rotate by re-entering | R-8.1, R-8.3 |
| Bot configuration | deployed configuration records (AD-4) | added | values inside permitted ranges, else not-configured | redeploy defaults | R-10.* |
| Access grant | permission set | added; assignment separate | only assigned users reach panel/operation | unassign | R-9.* |
| Components (tab, app, Apex, UI) | org metadata | added only | existing metadata unchanged; names unique | destructive change | R-12.* |
| Exchange content at xAI | xAI service | request asks not to store | outside org control; unknown retention | n/a | G-7 open |

Unknowns: what the org already holds (G-1); xAI retention (G-7). A denied metadata read is not evidence of absence.

## Service boundary: xAI Grok

- **Current authority:** xAI for reply content, model availability and rate limits; the org for identity, access and configuration.
  No org record data crosses. Reuse: platform callout and credential facilities; no new middle tier.
- **Freshness vs revocation:** nothing about authorization or replies is cached. Revoking the key, removing the grant or changing config takes
  effect on the next request. Cache: not applicable.
- **Incremental state:** none held remotely by design (stateless; client re-sends context each time, R-5). Client-supplied context is untrusted (R-5.3).
- **Async completion:** synchronous request/response with one callout; the outcome of a timed-out call is unknown, retry is user-initiated,
  duplicates are possible and accepted (no idempotency key; stated in the timeout message).
- **Owned event coverage:** outcome-class debug line (NFR-7); no persistent audit; excluded with reason above.
- **Remote map:** required behaviour → route: server operation → HTTP callout → xAI inference endpoint → effective identity: the org user
  invoking the operation, authorized via the grant to use the credential → completion evidence: mocked tests now, one live read-back later (G-2).
  Developer deploy identity is unrelated to the runtime caller.

## Open gaps and prerequisites

| ID | Under | Gap | Owner | Safe interim / consequence |
| --- | --- | --- | --- | --- |
| G-1 | R-12, NFR-6 | Target dev org alias/username, API version, existing component names, test level not discovered (no discovery ran) | person/environment (read-only `sf org list`, metadata listings at plan) | R-12 and deploy work unready; spec and local work proceed |
| G-2 | R-2.1, R-7.4, R-8.3 | xAI API key and entering it in the org credential (a secret cannot be deployed from source) | person only | live checks wait; mocked checks proceed |
| G-3 | R-13 | usage quota and spend budget | owner decision | interim containment in R-13 |
| G-4 | R-2, R-6, R-8 | unverified API facts: Responses vs Chat Completions endpoint to use (docs call Chat Completions legacy), `store:false`, output-cap parameter name, incomplete-reply field, valid model id `grok-4.7` | research with key (one bounded read, e.g. list models) | request-shape ACs written to rule, field names finalised at plan |
| G-6 | R-1, R-9 | which user receives the grant and who assigns it | person/admin | release-plan names the assignment step |
| G-7 | R-8, NFR-3 | xAI data-retention terms acceptable for the data users may type | person | disclosure notice stays; no sensitive-data claim made |
| G-8 | NFR-9 | whether the target org offers a dark appearance | discovery | token-only styling either way |

## Evidence limits

Nothing was executed against an org or xAI. Documentation claims used: Salesforce callout limits (default timeout 10 s, 1 ms–120 s per
callout, 120 s cumulative, 100 callouts, 6 MB sync / 12 MB async request or response, callout not allowed after DML in the same transaction)
— `developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-timeouts.html`; heap 10 MB sync/25 MB async
from the Winter '27 developer guide and limits page, older docs 6/12 MB — `.../apex-gov-limits.html`; Named/External Credential custom-header API key pattern
(`Authorization` formula header, secrets cannot be placed in the endpoint URL) — `help.salesforce.com` articles on API keys in custom headers;
xAI `POST https://api.x.ai/v1/responses` (stores by default 30 days, `store:false` option) and `POST /v1/chat/completions` (labelled legacy), rate limits per model and tier —
`docs.x.ai/developers/rest-api-reference/inference/*`, `docs.x.ai/developers/rate-limits`. These came from web search snippets, not
page-by-page reads or probes; pages disagree in places (model names, product branding), so G-4 stays open. Plain-text/no-streaming claim for Apex callouts is
inference. All checks above are planned, none run.

## Retired

None (first specification).

## Submission

**summary:** Spec for a Grok bot in a Salesforce dev org: Lightning chat panel (R-1) answering via one xAI Grok call per message (R-2) with
bounded in-session context (R-3, R-5), validated input (R-4), bounded reply and timeout (R-6), explicit failure classes (R-7), key/data
handling (R-8), grant-based access (R-9), configurable defaults (R-10), single in-flight request (R-11), additive deploy (R-12) and an
open usage/spend decision (R-13). 13 requirements, 8 transitions, 6 hand-computed walks (NOT-REPLAYED; sim not executed).
Open: G-1 org discovery, G-2 xAI key (person), G-3 usage/spend limits, G-4 unverified xAI API facts, G-6 grant assignment, G-7 xAI retention, G-8 dark mode.
Assumptions (value, basis, alternatives, revalidation):
- A-1 interpretation "Grok bot" = in-org chat assistant backed by xAI Grok (not Einstein/Agentforce, Slack or record-grounded); basis S-1 + platform host; alternatives: Agentforce/Messaging bot, record-grounded assistant; revalidate on any user correction. Under R-1..R-3.
- D-persist no conversation persistence (R-3, R-8); basis: request asks for no history, avoids personal-data storage; alternative: custom object per user; revalidate if history across sessions is requested.
- B-1 Max_Message_Chars 4,000 (R-4); B-2 20 messages (R-5); B-3 100,000 chars (R-5); B-4 1,024 output tokens (R-6); B-5 60 s timeout (R-6); bases and alternatives per Bounds table; B-1..B-4 are product choices bounded above by documented platform limits (no external source for exact values), B-5 is derived from the 10 s default and 120 s ceiling. Revalidate on measured latency, context window confirmation, cost review or users hitting a cap. B-7 quota/spend: left OPEN (no basis).
- No automatic retry (R-7); basis: 2 × 60 s exhausts the 120 s cumulative callout budget and doubles cost; alternative: one retry on 5xx with a 30 s timeout.
- Config out-of-range values fail closed rather than clamp (R-10); alternative: clamp and warn.
- Plain-text rendering, no streaming, no Markdown (R-2); revalidate if rich output requested.
- Visual: Gemini-light/Material 3 Expressive adapted to SLDS tokens (NFR-9); platform convention wins over the reference.

**primary:** R-1, R-2, R-3 (chat panel reachable; message gets a Grok reply; conversation keeps context). R-1 and R-2 have lower-layer
(Apex/Jest) checks only until G-1/G-2 are closed; their Browser and Live acceptance lines are open.

**evidence_refs:** KNOWLEDGE/spec.md (all R-1..R-13, Bounds table, Walks, NFRs, State and data assessment, Service boundary, Open gaps);
KNOWLEDGE/architecture.md (AD-1..AD-9); RUN/scratch/sim.py (written, not executed); GUIDES/behavioral-requirements.md#behavior-model and
#traceability-and-review; GUIDES/requirements-definition.md; GUIDES/service-discovery.md#verification; GUIDES/platforms/salesforce.md;
GUIDES/platforms/ui.md#light-expressive-starting-point; the Salesforce and xAI documentation URLs listed under Evidence limits. No backchain
receipt (command does not exist in this run; duty 11 omitted). Request-outcome mapping: "Grok bot" → R-2, R-3; "in a Salesforce org" → R-1, R-9, R-12;
"development org" → R-12, NFR-6; every R has at least one AC.
