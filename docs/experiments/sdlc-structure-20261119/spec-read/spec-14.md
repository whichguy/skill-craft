# Help desk ticket service

The ticket HTTP API, operator CLI, audit log, notifications and weekly report retain the existing contracts in README.md, docs/api.md and docs/decisions. The deadline rules below come from the help desk's 2026-11-21 response-time request.

## Requirements

### R-1 Ticket deadlines

- When the feature is on, creation, reads, edits, transitions and list items show a read-only ISO UTC `due` timestamp. A ticket created at 2025-09-01T08:00:00.000Z is due at 12:00Z for urgent, 08:00Z the next day for high, 08:00Z three days later for normal or 08:00Z seven days later for low. Check with the manual clock over HTTP for all priorities.
- Operators may configure positive whole response hours per priority through `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` and `DUE_HOURS_LOW`. The effective setting applies to new deadlines. Invalid overrides fail startup with the setting name. Check configured creation and invalid settings.
- Editing priority or restarting under different hours preserves the original `due`. Check the edit and the response after restarting with the same persisted ticket. Request body validation and existing audit/notification behavior remain in effect.

### R-2 Overdue pages

- With the feature on, `GET /tickets?overdue=true` selects open and in-progress tickets whose deadline is before the clock instant. Equality and all later due times are excluded. Resolved and closed tickets are excluded even when past due. Check all statuses and the boundary at due and one millisecond after it.
- Apply overdue in conjunction with the existing selection before the cursor and page limit. Preserve existing status/priority selection and ID order. `overdue=false` leaves selection unchanged, and invalid values produce the usual 400 envelope while enabled. Check two pages and a combined filter through HTTP.

### R-3 Migration and persistence

- Backfill any missing deadline from the ticket's persisted creation time and priority. Preserve existing deadlines, IDs, updated timestamps, history and outbox across migration and restart. The single service process owns the file. Check a mixed version-1 fixture and repeat startup after changing configuration. A startup requiring migration completes the atomic save before listening. Check the on-disk file before an HTTP listener runs, and test a failed save.
- Optional in-memory operation remains available. In memory, deadlines last for the process lifetime.

### R-4 Activation and rollback

- Only the exact `DUE_TIMES=on` setting exposes deadlines and makes the overdue parameter effective. Off-mode ticket responses and query behavior match the established API. Human CLI output is flag-gated and raw CLI and weekly report fields remain intact. Check both flag states.
- Release 1.4.0 must start and list every ticket using a file the new release wrote. Check the original 1.4.0 code over HTTP against an upgraded disposable file with legacy and new rows. Operators can keep a post-migration backup of deadline metadata because the 1.4.0 writer discards the field on save. Old-format rows with missing deadlines are eligible for backfill when the new version starts again.
- Production activation follows the instructions in docs/operations.md. The repository's local checks use disposable data. Production activation is owned by the service operator.

### R-5 Existing entry points and tests

- Keep `npm start`, `PORT`, `npm run report:weekly`, the CLI and dependency-free Node runtime. Existing tests stay unchanged. Add the deadline cases under test/ so `npm test` runs the original and new cases. Confirm via the complete suite and local startup/rollback.

## Non-functional requirements

- Preserve the version-1 atomic single-file write, existing ordering and page envelope. No new network access, dependency, background work or new identifying data is needed. The existing CLI table, empty output and error conventions remain, and raw output stays script-compatible.
- The overdue decision uses one clock observation per list and the existing linear scan. No new production latency threshold or graphical UI is required.

## Retired

None.
