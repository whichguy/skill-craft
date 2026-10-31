# Architecture

## Decisions
AD-1: Extend the existing store and outbox for assignment, keeping audit and notification effects together and asynchronous worker delivery. Preserve version 1 files with absent assignee treated as null. Make each actual assignment notification distinct so pending deduplication cannot suppress later assignments.

## Real-boundary checks
All checks planned locally: node:test exercises HTTP on an ephemeral port, store and outbox, real file persistence and CLI invocation; worker integration exercises notification output. Isolated memory and temporary files prevent retained state between runs. No remote deployment or browser exists in this request. Worker retry and dead-letter paths remain covered by existing tests. No cache or authorization layer is present.

## Structure
CommonJS API routes call validation and TicketStore; store owns ticket, audit and outbox. Add nullable assignee to the existing version 1 ticket record, defaulting missing legacy values to null. The existing worker and notification template own delivery. Query and formatting remain in existing modules. Name additions locally to avoid collisions.

## Conventions and interfaces
Follow CONTRIBUTING.md; standard library only, no external services or deployment. API caller uses request/response; worker asynchronously sends queued events and records failures.

## Stack
Node.js >=22, CommonJS and standard library; no dependencies.

## Interfaces and boundaries
HTTP and CLI use the local store; the worker owns async outbox delivery. Legacy version 1 records without assignee load as null.

## Superseded
None.

## New feature real-boundary checks
Planned local HTTP on ephemeral listener exercises real API, store and outbox. Planned local worker with controlled clock and file notifier validates event rendering and delivery. Temporary data file round-trip validates recovery across service instances. These do not establish hosted delivery; none was requested. No remote service, cache or account is involved.

### AD-2 Reassignment and escalation (implemented)
Extend existing CommonJS store, HTTP routes and worker jobs; reuse name validation, audit, outbox, data file and notifier. Reassignment uses assignment semantics; escalation uses durable event/marker recorded with the enqueue. Alternative independent timers or direct notifications bypass existing recovery. Version 1 data remains readable; DATA_FILE is the sole persistence target, and memory-only operation cannot survive restart. Escalation checks creation time each tick and never changes assignee. Worker runs in one service process; existing file ownership rules remain. No new remote runtime or dependencies.

S2 implementation: retained `ticket.escalated` outbox events in all statuses serve as the per-ticket marker, persisted with the event. The worker job queues before delivery; no schema change. Runtime wiring follows in S3.

S3 wires the escalation job before outbox delivery when ONCALL is configured; the interval controls both.
