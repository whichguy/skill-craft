## Use cases

### U-1: A requester creates a ticket, to see when the help desk promises a response
Flow: With due times enabled, the requester sends `POST /tickets` and gets a `201` response with an `open` ticket and its `due` time. From `2025-09-01T08:15:00.000Z`, the default due times are `2025-09-01T12:15:00.000Z` for `urgent` (4 hours), `2025-09-02T08:15:00.000Z` for `high` (24 hours), `2025-09-04T08:15:00.000Z` for `normal` (72 hours), and `2025-09-08T08:15:00.000Z` for `low` (168 hours). Omitting the priority gives the `normal` deadline. Fetching the ticket shows the same due time.
Source: request

### U-2: A help-desk operator changes response hours, to make a different promise for future tickets
Flow: The operator changes the hours for a priority through configuration. A new ticket of that priority uses the new hours. A ticket with a deadline already assigned keeps it when the hours change, including if an agent later edits the ticket's priority.
Source: request

### U-3: A help-desk agent lists overdue tickets, to find outstanding responses
Flow: The agent calls `GET /tickets?overdue=true` and sees `open` and `in_progress` tickets whose deadline is strictly earlier than the current time. A ticket due at the current time is excluded. Resolving a matching ticket removes it from the listing. Reopening it puts it back if its deadline is still past. The agent can narrow the listing with an existing filter and follow `next` with the same filters. With no matches, the page has `items: []` and `next: null`.
Source: request

### U-4: A production operator prepares the live data file, to enable due times for existing tickets
Flow: The operator runs the new release's preparation procedure on the production `DATA_FILE`. Each existing ticket without a deadline gets one from its own `created` time and recorded priority, including resolved and closed tickets. The operator enables `DUE_TIMES=on` once that file holds the deadlines. The service starts through `npm start` on `PORT` and answers `GET /health` with `{"status":"ok"}` when it is serving. After a `SIGTERM` stop and restart, enabled ticket responses still show the saved deadlines. If preparation is interrupted, the operator can retry on the retained file once any blocking fault is corrected.
Source: request

### U-5: An existing API client keeps using the service with due times disabled, to continue its normal workflow during rollout
Flow: While `DUE_TIMES` is unset or has a value other than `on`, the client creates, reads, lists, edits and transitions tickets with the 1.4.0 responses. Supplying `overdue=true` has the same effect as it did in 1.4.0. This applies even when the file has been prepared for activation.
Source: request

### U-6: A production operator rolls back to 1.4.0, to restore service after a bad release
Flow: The operator stops the new release and starts the original 1.4.0 against the data file the new release wrote. The server starts on the configured port. Walking the ordinary ticket listing retrieves every ticket in that file, including tickets created by the new release and tickets whose deadlines were backfilled.
Source: request

### U-7: An operator or support lead reads the ticket file, to inspect tickets or produce the weekly counts
Flow: The operator uses `bin/tickets.js list` or `show` on the data file before or after due times are enabled. The weekly report still consumes `list --raw`, with id, status, priority and title in that order, and reports the counts from the file.
Source: existing: README.md and docs/operations.md

### U-8: A maintainer runs `npm test`, to verify due times and the existing service together
Flow: `npm test` runs the original tests as written alongside the new `node:test` tests under `test/`, and both pass.
Source: request

## Clauses

### C-1: `npm start` runs the Node.js ticket API on the configured port.
Observable: Start with Node.js 22 or later and `PORT=8080` where that port is free. On that port, `GET /health` returns HTTP 200 with `{"status":"ok"}`. An unset or empty `PORT` uses `4180`. The accepted port range is `0` through `65535` inclusive, with `0` letting the operating system choose a free port.
Source: existing: README.md, src/config.js and src/server.js

### C-2: The service runs without npm dependencies.
Observable: `npm start` and `npm test` work from a checkout with Node.js and no installed npm packages.
Source: existing: README.md and CONTRIBUTING.md

### C-3: With `DUE_TIMES` other than `on`, HTTP responses retain 1.4.0 behavior.
Observable: With `DUE_TIMES` unset, empty or set to a value other than `on`, the same requests against equivalent legacy ticket data have the 1.4.0 statuses and JSON payloads. This includes ticket payloads without `due` and the legacy treatment of `overdue` as an ignored query parameter, even after deadlines have been saved to `DATA_FILE`.
Source: request

