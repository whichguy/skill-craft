R-3 as the newest commit of the spec at or before N1 (2026-11-23T01:46:22Z) holds it, unverified:

### R-3 Backfill and rollback

Basis: existing-data and rollback request, 2026-11-22. The operator pauses writers and runs an offline backfill (default chosen 2026-11-22). The migration uses each ticket's stored created time and priority, preserves any due already present and rewrites the version-1 file atomically. Startup with on and an incomplete existing file fails with migration guidance (default chosen 2026-11-22).
- Test refusal on incomplete data, run the backfill command on genuine service-written legacy data, compare audit, outbox, sequence and ticket fields after migration, then rerun with changed hours and compare bytes. Start and query via normal server entry points with on.
- Run version 1.4.0 on recent candidate-written data and compare every ticket. Its next write strips due properties, so the operations procedure saves a copy of candidate due values before rolling back.
