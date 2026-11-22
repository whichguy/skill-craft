Verdict: reject
## What must be true
- Start the service with npm start on PORT and call GET /health. | held
- Enable due times and create tickets of each priority including omitted priority, then verify their due timestamps equal created plus 4, 24, 72 and 168 hours as applicable. | held
- Change response hours through configuration alone and verify new tickets use the new hours while existing tickets keep their original due times after restart. | held
- Change a ticket's priority and move it through the lifecycle, checking due in create, detail, list, patch and transition responses. | held
- Query overdue tickets across open, in-progress, resolved, closed and future tickets and verify only the past-due open and in-progress tickets appear. | held
- Apply existing list filters and cursor pagination to an overdue listing and verify the result is restricted by the overdue condition before pagination. | held
- Upgrade a file written by 1.4.0 and verify due is stored for every legacy ticket using each ticket's own creation time and priority, with values stable across repeated backfill or restart. | held
- Prepare a production data file for activation and verify that due times cannot be exposed before all its tickets have stored due times. | held
- With DUE_TIMES unset or other than on, check that normal API responses omit due and that the previously ignored overdue query leaves results alone, even with a prepared file. | held
- Start the unmodified 1.4.0 service against a data file written by the delivery and list every legacy and newly created ticket. | held
- Check that the ordinary listing still sorts by id, supports individual filters and cursors, and combines status and priority as the running 1.4.0 service does. | held
- Check that no-op updates leave updated and audit alone, that audit actors and transition rules still work, and that unknown body fields get the usual error envelope. | held
- Create and resolve a ticket and check the audit and outbox, notification delivery, and persistence across restarts. | held
- Use the CLI to list and show tickets with history, check status and priority filtering, verify its raw columns and weekly report, and verify those commands leave the data file alone. | held
- Run the unchanged existing tests together with the added node:test coverage through npm test. | held
- Roll back to 1.4.0, let it save, then re-enable due times with different configured hours and verify that tickets which had due times keep them. | broken
- Start with a documented response-hours value and verify that startup and ticket creation agree on whether the setting is usable. | broken
## Findings
- Once a ticket has a due time, later changes to the response schedule or priority must leave it fixed. | A 1.4.0 save discards the only stored copy of each deadline, so re-enabling the delivery can assign a different deadline to the same ticket. | Probe: Start the delivery with `PORT=0 DATA_FILE=<fixture> DUE_TIMES=on npm start`, create urgent T-0006 and patch it to low. `GET /tickets/T-0006` still showed `2026-11-22T06:26:45.904Z`. Start unmodified 1.4.0 on the same file with `PORT=0 DATA_FILE=<fixture> node src/server.js`. `GET /tickets` showed all 12 tickets. Creating a ticket under 1.4.0 rewrote the file without any `due` fields. Restart the delivery on the same file with `DUE_TIMES=on DUE_HOURS_LOW=192`. `GET /tickets/T-0006` returned `2026-11-30T02:26:45.904Z`.
- Operators must be able to configure response hours, and the existing service refuses unusable configuration values at startup with the variable named. | The documented maximum is accepted at startup even though it cannot produce a representable due time for any ticket. A normal urgent create then fails. | Probe: Run `PORT=0 WORKER_INTERVAL_MS=0 DUE_TIMES=on DUE_HOURS_URGENT=9007199254740991 node src/server.js` with `DATA_FILE` unset. The service bound a port. `POST /tickets` with `{"title":"Example ticket","requester":"demo@example.com","priority":"urgent"}` returned HTTP 500 with `{"error":{"code":"internal","message":"internal error"}}`.
## Decisions made for the requester
- Read one positive whole-hour environment override per priority at startup. | Read all four values from a schedule file or accept fractional hours.
- Prepare missing deadlines in one enabled startup before binding the port, and allow enabled memory-only use. | Require a separate preparation command for persistent deployments and require a data file whenever the flag is on.
- While the feature is off, retain saved deadlines and defer assignment for new tickets until the next enabled startup. | Assign and save hidden deadlines for new tickets while the feature is off.
- When enabled, accept one exact `overdue=true` or `overdue=false` and return 400 for other supplied forms. | Ignore unrecognized forms or use the first value when the parameter is repeated.
- Apply the existing OR between status and priority within the overdue result. | Require both filters to match within the overdue result.
- Exclude deadline assignment from ticket audit entries and notifications. | Record assignment on creation and backfill in the audit log.
- Refuse enabled startup on a malformed saved deadline with a file and ticket diagnostic. | Treat malformed values as missing and recalculate them.
- Refuse deadline arithmetic overflow instead of clamping the written timestamp. | Clamp at the last representable timestamp.
- Store the deadline as an optional version-1 ticket field. | Use a separate deadline archive compatible with 1.4.0.
- Keep the human CLI table and show output independent of the feature flag, with deadlines visible through HTTP. | Add deadlines to the human CLI output when enabled.
