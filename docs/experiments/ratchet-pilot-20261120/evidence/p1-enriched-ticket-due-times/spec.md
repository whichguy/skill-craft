## Use cases

### U-1: A requester creates a ticket to see when a response is due
Flow: With due times enabled, create urgent, high, normal and low tickets. With the default settings, each response shows `due` 4, 24, 72 or 168 elapsed hours after that ticket's `created`, respectively. A ticket submitted without a priority uses normal. A later detail or list request shows the same deadline.
Source: request

### U-2: An agent changes a ticket to keep its record current
Flow: Change a title or priority, repeat a patch with the same values, or move a ticket through its permitted states. Each successful ticket response shows the original `due`. Resolving it removes it from the overdue listing. Reopening it makes it eligible again at its original deadline. A patch to a closed ticket or an impermissible transition still returns 409 `conflict`.
Source: implied: the fixed deadline applies throughout the existing ticket lifecycle

### U-3: An agent asks for overdue tickets to find work that has missed its response deadline
Flow: Request `GET /tickets?overdue=true` before, at and just after a deadline. Compare open, in-progress, resolved and closed tickets. Only open and in-progress tickets whose deadlines have passed appear. When the store is empty or there are no matches, the page is empty.
Source: request

### U-4: A dashboard client pages through overdue tickets to review all matching work
Flow: Add a status or priority filter, or both, to `overdue=true`. Follow `next` as `cursor` with the same filters. Try the default size of 20, the minimum of 1 and the maximum of 100, with more than one page of matches and nonmatching tickets between them. Results stay in numeric ID order. The final page has `next: null`, including when it has exactly the requested number of matches.
Source: implied: the overdue filter extends the existing ticket listing

### U-5: An API client submits invalid input to receive the normal error response
Flow: Try to supply `due` on a write, send an unsupported overdue value with the feature enabled, or give an invalid status, priority, cursor or page size such as 0 or 101. Check the HTTP 400 `invalid` envelope. Try a nonexistent ticket and an unavailable lifecycle move to see the existing 404 `not_found` and 409 `conflict` responses.
Source: implied: the server owns due times and existing error conventions apply

### U-6: A help-desk operator adjusts response hours to change deadlines for future tickets
Flow: Set an override for a priority through the environment and restart. Create a ticket at that priority to see the new duration. Other priorities still use their own settings, and tickets with deadlines already set retain them. Try an unusable value and get a startup diagnostic naming the setting.
Source: implied: response hours are configurable, while assigned deadlines are fixed

### U-7: A production operator prepares the existing file to enable due times safely
Flow: Back up the existing state, choose the response hours, stop its current owner and start the new release with due times disabled. The file gets the missing deadlines for every ticket, including inactive tickets, based on each saved `created` and priority. Clients still see the 1.4.0 API. Verify preparation in the file, then restart with `DUE_TIMES=on` and see deadlines for old and new tickets.
Source: implied: production activation follows durable backfill

### U-8: A production operator retries a failed preparation to protect the current data
Flow: First try enabling the service before the file is ready and see startup refused. Then attempt preparation with an unreadable or invalid file, a malformed saved deadline, or a destination that cannot be replaced. The release refuses to serve with partial preparation, explains the failure and leaves the existing file available for correction or restoration. Correct the cause, retry and verify a complete file.
Source: implied: production activation requires a usable, completely prepared file

### U-9: An operator restarts or disables the feature to control exposure
Flow: Restart a prepared store with the same or changed hours and compare the deadlines. Start with `DUE_TIMES` unset or otherwise different from `on` and make ordinary API calls, including a list request containing `overdue`. Create another ticket while the feature is disabled, then reenable it after verifying the file. Existing deadlines survive the intervening ticket, outbox and shutdown saves.
Source: implied: the gate controls the API while persisted deadlines remain fixed

### U-10: An operator starts a fresh service to use due times without legacy tickets
Flow: Start with a missing file, a valid data file with zero tickets, or without `DATA_FILE`. The list is initially empty. With `DUE_TIMES=on`, the first new ticket has a deadline. With a data file, it keeps that deadline on restart. Without one, state lives only for that process.
Source: implied: the rollout includes the first run and the existing memory-only service

### U-11: An operator rolls back to 1.4.0 to keep the help desk running
Flow: Stop the new release after it has prepared legacy tickets and saved additional ticket activity. Retain a copy of the resulting file, then start the unmodified 1.4.0 on that same data file. Page through all tickets, read individual tickets and continue the existing workflow, including ticket creation. If returning to the new release after 1.4.0 saved state, retain the latest ticket data and recover prior due times from the copy before reenabling.
Source: implied: an unmodified 1.4.0 must consume the new release's output and previously assigned deadlines must remain recoverable

### U-12: An operator reads tickets from disk to inspect due times without writing state
Flow: Run `bin/tickets.js` with `DATA_FILE` or `--data FILE`. Use `show` to read a ticket and its history, and `list` to inspect matching tickets, including lists longer than 100. With due times enabled for the CLI, inspect deadlines in human-readable output. With legacy or disabled output, the existing commands still work. An absent ticket returns exit 1, and a usage or file failure returns exit 2.
Source: implied: displaying due times reaches the existing human-facing ticket reader

### U-13: A support lead runs the weekly report to keep the dashboard counts working
Flow: Read a legacy or prepared file via `list --raw` or the weekly report. Each raw line has four tab-separated columns, id, status, priority and title, in that order. The report still counts every ticket by status and priority; a valid file with zero tickets yields zero counts.
Source: existing: README.md and scripts/weekly-report.js

### U-14: An operator checks history and notifications to verify that rollout preserves normal ticket activity
Flow: Compare history, the outbox, and ticket timestamps before and after preparation. Create, patch, resolve and reopen tickets and inspect their normal audit and notification effects. Merely passing a deadline has no write or delivery effect. Restart and check that the existing history, delivery state and next identifiers are still present.
Source: implied: assigning and reading due times must preserve existing audit, notification and persistence behavior

### U-15: A maintainer runs the test suite to check the change and the existing service together
Flow: Run `npm test` on the changed repository. It discovers the new `node:test` tests under `test/` and runs the existing tests as written.
Source: request

## Clauses

### C-1: A new ticket's deadline is based on its creation time
Observable: Compare a newly assigned deadline to the ticket's own `created`. The difference is the configured number of elapsed hours for its priority when created, with an hour equal to 3,600 seconds.
Source: request

### C-2: The default urgent response time is 4 hours
Observable: With no urgent override, an urgent ticket created at 2025-09-01T08:00:00.000Z is due at 2025-09-01T12:00:00.000Z.
Source: request

### C-3: The default high response time is 24 hours
Observable: With no high override, a high ticket created at 2025-09-01T08:00:00.000Z is due at 2025-09-02T08:00:00.000Z.
Source: request

### C-4: The default normal response time is 72 hours
Observable: With no normal override, a normal ticket created at 2025-09-01T08:00:00.000Z is due at 2025-09-04T08:00:00.000Z.
Source: request

### C-5: The default low response time is 168 hours
Observable: With no low override, a low ticket created at 2025-09-01T08:00:00.000Z is due at 2025-09-08T08:00:00.000Z.
Source: request

### C-6: Operators can configure the response hours without changing code
Observable: Restart with different response hours for a priority and see those hours used for tickets newly assigned deadlines at that priority.
Source: request

### C-7: Each priority has its own environment variable for its response hours
Observable: Set `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` or `DUE_HOURS_LOW` to override the corresponding priority independently.
Source: choice: per-priority overrides follow the service's environment configuration convention

