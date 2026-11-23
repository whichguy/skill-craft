# Architecture

## Decisions
### AD-1 Existing store and outbox
Extend existing route, validation, store, persistence and notification template; preserve synchronous audit and save path. Each actual assignment needs a distinct pending outbox key; no-op and unassignment enqueue none. Read legacy records without assignee as null. This decision follows CONTRIBUTING.md and README.md.
### AD-2 Filter intersection and CLI
Combine supplied filters with AND before cursor pagination. Append raw output column to preserve positional consumers; add table column.

## Real-boundary checks
Planned local HTTP component tests use ephemeral server and in-memory state; local persistence/worker integration tests use isolated files and actual notifier, not a remote target. CLI test uses actual command against a temporary data file. Worker and notifier are the established delivery boundary; remote mail relay is outside the requested local target. No cache or authentication is involved. Re-run full suite on final candidate.

## Structure
AD-1 applies in local Node CommonJS: app route calls validation and TicketStore; persistence owns version 1 ticket records, outbox owns events, templates own wording. Extend existing namespaces rather than adding a service. The assignee is null or a validated string in the existing ticket record; legacy records lacking it read as null. DATA_FILE remains the optional authoritative snapshot; worker retries outbox delivery. API and CLI read the same store. Node HTTP requests are handled by existing synchronous mutations; no additional connection, cache or identity is introduced.

## Conventions
Follow CONTRIBUTING.md: standard library only, errors through envelope, store mutations with audit, outbox and persistence; preserve raw CLI column positions.

## Stack
Node.js 22 or later, CommonJS and standard-library HTTP, filesystem and test runner; no npm dependencies.

## Interfaces and boundaries
API clients use HTTP and JSON; operators use the CLI over DATA_FILE. Store owns ticket mutations, audit, outbox and persistence; worker owns retry and notifier delivery. Remote mail relay is outside local verification.

## Superseded
None.

### Bulk and escalation boundary checks

Planned local checks use real HTTP listener on ephemeral port, in-process worker and file persistence in isolated temp directories. The notifier's in-memory delivery checks its rendered payload; this does not verify a downstream mail relay. The worker's outbox handles retry and reports dead events via existing logs. No remote, browser, cache or authentication boundary is in scope. Tests use fresh state for each run.

### AD-3 Bulk assignment and escalation (implemented)

Extend the existing CommonJS app/validation/store for the bulk endpoint; reuse assignment audit and event semantics, with one synchronous store operation. Add a worker job before outbox delivery and a durable per-ticket escalation marker in the existing version 1 JSON record, defaulting missing legacy markers to null. Atomically persist marker and event together; no extra database, timer or cache. ONCALL and threshold are service configuration; API remains on the existing internal HTTP boundary. Alternative separate scheduler/storage adds unnecessary infrastructure. The service's single-process ownership and optional DATA_FILE remain the existing operating assumptions. Check legacy load, restart, worker and API boundaries in node:test.

### Comment real-boundary checks

Planned local HTTP integration and restart tests exercise real router, store and JSON file; worker/notifier tests observe the rendered message. External mail relay is outside this repository; no deployment was requested. Existing synchronous store operations serialize changes; no cache, new access control or remote reconciliation applies.

### AD-4 Comments within existing ticket state (planned)

Reuse CommonJS src/app.js validation and TicketStore, its audit, version-1 JSON persistence and outbox; add per-ticket comment records, default absent legacy field to empty, and a unique event key per comment with a renderable template. Local Node runtime owns state and synchronous mutations; HTTP is the consumer interface; worker delivers asynchronously and retries. No schema migration operation, external service, cache or new dependency. IDs must avoid reuse after restart. Existing file retention and access remain; no new cleanup policy. Alternative separate store would add coordination without a requirement. Verify restart, legacy fixture, notification and unchanged tests.
