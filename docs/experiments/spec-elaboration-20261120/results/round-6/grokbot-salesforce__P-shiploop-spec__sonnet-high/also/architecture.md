# Grok Bot for Salesforce — Architecture

Status: proposed at the spec stage, 2026-11-20. Nothing here has been built, deployed or probed against an org.
`spec.md` says what the product must do; this file records how it is built. A choice about structure or technology
is an `AD-<n>` here and is never a requirement there. Where a decision rests on a platform claim, the source is
named; a claim marked **PROBE** has no probe result yet and must be confirmed before the dependent work is planned
as ready.

## Decisions

### AD-1 Runtime shape: Lightning web component + Apex controller + server-side callout

- Status: proposed. Serves R-2, R-3, R-4, R-8.
- The chat surface is one Lightning web component placed on a custom tab. One Apex entry point (`@AuraEnabled`)
  receives `{message, priorExchanges[]}` and returns `{ok, reply}` or `{ok:false, category}`. The browser never calls
  xAI directly; the browser holds no key and needs no CSP Trusted Site for xAI.
- Alternatives not chosen: a browser-side `fetch` to xAI (would expose the key, violates R-5); an Agentforce or
  Einstein agent with an external action (a different product from the request, see PD-1 in `spec.md`); a
  Flow/HTTP-callout action (no transcript UI).
- Names (component, Apex classes, tab, app, permission set, custom metadata type, external credential, named
  credential) are chosen at step-plan after listing the target org's existing components
  (`sf org list metadata --metadata-type LightningComponentBundle`, `ApexClass`, `CustomTab`, `CustomApplication`,
  `NamedCredential`, `ExternalCredential`, `PermissionSet`, `CustomObject`), per `GUIDES/platforms/salesforce.md`
  "Service discovery". No name is reserved here. Apex and metadata API names are org-wide without a namespace.
- Revalidate when: the target org turns out to hold a clashing name, or a package namespace is introduced.

### AD-2 Callout route and credential custody: Named Credential over an External Credential

- Status: proposed. Serves R-5, R-6, R-10.
- The Apex callout targets `callout:<NamedCredentialName>/...`. The base URL lives in the Named Credential. The API
  key lives in an External Credential using the **Custom** authentication protocol with a **Named Principal**
  identity; an `Authorization: Bearer <key>` header is built by formula from the stored secret parameter
  (`$Credential.<ExternalCredentialName>.<ParamName>`).
- Source: Salesforce Help, "Use API Keys in Custom Headers with Named Credentials" and "Create or Edit a Custom
  Authentication External Credential" (found by search 2026-11-20; page bodies not opened). Search results state:
  Custom protocol supports only the Named Principal identity type; a principal links the external credential to
  permission sets; at run time the platform checks the user holds the permission set; users need access to the
  User External Credentials object.
- Consequence: all permitted users share one key (PD-6). Per-user keys would need a different protocol and are out
  of scope.
- **PROBE (person + org)**: the secret parameter value is entered in Setup after deploy and is not carried by
  source. Confirm in the primary doc or on the first deploy that a retrieve of the External Credential does not
  return the secret. Until confirmed, R-5.2 stays open.
- **PROBE**: the permission set metadata field that grants a principal to a permission set
  (`externalCredentialPrincipalAccesses`) exists at the selected API version.
- A known community note (not verified, about 250 days old at search time) says custom headers are not sent to an
  OAuth token endpoint. It does not apply: this design uses a static key, not OAuth.

### AD-3 Callout style: synchronous Apex callout, not a Continuation

