## Use cases

### U-1: A requester opens a ticket to get a response deadline
Flow: With `DUE_TIMES=on`, the requester sends `POST /tickets` and receives a ticket with `due`. By default, a ticket created at `2025-09-01T08:15:00.000Z` is due at `2025-09-01T12:15:00.000Z` for urgent, `2025-09-02T08:15:00.000Z` for high, `2025-09-04T08:15:00.000Z` for normal or `2025-09-08T08:15:00.000Z` for low.
Source: request

### U-2: A help-desk lead changes response hours for future deadlines
Flow: The lead changes the configured hours without changing code. An agent opens another ticket at the affected priority and sees the new interval reflected in its `due`. The agent reads an already assigned ticket after the configuration change or after changing that ticket's priority and sees its original `due`.
Source: request

### U-3: An agent finds overdue work to decide what to handle next
Flow: With due times enabled, the agent calls `GET /tickets?overdue=true` and pages through open and in-progress tickets past their deadlines. Resolved and closed tickets stay out of the result. The agent can narrow the result by an existing filter or read a ticket directly to see its deadline.
Source: request

### U-4: A production operator enables due times on the existing data file
Flow: While the feature is disabled, requests have their 1.4.0 behavior. The operator starts the service with `DUE_TIMES=on` on the existing `DATA_FILE`. The service assigns each ticket missing a deadline one based on its own creation time and priority, saves the deadlines, and then serves requests. The operator verifies the deadlines through the API. A restart keeps the assigned values.
Source: answer

### U-5: A production operator rolls back to 1.4.0 to restore service
Flow: The operator stops the new release using the existing process controls and starts 1.4.0 on the same file the new release wrote. The service starts and the operator can list every ticket, including tickets created by the new release.
Source: request

### U-6: An operator or support lead reads the saved tickets with existing tools
Flow: The operator uses `bin/tickets.js` to list or show tickets from the data file. The support lead runs the weekly report, which reads the tab-separated `id`, `status`, `priority` and `title` from `list --raw`, and gets the existing counts.
Source: existing: README.md

### U-7: A maintainer runs the service and its test suite
Flow: The maintainer starts the dependency-free Node.js service with `npm start` on a port selected through `PORT`. They run `npm test`, which runs the original tests and new `node:test` tests under `test/`.
Source: request

## Clauses

### C-1: A new ticket's deadline is its recorded creation time plus the configured elapsed hours for its priority at creation
Observable: With due times enabled, subtract the `created` instant from `due` on a successful `POST /tickets` response. With default settings, the difference is 4 hours for `urgent`, 24 for `high`, 72 for `normal` and 168 for `low`.
Source: request

### C-2: A new ticket with no supplied priority uses the normal response interval
Observable: With due times enabled, omit `priority` in a valid create request. The returned priority is `normal` and `due` is `created` plus the configured normal interval, 72 hours by default.
Source: existing: docs/api.md

### C-3: Operators can configure the response hours for each priority without changing code
Observable: Start the same release with an environment override for one priority, such as 6 hours for urgent. A newly created urgent ticket is due 6 hours after creation. Priorities left at their defaults retain their respective 24, 72 and 168 hour intervals. Unset or empty settings use their defaults.
Source: implied: U-2 and the environment settings convention in README.md
Open: The requester would settle any required configuration interface details, including variable names, whether the values are supplied together, and whether hours may be fractional or zero. Use a supported positive whole-hour override when checking this clause.

### C-4: An unusable response-hours setting is reported at startup when the service needs that setting
Observable: Supply a value outside the release's supported response-hours settings on a startup that uses the schedule. The process refuses to start with a diagnostic naming the setting. Correct the setting or use its default to remove that configuration error.
Source: existing: README.md
Open: The request supplies no minimum, maximum or numeric syntax for overrides. The requester would settle any product limits within the timestamp range, and whether the schedule must be validated on a disabled startup that does not prepare deadlines.

