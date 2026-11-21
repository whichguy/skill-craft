# Grok Bot for Salesforce: Architecture

Structure and technology decisions only. Product behaviour lives in `spec.md` (R-<n>); nothing here
changes an acceptance line. Every AD below is a **proposal made at spec time**: nothing was built, deployed or
probed. Names are proposed, and the plan must run the name-clash listing (`sf org list metadata`, see
`GUIDES/platforms/salesforce.md` Service discovery) against the target org before freezing them. That check is
**NOT-RUN**: there was no org access or command permission in this stage.

## Decisions

### AD-1 Runtime path: Lightning page, then server operation, then stored credential, then xAI
- **Status:** proposed.
- **Decision:** a Lightning web component `grokChat` (exposed through `lightning__Tab` and a `CustomTab`) calls one
  `@AuraEnabled` Apex method on `GrokChatController`. That method calls `https://api.x.ai` through a Named Credential
  (`callout:Grok_xAI`). The browser never talks to xAI and never holds the key.
- **Why:** the API key cannot live in browser code. A browser call would also need CSP Trusted Sites entries and would
  expose the key. A Named Credential lets Salesforce own the key (primary doc: Salesforce "Named credentials" and
  "Use API Keys in Custom Headers with Named Credentials", help.salesforce.com).
- **Alternatives considered (not selected):**
  - Agentforce / Einstein "bring your own LLM". It was not requested, needs org features not established here, and
    cannot be verified without org evidence. Revisit if the user asks for Agentforce.
  - A Flow HTTP-callout action. It gives weaker control over error classification and testing.
  - Apex Continuation (async callout). See AD-5.
- **Runtime actors:** end user (browser), Salesforce server (Apex under the invoking user), xAI API. `sf` CLI and any
  MCP are development tools only, not runtime actors.
- **Revalidate when:** an org restricts Named Credentials, or the user asks for record-grounded answers.

### AD-2 xAI API surface: Responses API, stateless
- **Status:** proposed; request and response body shapes **not yet probed** (open gap G-4 in `spec.md`).
- **Decision:** `POST https://api.x.ai/v1/responses` with `store:false`. The component and server send the whole
  window each time instead of using `previous_response_id`. The default global endpoint is used. The US regional
  endpoint `https://us.api.x.ai/v1` is not selected because no residency requirement was stated.
- **Why:** xAI documents Chat Completions as legacy/deprecated and `/v1/responses` as the route for new work. Responses
  are stored 30 days by default and `store:false` opts out. Stateless windows match R-3, R-8 and R-9
  (sources: docs.x.ai "Chat Completions" legacy page, "Responses" reference, "Comparison with Chat Completions",
  retrieved by search on 2026-11-21).
- **Mapping to confirm by probe (G-4):** where the system prompt goes (`instructions` or a `system` role in `input`);
  the reply text path (assumed `output[].content[].text` where `type=="output_text"` inside an item whose
  `type=="message"`); whether `store:false` is accepted; the exact error body for 401/429.
- **Fallback if the probe contradicts this:** switch to `/v1/chat/completions`. The server contract (AD-5) and every
  R-<n> stay unchanged because only the adapter's request and parse change.
- **Revalidate when:** xAI changes the API, or model access changes.

### AD-3 Credential custody: External Credential plus Named Credential
- **Status:** proposed.
- **Decision:**
  - External Credential `Grok_xAI_Ext`: Custom protocol, one principal `Grok_Key` (Named Principal), one secret
    parameter `ApiKey`.
  - A custom header `Authorization` on the External Credential with value formula
    `'Bearer ' & $Credential.Grok_xAI_Ext.ApiKey`.
  - Named Credential `Grok_xAI`: URL `https://api.x.ai`, Generate Authorization Header off, Allow Formulas in HTTP
    Header on.
  - Permission set `Grok_Bot_User` carries: access to the Apex class, tab visibility, and the External Credential
    principal. Nothing is assigned by the deploy.
