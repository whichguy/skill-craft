## Use cases

### U-1: A requester or agent opens a ticket and gets its due time
Flow: With due times on, someone sends `POST /tickets` with `{"title":"VPN drops every hour","requester":"maria@example.com","priority":"high"}` at 2025-09-01T08:15:00.000Z. The answer is 201 and the ticket carries `"due":"2025-09-02T08:15:00.000Z"`, 24 hours after `created`. Sent without `priority`, the ticket is `normal` and its `due` is 72 hours after `created`.
Source: request

### U-2: An agent or dashboard reads due times
Flow: With due times on, `GET /tickets/T-0042`, `GET /tickets`, `PATCH /tickets/T-0042` and `POST /tickets/T-0042/transition` all show the ticket with its `due`. The agent sees the same `due` every time, whatever happens to the ticket meanwhile.
Source: request ("Every ticket shows its due time as `due`")

### U-3: A team lead lists the tickets that are overdue
Flow: With due times on, `GET /tickets?overdue=true` lists the `open` and `in_progress` tickets whose `due` is before the current time, in id order, a page at a time like any listing. A resolved or closed ticket is never in it. The lead may add `status`, `priority`, `limit` and `cursor`.
Source: request

### U-4: The help desk changes how many hours each priority gets
Flow: An operator sets `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` or `DUE_HOURS_LOW` in the service's environment and restarts it. Tickets created from then on get the new hours; tickets that already have a due time keep it. A value the service cannot use stops it at start with a message naming the variable.
Source: request ("the help desk must be able to change those hours without a code change"); implied: every setting of this service is an environment variable read at start (README.md, Configuration)

### U-5: An operator deploys the new release over the production data file
Flow: The operator starts the new release with `DATA_FILE` pointing at the production file written by 1.4.0 and `DUE_TIMES` unset. Before the service listens, every ticket in the file that has no `due` is given one (its `created` plus the hours of its current priority) and the file is saved. The operator opens the file and finds a `due` on every ticket. From then on those due times never change.
Source: request ("The tickets already in the production data file get due times too ... and keep them from then on")

### U-6: An operator switches due times on
Flow: Once the file holds the due times (U-5), the operator sets `DUE_TIMES=on` and restarts. From the first request the API shows `due` on every ticket and answers `overdue=true`.
Source: request ("Due times are switched on in production only once the data file holds them")

### U-7: Nothing changes for anyone while due times are off
Flow: With `DUE_TIMES` unset, empty or anything other than `on`, every client sees the same answers as release 1.4.0 gives: no `due` in any ticket, `overdue` an unknown parameter that is ignored. The due times are nonetheless kept in the data file for the day the operator switches them on.
Source: request ("until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today")

### U-8: An operator goes back to release 1.4.0
Flow: The new release misbehaves. The operator stops it, starts release 1.4.0 on the same data file, with no conversion step, and 1.4.0 starts and shows every ticket the new release held, with the fields 1.4.0 knows.
Source: request ("operators must be able to go back to the current release, 1.4.0, and it must still start on the data file the new release wrote and show every ticket")

### U-9: An operator moves forward again after a rollback
Flow: After running 1.4.0 on the file (which may have added tickets and dropped the due times it does not know), the operator starts the new release again. Every ticket without a `due` is stamped at start, as in U-5, and the service carries on.
Source: implied: U-8 followed by a second deployment; 1.4.0 keeps only the ticket fields it knows (docs/decisions/0008-json-data-file.md)

### U-10: An agent works a ticket and its due time stays where it was
Flow: An agent raises a ticket's priority from `normal` to `urgent`, lowers another's from `urgent` to `low`, retitles one, moves one through `in_progress`, `resolved`, back to `open` and on to `closed`. After each step `due` is the value it had when the ticket was created.
Source: request ("A ticket's due time is set once: a later change of the hours or of the ticket's priority does not move it")

### U-11: A client sends something the API does not accept
Flow: A client puts `due` in a `POST /tickets` or `PATCH /tickets/:id` body, or asks `GET /tickets?overdue=false` (due times on). It gets the 400 `invalid` envelope the API gives every bad request.
Source: implied: a due time is set once by the service, and the API refuses unknown fields and bad query values (docs/api.md)