### C-5: A ticket returned by the enabled API has its assigned deadline in `due`
Observable: Inspect the ticket in a 201 create response, a 200 detail, patch or transition response, or an item in a 200 list response with due times enabled. Each has `due` as an ISO 8601 UTC timestamp in the same convention as `created` and `updated`.
Source: request

### C-6: The API treats `due` as a server-assigned field
Observable: Include `due` in an otherwise valid create, patch or transition body. The API rejects it with HTTP 400 and the existing `error.code` of `invalid`, leaving the attempted ticket creation or change unapplied.
Source: existing: docs/api.md

### C-7: Changing the configured hours leaves an assigned deadline unchanged
Observable: Record the `due` of a saved ticket, then run the new release on that data with a different response interval for its priority. Reading the original ticket still returns the original `due`.
Source: request

### C-8: Changing a ticket's priority leaves its assigned deadline unchanged
Observable: Patch a non-closed ticket from one priority to another with a different response interval. The 200 response and later reads show the new priority with the original `due`.
Source: request

### C-9: A lifecycle transition leaves the assigned deadline unchanged
Observable: Follow `open → in_progress → resolved`, then either reopen to `open` or close from `resolved`. Read the ticket after each accepted move and find its original `due`. A reopened ticket uses that same deadline for overdue queries.
Source: implied: the deadline is set once in the request

### C-10: An enabled overdue query selects tickets by their current status and assigned deadline
Observable: Call `GET /tickets?overdue=true` with the feature enabled. A ticket qualifies when its current status is `open` or `in_progress` and its `due` is strictly earlier than the service's time when the query is evaluated. At exactly `due` it does not qualify. Future deadlines and the statuses `resolved` and `closed` are excluded. An active ticket can start qualifying as time passes without a ticket edit.
Source: request

### C-11: Omitting `overdue` leaves the enabled listing unrestricted by the deadline
Observable: With the feature enabled, an unfiltered `GET /tickets` can return tickets in all four statuses with past or future deadlines.
Source: implied: U-3 offers an opt-in listing filter
Open: The requester would settle how the enabled listing handles values other than the single literal `true`, including `false`, an empty value, other spellings and repeated or conflicting values. If a value is rejected as malformed, the existing HTTP 400 `invalid` envelope applies.

### C-12: The overdue filter intersects with an existing listing filter
Observable: With the feature enabled, add a valid `status` or `priority` filter to `overdue=true`. The results meet the overdue condition and that filter. In particular, `status=resolved` and `status=closed` each produce an empty result.
Source: existing: docs/api.md
Open: For enabled queries that send both `status` and `priority`, the requester would resolve the discrepancy between the intersection documented in docs/api.md and the union implemented in src/tickets/query.js. With `overdue=true`, either interpretation must exclude tickets that are not overdue.

### C-13: The overdue listing pages over matching tickets in numeric ticket ID order
Observable: On a stable set of matches, `GET /tickets?overdue=true` returns a 200 page as `{ "items": [...], "next": ... }`. Each page has up to `limit` matching tickets, 20 by default. Limits of 1 and 100 are accepted, while values outside 1–100 and values that are not whole numbers return HTTP 400 `invalid`. Reuse `next` as the opaque `cursor` with the same filters to continue after the last ID served. The last page has `next: null`. A query with no matches yields `{ "items": [], "next": null }`.
Source: existing: docs/api.md

### C-14: The disabled service gives the same API answers as 1.4.0
Observable: With `DUE_TIMES` unset, empty or set to a value other than `on`, send the same requests against equivalent ticket, audit and outbox state. Ticket responses have the old fields without `due`. The `overdue` parameter is ignored, even at `true`, just as an unrecognized query parameter was in 1.4.0. Existing status/priority results, pagination, status codes and error envelopes remain as in 1.4.0. The same holds when there are already deadlines in the file.
Source: request

