# Grok Bot for Salesforce: architecture decisions

Structure and technology choices only. What the product must do lives in `spec.md` (R-<n>); product
decisions are PD-<n> there. Status values: accepted (decided here, pending verification), unresolved.
Nothing below has been built or run; every "verified" word refers to the source named beside it.

Evidence legend: **[P]** read in a primary vendor page during this stage; **[S]** seen only as a search-result
summary of a vendor page (page itself not read); **[U]** unverified, needs the named probe.

## Decisions

### AD-1: Bot surface is a custom Lightning chat component, not Agentforce, Einstein Bots or a Messaging channel
- Status: accepted (default taken for the ambiguous request; see spec PD-1).
- Choice: one Lightning web component (provisional bundle `grokBotChat`) hosted on a custom tab inside a
  custom Lightning app. A bot "in a development org" is read as a chat surface a signed-in org user opens.
- Why: smallest surface that delivers "a Grok bot": Agentforce/Einstein Bots/Messaging cannot call an
  arbitrary external model without further licences, channels and configuration the request never named.
- Alternatives rejected: Agentforce custom model (needs a licence/feature the org may not have; unknown);
  Einstein Bot + callout action (dialog-tree product, wrong shape for open conversation); Experience Cloud
  site (adds guest/identity scope nobody asked for).
- Revalidate if: the user says "bot" meant Agentforce, Messaging for In-App/Web, Slack, or an Experience site.

### AD-2: Server-side call to xAI through the Responses API, full history sent per call
- Status: accepted. Evidence: **[P]** `https://docs.x.ai/docs/api-reference` (read in this stage): `POST /v1/responses`
  with base URL `https://api.x.ai/v1`, `Authorization: Bearer <key>`, required `model` and `input`, `input` accepts
  role-tagged messages including `system`; response `output` is an array whose item with `"type": "message"`
  carries `content[]` parts with `"type": "output_text"` and a `text` field. **[P]** `https://docs.x.ai/developers/models`:
  "No role order limitation: You can mix `system`, `user`, or `assistant` roles in any sequence."
- Choice: Apex makes one synchronous HTTPS callout per user message to `POST https://api.x.ai/v1/responses`,
  body `{"model": <setting>, "input": [system message, ...windowed history, new user message]}`; the reply text
  is the concatenation of every `output_text` part of every `message` item in `output`. `stream` is not sent.
- Why Responses and not Chat Completions: the Chat Completions doc URLs tried returned HTTP 404 in this stage
  and the reply path could not be read; a search summary **[S]** calls Chat Completions "legacy" with new
  features arriving in Responses first. Responses is the documented primary interface **[P]**.
- Why full history per call and not server-held conversation state: keeps conversation content out of any
  provider-side store that this spec cannot yet describe (spec G-10); the client/Apex owns the window.
- Unverified **[U]**: whether `stream` defaults to false (page says only "If set, partial message deltas will be
  sent"); error status/body shapes; rate limits; whether an `incomplete` status exists. Probe at prepare with a
  real key (spec G-2, G-5). Until probed, the parser treats "no extractable text" as the malformed-response
  error class and classifies by HTTP status only.
- Revalidate if: a model id the org config names is not accepted by `/v1/responses`; xAI changes the schema.

### AD-3: Credential in a Named Credential backed by an External Credential (custom header), never in code or data
- Status: accepted design; mechanics **[U]**. Evidence: **[S]** developer.salesforce.com pages "Custom Headers and
  Bodies of Apex Callouts That Use Named Credentials" and "Get Started with Named Credentials" (fetch refused
  with HTTP 403, so only search summaries were seen): an external credential can carry custom headers such as an
  API key, and Apex addresses the endpoint as `callout:<NamedCredential>/<path>`.
- Choice: Named Credential `Grok_API` (URL `https://api.x.ai`) + External Credential `Grok_API_Credential` with one
  named principal and an `Authorization` custom header whose value is `Bearer {!$Credential.<param>}` (exact
  merge-field syntax to be confirmed at prepare). Apex never reads, builds or logs the key.
