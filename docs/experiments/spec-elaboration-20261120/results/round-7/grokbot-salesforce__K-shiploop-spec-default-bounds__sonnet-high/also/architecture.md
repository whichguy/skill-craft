# Grok Bot for Salesforce — Architecture Decisions

How the product is built. What it must do is in `spec.md` (`R-<n>`, `A-<n>`, `G-<n>`). Decisions are `AD-<n>`. Each was
made on 2026-11-21 from the request *"Create a Grok bot in a Salesforce development org."* and the spec; none has been
implemented or probed in an org.

## Decisions

### AD-1 Build a custom chat on the Salesforce platform (Lightning web component + Apex), not a native bot builder
- **Status:** accepted (default). **Serves:** R-1, R-2, R-9.
- **Decision.** One Lightning web component (chat UI) calls one Apex service that calls xAI. Salesforce's built-in bot/agent
  builders are not used.
- **Rationale.** Grok is an external xAI model reached over HTTPS with a Bearer key; whether the org's native agent tooling can
  target xAI models was **not verified** (unknown, not a claim of absence). The custom path needs no such support and gives
  control of history, errors, and secret custody.
- **Revalidate when:** the user names Agentforce/Einstein as the required channel, or the org is found to offer an xAI model provider.

### AD-2 Call xAI's Chat Completions endpoint through a single adapter class
- **Status:** accepted. **Serves:** R-2, R-3, R-5, R-13.
- **Decision.** `POST https://api.x.ai/v1/chat/completions` with `model`, `messages`, `max_completion_tokens`. Parse
  `choices[0].message.content`, `choices[0].finish_reason`, `usage.*`. Map HTTP status and exceptions to the R-5 codes in one class
  (`GrokClient`), so no other class knows xAI's field names.
- **Rationale (evidence, docs.x.ai read 2026-11-21).** The endpoint is documented, stateless and OpenAI-compatible with clear
  field names; xAI describes it as the predecessor of the Responses API and says new integrations should use Responses, **with no
  deprecation or removal date**. Responses stores new responses for 30 days and its input-array item shape and usage field names are
  inconsistently documented, so it was not chosen for the first version. Chat Completions' retention behaviour is not stated (G-6).
- **Revalidate when:** xAI dates a deprecation, or G-6 is resolved against it. Switching is a one-class change (R-13).
- **Not used:** `max_tokens` (documented as deprecated).

### AD-3 Apex ↔ component contract: a returned result object, not thrown errors, for expected failures
- **Status:** accepted. **Serves:** R-2–R-5, R-8.
- **Decision.** One `@AuraEnabled` method `GrokBotController.sendMessage(message, history)` where `history` is a list of
  `{role, content}`; it takes **no** model, prompt, or limit parameters (R-11.1). It returns `{ok, reply, truncated, droppedCount,
  errorCode, errorMessage, referenceId}`. Expected failures (R-4, R-5) are returned, never thrown, so no platform error text reaches the
  browser (R-5.2); unexpected exceptions are caught at the controller and returned as UNAVAILABLE.
  The component calls it imperatively (user-triggered, not cacheable), so no wire/cache refresh is involved.
- **Server order of operations.** validate message and history roles → read configuration → validate configuration ranges → trim
  history (R-3) → build request → one callout → map result → write one log line (R-5). No DML occurs (callout-before-DML rule; R-11.2).
- **Reference id.** Generated server-side per turn (UUID text, ≤ 36 characters).

### AD-4 Credentials: External Credential + Named Credential, key in the platform secret store
- **Status:** accepted; mechanics to be **probed at prepare** (G-8). **Serves:** R-6.
- **Decision.** The xAI key is a principal parameter of an External Credential (custom authentication protocol); the Named Credential
  points at `https://api.x.ai` and adds the `Authorization: Bearer <key>` header through the credential's header mechanism, so the key is
  never in Apex source, configuration, or the browser. Apex calls `callout:<NamedCredentialApiName>/v1/chat/completions`.
  The "Grok Bot User" permission set grants the External Credential principal access.
- **Evidence.** Salesforce documents custom headers and merge fields for callouts using Named Credentials, and recommends the
  External-Credential-based Named Credentials over legacy ones. The exact header-formula form is from a secondary source and must be
  confirmed by `sf project deploy validate` and a first call.
- **Out-of-band step.** Entering the key is a person-only Setup action (G-2); source control carries the credential *definition* only.
- **Revalidate when:** a deploy rejects the metadata shape, or the platform changes the header mechanism.