### C-15: With `DUE_TIMES=on`, the service assigns missing deadlines and saves them before serving
Observable: Start the service with `DUE_TIMES=on` on a usable `DATA_FILE` containing tickets without deadlines, with no separate preparation step. Missing deadlines alone never cause startup to be refused. Before serving requests, the service saves a deadline for every ticket missing one, including tickets from 1.4.0 and tickets created while due times were disabled. It calculates each deadline from the ticket's own `created` and priority at assignment, using the configured response interval for that priority. This includes `open`, `in_progress`, `resolved` and `closed` tickets. The date of the deployment and each ticket's `updated` are not the basis for the calculation. An empty set of tickets needs no deadlines assigned.
Source: answer

### C-16: Production due-time responses require a data file with all ticket deadlines saved
Observable: During production rollout, a client cannot receive an enabled ticket view or overdue page while the production file still has tickets without deadlines. After the file has all its deadlines and the service runs with `DUE_TIMES=on`, clients can use both views.
Source: request

### C-17: Retrying preparation preserves deadlines already assigned by the new release
Observable: Repeat preparation on a file that already has assigned deadlines, including a file with both assigned and missing deadlines. At successful completion, the existing values are unchanged and every previously missing deadline has been assigned once.
Source: implied: the set-once rule and U-4

### C-18: Interrupted preparation leaves a recoverable data file
Observable: If preparation fails or is interrupted while saving, the production file still represents a complete readable state from before or after the save. The operator can correct the cause and retry without dropping tickets or replacing already saved deadlines. An incomplete preparation is not reported as ready to expose due times.
Source: existing: docs/operations.md

### C-19: An unrepresentable calculated deadline cannot count as a prepared ticket
Observable: If adding the required hours produces a timestamp the service cannot express, preparation cannot signal success for that ticket. For the service's Node.js Date representation, `−8,640,000,000,000,000` through `+8,640,000,000,000,000` milliseconds from the Unix epoch are representable, including both endpoints. One millisecond past either endpoint is unrepresentable.
Source: implied: U-4 and the Node.js timestamp range confirmed by a Date probe
Open: The requester would settle any narrower supported date range or recovery policy for a legacy record whose calculated deadline cannot be represented. A preparation failure follows the data-file diagnostic convention.

### C-20: A data file the service cannot use is diagnosed at startup
Observable: Start with an invalid JSON file, an unsupported file version or an unusable record. The service refuses the file with a diagnostic naming the file and the offending record or file-level problem. Correcting the problem or restoring a usable copy lets the operator retry.
Source: existing: docs/operations.md
Open: The requester would settle whether invalid stored due data is refused or recoverable through preparation, and how a disabled run treats it. A missing deadline in legacy data is eligible for preparation.

### C-21: The new release retains assigned deadlines when it rewrites the data file
Observable: After an assigned deadline has been saved, perform ticket changes or let the worker record notification delivery, then stop and restart the new release on the file. The enabled API reports the same `due`. A period of writing the file with due times disabled also preserves those values for later enabled runs.
Source: implied: the set-once rule and the whole-file saves described in docs/operations.md

### C-22: A successful new ticket creation in enabled production saves its assigned deadline with the ticket
Observable: After a 201 response, reload the data file in a new instance and read the ticket with its original `due`. A file copied as a save is interrupted contains either the prior state or the committed creation, which includes the ticket with its deadline, its creation audit entry and its queued notification.
Source: implied: U-4 and the existing whole-state save contract in docs/decisions/0008-json-data-file.md

### C-23: Preparation preserves existing ticket records apart from deadline-related additions
Observable: Compare the tickets before preparation and after it succeeds. The same IDs identify the same titles, requesters, priorities, statuses and creation times.
Source: implied: U-4 assigns deadlines to existing tickets
Open: The requester would settle whether deadline assignment during preparation counts as an edit for the ticket's `updated` timestamp.

