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

### R-5 Bulk reassignment
Basis: current request S1–S3; R-1 and R-2 remain unchanged. POST /tickets/reassign validates exactly `from` and `to` as distinct trimmed agent names with existing name constraints; malformed, absent, null, equal or extra fields return 400 without changes. It moves every open or in_progress ticket assigned to from, returning 200 with moved count and ids in numeric ticket ID order, including empty result. Each move has the same audit, timestamp, persistence and notification behavior as single assignment. Confirm with HTTP, store and outbox tests including excluded statuses and invalid inputs.

### R-6 Urgent escalation
Basis: current request S4–S5. Worker scans open, unassigned, urgent tickets whose creation time is strictly older than ESCALATE_AFTER_MINUTES (default 60); no ONCALL means no escalation. Enqueue a notification to ONCALL saying escalated, and record the escalation durably together with its event; each ticket escalates at most once over its lifetime including restart, regardless of later state changes. Existing delivery retries apply. Legacy saved records remain valid; durability requires DATA_FILE. Confirm by deterministic clock and worker tests at the age boundary, eligible and ineligible states, missing on-call, repeat ticks, notification rendering and data-file restart. Worker interval zero disables scheduled work. Age is interpreted as time since ticket creation; implementation and local checks are complete.

## State and boundaries
TicketStore owns serialized ticket changes, audit and pending outbox in optional DATA_FILE; reads remain available to existing API and local CLI consumers. Worker handles retries and NOTIFY_FILE relay or memory. Legacy records load with null assignee, new assignments survive restart; process-only state expires at shutdown without DATA_FILE. Existing service has no new identity, permission or retention system requested; access and retention remain as before. Synchronous store operations order local changes; no new distributed concurrency mechanism is introduced. No cache or revocation service is involved.

## Non-functional requirements
No dependency additions; Node >=22 (package.json). Preserve prior error envelope, raw report column positions and old data file compatibility; confirm with tests. Existing 64-character name bound and single-line format protect CLI output. No additional latency, scale, uptime or confidentiality bound was supplied; preserve existing operational model and avoid inventing one.

## Verification status
R-1 through R-4 passed local item and integrated system tests. The returned source passed the full 122-test suite in a clean copy; rerun it after service or test changes. Notification delivery is verified through the local worker and notifier, not an external relay.

## Retired
None.

## Reassignment and escalation verification
R-5 and R-6 passed item checks on the local candidate: HTTP validation and assignment effects, strict eligibility, worker delivery, legacy load, and restart after sent notification and later state changes. The full 126-test suite, including the system case, passed on a clean copy of the returned tree. DATA_FILE is required for durability; no remote relay was observed.
