# Help desk ticket service

## Requirements

### R-1 Fixed per-ticket response deadline

Basis: 2026-11-21 response-time request S2–S4. The service computes a UTC ISO 8601 `due` at creation using the ticket's creation time and its priority. The default elapsed hours are urgent 4, high 24, normal 72 and low 168. Operators can override each independently via the runtime environment. Invalid configured hours fail with the variable named.

- A ticket at 08:00 UTC on September 1, 2025 is due at 12:00 on September 1 for urgent, 08:00 September 2 for high, 08:00 September 4 for normal or 08:00 September 8 for low. A 6-hour urgent override makes a newly opened urgent ticket due at 14:00. Confirm through the actual creation route against a manual clock.
- Changing the priority and restarting with different hours preserves earlier deadlines. Clients cannot submit a deadline. Confirm via PATCH, GET and a file-backed restart.
- An enabled service includes `due` in each ticket object, and the enabled human CLI displays it. Exact `DUE_TIMES=on` controls exposure. When disabled, HTTP bodies, legacy filtering and human CLI output follow the baseline, while candidate-created tickets still have their original deadline persisted. Raw CLI columns always keep their original layout. Confirm with HTTP, file and CLI checks.

### R-2 Overdue listing

Basis: 2026-11-21 response-time request S5, with known filter and page behavior observed in src/tickets/query.js and test/query.test.js.

- With the flag enabled, an exact `overdue=true` keeps only open and in_progress tickets whose due is strictly before the sampled time. Equality, future dates, resolved and closed tickets do not qualify. Confirm through HTTP using a manual clock and actual lifecycle transitions.
- Apply the deadline constraint after existing filter matching and before cursor pagination; an omitted or other overdue value leaves the legacy query behavior. Confirm HTTP ID sequences across pages and with a status/priority filter.

### R-3 Data preparation and rollout

Basis: 2026-11-21 response-time request S6–S7; docs/operations.md governs single-writer operation.

- Stop the service, then run an offline migration against an existing file. Each missing deadline uses the stored creation time and stored priority. Existing deadlines, ticket fields, ids, audit entries and outbox records are retained. Validate the whole file before writing; rerunning against a fully prepared file leaves it unchanged. Confirm by inspecting the file and re-reading with the service.
- Enabled startup against a stored ticket missing due fails before HTTP listens, and leaves the file untouched. After migration, enabled startup serves the durable values. A fresh empty store can start enabled. Confirm by startup and HTTP on disposable files.

### R-4 Rollback

Basis: 2026-11-21 response-time request S8 and baseline commit 404b4ef (version 1.4.0).

- Unmodified 1.4.0 starts on the same file the candidate wrote and returns all its legacy and new tickets. Confirm by starting the archived baseline executable against that file and requesting tickets through HTTP.
- Because the old writer omits due, the operator can snapshot the file before rollback and restore deadlines from that copy during a later migration, preserving current ticket edits and new tickets. Confirm with an old schema rewrite plus a migration and re-enable.

### R-5 Existing workflows

Basis: 2026-11-21 response-time request S1 and S9–S10, README.md and CONTRIBUTING.md.

- `npm start` respects `PORT`, and `npm test` runs the original suite unchanged and the new node:test coverage. CLI raw and weekly reporting continue to read the same four columns. No npm dependency is added. Confirm by actual commands and reviewing the diff.

## Non-functional requirements

Retain the existing Node support and single-writer atomic replacement model. Migration recovery uses a backup or an idempotent rerun. Persist only the additional deadline and retain the existing visibility and attribution of personal data. The CLI adopts its existing table and detail conventions. No new graphical UI, service, timer or throughput target is required.

## Retired

None.