### C-4: A ticket created with due times enabled gets a deadline from its creation instant plus the configured hours for its priority.
Observable: Create tickets at `2025-09-01T08:15:00.000Z` with default settings. An `urgent` ticket has `due` `2025-09-01T12:15:00.000Z` (4 hours), `high` has `2025-09-02T08:15:00.000Z` (24 hours), `normal` has `2025-09-04T08:15:00.000Z` (72 hours), and `low` has `2025-09-08T08:15:00.000Z` (168 hours). The offsets are elapsed hours.
Source: request

### C-5: Creating a ticket without a priority uses the `normal` response hours.
Observable: Omit `priority` from a valid `POST /tickets` body. The `201` response has `priority: "normal"` and, when enabled with default hours, a `due` 72 hours after `created`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-6: Operators can configure the response hours for each priority without editing code.
Observable: Set different hours for `urgent`, `high`, `normal` or `low` through the service's environment configuration. A ticket newly assigned a due time for that priority uses its configured number of hours. An unset or empty hours setting uses that priority's default.
Source: request
Open: The requester decides the accepted range and precision for hours, including zero and fractional values. The configuration needs to support changing the stated defaults to usable response durations.

### C-7: An unusable response-hours setting used on service startup is reported as a configuration error.
Observable: Start the service with an hours setting it needs for startup set to a value it cannot use. The process exits without serving and reports the setting by name, as it does for an unusable `PORT` value.
Source: existing: README.md, Configuration, and src/server.js

### C-8: Enabled HTTP responses that return a ticket include its assigned `due` as an ISO 8601 UTC timestamp.
Observable: Read `due` in the successful `POST /tickets`, `GET /tickets/:id`, `PATCH /tickets/:id` and `POST /tickets/:id/transition` responses and in every ticket in `GET /tickets` pages, including overdue pages. A resolved or closed ticket still has `due` wherever it is returned. For a high-priority ticket created at `2025-09-01T08:15:00.000Z` under defaults it reads `2025-09-02T08:15:00.000Z`.
Source: request

### C-9: `due` remains server-assigned on ticket mutation routes.
Observable: Include `due` in an otherwise valid create, patch or transition request body. The route returns HTTP 400 with `error.code` `invalid` for the unknown field. The request creates no ticket or change.
Source: existing: docs/api.md and src/tickets/validate.js

### C-10: Applying new response hours leaves previously assigned deadlines fixed.
Observable: Assign a `high` ticket its default 24-hour deadline, then configure `high` for 30 hours. A new `high` ticket has a 30-hour offset, and the first ticket still shows its original deadline.
Source: request

### C-11: A ticket keeps its deadline through subsequent ticket edits and lifecycle moves.
Observable: Change a ticket from `high` to `urgent`, edit its title, or move it through permitted statuses, including reopening from `resolved`. The original `due` is returned after each change.
Source: request

### C-12: The enabled overdue filter matches exactly the active tickets whose deadlines have passed.
Observable: Call `GET /tickets?overdue=true`. An `open` or `in_progress` ticket qualifies when `due` is earlier than the service's current time, including immediately after the deadline without a ticket edit. It is excluded before or exactly at `due`. `resolved` and `closed` tickets are excluded regardless of `due`. A reopened ticket qualifies again if its original `due` is in the past.
Source: request

### C-13: An ordinary ticket listing leaves eligibility independent of due time.
Observable: With due times enabled, omit `overdue` from `GET /tickets`. Tickets of any status and due time remain eligible under the listing's existing filters and cursor rules.
Source: implied: U-3 adds an opt-in filter to the existing listing
Open: The requester decides the enabled behavior for `overdue=false`, empty values, other values and repeated `overdue` parameters. If a value is rejected as invalid, the existing query error is HTTP 400 with `error.code` `invalid`.