- **Constraint (documented):** Custom authentication is a Named Principal, so every permitted user shares one key.
  A secret cannot be put in the endpoint URL (help.salesforce.com "Use API Keys in Custom Headers with Named
  Credentials"; "Create or Edit a Custom Authentication External Credential").
- **Person-only steps** (cannot be automated here, so they are prerequisites G-1 and G-2): entering the key value in
  Setup, and assigning `Grok_Bot_User` to the test user.
- **Unknown to probe (G-6):** whether redeploying the External Credential metadata preserves the stored key and
  principal credentials.
- **Revalidate when:** per-user billing or identity is requested (this needs a different protocol).

### AD-4 Bot settings in a custom metadata type
- **Status:** proposed.
- **Decision:** custom metadata type `Grok_Bot_Setting__mdt` with one record `Default`. Fields: `Model_Id__c`,
  `System_Prompt__c`, `Timeout_Ms__c`, `Max_Input_Chars__c`, `Max_History_Exchanges__c`. It holds no secrets.
  Defaults are in `spec.md` A-3. It deploys with the code (`GUIDES/platforms/salesforce.md`: configuration goes in
  custom metadata, not records).
- **Consequence:** values in source overwrite admin edits made in the org on the next deploy. This is accepted for a
  development org (A-8).

### AD-5 Synchronous callout with a structured outcome
- **Status:** proposed.
- **Decision:** one synchronous `HttpRequest` per Send with `setTimeout` from settings. The Apex method **returns** an
  outcome object and does not throw for the failure classes in R-5:
  `{ success, reply, category, message }`. `category` is one of `invalid_input`, `not_configured`,
  `connection_failed`, `auth_failed`, `rate_limited`, `upstream_error`, `timeout`, `bad_response`, `internal`. Only
  unexpected platform errors, such as the platform denying class access, reach the component as rejected promises.
  The component maps them to the `internal` message.
- **Why synchronous:** the platform limits are 1 to 120,000 ms per callout, 120 s cumulative, and 100 callouts per
  transaction. This design makes one callout, and callout time is excluded from the 5-second long-running-request
  threshold (developer.salesforce.com "Callout Limits and Limitations", "Execution Governors and Limits").
  Continuation (3 parallel callouts, 120 s, separate transaction) adds complexity without a stated need.
- **No retry inside the server:** a retry could double-bill xAI (R-5 timeout semantics).
- **Security:** class declared `with sharing`. The method does no DML and queries no standard or custom object, only
  the custom metadata record. Sharing, object CRUD and FLS are therefore recorded separately in R-11. Where user mode
  applies it is stated there. The 100-callout and bulk concerns are not applicable because the entry takes one
  conversation and is not reachable from triggers or Flow.
- **Revalidate when:** the org shows concurrent-request-limit errors under many simultaneous waits (G-5 observes
  this), or a streaming requirement appears. Apex HTTP cannot stream.

### AD-6 UI implementation
- **Status:** proposed.
- **Decision:** a single LWC `grokChat`. It uses SLDS 2 styling hooks and CSS custom properties with fallbacks, not
  hard-coded colours, so it inherits the host theme. It uses SLDS utility icons only. Transcript text is bound as text
  (`{message.text}`), never `lwc:dom` or `innerHTML`. The component has an `aria-live="polite"` log region and an
  `role="alert"` error item. Jest tests under `force-app/main/default/lwc/grokChat/__tests__`.
- **Visual direction (from the UI visual-direction guide, light expressive starting point):** light Gemini look and
  feel with Material 3 Expressive principles, adapted to Lightning. Platform conventions (SLDS) take precedence over
  the reference. Concrete treatment is the plan's choice. See spec NFR-5 for the observable criteria.
- **Not selected:** a custom font download, an external UI toolkit or a markdown library. The first two would break
  platform conventions. A markdown renderer would add an XSS surface not requested (R-10).

### AD-7 Conversation state is client-held and stateless on the server
- **Status:** proposed.
- **Decision:** the component holds the transcript in memory. Each Send passes the transcript's last window to Apex.
  The server re-applies the window and role validation (R-3) and trusts nothing the client sends. No custom object, no
  cache, no platform event.
- **Why:** the lifetime is "until Clear or leaving the page" (R-8). Persistence is not requested and would add a
  data-retention duty (A-5).
- **Revalidate when:** history across sessions or admin review is requested. That needs a custom object with sharing
  and a retention rule.

### AD-8 Metadata inventory, naming and delivery
- **Status:** proposed.
- **Planned files** (`force-app/main/default/`):
  - `classes/GrokChatController.cls`, `classes/GrokChatControllerTest.cls`
  - `lwc/grokChat/*`
  - `tabs/Grok_Bot.tab-meta.xml`
  - `objects/Grok_Bot_Setting__mdt/…`, `customMetadata/Grok_Bot_Setting.Default.md-meta.xml`
  - `externalCredentials/Grok_xAI_Ext.externalCredential-meta.xml`
  - `namedCredentials/Grok_xAI.namedCredential-meta.xml`
  - `permissionsets/Grok_Bot_User.permissionset-meta.xml`
  - `sfdx-project.json`, `.gitignore` listing `.sf/` and `.sfdx/`, `package.json` for Jest
- **API version:** the target org's current version, decided at plan from `sf` evidence. It is not fixed here
  (G-3).
- **No app:** the tab is reachable at `/lightning/n/Grok_Bot` and in App Launcher "All Items" for a user with
  visibility. A Lightning app is not requested (A-6).
- **Ordering:** metadata and settings, then the server operation, then the component, then the permission set. The
  deploy is separate from permission-set assignment and key entry, each with its own authorization.
- **Rollback or compensation limit:** a destructive-changes deploy can remove the metadata. It cannot recover a
  stored key, and the key would have to be re-entered.

## Test layers (inputs to test strategy, none run)
- Apex tests in the org with `HttpCalloutMock`, run as `sf apex run test … --result-format tap`. These are remote
  tests.
- Jest for the component, run locally.
- A bounded live probe (G-4, G-5, G-6) with a person-supplied key.
- A browser check as the permitted test user at `/lightning/n/Grok_Bot`, using the authorised `sf org open` flow.
