## Use cases

### U-1: A requester or agent opens a ticket, to have its response deadline fixed at once
Flow: They `POST /tickets` with `{"title": "VPN drops every hour", "requester": "maria@example.com", "priority": "high"}`. With due times on, the 201 answer is the ticket with a `due` field of the creation time plus 24 hours (created `2025-09-01T08:15:00.000Z` gives due `2025-09-02T08:15:00.000Z`). A later `GET /tickets/<id>` shows the same `due`. Urgent adds 4 hours, high 24, normal 72 (also when `priority` is left out), low 168.
Source: request

### U-2: An agent works a ticket, and its deadline does not move under them
Flow: They read the ticket, change its priority with `PATCH /tickets/<id>` (say from `normal` to `urgent`), move it through `in_progress`, `resolved` and back to `open`. Every answer and every later read shows the `due` it had at creation.
Source: request ("A ticket's due time is set once")

### U-3: A team lead lists the tickets that have missed their deadline, to chase them
Flow: They `GET /tickets?overdue=true`. They see, in id order and in the usual cursor pages, only the tickets that are `open` or `in_progress` and whose `due` is earlier than the time of the request. They page on with `next`. They may add `status` or `priority` to narrow the list. With nothing overdue they see `{"items": [], "next": null}`.
Source: request

### U-4: The help-desk manager changes the response hours, to match a new promise
Flow: They set one or more of the four hours settings in the service's environment and restart it. Tickets created from then on are due after the new hours; every ticket that already has a due time keeps it. They set a value the service cannot use (`0`, `1.5`, `four`) and the service refuses to start and names the variable.
Source: request ("must be able to change those hours without a code change")

### U-5: An operator brings the new release to the production data file, to switch due times on safely
Flow: They deploy the new release on the production data file with `DUE_TIMES` unset. The service starts, gives every ticket in the file a due time from its creation time and priority, saves the file, and answers exactly as 1.4.0 does. They look at the data file and see `due` on every ticket. They set `DUE_TIMES=on` and restart: tickets now show `due` and `overdue=true` works, with the same due values the file already held.
Source: request ("Due times are switched on in production only once the data file holds them")

### U-6: An operator finds the new release misbehaving and goes back to 1.4.0
Flow: They stop the new release, start 1.4.0 on the same data file (the file the new release wrote, with `due` on its tickets), and 1.4.0 starts and shows every ticket. They may later start the new release again on the file; tickets that 1.4.0 rewrote without `due`, and tickets it created, are given due times again at that start.
Source: request ("operators must be able to go back to the current release, 1.4.0")

### U-7: An existing client, the operators' command line and the weekly report carry on as before
Flow: With `DUE_TIMES` off, a client calls every endpoint as before and sees the same answers: no `due` field and `overdue` ignored. The command line (`list`, `list --raw`, `show`) and `scripts/weekly-report.js` print what they print today, also on a data file that holds `due` and also on one that does not.
Source: request ("Everything the service already does keeps working")

### U-8: An operator starts the service on a data file that is wrong or cannot be updated
Flow: A ticket's `due` in the file is not a time: the service refuses to start and its message names the record, like every other bad record. The file cannot be written when the due times have to be added to it: the service refuses to start and says why, rather than run with due times only in memory.
Source: implied: docs/operations.md ("A file it cannot use stops it with a message that names the record") and the sentence "keep them from then on"

### U-9: A developer runs the test suite
Flow: They run `npm test` and the existing tests pass unchanged, together with new `node:test` files under `test/` for the due times, the overdue listing, the settings, the backfill and the 1.4.0 compatibility.
Source: request

## Clauses

### C-1: The default response hours by priority are 4 for urgent, 24 for high, 72 for normal and 168 for low
Observable: With none of the hours settings given, a ticket created at `2025-09-01T08:15:00.000Z` has `due` `2025-09-01T12:15:00.000Z` when urgent, `2025-09-02T08:15:00.000Z` when high, `2025-09-04T08:15:00.000Z` when normal (also when `priority` is omitted from the request) and `2025-09-08T08:15:00.000Z` when low.
Source: request

