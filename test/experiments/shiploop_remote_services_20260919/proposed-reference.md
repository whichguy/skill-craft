# Proposed service and observability reference

Post-review and observability revision; not evaluated in the paired study. Load
only affected sections. Observability applies proportionately to local and remote
flows; remote-service sections require relevant remote dependence. This is
proposed guidance, not an active ShipLoop instruction.

## Owned observability and existing coverage

Discover existing logs, audit trails, relevant metrics/traces, collection routes
and operational owners for affected apps, runtimes, identity providers and remote
services. For each needed signal, establish purpose, authoritative emitter,
destination, coverage evidence and retrieval/access/retention limits. Reuse
unchanged, then configure, then extend owned instrumentation into existing
systems. Propose a new facility only for an evidenced gap those options cannot
meet. Inaccessible evidence remains unknown with an owner. Do not duplicate
events adequately recorded by their owner or infer upstream events the app cannot
observe. An MCP connection or local log does not prove remote audit coverage.

Ensure successful and failed logins are recorded where authentication is part
of the system. Reuse adequate provider/platform coverage. Distinguish app-owned
session establishment, refresh or authorization outcomes from upstream logins.
Outcome, severity and incident classification are separate; an ordinary failure
is not automatically an incident or alert. Assess operational transitions,
errors, latency, retries and cache/async recovery as relevant; do not introduce
authentication or a telemetry stack into a local stateless change.

Use existing structured conventions and safe correlation across owned boundaries.
Minimize fields, exclude credentials/tokens and sensitive payloads, sanitize
untrusted event text, protect log access and define retention. Confirm required
auth/audit events survive debug settings and sampling. Choose explicit bounded
loss/outage behavior without allowing diagnostic failure to replace the original
outcome, except where a required audit policy specifies otherwise. Retain
investigation/alert ownership; logs do not replace durable work state. Verify
generation and destination retrieval with controlled events, secret exclusion,
duplicate delivery and sink failure as applicable. Link coverage, required
emitter/configuration changes, tests and runbooks to spec and work-item handoff.
Recheck new entrypoints and changed flows; a backend alone does not prove coverage.

## Remote services and state

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
and allowed behavior when freshness or authority cannot be established. Derive
cache isolation keys from trusted canonical tenant/security/query context, not
unverified caller claims. Cache filtered authorized output under that scope, or
enforce complete current row/field/query policy on an internal cache before every
exposure. Bypass or deny if isolation or required current authority is unavailable. A
user-scoped key or TTL alone does not prove safe revocation. Reuse supported
native refresh facilities and assess every affected cache layer.

For cooperating services, choose synchronous return, a durable operation record
with bounded polling, or notification/subscription plus authoritative read-back
according to the requirement. Define acceptance versus commit versus completion,
state/worker ownership, correlation separately from retry identity and resource
revision, duplicate/reordered results, restart recovery, timeout/cancellation,
and reconciliation after unknown outcomes. A notification can be only a hint;
record its actual delivery guarantee and missed-notification recovery. Authorize
operation lookup/status, notification recipients and result reads against the
current tenant/subject policy. Define worker execution under current submitter,
approved delegated snapshot or service authority, and revocation/cancellation
after acceptance. Retain worker least privilege and input/result/error retention
and purge decisions. Do not assume a browser session supplies worker authority. Prevent old
account/session callbacks from updating a replacement context. No event bus is
required when record state and polling meet the need.

Retain a compact decision and evidence in existing design/environment notes.
Link affected requirements, source artifacts, schema/migration files, service
contracts, tests, deployment/configuration files and operational documentation
to ordered work items, using ordinary evidence_refs and work-item context.
Step planning must reopen those exact sections and revalidate changed assumptions.
Use stable relevant headings (capabilities, cache authority, async completion,
remote delta, observability coverage, verification) in the existing note. Verify a cold handoff actually
presents and consumes these locators; opaque reference strings are not enforcement.
Keep material unknowns and their gating stage visible. For local/stateless work,
record remote inapplicability and any sufficient existing observability briefly,
then proceed; do not invent remote or logging prerequisites.
