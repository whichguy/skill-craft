# Grok Bot architecture

## Decisions

### AD-1 — Lightning Experience entry and Salesforce server boundary

Use a Lightning Web Component exposed as a `lightning__Tab` target, a matching CustomTab and a Lightning app with that navigation item. Candidate app and tab API names are `Grok_Bot` (in their distinct metadata types) and the component bundle name is `grokBot`. Use the App Launcher and navigation labels **Grok Bot** for the acceptance route. Confirm names against the target before committing them. A dedicated permission set and assignment control feature visibility, Apex access and use of the external credential principal. Require the bot’s custom permission on each invocation via Salesforce’s current-user permission check, independent of class access and the credential principal’s own gate. Invocation is imperative, non-cacheable Apex, with a single request/response per admitted Send. Keep ephemeral UI state within the rendered view and use the Salesforce-authorized execution context. Separate deployment, visibility/assignment and credential configuration during release. A dedicated tab provides a short internal path and does not place the composer in a record context or require a separate host. Confirm platform versions, actual browser route, deployment identity and grants in the target. [R-1](spec.md#r-1--open-the-bot-in-the-development-org), [R-4](spec.md#r-4--enforce-access-and-protect-credentials), [S1–S3](spec.md#source-references).

### AD-2 — Stateless Grok invocation and managed credential

Use a Salesforce Named Credential with fixed origin `https://api.x.ai` and a linked External Credential using Custom authentication with a restricted named principal. Populate its API key through approved Salesforce setup and supply `Authorization: Bearer <managed key>` as a configured header. Disable the generated authorization header when using this custom header. Validate the required principal and secure backing access in the target. Keep the configured value out of source metadata, the client, tests and logs. Use one server-side TLS `POST /v1/responses` with JSON and these fixed settings:

| Field | Value |
| --- | --- |
| `model` | `grok-4.3` |
| `reasoning.effort` | `none` |
| `input` | Exact admitted R-3 text as a string |
| `store`, `stream`, `background` | `false` |
| `max_output_tokens` | `512` |

Omit tools, identity metadata, history and prior response IDs. Configure the Apex wait parameter at 30,000 ms, within the documented range. R-2’s independent browser deadline governs which completion may display because the Apex timeout parameter alone does not establish an end-to-end deadline. Validate HTTP 200, response object, reported model, final `completed` status and at least one nonblank assistant message `output_text` part in the documented output envelope. Use the parts in order as returned, joining successive parts with a newline. An explicit refusal or incomplete result takes precedence over any partial text. Discard other output and strip raw envelopes on return to the client. Map other results per R-2 and check confirmed provider-specific codes before relying on them. Confirm the actual selected model and schema in a funded team before activation. An unavailable model requires an explicit decision revision. Responses is the provider-recommended current text API, and the selected text-capable model supports a no-reasoning setting suitable for this foreground default. No intermediary service or separate data store is needed. [R-2](spec.md#r-2--get-a-grok-answer), [R-5](spec.md#r-5--keep-each-exchange-private-and-temporary), [S2–S3 and X1–X4](spec.md#source-references).

### AD-3 — Theme inside the bot surface

Use Salesforce Lightning Design System conventions and a single Salesforce icon family. Start from light Google Gemini’s Material 3 Expressive treatment for the bot content area, with light as the initial mode and a component-scoped dark palette. Reuse Lightning primitives where their supported styles satisfy both appearances. Scope any tailored controls and tokens to the bot. Avoid depending on internal base-component markup or SLDS 1-only hooks on an SLDS 2 host. No second UI toolkit is needed for the simple composer, exchange and status controls. The plan selects the concrete hierarchy, palette, type and spacing tokens, and checks them in the target theme and both bot appearances. [R-6](spec.md#r-6--use-a-polished-accessible-chat-surface), [U1–U2](spec.md#source-references).
