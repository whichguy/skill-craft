# Help desk ticket service

## Scope

The internal HTTP API and read-only operator CLI serve the shared ticket store. Production operators control configuration and rollout.

## Requirements

### R-1 Assign immutable deadlines

Basis is the November 21, 2026 request to promise response times. For a ticket created at 2025-09-01T08:00:00.000Z, verify through HTTP that urgent, high, normal and low are due at 12:00 UTC that day, or 08:00 UTC on September 2, 4 and 8 respectively. Verify that configured hours change newly assigned deadlines and that a priority edit and restart with new configuration retain an existing deadline. Invalid deadline settings name the environment variable at startup. Deadlines are derived from creation in UTC and remain read-only ticket data.

### R-2 Expose and filter ticket deadlines

Basis is the November 21, 2026 request for due and overdue. With exact DUE_TIMES=on, verify full-ticket API responses include ISO UTC due, and human CLI views show it. Verify that overdue=true limits the list to open and in_progress records strictly earlier than the current clock, before pagination and in addition to the existing filters. At the exact instant a ticket is still excluded. With the flag disabled, test legacy JSON and CLI output and verify the API still ignores overdue. Preserve the raw CLI columns consumed by the weekly report.

### R-3 Migrate existing data before exposure

Basis is the November 21, 2026 request to backfill production data and expose it only after persistence. The service file owner preserves existing assigned deadlines and fills missing ones from persisted creation and priority, making a whole-file save before service availability. Verify old and mixed file backfill, successful retry without recalculation, creation during disabled exposure, and startup failure before listening when a needed save fails. Audit and outbox records, IDs and ticket timestamps retain their meanings. One service process owns writes. The CLI only reads.

### R-4 Allow rollback to 1.4.0

Basis is the November 21, 2026 rollback request. Start the unchanged 1.4.0 source on a candidate-written disposable file and verify that it lists every old and new ticket. The operator retains the pre-rollback snapshot to recover assigned deadlines if 1.4.0 rewrites the live file. Rehearse reapplying only deadline metadata if rolling forward. The old writer is outside the candidate's control.

### R-5 Preserve existing paths and tests

Basis is the November 21, 2026 requirement to preserve the service and extend its suite. Run the existing npm test entry point with every original test and new node:test cases under test/. Keep use of PORT, npm start, CLI commands, notification delivery, audit behavior and dependency-free Node intact.

## Non-functional requirements

Verify file migration is atomic under the existing single-writer design and does not change the status or visibility of ticket data. Verify deadlines in UTC without wall-clock test waits. Human CLI output uses the established alignment and labels. There is no new graphical interface, authentication model or stated performance target.

## Retired

None.
