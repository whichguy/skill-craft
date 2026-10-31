# Architecture

## Decisions
### AD-1 Assignment integrates with existing store
Reuse validation, Router, TicketStore.apply, outbox, worker, JSON persistence and CLI. Assignment is a store-owned audited change, not a direct notifier call. Every actual assignment needs a distinct outbox key because pending-key deduplication otherwise suppresses reassignment. Default missing legacy assignee to null on read. Append assignee after the existing raw columns.

### AD-2 Bulk and escalation integration
Accepted plan: reuse store assignment semantics and numeric ID sorting for bulk API. Add worker-owned escalation scan; use durable store-owned record plus outbox event in same save, retaining version-1 compatibility. Alternative pending-key deduplication alone fails after delivery. Node CommonJS, local HTTP, optional JSON data file, and notifier remain existing boundaries; no new dependency or remote system. Verify restart, worker and API in node:test.

## Real-boundary checks
Planned local node:test drives the HTTP server, persistent file across restart, notifier/worker, CLI and report. No remote target is named; no deployed claims. Per-test isolated memory, temporary file and ephemeral port provide clean state, and tests should fail on the base when the feature is absent. No cache or authorization boundary exists in the current service. Existing outbox retry tests cover recovery, and a new delivery test observes the configured local notification boundary.

## Stack
Node >=22 CommonJS, built-in HTTP, filesystem and node:test; no dependencies.

## Structure
AD-1: src/app.js dispatches to src/tickets/validate.js and src/store.js; src/tickets/query.js filters, src/persistence.js projects version-1 state, src/templates.js renders worker events, src/format.js renders CLI. Add an assignee field (nullable string, <=64 trimmed single-line characters) to ticket records; missing legacy field becomes null. Existing DATA_FILE owner, retention and atomic replacement remain. No remote environment is in scope. New methods and action names are module-local or named exports and must not collide with existing names.

## Conventions
CONTRIBUTING.md owns store, audit, outbox, error and testing conventions; no dependency is added.

## Interfaces and boundaries
HTTP request/response and read-only CLI remain the entry points; worker asynchronously delivers outbox events to configured notifier. Existing retry and crash recovery apply. Assignment persists with ticket and audit in one save; no new cache, auth or channel.

## Superseded
None.

The assembled suite and local real-boundary checks are due at system-test, owned by the run executor; no hosted target is specified.

## Real-boundary checks

Planned: local Node HTTP service exercises request and response, store audit and outbox; worker tick delivers to local notifier, then a fresh store reads temporary DATA_FILE to verify restart durability. No deployed target or external services required. Local tests do not claim remote delivery.

## Integrated verification due

The assembled local service must pass the full suite at system-test, including real local HTTP and data-file restart; owner: ShipLoop system-test. Escalation uses audit event as lifetime marker and outbox for delivery, both saved in one snapshot; no file schema change. Existing outbox crash/retry semantics and local source return remain the boundary.