### C-2: Each priority's response hours is set by its own environment variable, with the name `DUE_HOURS_<PRIORITY>`
Observable: `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` and `DUE_HOURS_LOW` set the hours of urgent, high, normal and low tickets. With `DUE_HOURS_HIGH=30`, a high ticket created at `2025-09-01T08:15:00.000Z` is due `2025-09-02T14:15:00.000Z` and the other three priorities keep their defaults.
Source: choice: the request says the hours must be changeable without a code change and says nothing of where; every other setting of the service is an environment variable (README.md, "Configuration"), so the help desk already knows that place

### C-3: An unset or empty hours variable means the default hours
Observable: With `DUE_HOURS_LOW` unset, empty, or only spaces, a low ticket is due 168 hours after creation.
Source: existing: README.md ("Unset or empty means the default")

### C-4: An hours value is a whole number from 1 to 8760, and any other value stops the service at start
Observable: `DUE_HOURS_URGENT` of `1` and of `8760` is accepted (8760 is 365 days). `0`, `-1`, `1.5`, `four`, `4h` and `8761` each make `npm start` exit with status 2 after writing a message on standard error that names `DUE_HOURS_URGENT`; the service does not listen. Surrounding spaces are ignored, as for the other whole-number settings. Each of the four variables is checked in the same way.
Source: existing: README.md ("A value the service cannot use ... stops it at start with a message naming the variable"); choice: 1 as the lowest because a zero-hour response time is no promise, and 8760 (one year) as the highest because the request gives no bound

### C-5: The hours settings are checked and used whether or not due times are switched on
Observable: With `DUE_TIMES` unset and `DUE_HOURS_NORMAL=0`, the service refuses to start as in C-4. With `DUE_TIMES` unset and `DUE_HOURS_NORMAL=10`, a ticket created at `2025-09-01T08:00:00.000Z` is stored in the data file with `due` `2025-09-01T18:00:00.000Z`.
Source: choice: due times are recorded while the switch is off (C-22), so the hours must be sound then too

### C-6: A changed hours setting applies to tickets created or given a due time after the service next starts, and moves no existing due time
Observable: A ticket created under `DUE_HOURS_NORMAL=72` and shown with due `2025-09-04T08:15:00.000Z` still shows that due after the service is restarted under `DUE_HOURS_NORMAL=10`; a ticket created after the restart is due 10 hours after its creation. The hours are read when the service starts, so changing the environment of a running process changes nothing.
Source: request ("a later change of the hours ... does not move it")

### C-7: `DUE_TIMES` set to `on` switches due times on; unset, empty, or any other value leaves them off
Observable: With `DUE_TIMES=on`, tickets show `due` and `GET /tickets?overdue=true` filters. With `DUE_TIMES` unset, empty, `off`, `ON`, `true` or `1`, the service answers as with C-24 and C-25 (exactly as 1.4.0).
Source: request ("until the DUE_TIMES environment variable is `on`"); choice: only the exact value `on` counts, so a misspelling can never switch the feature on by accident and the service still starts

### C-8: A ticket's due time is its creation time plus its priority's hours, counted as elapsed hours
Observable: `due` minus `created` is exactly the hours of the ticket's priority at creation times 3,600,000 milliseconds: no business hours, no weekends, no holiday, no daylight-saving shift. A ticket created at `2025-03-29T23:30:00.000Z` as urgent is due `2025-03-30T03:30:00.000Z`.
Source: request ("the time it was created plus the response time for its priority")

### C-9: The due time is computed from the same instant as the ticket's `created`
Observable: The ticket in the 201 answer has `due` equal to its `created` plus the hours to the millisecond, and every later read of it shows the same `created` and `due`.
Source: implied: "the time it was created plus ..."; a second reading of the clock would make due drift from created

