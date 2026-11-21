## Use cases

### U-1: A requester or agent opens a ticket and sees when a response is due
Flow: With DUE_TIMES on, they `POST /tickets` with a priority (urgent, high, normal or low; normal when none is given). The 201 answer shows `due`, an ISO 8601 UTC time exactly 4 hours (urgent), 24 hours (high), 72 hours (normal) or 168 hours (low) after `created`. `GET /tickets/:id` and `GET /tickets` show the same `due`, whatever the ticket's status.
Source: request

### U-2: An agent lists the tickets that have missed their response time
Flow: With DUE_TIMES on, they call `GET /tickets?overdue=true`. They see only tickets whose status is open or in_progress and whose `due` has passed, in id order, paged like every listing (`items`, `next`, `limit`, `cursor`).
Source: request

### U-3: The help desk changes its response times
Flow: The operator sets the hours for one or more priorities in the service's configuration and restarts the service. Tickets created from then on get the new hours. Tickets that already exist keep the `due` they had, and a ticket whose priority is changed keeps its `due` too.
Source: request

### U-4: An operator turns due times on in production
Flow: The operator installs the new release with DUE_TIMES unset (or not `on`) and starts it on the production data file. The service answers exactly as release 1.4.0 does, but the data file now holds a due time for every ticket, old and new. When the operator is satisfied, they set DUE_TIMES=on and restart; `due` and `overdue` now work for every ticket.
Source: request

### U-5: An operator goes back to 1.4.0
Flow: After the new release has written the data file (with DUE_TIMES off or on), the operator starts release 1.4.0 on the same file. It starts and `GET /tickets` shows every ticket. The command line `bin/tickets.js` of either release also reads the file.
Source: request

### U-6: Existing users and scripts carry on
Flow: Clients, the operators' command line, the weekly report and the existing tests behave as before. Nothing they use today changes, except that with DUE_TIMES on the tickets also show `due`.
Source: request

## Clauses

### C-1: With DUE_TIMES on, a new ticket's due time is its creation time plus the response hours of its priority
Observable: Start the service with DUE_TIMES=on and no hours settings. Create tickets of each priority. The answer to `POST /tickets` has `due` and, for each, `due` minus `created` is exactly 4 h for urgent, 24 h for high, 72 h for normal (also when no priority is given) and 168 h for low. `due` has the same form as `created` (ISO 8601, UTC, milliseconds, e.g. `2025-09-02T08:00:00.000Z`).
Source: request

### C-2: With DUE_TIMES on, every ticket shows `due` wherever the service shows the ticket
Observable: `due` is in the ticket of `GET /tickets/:id`, of every item of `GET /tickets`, and of the answers of `POST /tickets`, `PATCH /tickets/:id` and `POST /tickets/:id/transition`, with the same value in all of them, for tickets of every status, resolved and closed included.
Source: request ("Every ticket shows its due time as `due`")

### C-3: A ticket's due time is set once
Observable: After a ticket is created, changing its priority with `PATCH`, moving it through any status, reopening it, and restarting the service all leave its `due` exactly as the creation answer showed it. Also unchanged: `created`.
Source: request

### C-4: The response hours are configurable, per priority, without a code change
Observable: The operator sets the hours for each of the four priorities in the service's configuration (environment variables, as every other setting in README.md, "Configuration"), restarts, and a ticket created afterwards has `due` equal to `created` plus the configured hours for its priority. A priority whose hours are not set uses its default (4, 24, 72, 168). The settings are listed in the README's configuration table with their defaults.
Source: request; implied: every other setting is an environment variable listed in README.md
Open: The names of the four settings are not given. The builder chooses them and documents them in the README table; a test must find them there, not assume them. What range of hours is accepted (zero, fractions, an upper limit) is the requester's to decide; a test uses whole numbers of hours from 1 to 1000 only.

### C-5: A change of the hours moves no existing due time
Observable: Create tickets, change the hours, restart, and create more. The earlier tickets show the `due` they had; only the later tickets use the new hours.
Source: request

