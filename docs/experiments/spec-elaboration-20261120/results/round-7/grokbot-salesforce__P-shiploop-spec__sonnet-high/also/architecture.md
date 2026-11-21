# Grok Bot for Salesforce: architecture

How the product is built. What it must do is in `KNOWLEDGE/spec.md`; this file does not restate it. Decisions are
`AD-<n>`. Status: proposed at the spec stage; the plan confirms each against the target org (G-1) and records any change
here. Nothing was probed in an org.

## Decisions

### AD-1 Lightning web component page backed by an Apex controller, called by imperative Apex

- **Choice:** one Lightning web component (chat page) placed on a custom tab inside a custom Lightning app. One
  `public with sharing` Apex class exposes a single `@AuraEnabled` method, called imperatively, that takes the new message
  and prior history and returns a structured result `{ok, reply, code, message}`.
- **Why:** the smallest native stack that gives a Lightning page, a server hop for the xAI callout, and the
  permission-set gating of R-8. Alternatives not chosen: Agentforce agent or Flow (a different product reading, DD-1), a
  Visualforce page (older), a browser-direct call to xAI (would put the key in the browser and break R-7).
- **Consequence:** the sharing, CRUD and FLS statement of R-8 is satisfied because no sObject data is read or written;
  user mode DML and queries are not used because there are none. If a later request adds record access, use user-mode
  operations (Salesforce documents `WITH USER_MODE` and the `AccessLevel.USER_MODE` argument).
- **Maps to:** R-1, R-2, R-8.

### AD-2 xAI chat completions endpoint, endpoint path held in configuration

- **Choice:** `POST` to the xAI host at the configured path, default `/v1/chat/completions`, with a stateless body
  (`model`, `messages`, `max_tokens`). Reply text is taken from the first choice's message content.
- **Why:** stateless matches DD-2 and keeps the history bound (R-4) under the product's control. xAI documents the
  endpoint as OpenAI-compatible but labels it legacy and recommends its Responses API for new capabilities; the path is
  therefore configuration (R-9) and the parse is isolated in one method so a switch is a local change.
- **Open:** request and response shape are not probed (G-4). The first live call decides; if the Responses API is
  required, this decision is superseded here and the R-3 acceptance bodies are updated through the correction route.
- **Maps to:** R-3, R-9.

### AD-3 Named Credential plus External Credential with a custom header; key entered in Setup

- **Choice:** an External Credential using the Custom protocol with one principal and a secret parameter for the key; an
  `Authorization` header formula builds `Bearer <key>`; a Named Credential for the xAI host references it. Apex calls
  `callout:<NamedCredentialName><path>`. The principal is mapped to the product's permission set, so credential use
  follows R-8. The Named Credential does not generate its own authorization header and allows formulas in headers.
  No Remote Site Setting is needed.
- **Why:** Salesforce's supported route for an API key that never reaches code (R-7). Source: Salesforce help on API keys
  in custom headers with Named Credentials.
- **Open:** secret values are expected not to be deployable (G-6); the administrator enters the key after deploy. Metadata
  field names move between API versions and are confirmed at implement.
- **Maps to:** R-3, R-7, R-8.

### AD-4 Synchronous callout, no Continuation, no queueable

- **Choice:** the controller makes one synchronous callout with the configured timeout (default 60,000 ms, platform
  ceiling 120,000 ms) and returns when it completes. The page awaits the promise.
- **Why:** DD-13 and the product need no background work; the platform's per-callout ceiling equals the Continuation
  ceiling, so a Continuation adds no wait headroom. Callout wait time is excluded from the 5-second long-running request limit.
- **Consequence:** there is no durable operation record; an unknown outcome is a timeout shown to the user (spec service
  boundary).
- **Maps to:** R-3, R-11.

### AD-5 Configuration in a custom metadata type; no custom objects

- **Choice:** one custom metadata type with a single default record holding model, system prompt, history limit, maximum
  message length, token cap, timeout and endpoint path. The controller reads the record, validates the R-9 ranges and
  returns `CONFIG` on violation. No custom object stores conversations or settings.
- **Why:** the Salesforce platform guide says configuration belongs in custom metadata, which deploys with the code and is
  admin-editable. DD-2 needs no stored data.
- **Maps to:** R-9, R-10.

### AD-6 Conversation state lives in the component

