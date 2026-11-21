# Help desk tickets

## Requirements

### R-1 Immutable deadlines

The help desk response times request of 2026-11-21 adds a deadline to each ticket. A ticket created at 2025-09-01T08:00:00.000Z is due on the same day at 12:00 UTC for urgent, September 2 at 08:00 for high, September 4 at 08:00 for normal, or September 8 at 08:00 for low. Operators can set positive whole hours by priority in the process environment. Changing priority, status or settings preserves a deadline already set. Client writes cannot set due. Observe create, patch and transition responses plus restart and configuration tests.

### R-2 Feature visibility

The response times request adds ISO UTC `due` to all HTTP ticket representations when `DUE_TIMES=on`. Human CLI output also shows stored due times with that flag. Existing flag-off ticket bodies and query handling continue unchanged. The raw CLI and report retain their existing format. Observe identical flag-off HTTP and raw CLI results and test the field on enabled endpoints.

### R-3 Overdue listing

The enabled `GET /tickets?overdue=true` includes open and in-progress tickets whose stored due is strictly earlier than the current time. Exclude tickets due at the current time and tickets in resolved or closed status. Apply before the cursor page and intersect with the existing status-or-priority filter. Absent and false leave normal listing behavior in effect. Other values use the existing invalid-query response when enabled. Verify by moving the injected clock and walking multiple pages over mixed-status data.

### R-4 Backfill and rollout

The service computes missing deadlines from each stored creation time and stored priority even when HTTP exposure is off. On a data-file start it completes the durable write before accepting requests. Repeated startup leaves stored deadlines intact. Backfill preserves tickets, timestamps, counters, audit and outbox except the added field and normal file-save timestamp. A failed backfill prevents startup. Tests use an isolated local copy with legacy and already-populated records. Production rollout and configuration are operator-owned.

### R-5 Release compatibility and unchanged behavior

The actual 1.4.0 server and CLI must read the new file and show all tickets. Existing tests remain unchanged and pass with the new node:test cases under npm test. Recovery procedures preserve the migrated values for a future re-upgrade, because the old writer removes properties it cannot store. The repository and local tests are the delivery target.

## Non-functional requirements

Keep the service dependency-free with Node.js 22+ and the existing single-writer contract. Reuse the atomic full-file replacement, audit and outbox conventions in the repository decisions. No new UI or external service is needed. Keep the existing CLI conventions for table, details and errors. No new latency or throughput target is specified.

## Retired

None.
