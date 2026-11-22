### R-3 Backfill and rollback

Basis: the 2026-11-22 request to store deadlines for existing tickets before exposure and allow the current release to read the written file.
- Default of 2026-11-22: start the new release with the flag off to atomically save due for missing tickets before serving; startup also completes this save before enabled service readiness. Use each record's creation timestamp and stored priority. A rerun only fills missing values. Check the file before the first response and on restart with changed hours; preserve ticket details, numbering, audit and outbox.
- Exact release 1.4.0 opens the candidate-written file and returns all tickets, including those created after migration. Use a disposable file with the unchanged 1.4.0 runtime. File ownership stays single-writer. Production deployment is outside the local check.
- TC-3 in test/due-times.test.js checks a failed migration leaves the previous file byte-for-byte intact. The exact-release TC-4 run verifies the old reader on candidate-written data. (W1/S1)
