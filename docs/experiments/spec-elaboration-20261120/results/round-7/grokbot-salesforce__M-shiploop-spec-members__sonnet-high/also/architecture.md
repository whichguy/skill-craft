# GrokBot for Salesforce: architecture decisions

Structure and technology choices live here, never in `spec.md`. Each decision is **proposed** at the spec stage:
no org, repository or key was inspected (spec.md G-1, G-2), so nothing below is "accepted by observation". Planning
reopens each entry and revalidates it against the observed org. Primary sources are listed at the end.

## Decisions

### AD-1: Chat surface is a Lightning web component calling Apex; the browser never talks to xAI
- **Status:** proposed. **Serves:** R-1, R-2, R-3, R-8, R-9, R-12.
- Lightning web component (LWC) for the UI; Apex `@AuraEnabled` methods for send, list, load and delete. All names
  carry the prefix `GrokBot` (Apex class names, metadata API names and custom objects are org-wide; clash check is G-1).
- Reason: the credential must not reach the browser (R-7); Salesforce's callout machinery (Named Credential) is
  available only from server-side Apex/Flow, and a browser call would also need CSP Trusted Sites.
- Alternatives considered: Agentforce/Einstein agent (rejected: needs separate licences and model hosting, the
  request names Grok, not Agentforce); Flow with an HTTP Callout action (rejected: poor control over error classes
  and history windowing); Experience Cloud or Slack surfaces (out of scope).
- Apex runs in **user mode** (`WITH USER_MODE` queries, `AccessLevel.USER_MODE` DML) inside `with sharing` classes, so
  sharing, object CRUD and FLS are enforced separately (R-9). API version: the org's current supported version,
  verified at prepare (G-1); not assumed.

### AD-2: xAI credential is an External Credential plus Named Credential; the key is never in metadata, code or records
- **Status:** proposed. **Serves:** R-7, R-3.
- Named Credential `GrokBot_xAI` (endpoint base `https://api.x.ai`) references External Credential
  `GrokBot_xAI_Cred` (custom protocol, one named principal, one custom header `Authorization` whose value is
  `Bearer ` plus the secret parameter). The secret value is entered by an administrator in Setup after deploy; the
  deployed metadata carries the credential's shape, not its value.
- Callers reach it by `callout:GrokBot_xAI/...`. The running user needs External Credential Principal Access, granted
  through the GrokBot user permission set (AD-8). Whether Apex additionally needs read on user-external-credential
  data for a *named* principal is **unverified** (a community source only): probe, G-4.
- Alternative: key in custom metadata or a custom setting (rejected: readable by admins and by deploys, appears in
  source control).

### AD-3: Conversations are two custom objects in a master-detail relationship
- **Status:** proposed. **Serves:** R-8, R-9, R-10, R-12.
- `GrokBot_Conversation__c`: Name (title, 80 chars, per R-8), `Last_Message_At__c` (datetime). Organisation-wide
  default **Private**, so only the owner reads it.
- `GrokBot_Message__c`: master-detail to the conversation (cascade delete, sharing inherited from the parent),
  `Role__c` (restricted picklist `User` | `Assistant`), `Content__c` (long text area, 32768). Order is by an
  auto-number Name, so a pair inserted in one DML keeps its order and adjacency.
- No existing standard or custom object fits (checked only by reasoning: org inventory is G-1). Tokens, model id and
  raw response body are deliberately **not** stored (R-12/R-7 minimise retained data).

### AD-4: Behaviour settings are one custom metadata type with a `Default` record
- **Status:** proposed. **Serves:** R-11 and every default in spec.md "Defaults".
- `GrokBot_Setting__mdt`, record `Default`: Model, System_Prompt, Timeout_Ms, Max_User_Chars, History_Window,
  Max_Messages_Per_Conversation, Max_Output_Tokens, List_Limit. Deployed with the code; edited by an administrator.
  Contains nothing secret.

### AD-5: Callout first, then one all-or-nothing write (platform ordering rule)
- **Status:** proposed. **Serves:** R-3, R-6, R-12.
- Apex may not make a callout in a transaction that already holds uncommitted DML. So a send is: validate; read
  settings and (if the conversation exists) read history with SOQL; **one** callout; then insert (conversation if
  new, user message, assistant message) in a single DML section with a savepoint. A failed callout therefore leaves
  no row behind, and the browser keeps the draft for retry (R-6).
