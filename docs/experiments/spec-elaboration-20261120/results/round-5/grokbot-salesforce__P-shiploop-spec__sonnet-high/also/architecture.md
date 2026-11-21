# Grok Bot for Salesforce: architecture

How the product is built. What it must do is in `spec.md` (`R-<n>`); this file never restates it. Decisions are
`AD-<n>`. Runtime versions, org alias and working commands belong in `environment.md` (not written in the spec stage:
no org was probed). No secret value appears here, only names and shapes.

## Stack

- Salesforce DX source project (metadata format), deployed with the `sf` CLI (installed at `/opt/homebrew/bin/sf`; its
  version was not probed). Target org alias, edition and API version: unknown (spec gap G-1). The project's
  `sourceApiVersion` is set to the target org's current version at prepare, never guessed here.
- Apex (service, controller, tests), Lightning Web Components with SLDS 2 styling hooks, Jest for the component
  (`@salesforce/sfdx-lwc-jest`, version chosen at prepare), custom metadata type for configuration.
- xAI API `POST https://api.x.ai/v1/responses` (vendor docs read 2026-11-20, spec source `S-1`).
- No new runtime dependency, no third-party UI library: the component uses base Lightning components and SLDS only.

## Structure

Proposed names; they must be checked against the org's existing metadata before first use (spec G-3). API names are
org-wide without a namespace.

| Unit | Owns |
| --- | --- |
| `GrokBotController` (Apex, `with sharing`, `@AuraEnabled` non-cacheable `send`) | The browser boundary: takes the history and text, returns a result object, never throws a raw exception to the client. |
| `GrokBotService` (Apex) | Validation (R-3, R-4), request building, classification (R-7), log-line production (R-12). Stateless. |
| `GrokBotConfig` (Apex) | The one seam through which configuration is read, replaceable in tests. |
| `GrokBotHttp` (Apex) | The one place the callout is made, replaceable by `HttpCalloutMock`. |
| `Grok_Bot_Config__mdt` + record `Default` | Configuration fields from R-6. |
| `grokBot` (LWC) and child components `grokBotMessage`, `grokBotComposer` | Presentation, draft, transcript, pending token, states T-1 to T-10. |
| `Grok_Bot` tab, `Grok_Bot` app | The consumer entry; `lightning__Tab` in `js-meta.xml` only makes the component eligible, the `CustomTab` file creates the entry. |
| `Grok_Bot_User` permission set | Tab, app, Apex class and External Credential principal access. Never assigned by deploy. |
| `Grok_Bot_xAI` External Credential (principal `Default`) and `Grok_Bot_xAI` Named Credential (`https://api.x.ai`) | Endpoint and key custody. The principal's secret parameter is empty in source. |
| `docs/` admin setup note | The person-only steps (spec R-13). |

## Conventions

- Apex test classes `*Test`; one test per spec acceptance line, named with its `R-<n>.AL-<n>` ID so the code is the
  one home of test IDs. Apex tests use `Test.setMock(HttpCalloutMock.class, ...)`; none calls xAI.
- LWC Jest tests next to each component; Apex is mocked at the import boundary; promises are controlled explicitly,
  no sleeps.
- No colour literals in component CSS; only `--slds-g-*` hooks. Icons only through `lightning-icon`.
- `.sf/` and `.sfdx/` listed in `.gitignore`.
- Log lines are produced only by the service's one builder and never include user text, model output, headers or
  the upstream body.

## Interfaces and boundaries

- **Browser to Apex:** imperative call to `GrokBotController.send(history, text)` returning
  `{ok, answer, model, truncated, category, message}`. Not wired and not cacheable (a send is a side-effecting, billed
  call; no cache and no refresh mechanism is needed, so none is built).
- **Apex to xAI:** one synchronous request to `callout:Grok_Bot_xAI/v1/responses`. Body keys exactly: `model`,
  `input`, `instructions`, `store` (false), `max_output_tokens`, and optionally `reasoning`. Authority: the platform
  injects the `Authorization` header from the External Credential principal at call time; Apex never sets it.
  Answer text is read from the first `output` item of type `message`, content item of type `output_text`; only `status`
  and `output` are relied on for success.
- **Freshness and revocation:** each send is a live call. No cache, no copy, so no stale authorisation or answer.
  Revoking `Grok_Bot_User` takes effect on the next call (the platform refuses it).
- **Async and recovery:** none. Synchronous completion; a timeout leaves the xAI-side outcome unknown, the user is told,
  and the product does not retry or reconcile. xAI documents no idempotency key (`S-1`), so no exactly-once claim is made.
- **Owned event coverage:** one `GrokBot outcome=...` debug line per send. No other logging, audit store or metric
  facility is added. Provider-side events (xAI console usage) belong to the account owner.
- **Config reads:** through the custom metadata accessor, so no query limit is spent per send.

## Real-boundary checks

A local or mocked test cannot prove these; each needs the target org and, where noted, the user's xAI key.
Owner: the run operator, except the key which only the administrator may enter.

