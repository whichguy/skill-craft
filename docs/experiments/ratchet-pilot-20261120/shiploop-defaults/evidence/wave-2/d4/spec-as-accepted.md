# Help desk ticket service specification

## Requirements

### R-1 Assign a due time once

Basis: 2026-11-21 response-time request. New ticket due is its persisted created time plus 4 urgent, 24 high, 72 normal or 168 low elapsed hours. Default of 2026-11-21: use individual positive whole-hour SLA_HOURS_<PRIORITY> environment settings, with unset values using the defaults and invalid values naming the setting. A priority update, lifecycle change, config change, or feature toggle retains the assigned value. Verify with deterministic HTTP creates and a file-backed restart.

### R-2 Expose due times and filter overdue tickets

Basis: 2026-11-21 response-time request and docs/api.md listing contract. With DUE_TIMES=on, ticket reads, create, edit, transition and lists expose ISO due. Default of 2026-11-21: only literal overdue=true narrows a list, and overdue means open or in progress with a due instant strictly before now. Preserve the status/priority OR filter, sort, cursor and envelope. Verify equality, resolved and closed exclusions, and combined filters with loopback HTTP.

### R-3 Backfill before activation

Basis: 2026-11-21 response-time request and data-file decision 8. Fill absent dues from existing created and priority without modifying audit, outbox, ticket IDs, update times or assigned values. Default of 2026-11-21: use a one-shot offline command and catch up missing dues before enabled startup listens. Verify file read-back, repeated backfill, and restart with a changed policy. Off-mode API responses stay in the baseline shape and ignore overdue. The single service process or the offline operator owns the data file at any one time.

### R-4 Readability in rollback

Basis: 2026-11-21 response-time request. Actual 1.4.0 must start using the new file and list its existing and newly created tickets. Its writer discards the optional due field, so operator instructions preserve the due-bearing copy and protect later ticket changes during re-upgrade. Verify against a copy using the unchanged 1.4.0 executable.

### R-5 Preserve existing behavior and tests

Basis: 2026-11-21 response-time request and CONTRIBUTING.md. Preserve dependency-free Node 22+ service, npm start and PORT, CLI and raw report contracts, and the unchanged suite. Add node:test coverage under test/ and run npm test.

## Non-functional requirements

The version-1 file remains atomically replaced and single writer. Feature work adds no service, timer, dependency or new personal data. The existing CLI retains the documented table and raw contracts. No new graphical interface is introduced.

## Retired

None.
