# Grok Bot for Salesforce: architecture

How the product is built. What it must do is in `spec.md` (`R-<n>`); this file holds structure and technology
choices as `AD-<n>`. It records names and shapes, never secret values. Nothing here has been implemented or
probed against an org: every status is a *proposal* (accepted for planning) unless it says unresolved.

## Stack

- Salesforce Lightning Web Components (UI), Apex (server logic), Salesforce Named Credential + External
  Credential (outbound call and key custody), Custom Metadata Type (configuration), Permission Set (access),
  Custom Tab + Lightning App (entry). Source format (`force-app/main/default/...`), unmanaged, no namespace.
- Tooling: Salesforce CLI (`sf`) for deploy/validate/test/listing; LWC Jest (`@salesforce/sfdx-lwc-jest`) for
  local component tests; Apex tests run in the org. Runtime versions and working commands are recorded in
  `environment.md` once discovered (none exist yet).
- External: xAI API (Grok models). The product has no other runtime dependency and adds no npm runtime library.

## Structure

Runtime path: **user → LWC → Apex controller → Named Credential → xAI API**. The deploy CLI is a development
tool and is not on that path.

| Part | Responsibility | Owner of |
| --- | --- | --- |
| LWC (chat component) | Transcript, draft, pending/error/empty states, client-side validation, stale-reply discard, rendering | Transient conversation state (R-10) |
| Apex controller (`@AuraEnabled`, imperative) | Thin entry: validates, delegates, returns the result DTO | Nothing stateful |
| Apex service | Builds the window (R-4), reads configuration (R-9), makes the single callout, parses the reply, classifies failures (R-6) | Provider-call contract |
| Config custom metadata type + default record | Model, system prompt, limits | Configuration (R-9) |
| External + Named Credential | Endpoint host, key custody, Bearer header | The key's storage (R-7) |
| Permission set | Tab/app visibility, Apex class access, credential principal access | Access grants (R-8) |
| Tab + app | Consumer entry (R-2) | Entry |

## Conventions

- Names carry the `GrokBot` prefix (see AD-4). No `global` members; no namespace.
- The Apex service takes its HTTP boundary through an overridable seam so tests can use `HttpCalloutMock`.
- Errors cross the Apex/LWC boundary as a result object, not as thrown exceptions (AD-6).
- LWC styling uses SLDS styling hooks/tokens; component CSS classes use the `grok-` prefix; no `window`
  globals, no `localStorage`/`sessionStorage` of message content (R-10, R-14).
- `.sf/` and `.sfdx/` are git-ignored (R-16).

## Interfaces and boundaries

- **LWC → Apex:** one imperative method taking the message list `[{role, content}]` (roles `user`/`assistant`
  only) and returning `{ok, reply, errorCategory, userMessage}`. Not cacheable.
- **Apex → xAI:** one HTTPS POST per accepted send through the named credential; JSON body of model, messages
  (system prompt first), `stream:false`, optional max output tokens; the reply text is taken from the
  response. Endpoint shape depends on AD-2.
- **Authority:** user's Salesforce session for the browser→Apex hop; platform credential principal for
  Apex→xAI. No caching at either hop. (Spec "Service boundaries".)

## Real-boundary checks

Things a local test cannot prove, each with its owner (see spec R-15):

| Check | Surface | Owner | Prerequisite |
| --- | --- | --- | --- |
| Deploy terminal status and metadata read-back | Org via `sf` | Run | OG-2 |
| Apex tests incl. callout mock, config, validation | Org remote test (TAP) | Run | OG-2 |
| Tab visible only with permission set; chat renders | Browser via `sf org open` route | Run | OG-2, OG-6 |
| Real Grok reply; auth/principal failure behaviour | Browser + xAI live | xAI account owner (key), admin (principal) | OG-3, OG-4 |
| Log contains no message text | Org remote test + `sf apex get log` | Run | OG-2 |
| Accessibility, contrast, overflow, reduced motion | Browser | Run | OG-2 |

## Decisions

### AD-1 Chat assistant as LWC + Apex on a custom tab
- **Status:** proposed (accepted for planning); depends on user confirming PD-1 (OG-1).
- **Choice:** a Lightning web component exposed to a Lightning tab, calling a single Apex controller, which
  calls xAI. A Lightning app lists the tab so App Launcher has a stable entry.
- **Why:** smallest structure that satisfies R-1 to R-4 inside the org with the platform's own UI and access
  model; reuses native facilities (named credential, permission set, custom metadata).
- **Alternatives:** Agentforce/Einstein Bot Builder (needs licensing and a different runtime, not requested);
  Flow + invocable Apex screen (weaker interaction and UI control for R-12); Visualforce (legacy); external
  chat site (not "in the org").
- **Evidence limit:** `lightning__Tab` on the component only makes it eligible for a tab; the tab and app are
  separate metadata files (Salesforce platform guidance in `GUIDES/platforms/salesforce.md`).

### AD-2 xAI endpoint and wire shape: UNRESOLVED
- **Status:** unresolved (spec OG-13, EL-1/EL-2).
- **Default for planning:** `POST /v1/chat/completions` (OpenAI-compatible; request `{model, messages[],
  stream:false, max_tokens?}`; reply at `choices[0].message.content`), because its shape is widely documented.
- **Conflict:** xAI documentation was reported as marking Chat Completions legacy with `/v1/responses` as the
  primary interface; a second search could not confirm. The Responses request/response shape was **not
  verified**.
- **Rule:** the parsing and request building sit behind one Apex method so switching endpoint changes one
  class; spec behaviour is endpoint-agnostic. Resolve by reading docs.x.ai at planning and, with a key, one
  probe call. Do not hard-code a model name in code (AD-5).
