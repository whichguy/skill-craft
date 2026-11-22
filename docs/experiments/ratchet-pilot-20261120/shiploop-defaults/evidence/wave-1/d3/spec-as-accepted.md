# Help desk tickets specification

## Requirements

Basis for R-1 through R-6: help-desk request of 2026-11-21, with existing contracts in README.md, docs/api.md and docs/operations.md. Checks are local with disposable data; the production file is operator-managed.

### R-1 Assign and retain due times

With due times on, creating an urgent ticket at 2025-01-01T00:00:00.000Z assigns 2025-01-01T04:00:00.000Z. Other defaults are high 24, normal 72 and low 168 hours. Default of 2026-11-21: operators override a priority through DUE_HOURS_<PRIORITY> using positive whole hours. HTTP create, show, list, patch and transition return due. Later priority or settings changes leave the stored value intact. Invalid active configuration fails clearly. Check create and read across priority changes and restarts.

### R-2 List overdue tickets

GET /tickets?overdue=true combines strictly past due and active status with the existing filter and cursor behavior. Default of 2026-11-21: equality is excluded. Resolved, closed and future cases are excluded. Confirm with a manual clock at equality and one millisecond later, and page through qualifying IDs.

### R-3 Backfill and activate

Default of 2026-11-21: stop the file writer and run an explicit command before enabling. Backfill assigns due for every missing ticket deadline from the stored created time and priority, including closed tickets. Repeat runs keep assigned values, even with changed settings. Preserve IDs, counters, audit and outbox. Starting with DUE_TIMES=on and an existing incomplete file fails before serving. An absent file for first start and the in-memory mode can safely start empty. Verify writes, idempotence, and activation against disposable files.

### R-4 Preserve the disabled contract

With DUE_TIMES unset or any value other than on, HTTP shapes and query behavior match 1.4.0, including ignoring overdue. Preserve stored due through new-version writes while disabled. Human CLI output exposes due when on and the file holds it. Raw CLI columns retain their positions. Confirm disabled HTTP, CLI and report against populated data.

### R-5 Roll back to 1.4.0

The exact 1.4.0 service must start on the new data file and serve every ticket. Preserve the current file before a writable rollback. A later reactivation can use that copy to restore missing assigned deadlines by ticket ID, preserving tickets and other changes written by the rollback release. Check an actual old server read and write followed by recovery.

### R-6 Preserve prior behavior and tests

Existing routes, errors, lifecycle, notifications, audit and reports stay compatible. Existing tests remain byte-for-byte intact. New node:test coverage under test/ runs through npm test.

## Non-functional requirements

Node 22 or later and no npm dependencies. Retain old-or-new atomic file replacement and one writer per file. A failed backfill must leave the original file intact. Use existing access to ticket and data-file state. No new outbound effects, identities, or retention behavior.

## Retired

None.