### U-12: An operator uses the command line and the weekly report
Flow: The operator runs `bin/tickets.js list`, `list --raw`, `show` and `scripts/weekly-report.js` on a data file that holds due times, and on one that does not. They print what they printed in 1.4.0, and the data file is not written.
Source: existing: README.md, "Command line"

### U-13: A maintainer runs the tests and reads the documents
Flow: `npm test` runs the existing tests unchanged, plus the new ones under `test/`, and they pass. The README, the API document, the operations document and the changelog describe the new settings, the field, the parameter and how to roll out and roll back.
Source: request ("Add node:test tests under test/ ..."); implied: CONTRIBUTING.md ("a change of behaviour comes with a test of it", releases bump the version and the changelog, an API or data file change gets a record)

## Clauses

### C-1: A ticket's due time is its creation time plus the response time of its priority
Observable: A ticket created at 2025-09-01T08:15:00.000Z with default hours has due time 2025-09-01T12:15:00.000Z if `urgent`, 2025-09-02T08:15:00.000Z if `high`, 2025-09-04T08:15:00.000Z if `normal`, 2025-09-08T08:15:00.000Z if `low`.
Source: request

### C-2: The default response times are 4, 24, 72 and 168 hours
Observable: With none of the four hours variables set, `urgent` is 4 hours, `high` 24, `normal` 72 and `low` 168. Those are the only priorities the service has (`low`, `normal`, `high`, `urgent`), so every ticket has an hours value.
Source: request; existing: src/tickets/priorities.js lists the priorities

### C-3: A response time counts elapsed hours of 3,600,000 milliseconds
Observable: `due` minus `created` is exactly hours × 3,600,000 ms, on any date: no calendar, working-hours or daylight-saving adjustment applies. A ticket created at 2025-03-30T00:30:00.000Z with 24 hours is due 2025-03-31T00:30:00.000Z.
Source: choice: the request says "the time it was created plus the response time"; the service keeps all times in UTC (docs/api.md), where an hour has one length

### C-4: A ticket created without a priority is due 72 hours after it was created
Observable: `POST /tickets` with no `priority` gives a `normal` ticket whose `due` is `created` + 72 hours (default hours).
Source: implied: the default priority is `normal` (docs/api.md) and U-1

### C-5: `due` is written like `created`
Observable: When shown, `due` is a JSON string of ISO 8601 in UTC with milliseconds and a trailing `Z`, for example `2025-09-02T08:15:00.000Z`. It is never null and never a number.
Source: existing: docs/api.md ("Times are ISO 8601 in UTC")

### C-6: The response time of each priority is set by an environment variable
Observable: `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` and `DUE_HOURS_LOW` set the hours of `urgent`, `high`, `normal` and `low`. With `DUE_HOURS_NORMAL=48` a `normal` ticket created at 2025-09-01T08:15:00.000Z is due 2025-09-03T08:15:00.000Z, while the other three priorities keep their hours.
Source: choice: the request asks for a change without a code change and every setting of this service is an environment variable (README.md); the names follow the existing `WORKER_INTERVAL_MS` style

### C-7: An unset or empty hours variable takes its default
Observable: A variable that is unset, empty, or only spaces gives the default of C-2 for its priority, as the other settings do.
Source: existing: README.md ("Unset or empty means the default"), src/config.js trims

### C-8: An hours value is a whole number from 1 to 8760
Observable: `DUE_HOURS_HIGH=1` and `DUE_HOURS_HIGH=8760` (365 days) start the service; the values `0`, `8761`, `-5`, `2.5`, `1e3`, `24h` and `abc` do not.
Source: choice: 0 would make every ticket overdue the moment it exists, and the request names no maximum; one year is a generous ceiling that stays well inside the range of dates the runtime can hold. The bounds are the author's decision, not the requester's

