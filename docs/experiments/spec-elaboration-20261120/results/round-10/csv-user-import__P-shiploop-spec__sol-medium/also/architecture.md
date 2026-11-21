# User Administration Architecture

## Decisions

### AD-1 — Use the authoritative user-creation boundary

**Status:** Proposed boundary. The route and mechanism are unresolved. See [authorization](spec.md#r-1--restrict-imports-to-authorized-admins) and [batch creation](spec.md#r-3--create-the-batch-without-modifying-existing-users).

Prefer the ordinary user-creation authority for validation, scope, uniqueness and account defaults. The admin UI sends a request and receives an outcome. The selected write mechanism must be able to enforce the accepted batch policy across the ordinary creation path and concurrent writers. A client-side loop of individual creates cannot meet the proposed atomic contract. Treat any separate onboarding provider as an unresolved boundary until its effects, authority and ability to cooperate are established.

No runtime target, effective service identity, accepted prior contract, local implementation or remote state has been supplied. The directory and identity owners must identify the actual route, role and supported commit/revocation ordering, and confirm any companion writes or external effects against primary documentation or an isolated authorized probe. Confirm exact read-back through ordinary user management. These findings gate the write design. Revalidate on a change to the identity or directory contract.

### AD-2 — Scope temporary upload handling and result recovery

**Status:** Proposed placement. The storage, request lifetime and recovery mechanism are unresolved. See [upload](spec.md#r-2--accept-a-csv-and-explain-validation-failures) and [completion](spec.md#r-4--report-completion-and-recover-an-interrupted-attempt).

Prefer request/response submission and an explicit result lookup. Use a browser-context facility only for the selection before submission and for a minimal reference that survives refresh in the same context. Use bounded transient runtime input handling and minimal authoritative attempt metadata. Evaluate keeping the terminal outcome within the same consistency boundary as the user writes. Verify recovery after commit with a lost reply, pre-commit failure, restart, stale response, and expiry. A separate worker or durable input store would require a demonstrated need and a reviewed change in recovery behavior.

Before choosing facilities, the runtime owner verifies the target request limits, timeout and connection semantics, transient data cleanup, refresh behavior and authoritative commit/status guarantees. The product and privacy owners establish the attempt validity, purge and quota requirements. Check actual expiry enforcement and cleanup. The design remains dependent on AD-1 for the real consistency boundary.

### AD-3 — Reuse an authorized operational destination

**Status:** Proposed reuse. The facility and required coverage are unresolved. See [import operations](spec.md#r-5--protect-import-data-and-record-safe-operational-outcomes).

Keep ordinary identity events with their current owner. Use the existing authorized destination if it can provide the distinct import outcomes with safe correlation, access and retention. Extend only missing import coverage. Operations must identify the real emitter, sink, access route and applicable audit rules before selecting the integration. Check safe retrieval, redaction and sink failure against the actual route. Revalidate on changes to authority, audit policy or event destination.

### AD-4 — Extend the host admin design system

**Status:** Proposed reuse. Host surface and toolkit are unresolved. See [visual starting point](spec.md#non-functional-requirements).

Use the host's admin entry points, primitives and tokens where available. Before choosing the concrete composition, compare the host file chooser, inline errors and status components with the required states, keyboard path, long-content layout and theme support. Extend an existing component where it can supply the missing behavior. A new dependency requires a verified host gap and compatibility evidence. Review the rendered screen in both themes and supported viewport ranges.
