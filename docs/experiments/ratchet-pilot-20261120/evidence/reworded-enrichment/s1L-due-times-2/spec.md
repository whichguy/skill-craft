## Use cases

### U-1: A help-desk lead sets the response times, to promise what the team can keep
Flow: The lead (through whoever runs the service) sets one number of hours per priority in the service's environment and restarts it. Without any setting the hours are 4 (urgent), 24 (high), 72 (normal), 168 (low). A ticket created after the restart gets its due time from the new hours; tickets that already have a due time keep it. A value the service cannot use stops it at start with a message naming the variable.
Source: request ("the help desk must be able to change those hours without a code change"); existing: README.md "Configuration" (every setting is an environment variable; an unusable value stops the service at start naming the variable).

### U-2: A requester or agent opens a ticket, to see by when it will be answered
Flow: They `POST /tickets` as today. With due times on, the 201 answer carries `due`: the ticket's `created` time plus the hours of its priority. With due times off, the answer is exactly what it is today.
Source: request ("Each ticket gets a due time ... Every ticket shows its due time as `due`").

### U-3: An agent works a ticket, to see that its promise does not move
Flow: They read the ticket (`GET /tickets/:id`), change its priority (`PATCH`), move it along its lifecycle (`POST .../transition`), reopen it, and read it again. `due` is the same value every time.
Source: request ("A ticket's due time is set once: a later change of the hours or of the ticket's priority does not move it").

### U-4: An agent lists the tickets that are late, to work the most urgent backlog first
Flow: They call `GET /tickets?overdue=true` (optionally with `status`, `priority`, `limit`, `cursor`). They see, in id order and in pages, only open and in-progress tickets whose due time is before now. A resolved or closed ticket is never listed. A value other than `true` is refused.
Source: request ("`GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed"); existing: docs/api.md "List tickets".

### U-5: An operator deploys the new release on the production data file, to give the existing tickets their due times without changing any answer yet
Flow: They start the new release with `DATA_FILE` pointing at the file 1.4.0 wrote and `DUE_TIMES` not `on`. Before the service answers its first request, every ticket in the file without a due time has been given one, and the file on disk holds them. Every API answer is the same as 1.4.0's.
Source: request ("The tickets already in the production data file get due times too ... Due times are switched on in production only once the data file holds them: until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today").

### U-6: An operator switches due times on, to start promising response times
Flow: With the data file holding due times (U-5), they set `DUE_TIMES=on` and restart. Every ticket now shows `due` and the overdue listing works.
Source: request ("until the DUE_TIMES environment variable is `on`").

### U-7: An operator goes back to 1.4.0, to recover from a misbehaving release
Flow: They stop the new release and start 1.4.0 on the data file the new release wrote. 1.4.0 starts and shows every ticket exactly as before.
Source: request ("operators must be able to go back to the current release, 1.4.0, and it must still start on the data file the new release wrote and show every ticket"); existing: src/persistence.js (version 1; a different version is refused), docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote").

### U-8: An operator or integrator keeps using everything else, to be unaffected
Flow: Clients, the command line (`list`, `list --raw`, `show`), the weekly report and the notification worker behave as in 1.4.0.
Source: request ("Everything the service already does keeps working, and its existing tests must still pass as they are").

### U-9: A developer runs the tests, to know the change works
Flow: They run `npm test` and see the existing tests and the new due-time tests pass.
Source: request ("Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones").

## Clauses

### C-1: The response time of an urgent ticket is 4 hours by default
Observable: With no hours setting, with a manual clock at `2025-09-01T08:00:00.000Z`, `POST /tickets` with `"priority":"urgent"` answers `due` = `2025-09-01T12:00:00.000Z`.
Source: request

### C-2: The response time of a high ticket is 24 hours by default
Observable: At creation time `2025-09-01T08:00:00.000Z`, a `high` ticket has `due` = `2025-09-02T08:00:00.000Z`.
Source: request

