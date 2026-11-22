# Help desk tickets

## Requirements

### R-1 Fixed creation-time deadlines

Basis: response-time request, 2026-11-21 (S2–S4). The service persists an ISO UTC due value using the ticket's creation time plus 4, 24, 72 or 168 hours for urgent, high, normal or low. Confirm all four with a fixed clock. Existing priority changes and restarts with changed hours keep the original value. Default of 2026-11-21: operators configure DUE_HOURS_<PRIORITY> in positive whole hours. Unset or blank uses default. Invalid values name the variable at startup.

### R-2 Flagged responses and overdue lists

Basis: S5 and S7, 2026-11-21. Exact DUE_TIMES=on exposes due on ticket responses and activates exact overdue=true. Compare now strictly after due for open and in_progress tickets. Confirm future, equality, past, resolved, closed, and reopened cases. Default of 2026-11-21: intersect with existing status/priority OR filter before cursor pagination, ignore other overdue values, and show due in human CLI output with the flag on. The weekly report's four raw columns remain intact. With the flag off, persisted deadlines remain hidden and overdue is ignored.

### R-3 Backfill

Basis: S6–S7, 2026-11-21. Existing records receive due computed from their creation and stored priority, preserving existing due and domain records. Default of 2026-11-21: an offline command supports preparation before opt-in and enabled startup ensures backfill before listening. Confirm idempotence, preservation of ticket metadata, sequence, audit and outbox, and a clear error for a corrupt file.

### R-4 Service and rollback compatibility

Basis: S1 and S8–S10, 2026-11-21. Preserve npm start on PORT, CLI/report operation and existing tests. Confirm 1.4.0 starts and lists all tickets using the upgraded file. Rollback writes can drop due metadata, consistent with the old codec, so operations documents retaining a separate copy. Verify through the actual 1.4.0 codec and locally running server, then npm test with new files under test/.

## Non-functional requirements

Keep Node standard library only. Maintain single-writer, replace-whole persistence using the existing operational model. No new network dependency, identity, event sink or schedule. Maintain the CLI's established text formatting and raw machine contract.

## Retired

None.