### C-8: Unset or blank response-hour settings use their defaults
Observable: Omit an override or give it an empty or whitespace-only value to get that priority's default duration.
Source: existing: README.md and src/config.js

### C-9: A response-hour override is a positive whole number
Observable: A trimmed decimal integer such as `1` has the accepted form. Values such as `0`, `-1`, `1.5`, `1e2` or `four` are invalid.
Source: choice: use the existing whole-number environment setting convention for a positive response window

### C-10: An override that overflows the supported timestamp range is unusable
Observable: At startup an override must yield a representable deadline if applied to the current time. A resulting UTC instant beyond +275760-09-13T00:00:00.000Z is outside the service's timestamp range.
Source: choice: the timestamp range supplies the upper boundary without a separate policy limit in hours

### C-11: An invalid response-hour setting fails startup
Observable: Start with an invalid response-hour override. The process exits with status 2 before serving requests and its standard error names the variable.
Source: existing: README.md and src/server.js

### C-12: Changing response hours leaves assigned deadlines fixed
Observable: Restart with a different duration for the priority of a ticket that already has a deadline. The ticket retains that deadline.
Source: request

### C-13: Changing priority leaves the ticket's deadline fixed
Observable: Patch an urgent ticket to low, or a low ticket to urgent. Its deadline is the same before and after the patch.
Source: request

### C-14: Editing a title leaves the ticket's deadline fixed
Observable: Patch the title of a ticket with an assigned deadline. Its deadline retains its value.
Source: implied: the request says a due time is set once

### C-15: Lifecycle transitions leave the ticket's deadline fixed
Observable: Move a ticket through permissible states, including reopening from resolved. Every returned deadline retains its value.
Source: implied: the request says a due time is set once

### C-16: The API exposes every returned ticket's deadline as `due` when enabled
Observable: Inspect a ticket in the 201 create response, a 200 detail response, any returned list item, a successful patch response including a no-op, or a successful transition response. Each ticket object has its assigned value in `due`, regardless of status.
Source: request

### C-17: The API represents `due` using the service's UTC timestamp convention
Observable: Read a deadline as an ISO 8601 UTC string with millisecond precision, for example `2025-09-01T12:00:00.000Z`.
Source: existing: docs/api.md and src/store.js

### C-18: A client cannot set the deadline through a ticket request
Observable: Include `due` in a create, patch or transition body. The API rejects it as an unknown field with HTTP 400 `invalid`.
Source: implied: deadline assignment is server-owned and the existing endpoints reject unknown fields

### C-19: Only the value `on` enables due-time API behavior
Observable: Start with `DUE_TIMES=on` to enable the feature. Unset, empty, `off`, `ON`, `1` and values with surrounding whitespace leave it disabled.
Source: request

### C-20: Disabled mode retains the 1.4.0 ticket response shape
Observable: With due times disabled, compare create, detail, list, patch and transition ticket objects to the 1.4.0 shape of `id`, `title`, `priority`, `requester`, `status`, `created` and `updated`, even when the saved ticket has a deadline.
Source: request

### C-21: The list ignores the `overdue` parameter when due times are disabled
Observable: In disabled mode, `GET /tickets` returns the same status and body with or without an `overdue` parameter, including `true`, `false` or an otherwise invalid value, for the same remaining parameters and ticket state.
Source: request

### C-22: Disabled mode retains the other 1.4.0 HTTP responses
Observable: With due times disabled, unchanged requests into equivalent state have the 1.4.0 status codes and response bodies, including existing validation, history, health and outbox responses.
Source: request

### C-23: `overdue=true` restricts results to tickets with an active status
Observable: Among tickets with passed deadlines, an enabled overdue list can contain `open` or `in_progress` tickets. `resolved` and `closed` tickets are excluded.
Source: request

### C-24: `overdue=true` restricts results to tickets past their deadlines
Observable: Hold an active ticket's deadline at 2025-09-01T12:00:00.000Z. It is absent when the current time is 2025-09-01T11:59:59.999Z and present when the current time is 2025-09-01T12:00:00.001Z.
Source: request

### C-25: A deadline equal to the current instant has yet to pass
Observable: An active ticket is excluded by `overdue=true` when the current time equals its `due` exactly.
Source: choice: treat “has passed” as strictly earlier than the current time

### C-26: Overdue membership is evaluated as of a single current instant per request
Observable: Advance the clock past an active ticket's deadline with the worker disabled. The next enabled overdue request includes that ticket without a write. Tickets on the same page are judged against the same instant.
Source: implied: listing overdue tickets depends on whether their deadline has passed at the time of the listing

### C-27: An overdue listing uses the current ticket status
Observable: An overdue in-progress ticket drops out on resolution. If it is reopened after its deadline, it appears again on the next overdue request.
Source: implied: only currently open or in-progress tickets qualify

### C-28: An omitted `overdue` parameter applies no deadline restriction
Observable: With due times enabled, a normal list without `overdue` can include both future-due tickets and tickets with passed deadlines.
Source: implied: the request defines a filter selected by `overdue=true`

### C-29: `overdue=false` leaves deadline filtering off
Observable: With due times enabled, adding `overdue=false` produces the same list as omitting it for the same remaining query and state.
Source: choice: provide the ordinary false value for the optional Boolean filter

### C-30: An unsupported `overdue` value is an invalid query in enabled mode
Observable: Send `overdue=`, a bare `overdue`, `overdue=TRUE`, `overdue=1` or any decoded value other than `true` or `false`. The API answers 400 `invalid` with a human-readable message naming `overdue`.
Source: choice: validate the new parameter like the existing enumerated query parameters

### C-31: Repeating `overdue` uses the first value
Observable: With due times enabled, `overdue=true&overdue=false` acts like `overdue=true`, and a malformed first value still yields an invalid query.
Source: choice: follow the existing list query's first-value convention

### C-32: The overdue restriction combines with the status filter
Observable: With `overdue=true&status=open` an otherwise matching in-progress ticket is excluded. With `overdue=true&status=resolved` the result is empty.
Source: implied: an overdue listing honors the existing status filter

### C-33: The overdue restriction combines with the current priority filter
Observable: With `overdue=true&priority=urgent`, an overdue normal ticket is excluded. After changing its priority to urgent it can match using its original deadline.
Source: implied: priority still filters the current ticket while the deadline is fixed

### C-34: An overdue list requires all supplied filters to match
Observable: On an enabled API, a query for `overdue=true&status=open&priority=urgent` excludes both an overdue normal open ticket and an overdue urgent in-progress ticket.
Source: choice: use the conjunction documented in docs/api.md for overdue listings while preserving the current behavior of ordinary queries

### C-35: A disabled list preserves the 1.4.0 behavior for combined filters
Observable: On a disabled API, `status=open&priority=urgent` still includes tickets matching either filter, as 1.4.0 actually does.
Source: existing: src/tickets/query.js

### C-36: An ordinary enabled list preserves the current combined-filter behavior
Observable: With due times enabled, `status=open&priority=urgent` without an overdue restriction still includes tickets matching either filter.
Source: choice: preserve existing ordinary list behavior where the new filter is unused

### C-37: Overdue filtering happens before pagination
Observable: Interleave matching and nonmatching tickets, then request `overdue=true&limit=2`. The page contains the first two matching tickets when at least two qualify, and its cursor advances past the last ticket returned.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-38: An overdue query with no remaining matches produces an empty last page
Observable: Query an empty store, a set with no matches, or after a cursor beyond the last current match. Receive HTTP 200 with `{"items":[],"next":null}`.
Source: existing: docs/decisions/0005-cursor-pagination.md and src/pagination.js

