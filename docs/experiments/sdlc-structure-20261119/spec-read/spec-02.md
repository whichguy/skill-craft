# Help-desk ticket service

## Requirements

### R-1. Set due times once

For the response promises requested on 2026-11-21 (S2–S4), each new ticket gets a UTC ISO timestamp equal to its creation instant plus the hours configured for its initial priority. Defaults are urgent 4, high 24, normal 72 and low 168. The service reads whole positive hour settings from DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL and DUE_HOURS_LOW, takes defaults for missing or blank values, and reports the name of an invalid setting at startup. Confirm four exact timestamps from a fixed clock, an override, a later priority edit and a restart with changed config. Ticket clients cannot supply or patch due.

### R-2. Expose and filter deadlines

For the HTTP behavior requested on 2026-11-21 (S5, S7), exact DUE_TIMES=on adds due to all ticket responses, including mutation results. GET /tickets?overdue=true then includes only open and in_progress tickets with due strictly before the current instant, applied before cursor pagination and alongside existing filters. Compare HTTP results at equality and one millisecond later, for all lifecycle states and with an existing filter and limit. When the flag is unset or has another value, HTTP keeps the legacy shape and ignores the overdue parameter. Human CLI views can display stored due with the flag on. The weekly report keeps the four raw columns.

### R-3. Backfill before activation

For the stored tickets requested on 2026-11-21 (S6–S7), backfill missing due values from each record's created instant and saved priority while leaving stored due, status, history, event and counter data intact. New tickets also get stored due while exposure is off. Under the single-writer condition in docs/operations.md, missing values are written together before HTTP listens. An unsuccessful write prevents startup and leaves the previous snapshot readable. Check the file before stopping the candidate, verify repeat startup after configuration changes, and simulate an unwritable replacement.

### R-4. Keep release 1.4.0 readable and preserve existing consumers

For rollback and regression behavior requested on 2026-11-21 (S8–S10), exact release 1.4.0 starts from the candidate-written version-1 file and lists every ticket, including tickets created by the candidate. The old release may discard fields it does not understand when it saves; document deadline preservation and reactivation implications. Keep the pre-existing HTTP, CLI, audit, delivery and report behavior, including raw column order and legacy filter behavior. Verify against the exact release and run npm test unchanged with additional node:test coverage in test/.

## Non-functional requirements

Use Node.js 22+ and its standard library, with no packages. The migration runs in the existing single writer and retains atomic replacement behavior. Audit, requester data, notification delivery and access scope follow the existing service. CLI follows the existing column and details layout. No graphical UI or new identity is in scope.

## Retired

None.
