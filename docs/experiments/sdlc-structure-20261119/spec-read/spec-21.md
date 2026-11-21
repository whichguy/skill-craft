# Help desk tickets

## Requirements

### R-1 Persistent ticket deadlines

- Basis: November 21, 2026 request S2–S4. New tickets get a UTC `due` instant at creation. An urgent ticket created at 08:00 UTC defaults to 12:00 UTC on the same day. High, normal and low default to 24, 72 and 168 elapsed hours. HTTP create tests cover each priority and an environment override.
- Store the deadline once. HTTP PATCH and database restart tests confirm that a priority change or different hour configuration leaves the original value in place. New tickets use the current settings. Client attempts to supply `due` follow the existing unknown-field error contract.

### R-2 Enabled ticket reads and overdue selection

- Basis: November 21, 2026 request S5 and S7. With `DUE_TIMES=on`, create, get, list, patch and transition return `due`. Human CLI reads may show the saved time. Raw output retains its four fields for the existing report.
- `GET /tickets?overdue=true` selects only `open` and `in_progress` tickets with `due < now`, before applying the page size and cursor. Test overdue, exact cutoff, future, resolved, closed and combined query cases with the manual clock.
- With any other flag value, ticket response shapes, audit, outbox and filter results follow 1.4.0. Exercise both default and explicit off.

### R-3 Historical migration and rollback

- Basis: November 21, 2026 request S6–S8. Operators stop the sole writer and run the backfill before enabling. Existing tickets without due use their stored creation time and priority. An enabled service refuses an incomplete configured file. Reruns preserve existing values. Check the data file and restart the service on disposable legacy and mixed data.
- Keep every ticket and all unrelated state in the version-1 snapshot. Migration does not change updated, audit history, sequence, or outbox. On an error the original snapshot remains available. Start actual 1.4.0 on the candidate snapshot and verify its ticket list. A preserved migrated copy is the recovery source for deadlines if 1.4.0 writes before re-upgrade.

### R-4 Existing service and tests

- Basis: November 21, 2026 request S1 and S9–S10. Keep the Node built-in-only service, npm start, PORT setting and CLI/report interfaces, with the 117 original tests and new node:test cases all running under npm test.

## Non-functional requirements

Single writer and atomic whole-file replacement as in decision 8. Use the existing HTTP envelope, logs, audit retention, CLI presentation and notification lifecycle. Repeatability, compatibility and data integrity are checked locally at the file and live API boundaries. The scope contains no new graphical interface, external dependency or production deployment.

## Retired

None.
