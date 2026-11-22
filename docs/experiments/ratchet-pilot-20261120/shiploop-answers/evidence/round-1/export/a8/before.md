### R-3 Prepare legacy data before serving and preserve rollback compatibility

- Default (2026-11-22): startup backfills missing deadlines before listening using each row's created timestamp and stored priority, with the flag off during production preparation. Keep existing deadlines and leave audit, outbox and identifiers intact. Test mixed data and repeated startup with changed settings.
- A 1.4.0 process starts against candidate-written data and returns every ticket, with original fields and identifiers. Verify with the unchanged 1.4.0 executable and a temporary data file.
- A write failure aborts preparation before serving. Verification uses an isolated fixture, and the runbook records single-writer and backup procedures.
