### R-3 Prepare legacy data before serving and preserve rollback compatibility

- The requester decided that startup with DUE_TIMES=on calculates each missing deadline from that ticket's creation time and stored priority, saves the file, and then serves. Missing due times trigger automatic backfill.
- Backfill keeps existing deadlines and leaves audit, outbox and identifiers intact. Test a mixed data file and repeated startup with changed settings.
- A 1.4.0 process starts against candidate-written data and returns every ticket, with original fields and identifiers. Verify with the unchanged 1.4.0 executable and a temporary data file.
- A write failure aborts preparation before serving. Verification uses an isolated fixture, and the runbook records single-writer and backup procedures.