### C-39: A deadline passing does not change ticket status
Observable: Leave a ticket open as the clock crosses its deadline. It is still open on GET.
Source: implied: overdue is a filter on existing lifecycle statuses

### C-40: Reading for overdue tickets does not change ticket state
Observable: Compare saved state before and after a series of overdue list requests with the worker disabled and no other activity. The requests make no saved changes.
Source: implied: the new GET parameter is a read filter

### C-41: A deadline passing does not enqueue a notification
Observable: Leave a ticket undisturbed as its deadline passes. No new notification appears in the outbox because of that deadline.
Source: implied: the request adds a deadline and a filter to the existing notification workflow

### C-42: The release backfills deadlines for all production tickets that lack them
Observable: Prepare a legacy file containing more than 100 tickets across all four statuses. Each receives a deadline, with no ticket omitted due to its status or age.
Source: request

### C-43: Backfill calculates each missing deadline from that ticket's saved creation time
Observable: Prepare a ticket whose saved `created`, saved `updated` and preparation time differ. Its deadline equals the saved `created` plus the response duration.
Source: request

### C-44: Backfill selects response hours from the ticket's own stored priority
Observable: Prepare a legacy ticket whose saved priority differs from its creation audit entry. Its missing deadline uses the duration configured for the priority in the saved ticket record at preparation.
Source: implied: the request bases backfill on the existing tickets' own priority

### C-45: Backfill preserves deadlines already present in a partially prepared file
Observable: Prepare a file with both assigned and missing deadlines under a changed schedule. Only the missing deadlines receive newly calculated values.
Source: implied: a persisted deadline is set once

### C-46: The new release can prepare an existing file with visibility disabled
Observable: Start the new release on a valid file with missing deadlines while due times are disabled, including with the worker off. By the time it serves requests, the missing deadlines are saved to that file.
Source: choice: startup preparation lets the operator finish storage rollout before enabling visibility without a new command

### C-47: An enabled persistent service accepts traffic only once its file holds the assigned deadlines
Observable: On a production start using existing tickets, the file contains every existing ticket's deadline before any due-enabled ticket response is available.
Source: request

### C-48: Enabled startup refuses a persistent file that still needs preparation
Observable: Start with `DUE_TIMES=on` on a file with any ticket missing its deadline. Startup fails before listening with a diagnostic identifying the file and the incomplete preparation.
Source: choice: fail closed at cutover and point the operator back to the preparation step

### C-49: Preparing an already complete file performs no backfill rewrite
Observable: Start on a fully prepared file with the worker disabled. Before any regular state change or shutdown save, the file is unchanged.
Source: choice: repeatable preparation should have no write to do once the file is complete

### C-50: The release records a new ticket's deadline even while due times are disabled
Observable: Create a ticket while due times are disabled with `DATA_FILE` set. At the successful response, the data file already holds that ticket's deadline based on the hours in effect at creation.
Source: choice: keep a prepared production file ready for cutover while it continues accepting tickets

### C-51: A first enabled start can serve an empty store
Observable: Start with due times enabled using a missing file, a valid file with zero tickets, or memory-only operation. Health is available and the first list is empty.
Source: implied: a store with no tickets has no existing deadlines to prepare

### C-52: An enabled persistent create cannot expose a ticket whose initial save failed
Observable: Make the destination unwritable after an enabled service starts. A create that fails to save is absent from subsequent ticket reads.
Source: implied: a persistent ticket must have a saved deadline before the enabled service shows it

### C-53: A successful persistent creation with due times enabled saves the assigned deadline with the ticket
Observable: Immediately after a successful create response with `DATA_FILE` set and visibility enabled, inspect the file to find the new ticket's assigned deadline.
Source: implied: a deadline set at creation must survive a restart

### C-54: Restarting the new release retains stored deadlines
Observable: Read a ticket's saved deadline, stop the new release, then reopen the file with the new release. The ticket has the same deadline.
Source: request

### C-55: Saving ordinary state preserves deadlines already recorded by the new release
Observable: After a ticket edit, an outbox delivery save or a normal shutdown, the file still contains the same deadlines for all previously prepared tickets. This holds with visibility enabled or disabled.
Source: implied: a whole-file rewrite must not discard deadlines that were set once

### C-56: Backfill leaves existing ticket data intact
Observable: Compare the pre-preparation ticket records to the prepared records while ignoring the added deadlines. All existing ticket IDs and field values, including `updated`, are the same.
Source: implied: backfill adds the deadline to records the service already holds

### C-57: Backfill leaves existing audit history intact
Observable: Compare the audit array before and after preparation. All existing audit entries retain their supported fields and values.
Source: implied: preparation supplies stored derived metadata rather than a new ticket action

### C-58: Backfill leaves the notification outbox intact
Observable: With the worker stopped, compare the outbox before and after preparation. It contains the same events, states, retry timestamps and next event ID.
Source: implied: deadline preparation causes no requester notification

### C-59: Backfill leaves the ticket sequence intact
Observable: Compare `nextNumber` before and after preparation. The next ticket created still uses that number.
Source: implied: backfill works on existing tickets and does not create tickets

### C-60: Preparation publishes a complete saved state atomically
Observable: Observe the file during preparation. A reader or crash can see the old complete document or the new complete document with deadlines, never a partly written document or an intermediate backfill.
Source: existing: docs/decisions/0008-json-data-file.md

### C-61: A preparation that cannot persist its result does not start the service
Observable: Prepare a legacy file that can be read but cannot be replaced. The service exits before listening and standard error identifies a failure to save that file.
Source: implied: production cannot enable due times until preparation is durable

### C-62: A failed preparation leaves the original file intact
Observable: Fail validation or the write during preparation, then compare the original file. Its contents are unchanged and retrying against it remains possible after the cause is corrected.
Source: implied: a failed upgrade must leave the production state usable

### C-63: Any stored deadline must be valid when read
Observable: A ticket with a present deadline that is null, a number, malformed or outside the service's ISO 8601 UTC timestamp convention is refused as invalid data. The diagnostic identifies the file and the offending ticket field, such as `tickets[3].due`.
Source: choice: validate supplied deadline values like persisted timestamps instead of treating corruption as a missing deadline

### C-64: An assigned deadline must be later than the ticket's creation time
Observable: A stored deadline at or before the saved `created` instant is refused with a diagnostic identifying the ticket field.
Source: choice: every supported response duration is positive

### C-65: Preparation rejects a ticket whose calculated deadline cannot be represented
Observable: If the saved creation instant plus its response duration is beyond the supported timestamp range, startup fails with a diagnostic identifying the file and the affected ticket record.
Source: implied: preparation cannot commit a ticket for which it cannot supply a usable deadline

### C-66: A create whose deadline cannot be represented returns the usual internal error
Observable: If the clock reaches a point after startup at which a create would overflow the timestamp range, it returns HTTP 500 `internal` before allocating an ID or making the ticket change.
Source: choice: an unrepresentable server-assigned timestamp is a server fault and must not produce a partial creation

### C-67: A file written by the new release starts on unmodified 1.4.0
Observable: After preparation and subsequent saves by the new release, start the original 1.4.0 on the resulting file. It starts without requiring prior conversion or an older data snapshot.
Source: request

### C-68: Rollback keeps every ticket visible to 1.4.0
Observable: On 1.4.0, page through the same file after rollback. Every existing ticket, including ones created by the new release, appears with its original ID and legacy fields.
Source: request

