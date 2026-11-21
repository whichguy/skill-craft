# Grok Bot for Salesforce: architecture

Structure and technology decisions only. Product behaviour is in `KNOWLEDGE/spec.md`. Written at the spec stage as
proposals; the plan confirms them against the real org.

## Decisions

- **AD-1 Runtime shape.** A Lightning Web Component (chat UI) calls one imperative, non-cacheable `@AuraEnabled`
  Apex method; Apex makes the xAI callout. Rationale: the API key must never reach the browser (R-6); a browser
  fetch would expose it and need CSP/Trusted-site changes. Alternative rejected: Flow/External Services (no
  bounded-history or error-category control). Serves R-2, R-5, R-6.
- **AD-2 Apex layering.** `GrokBotController` (thin, `with sharing`, input from LWC, returns a structured outcome
  with `ok`, `text`, `category`) → `GrokBotService` (builds request, maps status to category, enforces R-4/R-3
  server-side) with the HTTP send behind a seam that a test can replace with `HttpCalloutMock`. Serves R-3..R-5, R-12.
- **AD-3 xAI endpoint.** Prefer `POST /v1/responses` (documented preferred; Chat Completions is labelled legacy)
  with the full bounded history sent in each request and storage disabled if the API offers it (`store` default
  unconfirmed, G-3), so conversation state stays client-held (A-4, R-10). Fallback: `POST /v1/chat/completions`.
  The plan decides after a probe of the real request/response schema with the key (G-3, G-4). Serves R-2, R-10.
- **AD-4 Credentials.** External Credential (custom protocol, one named principal, API key as an `Authorization`
  header formula) + Named Credential for `https://api.x.ai`; permission set lists the principal. No Remote Site
  Setting expected (PF-8, G-6). No secret in metadata. Serves R-6, R-7.
- **AD-5 Provisional names** (to be cleared against the org inventory, G-5): Apex `GrokBotController`,
  `GrokBotService`, tests `GrokBotServiceTest`, `GrokBotControllerTest`; LWC `grokBotChat`; tab and app
  `Grok_Bot`; permission set `Grok_Bot_User`; custom metadata type `Grok_Bot_Config__mdt` with record `Default`;
  credentials `Grok_xAI` (external) and `Grok_xAI_API` (named). Serves R-1, R-7, R-8, R-11.
- **AD-6 UI approach.** SLDS styling hooks/tokens only, one SLDS utility icon set, no custom colours; Gemini-light
  look expressed as tonal rounded message surfaces and a prominent composer within SLDS; concrete tokens chosen
  in the plan's UI direction. Serves NFR-1.
- **AD-7 Config seam.** Config is read from the custom metadata type via `getInstance`/query inside the service
  through an overridable method so tests inject values (R-8/1). Serves R-8, R-12.

## Conventions and checks (proposed)

- Tests: Apex tests with `HttpCalloutMock`, run in the org with `--result-format tap`; LWC Jest locally.
- Deploy: source-format DX project; `.sf/` and `.sfdx/` git-ignored; separate commands for deploy, permission-set
  assignment, and key entry.
- Real-boundary checks: org metadata read-backs and a browser run in the target org (R-11, R-13); mocks do not
  stand in for them.
