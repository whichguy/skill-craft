# Grok Bot for Salesforce — Architecture

How the product is built. What it must do is in `KNOWLEDGE/spec.md`; neither restates the other. Decisions are `AD-<n>`.
Status: all **proposed** by the spec stage; nothing is implemented or verified in an org (no org identified, spec G-1).

## Decisions

### AD-1 Lightning Web Component page + one Apex `@AuraEnabled` entry point (proposed)
- Serves R-1, R-2, R-3, R-10. A single LWC (`grokBotChat`) holds the transient transcript and calls one Apex method
  (`GrokBotController.sendMessage`) imperatively (not wire; not cacheable, since each call is a unique, side-effecting
  request). Apex is `with sharing`, takes message + prior turns and returns a result object carrying either reply text or
  an error category, message and reference id (the contract the spec's R-5 table describes).
- Alternatives: Agentforce/Einstein Bot (PD-1, G-5); Flow with an invocable action (poor chat UX, no transcript control).
- Revalidate if PD-1 changes.

### AD-2 xAI reached via a Named Credential bound to an External Credential (proposed)
- Serves R-6. External Credential (custom protocol, one principal, one secret authentication parameter holding the key)
  plus a Named Credential for host `https://api.x.ai`, adding the `Authorization: Bearer <key>` header through the
  credential's header formula so Apex never sees the key. Apex uses endpoint `callout:<NamedCredentialName>/v1/responses`.
  No Remote Site Setting is needed for a Named Credential callout. Access to the principal is granted by permission set
  (`externalCredentialPrincipalAccess`). Exact header-formula syntax and permission-set element to be confirmed against the
  current Salesforce Named Credentials docs at plan time (primary pages not retrievable from the spec stage).
- Alternatives rejected: key in custom metadata/settings/Apex (R-6 violation); legacy Named Credential with password.

### AD-3 Use xAI `POST /v1/responses` with `store:false` (proposed)
- Serves R-2, R-9. Source: docs.x.ai Responses page (read 2026-11-21): path `/v1/responses`; body `model`, `input`
  (array of `{role, content}`), `instructions`, `store`, `max_output_tokens`; reply text in `output[]` items of
  `type: "message"` → `content[]` of `type: "output_text"` → `text`; Bearer auth. Concatenate `text` of all
  `output_text` parts of `message` items; ignore other item types.
- Fallback: if the live probe shows the Responses endpoint is unavailable for the key, `POST /v1/chat/completions`
  (OpenAI-compatible; labelled legacy by a secondary source, docs pages not retrievable). Switching is an AD change plus
  new parse mapping, not a silent swap.
- Verify with a probe at release-verify (G-2, G-3); until then **unverified against a live key**.

### AD-4 Synchronous callout now; Continuation only if the probe demands it (OPEN)
- Serves R-5, NFR-2. Default: a synchronous Apex callout with the configured timeout (request timeout set from
  configuration, bounded 1–120 s). Risk: Salesforce limits concurrent long-running requests and Grok reasoning replies
  may be slow; the alternative is `@AuraEnabled(continuation=true)` (Continuation, documented 120 s max, 1 MB response
  limit per search summary, unverified for LWC). The plan must probe the target org and record the numbers before this
  closes (spec G-4). Do not pick Continuation without that evidence; its response-size cap interacts with A-4.

### AD-5 Configuration in a custom metadata type (proposed)
- Serves R-8. `Grok_Bot_Config__mdt` with one record `Default` holding model, instruction, max message chars, max
  history pairs, max output tokens, timeout. Read through the type's `getInstance`/query (no SOQL governor cost for
  `getInstance`; verify). Deployable with code, editable by admins without code. Validation in Apex (fail closed).
- Alternative: custom settings (rejected: not metadata-deployable the same way; guide prefers custom metadata).

### AD-6 Transcript is LWC component state only (proposed)
- Serves R-3, R-9, R-10, PD-3. No Salesforce object, no browser storage. A monotonically increasing request token in
  the component discards stale replies after New chat (T-7).

### AD-7 Naming and metadata inventory (proposed; pending G-6)
- Prefix `GrokBot` / `Grok_Bot` to avoid org-wide clashes: Apex `GrokBotController`, `GrokBotService`,
  `GrokBotConfigReader`, `GrokBotControllerTest`; LWC `grokBotChat`; tab `Grok_Bot`; app `Grok_Bot`; permission sets
  `Grok_Bot_User`, `Grok_Bot_Admin`; External Credential `Grok_xAI`; Named Credential `Grok_xAI`; custom metadata
  type `Grok_Bot_Config__mdt`. Consumer entry: tab API name `Grok_Bot`, path `/lightning/n/Grok_Bot`; the component's
  `js-meta.xml` exposes `lightning__Tab` and the `CustomTab` file plus the app and permission-set visibility are
  separate source files (a `lightning__Tab` target alone creates no tab).
- Tool state: `.sf/` and `.sfdx/` in `.gitignore`.

### AD-8 UI structure and visual direction (proposed)
- Serves NFR-4, NFR-5. Template: header (title, New chat), transcript region (live region), composer (textarea,
  counter, Send). Reference: light Google Gemini look with Material 3 Expressive principles, adapted within SLDS:
  tonal rounded message surfaces, one accent, platform sans-serif font stack (no external fonts), `lightning-icon`
  SLDS utility icons only, CSS custom-property tokens with light default and dark variant (mechanism to verify, G-8),
  `prefers-reduced-motion` honored. Concrete token values chosen at plan (`plan-record` UI direction).

### AD-9 Reply rendering as plain text (proposed)
- Serves NFR-6, R-2. Bind text via template expressions with `white-space: pre-wrap`; no `lwc:dom="manual"`, no
  `innerHTML`, no markdown library (also avoids a dependency, NFR-9).

### AD-10 Test architecture (proposed)
- Serves NFR-8. Apex tests with `HttpCalloutMock`/`Test.setMock`; the configuration reader is injectable so tests set
  values; LWC Jest tests mock the Apex import. No test calls xAI. Apex tests are remote tests (run in the org via
  `sf apex run test --class-names GrokBotControllerTest --synchronous --result-format tap`); Jest runs locally.
  Not yet replayed: no project exists.
