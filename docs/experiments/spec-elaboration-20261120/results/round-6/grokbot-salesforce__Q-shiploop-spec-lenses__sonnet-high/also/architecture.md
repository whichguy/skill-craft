# Grok Bot: architecture

## Decisions

Status of every entry: **proposed** by the spec stage; the plan confirms or revises. Requirements they serve are in
[spec.md](spec.md); no decision here is a product requirement.

### AD-1 Shape: LWC chat tab, Apex controller, one synchronous callout
- Status: proposed. Serves R-1, R-2, R-5, R-11.
- Browser component `grokBotChat` (in tab `Grok_Bot`, app `Grok_Bot_App`) calls an imperative, non-cacheable
  `@AuraEnabled` method on `GrokBotController` (`with sharing`, no SOQL/DML). The controller makes the one callout
  and returns a small result object (`category`, `text`, `correlationId`, `truncated`). Alternatives not chosen:
  Agentforce/Einstein (different product), Flow-only (poor error control), Platform Events or Queueable
  (async adds no value without streaming, A-6).
- Evidence limit: whether a cacheable method may callout was not verified; non-cacheable avoids the question.

### AD-2 xAI endpoint isolation and API choice
- Status: **unresolved** (G-4). Serves R-2, R-7, NFR-10.
- Provider specifics (path, request/response shape, finish reason mapping) live in one class `GrokClient`.
  Preferred route: the one xAI recommends for new work; fallback: OpenAI-compatible Chat Completions (documented as
  legacy). Decision after a live probe with the key. Conversation stays stateless: the caller sends history.

### AD-3 No streaming
- Status: proposed. Apex callouts are synchronous request/response (P-2); streaming would need a different transport.
  Replies appear whole. Revisit only if latency complaints arise (G-8).

### AD-4 Credential: External Credential + Named Credential `Grok_API`
- Status: proposed. Serves R-7. One named principal mapped to permission set `Grok_Bot_User`; the secret is entered
  by an admin after deploy (P-5). Bearer header expression to be confirmed by probe.

### AD-5 Configuration: one custom metadata type
- Status: proposed. Serves R-8. `Grok_Bot_Config__mdt` with record `Default`; read by Apex; deploys with source.
  Invalid config fails closed.

### AD-6 No persistence
- Status: proposed. Serves R-9. Transcript in component memory; per-request log line to the debug log with
  metadata only. A durable log object or transcript store is deliberately omitted (G-6).

### AD-7 UI direction (to be completed at plan)
- Status: proposed. Serves NFR-6, NFR-11. Use SLDS components and styling hooks for platform conventions; light
  default with dark variant; tokens defined once; one icon set (SLDS utility). Concrete palette, type scale and the
  signature element are chosen at plan and recorded here.

### AD-8 Testing split
- Status: proposed. Serves NFR-8. Apex tests with `HttpCalloutMock` (remote tests, run in the org after deploy);
  LWC Jest tests (local); browser check of the deployed tab (needs org access, G-2); Live prompt (needs key, G-1).
