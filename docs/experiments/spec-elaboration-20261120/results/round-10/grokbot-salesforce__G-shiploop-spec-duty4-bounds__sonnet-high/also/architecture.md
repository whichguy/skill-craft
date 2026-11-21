# Grok Bot for Salesforce: architecture

Structure and technology choices for the product specified in `spec.md`. Requirements never live here; decisions
are referenced from `spec.md` by AD-<n>. Status values: accepted-default (chosen under unattended policy, reversible),
unresolved, superseded.

## Decisions

### AD-1 Interpretation: a custom chat component backed by a server-side call to xAI's Grok API
- Status: accepted-default. Basis: request "Create a Grok bot in a Salesforce development org." (2026-11-21).
  "Grok" is xAI's model family; "bot" is read as a conversational chat surface. Salesforce also ships its own
  "Einstein Bot" / Agentforce agent product; the request names neither.
- Chosen: a Lightning web component chat UI, an Apex controller, and a callout to the xAI HTTP API.
- Alternatives not chosen: (a) an Agentforce/Einstein Bot whose LLM is a bring-your-own Grok model (needs an
  Agentforce-enabled org and a model-registration route this stage did not verify); (b) a Flow with an HTTP callout
  action (no multi-turn UI); (c) a browser-side direct call to api.x.ai (would put the API key in the client).
- Revalidate if the user says the bot must be an Agentforce/Einstein Bot or surface in Messaging/Experience Cloud.
- Evidence limit: no org was inspected, so (a) is unconfirmed rather than ruled out.

### AD-2 API key custody: Named Credential plus External Credential, shared named principal
- Status: accepted-default. The key lives only in an External Credential principal (secret entered by an org admin
  in Setup), referenced by a Named Credential whose URL is `https://api.x.ai`; Apex addresses it as
  `callout:<NamedCredentialApiName>/<path>`. No key in source, Custom Metadata, Custom Settings, records or LWC.
- Access: an External Credential principal is usable only by users whose permission set (or profile) is mapped to
  the principal (Salesforce Named Credentials documentation, found by search, not opened in full).
- Bearer header: the External Credential custom-header (AuthHeader) parameter is expected to carry
  `Authorization: Bearer <key>`; this exact setup is UNVERIFIED until step-plan reads the Named Credentials
  reference or a probe succeeds.
- Alternatives not chosen: per-user principal (every user would need their own xAI key; not requested); Remote Site
  Setting with a key in Custom Metadata (key readable by admins and by metadata retrieval).
- Secret values are not metadata that can be deployed from source: the secret is a person-only step (G-2).

### AD-3 Wire contract: xAI Chat Completions, endpoint path held in configuration
- Status: accepted-default, revalidate at step-plan. Evidence: the xAI documentation (search result titled
  "Model Capabilities / legacy / chat-completions", docs.x.ai) lists POST `https://api.x.ai/v1/chat/completions`,
  Bearer authentication, and labels Chat Completions "legacy" with new features arriving first on the Responses API.
- Chosen: Chat Completions, because its request/response is a single synchronous JSON exchange that fits an Apex
  callout. The base path and model ID are configuration (AD-4) so that a move to the Responses API changes the
  adapter and configuration, not the UI.
- Expected response read: `choices[0].message.content` and `choices[0].finish_reason`. UNVERIFIED against the
  official page (only third-party guides describe OpenAI compatibility); step-plan reads the official reference
  and, once G-2 is resolved, one authorized smoke call confirms it.
- Alternatives: Responses API (newer, schema unread); streaming (see AD-6).
- Revalidate when xAI deprecates the endpoint or the probe contradicts the response read.

### AD-4 Configuration in a Custom Metadata Type
- Status: accepted-default. One Custom Metadata Type with one record holds: model ID, system prompt, endpoint path,
  max output tokens, callout timeout ms, history exchanges, max user-message characters, max history-message
  characters. Custom Metadata deploys with the code (Salesforce platform guide, `GUIDES/platforms/salesforce.md`
  "Model stored data"). Defaults are D-1..D-9 in `spec.md` R-6. Values are read by Apex on each request (no
  caching), so an edit in Setup takes effect on the next send.
- No secret in this type (AD-2).

### AD-5 Stateless Apex; transcript owned by the component instance
- Status: accepted-default. The Apex method receives the new user message plus the prior completed exchanges from
  the component and holds no state between calls (no records, no Platform Cache, no Custom Setting writes). The
  component keeps the transcript in memory for the life of the page. Consequence: refresh, navigation or "Clear"
  ends the conversation (R-8).
- Alternatives not chosen: a custom `Conversation__c`/`Message__c` pair (adds CRUD/FLS, sharing, retention and
  deletion obligations the request does not ask for); Platform Cache.
- Revalidate if the user asks for saved or shared conversations.

### AD-6 One synchronous, non-cacheable Apex invocation per send; no streaming
- Status: accepted-default. The component calls an `@AuraEnabled` (non-cacheable) method imperatively; one send is
  one callout. Apex callouts are request/response; incremental token streaming to the browser is not
  provided by this route. UNVERIFIED as a platform statement: step-plan confirms it in the Apex callout
  documentation before the spec's "no streaming" non-goal is relied on.
- The method returns a structured result (success flag, reply, finish reason, stable error code, safe message)
  rather than letting a raw exception text reach the client (R-7).
- Alternatives: Queueable/async completion with polling (adds a status record and a recovery owner with no benefit
  for a request that fits in the 120 s synchronous callout limit).

### AD-7 Consumer entry: custom tab and app, permission set grants everything
- Status: accepted-default, per `GUIDES/platforms/salesforce.md` "Service discovery". Metadata set: the LWC bundle
  (`lightning__Tab` target), a `CustomTab`, a `CustomApplication` listing the tab, one permission set granting tab
  visibility, access to the Apex class, and the External Credential principal. Names carry the prefix `GrokBot` /
  `grokBot`; step-plan lists existing metadata in the target org (`LightningComponentBundle`, `CustomTab`,
  `CustomApplication`, `ApexClass`, `NamedCredential`) to rule out a clash before fixing names.
- Deploy, permission-set assignment, and the credential secret are three separate steps with separate authority.

### AD-8 Verification surfaces
- Status: accepted-default. Apex tests use `Test.setMock(HttpCalloutMock.class, ...)` because a test cannot make a
  real callout (UNVERIFIED here; confirm at step-plan). LWC logic is exercised with Jest. The deployed behaviour is
  observed in a browser at `/lightning/n/<TabApiName>` as an assigned user. A live xAI call needs G-1 and G-2.
- Apex test commands use `--result-format tap` (platform guide "Testing").
