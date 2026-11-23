### R-3 Durable backfill

From each persisted record's creation time and stored priority, calculate any missing due time. The November 2026 operator clarification requires a separate, repeatable command: stop the service and run `DATA_FILE=... npm run migrate:due`, then enable the feature. Starting the service never fills in existing deadlines. With the feature on and any due value absent, startup fails and names `npm run migrate:due`. A migration write failure leaves the old file available. Existing due values, ticket IDs, timestamps, statuses, audit, outbox and counters persist. Check the file around the migration and restart with different hours.

The offline command preserves all previously set due times, changes only missing deadlines, and reports the count. The migration test verifies identical bytes on a no-op repeat (W1/S1).

The startup test observes exit status 2 and the migration command when a deadline is missing. An omitted flag leaves existing deadlines hidden and does not fill missing ones (W1/S2).