### AD-5 Admin-tunable settings in one custom metadata type
- **Status:** accepted. **Serves:** R-3, R-5.4, R-6.
- **Decision.** Custom metadata type `GrokBot_Config__mdt` with one default record carrying model, system prompt, reply cap, timeout,
  history window and history budget (A-5 defaults). Deploys with the code; no secrets. The service validates ranges on every turn and returns
  NOT_CONFIGURED on violation (no clamping). Rationale: platform guidance to keep configuration in custom metadata, not records.

### AD-6 Metadata names and the consumer entry
- **Status:** proposed names, **to be checked for clashes at prepare** (G-4). **Serves:** R-1, R-9.
- **Names (no namespace, so `c`):** component `grokBotChat`; Apex `GrokBotController`, `GrokClient`, `GrokBotConfig`,
  tests `GrokBotControllerTest`, `GrokClientTest`; custom metadata type `GrokBot_Config__mdt`; External Credential `xAI_Grok_Credential`;
  Named Credential `xAI_Grok`; tab `GrokBot`; app `Grok_Bot`; permission set `GrokBot_User` (label "Grok Bot User"). Apex, tab and
  metadata API names are org-wide, hence the check.
- **Entry.** `lightning__Tab` in the component's meta file only makes it eligible; the entry is the files `tabs/GrokBot.tab-meta.xml` and
  `applications/Grok_Bot.app-meta.xml` plus visibility in the permission set. Consumer path: App Launcher → Grok Bot →
  `/lightning/n/GrokBot`. Deploy, permission-set assignment and key entry are separate commands/steps (R-9).
- **API version:** the highest version the target org supports, read at prepare (G-1); not assumed here.

### AD-7 State lives in the component; the service is stateless; no custom objects
- **Status:** accepted. **Serves:** R-3, R-7, R-8, R-9.
- **Decision.** Transcript and pending/failed flags are component-local state (T-1…T-10). The browser sends the delivered history each turn;
  the server trusts nothing in it beyond role and length validation (R-3.5). Late replies after "New chat" are discarded by comparing a
  per-chat generation counter captured when the request started. No sharing, no cache, no persistence, no scheduled or background work.
- **Rationale.** A-4. Adds none of: store, queue, platform cache.

### AD-8 Verification layering
- **Status:** accepted. **Serves:** all acceptance lines.
- **Layers.** (1) Apex tests with an `HttpCalloutMock`, run in the org (**remote tests**): `sf apex run test --target-org <alias>
  --class-names <Class> --synchronous --result-format tap` (TAP is the reporter ShipLoop reads). (2) LWC Jest tests locally with a
  controllable Apex stub (promises resolved by the test, no sleeps). (3) Metadata deployment checks by CLI listing. (4) Browser check as an
  assigned test user at `/lightning/n/GrokBot` (layout, keyboard, motion, contrast spot-check). (5) Live Grok smoke, gated by G-2.
  Local doubles never stand in for permission, governor, or org behaviour.
- **Not used as evidence:** `System.runAs` for class-access enforcement (R-1.2).

### AD-9 Visual direction (concrete starting choices; the plan may refine)
- **Status:** accepted starting point. **Serves:** R-10.
- **Reference.** Light Gemini-style / Material 3 Expressive starting point from the UI guide, applied inside Lightning Experience: SLDS
  tokens and utility icons take precedence over any imported look.
- **Choices.** Light first; token names `--gb-*` (component-prefixed, CSS scoped by LWC shadow/synthetic scoping, no globals) mapped to SLDS
  styling hooks with literal fallbacks; dark token set swapped in when the shell signals dark (G-7). Bubbles: user = accent-tinted surface
  with a larger radius, bot = neutral tonal surface; max bubble width ~85% (narrow) / 70% (wide). Composer: rounded container, luminous
  focus ring, Send as the strongest filled control. Signature: integrated thinking indicator in the composer area. Motion: 120–200 ms fade/slide
  of a new bubble and 3-dot pulse, removed under reduced motion. Type: the shell's sans-serif; scale 12/14/16/20 px.
- **Components.** `grokBotChat` (container), child presentational pieces only if needed (message bubble, composer, banner). Native
  `lightning-icon` for icons; native textarea for the composer.

## Revalidation triggers (summary)
The user names a different channel or model vendor; xAI dates the Chat Completions deprecation; the target org offers an xAI model provider;
a name clash or deploy rejection appears at prepare; the service is changed to read Salesforce records (reopens sharing/CRUD/FLS, R-11).
