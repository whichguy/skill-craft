## Use cases

### U-1: A support lead or agent asks which tickets have run past their promised response time
Flow: They call `GET /tickets?overdue=true`. They see the usual page (`{ "items": [...], "next": ... }`) holding only tickets that are `open` or `in_progress` and whose `due` time has passed, each showing its `due`. A ticket that is resolved or closed does not appear, however late it was. They can add `status` or `priority` to narrow it further.
Source: request

### U-2: A requester's ticket, or an agent reading it, shows when a response is due
Flow: A ticket is created with priority `urgent` at 2025-09-01T08:00:00.000Z. Every response that shows the ticket (create, get, change, transition, listing) shows `"due": "2025-09-01T12:00:00.000Z"`. The same ticket changed to `low` later still shows that `due`.
Source: request

### U-3: An operator changes the response times the help desk promises
Flow: The operator changes the hours for a priority in the service's settings and restarts the service. Tickets created from then on get a due time from the new hours. Tickets that already have a due time keep it.
Source: request

### U-4: An operator brings due times to production safely
Flow: The operator deploys the new release with `DUE_TIMES` unset. Clients see no change. The data file is given a due time for every ticket, old and new. The operator checks the file, then sets `DUE_TIMES=on` and restarts: clients now see `due` and can use `overdue=true`, and the due times are the ones that were saved, not new ones.
Source: request

### U-5: An operator goes back to 1.4.0 when the new release misbehaves
Flow: The operator stops the new release and starts 1.4.0 on the same data file. It starts and shows every ticket as it did before the new release. If they later return to the new release, every ticket has a due time again.
Source: request

### U-6: An existing client or script keeps working
Flow: A dashboard, the operator command line (`bin/tickets.js`) and the weekly report use the service as before; with `DUE_TIMES` not `on` they see exactly what 1.4.0 showed.
Source: request

## Clauses

### C-1: A new ticket's due time is its creation time plus the response time of its priority: 4 hours for `urgent`, 24 for `high`, 72 for `normal`, 168 for `low`
Observable: With no hours settings and `DUE_TIMES=on`, creating tickets at 2025-09-01T08:00:00.000Z with priority `urgent`, `high`, `normal` (also when `priority` is omitted) and `low` shows `due` of 2025-09-01T12:00:00.000Z, 2025-09-02T08:00:00.000Z, 2025-09-04T08:00:00.000Z and 2025-09-08T08:00:00.000Z.
Source: request

### C-2: The due time is exactly the ticket's `created` time plus that many elapsed hours, written like the service's other times
Observable: `due` is an ISO 8601 UTC string with milliseconds (`2025-09-01T12:00:00.000Z`) and `due` minus `created` is exactly hours × 3,600,000 ms, including across a day, month or year end and a daylight-saving change of any zone (no calendar or business-hours adjustment).
Source: request ("the time it was created plus the response time"); existing: docs/api.md ("Times are ISO 8601 in UTC")

### C-3: An operator can change the hours for each priority in the service's settings, without a code change; an unset or empty setting means the hours in C-1
Observable: With the setting for `urgent` set to 2 (and `DUE_TIMES=on`), after a restart a new urgent ticket created at 08:00 shows a `due` of 10:00 the same day; the other priorities still use their C-1 hours. Setting any one priority does not change the others.
Source: request; choice: settings are environment variables, as every other setting in README.md is, and take effect when the service next starts
Open: the names of the four variables, whether a change must take effect without a restart, and who may change them are not in the request; the requester decides. The names are documented (C-27).

### C-4: A hours setting the service cannot use stops it at start with a message naming the variable
Observable: A value that is not a whole number (`abc`, `-3`) exits the process with a non-zero status and a message naming the variable, as `PORT=http` does today, and the service does not listen.
Source: existing: README.md ("A value the service cannot use … stops it at start with a message naming the variable")
Open: whether `0` and fractional hours (`1.5`) are usable; whether the same refusal applies while `DUE_TIMES` is not `on` (the request says the service then answers "exactly as it does today", which started with any value). The requester decides.

### C-5: An hours setting too large for a due time to be represented stops the service at start, like C-4, instead of failing later
Observable: JavaScript dates hold at most 8,640,000,000,000,000 ms after 1970-01-01T00:00:00Z. A setting for which a ticket created now would get a due time past that (for example `9007199254740991` hours) is refused at start naming the variable; creating a ticket never answers 500 because of the hours.
Source: implied: C-1 must give a valid time for every ticket; runtime limit of Date
Open: the exact largest accepted value; the requester decides, any cap below the runtime limit is acceptable.

### C-6: A ticket's due time does not move when the ticket's priority changes
Observable: A `high` ticket created at 08:00 shows `due` 24 hours later; after `PATCH` to `urgent` (or `low`) the ticket shows the same `due`, in the response, in `GET /tickets/:id`, and after a restart. Changes of title, status (including reopening a resolved ticket) and resolution also leave it.
Source: request

