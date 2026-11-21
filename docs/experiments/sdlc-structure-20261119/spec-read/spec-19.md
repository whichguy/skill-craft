# Help desk ticket service

## Requirements

### R-1 Assign a due time once

Basis: help desk response-time request, 2026-11-21. Use the UTC creation instant plus 4 hours for urgent, 24 for high, 72 for normal, and 168 for low. The operator can override each independently at process startup. Use positive whole hours, with startup diagnostics for invalid settings. No request may set a deadline directly. Changing priority or the response-time settings preserves existing deadlines. Check creation and mutation via HTTP and reload with changed settings.

### R-2 Expose due and overdue tickets when enabled

Basis: help desk response-time request, 2026-11-21. With DUE_TIMES=on, creation, list items, detail, patch, and transition include the ISO UTC `due` field. With the flag absent or another value, ticket bodies and query handling keep the 1.4.0 behavior. For example, with the clock at 2025-09-01T08:00:00.000Z an urgent ticket is due at 12:00 UTC. It is excluded at 12:00:00.000Z and listed at 12:00:00.001Z if open or in_progress. The overdue restriction applies before pagination. Absent or false applies no restriction. Invalid recognized values get the standard invalid envelope when enabled. Audit events and CLI output keep their existing contracts. Check via the real HTTP listener and manual clock.

### R-3 Backfill storage and support rollback

Basis: help desk response-time request, 2026-11-21, and ADR 8. On startup with a data file, use each legacy ticket's recorded creation time and priority to set its missing due. Commit the complete snapshot atomically before listening. Reopen with changed settings and verify existing due values, ticket IDs, audit and outbox state are preserved. New tickets receive due values even during flag-off staging. Keep the version-1 file readable by the actual 1.4.0 service and CLI. Verify all ticket IDs and ordinary fields via the old HTTP listener on a candidate-written file. The 1.4.0 writer does not retain unrecognized ticket fields, so deadline recovery after old writes uses the retained due-bearing backup and the latest ticket state.

### R-4 Preserve existing consumers and verification

Basis: help desk response-time request, 2026-11-21. Keep existing npm start, PORT, npm test, Node standard library, CLI raw column order and existing tests. Add node:test coverage under test/. Check by running the unchanged baseline suite along with new focused cases.

## Non-functional requirements

Use the existing single-writer atomic snapshot and complete the backfill before accepting HTTP traffic. Backfill must preserve existing ticket, audit and outbox contents aside from adding missing deadlines and updating the snapshot timestamp. Repeated startup with complete deadlines does not change existing values. Production rollout itself remains operator-owned.

## Retired

None.
