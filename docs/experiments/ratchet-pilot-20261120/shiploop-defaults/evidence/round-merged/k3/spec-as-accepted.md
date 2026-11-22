# Specification

## Requirements

### R-1 Immutable due times
Help-desk response commitments use creation time plus 4 / 24 / 72 / 168 elapsed hours for urgent / high / normal / low. Operators may override these hours by environment at start. Persist the computed ISO timestamp once, including for new tickets while the switch is off. HTTP and restart tests confirm all defaults, overrides, and unchanged values across priority, status and configuration changes.

### R-2 Gated exposure and overdue retrieval
Only exact DUE_TIMES=on exposes due on HTTP ticket representations and human CLI views. An exact overdue=true restricts the HTTP listing before pagination to open and in_progress tickets with due strictly earlier than now, in addition to existing filters with their current OR semantics. Other values follow existing unknown-query behavior. HTTP and CLI checks cover the gate, time equality, statuses, filter composition, page boundaries and legacy output.

### R-3 Backfill and rollback
Operators stop the sole writer and use an idempotent command to populate missing due values from each stored creation time and priority; existing values remain. Activation refuses an incomplete existing file. The unchanged 1.4.0 release can start on the new file and list every ticket. Disk/restart command tests and a release probe using unchanged 1.4.0 confirm these outcomes.

### R-4 Current service behavior
Preserve standard-library Node, PORT and npm start, raw CLI columns and weekly report, API/audit/outbox behavior, and the existing node:test suite without changes. Run new cases and existing cases together with npm test.

## Non-functional requirements
The service continues to own the JSON file as one writer. Migrate offline with existing same-directory rename; no external services, schema version bump or new access. The current in-memory list scan and per-write JSON serialization remain appropriate at current documented volume.

## Open questions
Production scheduling and file location belong to operations during rollout.
