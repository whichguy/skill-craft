# Ticket assignment specification

## Requirements

### R-1 Assignment API
Basis: user request; existing API and validation conventions in docs/api.md and src/tickets/validate.js. PUT /tickets/:id/assignee accepts exactly an assignee string, trimmed and single-line, nonempty and at most 64 characters, or null. It returns the updated ticket; malformed input yields 400, missing ticket 404. Only open or in_progress tickets permit either operation; resolved and closed yield 409 without side effects. Repeating the current value changes nothing, including updated, audit and notifications. Confirm by HTTP tests for valid, null, boundary, malformed, missing, state and no-op cases.

### R-2 Ticket representation and storage
Basis: user request; src/store.js and src/persistence.js. Every ticket returned by create, get, list and updates has assignee null initially or its current agent. Version 1 data files without the field load as null; changes persist and survive restart, with existing fields and audit preserved. Confirm by API and persistence restart tests, including a legacy file.

### R-3 Notifications and audit
Basis: user request and CONTRIBUTING.md. Each actual assignment enqueues a notification to the new agent through the existing outbox and worker; unassignment and no-op produce none. An assignment records actor and old/new values in audit; notifications remain retryable using existing worker semantics. Multiple real assignments, even while pending, must not suppress each other. Confirm by audit, outbox and delivery tests.

### R-4 Filtering
Basis: user request. GET /tickets accepts assignee=agent and assignee= for unassigned; all supplied filters must match, before pagination. Confirm by HTTP tests combining status, priority and assignee, and pages. Existing individual filters and cursor behavior remain.

### R-5 Command line and compatibility
Basis: user request and README.md. CLI list displays each assignee and unassigned state; raw output retains its first four existing columns and appends the assignee. Existing behavior and tests remain valid; new node:test tests run via npm test. Confirm with CLI execution and full suite.

## Non-functional requirements
Standard library only, Node >=22, existing error envelope and worker retry semantics (CONTRIBUTING.md). No new remote service or authentication; API and stored state remain readable to existing operators. Existing optional data file determines lifetime, with no new retention policy. Concurrent handlers use existing synchronous store operations. No new performance bound requested; existing pagination remains. Verify by inspection and npm test.

## Retired
None.
