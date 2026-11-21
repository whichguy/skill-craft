# Ticket service specification

## Requirements

### R-1 Calculate and keep one due time

Basis is the operator request of 2026-11-21, S2–S4. Creation assigns one UTC ISO deadline from the creation instant and the priority at creation. Defaults in hours are urgent 4, high 24, normal 72, low 168. Operators can override individual priorities with DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL and DUE_HOURS_LOW. Unset or empty values use defaults and invalid overrides identify the setting. Changing priority, status or configuration, including across restarts, preserves an existing due. The server owns this field and write bodies cannot supply it.

Acceptance uses deterministic HTTP creates at 2025-09-01T08:00:00.000Z, yielding 12:00Z that day, 08:00Z September 2, 08:00Z September 4 and 08:00Z September 8 respectively. An urgent 2-hour override yields 10:00Z. Restart and patch keep the earlier due.

### R-2 Expose deadlines and list overdue tickets on opt-in

Basis is S5 and S7. Only DUE_TIMES=on exposes due in ticket responses and human CLI views. The existing four CLI raw columns remain the weekly report input. Off, all legacy response bodies, query semantics and CLI output remain as before, including ignoring overdue. With the flag on, overdue=true restricts the existing matching set before cursor pagination to open or in_progress and due strictly earlier than the current instant. Unset, false and other values retain normal listing. Resolve or close removes the ticket from overdue, and reopening can include it again.

Acceptance uses HTTP create, list, show, patch and transition and an exact-deadline clock comparison followed by a 1 ms move. It checks filtered cursor pages and the CLI list, show and raw output. It checks old response shapes while off.

### R-3 Prepare historical data before activation

Basis is S6 and S7. An offline operator command uses the same hour overrides on stored creation and priority for tickets missing due. It preserves existing deadlines, statuses, updated timestamps, IDs, audit entries and outbox. A second run with no missing deadline does not rewrite the file. An incomplete populated file fails enabled service startup before listening, with an actionable preparation error. Fresh storage or memory-only startup has no outstanding preparation. While off, new tickets still receive stored deadlines.

Acceptance compares complete version-1 documents before and after preparation, executes the command twice with different overrides and restarts against the prepared file. Failure cases cover missing, corrupt and incomplete files. Single-writer authority and backup are owned by the service operator.

### R-4 Roll back to 1.4.0 and preserve existing behavior

Basis is S1 and S8–S10 plus decision 0008. The release keeps the existing file version. Real 1.4.0 starts against an enriched file and lists every ticket with its 1.4.0 representation. It omits the added field when writing, so operators retain a due-enriched backup before rolling back. Existing tests stay unchanged and pass alongside new node:test cases with npm test. The service remains dependency-free and uses npm start and PORT.

Acceptance runs the original 1.4.0 executable against a copy of the candidate-written data file, enumerates tickets and verifies their old representation. Run the complete npm suite and compare existing test files to the starting revision.

## Non-functional requirements

- Configuration and file validation fail through existing diagnostic conventions. Offline preparation replaces the JSON state atomically after all records pass checks, with no added external service, scheduled job or new identity.
- Response freshness follows the existing shared clock and single-process store. The feature includes no new graphical UI, data recipient, cache or performance target. Human CLI views preserve their existing formatting and raw output stays stable.

## Retired

No retired requirements.
