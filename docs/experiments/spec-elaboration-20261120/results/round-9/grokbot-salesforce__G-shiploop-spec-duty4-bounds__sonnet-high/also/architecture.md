# Grok Bot for Salesforce — Architecture

Proposed decisions for planning; none implemented or probed. Requirements are in `KNOWLEDGE/spec.md` (R-<n>).
Names below are working names; the actual `GrokBot*` names are fixed at plan after listing the org's existing components.

## Decisions

### AD-1 Runtime shape (R-1, R-2, R-11)
A Lightning web component chat panel calls one Apex `@AuraEnabled` operation imperatively; Apex makes a single synchronous HTTP callout to xAI and
returns a DTO `{reply | errorClass, truncated}`. No queue, Continuation or middle tier. Alternative considered: Continuation (async, up to 120 s):
unnecessary for one callout; revisit only if concurrent long-running request limits bite (a documented note says callout time is not counted toward the
5 s long-running threshold; confirm by probe).

### AD-2 xAI endpoint (R-2, R-6, R-8) — unverified (G-4)
Prefer the Responses API (`POST https://api.x.ai/v1/responses`, `store:false`, history passed as input) because the docs mark Chat Completions as legacy;
fall back to `/v1/chat/completions` if a probe shows a gap. Model id held in configuration; default `grok-4.7` as shown in current xAI docs.

### AD-3 Credential custody (R-8, R-9)
An External Credential (custom authentication protocol) holding the API key as a principal parameter, a Named Credential pointing at the xAI base URL
with a custom header `Authorization: Bearer <key>` (formula header; key never in the URL), and the permission set granting External Credential
Principal Access. The key value is entered by the admin in Setup (a secret is not deployable from source). Claim to verify at plan: permission-set
principal access and the "Allow Formulas in HTTP Header" setting.

### AD-4 Configuration (R-10)
A custom metadata type with one default record (model, system instruction, caps, timeout), deployed with the code; Apex validates ranges at use.

### AD-5 State placement (R-3, R-8)
Transcript and context live in the LWC's memory; the Apex operation is stateless and re-validates the supplied history on every call.
No custom object, cache or platform cache. Server-side trimming (R-5) is authoritative.

### AD-6 Access (R-9)
Permission set `GrokBot_User` grants tab, app, Apex class access and credential principal access. The Apex operation also checks the grant
(custom permission or class access) server-side. Sharing/CRUD/FLS not applicable: no records are read. Class declared `with sharing` as a default.

### AD-7 UI (NFR-9)
SLDS-based component with styling hooks, SLDS utility icons, no third-party UI library or fonts; `lightning__Tab` target plus an explicit
`CustomTab` and app (or tab in an existing app) in source, since the target alone creates no tab.

### AD-8 Testing (NFR-8)
Apex tests with `HttpCalloutMock` capturing the request (remote tests, TAP reporter, run in the org); Jest for the component; browser check of the tab;
one optional live probe when the key exists. Apex coverage rule follows the org's effective test level, read at plan.

### AD-9 Logging (R-8, NFR-7)
One structured `System.debug` line per request: outcome class, HTTP status, latency ms, counts. No content, no key.
