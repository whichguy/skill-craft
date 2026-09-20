# Service discovery

Use this conditional guide when a requested behavior depends on another system's
data, metadata, configuration, authority, or independently executing work. An
MCP can be a route to that system; its name or tool inventory does not prove a
runtime dependency, connection, identity, or authority. Use the existing
[platform discovery](platform-discovery.md#discover-before-choosing-a-mechanism)
and [behavior model](behavioral-requirements.md#actors-channels-and-state-ownership)
for their applicable questions. Do not create a service, cache, broker, logging
backend, or remote prerequisite merely to complete this guide.

## Select scope

Start from the requested user or business outcome. Trace the affected flow from
its caller through services, state owners, and observable result. Identify the
authoritative data and business-rule owner, current native/shared capabilities,
and any actual remote boundary. Distinguish a development/provisioning MCP from
the product's runtime caller, adapter, and identity; they may be unrelated.

Classify each applicable need as **reuse**, **configure**, **extend**, **new
justified component**, **unresolved**, or **not applicable**. A local or
stateless change stays local when no consequential boundary exists. Still assess
owned observability when the affected flow includes authentication, security, or
an operationally consequential outcome; a small formatter does not acquire
telemetry because this guide exists.

Select only the cache, query, schema, asynchronous, and observability questions
that can change the requested design. This is not a one-size-fits-all
middle-tier blueprint.

For incremental work, reconcile four inputs before proposing a change:

1. prior accepted intent and constraints;
2. current local definitions, callers, and tests;
3. current observed remote state; and
4. the requested delta.

Record differences as intended change, remote drift, local drift, or unknown.
Preserve unrelated remote fields, configuration, automation, consumers, and
data. A permission-denied read is not evidence that an object or record is
absent. Recheck volatile schema, permissions, and dependencies before an
authorized change; source files must not blindly overwrite remote drift.
Before applying a selected delta, plan the compatible schema/configuration and
consumer order, any required backfill/cutover and rollback or repair path. Bind
the write to the revalidated target/revision where supported; retain final status
and read-back, including partial or unknown outcomes, before dependent work.

## Remote capabilities and state

For every selected remote operation, retain a compact map: required behavior →
observed supported route (MCP, API, CLI, SDK, or browser) → remote artifact →
effective identity and required authority → completion and read-back evidence.
Separate metadata/schema work, configuration, and record CRUD. Also map the
runtime path separately: caller → business operation → adapter/query facade →
source of truth. A tool available to a developer does not establish runtime
permission or a product interface.

For a selected read route, establish needed filtering, joins, pagination, source
availability, quotas, latency, and retention only when they affect the choice of
direct access, an existing query facade, cache, or projection.

Scoped, authorized, read-only remote inspection is valid discovery when it can
settle a named uncertainty about current schema, configuration, access, or
state. Establish the target and effective role first; retrieve only what is
needed; retain a sanitized operation/source, as-of time, coverage, and limit in
the decision note. Do not copy secrets or unnecessary business records into
durable context. A safe read does not authorize a write, deployment, test data,
or persistent connector installation. If inspection cannot answer a material
question, define a bounded experiment with its allowed effects, target,
identity, expected observation, cleanup, and decision consequence as described
by [research experiments](research-loop.md#run-bounded-discriminating-experiments).

## Cache and authorization

Make “zero copy” precise: it can mean no application database, no durable
secondary copy, or no secondary retention at all. Record fields/results kept,
where, lifetime, and policy. A direct query proxy need not retain results;
transient caching is compatible with some zero-copy constraints and incompatible
with others. Prefer direct/native access, then an existing facade, then a cache
or projection only when measured benefit and the full correctness contract
justify it.

For each cache, specify data freshness and authorization freshness separately.
Define maximum age, read-after-write behavior, outage behavior, and whether
current authorization is required at response time. A user-specific key or TTL
does not by itself make revocation safe. Build partitions from trusted,
server-derived tenant/principal and relevant query, row, field, purpose, locale,
and schema context; never caller-asserted entitlements. Cache an already filtered
representation under that scope, or reapply complete current policy enforcement
before every exposure. Do not expose protected information through cached errors,
counts, or existence signals.

List invalidation or revalidation sources: create/update/delete, membership and
aggregate changes, schema/derived-result changes, sharing or policy changes, and
logout/account switch. Cover a slow pre-invalidation fill that completes late,
plus lost, delayed, duplicate, or reordered events and disconnected consumers.
Use a supported generation/revision rule, resynchronization/rebuild, bypass, or
denial policy; do not promise stronger consistency than the authorization source
can establish. When trust in current authorization or isolation is missing,
bypass the cache or deny the result according to the selected requirement.
A bypass must route through a source or adapter that enforces current row, field,
and query policy; reading a privileged source directly is not a safe bypass.
Specify retention/purge independently from permission to serve. Apply the
[state](coding-practices.md#state) and [security](coding-practices.md#security)
cards when implementation follows.

## Asynchronous cooperation

Choose the simplest sufficient contract: synchronous completion, an existing
durable operation record read through polling, or a notification that prompts an
authoritative read-back. Polling is sufficient when its latency, load, and quota
fit. A notification or accepted request is not proof of business completion, and
the UI cannot be the only owner of work promised after it closes.

Define when acceptance becomes durable; the worker/dispatcher authority and
abandoned-work recovery; allowed states and terminal result; and how final status
is committed and read back. Reuse transactions, conditional updates, and
recovery scans that meet the contract. Do not introduce a broker or outbox
without a demonstrated dispatch/recovery gap.

Keep operation, correlation, idempotency, resource revision, and replay
identities distinct where relevant. State duplicate, stale/out-of-order,
unknown-outcome, retry, cancellation, deadline, and worker-crash behavior. For
consequential execution, choose current submitter authority, a permitted
delegated snapshot, or service authority; do not assume a worker inherits a
browser session. Specify the effect of revocation or cancellation after
acceptance on queued and running work, final writes, and result visibility.
Where supported, guard the final write atomically with a conditional revision,
fencing token, or equivalent mechanism so a reclaimed or stale worker cannot
overwrite a newer terminal result; an earlier lease check alone is insufficient. Otherwise
define and test the actual reconciliation rule. Do not promise exactly-once.
Authorize operation lookup, status/progress, result access, and notification
recipients separately. Retain and purge operation inputs, errors, and results
deliberately. Apply the existing
[event and state agreement](behavioral-requirements.md#incoming-events-connections-and-state-agreement)
guidance to the selected boundary.

## Observability coverage

Map relevant local and remote/MCP-adjacent events before adding instrumentation:
event purpose, authoritative emitter, responsible operator, existing logger,
audit trail, metric/trace facility, collector/destination, retrieval access,
retention, and delivery limits. Reuse in this order: unchanged coverage,
configuration of existing coverage, extension of owned instrumentation into its
current destination, then a new facility only for a demonstrated unmet need. An
inaccessible log is an evidence gap, not proof that logging is absent.

Where authentication is part of the system, cover successful and failed login
attempts. Reuse adequate identity-provider or platform events, and add only
distinct application-owned outcomes such as session creation rejection,
authorization denial, refresh, logout, or revocation where applicable. A failed
login is an authentication outcome, not automatically a security incident or a
page. Do not re-emit a provider's authoritative event, reproduce authentication
internals the application cannot observe, or add duplicate storage without a
need.

For owned gaps, select useful operation outcomes, failures, timing, retries,
cache invalidation/recovery, and background-work transitions. Use safe
correlation identifiers across boundaries while keeping logs distinct from
durable work state. Protect logs with minimum necessary data, access control, and
retention/purge rules; omit passwords, tokens, session credentials, and raw
sensitive payloads, and sanitize untrusted fields. Required audit events must
not disappear under debug controls or sampling. Treat sink failure and any
fail-closed audit rule as explicit behavior, preserving the original business
error where diagnostic failure is ordinary. Follow
[logging and debugging](coding-practices.md#logging-and-debugging) for safe
implementation detail.

## Development handoff

Keep one concise, maintained decision in an existing architecture, design, or
environment note. Its current, authoritative sections should state status
(accepted, unresolved, superseded, or not applicable), target/role observations,
the four-way delta, selected capability and runtime maps, data/cache and async
contracts, observability coverage/reuse decision, evidence limits, file roles,
ordered prerequisites, checks, and revalidation triggers. Link that note from
the repository knowledge index at `REPO/SHIPLOOP.md`, preserving existing
project-document links and structure. Do not impose a filename or duplicate a
project's documentation.

At planning and operations, reopen the index and the exact current sections,
not a remembered chat transcript or arbitrary whole documents. Retain their
locators in the accepted result's existing `evidence_refs`; where an INNER work
item needs them, put a compact locator and decision/revalidation summary in that
item's existing `context`. The Navigator transports these host-authored
locators; it does not read, enforce, or replay all referenced decisions. No new
result field, runtime projection, ledger, or stage is required.

Discovery/research establishes observed facts and decisions; specification makes
freshness, authorization, completion, retention, and observability criteria
testable; test strategy identifies local/remote surfaces, identities, fixtures,
setup, teardown, and suite membership. The plan orders metadata/configuration,
service/adapter, cache/worker, UI, observability, test, and delivery work only
when justified. Step planning reopens and revalidates its exact sections before
edits. Operations and handoff retain current log/audit retrieval and recovery
locators, observation dates, and unresolved limitations.

## Verification

For this guide's maintenance, verify package-relative links after relocation.
For a product change, choose checks that prove the selected contract rather than
keyword presence. Test the actual selected remote route and identity where
authorized; local mocks do not prove remote schema, permissions, cache safety,
or delivery. Retain blocked access as a prerequisite and use synthetic or
isolated fixtures where that is the only authorized surface.

Exercise relevant decisions: an incremental metadata/state read preserves
unrelated remote changes; direct reads remain available when a cache is unsafe;
cache hit/miss/write/expiry/outage, permission revocation without a data edit,
delayed fill, and invalidation-event gaps follow the contract; durable polling
remains correct without notification; worker crash, duplicate/stale completion,
and unauthorized status/result access are handled; and observability reuses
provider login coverage while testing any distinct owned success/failure event,
safe destination retrieval, redaction, required-event filtering, and sink
failure. Record the command, target/scope, observation, and limitation. A
passing documentation or synthetic test is evidence of that surface only.