- **Revalidation triggers:** the xAI docs change; the probe returns 404/410 or a deprecation notice.

### AD-3 Credential custody: External Credential + Named Credential
- **Status:** proposed; OG-8 open.
- **Choice:** the xAI host and a Bearer header are carried by a Named Credential (new External-Credential
  model, which Salesforce recommends over legacy named credentials); the API key is a principal parameter
  entered by an administrator in Setup; the Apex only builds a `callout:<NamedCredentialApiName>/...` endpoint.
  Principal access is granted by the permission set (AD-8).
- **Why:** key never in source, browser or Apex; callout authorization is platform-enforced and revocable per
  permission set; avoids a separate Remote Site Setting (to verify at plan).
- **Alternatives:** key in custom metadata/custom setting/custom label (stored in plain text, deployable, too
  readable: rejected); legacy named credential password (discouraged by Salesforce); protected custom
  metadata (not verified suitable).
- **Evidence limit:** header formula syntax for referencing a principal parameter and whether secret values are
  excluded from retrieved metadata were not verified (OG-8). Do not retrieve credential values into the repo.

### AD-4 Naming (to be checked against the org before use, OG-5)
- **Status:** proposed.
- LWC `grokBotChat`; Apex `GrokBotController`, `GrokBotService`, `GrokBotServiceTest`; custom metadata type
  `GrokBotConfig__mdt` with default record `GrokBotConfig.Default`; External Credential and Named Credential
  `GrokXai`; permission set `Grok_Bot_User`; tab `Grok_Bot` (label "Grok Bot", path
  `/lightning/n/Grok_Bot`); app `Grok_Bot` (label "Grok Bot").
- **Rule:** verify no clash with `sf org list metadata` for each type before the first deploy; on a clash
  change the bot's name, never overwrite. Another ShipLoop run in the same org is a naming constraint.

### AD-5 Configuration in a custom metadata type
- **Status:** proposed.
- **Choice:** one `GrokBotConfig__mdt` record (model name, system prompt, max input length, history window,
  timeout ms, optional max output tokens), read per send without SOQL (`getInstance`-style access).
- **Why:** deploys with code; admin-editable without a code deploy; platform guidance prefers metadata types
  over records for configuration. Not a secret store (R-7).
- **Evidence limit:** the exact read API and field types are settled at step planning.

### AD-6 Result object instead of thrown errors
- **Status:** proposed.
- **Choice:** the controller returns `{ok, reply, errorCategory, userMessage}` with the R-6 categories and
  never throws to the UI for expected failures.
- **Why:** gives the UI deterministic categories and avoids relying on how the platform masks exception
  messages (not verified here); keeps provider bodies and keys out of user-visible text by construction.

### AD-7 Conversation state lives in the component
- **Status:** proposed.
- **Choice:** transcript, draft, pending flag and a request sequence token are LWC component state; the Apex
  side is stateless; the whole window travels per call; replies carrying a stale sequence token are dropped.
- **Why:** PD-3 (transient); needs no object, cache or session store; implements R-10 stale-reply rule.
- **Limit:** a call already sent cannot be cancelled server-side (EL-6).

### AD-8 One permission set grants everything the user needs
- **Status:** proposed.
- **Choice:** `Grok_Bot_User` grants tab visibility, app visibility, access to the Apex classes, and the
  credential principal. Assignment is a separate administrator action, never part of the deploy.
- **Why:** R-8 and the platform guidance that visibility is a separate authorized step.
- **Evidence limit:** whether principal access to an External Credential is granted through the permission
  set's external-credential-principal access (per Salesforce docs: principals map to permission sets) is
  taken from docs, not probed (OG-8).

### AD-9 UI direction: SLDS-first with a Gemini-light composition
- **Status:** proposed; concrete tokens finalised at step planning.
- **Reference:** the light Google Gemini look with Material 3 Expressive principles, adapted to the Salesforce
  Lightning identity (platform conventions take precedence).
- **Concrete choices:** SLDS styling hooks for colour, spacing and type (no hard-coded hex beyond token
  fallbacks); tonal rounded message bubbles (user bubble: brand-tinted; assistant: neutral surface), composer
  pinned at the bottom with a confident primary Send action; one subtle accent on the pending indicator;
  SLDS utility icons only; assistant avatar as a utility icon (no xAI/Grok logo); focal point = transcript +
  composer; empty state has three starter prompts; motion limited to message entrance and the pending
  indicator, disabled under `prefers-reduced-motion`.
- **Alternatives:** a third-party chat UI library (not needed; would add a dependency and conflicts with the
  platform's content security rules, unverified); fully custom colours (breaks theme following).
- **Evidence limit:** whether the org offers a dark theme (OG-9).

### AD-10 Test layering
- **Status:** proposed.
- **Choice:** Jest for component logic with Apex mocked; Apex tests in the org with `HttpCalloutMock` for
  controller/service; deployed-tab browser checks for entry, rendering and accessibility; one live xAI call for
  the provider contract. No layer substitutes for another (spec R-15, AC-15.3). Apex tests are remote tests
  (they run the deployed code) and use TAP output.

### AD-11 Separate deploy, credential entry and access grant
- **Status:** proposed.
- **Choice:** order: validate (dry run) → deploy → admin enters key → admin assigns permission set → verify;
  each its own command or person step with its own authorization (spec R-16). A safe read of org state is
  not authority to change it.

### AD-12 API version chosen from the target org
- **Status:** unresolved until OG-2.
- **Choice:** set `sourceApiVersion` to a version verified as supported by the target org (read from the org,
  not copied from a template or this document).

## Superseded

none