### C-9: An unusable hours value stops the service at start
Observable: With `DUE_HOURS_URGENT=0` the process prints a message that contains `DUE_HOURS_URGENT`, listens on no port and exits with status 2, like `PORT=http`. The same holds for each of the four variables, whether `DUE_TIMES` is on, off or unset.
Source: existing: README.md ("A value the service cannot use ... stops it at start with a message naming the variable"), src/server.js exits 2 on a ConfigError; implied: the hours are used to stamp tickets whatever `DUE_TIMES` says (C-30)

### C-10: The hours are read when the service starts
Observable: Changing a variable has no effect on a running service; after a restart it does. There is no endpoint or command to change the hours of a running service.
Source: existing: src/config.js reads the environment once at start; choice: the request asks only for a change without a code change

### C-11: A change of the hours moves no existing due time
Observable: A ticket with `due` 2025-09-02T08:15:00.000Z (24 hours, `high`) still shows that value after the operator sets `DUE_HOURS_HIGH=12` and restarts; a `high` ticket created after the restart is due 12 hours after it was created.
Source: request

### C-12: A change of a ticket's priority moves no due time
Observable: `PATCH /tickets/T-0001` with `{"priority":"urgent"}` on a `normal` ticket, and with `{"priority":"low"}` on an `urgent` one, leaves `due` as it was before the request, and a later `GET` shows the same value.
Source: request

### C-13: No other change moves a due time
Observable: A change of title, each lifecycle move (`open` → `in_progress` → `resolved` → `open` again via reopen, `resolved` → `closed`), a `PATCH` that changes nothing, and a restart of the service each leave `due` as it was.
Source: implied: "set once" in the request; U-10

### C-14: A ticket's due time is fixed when it is created and saved with the ticket
Observable: In a service with a data file, the file written by the change that creates a ticket already holds that ticket's `due`; no file written by the service holds a ticket without one, from the first save after it starts.
Source: implied: due times must be in the data file before they are switched on, so no ticket can be saved without one

### C-15: Clients cannot set a due time
Observable: `POST /tickets` or `PATCH /tickets/:id` with a `due` field in the body is answered 400 `invalid` in the usual envelope, whether due times are on or off, and changes nothing.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)"); implied: "set once"

### C-16: Due times are on only when `DUE_TIMES` is `on`
Observable: A service started with `DUE_TIMES=on` (spaces around the value ignored) shows due times and answers `overdue=true`.
Source: request

### C-17: Any other `DUE_TIMES` value leaves due times off, without an error
Observable: With `DUE_TIMES` unset, empty, `off`, `ON`, `1`, `true` or `yes` the service starts normally and behaves as C-18 to C-21 describe.
Source: request ("until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today"); choice: only the exact word `on` switches it on, so a stray value can never expose unreleased behaviour

### C-18: With due times off, no ticket shows a `due`
Observable: The ticket objects from `POST /tickets` (201), `GET /tickets/:id`, `PATCH /tickets/:id`, `POST /tickets/:id/transition` and every item of `GET /tickets` have no `due` key and exactly the seven keys of 1.4.0: `id`, `title`, `priority`, `requester`, `status`, `created`, `updated`.
Source: request

### C-19: With due times off, `overdue` is an unknown parameter and is ignored
Observable: `GET /tickets?overdue=true` returns the same body as `GET /tickets`, and `?overdue=banana` does too; both answer 200 and list resolved and closed tickets that are past their due time.
Source: request; existing: src/tickets/query.js ignores parameters it does not know

### C-20: With due times off, every other answer is as in 1.4.0
Observable: The audit endpoint, `GET /admin/outbox`, `GET /health`, every error envelope and status, and the order and paging of listings are as 1.4.0 gives them for the same requests and the same data.
Source: request ("answers exactly as it does today")

### C-21: With due times off, due times are still kept in the data file
Observable: With `DUE_TIMES` unset and a data file, a ticket created through the API is saved with its `due`, and every ticket stamped at start (C-30) is saved with its `due`; the file shows them although the API does not.
Source: implied: the request switches due times on only once the data file holds them