### C-3: The response time of a normal ticket is 72 hours by default
Observable: At creation time `2025-09-01T08:00:00.000Z`, a `normal` ticket (including one created without a `priority`, which is `normal`) has `due` = `2025-09-04T08:00:00.000Z`.
Source: request; existing: docs/api.md ("`priority` is optional (`normal`)")

### C-4: The response time of a low ticket is 168 hours by default
Observable: At creation time `2025-09-01T08:00:00.000Z`, a `low` ticket has `due` = `2025-09-08T08:00:00.000Z`.
Source: request

### C-5: A ticket's due time is exactly its creation time plus the hours, to the millisecond
Observable: For every ticket, `due` minus `created` equals the hours of the ticket's priority (at the time `due` was set) times 3,600,000 ms, with no daylight-saving or calendar adjustment (hours are counted in UTC). Example: `created` `2025-03-29T23:30:15.250Z`, `high` → `due` `2025-03-30T23:30:15.250Z`.
Source: implied: "the time it was created plus the response time"

### C-6: `due` is written in the same form as the other times of the API
Observable: `due` is an ISO 8601 UTC string with milliseconds and a trailing `Z`, like `created` (`2025-09-02T08:00:00.000Z`).
Source: existing: docs/api.md "Conventions" ("Times are ISO 8601 in UTC")

### C-7: The hours of each priority are set by one environment variable each
Observable: `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` and `DUE_HOURS_LOW` set the hours of that priority. With `DUE_HOURS_URGENT=2` and creation at `2025-09-01T08:00:00.000Z`, an urgent ticket's `due` is `2025-09-01T10:00:00.000Z`; the other three priorities still use their defaults. Unset or empty means the default (4, 24, 72, 168).
Source: choice: the request fixes that the hours are changeable without code but not how; the service's existing way of configuring is an environment variable per setting (README.md "Configuration"), so these four names are decided here.

### C-8: A setting of hours takes effect for tickets created after the service starts with it
Observable: After a restart with `DUE_HOURS_HIGH=10`, a `high` ticket created next has `due` = `created` + 10 hours. A running service does not re-read its environment.
Source: choice: every existing setting is read once at start (src/config.js); no endpoint or file reload is asked for.

### C-9: The hours are whole numbers from 1 to 8760
Observable: `DUE_HOURS_*` values `1` and `8760` are accepted. `0`, `8761`, `-3`, `4.5`, `abc` and `1e2` stop the service at start. Surrounding whitespace is ignored, as for the other numeric settings.
Source: choice: 8760 (one year) is decided as the largest, 1 as the smallest, because a due time at or before creation, or a date beyond what JavaScript can represent, is meaningless; whole hours follow the existing numeric settings (src/config.js `wholeNumber`).

### C-10: An unusable hours value stops the service at start, naming the variable
Observable: Starting with `DUE_HOURS_NORMAL=abc` (or any value C-9 refuses), `npm start` writes a message containing `DUE_HOURS_NORMAL` to standard error, listens on no port and exits with status 2, the same as `PORT=http` does today.
Source: existing: README.md "Configuration" ("A value the service cannot use ... stops it at start with a message naming the variable"); src/server.js (ConfigError exits 2)

### C-11: The hours settings are checked whether or not due times are on
Observable: `DUE_TIMES` unset and `DUE_HOURS_LOW=abc` stops the service at start as in C-10.
Source: choice: due times are computed and stored while the switch is off (C-19, C-20), so the hours are in use then; failing at start is safer than failing at the switch.

### C-12: A ticket's due time is set when the ticket is created and is stored with it
Observable: `GET /tickets/:id` straight after creation, and at any later time, shows the `due` the creation answer showed.
Source: request ("A ticket's due time is set once")

### C-13: Changing the hours does not move the due time of an existing ticket
Observable: A ticket created under `DUE_HOURS_HIGH` unset (due = created + 24 h); the service is restarted with `DUE_HOURS_HIGH=10`; the ticket's `due` is unchanged and a ticket created afterwards gets 10 h.
Source: request ("a later change of the hours ... does not move it")