### C-24: Preparing deadlines preserves append-only ticket history
Observable: Existing audit entries remain present with their original sequence, ordering and contents after preparation.
Source: existing: docs/decisions/0007-append-only-audit-log.md
Open: The requester would settle whether initial deadline assignment should appear in an enabled ticket's creation audit entry or in a new audit entry during preparation, and what actor or action to record for a preparation entry. Existing audit entries cannot be rewritten for that purpose.

### C-25: Preparing deadlines does not replay ticket lifecycle notifications
Observable: With the worker paused using `WORKER_INTERVAL_MS=0`, compare `GET /admin/outbox` before and after preparing deadlines for existing tickets. Preparing a deadline neither generates a new ticket receipt or resolution notification nor changes the existing pending, sent and dead events.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-26: Ticket changes still produce their existing audit effects with due times enabled
Observable: Create, patch and transition a ticket. Its history retains the corresponding `ticket.created`, `ticket.updated` and `ticket.transitioned` entries with the recorded changes and actor from `X-Actor` or `system` when absent. A patch that supplies the current values does not advance `updated` or add an audit entry.
Source: existing: docs/api.md

### C-27: Ticket changes still produce their existing notification effects with due times enabled
Observable: With the worker paused, create and resolve a ticket. The outbox records the existing receipt and resolution notifications for its requester. Resolving it again after reopening while the same resolution notification is pending does not enqueue a duplicate.
Source: existing: docs/operations.md

### C-28: The next ticket number survives preparation
Observable: Prepare a file written by 1.4.0, then create a ticket. It receives the next saved sequence number without reusing an existing ID.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-29: Release 1.4.0 starts on the production data file written by the new release
Observable: After the new release prepares and writes the production file, stop it and start the unchanged 1.4.0 release with that same `DATA_FILE`. It reaches `GET /health` with HTTP 200 and `{ "status": "ok" }` using the 1.4.0-compatible version-1 file, without converting it or restoring a pre-upgrade copy.
Source: request

### C-30: Release 1.4.0 can show every ticket after rollback
Observable: Page through the unfiltered tickets in 1.4.0 on the new release's file. All ticket IDs from before rollback are present with their ordinary ticket data, including tickets from before preparation and tickets created by the new release.
Source: request
Open: The requester would settle the deadline guarantee for a later re-upgrade after 1.4.0 has itself rewritten the file. Its reader and writer discard fields they do not recognize, so 1.4.0 starting on the file does not by itself demonstrate that deadlines survive a 1.4.0 write.

### C-31: The CLI's existing read commands work on the new release's data file
Observable: Use `bin/tickets.js list` with its existing filters or `bin/tickets.js show ID` with an existing ID, selecting the file through `DATA_FILE` or `--data FILE`. The operator can still list matching tickets or see a ticket's details and history. These commands leave the file untouched.
Source: existing: README.md
Open: The requester would settle whether the human-readable table or detail view displays due times, and if so how the production toggle applies to those views.

### C-32: The CLI preserves the positional raw listing consumed by the weekly report
Observable: Run `bin/tickets.js list --raw` on a file that contains deadlines. Each line still has the four tab-separated columns `id`, `status`, `priority`, `title` in that order. The weekly report still reads those rows to count tickets by status and priority.
Source: existing: README.md

### C-33: The service starts with `npm start` on the selected port
Observable: On Node.js 22 or later, start with `PORT` set to a free port. The service answers there. The existing default is 4180 if `PORT` is unset or empty. The supported whole-number range is 0 through 65535, where 0 selects a free port and values outside the range are refused at startup.
Source: existing: README.md and src/config.js

### C-34: The service runs without installing npm dependencies
Observable: Run `npm start` from a clean checkout on Node.js 22 or later with no npm dependencies installed. The service starts when its configuration and data are usable.
Source: request

### C-35: The original tests pass unchanged
Observable: Run `npm test` and observe the existing suite pass with its original test files intact.
Source: request

### C-36: The new due-time tests run in the standard test command
Observable: New `node:test` tests under `test/` cover the new behavior. Running `npm test` discovers and passes them alongside the original suite.
Source: request
