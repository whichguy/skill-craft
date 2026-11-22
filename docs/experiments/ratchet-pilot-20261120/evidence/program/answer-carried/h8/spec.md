## Use cases

### U-1: A requester opens a ticket to see when a response is due
Flow: With due times enabled, the requester submits a ticket using `POST /tickets`. With the default schedule, a ticket created at 2025-09-01T08:00:00.000Z is due at 2025-09-01T12:00:00.000Z if urgent (4 hours), 2025-09-02T08:00:00.000Z if high (24 hours), 2025-09-04T08:00:00.000Z if normal (72 hours), or 2025-09-08T08:00:00.000Z if low (168 hours). Omitting priority uses normal. The ticket returned by the API includes `due`.
Source: request

### U-2: A help-desk operator adjusts response hours to change future promises
Flow: The operator supplies different response hours without changing code. A ticket whose due time is set under the new schedule uses the new hours for its priority. Tickets that already had due times keep them, including when agents edit their priorities or reopen them.
Source: request

### U-3: An agent lists overdue tickets to find work that is past due
Flow: The agent calls `GET /tickets?overdue=true`. The list contains open and in-progress tickets whose due time is earlier than the service's current time. Resolved and closed tickets are excluded. The agent can narrow the list with existing filters or follow the next cursor. If no tickets match, the list is empty.
Source: request

### U-4: A production operator starts the service with due times enabled
Flow: The operator starts the service on the existing `DATA_FILE` with `DUE_TIMES=on`. During startup the service assigns missing due times to tickets in all states based on their own creation times and priorities, saves the file, and then serves. The API shows the saved due times. If startup preparation is interrupted, the operator can restart the service without moving due times that were already saved.
Source: answer

### U-5: A production operator rolls back to 1.4.0 to restore service
Flow: The operator stops the new process, starts release 1.4.0 on the same data file, then reads the tickets through the old API. Release 1.4.0 starts with the existing tickets and the tickets added by the new release.
Source: request

### U-6: A support lead runs the weekly report to keep counting tickets after the rollout
Flow: The operator's read-only CLI still reads the data file through `DATA_FILE` or `--data FILE`. The weekly report reads `list --raw` using its existing tab-separated columns and still counts tickets by status and priority, including tickets stored with due times.
Source: existing: README.md and docs/operations.md

### U-7: A maintainer runs the test suite to check the change
Flow: The maintainer runs `npm test`. It runs the unchanged existing tests and the new `node:test` tests under `test/`.
Source: request

## Clauses

### C-1: The service starts through `npm start` on its configured port.
Observable: On Node.js 22 or later, the operator can start the service without installing npm dependencies. `npm start` using `src/server.js` serves `GET /health` with 200 and `{"status":"ok"}` on the selected `PORT`. Unset or empty `PORT` uses 4180. An explicit port is a whole number from 0 through 65535, with 0 requesting an available port from the system.
Source: existing: README.md, package.json, src/config.js and src/server.js

### C-2: A newly created ticket receives a due time from its creation time and effective priority when due times are enabled.
Observable: With the default response hours, tickets created at 2025-09-01T08:00:00.000Z have due times of 2025-09-01T12:00:00.000Z for urgent (4 elapsed hours), 2025-09-02T08:00:00.000Z for high (24), 2025-09-04T08:00:00.000Z for normal (72), and 2025-09-08T08:00:00.000Z for low (168). A creation with no priority specified has the normal due time.
Source: request

### C-3: Help-desk operators can change the response hours for each priority without changing code.
Observable: Using the service's environment-based configuration, an operator can set a different response time for any of urgent, high, normal or low. Once the new settings apply, subsequent assignments use the configured hours for that priority. The default schedule applies when no override is supplied.
Source: request
Open: The build may choose the setting names and syntax. The requester decides which hour values the desk needs to support, including zero or fractions, any policy bounds, and whether changes need to take effect without a restart.

