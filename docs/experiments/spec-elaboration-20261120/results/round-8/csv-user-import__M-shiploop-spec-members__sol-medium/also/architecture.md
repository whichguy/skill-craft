# User Administration Architecture

## Decisions

### AD-1 — Reuse the ordinary user authority

**Status — proposed, with unresolved integration prerequisites.** Use the product's ordinary authorization and user-creation authorities for import once located. Keep the import interaction in the existing Users administrative interface if it supports the requirements. A parallel identity store or independent set of creation rules would let permissions, uniqueness and default account states diverge between ordinary creates and imports. No framework, storage engine, transport or background processing model has been selected.

**Basis and evidence limits.** The 2026-11-21 request asks for a new way to create ordinary users. This workspace has no baseline, runtime, local definitions, callers, deployed service observations or authenticated target. Their behavior and drift are unknown. The functional change, unchanged state, access rules, completion and recovery contract, and owned diagnostics are specified in [Requirements](spec.md#requirements) and [Service boundary contracts](spec.md#service-boundary-contracts).

**Capability and placement checks.** Product and runtime owners must verify the real administration entry, effective roles and target scope, ordinary create authority, identity reservations, revocation ordering, commit visibility, side effects, and same-attempt reconciliation before choosing a structure for dependent work. Use the existing audit destination when authorized evidence shows adequate coverage. Runtime owners must map transient inputs, recoverable attempt state and cleanup to supported facilities and quotas. If a required ordinary effect crosses a boundary, verify joint commit or escalate the all-or-none decision for correction. The UI owner must inspect the actual design system and platform before selecting components or appearance. Revalidate against the target whenever role, user schema, side effects, audit policy, runtime quotas or recovery semantics change.

**Document roles.** [The product specification](spec.md) owns behavior and acceptance. This decision owns the proposed integration approach. There is no runtime inventory or repository index in the standalone stage. The [service discovery handoff guide](../GUIDES/service-discovery.md#development-handoff) and [its verification guidance](../GUIDES/service-discovery.md#verification) supply the decision and evidence discipline.