### C-14: Changing a ticket's priority does not move its due time
Observable: A `normal` ticket (due created + 72 h) patched to `urgent` shows the same `due` in the 200 answer and in later reads; the audit entry of the patch lists `priority` only.
Source: request ("a later change ... of the ticket's priority does not move it")

### C-15: A move through the lifecycle does not move the due time
Observable: `open` → `in_progress` → `resolved` → `open` (reopen) → `in_progress` → `resolved` → `closed`: every answer and every later read shows the same `due`.
Source: implied: "set once"

### C-16: A request that changes nothing leaves `due` and `updated` as they were
Observable: `PATCH` with the title and priority the ticket already has answers 200 with the same `due` and the same `updated`, and adds no audit entry.
Source: existing: docs/api.md "Change a ticket"

### C-17: A client cannot set or change `due`
Observable: `POST /tickets` or `PATCH /tickets/:id` with a `due` field in the body answers 400 `invalid` in the error envelope, whether `DUE_TIMES` is `on` or not, and the ticket is not created or changed.
Source: existing: docs/api.md "Conventions" (unknown fields are refused, 400); src/tickets/validate.js `onlyFields`

### C-18: With `DUE_TIMES` equal to `on`, every ticket shows `due`
Observable: With `DUE_TIMES=on`, the ticket object has the field `due` (a string, C-6) in: the 201 of `POST /tickets`, the 200 of `GET /tickets/:id`, the 200 of `PATCH /tickets/:id`, the 200 of `POST /tickets/:id/transition`, and every item of `GET /tickets`. It has its previous seven fields (`id`, `title`, `priority`, `requester`, `status`, `created`, `updated`) with the values they have today.
Source: request ("Every ticket shows its due time as `due`")

### C-19: Only the exact value `on` switches due times on
Observable: `DUE_TIMES` unset, empty, `off`, `ON`, `On`, `true`, `1`, ` on` or `on ` all leave due times off (C-20); `on` turns them on. Any of these values lets the service start.
Source: choice: the request names `on` only; treating everything else as off is the loosest reading that keeps "answers exactly as it does today" the default and never refuses to start over this switch.

### C-20: With due times off, no answer shows `due`
Observable: Without `DUE_TIMES=on`, no ticket object in any API answer has a `due` field; a ticket has exactly the seven fields of C-18.
Source: request ("until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today")

### C-21: With due times off, `overdue` in the query changes nothing
Observable: Without `DUE_TIMES=on`, `GET /tickets?overdue=true` answers what `GET /tickets` answers (as `?offset=40` does today, unknown parameters are ignored), and `?overdue=banana` is answered 200, not 400.
Source: request ("answers exactly as it does today"); existing: test/query.test.js ("ignores parameters it does not know")

### C-22: With due times off, every other answer is the one 1.4.0 gives
Observable: For the same data and the same requests, without `DUE_TIMES=on` the status codes, bodies (ticket objects, pages, `next` cursors, error envelopes and messages), the audit log of every ticket, and `GET /admin/outbox` equal 1.4.0's, apart from values that depend on the time of the request.
Source: request ("answers exactly as it does today")

### C-23: Due times are computed and stored while the switch is off
Observable: With `DUE_TIMES` unset, a ticket created at `2025-09-01T08:00:00.000Z` as `high` has in the data file `"due": "2025-09-02T08:00:00.000Z"`. After the service is restarted with `DUE_TIMES=on`, `GET /tickets/:id` shows that same `due`.
Source: implied: "Due times are switched on in production only once the data file holds them" — a ticket created between deploy and switch-on must hold its due time as well.

### C-24: The data file holds a ticket's due time as the ticket's field `due`
Observable: In the JSON file at `DATA_FILE`, each element of `tickets` has `"due"` (a string as in C-6) beside its seven earlier fields.
Source: implied: "the data file holds them"; existing: docs/decisions/0008-json-data-file.md ("a field added to a ticket is added [to the record functions] too, or it is lost at the next restart")

