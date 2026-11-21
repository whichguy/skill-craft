# Grok Bot for Salesforce: architecture

How the product is built. What it must do is in `spec.md`; neither restates the other. Decisions are `AD-<n>`.
Status values: accepted, unresolved, superseded, not applicable. Nothing here was probed against a live org or the
live xAI API (no org alias, credential or xAI key was available to this stage); every "unresolved" names the
confirming observation.

## Decisions

### AD-1: Salesforce-native Lightning app, Apex callout adapter, no middleware (accepted)
- Basis: request "Create a Grok bot in a Salesforce development org" (2026-11-21), read as R-1..R-11 in `spec.md`.
- Choice: a Lightning Web Component (the chat UI) calls one `@AuraEnabled` Apex method; Apex calls the xAI HTTPS API
  directly from the org. No external server, queue, Heroku/AWS relay or Agentforce dependency.
- Why: the request puts the bot inside the org; a relay would be a new component with its own hosting and secret.
  A synchronous callout from user-initiated Apex is allowed when no DML is pending in the transaction (Salesforce Apex
  Developer Guide, "Callout Limits and Limitations": 100 callouts per transaction, 120 s cumulative, per-callout
  timeout 1 ms to 120,000 ms, no callout after uncommitted work). The bot performs no DML, so that rule is met by
  construction.
- Alternatives not pursued: Agentforce agent with a bring-your-own model (different product surface, different
  licensing, not what was asked); Slack bot (request says Salesforce org); Flow HTTP callout action (poor fit for
  history windowing, error mapping and Apex tests).
- Revalidate if: the org lacks Lightning Experience, or Apex callouts to `api.x.ai` are blocked by org policy.

### AD-2: xAI endpoint and wire shape (unresolved)
- Observed (secondary search results 2026-11-21, not a probe): xAI documents Chat Completions
  (`POST https://api.x.ai/v1/chat/completions`, `Authorization: Bearer <key>`, OpenAI-compatible) as *legacy*, and the
  Responses API (`/v1/responses`, `messages` renamed `input`, optional `previous_response_id` statefulness) as
  recommended for new integrations.
- Leaning (not a decision): Responses API, sent stateless (full windowed history every call, no `previous_response_id`),
  because `spec.md` R-9 forbids server-held conversation state. Chat Completions is the fallback if Responses cannot be
  made stateless or its response shape is awkward for Apex.
- Confirming observation: one authorized call per candidate endpoint with a throwaway prompt, recording status, the
  response JSON shape and whether any server-side storage flag exists. Until then the exact mock bodies in the `spec.md`
  cases are written as `SUCCESS_BODY(<text>)`.
- Blocks: the Apex request builder and response parser work item, and the concrete mock bodies in the Apex tests.
  Does not block metadata, UI, permission-set or deployment work.

### AD-3: Credential custody via External Credential + Named Credential (accepted, details unresolved)
- Choice: the xAI API key lives only in an External Credential (custom protocol, a named principal, one `Authorization`
  header parameter with value `Bearer <key>`); a Named Credential references it as the callout endpoint
  (`callout:<NamedCredential>/v1/...`). The key is typed into Setup by an admin after deploy and never appears in
  source, Custom Metadata, Apex, LWC, logs or test fixtures. Salesforce documents that a Named Credential removes the
  need to hard-code endpoint and auth into Apex, and that an external credential's principal points at a permission set
  that decides which users may use it (Named Credentials Glossary; External Credential Metadata API reference).
- Unresolved: (a) whether the custom-header parameter can hold the key as a secret value deployed *empty* and filled
  later; (b) the exact metadata element names at the org's API version; (c) whether the credential values survive a
  redeploy unchanged. Confirming observation: `sf project deploy validate` of the metadata plus a read-back of
  the principal after deploy (values are never read back).
- Not chosen: key in Custom Metadata or a custom setting (readable by admins and exported with metadata), key in a
  Protected Custom Metadata record (still source-controlled when deployed).

### AD-4: Conversation state lives only in the LWC (accepted)
- Choice: the transcript and the request-in-flight marker are component fields in the browser. Apex is stateless; the
  client sends the windowed history on every call. No custom object, no Platform Cache, no Big Object.
- Why: R-9 (no stored transcript) and "add no persistence the request does not need". Local memory is enough for a
  single-user, single-tab interaction. Consequence: a browser refresh ends the conversation; this is a stated
  behaviour, not a defect.
- Trusted-input note: because history comes from the client, the server treats it as untrusted input (role values
  whitelisted to `user` and `assistant`, sizes bounded, system prompt never taken from the client).
- Revalidate if a requirement for transcripts, audit or cross-device continuity is added.

### AD-5: Configuration in a Custom Metadata Type (accepted)
- Choice: one `GrokBot_Config__mdt` record `Default` holds model ID, system prompt, callout timeout (ms), max input
  characters, history window size. Deploys with the code, editable in Setup without a code change.
- The model ID default is unresolved (xAI model names in third-party sources disagree: grok-4.3, 4.5, 4.6, 4.7); it is
  read from xAI's current model list at research. See spec gap G-3.

### AD-6: Names (accepted as proposal; clash check is a prerequisite)
Apex and metadata names are org-wide (Salesforce guide `platforms/salesforce.md`). Proposed, all prefixed `GrokBot`:
Apex `GrokBotController`, `GrokBotService`, `GrokBotController_Test`; LWC `grokBotChat`; CMDT `GrokBot_Config__mdt`;
External Credential `GrokBot_xAI`; Named Credential `GrokBot_xAI_API`; Permission Set `GrokBot_User`; Custom Tab
`GrokBot`; Lightning App `GrokBot`. Before planning: list `LightningComponentBundle`, `CustomTab`, `CustomApplication`,
`ApexClass`, `PermissionSet` metadata in the target org and pick other names if any clash.

### AD-7: Authority split (accepted)
Four distinct identities, each recorded separately because none implies another: (1) the *developer/deployer* running
`sf` (metadata deploy, permission-set creation); (2) the *org admin* who enters the xAI key and assigns the permission
set; (3) the *end user* who chats and whose permission set grants Apex class access, tab visibility and external
credential principal access; (4) *xAI*, which sees only the callout. Apex runs in the end user's context (user mode
for any queries; there are none beyond reading the CMDT, which is not user data). A deployer's access establishes
nothing about an end user's access.

### AD-8: Rendering of model output (accepted)
Grok replies are rendered as text nodes (LWC template interpolation), never as HTML (`lwc:dom="manual"` / `innerHTML`
/ `lightning-formatted-rich-text` are not used on model output). Markdown is not rendered in this version; line breaks
and whitespace are preserved with CSS. Why: model output is untrusted; XSS through a reply is the one injection path
the bot exposes.