### C-69: The new release writes version 1 data files
Observable: Inspect the document's `version` after preparation or a regular save. It is `1`, the version accepted by unmodified 1.4.0.
Source: existing: src/persistence.js

### C-70: Rollback continues allocating ticket IDs from the saved sequence
Observable: Use the rolled-back service to create a ticket. It uses the next number stored by the new release.
Source: implied: preserving the existing service on rollback includes continuing its workflow on the same state

### C-71: The rollback runbook captures assigned deadlines before 1.4.0 owns the file
Observable: The instructions for switching back tell the operator to save a copy of the latest prepared file before starting 1.4.0. They identify that release's next whole-file save, including on shutdown, as the point at which its writer drops the added deadline data.
Source: choice: use the existing file-copy backup mechanism to retain deadlines that the old writer cannot preserve

### C-72: The rollout runbook explains how to recover assigned deadlines after a rollback save
Observable: The instructions explain how to recover deadlines by ticket ID from the retained copy into the latest 1.4.0 data with the file owner stopped. The operator keeps changes made under 1.4.0 and prepares only tickets still missing deadlines before enabling visibility. The latest file remains the source of ticket, audit and outbox state.
Source: choice: support returning to the new release with fixed deadlines through the operator's existing backup and offline file-maintenance workflow

### C-73: The operational documentation describes how to prepare a production file before enabling visibility
Observable: The operations instructions show how to choose the response-hour settings, prepare the file, verify that every ticket has a saved deadline, and then start with `DUE_TIMES=on`.
Source: implied: operators need a way to satisfy the production cutover condition

### C-74: The API documentation describes the deadline field
Observable: The API reference describes when ticket responses carry `due` and what it means.
Source: implied: clients need to discover the new ticket response field

### C-75: The API documentation describes overdue listing
Observable: The API reference describes the supported overdue query and its interactions with existing filters and pages. It identifies how ordinary lists differ when combining existing filters.
Source: implied: clients need to discover how to request overdue tickets

### C-76: The configuration documentation describes how to change the response hours
Observable: The README identifies the settings, their defaults of 4, 24, 72 and 168 hours for urgent, high, normal and low, respectively, and the effect of restarting with a new schedule.
Source: implied: operators must be able to configure the promised hours

### C-77: Ticket numbers start at 1 in a fresh store
Observable: The first successful ticket creation in an empty store with no prior state returns `T-0001`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md and src/store.js

### C-78: Ticket IDs use their existing canonical format
Observable: IDs use the uppercase prefix `T-` with the positive safe integer sequence padded to at least four digits. The sequence extends from `T-9999` to `T-10000`; `T-0000`, `T-1` and `T-00001` are not valid IDs.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md and src/tickets/ids.js

### C-79: Ticket numbers are allocated in increasing sequence
Observable: Successive successful creates allocate successive numbers, including after restart on the same file.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-80: Creating a ticket returns HTTP 201 with the new ticket
Observable: Send a valid `POST /tickets` and receive the created ticket in the 201 response.
Source: existing: docs/api.md

### C-81: A newly created ticket starts open
Observable: A successful `POST /tickets` produces a ticket with `status: "open"`.
Source: existing: docs/api.md

### C-82: A newly created ticket records the creation instant
Observable: A successful create sets `created` to the service's time of creation.
Source: existing: docs/api.md and src/store.js

### C-83: A newly created ticket has its creation instant as its initial update time
Observable: The newly created ticket has `updated` equal to `created`.
Source: existing: src/store.js

### C-84: Omitting priority on creation uses normal
Observable: Submit a valid title and requester without priority. The new ticket has `priority: "normal"`.
Source: existing: docs/api.md

### C-85: Ticket write validation accepts only the four existing priorities
Observable: On create or patch, a supplied priority must be exactly `low`, `normal`, `high` or `urgent`. An empty, unknown, non-string or differently cased value produces 400 `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-86: Ticket write validation requires a nonempty title string when supplying a title
Observable: A missing create title, a non-string title or a title empty after trimming produces 400 `invalid`. Omission is allowed on a priority-only patch.
Source: existing: src/tickets/validate.js

### C-87: Title length is limited to 200 characters after trimming
Observable: A valid single-line title of 200 JavaScript string code units is accepted. One of 201 is rejected with 400 `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-88: Ticket write validation requires a nonempty requester string on creation
Observable: A missing, non-string or whitespace-only requester produces 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-89: Requester length is limited to 64 characters after trimming
Observable: A valid single-line requester of 64 JavaScript string code units is accepted. One of 65 is rejected with 400 `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-90: Ticket text is stored after trimming surrounding whitespace
Observable: Submit title or requester text with surrounding whitespace. The returned value is trimmed.
Source: existing: src/tickets/validate.js

### C-91: Ticket text rejects control characters inside the trimmed text
Observable: Submit a title or requester with an embedded tab, newline or other character in U+0000–U+001F or U+007F. The request returns 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-92: A write body must be a JSON object
Observable: Send an empty or whitespace-only body, malformed JSON, or valid JSON containing an array, null or another non-object value to a ticket write route. Receive 400 `invalid`.
Source: existing: docs/api.md and src/http.js

### C-93: A ticket write body cannot contain fields outside its route's allowed set
Observable: Create takes `title`, `requester` and `priority`; patch takes `title` and `priority`; transition takes `to`. An additional body field gets 400 `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-94: A ticket request body can be at most the configured byte limit
Observable: Submit an otherwise valid JSON body padded to exactly the configured limit in bytes and receive the normal success. Submit one byte more and receive 400 `invalid`.
Source: existing: README.md and src/http.js

### C-95: Ticket detail returns the requested ticket
Observable: Send `GET /tickets/:id` for a present ticket and receive HTTP 200 with that ticket.
Source: existing: docs/api.md

### C-96: A successful patch returns the current ticket
Observable: Send a valid `PATCH /tickets/:id` with a changed title, a changed priority or both for a mutable ticket. The 200 response contains the resulting values.
Source: existing: docs/api.md

### C-97: A patch must supply at least one editable field
Observable: Send `{}` to the patch endpoint. Receive 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-98: A closed ticket cannot be patched
Observable: Send a valid patch to a closed ticket, including one that resubmits its current values. Receive 409 `conflict`.
Source: existing: docs/api.md and src/store.js

### C-99: A no-op patch leaves the update timestamp unchanged
Observable: Patch a mutable ticket using its current normalized values. The request succeeds and `updated` retains its old value.
Source: existing: docs/api.md

### C-100: A no-op patch adds no audit entry
Observable: Compare history before and after a valid patch that changes no field. The history is identical.
Source: existing: docs/api.md

### C-101: A no-op patch adds no notification
Observable: With the worker off, compare the outbox before and after a valid patch that changes no field. The outbox is identical.
Source: existing: CONTRIBUTING.md and src/store.js

### C-102: A change to a ticket sets its update timestamp to the time of the change
Observable: Move the clock forward and make a successful field edit or lifecycle transition. The ticket's `updated` shows the new time.
Source: existing: docs/api.md and src/store.js

### C-103: A change to a ticket preserves its creation timestamp
Observable: After a successful edit or lifecycle transition, the ticket still has the same `created` value.
Source: existing: docs/api.md and src/store.js

### C-104: A transition requires a recognized destination status
Observable: A `POST /tickets/:id/transition` body must supply `to` as exactly one of `open`, `in_progress`, `resolved` or `closed`. A missing or unsupported value returns 400 `invalid`.
Source: existing: docs/api.md and src/tickets/validate.js

