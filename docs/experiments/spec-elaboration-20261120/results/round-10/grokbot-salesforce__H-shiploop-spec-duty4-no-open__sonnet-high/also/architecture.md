# Grok Bot for Salesforce — Architecture decisions

Structure and technology choices only. Product behaviour lives in `spec.md` as R-<n>. Status values: accepted,
unresolved, superseded, not applicable. Evidence limits are stated per decision; nothing here was executed against an
org (the spec stage runs no org command).

## Decisions

### AD-1 Shape: one LWC + one Apex controller + one Named Credential (accepted)
- Runtime path: browser LWC `grokBot` → imperative Apex call `GrokBotController.send` (`@AuraEnabled`, not
  `cacheable`, because it makes a callout) → `GrokClient` (HTTP) → `callout:Grok_API/chat/completions` → xAI.
- Reuse/configure/extend/new classification: Salesforce Lightning tab + LWC (new, nothing exists to extend); Named
  Credential + External Credential (configure the native credential facility; no key in code); Custom Metadata Type
  (new, native configuration home); no custom object, no cache, no queue, no Platform Event.
- Rejected: Agentforce / Einstein agent (the request is a Grok bot, not a Salesforce agent; would add a licence
  dependency); Flow HTTP callout (cannot express history trimming, role allow-listing or error mapping testably);
  Apex Queueable/async (a single synchronous callout fits the platform limits below; async would need a durable
  result store the requirements do not ask for).
- Controller is `with sharing`, performs no SOQL and no DML. `with sharing` is not what protects access here; access is
  enforced by the permission set (AD-5) and the External Credential principal grant. Object CRUD/FLS: not applicable
  because no standard or custom object is read or written; the Custom Metadata read is of the app's own
  configuration type.
- Evidence: Salesforce Apex callout limits page (100 callouts/transaction, 120 s cumulative timeout, 10 s default,
  120 000 ms maximum per callout, no callout after pending DML) —
  https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexref/apex_callouts_timeouts.htm, read through
  search results on 2026-11-21, not opened in full. Revalidate at plan with the target org's API version.