- Consequences to probe **[U]** at prepare, before any dependent step: (a) the secret value is entered in Setup by a
  person and is not deployable or retrievable as metadata; (b) the calling user's permission set must grant access to
  the external-credential principal or the callout fails, with an error text to be recorded; (c) no Remote Site Setting
  is needed for a Named Credential endpoint; (d) no Trusted URL (CSP) entry is needed because the call is server-side.
- Alternatives rejected: key in a custom metadata record or custom setting (readable by anyone who can read the
  setting, deployable in source: violates spec R-6); key in LWC/JS (client exposure); per-user principals (each user
  would need their own xAI key; request asks for no per-user billing).
- Revalidate if: (a)-(d) probes disagree; the org lacks External Credentials.

### AD-4: Metadata inventory, names and access grants (provisional names, subject to org clash check, spec G-7)
- Status: accepted; names provisional.
- Files (source format, additive): `lwc/grokBotChat/*`; `classes/GrokBotController.cls` (the `@AuraEnabled` boundary:
  `getReadiness()` and `sendMessage(...)`) and `classes/GrokBotService.cls` (request build, callout, parse, error
  classification); test classes `GrokBotServiceTest.cls`, `GrokBotControllerTest.cls`; `customMetadata/Grok_Bot_Setting.Default.md-meta.xml`
  and `objects/Grok_Bot_Setting__mdt/**`; `namedCredentials/Grok_API.namedCredential-meta.xml`;
  `externalCredentials/Grok_API_Credential.externalCredential-meta.xml`; `tabs/Grok_Bot.tab-meta.xml`;
  `applications/Grok_Bot_App.app-meta.xml`; `permissionsets/Grok_Bot_User.permissionset-meta.xml`; `flexipages` only if the
  tab needs a Lightning page wrapper (LWC tab target `lightning__Tab` per the platform guide).
- Access: the permission set `Grok_Bot_User` grants, in one place, the tab, the app, the Apex classes and the
  external-credential principal. Deploy, permission-set assignment and key entry are separate steps with separate
  authority (platform guide: deploy is not visibility).
- Entry URL path: `/lightning/n/Grok_Bot` (tab API name), reached through App Launcher > Grok Bot.
- Revalidate if: the clash listing (`sf org list metadata --metadata-type LightningComponentBundle|CustomTab|CustomApplication|ApexClass`)
  shows any of these names used, including by another ShipLoop run on the same org.

### AD-5: Configuration in a custom metadata type, no new custom object, no stored conversations
- Status: accepted. Per the platform guide, configuration lives in custom metadata, which deploys with the code.
- Choice: `Grok_Bot_Setting__mdt`, one record `Default`: `Model__c` (text), `System_Prompt__c` (long text),
  `Timeout_Ms__c` (number), `History_Window__c` (number), `Max_Input_Chars__c` (number). Admins edit values in Setup
  without a code change (spec R-9). No custom object, no DML anywhere in the product (spec R-8: nothing persisted).
- Not stored in the CMT: the API key (AD-3).
- Revalidate if: persisted transcripts or per-user settings are requested (a different spec, new R-numbers).

### AD-6: Security posture of the Apex boundary
- Status: accepted. Evidence: platform guide (`platforms/salesforce.md`), **[S]** Salesforce secure-Apex guidance.
- Choice: both Apex classes declared `with sharing`; the product runs no SOQL/DML on org data, so object CRUD and
  field-level security have no operation to enforce, and that is stated rather than implied by `with sharing`.
  The only query is the CMT read, which is configuration, not user data. Class access is granted by AD-4's permission set.
  Selected API version: unresolved (spec G-8); verify the default access mode of the selected version before relying on it.
- The controller never accepts a model id, endpoint, system prompt or timeout from the client: those come only from
  the CMT record, so a caller cannot redirect the callout or enlarge the request.
