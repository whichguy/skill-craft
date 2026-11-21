# Invoicing product architecture

## Decisions

### AD-1 — Runtime and delivery approach

**Status** — Unresolved. The 2026-11-21 request establishes the product outcome. The standalone stage supplies no observed runtime, billing integration, administrative surface or delivery capability. There is no accepted technology, service or persistence choice.

**Decision scope** — Prefer reuse of existing authorized administration, invoice and communication capabilities if the actual routes can meet the [specification's boundary contracts](spec.md#service-boundary-contracts). Establish the current target, principals, release roles and baseline before selecting or extending an execution mechanism. A developer connector grants no runtime authority.

**Evidence needed** — Identify the actual runtime and version, scheduling and independent execution capabilities, effective authority and revocation behavior, and numerical limits from primary documentation or a scoped probe. Verify how dispatch commitment orders against changes to eligibility, permission, control and destination. Verify supported acceptance read-back or safe same-operation replay across an acknowledgment gap. Identify existing scoped diagnostic coverage and purge behavior before selecting its reuse or extension. Confirm state durability and deduplication across interruption, concurrent work and release rollback. The logic and consumer outcomes remain in [spec.md](spec.md).

**Revalidation** — Reopen this decision when the baseline, channel, authority, runtime, release path or workload becomes known or changes. If the actual routes cannot meet a contract, record the observed limitation and reconcile the dependent specification before enabling affected dispatch.
