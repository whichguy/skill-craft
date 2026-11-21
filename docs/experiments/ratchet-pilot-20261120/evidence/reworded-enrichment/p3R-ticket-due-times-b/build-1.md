## Done

- C-1–C-2. Kept the dependency-free Node.js service entry point and existing `PORT` rules. Verified `npm start` and `GET /health` on an OS-selected port.
- C-3–C-6. Added the default schedule, startup environment overrides with configuration diagnostics, and exact elapsed-hour arithmetic through the inclusive Node.js Date bounds.
- C-7–C-10. Exposed `due` on every enabled ticket response, including no-op patches and all lifecycle states. Write bodies still reject the field. Assigned deadlines survive ticket edits, schedule changes and restarts.
- C-11–C-12. Preserved 1.4.0 HTTP responses and query behavior unless `DUE_TIMES` is exactly `on`, including when the file already holds deadlines.
- C-13–C-18. Filtered by active status and a strictly elapsed deadline using one clock sample per overdue request. Applied the restriction before numeric ordering and cursor pagination.
- C-19–C-22. Prepared missing deadlines from saved creation times and priorities before listening. Enabled creates commit the ticket and its deadline before returning success. Saved deadlines survive off-mode writes, worker saves, shutdown and later preparation. Ticket fields and the numbering sequence carry through preparation.
- C-23–C-24. Preserved existing audit and outbox records and counters through preparation. The usual create and resolve effects still run, including pending notification deduplication.
- C-25–C-27. Reused the version-1 whole-file rename. Exercised a failed preparation and retry against the intact file, a failed enabled creation that left the old file and live state available, and startup refusal for invalid data with exit status 2.
- C-28. Started unmodified 1.4.0 from local commit `ada051d` with `npm start` against the prepared file after the new service shut down. Paged through all 27 tickets, including three created by the new service, and fetched every ticket by ID to compare its legacy fields.
- C-29–C-32. Verified CLI list, show and history on both file generations without writes. Checked the four raw columns across the CLI's internal page boundary and verified the weekly status and priority totals.
- C-33–C-34. `npm test` passed all 129 tests, including 12 added `node:test` cases. The original test files are unchanged. Updated the README, API and operations docs, changelog and decision records.

## Not done

none

## Discoveries

- C-4 accepts positive safe whole hours through `9007199254740991` across the four `DUE_HOURS_*` settings, with defaults for unset or blank values. | Observable: Restart enabled with `DUE_HOURS_URGENT=6` and create an urgent ticket. | Why: The existing integer settings already define whitespace and range handling. The resulting deadline has its own Date bound.
- C-6 treats overflow as an internal error on create and a startup data-file error during preparation. | Observable: A deadline exactly at the maximum Date instant succeeds. One millisecond beyond gives HTTP 500 on create or exit status 2 on preparation with the ticket identified. | Why: A timestamp beyond the supported range cannot preserve the promised duration.
- C-14 keeps the union of status and priority when both are supplied and applies overdue eligibility to that union. | Observable: An overdue in-progress urgent ticket qualifies for `?overdue=true&status=open&priority=urgent`. | Why: The 1.4.0 implementation uses a union even though its API docs described an intersection.
- C-15 accepts one exact `true` or `false` when enabled. | Observable: `overdue=false` returns the ordinary listing. An empty, repeated or other value returns 400 `invalid`. | Why: The ordinary listing remains available and malformed filter requests get the existing validation envelope.
- C-20 prepares deadlines on enabled startup and supports enabled memory-only operation. | Observable: With `DATA_FILE` set, the saved deadlines are present by the listening log. Without it, deadlines last for the lifetime of their in-memory tickets. | Why: Service construction can commit preparation while the listener and worker are still stopped.
- C-23 leaves assignment out of audit history. | Observable: Preparation appends no entries and an enabled creation entry contains the existing ticket fields. | Why: Assignment is part of the stored ticket and the legacy history keeps its existing shape.
- C-27 treats a present malformed deadline as a data-file error during enabled startup. | Observable: A saved `due: null` fails with exit status 2 and a file-and-ticket diagnostic. Off mode preserves the value, and enabled startup can be retried after restoring the saved timestamp. | Why: Treating it as missing could silently replace an earlier assignment.
- C-28 reassigns missing deadlines after any 1.4.0 rewrite. | Observable: A graceful shutdown of 1.4.0 strips `due`. Subsequent enabled startup prepares those records from the ticket data and hours then in effect. | Why: The 1.4.0 writer keeps only the fields it knows, even though it can read and serve all tickets.
- C-29 keeps the existing CLI display independent of the HTTP flag. | Observable: The table and `show` output use the existing fields on a prepared file. | Why: The CLI already selects its display fields separately from file parsing.
- C-33 had an intermittent hang in an initial suite run before due-time behavior was wired. | Observable: The original audit API test reported a failure and its Node test process stayed alive until stopped by PID. A focused rerun and the full 129-test run passed. | Why: The initial run did not produce a failure diagnostic, so the source of the hang remains unverified.
