# Conditional remote-service discovery

When an affected outcome depends on externally owned data, schema, or work,
trace its required capabilities through the business service to the actual
state owner. Separate the tools used to inspect/provision the system (including
MCP) from the interface and identity used by the running application. For each
required operation, map the caller, remote artifact, observed tool/API and
version, effective authority, completion evidence, and missing capability.
Tool discovery or successful data queries do not prove metadata-write support.
Prefer existing native facilities; a proxy, cache, broker, or new schema is a
decision to justify, not a component to manufacture.

Use scoped authorized reads to compare intended changes with actual remote
metadata, configuration and relevant state. Distinguish absent from inaccessible
or partially observed. Compare prior accepted intent, current local definition,
current remote observation, and requested delta. Preserve unrelated changes;
retain drift, dependencies, migration order, compatibility, reconciliation and
read-back checks. Recheck volatile preconditions before the later authorized
write. Discovery reads do not authorize schema changes or production fixtures.

For relevant reads, compare direct/federated access, an existing query facade,
optional bounded caching, and a copied projection against actual query support,
latency, load/quotas, freshness, availability, security and operating cost.
Define what “zero copy” forbids: durable replication, or all secondary retention.
Caching retains another copy; record location, scope and lifetime explicitly.
Separate data-freshness tolerance from authorization-revocation tolerance.
For each selected cache, identify source of truth and owner; query/tenant/user
and other effective security context; authorization on hits; data, schema and
permission-change invalidation; commit ordering and read-after-write; missed,
duplicate and reordered invalidations; stale-fill races; recovery after loss;
and allowed behavior when freshness or authority cannot be established. A
user-scoped key or TTL alone does not prove safe revocation. Reuse supported
native refresh facilities and assess every affected cache layer.

For cooperating services, choose synchronous return, a durable operation record
with bounded polling, or notification/subscription plus authoritative read-back
according to the requirement. Define acceptance versus commit versus completion,
state/worker ownership, correlation separately from retry identity and resource
revision, duplicate/reordered results, restart recovery, timeout/cancellation,
and reconciliation after unknown outcomes. A notification can be only a hint;
record its actual delivery guarantee and missed-notification recovery. Authorize
both notification recipients and result reads using current context; prevent old
account/session callbacks from updating a replacement context. No event bus is
required when record state and polling meet the need.

Retain a compact decision and evidence in existing design/environment notes.
Link affected requirements, source artifacts, schema/migration files, service
contracts, tests, deployment/configuration files and operational documentation
to ordered work items, using ordinary evidence_refs and work-item context.
Step planning must reopen those exact sections and revalidate changed assumptions.
Keep material unknowns and their gating stage visible. For local/stateless work,
record inapplicability briefly and proceed; do not invent remote prerequisites.