| Check | Why a local test cannot prove it | Spec lines |
| --- | --- | --- |
| Live round trip with the real key and model | The wire contract is from docs, never exercised | R-2.AL-5, R-5.AL-4 |
| Wrong or empty principal secret: which exception and message result | Platform exception text is unprobed | R-5.AL-5, R-7.AL-5/6, G-7 |
| Permission set grants tab, class and principal; user without it is refused | `System.runAs` does not enforce class or principal access | R-1.AL-2, R-8.AL-1..3 |
| Deploy validation, test level, coverage gate | Depends on the org's actual gate | R-13.AL-1/6, G-4 |
| Debug-log line, no content leak | Needs a trace flag and a real log | R-12.AL-3 |
| Browser rendering at 320 px and 1,440 px, focus, reduced motion, dark theme | A DOM test cannot show layout or contrast | R-18, R-19, G-5 |

## Decisions

### AD-1: An in-org Lightning chat window, not an Agentforce, Slack or Models API bot

**Status:** accepted (default, user-reversible: spec D-1). **Why:** the request names a bot in a development org and a
specific model vendor; a Lightning web component calling the vendor API through a Named Credential is the smallest
design that puts Grok itself in the org and works in any development org. **Alternatives:** (a) Agentforce agent with a
bring-your-own-model connection: depends on the org's Agentforce and Einstein availability and on a Grok model being
offerable there, neither of which was verified, and it hands model access to the Salesforce trust layer; (b) Slack app or
Messaging channel bot: needs a second platform and channel setup the request did not ask for; (c) Flow with an HTTP
callout action: no conversational UI. **Consequence:** switching to (a) later is a new requirement set.

### AD-2: xAI Responses API via Named Credential and External Credential, `store: false`

**Status:** accepted. **Why:** `S-1` calls Responses "the primary interface" and `S-4` says new integrations should use it
(chat completions remains documented, not deprecated). The Named Credential fixes the host, the External Credential keeps the key
out of source, Apex and the browser, and its principal needs a permission-set grant (`S-6`). Sending `store: false` asks xAI not to keep the
exchange for retrieval (`S-1` documents 30-day retention for stored responses). **Alternatives:** chat completions (older
interface); a hard-coded key in a custom setting or CMDT (rejected: not a secret store); a Remote Site Setting with Apex-built
headers (rejected: puts the key in code or data). **Unverified:** that the External Credential's custom-header formula can build
`Bearer <key>` exactly as xAI expects (`S-6` summary says custom parameters can be referenced in a header formula); confirmed at
the live probe (spec G-2, G-7). **Revalidate when:** xAI changes the endpoint or retires the model id.

### AD-3: UI direction

**Status:** accepted for the spec; the plan owns concrete values. **Reference:** light Google Gemini look with Material 3
Expressive principles, adapted to "Grok Bot" and subordinate to Lightning Experience conventions (SLDS 2 hooks, the org's theme).
**Design guidance identity:** none discovered in this stage (no host design skill was inspected); fallback is `GUIDES/platforms/ui.md` and
this decision. **Choices to be fixed at planning and cited by step criteria:**
tone airy and calm; focal activity the transcript with a bottom-pinned composer; user messages on a tonal accent surface aligned
end, Grok messages on a neutral raised surface aligned start, both with rounded containers and smaller rounded controls (a shape hierarchy);
colour only from `--slds-g-color-*` hooks (surface, accent, on-accent), spacing from `--slds-g-spacing-*`, type from the SLDS scale;
one signature detail: a soft gradient shimmer on the pending bubble, static label under reduced motion; icons from the Lightning utility
set only. **Rejected:** a third-party chat UI library (new dependency, Locker/LWS and styling risk, no gap shown); hard-coded Gemini palette
(breaks dark mode and org theming). **Open:** exact token values and the dark-mode result depend on the org's theme (spec G-5).

### AD-4: Configuration in a custom metadata type

**Status:** accepted. **Why:** the platform guidance keeps configuration in custom metadata that deploys with the code; an administrator edits it in
Setup with no code change. **Alternatives:** custom setting (not source-deployable in the same way), hard-coded constants (needs a deploy per change),
a settings UI (out of scope). Out-of-range values fail closed (spec R-6) rather than being clamped.

### AD-5: Transcript owned by the component; Apex stateless

**Status:** accepted. **Why:** the lifetime is one page visit with no sharing and no recovery (spec A-6, R-10), so local component state is sufficient;
the client sends the windowed history each time and the service re-validates roles and size. **Alternatives:** a custom object or platform cache for
conversations (rejected: adds retained personal text, retention and deletion duties the request does not need); Apex-side session state (none exists
across requests without storage). **Consequence:** forging history harms only the forger and is bounded by the same server validation.

### AD-6: Classify failures by HTTP status and exception type; never parse error bodies; no automatic retry

**Status:** accepted. **Why:** `S-3` documents status codes but not the error-body shape or 5xx codes; one attempt per send avoids double billing and
hides no failure. **Alternatives:** parse xAI error JSON for finer messages (rejected until it is documented); automatic backoff (rejected: cost and unknown
idempotency). **Revalidate when:** xAI documents its error schema, or the platform exception text is probed (G-7).

### AD-7: Entry as a custom tab in a dedicated app, access through one permission set

**Status:** accepted. **Why:** `lightning__Tab` alone creates no entry; the platform guidance requires a `CustomTab` file, an app listing it, and a permission set
that grants them, each deployed separately from its assignment. **Alternatives:** a utility-bar item or record-page placement (not requested). The release plan
names the deploy, the permission-set assignment and the credential setup as separate commands with separate authorisation.

## Superseded

None.
