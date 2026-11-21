# Help desk ticket service specification

The established API, operations and CLI contracts live in docs/api.md, docs/operations.md and README.md. The due-time requirements below were added by the help desk request of 2026-11-21.

## Requirements

### R-1. Persist a fixed response deadline

- Defaults in elapsed hours are urgent 4, high 24, normal 72 and low 168. An operator can override each independently with environment configuration. Verify using configuration and HTTP creation tests for all four priorities.
- The service assigns ISO UTC `due` from the stored creation instant and priority at ticket creation even with visibility off. For pre-existing records without a deadline, use the record's current stored priority and creation instant, then save before serving. Verify raw file and read-back with a controlled clock and a legacy version-1 file.
- An existing deadline survives status or priority changes, restarts, and changed configured hours. Backfill leaves audit, outbox, ticket timestamps and counters intact and a repeated startup makes no migration write when all values exist. Verify mixed files, on/off restarts, and disk contents.
- The service is the single file writer. An enabled service starts listening only after any required backfill has been saved. Verify startup failure leaves the original readable on a forced save error.

### R-2. Expose and filter deadlines through the ticket API

- Only the exact environment setting `DUE_TIMES=on` enables the API feature. Ticket objects from create, list, get, update and transition expose `due` when on. With the flag off they retain their baseline shape and all `overdue` values are ignored. Verify every response surface and off mode against persisted data.
- `GET /tickets?overdue=true` restricts results to open or in_progress tickets whose deadline is strictly earlier than the current time, before cursor pagination. Example: an urgent ticket created at 2026-01-01 00:00Z is absent at 04:00Z and becomes eligible at 04:00:00.001Z if active. Omitted and other values use the ordinary listing. Verify controlled-clock status boundaries, combined queries, and a second page.
- Existing status/priority combination semantics remain as observed in the 1.4.0 runtime, including when the overdue restriction is applied. The CLI raw columns, audit schema, notifications, and weekly report stay compatible. Verify the unchanged test suite plus API/CLI checks.

### R-3. Roll back to 1.4.0 with the current data file

- The unchanged 1.4.0 binary starts against a file containing both migrated and newly created tickets from the new release. It lists all ticket IDs and can retrieve each legacy ticket view. Verify by starting the exact baseline package against synthetic upgraded data.
- Operators prepare the file with the flag off and enable it only after verification. The release guide records safe single-writer rollback. Before 1.4.0 writes, retain a copy of the upgraded file. On re-upgrade, allow the operator to recover dates from that copy by ticket ID and creation instant, preserving all live records and preferring any existing live deadline. Backfill tickets created under 1.4.0 using the ordinary rule. Verify the changed priority, new ticket, and retained original deadline in the local rollback sequence. Production activation belongs to operators.

### R-4. Keep the service usable through existing entry points

- The dependency-free service starts through npm start on PORT. The existing node:test suite remains unchanged, and npm test also discovers new behavior tests in test/. Verify using the existing command.
- The CLI and report continue reading version-1 files and the report's four raw columns keep their positions. The human-readable detail and list views show a stored due time when enabled. Verify both modes against a migrated file.

## Non-functional requirements

Preserve the current single-writer atomic JSON replacement and consistent read-only CLI access. No new dependency, daemon, permission or production access is required. Query evaluation adds one clock read and one scan consistent with the existing listing. No new UI or external service boundary is introduced.

## Retired

None.