### C-105: A valid lifecycle transition returns HTTP 200 with the moved ticket
Observable: Make a permitted transition and receive the ticket with the requested destination status in the 200 response.
Source: existing: docs/api.md

### C-106: The lifecycle permits only the existing four moves
Observable: The allowed moves are `open` to `in_progress`, `in_progress` to `resolved`, `resolved` to `closed`, or `resolved` to `open`.
Source: existing: docs/api.md and src/tickets/states.js

### C-107: Any other move to a recognized status conflicts with the ticket's state
Observable: Request a skipped, backwards, same-state or closed-origin transition outside the permitted set. Receive 409 `conflict`.
Source: existing: docs/api.md and src/tickets/states.js

### C-108: Rejected ticket writes leave state unchanged
Observable: Compare the tickets, audit and outbox before and after a validation failure or a refused lifecycle action. They are identical.
Source: existing: src/app.js and src/store.js

### C-109: Requests for missing tickets return 404 `not_found`
Observable: Send a valid detail, patch, transition or history request for an absent ticket. Receive 404 `not_found`; lookup of a noncanonical ID likewise finds no ticket.
Source: existing: docs/api.md and src/store.js

### C-110: A ticket list is an HTTP 200 cursor page
Observable: A valid list request returns an object with `items` and `next` as its only fields, including for a filtered page.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-111: An unfiltered list can return tickets in every status
Observable: Without any filters, paging through a store with open, in-progress, resolved and closed tickets returns all of them.
Source: existing: docs/api.md and src/tickets/query.js

### C-112: A status filter alone selects exactly that status
Observable: Pass `status=open`, `in_progress`, `resolved` or `closed`. Every result with only that filter has the requested status.
Source: existing: docs/api.md

### C-113: A priority filter alone selects exactly that priority
Observable: Pass `priority=low`, `normal`, `high` or `urgent`. Every result with only that filter has the requested priority.
Source: existing: docs/api.md

### C-114: An invalid status filter returns 400 `invalid`
Observable: Send a status filter with an empty, unknown or differently cased value. Receive 400 `invalid`.
Source: existing: docs/api.md and src/tickets/query.js

### C-115: An invalid priority filter returns 400 `invalid`
Observable: Send a priority filter with an empty, unknown or differently cased value. Receive 400 `invalid`.
Source: existing: docs/api.md and src/tickets/query.js

### C-116: Repeated existing query parameters still use their first value
Observable: For the existing `status`, `priority`, `limit` and `cursor` parameters, subsequent occurrences of the same parameter do not affect the result.
Source: existing: src/tickets/query.js

### C-117: Ticket listing order is ascending numeric ticket ID
Observable: Ticket `T-9999` appears before `T-10000` when both match a list, including an overdue list.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-118: A list page defaults to a limit of 20
Observable: Query without `limit` when at least 21 tickets match. The first page has 20 items.
Source: existing: docs/api.md

### C-119: A specified page limit must be a whole number from 1 through 100
Observable: `limit=1` and `limit=100` are accepted. An empty limit, 0, 101, a negative, a fraction or nondigit text yields HTTP 400 `invalid`.
Source: existing: docs/api.md and src/tickets/query.js

### C-120: An omitted cursor starts at the beginning of the matching tickets
Observable: With at least one match, a request without a cursor starts with the lowest matching ticket ID.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-121: A next-page cursor starts strictly after the last returned ID
Observable: Pass the previous page's opaque `next` as `cursor` with the same filters. No matching ID at or below the previous page's last ID reappears, even if the cursor ticket no longer matches.
Source: existing: docs/decisions/0005-cursor-pagination.md and src/pagination.js

### C-122: A list page has a next cursor exactly when another matching item remains
Observable: A page with more matches beyond it has a non-null `next`. A last page has `next: null`, including when the page size exactly equals the number of remaining matches.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-123: An invalid cursor returns 400 `invalid`
Observable: Pass an empty, malformed or unsupported-version cursor, or one with a noncanonical ticket ID as its key. Receive 400 `invalid`.
Source: existing: src/pagination.js and src/store.js

### C-124: Existing cursors remain usable
Observable: Reuse a cursor returned by 1.4.0 with the same query after starting the new release in disabled mode. Paging continues after the same ticket ID.
Source: implied: disabled mode answers as 1.4.0 does

### C-125: Unknown list query parameters are ignored
Observable: Adding `offset=40` or another unrecognized parameter does not change a page for the same recognized parameters.
Source: existing: docs/decisions/0005-cursor-pagination.md and test/query.test.js

### C-126: HTTP responses use the existing JSON media type
Observable: Check `Content-Type` on either a success or an error. It is `application/json; charset=utf-8`.
Source: existing: docs/api.md and src/http.js

### C-127: HTTP errors use the existing error envelope
Observable: Error responses carry `error.code` for programmatic branching and a human-readable string in `error.message`. The wording of a diagnostic is not a client contract.
Source: existing: docs/decisions/0004-error-envelope.md

### C-128: Unexpected faults produce a generic 500 `internal` response
Observable: Induce an unexpected handler fault. The response is HTTP 500 with code `internal` and a generic message, with no internal details or stack trace.
Source: existing: docs/decisions/0004-error-envelope.md and src/errors.js

### C-129: Unexpected handler faults are logged
Observable: Induce an unexpected handler fault and see the cause in the service's standard error log.
Source: existing: docs/decisions/0004-error-envelope.md and src/app.js

### C-130: An unknown route returns 404 `not_found`
Observable: Request a path with no matching route. Receive 404 `not_found`.
Source: existing: docs/api.md and src/app.js

### C-131: An unsupported method returns 404 `not_found`
Observable: Send `DELETE /tickets/T-0001`. Receive 404 `not_found` with a message naming the methods supported on that path.
Source: existing: src/app.js and test/api.test.js

### C-132: Routes tolerate a trailing slash
Observable: Request `GET /tickets/` with the same query as `GET /tickets`. Both requests route to the same endpoint.
Source: existing: src/router.js

### C-133: Path parameters are decoded
Observable: An existing ticket named `T-0007` can also be read with `GET /tickets/T%2D0007`.
Source: existing: src/router.js

### C-134: Bad percent encoding in a matched path parameter is invalid
Observable: Request a ticket with malformed percent encoding in its path segment. Receive 400 `invalid`.
Source: existing: src/router.js

### C-135: Health keeps its existing response
Observable: While the service serves requests, `GET /health` returns HTTP 200 and `{"status":"ok"}`.
Source: existing: docs/api.md and src/app.js

### C-136: The audit endpoint returns only the requested ticket's history in append order
Observable: Interleave changes on two tickets and request the first one's `GET /tickets/:id/audit`. The 200 response contains its oldest-first entries in `items`.
Source: existing: docs/decisions/0007-append-only-audit-log.md and src/app.js

### C-137: Audit sequence numbers are the one-based positions in the whole log
Observable: Compare the history of two tickets changed in interleaved requests. Their entries' `seq` values identify the positions in the whole log, starting at 1.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-138: Existing audit entries remain append-only
Observable: After additional ticket changes, preparation and a restart, earlier entries have the same values and sequence numbers.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-139: Each ticket mutation uses its existing audit action
Observable: Create, edit and move a ticket. Each change contributes one entry with `ticket`, `at` and its respective `action` of `ticket.created`, `ticket.updated` or `ticket.transitioned`.
Source: existing: docs/api.md and src/store.js