### C-7: A change of the hours does not move the due time of any ticket that has one, including after a restart
Observable: Tickets created under the C-1 hours show the same `due` after the service is restarted with different hours, whether `DUE_TIMES` was `on` throughout or was turned on at that restart.
Source: request

### C-8: With `DUE_TIMES=on`, every ticket shows its due time as `due` wherever the API shows a ticket
Observable: `due` is present, a string, on the 201 of `POST /tickets`, on `GET /tickets/:id`, on the 200 of `PATCH /tickets/:id` (also when the patch changes nothing) and `POST /tickets/:id/transition`, and on every item of `GET /tickets`, whatever the ticket's status. The ticket's other fields are as before.
Source: request

### C-9: `GET /tickets?overdue=true` lists only tickets that are `open` or `in_progress` and whose due time has passed
Observable: With tickets whose `due` is before the current time, those with status `open` or `in_progress` are listed and those with `resolved` or `closed` are not; a ticket with `due` after the current time is not listed whatever its status; an empty result is `{ "items": [], "next": null }`. Items carry `due`.
Source: request
Open: what `overdue` means with a value other than `true` (`false`, `1`, empty): ignored, or 400 `invalid` in the envelope, or the opposite listing. The request defines only `true`; the requester decides. No check relies on any other value.

### C-10: Whether a ticket is overdue follows the current time and the current status, not the time it was last changed
Observable: With a ticket due at 12:00 and the clock at 11:59:59.999 the ticket is not listed; with the clock after 12:00:00.000 and no change to the ticket it is listed; resolving it removes it from the list; reopening it (resolved to open) lists it again, unchanged `due`. At exactly 12:00:00.000 either answer is acceptable.
Source: request ("whose due time has passed"); implied: due times are fixed (C-6), so only the clock and status move a ticket in and out

### C-11: `overdue=true` combines with `status` and `priority` so that a ticket is listed only if it meets every condition given
Observable: `?overdue=true&status=resolved` is empty; `?overdue=true&status=open` lists only overdue open tickets; `?overdue=true&priority=urgent` lists only overdue urgent tickets; `?overdue=true&status=open&priority=urgent` lists only overdue open urgent tickets.
Source: request ("lists only"); existing: docs/api.md ("Filters combine: a ticket is listed only when it matches every filter given")

### C-12: The overdue listing pages like every other listing
Observable: Tickets come in id order, at most `limit` (1 to 100, 20 when absent) to a page as `{ "items", "next" }`; `next` passed as `cursor` with the same filters gives the following overdue tickets, none missing or repeated; `next` is null on the last page.
Source: existing: docs/api.md ("List tickets"), CONTRIBUTING.md ("Listings are cursor pages")

### C-13: `status` and `priority` filtering without `overdue` behaves as it does today
Observable: `?status=open`, `?priority=urgent`, their combination, `limit`, `cursor` and their `400 invalid` answers give the same results with due times on or off as in 1.4.0.
Source: existing: docs/api.md; request ("Everything the service already does keeps working")
Open: docs/api.md says combined filters must all match, but `matchesFilters` in src/tickets/query.js lists a ticket matching either. Whether to fix that is the requester's; nothing here depends on it.

### C-14: A due time cannot be set by a client
Observable: `POST /tickets` or `PATCH /tickets/:id` with a `due` field answers 400 `invalid` in the error envelope, as for any unknown field, with `DUE_TIMES` on or off, and creates or changes nothing.
Source: implied: "a ticket's due time is set once", from its creation time and priority; existing: docs/api.md ("Unknown fields … are refused")

### C-15: Due times are switched on only by `DUE_TIMES=on`
Observable: With `DUE_TIMES` equal to `on`, C-8 and C-9 apply. With it unset or empty they do not, and the service answers as C-16 and C-17 say.
Source: request
Open: what other values do (`ON`, `1`, `true`, `off`): treated as not on, or refused at start. The requester decides.

### C-16: Until `DUE_TIMES` is `on`, no ticket the API shows has a `due` field
Observable: Every ticket body (create, get, change, transition, listing items) has exactly the fields it has in 1.4.0: `id`, `title`, `priority`, `requester`, `status`, `created`, `updated`. This holds for tickets created before the release, while it ran, and after a restart.
Source: request

### C-17: Until `DUE_TIMES` is `on`, `overdue` in a listing has no effect
Observable: `GET /tickets?overdue=true` answers exactly what the same request without `overdue` answers (same tickets, same pages), as 1.4.0 does; `overdue=false` or `overdue=x` also gives no 400.
Source: request ("answers exactly as it does today")

### C-18: Until `DUE_TIMES` is `on`, everything else the API answers is as in 1.4.0
Observable: The same requests on the same data give the same status codes and bodies (errors, audit entries, outbox, health), apart from the ticket ids and times that differ by run.
Source: request

