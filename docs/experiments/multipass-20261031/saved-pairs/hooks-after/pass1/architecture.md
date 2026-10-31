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
