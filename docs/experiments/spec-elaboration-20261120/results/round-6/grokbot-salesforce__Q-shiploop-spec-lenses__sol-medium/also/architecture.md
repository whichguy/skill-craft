# Grok Bot for Salesforce Architecture

## Decisions

### AD-1 — Salesforce-native entry and server boundary

Use the existing Lightning Experience shell with a Lightning Web Component exposed through a Salesforce custom tab and an authorized app navigation item, linked with supported navigation. Choose the app and API names after checking the actual org. The component’s tab exposure makes it eligible; the tab metadata and effective visibility are separate. Use imperative Apex for the protected, non-cacheable invocation. The server enforces bot-specific permission and current configuration independently of entry visibility. No separate web host or CRM data adapter is needed. Applies to R-1 through R-4. Sources SF-1 through SF-4 in [spec.md](spec.md#sources).

**Pending confirmation.** Select the supported Salesforce API version, exact org/app, metadata names and grant route. Verify the runtime access and fresh return check on the actual role and execution path. Use one bounded outbound call per inference request. Confirm that the server execution path can observe effective enablement, configuration and permission changes before releasing a result, including off/on during an in-flight call; revise the architecture through the existing correction route if that cannot be observed without changing the accepted contract.

### AD-2 — Server-side xAI Responses API and protected credential

Use a Salesforce Named Credential backed by an External Credential for outbound TLS, with a scoped named principal and protected xAI inference key supplied by the operator. Map principal access to the intended permission scope. Put the Bearer header at the credential boundary through custom authentication, without embedding values in metadata, application source or UI. Use the xAI inference host selected for the approved account and `POST /v1/responses`. Submit the approved model ID, ordered role/text input, `store: false`, non-streaming mode and the approved output token budget. Send no tools or previous-response identifier. Extract only assistant message output text from a valid completed result; handle explicit refusal and other results under R-2.b. The route uses the provider’s current integration contract and keeps protected credentials and remote payload construction off the client. Sources SF-5 and XA-1 through XA-4 in [spec.md](spec.md#sources).

**Pending confirmation.** Provider owner provisions a permitted development key, model entitlement, endpoint, budget and retention policy. Salesforce operator confirms principal/credential provisioning and callout access on the selected org. The developer verifies the actual request and response shape, permitted model and effective limits without exposing credentials. Reusable response storage is separate from provider audit retention.

### AD-3 — Transient client context and correlated delivery

Keep completed role/text pairs, draft and current attempt in component memory. Take a bounded snapshot for each accepted request; commit replies by active view/attempt identity. Reset changes the view identity. Keep customer records, browser persistence, shared transcript stores, provider response chaining and durable jobs out of the design. Use the org’s existing restricted diagnostic capabilities if they can expose the safe fields and events in R-4.c. This supports R-2 through R-4 without defining a new durable state service.

**Pending confirmation.** Verify component lifecycle on the actual navigation route, input and serialized resource bounds and the authorized diagnostic facility. Confirm effectiveness of scoped revocation for fresh server operations and the controlled supersession case. Revisit only affected decisions on new evidence.
