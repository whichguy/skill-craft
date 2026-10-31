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