### C-4: An unusable response-hours setting is identified when the due-time operation that needs it fails.
Observable: A setting malformed under the supported syntax cannot silently yield a promise. An operator sees which setting caused a configuration failure. If an unusable setting prevents startup, the existing startup convention is a diagnostic on standard error and exit status 2.
Source: existing: README.md and src/server.js

### C-5: Assigned due times are valid instants under the service's timestamp convention.
Observable: A due time is expressed as ISO 8601 in UTC at the service's millisecond precision. The Node.js Date range runs from −8,640,000,000,000,000 through +8,640,000,000,000,000 milliseconds relative to the Unix epoch, inclusive. An assignment beyond either endpoint cannot succeed with a substituted instant.
Source: existing: docs/api.md and src/clock.js, with the Node.js Date bounds confirmed by a runtime probe
Open: The requester decides the desired operator recovery for a ticket or schedule whose calculated instant falls outside the representable range.

### C-6: When enabled, every ticket returned by the HTTP API includes its assigned due time as `due`.
Observable: The ticket in a successful create (201), individual read (200), patch (200), transition (200), or list item (200 for the page) contains `due` in addition to the existing ticket fields. This holds for open, in-progress, resolved and closed tickets wherever the endpoint returns them.
Source: request

### C-7: A ticket's assigned due time is fixed.
Observable: Re-reading the same ticket after changing the response hours, patching its priority or title, or changing its status returns the same due instant. This includes an allowed `resolved` to `open` transition.
Source: request

### C-8: Clients cannot supply `due` as a ticket write field.
Observable: Including `due` in a create, patch or transition body is an unknown-field error, HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-9: Until the service is started with `DUE_TIMES=on`, the HTTP API answers as in 1.4.0.
Observable: With the switch unset, empty or any value other than `on`, ordinary status codes and response bodies match 1.4.0 for the same requests and ticket state, including on a prepared file. Ticket responses lack `due`. The list ignores `overdue=true` and other `overdue` values as unknown parameters.
Source: request

### C-10: The enabled `overdue=true` listing selects tickets that are currently overdue.
Observable: At a fixed service time, each `open` or `in_progress` ticket with `due` strictly earlier than that time qualifies. Those two states are excluded when `due` is equal to or later than that time. `resolved` and `closed` are excluded even when their due time has passed. On a later request a ticket can qualify by passage of time alone, and a reopened ticket is evaluated against its original due time.
Source: request

### C-11: An enabled list request without `overdue` applies no due-time restriction.
Observable: With no other filters, `GET /tickets` can return tickets in all four states whether or not their due times have passed.
Source: implied: the request asks for overdue selection on `GET /tickets?overdue=true`
Open: The requester decides what supplied values other than `true` mean, including `false`, empty or unrecognized values, and how repeated `overdue` parameters are treated. Any rejection follows the existing HTTP 400 `invalid` error convention.

### C-12: The overdue condition remains required when an existing list filter is supplied.
Observable: With `overdue=true&priority=urgent` the returned tickets are overdue and currently urgent. With `overdue=true&status=open` they are overdue and currently open. With the overdue filter and `status=resolved` or `status=closed` alone, the result is empty.
Source: implied: U-3 and the filter contract in docs/api.md
Open: With both `status` and `priority`, docs/api.md promises a match on both but src/tickets/query.js currently matches either. The requester decides which combination of those two legacy filters to use in an overdue query. The overdue condition is mandatory either way. Ordinary listings keep their existing behavior.

### C-13: The overdue listing follows the existing cursor pagination contract for qualifying tickets.
Observable: The caller gets `{ "items": [...], "next": <cursor or null> }` in numeric ticket-ID order. Page size defaults to 20 and accepts whole numbers from 1 through 100, inclusive. Matching tickets fill the page up to that size even when nonmatching tickets come before them. Passing `next` back with the same filters continues after the last ID returned, using the conditions at the time of the new request. If no qualifying ticket remains, `next` is null. If the page has no matches, it is `{"items":[],"next":null}`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-14: Invalid existing listing arguments still use the existing error contract.
Observable: A status outside `open`, `in_progress`, `resolved`, `closed`, a priority outside `low`, `normal`, `high`, `urgent`, a limit outside the accepted whole numbers 1 through 100, or a malformed cursor produces HTTP 400 with `error.code` equal to `invalid`, including when `overdue=true`.
Source: existing: docs/api.md, src/tickets/query.js and src/pagination.js

