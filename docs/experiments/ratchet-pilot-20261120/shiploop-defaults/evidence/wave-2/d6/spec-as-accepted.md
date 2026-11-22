# Help desk ticket service
## Requirements
Basis for R-1 through R-6: the November 21, 2026 due-time request. Existing API, CLI and persistence contracts come from README, docs/api.md and decision 8.

### R-1 — Assign and keep deadlines
- Creating a ticket assigns a UTC ISO timestamp from its creation time plus 4/24/72/168 hours for urgent/high/normal/low. Verify the four defaults via HTTP and a manual clock.
- Default of November 21, 2026: positive whole hours from DUE_HOURS_<PRIORITY> override only that priority and invalid values identify the setting. Verify override loading and rejection through configuration tests.
- Priority changes, status changes and restarts with different hours retain the stored timestamp. Verify HTTP writes and restart with the same file.
### R-2 — Gate ticket output
- DUE_TIMES=on exposes due on ticket HTTP responses and human CLI output. Unset and other values preserve old responses and ignore overdue. Verify HTTP routes and CLI rendering.
- Raw CLI columns, weekly report, audit and outbox retain their existing contracts. Verify existing suite and raw CLI output.
### R-3 — List overdue tickets
- With the flag on, overdue=true selects only open or in_progress tickets whose deadline has passed. Default of November 21, 2026: strict cutoff, independently intersected with existing filters before pagination. Verify all statuses, equality and filtered pages through HTTP.
### R-4 — Backfill persistent data
- Default of November 21, 2026: startup fills only missing deadlines from each stored creation time and priority and persists them before serving even with the flag off. Restarts never rewrite an existing due value. Verify mixed legacy/new files and an immediate read after startup, with unchanged audit/outbox.
### R-5 — Read with release 1.4.0
- The unchanged 1.4.0 service starts on a real copy of the candidate-written file and returns all tickets with the old response shape. Verify using the baseline checkout and real HTTP before local delivery.
### R-6 — Preserve runtime and regression suite
- npm start uses PORT, with no dependencies. Keep existing tests as written and add node:test tests under test/ collected by npm test. Confirm test suite and startup.
## Non-functional requirements
- Atomic file write and single ownership remain as specified in decision 8. Migration must finish before listening and must preserve IDs, audit and outbox.
- Production deployment and its data verification are operator-owned. No UI, new access boundary or throughput target is introduced.
## Retired
None.
