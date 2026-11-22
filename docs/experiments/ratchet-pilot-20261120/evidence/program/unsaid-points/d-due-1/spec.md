## Use cases

### U-1: A ticket requester submits a ticket to get a response deadline
Flow: With due times enabled, the requester sends `POST /tickets` and receives the new open ticket with `due`. With the default hours and a creation time of `2025-09-01T08:00:00.000Z`, an urgent ticket is due at `2025-09-01T12:00:00.000Z` (4 hours), a high ticket at `2025-09-02T08:00:00.000Z` (24 hours), a normal ticket at `2025-09-04T08:00:00.000Z` (72 hours), and a low ticket at `2025-09-08T08:00:00.000Z` (168 hours). Omitting priority uses `normal`.
Source: request

### U-2: A help desk operator changes response hours to apply new targets to future tickets
Flow: The operator changes the hours without editing the service code. A ticket created under the new hours shows the new target for its priority. When an agent later reads an existing ticket or changes its priority, the ticket still shows the deadline that was originally set for it.
Source: request

### U-3: A help desk agent lists overdue tickets to find outstanding work
Flow: The agent calls `GET /tickets?overdue=true`. The list contains overdue `open` and `in_progress` tickets and excludes `resolved` and `closed` tickets. The agent follows `next` with the same filters until it is null. If there are no matches, the agent sees an empty page. A resolved ticket that reopens can qualify again at its original deadline.
Source: request

### U-4: A production operator prepares the existing file to enable due times
Flow: The operator deploys with due times hidden, prepares the production `DATA_FILE` until all its tickets have durable deadlines based on their creation time and priority, then serves enabled production responses with `DUE_TIMES=on`. The operator can repeat preparation after an interruption without changing deadlines that were already saved. With the switch off again, callers see the old API responses.
Source: request

### U-5: A production operator rolls back to 1.4.0 to recover service
Flow: The operator stops the new release and starts the unchanged 1.4.0 service on the same file. The operator can retrieve tickets from before activation and tickets created by the new release without restoring an older copy of the file.
Source: request

### U-6: An operator reads the ticket file to inspect tickets while the weekly report continues to run
Flow: The operator uses `bin/tickets.js list` or `show` on the production file. The support lead runs the weekly report, which uses the tab-separated id, status, priority and title positions in `list --raw` to count tickets.
Source: existing: README.md

### U-7: A maintainer runs the whole test suite to verify the release
Flow: The maintainer runs `npm test` and sees the unchanged existing tests and the new due-time tests under `test/` pass in the same run.
Source: request

## Clauses

### C-1: The service still starts through `npm start` on the configured `PORT`.
Observable: On the supported Node.js runtime (22 or later), start the service with a free `PORT` and get HTTP 200 with `{"status":"ok"}` from `GET /health` on that port.
Source: existing: README.md

### C-2: The service still runs without npm dependencies.
Observable: In a checkout without installed packages or registry access, start the service with `npm start` and exercise the ticket API.
Source: request

### C-3: A ticket created with due times enabled receives a deadline based on its creation instant and effective priority.
Observable: With the default hours, create tickets at `2025-09-01T08:00:00.000Z`. The deadlines are urgent `2025-09-01T12:00:00.000Z` (+4 hours), high `2025-09-02T08:00:00.000Z` (+24 hours), normal `2025-09-04T08:00:00.000Z` (+72 hours) and low `2025-09-08T08:00:00.000Z` (+168 hours). Omitted priority yields the normal deadline. The differences are elapsed hours from `created`, including across local clock changes.
Source: request

### C-4: Operators can configure the response hours by priority without editing code.
Observable: Configure a different usable number of hours for a priority through the service's settings. Create a ticket at that priority under the new settings and see that many elapsed hours between `created` and `due`. A priority without an override uses its default.
Source: implied: the request to change response hours without a code change and the environment-based defaults in README.md
Open: The requester would settle supported hour values where they affect policy, including whether zero or fractional hours are allowed and the supported range. The operator would settle whether settings must take effect without a restart. Setting names and syntax follow the implementation's documented controls.

