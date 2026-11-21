# Invoice Reminders Architecture

## Decisions

### AD-1 — Runtime and service integration

**Status** — Unresolved. The standalone spec has no selected platform, baseline or authorized target/runtime identity. See [requirements and service contracts](spec.md#requirements).

Use the billing authority for invoice data and current access decisions. Evaluate reuse of its unattended execution, durable operation state, permitted mail and scoped operational evidence in that order of need. Select extensions only where an existing capability cannot meet the required contract. An independent service is a candidate only if the target's facilities cannot supply the needed unattended operation, recovery or isolation. Runtime, store, transport and provider selection depend on target evidence.

| Contract needed | Observation before selecting an integration |
| --- | --- |
| Unattended timing and recovery | Verify clock/timezone, launch/restart behavior, execution limits and sustainable evaluation/read rate on the real target. |
| Billing authority | Map stable account and invoice identities, invoice state and recipient fields, authorized current read, permission revocation and existing reminder/configuration ownership. Preserve unrelated billing and configuration state during incremental change. |
| Durable attempt ownership | Verify recovery across process restart and safe conditional ownership/concurrent writes at the scope used by the deployed runtime. Confirm capacity, deletion and retention in the target store. |
| Mail and operational evidence | Verify effective sender and route, result meanings and correlation, possible authoritative reconciliation, quotas, minimum permitted content and approved retention. Identify the existing diagnostic destination and retrieval permission, and extend owned event coverage only where existing evidence is insufficient. |

When target access becomes available, record the route, target, scoped principal, primary documentation or bounded probe result and applicable limits. Revisit this decision when billing identity, schedule ownership, deployment target, sender or provider semantics change. See [service discovery guidance](GUIDES/service-discovery.md#development-handoff).