### AD-2 xAI protocol: Chat Completions, stateless, history held by the client (accepted)
- Endpoint `POST https://api.x.ai/v1/chat/completions`, `Authorization: Bearer <key>`, OpenAI-compatible body
  (`model`, `messages[{role,content}]`, `max_completion_tokens`, `stream:false`). Source: xAI docs
  (https://docs.x.ai/developers/rest-api-reference/inference/chat-completions.md), via search results 2026-11-21.
  `max_completion_tokens` is the current field; `max_tokens` is deprecated (same source). The `messages` role set and
  `stream` field are taken from the OpenAI-compatible claim and are **unverified against the primary page**: confirm
  at plan by fetching that page, and at prepare by one live call.
- Chosen over the Responses API (`POST /v1/responses`, `previous_response_id`) because Responses are stored by xAI for
  30 days (same docs, comparison page) and the `store` default was not confirmed; stateless Chat Completions keeps
  conversation memory in the browser and avoids a second retention location. xAI marks Chat Completions "legacy";
  revalidation trigger: xAI announces removal or a model that Chat Completions cannot serve (R-8 model change).
- No streaming: Apex callouts return the whole body; the UI shows a pending state (R-2).

### AD-3 Contract between LWC and Apex (accepted)
- Request DTO: `{ messages: [{role, content}] }` (the visible transcript, newest last, ending with the new user
  message). Response DTO (Apex never throws to the LWC for a handled failure; `AuraHandledException` messages are
  masked in production and cannot carry a code):
  `{ success: Boolean, reply: String, errorCode: String, errorMessage: String, correlationId: String }`.
- `errorCode` values: `INPUT`, `CONFIG`, `AUTH`, `RATE_LIMIT`, `UPSTREAM`, `TIMEOUT`, `BAD_RESPONSE`, `REQUEST`.
  Mapping of HTTP/Apex outcomes to codes is behaviour and is specified in R-6.
- Apex re-derives everything it trusts: system prompt from configuration; role allow-list `user`/`assistant`;
  trimming to the history bound; per-message length bound; total of one callout.
- `correlationId`: a random UUID (`System.UUID.randomUUID()`-style) generated per send; no user data in it.

### AD-4 Metadata names and inventory (accepted, collision check pending at prepare)
All names carry the `Grok` prefix; no namespace. Collision check (`sf org list metadata` for `ApexClass`,
`LightningComponentBundle`, `CustomTab`, `CustomApplication`, `CustomObject`, `ExternalCredential`, `NamedCredential`,
`PermissionSet`) is a prepare-time step against the actual org; a clash renames the artifact and records the change
here.

| Artifact | API name |
|---|---|
| LWC bundle | `grokBot` |
| Apex controller | `GrokBotController` |
| Apex HTTP client | `GrokClient` |
| Apex tests | `GrokBotControllerTest`, `GrokClientTest` |
| Custom Metadata Type | `Grok_Bot_Setting__mdt` (fields `Model__c`, `System_Prompt__c`, `Max_Tokens__c`, `Max_History_Messages__c`, `Max_Input_Chars__c`, `Timeout_Ms__c`); one record `Grok_Bot_Setting.Default` |
| External Credential | `Grok_xAI` (protocol Custom, named principal `Grok_Service`, one secret authentication parameter holding the API key, and an `AuthHeader` parameter `Authorization` = `Bearer ` + that secret) |
| Named Credential | `Grok_API` (URL `https://api.x.ai/v1`, bound to `Grok_xAI`) |
| Permission set | `Grok_Bot_User` (tab, Apex classes, External Credential principal access) |
| Tab | `Grok_Bot` (LWC tab); App `Grok_Bot_App` listing the tab |

- Evidence limit: the External Credential/Named Credential structure (principal, permission-set-gated principal
  access, `AuthHeader` custom header with a runtime formula, admin switch that allows Apex-built headers) comes from
  Salesforce documentation seen through search results
  (https://developer.salesforce.com/docs/platform/named-credentials/guide/get-started.html and the "Custom Headers
  and Bodies of Apex Callouts That Use Named Credentials" Apex guide page), not opened in full. The exact merge-field
  formula for the secret parameter and whether the key can be set without the Setup UI are **unverified**: the plan
  confirms them with `sf project deploy validate` and a live call. Secret values are never deployable source.

### AD-5 Access: permission set, not profile (accepted)
`Grok_Bot_User` grants: visibility of tab `Grok_Bot` and app `Grok_Bot_App`; access to `GrokBotController` (and
`GrokClient` if referenced directly); External Credential principal access for `Grok_xAI`/`Grok_Service`. Salesforce
guidance prefers permission sets (same Named Credentials guide). Assignment to a user is a separate authorised step
planned by name at release-plan; the deployment never assigns it silently. The configuration CMT type is readable by
Apex without a grant.

### AD-6 Test selection (accepted)
- LWC behaviour: Jest (`@salesforce/sfdx-lwc-jest`), Apex imports mocked. Proves rendering, state machine, and
  request payload, not Apex or org behaviour.
- Apex: `GrokBotControllerTest`/`GrokClientTest` with `HttpCalloutMock`, run in the org with
  `sf apex run test --target-org <alias> --class-names <Class> --synchronous --result-format tap`. These are remote
  tests (not mutation-checked, not base-run).
- Live: browser check of `/lightning/n/Grok_Bot` as the permission-set user, after the person-only key step (spec
  P-1). A mock-based pass never substitutes for it.
- Apex coverage: no production deploy gate was stated; tests are written for the changed Apex regardless. Org-level
  coverage gate for a non-dev target: unresolved, not applicable to a development org.

### AD-7 API version (unresolved value, rule accepted)
Source API version = the highest version the target org reports as supported, read at plan (`sf org list api` or
`sf project generate` default) and recorded in `sfdx-project.json`. No version is asserted here.

### AD-8 UI technology (accepted)
LWC with SLDS utility/styling hooks and `lightning-icon` utility icons only (one icon set). Light/dark follow the
Lightning platform appearance (platform conventions take precedence over a bespoke theme); concrete token mapping is
a plan decision recorded in `plan` output and revalidated by the rendered-UI check in spec NFR-UI.