### C-140: Audit changes record each changed field as a before-after pair
Observable: Patch a title to its current value while changing priority. The update entry's `changes` has only the priority's `from` and `to`. A lifecycle entry records the corresponding status change.
Source: existing: docs/decisions/0007-append-only-audit-log.md and src/store.js

### C-141: The creation audit entry retains its existing four change fields
Observable: Inspect `ticket.created` in either mode. Its `changes` records `title`, `priority`, `requester` and `status`, each with `from: null` and the initial value as `to`.
Source: existing: docs/api.md and test/store.test.js

### C-142: The supplied actor is recorded after trimming
Observable: Change a ticket with a valid `X-Actor` header with surrounding whitespace. The audit entry's `actor` is the trimmed name.
Source: existing: docs/api.md and src/http.js

### C-143: A missing or blank actor is recorded as `system`
Observable: Make a successful ticket change without an `X-Actor` header or with only whitespace in it. The audit actor is `system`.
Source: existing: docs/api.md and src/http.js

### C-144: An actor name can have at most 64 characters after trimming
Observable: A valid `X-Actor` value of 64 JavaScript string code units is accepted. A value of 65 returns 400 `invalid`.
Source: existing: docs/api.md and src/http.js

### C-145: Creating a ticket enqueues its received notification
Observable: With the worker stopped, create a ticket. The outbox shows a new `ticket.created` event addressed to the ticket's requester.
Source: existing: docs/api.md and src/store.js

### C-146: Resolving a ticket enqueues its resolved notification
Observable: With the worker stopped, resolve a ticket with no pending resolution event. The outbox shows a new `ticket.resolved` event addressed to the requester.
Source: existing: docs/api.md and src/store.js

### C-147: Notifications retain their existing keys
Observable: A creation or resolution notification's key is its event type followed by a colon and the ticket's ID, for example `ticket.created:T-0001`.
Source: existing: src/store.js and test/store.test.js

### C-148: A pending notification key prevents duplicate enqueue
Observable: Resolve, reopen and resolve a ticket again while its first resolution event is pending. The outbox still contains just one event for those two resolutions.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-149: A sent or dead notification no longer reserves its key
Observable: After a resolution event is sent or dead, reopen and resolve the ticket. A fresh notification with the same key can be enqueued.
Source: existing: src/outbox.js

### C-150: New outbox records start in the pending state
Observable: A newly enqueued event has `status: "pending"`, `attempts: 0`, and null `lastError` and `sentAt`.
Source: existing: src/outbox.js

### C-151: A new notification is eligible for delivery immediately
Observable: A newly enqueued event has `nextAttemptAt` equal to its `created` instant.
Source: existing: src/outbox.js

### C-152: Ticket mutations persist their associated audit and notification effects as one state change
Observable: A successful persistent create or resolve writes the ticket state with its audit entry and any newly enqueued notification in the same saved state.
Source: existing: docs/decisions/0006-notification-outbox.md and docs/decisions/0007-append-only-audit-log.md

### C-153: Requests do not deliver mail directly
Observable: Disable the worker and create or resolve a ticket. The request completes without a mail delivery and its notification is pending.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-154: The outbox endpoint groups events by their existing states
Observable: `GET /admin/outbox` returns HTTP 200 with `pending`, `sent` and `dead` arrays, including an empty array for a state without events.
Source: existing: docs/api.md and src/outbox.js

### C-155: Outbox records retain their existing content
Observable: An outbox event has `id`, `key`, `type`, `to`, `ticket`, `data`, `status`, `attempts`, `created`, `nextAttemptAt`, `lastError` and `sentAt`. The data for ticket notifications contains the title.
Source: existing: docs/api.md and src/store.js

### C-156: The worker delivers eligible pending emails on its ticks
Observable: A worker tick attempts delivery for events still pending whose `nextAttemptAt` is at or before its time. Events scheduled in the future wait.
Source: existing: docs/decisions/0006-notification-outbox.md and src/outbox.js

### C-157: The worker is the service's only scheduled work loop
Observable: Start with `WORKER_INTERVAL_MS=0`. No background job runs and queued notifications stay pending.
Source: existing: docs/decisions/0006-notification-outbox.md and CONTRIBUTING.md

### C-158: A successful delivery is recorded as sent
Observable: After a successful delivery, the event has `status: "sent"`, an incremented attempt count, the send time in `sentAt`, and null `nextAttemptAt` and `lastError`. The worker does not attempt it again.
Source: existing: src/outbox.js and test/worker.test.js

### C-159: The first four delivery failures schedule retries with the existing delay
Observable: A pending event's successive retries are set 1, 2, 4 and 8 seconds after failures one through four, respectively. The backoff calculation is capped at 300 seconds.
Source: existing: docs/operations.md and src/backoff.js

### C-160: The fifth delivery failure makes the event dead
Observable: After 5 failed attempts the event has `status: "dead"` and null `nextAttemptAt`. It is no longer attempted.
Source: existing: docs/operations.md and src/outbox.js

### C-161: Failed deliveries record the latest error
Observable: On each failure, `lastError` contains the error text truncated to 500 JavaScript string code units.
Source: existing: docs/operations.md and src/outbox.js

### C-162: The worker logs a warning when a notification dies
Observable: On the fifth failed delivery, a warning on standard error identifies the dead notification.
Source: existing: docs/operations.md and src/worker.js

### C-163: Finished notifications are retained
Observable: After further tickets, background activity and a restart on the data file, the same sent and dead events remain visible in the outbox.
Source: existing: docs/operations.md

### C-164: Notification delivery remains at least once
Observable: If the process dies after delivery but before the send is saved, restart reattempts the pending event with the same key and event ID.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-165: File notifications use the existing JSON lines contract
Observable: With `NOTIFY_FILE` set, each delivery appends one JSON line with `at`, `id`, `key`, `type`, `to`, `ticket`, `subject` and `body`.
Source: existing: docs/operations.md and src/notifier.js

### C-166: Notification text continues to use the existing event templates
Observable: Creation produces the existing received subject and body, and resolution produces the existing resolved subject and body. The feature adds no deadline content to those templates.
Source: existing: src/templates.js

### C-167: An event with no notification template follows the failure path
Observable: A due event whose type has no template fails delivery and follows the existing retry policy.
Source: existing: docs/decisions/0006-notification-outbox.md and src/templates.js

### C-168: The notifier keeps deliveries in memory when `NOTIFY_FILE` is unset
Observable: With no notification file configured, the notifier delivers to its in-process record of deliveries.
Source: existing: README.md and test/notifier.test.js

### C-169: The service runs through the existing start command
Observable: Run `npm start` to launch `src/server.js` and listen on the port selected by `PORT`.
Source: request

### C-170: The service runs on Node.js 22 or later
Observable: Run the existing service commands on Node.js 22.
Source: existing: README.md and package.json

### C-171: The service uses no npm dependencies
Observable: Run the service from the repository on a supported Node.js installation using the standard library without installing packages.
Source: request

### C-172: The default listener port is 4180
Observable: Start with `PORT` unset or empty and the service listens on 4180 when that port is available.
Source: existing: README.md and src/config.js

### C-173: The configured port is a whole number from 0 through 65535
Observable: `PORT=0` binds an available system-selected port. `PORT=65535` is a valid setting. A negative, fractional, nonnumeric or larger value fails configuration.
Source: existing: src/config.js

### C-174: The worker interval defaults to 500 milliseconds
Observable: Start with `WORKER_INTERVAL_MS` unset or empty and the service uses a 500 ms delivery interval.
Source: existing: README.md and src/config.js

