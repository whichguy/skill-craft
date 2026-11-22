# Ticket service requirements

## R-1 Configurable immutable deadlines

- S2–S4: With default settings, a new urgent, high, normal or low ticket is due 4, 24, 72 or 168 whole hours after creation, respectively. Request an HTTP ticket of each priority with the test clock fixed and compare exact UTC ISO times.
- Set any of DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL and DUE_HOURS_LOW to positive whole hours before start. Test an override and named rejection of invalid values. Test priority edits and restarts with changed settings against the initial timestamp.

## R-2 Gated ticket output and overdue query

- S5, S7: Only exact DUE_TIMES=on exposes due on ticket HTTP responses and human CLI output. Test get, create, list, patch and transition, and compare flag-off ticket output against the legacy shape. Keep the four raw CLI fields stable.
- With the switch on, overdue=true selects only open and in_progress tickets strictly past due, before cursor pagination and in addition to existing filters. Exercise all four states, an equal time, a future time and a multi-page list using the test clock. With the switch off, the query behaves like an unknown parameter.

## R-3 Compatible startup migration and rollback

- S6–S8: On the new release, load and validate the v1 file, fill missing deadlines from each persisted creation time and priority, and atomically save before listening. Test a legacy file, a file with some due times, a restart with different hours and unmodified audit/outbox/IDs.
- Run the actual 1.4.0 HTTP service and CLI against the new release's file and show that every ticket is readable. Document single writer, dark rollout and preserving deadline values through rollback writes.

## R-4 Existing interfaces and suite

- S1, S9–S10: Preserve npm start, PORT, Node standard-library-only operation, CLI/weekly report, existing request and worker behavior, and existing tests. Add node:test coverage under test/ and run npm test unchanged.

## Scope

Maintain local delivery, startup integrity, cursor semantics, and compatibility of existing clients. The whole-file operation remains linear in ticket count and only rewrites on startup if data changed. No new identity, dependencies, browser UI or production access.
