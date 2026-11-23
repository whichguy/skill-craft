### R-3 Backfill and rollback

Basis: existing-data and rollback request and owner clarification, 2026-11-22. Startup with DUE_TIMES on fills every missing due from the stored creation time and current stored priority. It preserves assigned deadlines, saves the version-1 snapshot atomically, and then serves.
- Start the enabled server on legacy data containing a mix of tickets with and without due. Read the file while the service is live to verify the full data and compare audit, outbox, sequence and ticket fields. Restart with changed hours and confirm the stored deadlines are identical.
- Run version 1.4.0 on recent candidate-written data and compare every ticket. Its next write strips due properties, so the operations procedure saves a copy of candidate due values before rolling back.