### C-5: Unusable response-hour configuration follows the existing startup error convention when needed for due times.
Observable: Start with due times enabled and a setting that the supported configuration syntax cannot interpret as response hours, such as `tomorrow`. The process exits with status 2 before serving requests and identifies the offending setting in its startup diagnostic.
Source: existing: README.md and src/server.js

### C-6: An enabled ticket API response exposes the ticket deadline as `due`.
Observable: On a successful create (201), individual read (200), patch (200), transition (200) or listing (200), the returned ticket has its deadline in `due` as an ISO 8601 UTC timestamp, for example `2025-09-01T12:00:00.000Z`. The field is present for each returned ticket regardless of whether its status is `open`, `in_progress`, `resolved` or `closed`.
Source: implied: “Every ticket shows its due time as `due`” and the ticket responses and time convention in docs/api.md
Open: The requester would settle whether human-readable CLI output from `list` or `show` is also meant to display the deadline.

### C-7: A change to the configured hours leaves an assigned deadline fixed.
Observable: Record a ticket's `due`, apply different hours for its priority and read the ticket again. Its `due` is identical while a newly created ticket at that priority uses the new hours.
Source: request

### C-8: A change to ticket priority leaves an assigned deadline fixed.
Observable: Patch an open ticket from `normal` to `urgent`. The response shows `urgent` with the same `due` as before the patch.
Source: request

### C-9: A lifecycle transition leaves an assigned deadline fixed.
Observable: Move a ticket from `open` to `in_progress` to `resolved`, then reopen it to `open`. Every response shows the original `due`. On the path from `resolved` to `closed`, the closed ticket also has the original `due`.
Source: implied: the request that a deadline is set once and the lifecycle in docs/api.md

### C-10: The ticket deadline is assigned by the service.
Observable: Send `due` as an extra request-body field to create or patch a ticket. The response is HTTP 400 in the existing `error` envelope with `code: "invalid"`. The caller cannot set or replace a deadline this way.
Source: implied: “A ticket's due time is set once” and the unknown body field rule in docs/api.md

### C-11: The enabled overdue listing selects tickets by current status and the passage of their saved deadline.
Observable: Request `GET /tickets?overdue=true` with due times enabled. An otherwise eligible ticket strictly past its deadline appears if currently `open` or `in_progress`. A future deadline excludes the ticket. `resolved` and `closed` tickets are excluded even when their deadlines are past. A ticket that reopens after its deadline can appear on the next listing, and an active ticket can become overdue with the passage of time alone.
Source: request
Open: The requester would settle membership at the exact deadline instant.

### C-12: Omitting the overdue query parameter does not opt into overdue filtering.
Observable: With due times enabled, call `GET /tickets` without filters and page through it. Tickets of all four statuses appear regardless of the relation of their deadlines to the current time.
Source: implied: the request introduces `GET /tickets?overdue=true` while keeping ordinary listing available

### C-13: The enabled overdue selection also honors existing listing filters.
Observable: Request `GET /tickets?overdue=true&status=open` and see only overdue `open` matches. Request it with just `status=resolved` as the other filter and see no matches. Request it with just `priority=urgent` as the other filter and see only urgent overdue matches.
Source: implied: U-3 and the listing in docs/api.md
Open: When both `status` and `priority` are present with the enabled overdue filter, the requester would settle the legacy discrepancy. docs/api.md specifies a match on both fields while src/tickets/query.js in 1.4.0 matches either. The overdue condition still applies to every returned item.

### C-14: Overdue results use the existing cursor-page contract.
Observable: With overdue filtering enabled, include nonmatching and matching ids interleaved in the file. For a fixed matching set, follow `next` with the same filters and get matching tickets in numeric id order, after the last id served, without duplicates or gaps. A page holds up to `limit` matching items, default 20 with accepted whole-number limits 1 through 100 inclusive. `next` is null when no match remains, including the empty response `{"items":[],"next":null}`. Invalid limits and cursors still return HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-15: If an enabled listing rejects an overdue query value, it uses the existing invalid-query response.
Observable: For any overdue query form that the enabled service treats as an invalid filter value, the response is HTTP 400 with an `error` object containing `code: "invalid"` and a human-readable `message`.
Source: existing: docs/decisions/0004-error-envelope.md
Open: The requester would settle whether any forms beyond the required single `overdue=true` are recognized, ignored or refused, including `false`, empty or unrecognized values, case variants and repeated values.