### C-22: With due times on, every ticket shows its `due`
Observable: The ticket objects from `POST /tickets` (201), `GET /tickets/:id`, `PATCH /tickets/:id`, `POST /tickets/:id/transition` and every item of `GET /tickets` and `GET /tickets?overdue=true` have a `due` as well as the seven keys of C-18. The objects of one ticket from these answers are equal.
Source: request

### C-23: The audit log does not list the due time
Observable: `GET /tickets/:id/audit` has no `due` key in any entry's `changes`, whether due times are on or off: a created ticket's entry lists exactly `title`, `priority`, `requester` and `status`, and a priority change lists only `priority`.
Source: existing: docs/api.md ("Actions so far", the created entry) and src/store.js CREATED_FIELDS; choice: the due time is set by the service, not by a person; keeping the log unchanged also keeps it loadable by 1.4.0

### C-24: `overdue=true` lists the open and in-progress tickets whose due time has passed
Observable: With due times on, `GET /tickets?overdue=true` returns the tickets whose `status` is `open` or `in_progress` and whose `due` is earlier than the service's current time, as instants (not as text), and no others.
Source: request

### C-25: A ticket is overdue only after its due instant
Observable: At exactly the instant `due` the ticket is not listed by `overdue=true`; one millisecond later it is. A ticket created and due 4 hours later (`urgent`) is listed at 4 hours and 1 ms and not at 3 hours 59 minutes.
Source: choice: "has passed" is read strictly, so a ticket due at 12:15:00.000 is on time at 12:15:00.000

### C-26: Resolved and closed tickets are never overdue
Observable: A `resolved` or `closed` ticket whose `due` is in the past is absent from `overdue=true`, however long ago it was due.
Source: request ("open and in-progress tickets"); existing: src/tickets/states.js ACTIVE lists `open` and `in_progress`

### C-27: A reopened ticket is judged again by its original due time
Observable: A ticket that was resolved before its due time and reopened after it is listed by `overdue=true` while it is `open` or `in_progress`; a ticket reopened before its due time is not listed until that time passes.
Source: implied: due is set once (C-13) and the listing depends on the current status

### C-28: Overdue is judged at the time of the request
Observable: A `high` ticket created at 08:00 is absent from `overdue=true` at 08:00 + 23 hours and present at 08:00 + 25 hours, with no write between the two requests.
Source: implied: "whose due time has passed"; existing: the service reads the time from its clock (src/clock.js)

### C-29: `overdue=true` is combined with `status` by requiring both
Observable: With an overdue `in_progress` ticket and an overdue `open` ticket, `?overdue=true&status=in_progress` lists only the first; `?overdue=true&status=resolved` or `status=closed` is `{"items":[],"next":null}` with 200.
Source: implied: the filters of a listing narrow it (docs/api.md, "Filters combine")

### C-30: `overdue=true` is combined with `priority` by requiring both
Observable: With an overdue `urgent` ticket and an overdue `low` ticket, `?overdue=true&priority=urgent` lists only the urgent one.
Source: implied: as C-29

### C-31: The combination of `status` and `priority` is not changed by this release
Observable: Without `overdue`, `GET /tickets?status=open&priority=urgent` answers exactly as 1.4.0 does for the same data (the code of 1.4.0 lists a ticket that matches either filter, although docs/api.md says both). This release neither fixes nor extends that, and with `overdue=true` the overdue test (C-24) is applied on top of whichever tickets that combination selects.
Source: existing: src/tickets/query.js matchesFilters, docs/api.md; choice: the request says everything the service does keeps working and that off answers as today, so a defect outside the request is left for its own change

### C-32: `overdue=true` pages like any listing
Observable: The answer is `{"items":[...],"next":<cursor or null>}`; items come in id order (not due order); `limit` is 1 to 100 (20 when absent); `next` is non-null exactly when more overdue tickets follow; passing `next` as `cursor` with the same filters gives the following tickets, none twice and none skipped.
Source: existing: docs/api.md ("List tickets"), docs/decisions/0005-cursor-pagination.md

### C-33: `overdue=true` with nothing overdue answers an empty page
Observable: 200 with `{"items":[],"next":null}`, not an error.
Source: implied: the empty case of the listing

