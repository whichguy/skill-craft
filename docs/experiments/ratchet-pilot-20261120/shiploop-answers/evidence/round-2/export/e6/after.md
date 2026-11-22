### R-3 Backfill and rollback

- The rollout default is startup preparation before the listener opens, including while presentation is disabled. It fills missing due timestamps from stored creation time and priority and persists them atomically in version 1; audit, outbox, IDs and existing due timestamps survive. Test with version-1 data and restarts.
- Version 1.4.0 starts on a file written by the candidate and exposes all old and new ticket records. Verify through actual release HTTP. Its write path strips unknown fields, so preserve a copy of due assignments before rollback and reconcile before re-enabling.