### C-16: Production ticket API responses follow 1.4.0 while `DUE_TIMES` is anything other than `on`.
Observable: Start with the switch unset, empty or set to a value other than `on`. Run the same ticket requests as on 1.4.0 against equivalent state, including state whose deadlines have been prepared. Successful responses carry no `due`, and existing statuses, response bodies and errors still apply. `GET /tickets?overdue=true` and other `overdue` values have no effect on the result. Combined status and priority filters still match either supplied field as in 1.4.0.
Source: request

### C-17: Operators can prepare production deadlines before exposing the feature.
Observable: Starting with a 1.4.0 production file, use the release's preparation procedure while due-time responses are still hidden. An inspection of `DATA_FILE` confirms every ticket has a persisted deadline before enabling responses. A file with zero tickets needs no deadlines added.
Source: request
Open: The production operator would settle how and when preparation runs, including whether it may stop ticket writes or must run while the service is serving traffic. The request fixes the outcome before activation.

### C-18: Preparation calculates a deadline for each legacy ticket that lacks one.
Observable: Prepare a file containing tickets with different saved `created` times and priorities, including tickets in `open`, `in_progress`, `resolved` and `closed`. Each missing deadline becomes that ticket's own saved creation instant plus the response hours for its priority in the ticket record. Changing the preparation clock or the ticket's `updated` time does not shift that calculation. With default hours, the offsets are 4 for `urgent`, 24 for `high`, 72 for `normal` and 168 for `low`.
Source: request
Open: The requester would settle which schedule governs legacy tickets if response hours had already been changed before preparation. For tickets created while responses are hidden, the operator would settle whether deadlines are assigned at creation or filled in during preparation.

### C-19: Repeating preparation keeps deadlines that are already saved.
Observable: Prepare a file that contains some tickets with saved deadlines and some without. Repeat preparation after an interruption or under changed response-hour settings. Tickets whose deadline was already saved keep that exact value, and the procedure can finish assigning deadlines to the remaining tickets.
Source: implied: U-4 and the requirement that a ticket's due time is set once

### C-20: The production service exposes due-time behavior only after its file holds all required deadlines.
Observable: Attempt activation with `DUE_TIMES=on` against a production file containing a ticket without a deadline. Any successful enabled ticket response comes only after the file contains all required deadlines. After successful preparation, start with `DUE_TIMES=on` and observe enabled responses.
Source: request
Open: The production operator would settle whether premature activation refuses startup, keeps serving with the feature hidden, or completes preparation before serving. The requester would settle enabled behavior when no `DATA_FILE` is configured. The existing off-mode in-memory service remains covered by C-16.

### C-21: A saved due time cannot be silently replaced as a way to handle invalid deadline data.
Observable: If a production file contains a value for an assigned deadline that cannot be interpreted as a time, the service does not present a guessed or recalculated deadline for that ticket as if it were the saved one. If startup refuses the file as unusable, the diagnostic identifies the file and the offending record, with exit status 2 as for other data-file validation failures.
Source: implied: the fixed deadline requirement and the file validation convention in docs/operations.md
Open: The production operator would settle the recovery procedure for a damaged deadline, including whether any service mode can continue while preserving the damaged value for recovery.

### C-22: Deadline arithmetic cannot expose an invalid timestamp as a valid deadline.
Observable: At the limits of the service clock's Date range, from `-271821-04-20T00:00:00.000Z` through `+275760-09-13T00:00:00.000Z` inclusive (±8,640,000,000,000,000 milliseconds from the epoch, confirmed with Node), a result representable by that clock can be serialized. A calculation beyond its range cannot produce a successful due time by wrapping, clamping or returning an invalid timestamp.
Source: implied: the creation-plus-hours rule and the Date-based ISO clock in src/clock.js and src/store.js
Open: The production operator would settle how to recover a valid legacy ticket whose calculation exceeds the supported time range. The existing startup and HTTP error conventions apply when the operation fails.

