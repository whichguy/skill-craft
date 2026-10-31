# Ticket assignment specification

## Requirements

### R-1 Assignment API and state
Basis: request S2–S6; existing validation, store and state rules in src/app.js, src/tickets/validate.js, src/store.js and src/tickets/states.js. Every ticket, including legacy saved records, exposes `assignee` null until assigned. PUT /tickets/:id/assignee accepts exactly an assignee value: null unassigns, a trimmed nonempty single-line name of at most 64 characters assigns. Invalid, missing, or additional fields produce 400; unknown ticket produces 404. Open and in_progress accept changes; resolved and closed produce 409, including no-op requests. A repeated same assignment or unassignment changes no timestamp, audit, outbox or file. Actual changes are audited and persisted. Confirm by HTTP, store and legacy/restart tests for all states, valid boundaries, errors and no-op. Existing create, update and transition behavior remains.

### R-2 Assignment notification
Basis: S7; src/outbox.js, src/worker.js and src/templates.js. Every actual assignment to a non-null name enqueues a deliverable notification addressed to that agent, including successive changes before earlier delivery; unassignment and no-op do not enqueue. Confirm by outbox and worker delivery tests, including reassignment. The response confirms enqueue, not external relay delivery; existing retries and dead-letter behavior remain.

### R-3 Listing filters
Basis: S8; src/tickets/query.js. GET /tickets with assignee= selects null; nonempty assignee selects matching name; all supplied filters must match simultaneously before pagination. Confirm with HTTP test containing positive and negative combinations, empty filter and pagination. Existing status, priority and cursor validation remain.

### R-4 CLI and compatibility
Basis: S1, S9–S11; README.md, src/format.js. Table listing shows each assignee including unassigned; raw listing includes assignee without moving existing id, status, priority and title columns consumed by weekly report. Existing tests remain unchanged and pass; new node:test cases run under npm test. Confirm CLI execution against persisted legacy and assigned data, weekly report and full test suite. No dependencies; PORT startup unchanged.

## State and boundaries
TicketStore owns serialized ticket changes, audit and pending outbox in optional DATA_FILE; reads remain available to existing API and local CLI consumers. Worker handles retries and NOTIFY_FILE relay or memory. Legacy records load with null assignee, new assignments survive restart; process-only state expires at shutdown without DATA_FILE. Existing service has no new identity, permission or retention system requested; access and retention remain as before. Synchronous store operations order local changes; no new distributed concurrency mechanism is introduced. No cache or revocation service is involved.

## Non-functional requirements
No dependency additions; Node >=22 (package.json). Preserve prior error envelope, raw report column positions and old data file compatibility; confirm with tests. Existing 64-character name bound and single-line format protect CLI output. No additional latency, scale, uptime or confidentiality bound was supplied; preserve existing operational model and avoid inventing one.

## Verification status
R-1 through R-4 passed local item and integrated system tests. The returned source passed the full 122-test suite in a clean copy; rerun it after service or test changes. Notification delivery is verified through the local worker and notifier, not an external relay.

## Retired
None.
