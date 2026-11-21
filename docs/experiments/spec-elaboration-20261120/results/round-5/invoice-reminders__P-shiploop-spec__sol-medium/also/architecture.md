# Invoice Reminders Architecture

## Decisions

### AD-1 — Resolve the runtime and reuse supported boundaries

**Status.** Unresolved. No product checkout, baseline, runtime, account, route, worker identity, quota or service inventory was supplied. No target capability or permission was observed. The intended delta is unattended reminder processing for an approved invoice scope. Existing configuration, callers, policies and drift require inspection before any change.

**Selection.** Prefer the deployed billing system's existing scheduler, scoped invoice read, durable work/outcome facility, notification route and operator diagnostics where each meets the contract. Selection remains open for scheduling, enumeration, exclusion of concurrent submissions, current authority at execution, provider reconciliation, operator read-back and quota limits. A required capability without a supported existing route is an architecture gap. Provider ownership of acceptance and application ownership of recovery are specified at the product boundary in [R-2](spec.md#r-2--deliver-the-reminder-to-the-authorized-billing-contact) and [R-3](spec.md#r-3--recover-processing-and-show-truthful-outcomes).

**Confirmation.** Runtime owner identifies the actual runtime and account, authoritative artifacts and supported routes, including distinct configuration, worker and operator roles. Record as-of scoped access and read-back with primary documentation or authorized observations. Verify unattended execution, complete enumeration, revocation handling, durable handoff, exclusive submission and response-loss recovery using the selected route. Inspect existing diagnostics for owned outcomes and denied access, and extend the current authorized destination only where coverage is missing. Record actual workload and applicable runtime or provider quota and retention constraints. Revalidate these observations when target, role, policy, provider or version changes. Live activation remains contingent on the affected gaps in [the specification](spec.md).