### C-14: Overdue eligibility is required in addition to existing listing filters.
Observable: With the feature enabled, `?overdue=true&status=open` returns only overdue `open` tickets. `?overdue=true&status=resolved` or `status=closed` returns an empty page. `?overdue=true&priority=urgent` returns only overdue `urgent` tickets regardless of the schedule under which their deadlines were originally assigned.
Source: implied: U-3 and the filters in docs/api.md
Open: The requester decides how to combine `status` and `priority` when both accompany `overdue=true`. `docs/api.md` describes an intersection while 1.4.0 in `src/tickets/query.js` matches either filter when both are supplied. Overdue eligibility applies under either interpretation.

### C-15: Overdue results use the existing cursor pagination contract over the matching tickets.
Observable: `GET /tickets?overdue=true` returns `{ "items": [...], "next": ... }` in numeric ticket ID order. `limit` defaults to 20 and accepts whole numbers from 1 to 100 inclusive. Nonmatching rows consume no slots. Pass a returned `next` back as `cursor` with the same filters to continue after that page's last ID, even if that ticket has since stopped matching. `next` is null when no further matching ticket remains, including when there are zero matches or the last page is exactly full.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-16: The existing query validation still applies to overdue listings.
Observable: With the feature enabled, add `status=done`, `priority=critical`, `limit=0`, `limit=101` or `cursor=abc` to separate `overdue=true` requests. Each answers HTTP 400 with `error.code` `invalid` and a human-readable message.
Source: existing: docs/api.md and test/api.test.js

### C-17: Preparation assigns a missing deadline to every ticket already in the data file.
Observable: Prepare a 1.4.0 file containing `open`, `in_progress`, `resolved` and `closed` tickets. Each ticket gets its saved `created` instant plus the response hours for its recorded priority under the settings used to prepare the file. At defaults, a ticket recorded as `high` and created at `2025-09-01T08:15:00.000Z` gets `2025-09-02T08:15:00.000Z` regardless of its saved `updated` value or when preparation runs.
Source: request

### C-18: Enabled production responses start only after the configured data file holds all required deadlines.
Observable: Start from a production file with tickets missing deadlines. The first HTTP response exhibiting due-time behavior occurs only after the file durably holds deadlines for all existing tickets. If preparation cannot save the required values, the service does not expose enabled responses for that file. An empty store has no existing deadlines to prepare.
Source: request
Open: The requester decides the operator workflow for preparation and early activation, such as a preparation step before starting the enabled server or startup preparation that finishes before any enabled response. The handling and operator diagnosis when a legacy creation instant plus the configured hours lies outside the time range used for due timestamps is also undecided. Node's built-in `Date` represents instants from `-8640000000000000` to `8640000000000000` milliseconds from the Unix epoch, inclusive.

### C-19: Due times can be used with the existing memory-only service mode.
Observable: Start with no `DATA_FILE` and with `DUE_TIMES=on`. The service starts empty, returns a deadline for a newly created ticket and supports overdue queries for tickets in that process. A fresh process without a file again starts empty.
Source: implied: README.md's memory-only mode and the request's production data-file prerequisite

### C-20: A successfully created ticket's deadline survives a restart with its data file.
Observable: With due times enabled and `DATA_FILE` configured, create a ticket and restart from that file. The ticket has the same `due` from the successful creation even when response hours differ at restart.
Source: implied: the set-once rule and docs/decisions/0008-json-data-file.md

### C-21: Once saved by the new release, an assigned deadline survives subsequent processing of that file by the new release.
Observable: Run preparation again or restart with different response hours after a ticket's deadline has been saved. A repeat preparation fills missing deadlines while the assigned value stays the same. Start with the switch disabled, let the new release save the file through an ordinary ticket or outbox change or a clean stop, then enable it again. The previously assigned deadline is still the same.
Source: implied: the set-once rule and the rollout sequence in U-4 and U-5
Open: The requester decides what a subsequent upgrade must do after 1.4.0 has rewritten the file. Its writer retains only fields it knows, so a legacy save can discard data that a startup and read in 1.4.0 could tolerate.

### C-22: An interrupted preparation preserves a readable production state.
Observable: Interrupt preparation during a save of an existing production file. The active file remains a complete state from before or after the interrupted save, with all its tickets. The operator can resume preparation on that file once the interruption or write fault is resolved.
Source: existing: docs/operations.md and docs/decisions/0008-json-data-file.md