- Status: proposed. Serves R-3, R-7, NFR-1.
- Documented limits (Salesforce Apex Developer Guide, "Callout Limits and Limitations" and "Execution Governors
  and Limits", found by search 2026-11-20): default callout timeout 10 s; configurable per request 1 ms to
  120,000 ms; cumulative callout time per transaction capped at 120 s; 100 callouts per transaction.
- Documented: since Winter '20 all callouts are excluded from the long-running request limit, so a Continuation no
  longer gives a limits advantage; it gives a better user experience (source: Lightning Web Components guide,
  "Make Long-Running Callouts with Continuations", search 2026-11-20).
- Decision: one synchronous callout per turn with `setTimeout(configured ms)`; the LWC awaits the imperative Apex
  call and shows a pending state. Chosen for simplicity and for Apex-testability (Apex tests cannot make callouts
  and use `HttpCalloutMock`; the same source states a Continuation in a static `@AuraEnabled` context is hard to
  test).
- Revalidate when: the configured timeout needs to exceed 120 s, or a measured wait makes the UI unusable
  (a Continuation, up to 3 parallel callouts, global 120 s, would then be reconsidered). Neither is evidenced now.

### AD-4 xAI request contract isolated in one class; endpoint choice is conditional

- Status: **unresolved pending PROBE**. Serves R-3, R-4, R-7, R-10.
- Observed in xAI docs (docs.x.ai, search 2026-11-20): base `https://api.x.ai`; `Authorization: Bearer <key>`;
  `POST /v1/chat/completions` is documented and OpenAI-compatible but labelled **legacy**; the Responses API
  (`/v1/responses`) is labelled recommended and "new features will come there first"; `GET /v1/models` lists the
  model IDs the key may use. The docs name `grok-4.7` as the current flagship, `grok-4.3` and `grok-4.20` variants
  also appear; the search tool itself warned that some page text may be unreliable. Model IDs are therefore
  configuration (R-9), never a literal in code.
- Decision: all xAI request building and response parsing sits in a single Apex class so a switch of endpoint
  touches one file. Default until the probe: Chat Completions (`messages[]` of `{role, content}`; reply at
  `choices[0].message.content`), because its shape is the better documented for a stateless client. The Responses
  API with `store:false` is the candidate if the probe shows chat completions is unavailable or deprecated for
  the key's tier.
- **PROBE** (needs GAP-2 key): one live `GET /v1/models` and one live minimal completion from the target org
  through the Named Credential, recording status, response shape and the model ID used. Mock shapes in Apex tests
  are provisional until this runs (they encode the shape assumption).
- The `user`/identity field of the API is not sent (R-10).

### AD-5 Configuration in custom metadata

- Status: proposed. Serves R-9.
- A custom metadata type holds one configuration record: model ID, system prompt, maximum prompt characters,
  maximum remembered exchanges, callout timeout in ms, optional maximum output tokens. Custom metadata deploys with
  the code (`GUIDES/platforms/salesforce.md`: keep configuration in custom metadata, not records).
- The Apex read of configuration is deliberately a system-level read of non-secret values the product itself owns;
  it is not a read of user data, so sharing/CRUD/FLS enforcement does not apply to it. The secret is never in this
  type. Fields are not renamed after release (API-name rename breaks consumers).
- Defaults carried in the shipped record are the PD-7 assumptions of `spec.md`; editing the record in Setup changes
  behavior with no code change.

### AD-6 Conversation state lives in the component; the server is stateless

- Status: proposed. Serves R-4, R-8, R-11.
- The transcript, in-flight flag and a monotonically increasing conversation generation number live in LWC
  component state. The browser sends the windowed prior exchanges with each call (the component computes the
  window; Apex re-applies the configured limits as the authority, so a tampered client cannot send a larger
  history or longer prompt than configured). No record, platform event, file or cache stores a message.
- Late responses: the component compares the generation number captured at send time with the current one and
  discards a stale response (T-6 in `spec.md`).

### AD-7 Entry and access: custom tab + custom app + one permission set

- Status: proposed. Serves R-2, R-6.
- Source metadata, not a side effect: a `CustomTab` for the component, a `CustomApplication` listing the tab, one
  `PermissionSet` granting: tab visibility, the app, Apex class access for the controller, and the External
  Credential principal. `lightning__Tab` in the component's `js-meta.xml` makes the component eligible only
  (`GUIDES/platforms/salesforce.md`). The route is `/lightning/n/<TabApiName>`.
- Deploy, permission-set assignment and secret entry are separate steps with separate authority (R-1, R-5, R-6).
  The agent must not assign the permission set or enter the key without explicit authorization.
- Probe at prepare and release-check: consumer user, their permission set assignments and `PermissionSetTabSetting`
  rows, per the platform guide's read-only probe.

### AD-8 Apex security posture

- Status: proposed. Serves R-6, NFR-3.
- Controller `with sharing`; the product reads no user records, so sharing, object CRUD and FLS are each recorded
  as not applicable in `spec.md` R-6, not left implicit. Any future record access must use user-mode operations
  (`WITH USER_MODE` / `AccessLevel.USER_MODE`; Salesforce "Secure Apex Classes" and "Enforce Object and Field
  Permissions", search 2026-11-20). One search result states that API version 67.0 and later defaults to user
  mode; **PROBE**: confirm against the selected API version before relying on it; the design does not rely on it.
- The API version is chosen at plan from `sf` org evidence, not assumed here.

### AD-9 UI direction (supports NFR-6)

- Status: proposed; reference and starting appearance are recorded here so planning and acceptance can check the
  rendered result against concrete choices.
- Reference: the light Google Gemini look and feel with Material 3 Expressive principles
  (`GUIDES/platforms/ui.md#light-expressive-starting-point`), adapted inside Lightning Experience. Platform
  conventions take precedence: SLDS styling hooks (CSS custom properties) carry colors, spacing and radii so the
  org theme applies; SLDS utility icons are the single icon set.
- Starting appearance: light first, with a dark token set available. Whether Lightning Experience in the target
  org exposes a user dark theme is **unknown** (GAP-6); the component must not hard-code colors outside the token
  block so either case works.
- Concrete choices: luminous light canvas with a faint tint gradient behind the transcript only; transcript is the
  focal point and takes the widest column (readable measure, centered, with generous side space on wide screens);
  user messages on a tinted accent surface aligned to the end, Grok messages on a neutral tonal surface aligned to
  the start, both softly rounded with a smaller radius on the control set (a deliberate shape hierarchy); composer
  pinned at the bottom as a large rounded surface with a multi-line text area and one strong accent send control;
  humanist system sans-serif (the platform font stack) with a clear size scale; one restrained saturated accent.
  Signature: a soft accent-gradient "thinking" indicator that animates only while a turn is pending and becomes
  static under reduced motion. Header: product name, new-chat action, quiet model/disclosure line.
- Rendering of replies: plain text via text bindings only (no `lwc:dom="manual"` / `innerHTML` / rich-text
  component for model output), `white-space: pre-wrap`, code fences shown in monospace as literal text (R-12).
- Revalidate when: the org's Lightning theme support is probed, or a markdown-rendering decision is made (PD-8).

### AD-10 Test layering (selection input for test-strategy; not a test plan)

- Status: proposed. Serves every R.
- Apex tests (remote, run in the org with `sf apex run test ... --result-format tap`; `HttpCalloutMock` for xAI
  statuses 200/401/404/429/500/malformed and `CalloutException`): request body, history trimming, config limits,
  error categories, no DML, access. LWC Jest: transcript state machine, input validation, stale-response discard,
  safe rendering, accessibility attributes. Browser check in Lightning with the intended permission-set user:
  tab entry, pending/error/empty states, widths, focus, contrast. Live check: one real turn through the credential
  (needs GAP-1, GAP-2). None substitutes for another.
- Apex tests are required because Apex is added; a production deploy would also need the Apex coverage gate, a
  development org deploy does not by itself (verify the actual deploy's effective test level at release-plan).