- Alternative: persist the user message first, then callout in Queueable (rejected: second transaction, extra
  status states, no need for async: replies fit inside the 120 s cumulative callout bound).
- Synchronous callout from `@AuraEnabled` (not Continuation): one callout per request, within the 100-callout and
  120 s limits. Reopen if a model routinely needs more than the configured timeout (G-8).

### AD-6: xAI endpoint is the stateless Chat Completions API, history resent from Salesforce
- **Status:** proposed; **endpoint family is the least certain choice**. **Serves:** R-3, R-4.
- `POST /v1/chat/completions` with `model`, `messages` (system + history + new user message), `max_tokens`
  (naming of the output-cap parameter is to be confirmed by probe, G-3), `stream: false`. Reply text is
  `choices[0].message.content`.
- xAI's documentation marks Chat Completions as legacy and says new features arrive first in the Responses API
  (`/v1/responses`, with optional server-held state via `previous_response_id`, stored 30 days unless `store:false`).
  Chosen anyway because it is stateless (Salesforce owns the transcript, so delete in R-10 truly removes it from our
  side) and its request/response shape is documented. Responses with `store:false` is the consequential alternative;
  switching is a change to one Apex adapter class and the Named Credential path.
- Streaming rejected: the Apex callout API returns a complete response; tokens cannot be forwarded progressively.

### AD-7: Consumer entry is a custom tab inside a dedicated Lightning app
- **Status:** proposed. **Serves:** R-2.
- LWC `grokBotChat` exposes `lightning__Tab`; `CustomTab` `GrokBot` (label "Grok Bot", path
  `/lightning/n/GrokBot`); `CustomApplication` `GrokBot` lists the tab. `lightning__Tab` alone creates no tab
  (`GUIDES/platforms/salesforce.md`, Service discovery). Tab and app visibility come from the permission set (AD-8).
- UI skin: Salesforce Lightning Design System (SLDS) tokens and styling hooks, because the platform convention
  takes precedence over a bespoke palette; see spec.md NFR-8 for the recorded visual direction.

### AD-8: Two permission sets; deploy and assignment are separate authorisations
- **Status:** proposed. **Serves:** R-2, R-7, R-9.
- `GrokBot_User`: tab and app visibility, Apex class access, CRUD and FLS on both objects (create, read, delete of
  own conversations; no edit of messages), External Credential principal access (AD-2).
- `GrokBot_Admin`: read and edit on `GrokBot_Setting__mdt` is a Setup right, not an object permission, so the admin
  role is documentation of who sets the key and settings rather than a second permission set (**simplification:
  one permission set**; reopen if G-4 shows the principal needs separate handling).
- Assigning `GrokBot_User` to a person is its own command with its own authority (G-10).

### AD-9: Reads are not cached; the client re-reads after every mutation
- **Status:** proposed. **Serves:** R-8, R-10, R-12.
- List and transcript methods are not `cacheable=true`; the LWC calls them imperatively after a send, an error, or a
  delete. Reason: they are authorisation- and freshness-sensitive and data changes by DML in the same session; stale
  wire results would mask E-SAVE/unknown outcomes (R-8). No client storage of drafts or messages.

### AD-10: Observability is the platform's own, plus categorised failure logging
- **Status:** proposed. **Serves:** NFR-5.
- Apex writes one `System.debug` line per failed send with error code, HTTP status and conversation Id; never the
  prompt, reply text, headers or key. No new log object. Event Monitoring or debug-log retention is not assumed.

## Sources used for the decisions above
- Apex callout limits (120 s cumulative, 100 callouts, 1 ms to 120000 ms per-request timeout, no callout with
  uncommitted work pending): `developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexref/apex_callouts_timeouts.htm`
  (search result 2026-11-21; the pending-work rule appeared in one rendering of the page only, so probe in G-1 flow).
- Named/External Credentials structure, principals, custom headers:
  `developer.salesforce.com/docs/platform/named-credentials/guide`, `.../nc-glossary.html`,
  `.../api_meta.meta/api_meta/meta_externalcredential.htm`.
- xAI Chat Completions (`https://api.x.ai/v1/chat/completions`, Bearer token, legacy status): `docs.x.ai/developers/rest-api-reference/inference/chat-completions.md`.
- xAI Responses API, `previous_response_id`, 30-day storage, `store:false`: `docs.x.ai/developers/rest-api-reference/inference/responses.md`.
- Secure Apex / CRUD-FLS / sharing: `GUIDES/platforms/salesforce.md`.