### C-6: A hours setting the service cannot use stops it at start, naming the variable
Observable: A setting for hours that is not a number of hours (for example text like `soon`) makes the service exit at start with a message that names that variable, as README.md says for any unusable setting. The data file is not changed by that start.
Source: existing: README.md ("A value the service cannot use ... stops it at start with a message naming the variable"), src/config.js

### C-7: A ticket created while DUE_TIMES is off still gets its due time in the data file
Observable: With DATA_FILE set and DUE_TIMES not `on`, create a ticket. The data file's record of that ticket holds its due time (in the field `due`), equal to created plus the hours of its priority. Restart with DUE_TIMES=on and `GET /tickets/:id` shows that same `due`.
Source: implied: "Due times are switched on in production only once the data file holds them"; a ticket made in the off period would otherwise reach the switch without one
Open: The field's name in the data file is not given; `due`, the same as the API, is the builder's choice and a test may check it only through the restart.

### C-8: Starting on a data file whose tickets have no due time gives each one a due time from its own creation time and priority
Observable: Take a data file written by 1.4.0 (tickets with `created` and `priority`, no due time). Start the new release on it with DUE_TIMES off or on, without sending a request. The file on disk now holds, for every ticket whatever its status, `created` plus the hours for its own priority as its due time. A ticket created long ago has a due time long past. A ticket without a due time, which a 1.4.0 run left after the rollback (U-5), gets one the same way at the next start.
Source: request ("The tickets already in the production data file get due times too, from their own creation time and priority")

### C-9: A ticket that already has a due time in the data file keeps it
Observable: Start the new release on a file where a ticket holds a due time that differs from created plus the current hours (because the hours or the priority changed since). The ticket shows, and the file keeps, that due time. Only tickets without one are given one.
Source: request ("keep them from then on")

### C-10: Giving the old tickets due times changes nothing else in the data file
Observable: After the start of C-8, every field of the file other than the tickets' due times is as it was: `updated` of every ticket, the audit log (no new entries), the outbox (no new notifications), `nextNumber`, and the file's `version`. `GET /tickets/:id/audit` of an old ticket is the same before and after.
Source: implied: a due time is not a change a person made; the audit log is append-only and a change that changes nothing is not a change (CONTRIBUTING.md, docs/decisions/0007)

### C-11: A data file whose due time is not a time is refused at start
Observable: A file in which a ticket's due time is not a time (for example `"soon"`) stops the service at start with a message that names the record (e.g. `tickets[0].due`), as it does for any other bad field. The file is not changed.
Source: existing: docs/operations.md ("At start the service checks every record"), src/persistence.js

### C-12: The data file is written so that release 1.4.0 can still read it
Observable: Start release 1.4.0 (a checkout of its tag, with a copy of the file) on a data file that the new release wrote, with at least one ticket made by the new release and one old ticket. It starts without refusing the file, and `GET /tickets` lists every ticket with the same id, title, priority, requester, status, created and updated as the new release showed. The audit log and the outbox it shows are the same as before. This holds for a file written with DUE_TIMES off and with it on.
Source: request ("it must still start on the data file the new release wrote and show every ticket"); existing: docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote")

### C-13: The new release still reads every data file that 1.4.0 wrote
Observable: A file from 1.4.0 (version 1, tickets without a due time) loads in the new release, with DUE_TIMES off or on, and shows every ticket exactly as before, apart from C-8.
Source: existing: docs/decisions/0008-json-data-file.md

### C-14: Until DUE_TIMES is `on`, the service answers exactly as 1.4.0 does
Observable: With DUE_TIMES unset, empty or `off`, the same requests give the same answers as 1.4.0, byte for byte apart from times: no ticket in any answer has a `due` field; `GET /tickets?overdue=true` is treated like any parameter the service does not know, so it lists every ticket as `GET /tickets` does; the audit entries, the outbox and the errors have the same fields and values as before. The operators' command line shows the same output.
Source: request ("until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today")
Open: What the service does with a DUE_TIMES value that is neither `on`, `off`, unset nor empty (for example `ON`, `yes`, `1`): treat as off, or refuse to start under the rule of C-6. The requester decides; a test uses only `on`, `off`, unset and empty.

