Verdict: reject
## What must be true
- Run npm start with PORT=0 and GET /health to receive 200 with status ok, then stop cleanly with SIGTERM. | held
- With DUE_TIMES on, create one ticket per priority and one with priority omitted to see due 4, 24, 72 or 168 hours after created as applicable. | held
- Change response hours through configuration, then create a ticket to see the new deadline and retrieve an earlier ticket to see its original deadline. | held
- Change a ticket's priority and move it through the lifecycle to see the original due on PATCH, transition, GET detail and GET list. | held
- List overdue tickets with past and future deadlines across all four statuses to see only past open and in-progress tickets, then page through the filtered results and combine the filter with status or priority. | held
- Backfill a 1.4.0 data file with tickets of each priority and status, then inspect the saved deadlines and restart with changed hours to verify that deadlines, ticket timestamps, audit and outbox are preserved. | held
- Start with DUE_TIMES unset, off and another value and compare ticket responses and overdue query handling to 1.4.0, including after the file has due times. | held
- Attempt to enable production due times on a populated file missing deadlines and verify that enabled responses begin only after every deadline is persisted. | held
- Create a ticket during the disabled rollout window, change its priority and response hours, then enable due times and check that its deadline uses the priority and hours from creation. | broken
- Start release 1.4.0 on the enabled release's saved file and list every ticket, checking audit, outbox and sequential IDs. | held
- Create, read, update and transition tickets and verify the old fields, lifecycle conflicts, no-op update behavior, validation, status codes and error envelopes. | held
- List with status and priority separately and together, paginate by id with next cursors and check ignored query parameters and invalid filter values as in 1.4.0. | held
- Inspect audit history and the outbox after create, edit, resolve and reopen, then run the worker to verify notification delivery and restart to check persisted state. | held
- Run CLI list, list with filters, list --raw and show through --data or DATA_FILE, check exit codes and verify that the file stays read-only. | held
- Run the weekly report in text and JSON modes and check totals by status and priority from the raw columns. | held
- Start with unusable existing settings or malformed data and verify startup fails with diagnostics. | held
- Run npm test to verify the unchanged 1.4.0 tests and the new node:test coverage both pass without npm dependencies. | held
- After 1.4.0 writes to the rollback file, bring the new release back with changed hours and check how it handles the deadlines stripped by the 1.4.0 writer. | held
- Prevent startup from replacing an unprepared data file and check that the service exits before listening or altering the original. | held
- Set response hours to a duration that cannot produce a valid deadline at any supported creation instant and verify that startup refuses the unusable setting. | broken
## Findings
- A new ticket's deadline uses its creation-time priority and response hours, and the flag controls when clients see it | A ticket created while the flag is off has no saved deadline, so activation uses a later priority and schedule | Probe: With a prepared DATA_FILE, start with PORT=0 DUE_TIMES=off DUE_HOURS_URGENT=4 DUE_HOURS_HIGH=24, POST /tickets with priority urgent (201, T-0002, created 2026-11-22T02:24:04.338Z), then PATCH /tickets/T-0002 to high (200). The saved row had no due. Restart with DUE_TIMES=on DUE_HOURS_URGENT=9 DUE_HOURS_HIGH=11. GET /tickets/T-0002 returned 200 with due 2026-11-22T13:24:04.338Z, 11 hours after creation. The creation-time schedule gave 2026-11-22T06:24:04.338Z.
- The service refuses unusable configuration at startup and names the setting | The service accepts an hours value that exceeds the entire Node.js timestamp span, reports healthy, and fails every high-priority creation | Probe: PORT=0 WORKER_INTERVAL_MS=0 DUE_TIMES=on DUE_HOURS_HIGH=4800000001 node src/server.js started. GET /health returned 200, POST /tickets with priority high returned 500 with error.code internal, and POST /tickets with priority normal returned 201. The configured high duration is 17,280,000,003,600,000 ms, greater than the 17,280,000,000,000,000 ms between the earliest and latest representable timestamps.
## Decisions made for the requester
- Read one environment override per priority at startup and support positive whole hours | Use a single schedule setting, reload without restart, or support fractional hours
- Reject a ticket or backfill whose creation date plus an otherwise usable duration exceeds the timestamp range | Clamp the resulting deadline to the nearest representable timestamp
- Accept a single exact overdue=true or overdue=false when enabled and return 400 for other or repeated values | Ignore unrecognized values or use the first repeated value
- Apply overdue eligibility before the existing union of status and priority filters | Require both status and priority to match on overdue listings
- Prepare synchronously at enabled startup and permit enabled operation without a data file for local use | Require a separate preparation command or require a file for every enabled instance
- Assign deadlines without adding an audit field or a backfill audit entry | Record the first deadline assignment in ticket history
- Refuse a malformed saved deadline at enabled startup and allow operators to restore the value from a known-good copy | Treat a malformed deadline as missing and assign a replacement
- Re-prepare missing due values after an unmodified 1.4.0 writer strips them from the rollback file | Preserve the assigned values in rollback-compatible storage across 1.4.0 writes
- Keep due in HTTP ticket responses and retain the human-readable CLI formats | Display due in the CLI table or show output