### C-34: With due times on, `overdue` takes only `true`
Observable: `?overdue=false`, `?overdue=`, `?overdue=TRUE`, `?overdue=1` and `?overdue=yes` are answered 400 with code `invalid` and a message that contains `overdue`, in the usual envelope.
Source: choice: the request defines only `overdue=true`; refusing what it does not define is the API's rule for query values (docs/api.md, "a query value out of range"), and guessing `false` to mean "not overdue" would add a feature

### C-35: Without `overdue`, the listing is as before
Observable: With due times on, `GET /tickets` and the `status`, `priority`, `limit` and `cursor` forms list the same tickets in the same order and pages as 1.4.0, with `due` added to each item.
Source: request ("Everything the service already does keeps working")

### C-36: A ticket becoming overdue causes no event
Observable: When a ticket's due time passes, no audit entry is appended, no notification is enqueued (`GET /admin/outbox` and the notification file are unchanged), `updated` does not move, and nothing is written to the data file.
Source: choice: the request asks for a listing, not an alert; implied: CONTRIBUTING.md (background work is only the worker's, so the state is judged on read)

### C-37: At start, every ticket in the data file without a due time is given one
Observable: Starting the new release on a data file whose tickets have no `due` gives each one `due` = its own `created` + the hours of its own current `priority` (default hours: a `high` ticket created 2025-08-01T10:00:00.000Z gets 2025-08-02T10:00:00.000Z; a `low` one gets 2025-08-08T10:00:00.000Z). Each ticket is judged by its own `created` and `priority`, not by the time of the start.
Source: request

### C-38: The tickets are stamped before the service listens, and the file is saved
Observable: By the time the service accepts its first request (the port answers), the data file on disk already holds a `due` on every ticket; no request is answered from a state in which some ticket lacks one.
Source: request ("only once the data file holds them"); implied: with `DUE_TIMES=on` at the first start, no ticket may show without a due

### C-39: Stamping happens whatever `DUE_TIMES` says
Observable: A start with `DUE_TIMES` unset and one with `DUE_TIMES=on` on the same old file both leave the file with a `due` on every ticket.
Source: request (the file must hold the times before they are switched on)

### C-40: Stamping changes nothing but the due times
Observable: After stamping, each ticket's `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` are as before; the audit log has the same entries; the outbox has the same events with the same states; `nextNumber` and `outbox.nextId` are as before. No notification is enqueued for it.
Source: implied: stamping is a migration, not a change a person made (docs/decisions/0007-append-only-audit-log.md: the log records changes to a ticket by actors)

### C-41: A due time already in the file is kept
Observable: A ticket that has `due` in the file keeps exactly that value at start, even when its priority was changed since or the hours variables differ from the ones that produced it. A start on a file where every ticket has one stamps nothing.
Source: request ("keep them from then on", "set once")

### C-42: Stamping a second time gives the same due times
Observable: Starting, stopping and starting again over an old file leaves every `due` of the second start equal to that of the first, however much time and however many changes of the hours lie between.
Source: request ("keep them from then on")

### C-43: The stamping save replaces the file whole
Observable: At every instant the data file is the old document or the stamped one, never a mix and never a partial file, and no temporary file is left in its folder afterwards. A reader (the command line) that opens the file during the start finds a complete JSON document.
Source: existing: docs/decisions/0008-json-data-file.md, docs/operations.md

### C-44: A start that cannot save the stamped file does not serve
Observable: When the data file cannot be written at start (for example its folder is read-only) and some ticket needs a due time, the process exits with a status other than 0, prints a message that contains the data file's path, and listens on no port.
Source: choice: serving without the stamped file on disk would break the rule that the file holds the times first

### C-45: A start with nothing to stamp does not rewrite the file before the first change
Observable: With every ticket already holding a `due`, the data file's content is byte for byte the same after the service has started and before any request or stop.
Source: choice: an unnecessary write at start would be an unrequested change to production data

### C-46: A due time in the data file must be a time
Observable: A file whose ticket has `"due": "soon"`, `"due": 5`, `"due": null`, `"due": ""` or `"due": {}` is refused at start as a damaged file: the message names the file and the record, as `data/tickets.json: tickets[1].due is not a time`, the process exits with status 2 and listens on no port. A ticket without a `due` key is not refused (C-37).
Source: existing: src/persistence.js ("Loading checks each record"; created and updated are checked the same way, exit 2 in src/server.js)

### C-47: A due time before the creation time is accepted
Observable: A file with a valid `due` earlier than the ticket's `created` loads, and the ticket shows that `due`.
Source: choice: nothing in the request or the existing checks relates two times of a record, and refusing a production file for it would stop the service

### C-48: A ticket's due time shows as the file holds it
Observable: A `due` such as `2025-09-02T08:15:00.000Z` in the file is shown as `2025-09-02T08:15:00.000Z`; the service never rewrites it.
Source: implied: "keep them from then on"

### C-49: A first start without a data file needs no stamping
Observable: With `DATA_FILE` naming a file that does not exist, the service starts as in 1.4.0; the first ticket created is saved with its `due` (C-14).
Source: existing: src/persistence.js (a missing file is a first start)

### C-50: Without `DATA_FILE`, due times work and are not kept
Observable: A service with no `DATA_FILE` gives each new ticket a due time as in C-1, answers `overdue=true` with `DUE_TIMES=on`, and after a restart holds no tickets, as in 1.4.0.
Source: existing: README.md (`DATA_FILE` "without it the state lives in memory")

### C-51: Every save keeps every ticket's due time
Observable: After any change, after `SIGTERM`, and after a start with due times off, the data file's tickets each still hold the `due` they had; changing a title, priority or status never removes or rewrites one.
Source: implied: the data file is the only store of due times (docs/decisions/0008-json-data-file.md: "a field added to a ticket is added there too, or it is lost at the next restart")

### C-52: The data file stays version 1 and stays shaped as before
Observable: The file written by the new release has `"version": 1`, the same top-level keys (`version`, `savedAt`, `nextNumber`, `tickets`, `audit`, `outbox`), the same audit-entry and outbox-event fields as 1.4.0 writes, and for each ticket the seven fields of 1.4.0 plus `due`; nothing else is added anywhere.
Source: request (release 1.4.0 must still start on it); existing: src/persistence.js VERSION; docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote")

### C-53: Release 1.4.0 starts on the file the new release wrote and shows every ticket
Observable: With a file written by the new release (tickets with `due`, with due times on and off, created before and after the upgrade, with audit entries and outbox events), release 1.4.0 starts with exit status 0 and listens, `GET /tickets` lists every ticket with the same `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` as the new release showed, and `GET /tickets/:id/audit` shows the same entries.
Source: request

### C-54: Going back needs no change to the data file
Observable: The operator's rollback steps in docs/operations.md are: stop the service, start 1.4.0 with the same environment variables it understands and the same file. No edit, conversion or copy of the file is among them.
Source: request ("operators must be able to go back")

### C-55: The command line of 1.4.0 reads the new file too
Observable: `bin/tickets.js list`, `list --raw` and `show T-0001` of release 1.4.0 run on a file the new release wrote and print every ticket, with exit status 0.
Source: request ("it must still start on the data file ... and show every ticket"); existing: README.md (the command line reads the same file)

### C-56: After a rollback the new release stamps the tickets that lack a due time
Observable: Run the new release, then 1.4.0 (which on its first save drops the `due` fields it does not know and may add tickets), then the new release again. At the last start every ticket has a `due`; one added under 1.4.0 has `created` + the hours of its priority, and one that lost its `due` has its `created` + the hours of its priority at that start. The ticket's original `due` may differ from the new one when its priority changed or the hours variables changed in between.
Source: implied: U-9; choice: 1.4.0 cannot be changed, so re-deriving from `created` and `priority` is the only stamp available; the limit is stated in docs/operations.md (C-77)

### C-57: A ticket shows the same due time in every answer and after a restart
Observable: With the data file, the `due` shown for T-0001 by `POST`, `GET`, the list, `PATCH` and a transition, and again after stopping and starting the service, is one value.
Source: request ("set once")

### C-58: Due times work for the largest ticket numbers and counts
Observable: A ticket numbered T-10000 or above, and a listing of 100 items, show `due` in every item; with 250 tickets of which 130 are overdue, `?overdue=true&limit=100` gives 100 items and a `next`, then 30 with `next` null.
Source: existing: src/tickets/ids.js (numbers grow past four digits), docs/api.md (limit 100)

### C-59: The command line prints what it printed in 1.4.0
Observable: `list` prints the columns ID, STATUS, PRIORITY, REQUESTER, UPDATED, TITLE; `list --raw` prints tab-separated id, status, priority, title and nothing more; `show` prints id and title, then status, priority, requester, created and updated, then the history, exactly as before, for tickets with and without a `due` in the file.
Source: existing: README.md ("they must keep their positions"), src/format.js; choice: the command line is not part of the request's "every ticket shows its due time", and a new column or line might break scripts

### C-60: The command line never writes the data file
Observable: Running `list` or `show` on a file with tickets that lack a `due` leaves the file byte for byte as it was; those tickets still print.
Source: existing: bin/tickets.js ("never writes it"), README.md

### C-61: The weekly report is unchanged
Observable: `scripts/weekly-report.js` and `--json` give the same counts by status and by priority as before, on files with and without due times, and with `DUE_TIMES` on or off.
Source: existing: scripts/weekly-report.js, README.md

### C-62: A service built from settings without the new ones uses the defaults and has due times off
Observable: Starting the service with a settings object that has only the settings of 1.4.0 (`port`, `dataFile`, `notifyFile`, `workerIntervalMs`, `maxBodyBytes`, `logRequests`), as `test/helpers.js` does, works: 4/24/72/168 hours, due times off. `loadConfig({})` still has the six settings of 1.4.0 with the values they had.
Source: request ("its existing tests must still pass as they are"); existing: test/config.test.js, test/helpers.js

### C-63: The existing tests pass as they are
Observable: `npm test` passes every test of the 117 that were in `test/` before this change, with no existing test file edited.
Source: request

### C-64: The new tests are run by `npm test`
Observable: New test files under `test/` (named `*.test.js`, using `node:test`) are run by `npm test` with the existing ones and pass; they start servers only on port 0 and touch no file outside a temporary folder. They cover at least: C-1 to C-4, C-6 to C-9, C-11 to C-13, C-15, C-18 to C-19, C-22 to C-34, C-37 to C-46, C-52 and the 1.4.0 loading rule of C-53 (an old document with the fields 1.4.0 reads).
Source: request ("Add node:test tests under test/ for the new behaviour"); existing: CONTRIBUTING.md ("Tests")

### C-65: Creating, reading, changing and moving a ticket work as before
Observable: `POST /tickets` answers 201 with an `open` ticket and an id given in order (`T-0001`, ...); `GET /tickets/:id` answers 200 or 404; `PATCH` changes title and priority, refuses a closed ticket with 409 and refuses an empty patch with 400; transitions follow open → in_progress → resolved → closed with reopen from resolved, and a move outside it is 409.
Source: existing: docs/api.md

### C-66: A change that changes nothing is still not a change
Observable: `PATCH` with the values the ticket already has adds no audit entry, leaves `updated` as it was and leaves `due` as it was.
Source: existing: docs/api.md, CONTRIBUTING.md

### C-67: The audit and notification behaviour of changes is as before
Observable: Creating a ticket appends one `ticket.created` entry with `title`, `priority`, `requester` and `status` from null, and enqueues one `ticket.created` notification to the requester; resolving enqueues one `ticket.resolved` notification; the actor is the `X-Actor` header or `system`.
Source: existing: docs/api.md, docs/decisions/0006-notification-outbox.md, docs/decisions/0007-append-only-audit-log.md

### C-68: Bad requests are refused as before
Observable: A bad body, field, `status`, `priority`, `limit` (outside 1 to 100) or `cursor` is answered 400 `invalid`; an unknown ticket or route 404 `not_found`; every error is in the envelope `{"error":{"code","message"}}`. A request that failed does not change the data file.
Source: existing: docs/api.md, docs/decisions/0004-error-envelope.md

### C-69: The checks of the data file that exist keep refusing
Observable: A file that is not JSON, has another version than 1, has a ticket with a bad field, a `nextNumber` that reuses a number, an audit log with a gap or an outbox event in no known state is refused at start with the same messages as in 1.4.0, exit status 2.
Source: existing: src/persistence.js, test/persistence.test.js

### C-70: The other settings are as before
Observable: `PORT`, `DATA_FILE`, `NOTIFY_FILE`, `WORKER_INTERVAL_MS`, `MAX_BODY_BYTES` and `LOG_REQUESTS` keep their defaults, limits and error messages; `WORKER_INTERVAL_MS=0` still turns the worker off.
Source: existing: README.md, src/config.js

### C-71: A due time is never shown without being in the file
Observable: For any ticket shown by the API with due times on, the same `due` is in the data file (in a service with one) at that moment.
Source: implied: never a state where the answer and the file differ (data lost on restart)

### C-72: No ticket is without a due time while the service runs
Observable: With due times on, no `GET /tickets` item and no single ticket lacks `due`, for tickets created before and after the start, including those the old file held.
Source: implied: C-38, C-14; a ticket without a due would be neither overdue nor on time

### C-73: Stopping saves the due times
Observable: `SIGTERM` stops the service cleanly with exit status 0 as before, and the file left holds a `due` on every ticket.
Source: existing: docs/operations.md ("SIGTERM stops it cleanly"); C-51

### C-74: The README lists the new settings
Observable: The configuration table of README.md has rows for `DUE_TIMES` (default: off; `on` switches due times on) and for `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL`, `DUE_HOURS_LOW` (defaults 4, 24, 72, 168; whole hours 1 to 8760).
Source: existing: README.md ("Every setting is an environment variable"), CONTRIBUTING.md

### C-75: The API document describes `due` and `overdue`
Observable: docs/api.md shows `due` in the ticket and its field table, states that it is set once and cannot be sent, lists `overdue` among the listing's parameters with its rules (`true` only, open and in-progress tickets, strictly after the due time), and says that with due times off the field and the parameter are absent.
Source: existing: docs/api.md describes every field and parameter

### C-76: The operations document gives the rollout in order and the rollback
Observable: docs/operations.md states the order: deploy the new release with `DUE_TIMES` unset, check that every ticket in the data file has a `due`, then set `DUE_TIMES=on` and restart; and the rollback of C-54 with the consequence of C-56.
Source: request (rollout and rollback); existing: docs/operations.md

### C-77: The operations document states the rollback's limit
Observable: docs/operations.md says that release 1.4.0 drops the due times from the file when it saves, and that the next start of the new release stamps them again from `created` and the current priority, so a ticket whose priority changed, or hours that were changed meanwhile, may give a different due time.
Source: implied: C-56

### C-78: The release is numbered and recorded
Observable: `package.json` has version 1.5.0; CHANGELOG.md has a `1.5.0` section on due times, `overdue`, the settings and the stamping of old tickets; docs/decisions/ has record 0009 on due times, listed in its README index with status Accepted, and no earlier record is edited except in its status.
Source: existing: CONTRIBUTING.md ("Releases", "Decisions"); choice: 1.5.0, a minor release, because the change adds without breaking

### C-79: The service adds no dependency
Observable: `package.json` has no `dependencies` or `devDependencies`, and the service runs on Node.js 22 or later with only its standard library.
Source: existing: CONTRIBUTING.md ("No dependencies"), package.json `engines`

### C-80: A start with an old file and due times on shows the due times at once
Observable: Starting the new release on a 1.4.0 file with `DUE_TIMES=on` shows `due` on T-0001 in the first `GET /tickets/T-0001` and lists the overdue open tickets in the first `GET /tickets?overdue=true`, with no restart in between.
Source: request; implied: the operator who skips the two-step rollout is still safe (C-38)