### C-10: `due` is written as an ISO 8601 time in UTC with milliseconds, in the form of `created`
Observable: `due` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`, for example `2025-09-02T08:15:00.000Z`.
Source: existing: docs/api.md ("Times are ISO 8601 in UTC: `2025-09-01T08:15:00.000Z`")

### C-11: A change of a ticket's priority does not move its due time
Observable: A normal ticket created at `2025-09-01T08:15:00.000Z` (due `2025-09-04T08:15:00.000Z`) patched to `{"priority": "urgent"}` answers with priority `urgent` and `due` still `2025-09-04T08:15:00.000Z`; so do `GET /tickets/<id>` and the listing, and so does the data file.
Source: request ("a later change of ... the ticket's priority does not move it")

### C-12: A change of title, a transition of status or a reopening does not move a ticket's due time
Observable: After `PATCH` of the title, and after `open` to `in_progress` to `resolved` to `open`, the ticket's `due` equals the one it had after creation.
Source: implied: "A ticket's due time is set once"

### C-13: A client cannot set or change `due`
Observable: `POST /tickets` or `PATCH /tickets/<id>` with a `due` field answers 400 `invalid` with the message `unknown field: due`, whether `DUE_TIMES` is on or off, and the ticket is not created or changed.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)")

### C-14: Setting a due time is not a change of the ticket and leaves no audit entry
Observable: The audit entries of a ticket (`GET /tickets/<id>/audit`) are the same as in 1.4.0: `ticket.created` lists `title`, `priority`, `requester` and `status` from null and no `due`; no entry has `due` in its `changes`; giving a ticket its due time at start adds no entry and leaves the ticket's `updated` as it was.
Source: implied: docs/api.md ("`updated` ... when it last changed") and docs/decisions/0007-append-only-audit-log.md; a derived value fixed once is not a change anyone made

### C-15: With due times on, every ticket the service returns carries `due`
Observable: `due` is present in the 201 answer of `POST /tickets`, in `GET /tickets/<id>`, in every element of `items` of `GET /tickets` (with or without filters), in the 200 answer of `PATCH /tickets/<id>` (also one that changes nothing) and in the 200 answer of `POST /tickets/<id>/transition`. Every ticket has one, including resolved and closed ones and tickets that were in the data file before.
Source: request ("Every ticket shows its due time as `due`")

### C-16: The fields a ticket already shows keep their names, values and meaning when `due` is added
Observable: `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` are present and have the values they have in 1.4.0 for the same requests; `due` is an addition only.
Source: existing: docs/api.md ("The ticket")

### C-17: `GET /tickets?overdue=true` lists the tickets that are `open` or `in_progress` and whose due time has passed
Observable: Of tickets T-0001 (open, due 10:00), T-0002 (in_progress, due 10:00), T-0003 (open, due 12:00), T-0004 (resolved, due 10:00) and T-0005 (closed, due 10:00), requested at 11:00, the listing holds exactly T-0001 and T-0002. A ticket whose status is `resolved` or `closed` is never listed, however late its due time.
Source: request

### C-18: "Has passed" means the time of the request is later than `due`, so a ticket is not overdue at its due instant itself
Observable: At exactly the `due` instant (`due` equal to the service's current time to the millisecond) the ticket is not listed by `overdue=true`; one millisecond later it is.
Source: choice: the request says "has passed" and gives no rule for the instant itself; a ticket is late only once its time has gone by

### C-19: The overdue test uses the time of each request, so a ticket becomes overdue by time passing alone
Observable: A ticket not listed at one moment is listed by an `overdue=true` request made after its due time, with no change to the ticket and no other request between, with the background worker off (`WORKER_INTERVAL_MS=0`) as well as on.
Source: implied: "whose due time has passed"; CONTRIBUTING.md (background work is the worker's, and `WORKER_INTERVAL_MS=0` must stop all of it, so no listing may depend on it)

### C-20: A ticket reopened after its due time passed is listed as overdue again, and one resolved or closed drops out
Observable: A resolved ticket whose due time is past is not listed; after `transition` to `open` it is listed; after `in_progress` and `resolved` it is not listed.
Source: implied: the status rule in C-17 and C-12 (the due time does not move)

### C-21: `overdue=true` narrows a listing and combines with `status`, `priority`, `limit` and `cursor`
Observable: The tickets listed with `overdue=true` and another filter are only tickets that the same request without `overdue` lists and that are overdue. `?overdue=true&status=resolved` and `?overdue=true&status=closed` list nothing (`{"items": [], "next": null}`). `?overdue=true&priority=urgent` lists the overdue urgent tickets. Tickets come in id order; `limit` is 20 when absent and at most 100 (`101` is 400 `invalid`); `next` is null on the last page and otherwise a cursor that, passed back with the same filters, gives the page after it with no ticket twice and none skipped.
Source: implied: docs/api.md ("Filters combine"; "Tickets come in id order, a page at a time"); CONTRIBUTING.md ("Listings are cursor pages")

### C-22: With due times off, a ticket's due time is still recorded in the data file at creation
Observable: With `DUE_TIMES` unset and a `DATA_FILE`, a ticket created at `2025-09-01T08:15:00.000Z` as high appears in the file with `"due": "2025-09-02T08:15:00.000Z"` although no answer shows it. After the service is restarted with `DUE_TIMES=on`, the same ticket shows that `due`.
Source: choice: the request says due times are switched on once the file holds them; recording them while off is what keeps every ticket created between deploy and switch-on covered

### C-23: The service answers an `overdue` value other than `true` with 400 `invalid` when due times are on
Observable: With `DUE_TIMES=on`, `?overdue=false`, `?overdue=1`, `?overdue=TRUE`, `?overdue=` and `?overdue=yes` each answer 400 with `{"error": {"code": "invalid", "message": ...}}` whose message names `overdue`; `?overdue=true` is the only accepted value.
Source: choice: the request defines only `overdue=true`; refusing the rest follows the existing rule that a filter value that cannot be used is `invalid` (docs/api.md) and avoids a client reading `overdue=false` as "not overdue" and getting every ticket

### C-24: With due times off, no ticket representation has a `due` field
Observable: With `DUE_TIMES` off, the answers of `POST /tickets`, `GET /tickets/<id>`, `GET /tickets`, `PATCH /tickets/<id>` and `POST /tickets/<id>/transition` hold exactly the seven fields `id`, `title`, `priority`, `requester`, `status`, `created`, `updated` and no `due` key, not even `null`, also for tickets whose file record has a `due`.
Source: request ("the service answers exactly as it does today")

### C-25: With due times off, `overdue` is ignored like any parameter the listing does not know
Observable: With `DUE_TIMES` off, `GET /tickets?overdue=true`, `?overdue=false` and `?overdue=maybe` answer 200 with the same items as the request without `overdue`.
Source: request; existing: test/query.test.js ("ignores parameters it does not know")

### C-26: With due times off, every other answer is the one 1.4.0 gives
Observable: Status codes, error bodies, audit entries, outbox contents, the `ticket.created` and `ticket.resolved` notifications, ids and pagination are the same as 1.4.0's for the same requests.
Source: request ("answers exactly as it does today")

### C-27: When the service starts on a data file, it gives every ticket that has no `due` one: its creation time plus the hours of its current priority
Observable: A file of 1.4.0 holding T-0001 (high, created `2025-01-10T09:00:00.000Z`, closed) and T-0002 (low, created `2025-01-11T10:30:00.000Z`, open) gives, after start with default hours, T-0001 `due` `2025-01-11T09:00:00.000Z` and T-0002 `due` `2025-01-18T10:30:00.000Z`. Tickets of every status get one, resolved and closed included. It happens with `DUE_TIMES` unset as well as `on`.
Source: request ("The tickets already in the production data file get due times too, from their own creation time and priority"); choice: the hours are the ones in effect at that start, the file records no earlier hours

### C-28: The due times given at start are saved in the data file before the service listens
Observable: Once `npm start` has logged that it is listening, the data file already holds `due` on every ticket; a service killed right after start and started again, even under other hours settings or after a priority change in between, shows the same due times.
Source: request ("keep them from then on"; "once the data file holds them")

### C-29: A ticket that already has a `due` in the data file keeps it, whatever its creation time, priority or the hours
Observable: A file ticket with priority `low`, created `2025-01-10T09:00:00.000Z` and `"due": "2025-01-10T10:00:00.000Z"` shows `due` `2025-01-10T10:00:00.000Z` after any number of starts, under any hours settings.
Source: request ("keep them from then on")

### C-30: Giving due times at start changes nothing else in the file
Observable: The tickets' `id`, `title`, `priority`, `requester`, `status`, `created` and `updated`, the audit log, the outbox with its events and next id, and `nextNumber` are the same after the start as before; no notification is enqueued.
Source: implied: "The tickets already in the production data file get due times too" and CONTRIBUTING.md (a change that changes nothing is not a change: no audit entry, no notification)

### C-31: Tickets created after start are saved with their `due`, and every later save keeps it
Observable: After `POST /tickets`, after any `PATCH` or transition, and after a stop by `SIGTERM`, the data file holds `due` on every ticket, with the value shown by the API.
Source: implied: docs/decisions/0008-json-data-file.md ("a field added to a ticket is added there too, or it is lost at the next restart")

### C-32: The data file stays in format version 1, and a ticket's `due` is a field `due` of its record holding an ISO 8601 UTC time
Observable: The saved document has `"version": 1` and each ticket record has the fields 1.4.0 writes plus `"due": "<time>"`. The audit and outbox records and the other top-level fields (`savedAt`, `nextNumber`, `tickets`, `audit`, `outbox`) are those 1.4.0 writes.
Source: request ("it must still start on the data file the new release wrote"); existing: src/persistence.js (1.4.0 refuses any version but 1); docs/decisions/0008-json-data-file.md

### C-33: 1.4.0 started on a data file written by the new release starts and shows every ticket
Observable: `node src/server.js` of the 1.4.0 code with `DATA_FILE` set to a file the new release saved (with and without `DUE_TIMES` on, tickets in every status, and a ticket with a changed priority) starts, and `GET /tickets` lists every ticket with the `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` the new release showed; `GET /tickets/<id>/audit` and `GET /admin/outbox` hold the same entries. The 1.4.0 command line reads the file as well.
Source: request ("go back to the current release, 1.4.0 ... must still start on the data file the new release wrote and show every ticket")

### C-34: The new release starts on a data file written by 1.4.0, and on its own
Observable: A file with no `due` on any ticket, or on some tickets, starts with C-27 applied to the tickets missing one; a file written by the new release starts and keeps all its `due` values. A first start with no file starts empty, as today.
Source: existing: docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote ... A field older files do not have takes its default when they load")

### C-35: A ticket record whose `due` is present but not a time refuses the start, naming the record
Observable: A file whose `tickets[3].due` is `"tomorrow"`, `42`, `null` or `""` stops `npm start` with exit status 2 and a message on standard error that begins with the file name and names `tickets[3].due`, like `data/tickets.json: tickets[3].due is not a time`; the service does not listen and the file is not changed.
Source: existing: src/persistence.js and docs/operations.md ("stops it with a message that names the record")

### C-36: The service does not start when it cannot save the due times it has to add to the data file
Observable: With a data file with tickets missing `due` in a place where it cannot be replaced (a read-only folder), `npm start` exits with status 2 and a message on standard error naming the data file; it does not listen. With a file where every ticket has `due`, nothing needs saving and the start does not write the file.
Source: choice: running with due times only in memory would let them differ from one start to the next, which breaks "keep them from then on"

### C-37: A creation time in the file that is a valid time in another form gives a canonical UTC due
Observable: A ticket with `"created": "2025-09-01T10:15:00+02:00"` and priority high is given `due` `2025-09-02T08:15:00.000Z`, and its `created` shows as it is in the file.
Source: implied: the file's check accepts any text `Date.parse` reads (src/persistence.js, `time`), so an existing file may hold such a time

### C-38: A file ticket whose due time would lie beyond the latest time JavaScript can hold refuses the start, naming `created`
Observable: A ticket whose `created` plus its hours is later than `+275760-09-13T00:00:00.000Z` stops the start with exit status 2 and a message that names `tickets[<n>].created`.
Source: the runtime's own rule (the ECMAScript date range ends at 8,640,000,000,000,000 ms after 1970-01-01T00:00:00.000Z, so a later due time cannot be written)

### C-39: After a return to 1.4.0 and a new start of the new release, tickets that 1.4.0 left without `due` are given one by C-27 from their then-current priority
Observable: A ticket the new release gave a high-priority due, whose priority 1.4.0 changed to low and saved (dropping `due`, since 1.4.0 does not keep the field), shows after the new release starts again `due` created plus 168 hours; a ticket 1.4.0 created is given one in the same way. Tickets 1.4.0 did not rewrite keep their `due` by C-29.
Source: implied: the sentence about going back to 1.4.0, whose save writes only the fields it knows (src/persistence.js `ticketRecord`)

### C-40: Switching due times on or off by a restart changes no stored due time
Observable: A ticket's `due` is the same string before and after a restart that flips `DUE_TIMES` from unset to `on` and back, and the data file's `due` values are the same after each start.
Source: request ("A ticket's due time is set once")

### C-41: Two tickets created at the same moment or at once each get their own due time and id
Observable: Two `POST /tickets` sent together with the clock standing still both answer 201 with different ids and a `due` of their own creation time plus their own priority's hours.
Source: implied: where the parts meet; ids are never reused (docs/api.md)

### C-42: Nothing in the service notifies, logs or enqueues anything because a ticket becomes overdue
Observable: Left past its due time, a ticket causes no outbox event, no notification line and no new audit entry; `GET /admin/outbox` shows only the events it showed before.
Source: choice: the request asks for a due time and a listing only, and adds no feature the request's intent does not cover

### C-43: The service says at start how many tickets it gave a due time
Observable: When tickets were given a due time at start (C-27), the log on standard error holds a line saying how many, with the count in it; when none were, that line is not written. The wording is not fixed.
Source: choice: operators need to see that the file now holds the due times before they switch on; the wording and the logger format stay free

### C-44: The command line prints what it printed before and never writes the data file
Observable: `tickets list`, `list --raw` (columns id, status, priority, title, tab-separated, in this position), `list --status S` and `show <id>` print the same text for the same file as in 1.4.0, with no `due` column or line, exit with the same codes (0, 1 for an unknown ticket, 2 for a usage or file problem), and on a file where tickets lack `due` the file is unchanged after the run (same bytes, same modification time).
Source: existing: README.md ("`bin/tickets.js` reads the data file; it never changes it", the columns "must keep their positions") and docs/operations.md

### C-45: The weekly report's output is unchanged
Observable: `scripts/weekly-report.js` and its `--json` output give the same counts by status and priority for the same file, on files with and without `due`.
Source: existing: README.md ("Command line")

### C-46: A ticket's `title`, `requester` and `priority` are checked as before
Observable: `title` must be a string of 1 to 200 characters after trimming with no control character, `requester` of 1 to 64, `priority` one of `low`, `normal`, `high`, `urgent`; anything else is 400 `invalid`, as in 1.4.0.
Source: existing: src/tickets/validate.js and docs/api.md

### C-47: The lifecycle and its errors are unchanged
Observable: `open` to `in_progress` to `resolved` to `closed`, and `resolved` to `open`; any other move is 409 `conflict`; `closed` is final; a `PATCH` of a closed ticket is 409 `conflict`; an unknown ticket is 404 `not_found`; a `PATCH` with the values the ticket already has changes neither `updated` nor the audit log.
Source: existing: docs/api.md and src/tickets/states.js

### C-48: Notifications and the audit log work as before
Observable: Creating a ticket enqueues one `ticket.created` notification to its requester and resolving one enqueues `ticket.resolved`; each change has its audit entry with the actor from `X-Actor` (`system` without it).
Source: existing: docs/api.md

### C-49: The existing listing keeps its filters, its errors and its way of combining `status` and `priority`
Observable: `status` and `priority` values that are not a status or a priority are 400 `invalid`; `limit` is 1 to 100; a cursor the service did not issue is 400 `invalid`; `?status=open&priority=urgent` lists what it lists in 1.4.0. The code of 1.4.0 lists a ticket that matches either filter although docs/api.md says it must match both; this change neither corrects nor relies on that, and `overdue` is applied on top of whatever the request lists without it (C-21).
Source: existing: docs/api.md, src/tickets/query.js and request ("answers exactly as it does today"); choice: leaving the discrepancy for its own change keeps the switched-off answers identical

### C-50: The service's other settings and its endpoints work as before
Observable: `PORT`, `DATA_FILE`, `NOTIFY_FILE`, `WORKER_INTERVAL_MS`, `MAX_BODY_BYTES` and `LOG_REQUESTS` mean what the README says; `GET /health` answers `{"status": "ok"}`; `GET /admin/outbox` and the error envelope `{"error": {"code", "message"}}` are as before; a body over `MAX_BODY_BYTES` is refused as before.
Source: existing: README.md and docs/api.md

### C-51: Code that builds the store or the service without the new settings behaves as with due times off and the default hours
Observable: The existing tests of `test/`, which build `TicketStore` with only a clock and `createService` with the six settings of `test/helpers.js`, pass without any change to them.
Source: request ("its existing tests must still pass as they are")

### C-52: The existing tests are not changed and still pass
Observable: `npm test` runs the existing files of `test/` unmodified and all of their tests pass.
Source: request

### C-53: New `node:test` files under `test/` test the new behaviour, and `npm test` runs them with the existing ones
Observable: `npm test` (`node --test`) runs the new files and reports them passing. Together they cover at least: the four default hours (C-1), a changed hours setting and its refusals (C-2, C-4), the switch (C-7), the due computation (C-8), due not moving after a priority change (C-11), `due` in every answer when on and absent when off (C-15, C-24), the overdue listing with each status, the instant of due, `overdue` with other filters and with paging (C-17, C-18, C-21, C-23), the data file backfill, its persistence and the refusal of a bad `due` (C-27, C-28, C-29, C-35), and that the file stays loadable by 1.4.0's `fromDocument`-checks (C-32). They start no server on a fixed port and move time with `manualClock`.
Source: request; existing: CONTRIBUTING.md ("a change of behaviour comes with a test of it"; "HTTP tests start the service on port 0")

### C-54: The service has no dependencies
Observable: `package.json` lists no `dependencies` or `devDependencies`; the service runs on Node.js 22 with only its standard library.
Source: existing: CONTRIBUTING.md and README.md

### C-55: The README and the API document describe the new settings, field and filter
Observable: README.md's configuration table has rows for `DUE_TIMES` and the four `DUE_HOURS_*` variables with their defaults; docs/api.md shows `due` in "The ticket" and documents `overdue` in "List tickets", including that `overdue` is ignored while `DUE_TIMES` is not `on`.
Source: existing: README.md and docs/api.md describe every setting and field today

### C-56: The operations guide gives the order of roll-out and the way back
Observable: docs/operations.md says to deploy with `DUE_TIMES` unset, check that the data file's tickets hold `due`, set `DUE_TIMES=on`, and, to go back, to start 1.4.0 on the same file; and says that tickets 1.4.0 saves lose `due` and get it again at the next start of the new release (C-39).
Source: request ("Due times are switched on in production only once the data file holds them"; "operators must be able to go back"); existing: docs/operations.md

### C-57: The release is numbered 1.5.0 and recorded in the change log and in a decision record
Observable: `package.json` has version `1.5.0`; CHANGELOG.md has a `1.5.0` section above 1.4.0's naming due times, the overdue filter, the settings and the backfill; docs/decisions/ has a record `0009` for the data file's new field and the switch, listed in its README index.
Source: existing: CONTRIBUTING.md ("Releases"; "for anything that changes ... the data file ... record the decision")
