# Help desk ticket service

## Requirements

### R-1 Durable response deadlines

Basis: 2026-11-21 request S2–S4 and S6. Sources: README Configuration, docs/api.md Times, docs/operations.md Data file.
- At 2025-09-01 08:00 UTC, create urgent, high, normal and low tickets. Verify due timestamps at +4, +24, +72 and +168 elapsed hours on create and subsequent reads. Apply a deployment override and verify that new tickets use it.
- Create high, change it to urgent, restart with different hours and verify the original deadline. Inputs cannot supply or edit a deadline.
- Load an older file with a ticket created 2025-09-01 08:00 UTC and priority high. Verify 2025-09-02 08:00 UTC is on disk before the listener is available. Restart with different settings, verify the deadline and pre-existing records remain, and verify a complete file is not rewritten during initialization.

### R-2 Visibility and overdue listing

Basis: 2026-11-21 request S5 and S7. Sources: docs/api.md Endpoints; existing behavior at release 1.4.0; README Command line.
- With DUE_TIMES=on, all existing ticket response shapes include the ISO UTC due field. CLI human list and detail display deadline data. Raw CLI fields retain their four original columns.
- For overdue=true, advance the injected clock to one millisecond past a ticket's deadline. Only open or in_progress tickets with earlier deadlines qualify. Check equality, future dates, resolved and closed, reopening, filter combination and cursor pages via HTTP.
- With the flag absent or any value other than on, preserve 1.4.0 ticket output and ignore overdue. Verify that file persistence still prepares the deadlines. Audit and notification behavior retain their existing contract.

### R-3 Backward-readable production rollout

Basis: 2026-11-21 request S7–S9. Sources: docs/operations.md, decision 8, package.json at 5d2954c.
- Start exact release 1.4.0 on the upgraded disposable file. HTTP listing and detail return every pre-existing and newly created ticket, without requiring file conversion.
- Starting and writing on rollback is supported with a single process owner. Save the upgraded snapshot before rollback, because 1.4.0 strips deadline metadata when it writes. On roll-forward before restarting, restore deadlines from that snapshot against the current file, keeping intervening ticket records and filling tickets created under 1.4.0. Verify this sequence at the file and startup boundaries.
- Production operator owns actual rollout. Local release verification uses a disposable file, loopback and the exact 1.4.0 code.

### R-4 Existing functionality and verification

Basis: 2026-11-21 request S1, S9–S10. Sources: README, CONTRIBUTING, package.json.
- Node 22+ built-ins only. npm start respects PORT, npm test runs all legacy tests and new node:test coverage with the existing tests unchanged. Exercise the CLI and report contract against the upgraded file.

## Non-functional requirements

Retain the single-writer atomic snapshot, read-only CLI and one clock read per overdue query. Preserve existing error envelopes. No new graphical interface, network service, performance target, or personal data is required. Dates are UTC instants and remain in the ticket state for the life of the record.