### C-25: A restart keeps every due time
Observable: Create tickets, stop the service, start it again on the same `DATA_FILE`: every ticket shows the same `due` as before the restart (with `DUE_TIMES=on`).
Source: request ("keep them from then on")

### C-26: At start, a ticket in the data file without a due time is given one
Observable: A data file written by 1.4.0 (tickets have no `due`) is started with the new release. Ticket `created` `2025-08-20T10:00:00.000Z`, `urgent` gets `due` `2025-08-20T14:00:00.000Z`; `created` `2025-08-20T10:00:00.000Z`, `low` gets `2025-08-27T10:00:00.000Z`.
Source: request ("The tickets already in the production data file get due times too, from their own creation time and priority")

### C-27: Every ticket gets a due time at start, whatever its status
Observable: After C-26, tickets whose status is `open`, `in_progress`, `resolved` and `closed` each have a `due` in the data file.
Source: request ("The tickets already in the production data file")

### C-28: The due time given at start uses the ticket's priority and the hours in force at that start
Observable: A 1.4.0 ticket created as `normal` and since patched to `urgent` gets `created` + 4 h when the service starts with the default hours; with `DUE_HOURS_URGENT=2` it gets `created` + 2 h.
Source: choice: the request says "from their own creation time and priority", and the priority the ticket has at that time is the only one the file holds; the hours in force are the only ones that exist.

### C-29: The due times given at start are in the data file before the service answers
Observable: When `npm start` has logged that it is listening, the file at `DATA_FILE` already contains a `due` for every ticket, with `DUE_TIMES` unset as well as `on`; reading the file right after start needs no request to the API.
Source: request ("Due times are switched on in production only once the data file holds them")

### C-30: A ticket that already has a due time keeps it at start
Observable: A data file where some tickets have `due` and others do not: after start, those with `due` show the value in the file (even if it differs from created + hours of their priority or of the current hours) and only the others are given one.
Source: request ("keep them from then on"; "A ticket's due time is set once")

### C-31: A second start changes no due time
Observable: Start, stop and start again on the same file with different `DUE_HOURS_*` and different priorities patched in between: no ticket's `due` differs from what the first start stored.
Source: request ("keep them from then on")

### C-32: Giving due times at start is not an audited change and does not touch the tickets' other fields
Observable: After the start in C-26, `GET /tickets/:id/audit` of every ticket lists the same entries as before (same `seq` values, no entry about `due`), the log has the same number of entries, `updated` of every ticket is unchanged, and the outbox has no new notification.
Source: choice: the audit log records changes made by people (docs/decisions/0007-append-only-audit-log.md) and no one changes the ticket; 1.4.0 must also read the log back (C-36, C-37).

### C-33: A data file with a `due` that is not a time is refused at start
Observable: A data file where `tickets[3].due` is `"soon"` or `5` stops the service at start, as other record faults do, with a message that names `tickets[3].due` and exits with status 2; the file is not changed.
Source: existing: docs/operations.md and src/persistence.js ("At start the service checks every record ... names the record")

### C-34: A data file without any `due` is still accepted
Observable: A data file as 1.4.0 writes it (version 1, tickets without `due`) loads, and every ticket is shown with every field it had.
Source: existing: docs/decisions/0008-json-data-file.md ("must keep loading the files the previous version wrote")

### C-35: The data file keeps its format version
Observable: The file the new release writes has `"version": 1`, and the top-level fields `savedAt`, `nextNumber`, `tickets`, `audit` and `outbox` (with `nextId` and `events`) with the shapes they have today.
Source: implied: 1.4.0 refuses any version but 1 (src/persistence.js), so rollback (C-36) needs version 1; existing: docs/decisions/0008-json-data-file.md

