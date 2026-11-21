## Fixed

- C-1, C-6, C-7, U-6 — The draft read a combined schedule setting, leaving the specified per-priority overrides unused. New deadlines use the ticket's own creation instant and the corresponding `DUE_HOURS_*` setting.
- C-9, C-10, C-11 — The schedule reader accepted startup without validating the specified variables. Each override now requires a positive whole decimal number and a representable deadline at startup. Invalid settings identify the variable and exit with status 2.
- C-13, U-2 — Priority edits recalculated the deadline. Ticket writes now preserve the assigned value through edits and transitions.
- C-34, U-4 — Overdue lists inherited ordinary lists' either-filter behavior. The overdue query now requires all supplied filters to match before pagination.
- C-42, C-43, C-44, C-45, C-46, U-7 — Startup added deadlines only to the in-memory store. Disabled startup now saves all missing deadlines from each record's own creation time and priority, preserving stored deadlines and existing ticket data.
- C-47, C-48 — Enabled startup could serve deadlines generated in memory from incomplete files. It now refuses incomplete files before listening and identifies how to prepare them.
- C-52, C-237 — A failed initial save left the new ticket, audit entry, notification and sequence increments in memory. Failed ticket writes now restore all of those effects.
- C-60, C-61, U-8 — Startup never published a prepared file or surfaced a preparation write failure. It now replaces the file atomically and reports a failed save before listening.
- C-63, C-64 — The reader accepted any parseable deadline string, including deadlines at or before creation. It now checks the canonical UTC representation and chronological order.
- C-65 — A calculated backfill overflow escaped as an unqualified range error. The startup diagnostic now identifies the file and ticket.
- C-71, C-72, C-73 — The operations runbook lacked production preparation, verification, rollback backup and offline recovery steps. It now explains how to recover deadlines by ticket ID while retaining the latest ticket, audit and outbox state.
- C-74, C-75, C-76 — The API and README omitted the deadline field, overdue query behavior and restart-based hour configuration. Those details are documented.
- C-214, C-216, U-12 — Human-readable CLI output omitted saved deadlines and startup logic used to calculate missing values while reading. The CLI now displays stored deadlines when enabled and the README describes the switch.
- C-231, C-232, U-15 — There were no new deadline tests under `test/`. Added five `node:test` tests discovered by the existing npm test command.
- C-234, C-235, C-236 — The storage decision and release metadata were missing. Added indexed decision 9 and bumped the package and changelog to 1.5.0.
- C-238 — Allocating an ID at the safe-integer limit could leave an invalid next counter. Both counters now reject allocations without usable successors. Pending notification deduplication still permits a resolution that needs no new event.
- U-9, U-11 — The draft recomputed legacy deadlines at startup without saving them. Preparation and regular saves now retain those assignments in version 1. The rollback runbook covers deadline recovery after a 1.4.0 save.

## Disputed

none

## Discoveries

- The draft used an undocumented `RESPONSE_HOURS` setting | Observable: Read `src/config.js` and `README.md` at the starting revision | Why: The settings checks changed `DUE_HOURS_*`, which the draft never read.
- A failed rename could strand a temporary file | Observable: Force a replacement error in the starting revision and inspect the data directory | Why: The original save path wrote the temporary file before rename and had no cleanup path.
