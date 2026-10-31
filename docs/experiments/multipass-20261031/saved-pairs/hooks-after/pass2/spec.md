# Ticket assignment specification

## Requirements

### R-1 Assignment endpoint
Basis: request S2–S5; existing API contracts docs/api.md and CONTRIBUTING.md. Implemented and verified by the local assignment suite; system checks remain. PUT /tickets/:id/assignee accepts exactly assignee, null or a trimmed non-empty single-line name up to 64 characters. On open or in_progress, return 200 with the changed ticket; on resolved or closed, return 409; missing ticket 404; malformed input 400. Repeat of the existing assignee leaves ticket, updated timestamp, audit and outbox unchanged. Confirm by HTTP and store tests for boundaries, status, missing and no-op. Store owns state; serialized synchronous changes update audit and persistence together.

### R-2 Ticket representations and persistence
Basis: S6, S10; src/persistence.js. Implemented and verified by the local assignment suite; system checks remain. Created, read, listed and changed tickets include assignee null when unassigned or its assigned name. Existing version 1 files missing field load as null; assigned values survive restart; invalid saved values are rejected. Confirm API and file round-trip/legacy tests. State lifetime remains existing in-memory or DATA_FILE behavior; no new access control or retention policy.

### R-3 Notification
Basis: S7 and outbox contract. Implemented and verified by the local assignment suite; system checks remain. Each real assignment to a name enqueues an event addressed to that agent; reassignment including A→B→A while pending generates each notification; no-op and unassignment generate none. Worker renders and delivers assignment message through existing retry mechanism. Confirm outbox and worker tests, including recipient, message, and no-op. Delivery remains asynchronous with existing retry/dead behavior.

### R-4 Listing filters
Basis: S8; src/tickets/query.js. Implemented and verified by the local assignment suite; system checks remain. GET /tickets?assignee=Agent matches exact assigned name, assignee= matches null; status, priority and assignee filters all must match simultaneously, across cursor pages. Confirm HTTP tests with mixed filters and unassigned records.

### R-5 CLI listing and compatibility
Basis: S9–S11; README.md, package.json. Implemented and verified by the local assignment suite; system checks remain. Human and raw CLI listings show each assignee, with existing raw id/status/priority/title positions retained; unassigned is visibly indicated. Existing tests remain unchanged and npm test executes added node:test coverage. Confirm CLI invocation and full suite. Existing API and workflow remain functional except explicitly requested conjunctive filtering.

### R-6 Bulk reassignment
Basis: current request, src/tickets/validate.js, src/store.js. POST /tickets/reassign accepts exactly `from` and `to`, both valid non-null agent names after trimming and distinct; invalid input returns the standard 400 envelope before effects. It changes every matching open or in_progress ticket, returning 200 with `{moved, ids}` sorted in ticket ID order, including zero matches; resolved, closed and other agents remain unchanged. Each move creates the same audit and assignment notification as individual assignment. Confirm with HTTP and store tests covering mixed states, validation, order, no-op, audit and delivery.

Implemented by src/app.js, src/tickets/validate.js and src/store.js; test/reassignment-escalation.test.js exercises HTTP, audit and delivery. (W1/S1)

### R-7 Urgent escalation
Basis: current request, worker and persistence contracts. On each enabled worker tick, an open, unassigned urgent ticket strictly older than ESCALATE_AFTER_MINUTES since creation (default 60) is escalated by an outbox notification to ONCALL; unset or empty ONCALL disables escalation. Each ticket is escalated at most once, including after restart, without assigning it. Nonqualifying tickets do not escalate; worker interval 0 disables checks. Store owns retained escalation state with outbox, in memory or DATA_FILE, with old files readable. Existing asynchronous retry/dead behavior applies. Confirm threshold, exclusions, configuration, notification content and recipient, repeated ticks and DATA_FILE restart using deterministic clock and node:test.

The escalation store and worker job are covered by the escalation tests, including strict deadline and data-file reload; service configuration wiring remains S3. (W1/S2)

Service configuration and worker wiring are exercised by the configuration tests, including default, custom and disabled settings. (W1/S3)

## Non-functional requirements
Node >=22, standard library only; preserve existing error envelope and asynchronous outbox, use existing tests. Confirm npm test and package inspection. This is a plain terminal report; colors, themes, motion, focus and icons are inapplicable to a noninteractive text listing; preserve readable aligned columns. No new performance bound or remote deployment is requested.

## Retired
None.
