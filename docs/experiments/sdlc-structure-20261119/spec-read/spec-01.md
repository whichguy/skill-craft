# Help desk tickets specification

## Scope

The ticket API and operator CLI run locally with the existing dependency-free Node.js service. The 1.4.0 service contract comes from README.md, docs/api.md, docs/operations.md and decisions 4–8. The November 21, 2026 feature request adds response deadlines.

## Requirements

### R-1 — Assign due times once

- Basis: November 21 request, “the time it was created plus the response time for its priority” and “set once”.
- New tickets store an ISO UTC deadline from their exact creation time. Urgent, high, normal and low add 4, 24, 72 and 168 elapsed hours by default. At 2025-09-01T08:00:00.000Z an urgent ticket is due at 2025-09-01T12:00:00.000Z.
- Operators can override each priority with a positive whole number of hours at startup. A settings change only affects deadlines assigned afterward. Priority edits, transitions and restart preserve existing due values. Verify through HTTP creation, edit, transitions and restart with changed settings.

### R-2 — Expose and find overdue tickets

- Basis: November 21 request, “Every ticket shows its due time as due” and “GET /tickets?overdue=true”.
- With DUE_TIMES=on, ticket objects show due in create, read, list, patch and transition responses. Operator table and details show due. The positional four-column raw listing remains safe for the weekly report.
- An exact overdue=true selects only active tickets whose due instant is strictly earlier than the current clock. At the due instant the ticket is excluded. Open and in-progress qualify; resolved and closed do not. Apply the predicate before cursor pagination and allow the existing filters to narrow the result. Verify with a manual clock and real HTTP requests.

### R-3 — Backfill before exposure and retain compatibility when disabled

- Basis: November 21 request, “tickets already in the production data file get due times too” and “until the DUE_TIMES environment variable is on, the service answers exactly as it does today”.
- The offline command fills missing due fields using each ticket's own created and stored priority. It preserves existing due values, IDs and next number, timestamps, audit, and outbox. A complete file is a no-op and failure leaves the input state intact. Only the existing file owner or its offline replacement writes.
- An enabled service with missing deadlines fails before listening, with the migration remedy in the error. A missing data file is the existing empty-store case. Any switch value other than on preserves projections and treats overdue as an unknown query. Verify against synthetic legacy, partly migrated and fully migrated files.

### R-4 — Roll back to 1.4.0

- Basis: November 21 request, “it must still start on the data file the new release wrote and show every ticket”.
- Version 1 remains readable by the actual 1.4.0 server, including after candidate writes. Compare ticket IDs and preserved operational state against the candidate file with a local baseline process. 1.4.0 saves drop new fields, so operators keep a due-bearing checkpoint before starting it. On re-upgrade, restore missing deadlines with the checkpoint using ID and creation time and fill any still missing deadlines for tickets created on 1.4.0. Keep changes made during rollback.

### R-5 — Preserve the existing service and test runner

- Basis: November 21 request, “Everything the service already does keeps working” and “Add node:test tests under test/”.
- Keep npm start, PORT behavior, CLI raw and weekly report, worker, audit, errors and lifecycle. npm test runs the unchanged baseline suite plus the new cases. Verify with Node and real file/HTTP boundaries.

## Non-functional requirements

Use Node >=22 standard library only. Migration and service share the one version-1 file and its atomic replacement. No additional service, network dependency, timer or audit side effect is needed. Preserve established CLI spacing, labels and error style. The production runbook documents shutdown, backup, activation and rollback, using locally verified synthetic cases.

## Retired

None.
