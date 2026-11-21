# Help desk ticket service

## Requirements

The due-time requirements below come from the November 2026 request for help desk response commitments. The preserved runtime and interfaces are described in README, docs/api.md, docs/operations.md and decision 8. Verification uses local service and file fixtures.

### R-1 Immutable due times

A new ticket takes its creation instant plus 4 urgent, 24 high, 72 normal, or 168 low hours by default. Operators may override each priority through its environment setting. For example, urgent created at 2025-09-01T08:00:00.000Z is due at noon UTC. Verify via HTTP creation and read-back. A priority edit, state change, restart or configuration change leaves a saved deadline intact. An unset or empty override uses its default, and an unusable value names the setting at startup. Clients cannot set due via the ticket request body.

### R-2 Ticket responses and overdue listing

With exact DUE_TIMES=on, create, get, patch, transition and listed ticket objects show their saved UTC due time. The overdue=true filter includes only open and in_progress tickets with due strictly before the request clock instant. Equality, future timestamps, resolved and closed are excluded. The overdue restriction and supplied status and priority constraints apply before cursors and limits. The optional overdue=false value leaves the normal listing intact. Other overdue values get the standard invalid envelope while enabled. External HTTP tests verify response shapes, status boundaries and a cursor across matching rows.

### R-3 Dark rollout and backfill

On load, a saved ticket missing due takes its saved creation time plus the configured hours for its saved priority. Existing due values remain exact. The owning service writes the result using its normal atomic file replacement before accepting requests, regardless of flag state. A failed write prevents startup. A restart with no missing values makes no migration rewrite. Backfill leaves ticket fields, IDs, audit and outbox state intact. With the switch absent or anything besides on, HTTP output and overdue parameter handling are identical to 1.4.0. Test a mixed file, flag-off and enabled restarts and changed configuration against the same file.

### R-4 Rollback and established clients

The original 1.4.0 server must start on the new release's file and return every ticket. Its writer can drop unrecognized due fields if rollback proceeds to a write, so preserve a current backup before rollback and reconcile deadlines before re-enabling if 1.4.0 wrote. Verify the real baseline reader over candidate state. The CLI remains read-only and its raw four-column format remains compatible with the weekly report. With the switch on, human CLI output shows stored deadlines available to it. With the switch off, legacy output is unchanged.

### R-5 Regression suite

Keep npm start, PORT, Node 22+, zero dependencies, previous routes and test files. Add node:test coverage in test/ and execute it along with the existing tests through npm test.

## Non-functional requirements

Keep a single writer, atomic state replacement, the existing HTTP error envelope and the existing worker behavior. No new access or background process. The terminal output uses established table and detail conventions with legacy raw output preserved. No production host or file is in local delivery scope.

## Retired

None.
