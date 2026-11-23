R-4 as the newest commit of the spec at or before N1 (2026-11-23T01:50:52Z) holds it, unverified:

### R-4 Tickets already in the data file get due times
When the service starts on a data file whose tickets lack `due`, each such ticket gets due = its own `created` + hours of its own `priority`, and the file is saved at once (before any request), regardless of `DUE_TIMES`. Tickets that already have `due` keep it. Backfill is not a ticket change: no audit entry, `updated` untouched, no notification. The command line never writes the file.
- Positive: a v1 file with T-0001 {priority high, created 2026-01-01T08:00:00.000Z, no due}: after `createService` the file on disk holds due 2026-01-02T08:00:00.000Z; a second start with other hours leaves it. Confirmed by a service/persistence test reading the file.
- Positive: a file already holding due is not rewritten with a different due. Confirmed by a persistence test.
- Boundary: with no data file or an empty store nothing is written by backfill. Confirmed by a test.
- Boundary: `updated` and the audit log of the backfilled ticket are byte-equal before and after. Confirmed by a test.