- Order inside one transaction: read settings, build body, make the callout. No DML precedes the callout (a callout
  after uncommitted work in the same transaction is disallowed **[S]**), and there is none after it either.

### AD-7: One callout per transaction, imperative Apex call from the component, no Continuation, no async Apex
- Status: accepted. Evidence **[S]** (search summary of "Callout Limits and Limitations"): cumulative callout time per
  transaction is capped at 120 seconds; one callout's timeout ranges from 1 ms to 120,000 ms, default 10 s; at most 100
  callouts per transaction. Heap limit for synchronous Apex (6 MB) **[U]**.
- Choice: the component calls `sendMessage` imperatively and awaits the promise. The product makes exactly one callout,
  so only the single-call timeout matters; `Timeout_Ms__c` must be within 1,000..120,000 (spec R-9).
- Alternatives: Continuation (up to 3 callouts, long-running, adds a second code path; revisit only if replies must exceed
  the 120 s cap); Queueable/Platform Event (the UI would lose the synchronous owner of the answer; nothing requires background work).
- Revalidate if: measured reply time approaches the configured timeout, or reasoning models exceed 120 s.

### AD-8: UI toolkit, visual direction and component states
- Status: accepted.
- Toolkit: reuse Lightning base components and SLDS styling hooks for host chrome (card, button, spinner, icon via the
  SLDS utility icon set only); component-owned CSS uses custom properties scoped to the component's shadow DOM and a
  `grok-` class prefix. No third-party UI package or JS library.
- Visual direction (UI visual-direction guide, "light expressive starting point"): reference = the light Google Gemini look
  with Material 3 Expressive principles, adapted to a Salesforce Lightning host, where Lightning/SLDS platform
  conventions win for page chrome. Starting appearance: light, with a dark option. Concrete choices:
  luminous near-white canvas with a faintly tinted layered surface for the transcript; user messages in a soft tonal
  rounded bubble aligned right, Grok replies unboxed on the canvas with a small gradient "G" mark (the one visual
  signature: a luminous accent ring on the mark that animates only while a reply is pending); a pill-shaped composer
  pinned to the bottom of the component with a circular primary Send button; type = the host's system sans stack, 14px/20px
  body, 12px meta, 20px empty-state heading; spacing scale 4/8/12/16/24; radii 20px containers / 12px controls / 999px
  pill; one saturated accent (blue family) used for Send, focus ring and the pending ring.
- Component states: Not-ready (spec R-9), Empty (welcome + three example prompts that fill the composer, not auto-send),
  Idle, Pending (skeleton reply row + pending ring + Send disabled), Error (inline error row, class-specific text, Retry only
  for the transient group), Disabled composer.
- Motion: reply row fade/rise 160 ms; pending ring pulse; all disabled under `prefers-reduced-motion: reduce` (replaced by a
  static "Grok is thinking" text). Dark: tokens redefined under `prefers-color-scheme: dark`; whether the Lightning host exposes
  a theme signal is unresolved (spec G-12).
- Keyboard: Enter sends, Shift+Enter newline, Escape clears the composer when no request is pending, focus returns to the composer after
  a reply or error; new reply announced by an `aria-live="polite"` region.
- Revalidate if: the org's Lightning theme (SLDS 2 vs SLDS 1) renders the host tokens differently; check at the first browser run.

### AD-9: Test surfaces (decided here so the spec's "how confirmed" lines resolve)
- Status: accepted. Per the platform guide: Jest for the component (local), Apex tests for the service and controller
  (remote, run in the org with `sf apex run test --target-org <alias> --class-names <TestClass> --synchronous --result-format tap`),
  and a browser check of the deployed tab for the consumer surface. Apex tests use `HttpCalloutMock`; a mock proves the
  parse/classify/request-shape logic, not xAI's behavior or the credential. Live xAI behavior and credential
  access are confirmed only by a real send with a real key (spec G-2).
- No Apex test is planned for the LWC-only paths, and none for credential entry.