### C-15: Preparation fills missing due times on existing production tickets.
Observable: Starting with a valid 1.4.0 file, the prepared data file holds a due time for every ticket, including resolved and closed tickets. For example, a stored high-priority ticket created at 2025-09-01T08:00:00.000Z has a default due time of 2025-09-02T08:00:00.000Z regardless of its saved `updated` time or the date of preparation. Preparation uses the ticket's saved priority and the response hours in effect for the assignment.
Source: request

### C-16: With `DUE_TIMES=on`, the service fills missing due times during startup before serving requests.
Observable: A startup with `DUE_TIMES=on` on a valid production file whose tickets lack due times succeeds without a separate operator preparation step. The service assigns each missing due time from that ticket's own creation time and saved priority using the configured response hours. This includes tickets written after an earlier startup if they still lack a due time. The service saves the updated file before serving requests, and every ticket in the file must have a valid saved due time before the service serves due-time responses. Missing due times alone never cause startup to fail. A file with no tickets has no ticket due times to fill.
Source: answer
Open: The requester decides whether writes must remain available during preparation. The build may choose how completion is reported. The requester decides when dues are first assigned for tickets written while responses still use the old contract.

### C-17: A ticket's saved due time survives reuse of the data file by the new release.
Observable: After a ticket with a due time is saved, a later restart preserves that due time even under different response-hour settings. Saves made by the new release with due responses disabled, including ticket writes, outbox saves and shutdown, preserve previously saved due times.
Source: implied: U-2 and U-4 require a due time to be set once across normal operations

### C-18: Due-time preparation preserves the recoverability of the production data file.
Observable: If preparation cannot complete, the file remains a complete readable state, with any committed due times intact. An operator can correct the failure and retry for remaining tickets. If the operation fails before committing a replacement, the previous file is still readable. A file unusable under the existing data-file checks is still refused at startup with a diagnostic identifying the file and the problem.
Source: existing: docs/operations.md and docs/decisions/0008-json-data-file.md
Open: The requester decides how an already stored but malformed due value is to be repaired. A malformed value cannot establish readiness.

### C-19: Preparation preserves the existing ticket inventory.
Observable: Comparing the file before and after successful preparation shows the same IDs with the same titles, requesters, priorities, statuses and creation times. A ticket created after preparation receives the next sequential ID without reusing any existing ticket number.
Source: implied: U-4 prepares the existing tickets in place while preserving the numbering rule in docs/decisions/0002-prefixed-sequential-ids.md
Open: The requester decides whether adding a missing due time should change `updated` as an administrative edit.

### C-20: Due-time assignment preserves the existing audit history.
Observable: Audit entries recorded before preparation are still returned oldest first with their original sequence numbers, actors, timestamps and changes. With due responses disabled, audit queries still return their 1.4.0 responses.
Source: existing: docs/decisions/0007-append-only-audit-log.md and docs/api.md
Open: The requester decides whether assigning `due` during preparation should produce audit entries visible after activation, and whether new ticket creation entries should show `due` when enabled.

### C-21: Due-time preparation leaves existing notification obligations intact.
Observable: With the worker paused and no other operations occurring, the pending, sent and dead entries returned by `GET /admin/outbox` are the same before and after preparation. Assigning deadlines to old tickets does not enqueue new ticket-received or ticket-resolved notifications.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-22: Saving a new ticket with due times enabled retains the existing whole-state save guarantee.
Observable: With `DATA_FILE` configured, a successful creation has its ticket, due time, creation audit entry and corresponding outbox event available after restart. An interruption during a save leaves a readable file with the whole state before or after that save.
Source: existing: docs/decisions/0006-notification-outbox.md, docs/decisions/0007-append-only-audit-log.md and docs/decisions/0008-json-data-file.md