### C-23: A successful enabled ticket creation with a data file saves the assigned deadline with the ticket.
Observable: Create a ticket while enabled with `DATA_FILE` configured. After the HTTP 201 response, the file contains the new ticket with its assigned deadline and the same committed creation includes its audit entry and requester notification in the outbox.
Source: implied: the requirement to give each ticket a deadline and docs/decisions/0008-json-data-file.md and docs/decisions/0006-notification-outbox.md

### C-24: Routine saves by the new release preserve assigned deadlines even while responses are hidden.
Observable: With a prepared file, restart the new release with `DUE_TIMES` off, change a ticket or allow a pending notification result to be saved, and stop the service cleanly. Start the new release again with `DUE_TIMES=on`. The previously saved deadlines are identical, even if the response hours changed between starts.
Source: implied: the set-once requirement and U-4

### C-25: An interruption during deadline preparation leaves a usable whole data file.
Observable: Interrupt a preparation write. The configured data file still loads as a complete state, with the deadlines from before or after the interrupted write. Preparation can continue without losing any tickets. A successful activation does not expose an incomplete set of deadlines.
Source: existing: docs/operations.md and docs/decisions/0008-json-data-file.md

### C-26: Deadline preparation preserves existing ticket information.
Observable: Compare the existing tickets before and after preparation without intervening user edits. The same ids retain the same titles, requesters, creation times, priorities and statuses. The next ticket still receives the next unused sequential id.
Source: implied: U-4 and the persistence rules in docs/operations.md
Open: The requester would settle whether recording a deadline during preparation counts as an edit for the ticket's `updated` timestamp.

### C-27: Existing audit history remains readable when deadlines are introduced.
Observable: Query `GET /tickets/:id/audit` after preparing the data file and see each original entry unchanged in its original order. With due times enabled, ticket edits and transitions still append their usual actor, action and field changes, and a patch that changes no values leaves the ticket's audit history untouched.
Source: existing: docs/api.md and docs/decisions/0007-append-only-audit-log.md
Open: The requester would settle whether the audit log additionally records the assigned deadline at creation or appends an entry during preparation. Existing entries remain unchanged either way.

### C-28: Introducing deadlines preserves normal requester notifications.
Observable: With the worker off, inspect `GET /admin/outbox` after preparing deadlines and see the pre-existing notification records with their original states. Creating a ticket and subsequently resolving it still queue their normal `ticket.created` and `ticket.resolved` notifications, with the existing pending-key deduplication. Preparing or reading deadlines does not replay those notifications.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-29: Release 1.4.0 can start on the new release's production file and show every saved ticket.
Observable: Prepare a production file, serve the new release with due times enabled and create another ticket. Stop it and start the unmodified 1.4.0 release against the same file, without conversion or an older backup. Health succeeds. Paging `GET /tickets` and reading individual ids return all tickets from before and after activation with their legacy fields, including all four statuses. The file is readable by 1.4.0, whose loader requires version 1.
Source: request
Open: Release 1.4.0 drops unrecognized fields on rewrite. The requester would settle whether original deadlines must also survive a 1.4.0 write followed by re-enabling the new release, and which recovery procedure to use if so.

### C-30: The operator's CLI can still read tickets from the data file.
Observable: Point `bin/tickets.js` at a pre-upgrade file or one saved by the new release using `DATA_FILE` or `--data FILE`. `list` still lists tickets with the existing status and priority filters, and `show ID` still displays the ticket and its history. Running either read-only command leaves the file unchanged.
Source: existing: README.md and docs/operations.md

### C-31: Raw ticket listing retains the interface consumed by the weekly report.
Observable: On a file written by the new release, `list --raw` still provides one tab-separated line per selected ticket with id, status, priority and title in positions 1 through 4 respectively. The weekly report still reports the total and the correct counts by status and priority for the same file.
Source: existing: README.md and scripts/weekly-report.js

### C-32: The existing test suite still passes as written.
Observable: Run `npm test` and see all pre-existing tests pass without changing the existing tests.
Source: request

### C-33: The normal test run includes new due-time coverage.
Observable: Run `npm test` and see the additional `node:test` tests under `test/` for due-time assignment, overdue selection, rollout and persistence behavior run with the existing suite and pass.
Source: request
