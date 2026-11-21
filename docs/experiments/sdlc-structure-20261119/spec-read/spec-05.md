# Help desk ticket service

## Requirements

### R-1 Immutable configurable due times

Basis: 2026-11-21 response-time request, S2–S4. When a ticket is created, its due time is its stored creation timestamp plus 4 hours for urgent, 24 for high, 72 for normal or 168 for low. Positive whole-hour settings override a priority independently. POST returns an ISO UTC deadline when the feature is enabled. For a ticket created at 2025-09-01T08:00:00.000Z the default urgent deadline is 2025-09-01T12:00:00.000Z. A PATCH changes priority without moving due. A restart with changed hours affects newly assigned deadlines only. Verify at the HTTP and data file boundaries in T-1 and T-3. Invalid settings fail at startup with the variable named, as in README's configuration contract.

### R-2 Overdue active tickets

Basis: 2026-11-21 request, S5. When enabled, GET /tickets?overdue=true returns active tickets (open or in_progress) with a strictly earlier due time than the listing time. At the exact due time a ticket is excluded. Resolved and closed tickets are excluded, and a reopened overdue ticket is eligible again. Existing status/priority OR matching, ticket-ID order and cursor semantics continue to apply inside the overdue restriction. Other overdue parameter values have no effect. Verify with the service clock and real HTTP in T-2.

### R-3 Durable preparation and activation

Basis: 2026-11-21 request, S4–S7. Existing tickets receive due times using saved creation and priority at first preparation. On startup with DATA_FILE, save any missing deadlines atomically before the service listens. Then leave previously stored deadlines intact on every restart, regardless of priority or settings changes. Preparation emits no new audit or outbox activity. If the file cannot be prepared, the process must fail before binding. The single service process owns the file (docs/operations.md).
Only DUE_TIMES=on exposes due in HTTP ticket responses and human-readable operator CLI output, and allows the overdue query restriction. Without opt-in, HTTP ticket bodies, query behavior, and CLI output remain as in 1.4.0. The weekly-report raw column contract applies with either setting. Verify with a populated legacy file, restart, and CLI checks in T-3 and T-4.

### R-4 Rollback and existing service behavior

Basis: 2026-11-21 request, S1 and S8–S10. The exact 1.4.0 start entry point reads the data file the new release wrote and lists every ticket. It can continue handling writes and retain all ticket data its version knows. Because a 1.4.0 write drops unknown due fields, retain a pre-rollback copy of deadlines for any forward recovery, keeping live ticket changes. Verify HTTP and file reads with an isolated checkout of the 1.4.0 baseline (T-5). Keep the existing API, CLI, weekly report, audit and outbox behavior and the unchanged 117-test suite. Add built-in node:test coverage under test/ and retain npm start, PORT and npm test.

## Non-functional requirements

- Keep Node.js 22+ built-in modules and the existing single-writer atomic file replacement. Rehearse preparation and rollback on disposable data.
- Keep the CLI's established aligned layout and raw column positions. No new graphical interface, client-side state, access boundary or background job is introduced.
- No new timing SLA for startup or queries was requested. Use the existing in-memory listing and synchronous file-write model.

## Retired

None.