### C-175: The worker interval setting accepts whole milliseconds from 0 through 3600000
Observable: `WORKER_INTERVAL_MS=0` and `WORKER_INTERVAL_MS=3600000` are valid settings. A negative, fractional, nonnumeric or larger value fails configuration.
Source: existing: src/config.js

### C-176: The request body limit defaults to 65536 bytes
Observable: Omit `MAX_BODY_BYTES` or leave it empty. The default body limit is 65536 bytes.
Source: existing: README.md and src/config.js

### C-177: The body limit setting accepts whole byte counts from 1024 through 1048576
Observable: `MAX_BODY_BYTES=1024` and `MAX_BODY_BYTES=1048576` are valid settings. Values of 1023, 1048577, fractions or nonnumeric text fail configuration.
Source: existing: src/config.js

### C-178: Request logging only activates for `LOG_REQUESTS=1`
Observable: With `LOG_REQUESTS=1`, each handled request adds a line to standard error with method, URL, status and elapsed time. With the variable absent or set to another value, request logging is off.
Source: existing: README.md and src/log.js

### C-179: Unusable startup configuration is diagnosed by variable name
Observable: Start with an unusable existing setting such as `PORT=http`. The process exits with status 2, serving no requests, and standard error names the variable.
Source: existing: README.md and src/server.js

### C-180: The service shuts down gracefully on its existing signals
Observable: Send SIGTERM or SIGINT to the service. It stops its worker, finishes in-flight requests and saves its state before exiting successfully.
Source: existing: docs/operations.md and src/server.js

### C-181: Omitting the data file keeps the service in memory
Observable: With `DATA_FILE` unset or empty, a ticket exists for the life of that process. Restarting it without a file starts with an empty store.
Source: existing: README.md and docs/decisions/0008-json-data-file.md

### C-182: A missing data file starts with empty state
Observable: Start with `DATA_FILE` pointing to a nonexistent file. The store initially has no tickets, audit entries or outbox events.
Source: existing: src/persistence.js and test/persistence.test.js

### C-183: A persistent service loads its whole state at startup
Observable: Restart on the same file and find the saved tickets, audit history, outbox state and next identifiers.
Source: existing: docs/decisions/0008-json-data-file.md

### C-184: State changes are saved to the configured data file
Observable: With `DATA_FILE` configured, inspect the file after a successful ticket change or outbox delivery attempt. The new state is present without waiting for shutdown.
Source: existing: docs/operations.md and src/store.js

### C-185: A successful save replaces the data file as a single complete document
Observable: Copy the data file while the service is active to obtain a consistent state. A successful save leaves no temporary file behind.
Source: existing: docs/decisions/0008-json-data-file.md and test/persistence.test.js

### C-186: The saved document retains the existing state keys
Observable: Inspect a save for `version`, `savedAt`, `nextNumber`, `tickets`, `audit` and `outbox` with `nextId` and `events`. The release preserves the shapes of the legacy fields so the original reader can consume them.
Source: existing: src/persistence.js

### C-187: Ticket deadlines are stored as a new optional field on version 1 ticket records
Observable: Inspect a prepared version 1 file for a `due` field on each ticket record. Legacy ticket records may omit that field.
Source: choice: the old reader ignores unknown ticket fields and keeping the deadline beside the old fields makes file inspection and offline recovery direct

### C-188: Startup rejects an unreadable data file
Observable: Start with an existing configured data file that cannot be read. The service exits with status 2 before listening and the diagnostic names the file.
Source: existing: src/persistence.js and src/server.js

### C-189: Startup rejects a malformed data document
Observable: Start with invalid JSON or a JSON value that is not an object. The process exits before listening and the diagnostic identifies the file.
Source: existing: src/persistence.js

### C-190: Startup accepts only data-file version 1
Observable: Start with an otherwise valid document with a missing version or `version: 2`. The process exits before listening and the diagnostic identifies the unsupported version.
Source: existing: src/persistence.js and test/persistence.test.js

### C-191: Startup validates that the saved collections have their existing types
Observable: Replace `tickets`, `audit` or `outbox.events` with a non-array, or replace `outbox` with a non-object. Startup refuses the file and identifies the failed field.
Source: existing: src/persistence.js

### C-192: Startup requires a positive safe integer for the next ticket number
Observable: A nonnumeric, fractional, zero, negative or larger-than-9007199254740991 `nextNumber` makes the file unusable.
Source: existing: src/persistence.js

### C-193: Startup refuses a next ticket number that could reuse an ID
Observable: In a saved file with `T-0002`, setting `nextNumber` to 2 causes refusal and the diagnostic names the conflicting ID.
Source: existing: docs/operations.md and test/persistence.test.js

### C-194: Startup refuses duplicate ticket IDs
Observable: Place two records with the same ID in a file. Startup refuses it and identifies the duplicate.
Source: existing: src/persistence.js

### C-195: A saved ticket record must be an object
Observable: Insert a scalar, array or null as a ticket record. Startup refuses it and identifies the record.
Source: existing: src/persistence.js

### C-196: A saved ticket requires a canonical ID
Observable: Give a saved ticket an absent or noncanonical ID such as `T-1`. Startup refuses it and identifies the ID field.
Source: existing: src/persistence.js

### C-197: A saved ticket requires a nonempty title string
Observable: Give a saved ticket an empty or non-string title. Startup refuses it and identifies the title field.
Source: existing: src/persistence.js

### C-198: A saved ticket requires a nonempty requester string
Observable: Give a saved ticket an empty or non-string requester. Startup refuses it and identifies the requester field.
Source: existing: src/persistence.js

### C-199: A saved ticket requires an existing priority
Observable: Give a saved ticket an unsupported priority. Startup refuses it with a diagnostic identifying the field, for example `tickets[3].priority`.
Source: existing: src/persistence.js and docs/operations.md

### C-200: A saved ticket requires an existing status
Observable: Give a saved ticket an unsupported status. Startup refuses it and identifies the status field.
Source: existing: src/persistence.js

### C-201: A saved ticket requires a parseable creation time string
Observable: Give a saved ticket a missing, non-string or unparseable `created`. Startup refuses it and identifies the creation field.
Source: existing: src/persistence.js

### C-202: A saved ticket requires a parseable update time string
Observable: Give a saved ticket a missing, non-string or unparseable `updated`. Startup refuses it and identifies the update field.
Source: existing: src/persistence.js

### C-203: Startup does not apply stricter HTTP-only field validation to legacy saved titles or requesters
Observable: The file reader continues accepting nonempty legacy string values for title and requester under its existing persistence rules, even when a new HTTP request would refuse those values.
Source: existing: src/persistence.js and src/tickets/validate.js

### C-204: Startup rejects a saved audit sequence with a gap
Observable: Remove or reorder an entry so that its neighbors no longer have sequence values equal to their one-based positions. Startup refuses the data file and the diagnostic identifies the affected entry.
Source: existing: docs/decisions/0007-append-only-audit-log.md and src/persistence.js

### C-205: Startup validates each audit record's existing fields
Observable: An audit record must be an object with nonempty strings for `ticket`, `action` and `actor`, a parseable string `at`, and an object of `changes` whose values each have `from` and `to`. Violating a field results in refusal identifying the affected record or field.
Source: existing: src/persistence.js

### C-206: Startup requires a positive safe integer for the next outbox event ID
Observable: A nonnumeric, fractional, zero, negative or larger-than-9007199254740991 `outbox.nextId` makes the file unusable.
Source: existing: src/persistence.js

