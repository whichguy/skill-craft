R-3 as the newest commit of the spec at or before N1 (2026-11-22T21:56:28Z) holds it, unverified (a plain note stores no digest):

### R-3 Prepare existing data
Basis: S6-S7. Default from 2026-11-22: an operator stops the file owner and runs the backfill before enabling. Read the existing V1 file and fill missing due from stored creation time and priority. Preserve existing due, IDs, ticket fields, audit and outbox. Retry is a no-op on fully prepared data. Enabled startup with any missing due rejects a populated unprepared file. Verify migrations, retry under changed hours and failed startup. Actual production file remains operator-owned.
