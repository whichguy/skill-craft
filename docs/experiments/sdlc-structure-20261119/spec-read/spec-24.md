# Ticket service specification

## Scope

The dependency-free help-desk server, its operator CLI, cursor listings and version 1 state file are maintained together. Due times extend the response-time agreement without changing ticket lifecycle rules.

## Requirements

### R-1 Assign a persistent deadline

The 2026-11-21 response-time request defines defaults of urgent 4, high 24, normal 72 and low 168 hours after creation.
- Create tickets at 2025-09-01T08:00:00.000Z with each priority and expect the same-day 12:00 UTC, next-day 08:00 UTC, September 4 08:00 UTC and September 8 08:00 UTC, respectively, in their enabled HTTP responses and saved values.
- The operator can override hours by priority without a code change. Set urgent to 6 while leaving other priorities at defaults. The HTTP create response for an urgent ticket at 08:00 UTC is due at 14:00 UTC. Invalid hour values receive a startup configuration error naming the variable.
- Change a ticket's priority or lifecycle and restart with different hours. Existing due values survive those changes. New tickets use the hours effective on creation. Clients cannot supply due in a ticket mutation.

### R-2 Expose due and filter overdue

The 2026-11-21 request adds due to ticket responses and an overdue list.
- When enabled, every HTTP ticket representation and interactive CLI list or show includes due. The four raw report columns and audit and outbox formats stay intact. Test create, list, get, patch, transition, CLI list/show/raw and the weekly report protocol.
- GET /tickets?overdue=true includes only open or in_progress tickets strictly past their deadline. At the due instant the ticket is excluded. Resolved and closed tickets are excluded, and an overdue reopened ticket is included. Use the injected clock and check the result across cursor pages.
- Overdue must hold in addition to the existing status/priority predicate. Queries without literal overdue=true retain their existing meanings. Check filtering before pagination.

### R-3 Backfill without moving existing deadlines

The 2026-11-21 request requires every legacy ticket to use its stored creation time and priority.
- With the sole writer stopped, migrate a version 1 copy that contains both missing and existing due fields. Expect every missing value to use its own creation time and priority, all existing due values to remain, and the counters, other ticket fields, audit and outbox to retain their values. A second migration with changed hours must leave the complete file unchanged.
- Test refusal of corrupt input and verify no rewrite. An enabled service with a missing due in a saved ticket refuses startup before listening and gives operators the migration command. A new store can start enabled.
- Keep one operator-owned snapshot before running 1.4.0 on a migrated file. On re-upgrade restore missing deadlines for matching ticket IDs and creation times from that snapshot, then fill any remaining tickets from their own creation time and priority. Confirm a migration with the saved snapshot retains tickets and state written by the old release.

### R-4 Keep flag-off and rollback compatible

The 2026-11-21 request requires exact legacy responses unless DUE_TIMES is on and rollback compatibility with release 1.4.0.
- With the flag unset or any value other than on, create, fetch, list, patch and transition return legacy ticket fields, and overdue is ignored. CLI columns and read-only behavior stay compatible. Backfilled due fields survive writes with the flag off and new tickets already receive persistent deadlines.
- Start the original release on the version 1 file after migration and candidate runtime writes, then check all ticket IDs and ordinary data through HTTP. Its writer drops due fields, so R-3 defines the recovery procedure.
- Keep the original Node suite unchanged and add new node:test cases to npm test.

## Non-functional requirements

Keep the existing one-writer contract and atomic file replacement. Exercise idempotence, restart and rollback with a disposable persisted fixture. Use one clock read per filtered page and the existing cursor pipeline. No new runtime packages, scheduled jobs, account scope or external data sink. The interactive CLI keeps its aligned table and compact details conventions. Actual production file contents and access remain operator-owned.

## Retired

None.