### C-207: Startup refuses a next outbox event ID that could reuse an event ID
Observable: Set `outbox.nextId` to an existing event's ID or lower. Startup refuses the file and names the counter.
Source: existing: src/persistence.js

### C-208: Startup validates each outbox event's existing fields
Observable: An event record must be an object with a positive safe integer ID, nonempty strings for `key`, `type` and `to`, an existing outbox state, a nonnegative integer attempt count, a data object and a parseable string creation time. A pending event also requires a parseable string `nextAttemptAt`. Startup refuses a violation identifying the affected record or field.
Source: existing: src/persistence.js

### C-209: Data-file validation happens before the service listens
Observable: Start on a file with a bad record after otherwise valid records. No API response is served, the process exits with status 2 and standard error names the file and invalid record or field.
Source: existing: docs/operations.md and src/server.js

### C-210: The CLI uses the configured data file by default
Observable: Set `DATA_FILE` and invoke `node bin/tickets.js list` or `show ID` without `--data`. It reads that file.
Source: existing: README.md and bin/tickets.js

### C-211: An explicit CLI data path overrides the environment
Observable: Set `DATA_FILE` to one file, supply `--data FILE` for another and observe only the latter's tickets.
Source: existing: README.md and bin/tickets.js

### C-212: The CLI never changes the data file
Observable: Compare file bytes before and after `list` or `show` on a legacy, partially prepared or prepared valid file. It remains unchanged in every visibility mode.
Source: existing: README.md and docs/operations.md

### C-213: The CLI accepts either supported file layout
Observable: Use the new CLI to list or show tickets from valid files with or without saved deadlines, without having to run the server first.
Source: implied: the CLI must keep working against existing data and the new production file

### C-214: The human-readable CLI shows saved deadlines when enabled
Observable: With `DUE_TIMES=on` in the CLI's environment, both `show` and the ordinary table `list` identify each displayed ticket's stored deadline as due where it is present.
Source: choice: apply the visibility gate to human-readable ticket output without adding another setting

### C-215: The CLI does not invent deadlines for tickets without stored ones
Observable: With the CLI's due display enabled, showing a legacy ticket without a saved deadline displays no assigned deadline, regardless of the current response-hour settings.
Source: implied: CLI reads are read-only and a deadline is assigned once by the service

### C-216: The CLI documentation describes deadline visibility
Observable: The CLI instructions explain how operators display saved deadlines in human-readable output.
Source: implied: operators need to discover how to inspect deadlines from the command line

### C-217: The human-readable CLI preserves its existing output when visibility is disabled
Observable: Without due visibility, `list` uses its existing ID, STATUS, PRIORITY, REQUESTER, UPDATED and TITLE table columns, and `show ID` keeps its existing ticket details and history.
Source: existing: README.md and src/format.js

### C-218: The human-readable `show` command retains ticket history
Observable: Show a ticket using its ID and see its existing detail fields and the history for that ticket in chronological order, including when it has a due time.
Source: existing: bin/tickets.js and src/format.js

### C-219: CLI `list` retains its existing filters
Observable: Request `--status` or `--priority` to select the corresponding values. With both flags, the CLI retains its existing matching behavior of including tickets that match either value.
Source: existing: README.md, bin/tickets.js and src/tickets/query.js

### C-220: CLI `list` returns every match in numeric ticket ID order
Observable: List a file with more than 100 matching tickets. All matching IDs appear in increasing numeric order, including those beyond the first 100.
Source: existing: bin/tickets.js and docs/decisions/0002-prefixed-sequential-ids.md

### C-221: The human-readable CLI reports an empty list
Observable: Run ordinary `list` with no matching tickets. The result reports that there are no tickets.
Source: existing: bin/tickets.js

### C-222: Raw CLI output retains exactly four tab-separated columns in their existing order
Observable: For listed tickets written through the service, `list --raw` writes one line with ID, status, priority and title in that order, with no header or extra column. A raw list with no matches produces no lines.
Source: existing: README.md and src/format.js

### C-223: A successful CLI command exits 0
Observable: A successful `list`, `show ID` or standalone help request exits with status 0.
Source: existing: bin/tickets.js

### C-224: A CLI lookup for an absent ID exits 1
Observable: Run `show` with an ID absent from the file. The command exits with status 1 and reports the lookup failure on standard error.
Source: existing: bin/tickets.js

### C-225: CLI input failures exit 2
Observable: Run an unknown command or option, omit a required argument, pass an invalid filter, omit the data path, or point to a missing, unreadable or invalid file. The CLI exits with status 2 and reports the error on standard error.
Source: existing: bin/tickets.js

### C-226: The weekly report never changes the data file
Observable: Compare file bytes before and after generating the report from a legacy or prepared file. They are unchanged.
Source: existing: docs/operations.md

### C-227: The weekly report still counts tickets from the data file
Observable: Run `npm run report:weekly` with `DATA_FILE` or invoke the report with `--data FILE`. Its report includes the total and counts for all four statuses and all four priorities, including zero counts.
Source: existing: README.md and scripts/weekly-report.js

### C-228: The weekly report's JSON output retains its existing shape
Observable: Run the report with `--json`. Its JSON has the existing `total`, `byStatus` and `byPriority` keys and yields the same counts before and after preparation for the same tickets.
Source: existing: README.md and scripts/weekly-report.js

### C-229: The weekly report retains its human-readable output
Observable: Run the report without `--json`. It prints the existing date heading, status counts, priority counts and total.
Source: existing: scripts/weekly-report.js

### C-230: A failed weekly report exits 1
Observable: Invoke the report with a failing data-file read. It reports failure to standard error and exits with status 1.
Source: existing: scripts/weekly-report.js

### C-231: New due-time tests use `node:test` under `test/`
Observable: The new behavior is exercised by tests written with `node:test` in `test/`. They exercise the new due-time behavior specified above.
Source: request

### C-232: `npm test` discovers the entire test suite
Observable: Run `npm test`. The existing `node --test` command discovers both sets of tests.
Source: request

### C-233: All existing tests pass without edits
Observable: Compare the existing test files with the 1.4.0 baseline and run the suite. Those tests are unchanged and pass.
Source: request

### C-234: The data-format decision is recorded using the repository convention
Observable: The decision index identifies a numbered record describing the compatibility and preparation rules for stored deadlines.
Source: existing: CONTRIBUTING.md and docs/decisions/README.md

### C-235: The release bumps the package version
Observable: The new release has a package version newer than 1.4.0.
Source: existing: CONTRIBUTING.md

### C-236: The release changelog records the due-time change
Observable: The changelog has an entry for due times under the new package version.
Source: existing: CONTRIBUTING.md

### C-237: A failed initial save leaves no creation effects in enabled mode
Observable: After an enabled persistent create fails to save, the ticket is absent from detail and list reads, no creation audit entry or notification exists, and the next successful create uses the same ticket, audit and outbox sequence positions that the failed attempt would have used.
Source: implied: U-14 preserves the associated audit and notification effects, and C-52 requires the unsuccessfully saved ticket to remain absent

### C-238: Persistent writes preserve usable identifier sequences at their limits
Observable: A file with a next ticket number or next outbox event ID already at the largest safe integer can still be opened. If a request would allocate an identifier with no representable successor, it fails with the usual internal error and leaves ticket, audit and outbox state intact. Writes that require no such allocation can still succeed.
Source: implied: U-11 and C-67 require rollback on the new release's saved file, while C-192 and C-206 require safe next identifiers even after a save