### C-15: Only DUE_TIMES=on switches due times on, and it is read at start
Observable: With DUE_TIMES=on the answers of C-1, C-2 and C-16 hold; changing the variable takes effect when the service is started again, like every other setting.
Source: request; implied: settings are read at start (src/config.js)

### C-16: `GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed
Observable: With DUE_TIMES=on and a clock that can be moved: a ticket that is open or in_progress and whose `due` is before now is listed. A ticket whose `due` is still ahead is not listed. A resolved or closed ticket is not listed, however long ago its `due` was. The items are in id order and in the ticket's shape (C-2). After the clock passes a ticket's `due`, the ticket appears in the list without any change to the ticket; when a listed ticket is resolved it leaves the list; when a resolved ticket is reopened with a past `due` it enters the list.
Source: request
Open: Whether a ticket is overdue at exactly the instant of its `due` is not given ("has passed" suggests later than `due`); a test does not check that instant.

### C-17: The overdue listing is paged and combines with the other filters like any listing
Observable: `?overdue=true` takes `limit` and `cursor`, answers `{ items, next }` and follows the pages to the end without a ticket missing or repeated. With `status` or `priority` it lists only tickets that meet the overdue rule and the filter given (for example `?overdue=true&status=open&priority=urgent` lists only open urgent overdue tickets).
Source: existing: docs/api.md ("Filters combine: a ticket is listed only when it matches every filter given", "Tickets come in id order, a page at a time")
Open: Today's code combines `status` and `priority` with "or", not "and" as docs/api.md says (`matchesFilters` in src/tickets/query.js). Whether to correct that is the requester's to decide; this clause is about `overdue` only, and a test of `overdue` combined with another filter uses a combination that gives the same answer under both readings, or the stated "every" rule.

### C-18: A value of `overdue` other than `true` is not specified
Observable: Nothing is checked for `overdue=false`, `overdue=` or other values, except that the service answers (200 listing or 400 `invalid` in the error envelope), never 500, and never lists a resolved or closed ticket as overdue.
Source: choice: the request defines only `overdue=true`
Open: Whether `overdue=false` lists the tickets not overdue, all tickets, or is `invalid` (400, as an unusable `status` is today) is the requester's to decide.

### C-19: A due time never makes a request fail
Observable: Creating a ticket of any priority, with any hours accepted by the configuration, answers 201 and not 500. Any ticket the service holds can be read with `GET /tickets/:id`.
Source: implied: a created time plus hours must stay a time the service can write (a JavaScript date has a limited range)

### C-20: The operators' command line and the weekly report still work on a file that holds due times
Observable: `node bin/tickets.js list`, `list --raw` (columns id, status, priority, title, tab-separated, same positions), `show ID`, its exit codes, and `scripts/weekly-report.js` (also `--json`) give the same output on a file with due times as on the same file without them. They never write the file.
Source: existing: README.md ("Command line"), docs/operations.md

### C-21: Everything the service already does keeps working, and the existing tests pass as they are
Observable: With DUE_TIMES unset, `npm test` passes with the existing test files unchanged (the helpers' settings, which name no due-time setting, still start a service). The new tests are files of node:test under `test/`, run by the same `npm test`, and cover C-1 to C-17.
Source: request

### C-22: The release is named and its operator documentation is written
Observable: `package.json` version is above 1.4.0 and CHANGELOG.md has a section for it that mentions due times and DUE_TIMES. README.md's configuration table lists DUE_TIMES and the hours settings with their defaults. docs/api.md describes `due` and `overdue`. docs/operations.md or the README says how to switch on (start with it off, then on) and how to go back to 1.4.0.
Source: existing: CONTRIBUTING.md ("Releases"; "a change of behaviour comes with a test"), README.md ("Every setting is an environment variable"); request ("operators must be able to go back to ... 1.4.0")