- **Choice:** the component holds the transcript in memory. It sends the new message and, at most, the last N delivered
  messages, with N from the server-reported history limit (returned with the first call or by a small read method). The
  Apex controller truncates again and drops a leading assistant message (R-4).
- **Why:** server authority on bounds (never trust a client-asserted bound) with no persistence (DD-2).
- **Maps to:** R-4, R-5, R-10.

### AD-7 Names, namespace and API version

- **Choice:** every new component, class, tab, app, credential, permission set and configuration type begins with `GrokBot`
  (the tab and app labels read "Grok Bot"). No package namespace, so the component is `c-grok-bot-chat` in the org's default
  namespace. `sourceApiVersion` is set to the target org's supported version when the plan reads it (G-1).
- **Why:** Apex, trigger, metadata and component names are org-wide; the prefix avoids a clash (R-1.d).
- **Maps to:** R-1, NFR-10.

### AD-8 Access: one permission set grants everything

- **Choice:** permission set `GrokBot_User` with: custom tab visibility, custom app visibility, Apex class access to the
  controller, and the External Credential principal access. Assignment is a separate administrator command after deploy.
- **Why:** the platform guide plans visibility steps separately from deploy; a tab, app or class with no grant is hidden
  or refused (R-8.b).
- **Maps to:** R-1, R-8.

### AD-9 Errors returned as values

- **Choice:** the controller catches callout and parse failures and returns `{ok:false, code, message}` using the spec's
  code and message table. It does not throw `AuraHandledException` for these cases. Unexpected exceptions are caught at
  the method boundary and mapped to `CONNECTION`, so no stack trace reaches the page.
- **Why:** exact, replayable messages (R-6) and no leakage of raw bodies.
- **Maps to:** R-6.

### AD-10 Logging with a helper that accepts only code, status and elapsed time

- **Choice:** a small log helper writes one `System.debug` line with outcome code, HTTP status and elapsed ms. Its signature
  takes no free-text parameter, so content cannot be passed to it. No persistent log object.
- **Why:** R-12 and R-10 by construction; DD-2 means no sink is needed.
- **Maps to:** R-10, R-12.

### AD-11 Interface: platform components, token layer, plain-text rendering

- **Choice:** the page uses Lightning base components where they fit (icons, buttons) and its own CSS custom-property
  tokens for the palette (light default, dark through `prefers-color-scheme`), spacing and type scales; local font stacks only
  (no external fonts or CDN); the platform's utility icons as the single icon set; message text bound as text, never as
  rich text or `innerHTML`; a live region for status; `prefers-reduced-motion` honoured. The concrete palette, radii and
  signature element are chosen in the plan, following NFR-11's light expressive starting point with platform conventions
  taking precedence.
- **Why:** the platform restricts external assets; text binding is the defence behind R-13.
- **Maps to:** R-13, NFR-11.

### AD-12 Test layout and where each check runs

- **Choice:** Apex tests use an `HttpCalloutMock` (including a throwing variant for timeout and connection failure) and
  `System.runAs` for access, and are run in the org (a remote test) with a reporter ShipLoop can read:
  `sf apex run test --target-org <alias> --class-names <TestClass> --synchronous --result-format tap`. Component tests use
  Jest with the Apex method stubbed and a deferred promise for the in-flight cases. The deployed path gets a browser check as
  the assigned user, then one live call once the key exists. Apex tests are authored because Apex is added; no coverage
  threshold is claimed for a development org and none is invented.
- **Why:** each boundary is exercised where it actually runs; the Salesforce platform guide says Jest, Apex tests and
  browser checks do not substitute for one another.
- **Maps to:** R-2 to R-13, NFR-9.
- **Unrun:** these commands have not been run; no project or org exists at this stage.

## Layout (proposed)

```
sfdx-project.json
force-app/main/default/
  classes/GrokBotController.cls, GrokBotConfig.cls, GrokBotLog.cls, GrokBotControllerTest.cls (+ meta)
  lwc/grokBotChat/ (html, js, css, js-meta.xml, __tests__/)
  customMetadata/, objects/GrokBot_Setting__mdt/
  externalCredentials/, namedCredentials/
  permissionsets/GrokBot_User.permissionset-meta.xml
  tabs/GrokBot_Chat.tab-meta.xml
  applications/GrokBot.app-meta.xml
.gitignore            (lists .sf/ and .sfdx/)
README.md             (deploy, key entry, permission-set assignment, recovery)
```

The layout is a proposal; the plan fixes it once the org's existing names are listed (G-3).
