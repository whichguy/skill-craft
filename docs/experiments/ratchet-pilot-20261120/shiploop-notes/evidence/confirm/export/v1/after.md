### R-3 Persist historical deadlines before serving

- Based on S6–S8. Owner instruction N1 (2026-11-22): stop the service and run `DATA_FILE=path/to/tickets.json node scripts/backfill-due-times.js`. It derives each missing deadline from the stored creation timestamp and priority, preserves existing deadlines and saves atomically. The server performs no startup backfill. With `DUE_TIMES=on`, it refuses to start if a ticket lacks a deadline and names the command. Tickets created with display disabled still save their deadline. Verify the file at each step and after restarts.
- Keep the old document version. Start the release 1.4.0 HTTP service on a file produced by the candidate and compare all ticket IDs and legacy fields. Audit, outbox, IDs and existing ticket fields survive the backfill. Operators own actual production rollout. The old writer's treatment of new fields limits rollback and is documented.

- TC-3 checks the enabled startup error and unchanged file bytes before the explicit migration (W1/S1).

- TC-5 in test/due-times.test.js runs the actual backfill, then checks the version-1 file and refires enabled startup. TC-4 verifies human and raw CLI views (W1/S2).