### C-23: The existing memory-only startup mode remains available.
Observable: Without `DATA_FILE`, the service can still start with due responses disabled and serve tickets held only for that process's lifetime.
Source: existing: README.md and docs/decisions/0008-json-data-file.md
Open: The requester decides whether `DUE_TIMES=on` is also supported without a data file outside production. The production readiness rule concerns the production data file.

### C-24: Release 1.4.0 can start on the same data file last written by the new release.
Observable: After stopping the new process, an operator can point an unmodified 1.4.0 process at that file and start it without transforming or restoring the file. The file satisfies the 1.4.0 version 1 reader, including after the new release has served and saved tickets with due times.
Source: request

### C-25: Release 1.4.0 shows every ticket from the file used for rollback.
Observable: After the rollback in U-5, paging through the ordinary API list returns every ticket saved before rollback, including tickets carried over from the old release and tickets created by the new release. Individual reads show their 1.4.0 ticket fields.
Source: request
Open: The requester decides whether a later upgrade must recover the same due times after 1.4.0 itself has rewritten the file. Its ticket serializer discards fields it does not recognize.

### C-26: Due times leave the ticket lifecycle available under its existing rules.
Observable: Allowed moves are `open` to `in_progress`, `in_progress` to `resolved`, and `resolved` to `closed` or `open`, whether or not a ticket is overdue. Other moves between known states return HTTP 409 `conflict`, an unknown target returns 400 `invalid`, and a closed ticket remains closed.
Source: existing: docs/api.md and src/tickets/states.js

### C-27: Existing ticket patches retain their change semantics.
Observable: An accepted patch changes the supplied title or priority fields that differ, with their existing `ticket.updated` audit changes. A patch that repeats the current values leaves `updated` and the audit history as they were. Patching a `closed` ticket returns 409 `conflict`.
Source: existing: docs/api.md and test/api.test.js

### C-28: Existing requester notifications still follow their original triggers.
Observable: Creation still queues the ticket-received notification and resolution still queues the ticket-resolved notification under the existing pending-key deduplication rule. Seeing a due time, passing it, or listing overdue tickets adds no requester notification.
Source: existing: docs/api.md and docs/decisions/0006-notification-outbox.md

### C-29: The operator CLI can read tickets from a due-time-bearing file.
Observable: `node bin/tickets.js` with `DATA_FILE` or `--data FILE` can still run `show ID` for an existing ticket or `list` with its existing status and priority options on the new release's file. These commands still leave the file unchanged.
Source: existing: README.md and docs/operations.md
Open: The requester decides whether the human-readable CLI list or detail view should display due times and whether any such display follows the HTTP feature switch.

### C-30: The raw CLI output retains its existing tab-separated fields for scripts.
Observable: `list --raw` still yields one line per selected ticket with `id`, `status`, `priority` and `title` at positions 1 through 4 in the documented tab-separated output.
Source: existing: README.md and bin/tickets.js

### C-31: The weekly report still counts tickets stored with due times.
Observable: The same tickets produce the same `total`, `byStatus` and `byPriority` counts from `scripts/weekly-report.js --json` before and after due times are assigned.
Source: existing: README.md and scripts/weekly-report.js

### C-32: Production operators can stop the service cleanly with `SIGTERM`.
Observable: The worker stops, requests in flight finish, and the service saves its state before exiting. A restart on the file after the stop still has the saved tickets.
Source: existing: docs/operations.md and src/server.js

### C-33: The existing tests pass as written.
Observable: The pre-change tests are unchanged and all pass when run through `npm test`.
Source: request

### C-34: The normal test command covers the new due-time behavior.
Observable: `npm test` discovers and passes new `node:test` tests under `test/` covering the requested due-time behavior, including production preparation, activation and rollback compatibility.
Source: request