### C-19: A ticket created while `DUE_TIMES` is not `on` still gets its due time, and the data file holds it
Observable: A ticket created (`urgent`, 08:00) with `DUE_TIMES` unset, then the service stopped and started with `DUE_TIMES=on` and a different hours setting, shows `due` 12:00 the same day, and nothing is recalculated.
Source: request ("only once the data file holds them"); implied: C-7

### C-20: Every ticket already in the data file gets a due time from its own creation time and priority, and keeps it from then on
Observable: Starting the new release (any `DUE_TIMES`) on a data file whose tickets have no due time gives each one due = its `created` + the hours of its current `priority` (C-1 hours unless set). When later shown (`DUE_TIMES=on`) the due is the same after any number of restarts, after a priority change (C-6) and after the hours change (C-7). A ticket that already has a due time in the file keeps it. This also covers tickets without one that 1.4.0 wrote or rewrote (C-24).
Source: request

### C-21: The data file holds every ticket's due time once the new release has started on it, with `DUE_TIMES` not yet `on`
Observable: After the service has started and is answering on a data file that had no due times, without any request that changes a ticket, the file read as JSON has a due time for every ticket in it (a `due` field on each ticket record, the same ISO string C-8 will show). Starting on a file that already holds them leaves them as they are.
Source: request ("switched on in production only once the data file holds them"); choice: written at start, since the service otherwise saves only after a change, and the command line never writes
Open: whether operators prefer an explicit one-off migration instead of a write at start; the requester decides. Whatever is chosen, the observable result for an operator, using only the new release, is a file that holds every due time while `DUE_TIMES` is not `on`.

### C-22: Giving due times to existing tickets changes nothing else about them
Observable: After C-20/C-21, each ticket's `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` are as before, the audit log has no new entry, the outbox has no new notification, and `nextNumber` and outbox ids are as before. Creating a ticket writes the same audit entry as in 1.4.0 and no extra notification.
Source: implied: due times are derived from fields, not a change made by an agent; existing: CONTRIBUTING.md ("A change that changes nothing is not a change: no audit entry, no notification"), docs/api.md (`updated`)

### C-23: A data file written by the new release can be started by 1.4.0, which shows every ticket
Observable: The file written by the new release, whether `DUE_TIMES` was never `on` or was `on`, keeps `"version": 1`, and all the fields 1.4.0 reads keep their place and meaning; the version of src/persistence.js at the base commit (`git show ab7b9ee:src/persistence.js`) loads it without error, and 1.4.0 `GET /tickets` and `bin/tickets.js list` show all its tickets, with all the 1.4.0 fields.
Source: request ("must still start on the data file the new release wrote and show every ticket"); existing: docs/decisions/0008-json-data-file.md (version 1; loading keeps only the fields it knows)

### C-24: The new release starts again on a file that 1.4.0 has since written, and tickets without a due time get one
Observable: A file in which tickets lack due times because 1.4.0 rewrote it (including tickets 1.4.0 created) is accepted by the new release, which gives those tickets due times as in C-20 and keeps the ones it can read.
Source: implied: U-5, "go back" being reversible; existing: docs/decisions/0008-json-data-file.md ("A field older files do not have takes its default")

### C-25: A data file whose due time is not a time is refused at start with the reason
Observable: A ticket record with `due` that is not an ISO time string stops the service at start with a message naming the file and the record (for example `tickets[3].due is not a time`) and a non-zero exit, as other bad records do today.
Source: existing: docs/decisions/0008-json-data-file.md ("a file that fails a check stops the service with the reason"); src/persistence.js

### C-26: The operator command line and the weekly report keep working on a file that holds due times
Observable: `bin/tickets.js list` and `show` run on it without error and without writing the file; `list --raw` prints tickets as before with the columns id, status, priority, title in those positions, tab-separated; `scripts/weekly-report.js` gives the same counts.
Source: existing: README.md ("Command line"), src/format.js
Open: whether `list` or `show` should also print the due time. Nothing is required by the request beyond the API; the requester decides.

### C-27: The new settings are documented and the release is marked as new
Observable: README.md's configuration table lists `DUE_TIMES` and the four hours settings with their defaults; docs/api.md describes `due` and `overdue`; docs/operations.md says how to turn due times on and how to go back to 1.4.0; `package.json` has a version other than 1.4.0, with a matching new CHANGELOG.md section.
Source: existing: README.md ("Configuration"), CONTRIBUTING.md ("Releases"); request ("go back to the current release, 1.4.0")

### C-28: The existing tests pass as they are, and new tests for the new behaviour run with them
Observable: The test files that exist now are unchanged and `npm test` passes them; new `node:test` files under `test/` cover the new behaviour and `npm test` runs them too; no dependency is added to `package.json`.
Source: request; existing: CONTRIBUTING.md ("No dependencies", "Tests")