### C-36: 1.4.0 starts on a data file the new release wrote and shows every ticket
Observable: With a data file written by the new release (with `due` on every ticket, with `DUE_TIMES` on or off), 1.4.0 started on it with `DATA_FILE` listens on its port; `GET /tickets` pages through every ticket with its seven fields, the values they had; `GET /tickets/:id/audit` and `GET /admin/outbox` show everything they showed; `node bin/tickets.js list` and `show` of 1.4.0 show every ticket.
Source: request ("it must still start on the data file the new release wrote and show every ticket")

### C-37: The new release does not write anything into the data file that 1.4.0 checks and refuses
Observable: Every record the new release writes in `audit` and `outbox.events` and every ticket's `id`, `title`, `requester`, `priority`, `status`, `created`, `updated` passes the checks 1.4.0 makes (non-empty strings, valid times, audit `seq` numbered 1, 2, 3 ... in order, `nextNumber` above every ticket number, `outbox.nextId` above every event id).
Source: implied: C-36

### C-38: 1.4.0 working on that file loses no ticket, and the new release starts on the result
Observable: After 1.4.0 has written the file (it does not keep `due`: that is 1.4.0's own behaviour and is unchanged), starting the new release on it succeeds, shows every ticket, and gives each ticket a `due` as in C-26, from its priority then. Operators are told in docs/operations.md that a rollback to 1.4.0 loses the stored due times, which the later start recomputes.
Source: implied: "go back ... and it must still start" and a later return forward; choice: the recomputed value uses the priority at that time (C-28) because 1.4.0 cannot be changed to keep the old one.

### C-39: With `DUE_TIMES=on`, `GET /tickets?overdue=true` lists only open and in-progress tickets whose due time has passed
Observable: Tickets A (open, due `2025-09-02T08:00:00.000Z`), B (in_progress, due `2025-09-02T08:00:00.000Z`), C (resolved, same due), D (closed, same due), E (open, due `2025-09-04T08:00:00.000Z`), at clock `2025-09-03T00:00:00.000Z`: the answer lists A and B and no other.
Source: request

### C-40: A ticket is overdue only strictly after its due time
Observable: A open ticket due `2025-09-02T08:00:00.000Z`: at clock `2025-09-02T08:00:00.000Z` it is not listed by `?overdue=true`; at `2025-09-02T08:00:00.001Z` it is.
Source: choice: "has passed" is read as strictly later than the due time; the request gives no tie rule.

### C-41: The overdue check is made at the time of the request, by the service's clock
Observable: A ticket not listed by `?overdue=true` at one instant is listed once the clock has moved past its due time, with no change to the ticket and no restart; a ticket that reaches resolved or closed stops being listed.
Source: implied: "whose due time has passed"; existing: src/clock.js (the service reads time from its clock)

### C-42: A reopened ticket is overdue again if its due time has passed
Observable: A ticket whose due time has passed, resolved (not listed) and reopened to `open` (listed again, with the same `due`).
Source: implied: C-15 and "open and in-progress tickets"

### C-43: The overdue listing is in id order and in cursor pages
Observable: `?overdue=true` answers `{ "items": [...], "next": <cursor or null> }` in id order; `limit` (1–100, 20 by default) and `cursor` work as they do for the unfiltered list, with no overdue ticket served twice or skipped, and `next` is null on the last page.
Source: existing: docs/api.md "List tickets", docs/decisions/0005-cursor-pagination.md

### C-44: With no overdue ticket the listing is an empty page
Observable: `?overdue=true` with no ticket overdue answers 200 `{ "items": [], "next": null }`.
Source: implied: the empty case

### C-45: `overdue` narrows a listing that has other filters
Observable: With `DUE_TIMES=on`, `?overdue=true&status=in_progress` lists only the in-progress tickets that are overdue; `?overdue=true&status=resolved` lists nothing; `?overdue=true&priority=urgent` lists only overdue open or in-progress urgent tickets. In general the answer is the listing the same query without `overdue` gives, reduced to the overdue tickets.
Source: implied: "lists only"; existing: docs/api.md ("a ticket is listed only when it matches every filter given")

### C-46: With `DUE_TIMES=on`, `overdue` must be `true`
Observable: `?overdue=false`, `?overdue=`, `?overdue=TRUE`, `?overdue=1` and `?overdue=yes` answer 400 `invalid` in the error envelope, and the message names `overdue`.
Source: choice: the request defines only `overdue=true`; refusing other values follows the rule that a filter value the service cannot use is `invalid` (docs/api.md), where silently listing everything would hide a mistaken query.

### C-47: A bad `limit`, `cursor`, `status` or `priority` is still refused with `overdue=true`
Observable: With `DUE_TIMES=on`, `?overdue=true&limit=0`, `&limit=101`, `&cursor=abc`, `&status=done`, `&priority=critical` each answer 400 `invalid`.
Source: existing: docs/api.md "List tickets"; test/api.test.js

### C-48: The listing without `overdue` is the same with the switch on
Observable: With `DUE_TIMES=on`, `GET /tickets`, with `status` and `priority` filters, limits and cursors, lists the same tickets in the same order, pages and cursors as with the switch off; only each ticket additionally has `due`.
Source: existing: docs/api.md "List tickets"

### C-49: The combination of `status` and `priority` filters is left as it is
Observable: `GET /tickets?status=...&priority=...` answers, with the switch on or off, the tickets the 1.4.0 code answers. (docs/api.md says both filters must match while src/tickets/query.js `matchesFilters` lists a ticket that matches either one; this change does not alter that.)
Source: choice: "Everything the service already does keeps working" and "answers exactly as it does today" make 1.4.0's actual answer the one to keep; correcting the discrepancy is not requested.

### C-50: Errors are in the existing envelope and no new error code appears
Observable: Every refusal this change adds (C-17, C-46) is `{"error":{"code":"invalid","message":"..."}}` with status 400; no other status or code is used for due times.
Source: existing: docs/decisions/0004-error-envelope.md

### C-51: Creating a ticket keeps what it does today
Observable: `POST /tickets` still answers 201 with `status` `open`, `created` = `updated`, the next id, enqueues the "ticket received" notification, appends one `ticket.created` audit entry whose `changes` hold exactly `title`, `priority`, `requester` and `status` (each from `null`), and saves the data file.
Source: existing: docs/api.md "Create a ticket"; src/store.js `CREATED_FIELDS`

### C-52: The audit log, the outbox and the notifications do not mention `due`
Observable: With `DUE_TIMES` on or off, no audit entry has a `due` change, and the data of a notification event holds only `title`.
Source: choice: the request asks for `due` on the ticket only; adding it to history or messages would alter what operators and the mail relay see.

### C-53: The command line prints tickets as it does today
Observable: `node bin/tickets.js list` prints the columns ID, STATUS, PRIORITY, REQUESTER, UPDATED, TITLE; `list --raw` prints tab-separated `id`, `status`, `priority`, `title` in these positions, with no further column; `show ID` prints the same lines; on a data file with or without `due`, with `DUE_TIMES` on or off.
Source: existing: README.md "Command line" (the raw columns keep their positions: the weekly report reads them by position); choice: the request's "shows its due time" is read as the API's `due`, no command-line change being asked.

### C-54: The command line and the weekly report never write the data file and work on a file with or without `due`
Observable: `node bin/tickets.js list` and `show` and `node scripts/weekly-report.js` on a 1.4.0 file (no `due`) succeed and leave the file byte for byte unchanged — giving due times to such tickets is done by the service at its start only.
Source: existing: README.md and docs/operations.md ("never changes it"; "safe to run beside the service")

### C-55: The weekly report's counts are unchanged
Observable: `node scripts/weekly-report.js --json` on the same data file prints `total`, `byStatus` and `byPriority` with the same counts as before the change.
Source: existing: scripts/weekly-report.js

### C-56: The data file is still replaced whole after every change
Observable: After each change (and after the giving of due times at start) the file is complete JSON; no `*.tmp` file is left in its folder; a stop with SIGTERM leaves the state saved.
Source: existing: docs/decisions/0008-json-data-file.md; docs/operations.md "Process"

### C-57: If the data file cannot be written at start, the service does not start
Observable: With due times to give and a `DATA_FILE` in a folder the service cannot write to, `npm start` does not listen, writes a message to standard error and exits with a status other than 0.
Source: choice: starting with due times only in memory would let the operator switch due times on when the file does not hold them (request: "only once the data file holds them").

### C-58: Ticket ids and numbers behave as today
Observable: New tickets are `T-0001`, `T-0002` ..., a number is never reused, and a data file whose `nextNumber` would reuse one is refused at start.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md; src/persistence.js

### C-59: Without `DATA_FILE` the service runs in memory with due times
Observable: With no `DATA_FILE`, creating tickets shows `due` as in C-18 (with `DUE_TIMES=on`); nothing is written to disk and no file is needed.
Source: existing: README.md ("without it the state lives in memory")

### C-60: The other settings and their defaults are unchanged
Observable: `PORT`, `DATA_FILE`, `NOTIFY_FILE`, `WORKER_INTERVAL_MS`, `MAX_BODY_BYTES` and `LOG_REQUESTS` have the same defaults, ranges and failures as in README.md; the new release adds no required variable, so starting it with the environment 1.4.0 ran with works.
Source: existing: README.md "Configuration"

### C-61: The service still uses no dependencies and runs on Node.js 22
Observable: `package.json` lists no `dependencies` or `devDependencies`; `npm start` and `npm test` need no installation and no network.
Source: existing: CONTRIBUTING.md "No dependencies"; package.json `engines`

### C-62: The release is numbered above 1.4.0 and its change is listed
Observable: `package.json` `version` is `1.5.0`; `CHANGELOG.md` has a `1.5.0` section above `1.4.0` that mentions due times, `DUE_TIMES`, the four hours variables and `overdue`.
Source: existing: CONTRIBUTING.md "Releases"; choice: 1.5.0 as the next minor version for a feature that adds fields and a filter.

### C-63: The documents describe the new behaviour
Observable: `README.md` "Configuration" lists `DUE_TIMES` (default off; only `on` switches it on) and the four `DUE_HOURS_*` variables with their defaults; `docs/api.md` documents `due` in the ticket and `overdue=true` in "List tickets"; `docs/operations.md` gives the rollout order (start the new release with `DUE_TIMES` off, check the data file holds `due`, then set `DUE_TIMES=on`) and the rollback note of C-38.
Source: existing: CONTRIBUTING.md (the API, data file and configuration changes are documented)

### C-64: The new tests live under test/ and run with `npm test`
Observable: `npm test` exits 0; the new tests are `node:test` files under `test/` and are among the tests it runs.
Source: request

### C-65: The existing tests pass unchanged
Observable: No existing file under `test/` is changed in a way that edits or removes an existing test (a helper may be added but behaves as before); `npm test` shows every pre-existing test passing.
Source: request ("its existing tests must still pass as they are")

### C-66: The new tests cover the stated behaviour without real time or fixed ports
Observable: The new tests check, at least: the four default hours (C-1 to C-4); a changed hours setting (C-7) and its refusal values (C-9); `due` unmoved by a priority change and by a changed setting (C-13, C-14); `due` present with the switch on and absent without it (C-18, C-20); the overdue listing with its status rule, its boundary, its combination and its refusals (C-39, C-40, C-45, C-46); the backfill of a 1.4.0 data file, its persistence to disk and that existing `due` values are kept (C-26, C-29, C-30); and that a file the new release wrote still loads with the 1.4.0 checks (C-36, C-37). They hold time with a manual clock, start servers on port 0 and clean up their temporary files.
Source: implied: "Add node:test tests ... for the new behaviour"; existing: CONTRIBUTING.md "Tests"
