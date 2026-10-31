# Service requirements

## Requirements

### R-1 Assignment API
Basis: request S2–S5; existing API conventions docs/api.md and src/tickets/validate.js. PUT /tickets/:id/assignee accepts exactly assignee, a trimmed nonempty single-line string of at most 64 characters or null. Open and in_progress tickets accept the change; resolved and closed return 409, unknown ticket 404, malformed or unknown fields 400. A successful change returns the ticket, updates its timestamp and records actor and before/after in the audit. An identical assignment or unassignment on an active ticket leaves state, audit and outbox unchanged. Confirm by HTTP tests covering both active and inactive states, names and invalid bodies, unknown IDs and audit/no-op effects.

Observed: PUT route and request validation are exercised by HTTP regression tests. (W1/S2)

### R-2 Ticket state and persistence
Basis: request S6 and S10; README.md and src/persistence.js. New tickets and existing version-1 records missing the field expose assignee null; changed assignments survive persistence and restart and all read surfaces expose the field. Existing state, history, outbox and identifiers remain intact. Confirm by create/get/list and legacy and restart tests. TicketStore owns state, serialized in optional DATA_FILE; existing service access and retention are unchanged. No new identity, authorization or cache is introduced. Writes are synchronous in the single process; existing data-file recovery behavior applies.

Observed: src/store.js and src/persistence.js initialize and reload the nullable field; store regression tests covers legacy records. (W1/S1)

### R-3 Assignment notification
Basis: request S7 and CONTRIBUTING.md. Each actual assignment to a non-null agent enqueues a notification to that agent, including when a prior assignment is still pending; unassignment and no-op enqueue none. Existing worker renders and delivers it with established retries and dead-event behavior. Confirm pending events, distinct reassignments and worker delivery in tests. Existing outbox is the completion and recovery boundary, and notification sink and retention remain unchanged.

Observed: store regression tests exercises distinct pending assignments through the existing worker and notifier. (W1/S1)

### R-4 Filter intersection
Basis: request S8; docs/api.md promises intersection while src/tickets/query.js currently uses OR. GET /tickets accepts assignee=name and assignee= for unassigned; combines all given filters by AND, including status and priority, with existing pagination and validation unchanged. Confirm HTTP tests with matching and nonmatching combinations, empty value and cursors.

Observed: filter regression tests exercises the HTTP filter intersection and cursor pages, including an empty assignee. (W1/S3)

### R-5 CLI listing
Basis: request S9 and README.md. CLI list shows every ticket's assignee, including unassigned. Raw output preserves existing id, status, priority, title positions and appends assignee so the weekly report continues working. Confirm CLI and report tests with assigned and unassigned persisted tickets.

Observed: CLI regression tests verifies table and raw output and runs the weekly report. (W1/S4)

### R-6 Existing behavior and tests
Basis: request S1, S10–S11. Preserve existing API, CLI and no-dependency Node service; add node:test coverage under test and run all original tests unchanged with npm test. Confirm by npm test and review of the diff.

## Non-functional requirements
Node >=22 and no dependencies are binding (package.json, CONTRIBUTING.md). Existing body limit, error envelope, atomic file replacement, logging and worker retry semantics remain. Confirmation: existing suite plus focused tests. No new latency, scaling, authentication or retention bounds were requested; existing local service behavior remains. No hosted target was identified.

## Retired
None.