### C-23: Preparing deadlines preserves the existing ticket records' business data.
Observable: Compare tickets before and after preparation by ID. Each keeps its title, requester, status, priority and creation timestamp.
Source: implied: U-4 assigns deadlines to the existing tickets
Open: The requester decides whether deadline preparation counts as a change to `updated` in the enabled API. During the disabled rollout, the HTTP response remains governed by C-3.

### C-24: Preparing deadlines preserves ticket numbering.
Observable: After preparing and reopening a file whose next ticket number is 43, the next successful creation yields `T-0043`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md and docs/operations.md

### C-25: Deadline assignment preserves existing audit history.
Observable: Audit entries already present before preparation retain their sequence numbers, order, actor, timestamps, actions and field changes in `GET /tickets/:id/audit`. Ordinary ticket edits and transitions still append their usual entries.
Source: existing: docs/decisions/0007-append-only-audit-log.md
Open: The requester decides whether the initial deadline is included in the enabled creation audit entry or recorded as an operational audit change for backfilled tickets. The preexisting entries are append-only and the disabled HTTP behavior remains governed by C-3.

### C-26: An unchanged patch remains a no-op with due times enabled.
Observable: Patch an editable ticket with its current title or priority. The returned ticket has the same `updated` and `due` values, and its audit history gains no entry.
Source: existing: docs/api.md and test/store.test.js

### C-27: Deadline handling preserves the service's notification behavior.
Observable: With delivery paused using `WORKER_INTERVAL_MS=0`, creating and resolving a ticket still enqueue the existing `ticket.created` and `ticket.resolved` notifications, with the existing pending-key deduplication. In the absence of ordinary notification activity, preparation and the passage of a deadline leave the outbox entries in `GET /admin/outbox` as they were.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-28: The 1.4.0 release starts directly on the data file written by the new release.
Observable: Point the original 1.4.0 `npm start` at the saved `DATA_FILE` produced by the new release before or after activation. The file is readable as version `1`, and 1.4.0 serves `GET /health` on its configured port without converting the file or restoring an earlier copy.
Source: request

### C-29: The rolled-back 1.4.0 release can show every ticket in the new release's saved file.
Observable: Follow the ordinary ticket listing's cursors in 1.4.0 after rolling back. The listing includes every saved ticket ID with its ordinary ticket data, including migrated tickets and tickets created under the new release. A direct fetch by any of those IDs succeeds.
Source: request

### C-30: The operator's existing commands can read the ticket file through rollout.
Observable: With `DATA_FILE` or `--data FILE`, run `bin/tickets.js list` with its existing filters and `bin/tickets.js show` for a saved ticket. Both can read the file before or after deadline preparation and do not write it. The table still shows its existing ticket information and `show` still gives the ticket details and history.
Source: existing: README.md, docs/operations.md and bin/tickets.js
Open: The requester decides whether the human-readable table or `show` should also display `due` during the enabled rollout. The API exposure is specified in C-8.

### C-31: The raw CLI list retains its existing row layout.
Observable: Run `node bin/tickets.js --data FILE list --raw` against a file with saved due times. Each selected ticket occupies one line of four tab-separated fields in the existing positions: id, status, priority, title.
Source: existing: README.md and src/format.js

### C-32: The weekly report still counts tickets by the existing status and priority groups.
Observable: Run the weekly report against a file containing assigned deadlines. The reported total, counts for `open`, `in_progress`, `resolved` and `closed`, and counts for `urgent`, `high`, `normal` and `low` agree with the tickets in the file. The existing `--json` output remains usable by the dashboard.
Source: existing: README.md, docs/operations.md and scripts/weekly-report.js

### C-33: The existing test suite passes as written.
Observable: Run `npm test` with the existing tests intact. The existing tests pass, including the preexisting service, API, storage, notification and validation checks.
Source: request

### C-34: `npm test` runs passing `node:test` coverage of the new behavior from `test/`.
Observable: Run `npm test` to execute the added tests alongside the original suite. The new tests cover the required due-time behavior, including calculation, configuration, persistence, overdue selection, rollout and rollback compatibility.
Source: request
