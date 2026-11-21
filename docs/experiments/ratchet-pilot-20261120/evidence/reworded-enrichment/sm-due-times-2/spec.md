## Use cases

### U-1: A help-desk agent sees when each ticket is due, to know how long the requester can be made to wait
Flow: With DUE_TIMES `on`, the agent creates or fetches a ticket (`POST /tickets`, `GET /tickets/:id`, `GET /tickets`). Each ticket shows `due`: its creation time plus 4 h (urgent), 24 h (high), 72 h (normal) or 168 h (low). Changing the ticket's priority later leaves `due` as it was.
Source: request

### U-2: A support lead lists the tickets that have missed their due time, to chase them
Flow: With DUE_TIMES `on`, the lead calls `GET /tickets?overdue=true` and sees only open and in-progress tickets whose due time has passed.
Source: request

### U-3: An operator changes the response hours without a deploy, to adjust the promise
Flow: The operator changes the hours of a priority in the service's settings and restarts the service. Tickets created afterwards get the new hours; tickets that already have a due time keep it.
Source: implied: "the help desk must be able to change those hours without a code change"

### U-4: An operator introduces due times in production safely, and can go back
Flow: The operator deploys the new release with DUE_TIMES not `on`. The service answers as 1.4.0 does, while the data file gets a due time on every ticket. When the file holds them, the operator sets DUE_TIMES to `on` and restarts. If the release misbehaves, the operator starts 1.4.0 on the same data file and sees every ticket.
Source: request

## Clauses

### C-1: A ticket's due time is its creation time plus the response hours of its priority
Observable: With DUE_TIMES `on` and the default hours, a ticket created at 2025-09-01T08:00:00.000Z shows `due` 2025-09-01T12:00:00.000Z if urgent, 2025-09-02T08:00:00.000Z if high, 2025-09-04T08:00:00.000Z if normal and 2025-09-08T08:00:00.000Z if low, in the same ISO 8601 UTC form as `created`.
Source: request

### C-2: The default response hours are 4 (urgent), 24 (high), 72 (normal) and 168 (low)
Observable: Without any setting of the hours, the due times are those of C-1.
Source: request

### C-3: The response hours are changed through the service's settings, not in code
Observable: With the settings changed to other hours for a priority and the service restarted, a ticket of that priority created afterwards has `due` = `created` plus those hours; the other priorities keep theirs.
Source: request
Open: the names and format of the settings, and whether a change needs a restart, are not given; the requester or the operations owner decides (README says every setting is an environment variable). A value that is not a usable number of hours stops the service at start with a message naming the setting, as README says for other settings (choice: existing rule for unusable values).

### C-4: A ticket's due time is set once, when the ticket is created, and no later change moves it
Observable: After a ticket's priority is changed with `PATCH /tickets/:id`, after the response hours are changed and the service restarted, and after any status transition, `GET /tickets/:id` shows the same `due` as before.
Source: request

### C-5: Every ticket shows its due time as `due` when DUE_TIMES is `on`
Observable: With DUE_TIMES `on`, the ticket returned by `POST /tickets`, `GET /tickets/:id`, `PATCH /tickets/:id`, `POST /tickets/:id/transition` and each item of `GET /tickets` has a `due` field.
Source: request

### C-6: `GET /tickets?overdue=true` lists only open and in-progress tickets whose due time has passed
Observable: With DUE_TIMES `on`, the listing holds a ticket with status open or in_progress whose `due` is before the current time, and holds no resolved or closed ticket, and no ticket whose `due` is in the future. Paging (`limit`, `cursor`) and id order work as in an unfiltered listing.
Source: request
Open: whether a ticket whose `due` equals the current instant is overdue is not stated; tests must not rely on the exact instant.

### C-7: `overdue` combines with the other filters as the API document says
Observable: With DUE_TIMES `on`, `?overdue=true&priority=urgent` lists only tickets that are overdue and urgent (docs/api.md: "a ticket is listed only when it matches every filter given").
Source: existing: docs/api.md, "List tickets"
Open: src/tickets/query.js currently lists a ticket matching any one filter, contrary to docs/api.md; whether to keep that for existing filters is for the maintainers. Only the combination with `overdue` is stated here.

### C-8: Values of `overdue` other than `true`
Observable: With DUE_TIMES `on`, `overdue=true` is the only value that narrows the listing; a value that is not usable is answered in the error envelope as `invalid` (400), like the other filters (docs/decisions/0004-error-envelope.md).
Source: choice: the request defines only `true`; existing filters reject unusable values.
Open: whether `overdue=false` lists all tickets, only the not-overdue ones, or is `invalid` is not decided; tests must not rely on it.

### C-9: Tickets already in the data file get due times from their own creation time and priority
Observable: Starting the new release on a data file written by 1.4.0, with a ticket created 2025-08-01T10:00:00.000Z and normal priority, results in that ticket's `due` being 2025-08-04T10:00:00.000Z (the default hours) once due times are shown, whatever its status, and it is also so after a later restart with other hours set.
Source: request

### C-10: Due times are written to the data file whether or not DUE_TIMES is `on`
Observable: With DUE_TIMES unset or not `on` and DATA_FILE set, after the service starts and after a ticket is created, every ticket record in the data file holds its due time, so that the file can be checked before the switch is made.
Source: implied: "Due times are switched on in production only once the data file holds them"
Open: the name of the field in the file and when exactly the file is rewritten (at start or at the first change) are not given; the file must hold the due times at the latest after the first start and, for a new ticket, as soon as it is created.

### C-11: Once a ticket has a due time in the data file it keeps it across restarts
Observable: After a restart on the saved file, with the hours changed in between, each ticket's `due` is the same as before the restart.
Source: request

### C-12: Until DUE_TIMES is `on`, the API answers exactly as 1.4.0 does
Observable: With DUE_TIMES unset, empty or any value other than `on`, no ticket in any response has a `due` field; `GET /tickets?overdue=true` answers as 1.4.0 does (the parameter is ignored, and the listing is as without it); every other response is as in 1.4.0, including the audit entries of a ticket.
Source: request

### C-13: DUE_TIMES is read as `on` only for the value `on`
Observable: With DUE_TIMES=`on` the due times show (C-5, C-6); with it unset or empty they do not (C-12).
Source: request
Open: whether other spellings (`ON`, `1`, `true`) count as on is not stated; tests use `on` and unset only.

### C-14: Release 1.4.0 starts on a data file written by the new release and shows every ticket
Observable: Starting 1.4.0 (version 1 of the data file, whose loader keeps only the fields it knows) on a file the new release wrote, with or without DUE_TIMES `on`, starts without error and `GET /tickets` lists every ticket with its id, title, priority, requester, status, created and updated as before.
Source: request
Open: none on the outcome; the format version must stay one that 1.4.0 accepts (it refuses any version other than 1), and the new release's extra fields must not fail 1.4.0's checks (docs/decisions/0008-json-data-file.md).

### C-15: The new release starts on a data file written by 1.4.0 and keeps all of it
Observable: A file without due times loads; every ticket, audit entry and outbox event is listed or reported as before, and the next ticket number and event id are unchanged.
Source: existing: docs/decisions/0008-json-data-file.md ("must keep loading the files the previous version wrote")

### C-16: A due time does not appear in a ticket's audit history
Observable: `GET /tickets/:id/audit` has the same entries, with the same `changes` fields, as 1.4.0 would give for the same actions (creation lists title, priority, requester and status); setting or backfilling a due time adds no entry.
Source: implied: due is set once and never changed by a person; docs/decisions/0007-append-only-audit-log.md

### C-17: The command-line columns and the weekly report are unchanged
Observable: `bin/tickets.js list --raw` prints the tab-separated columns id, status, priority, title in this order, and `scripts/weekly-report.js` gives the same counts, for a file holding due times.
Source: existing: README.md, "Command line"
Open: whether the command line should also show due times is not asked for and is not required.

### C-18: Existing behaviour and tests are unchanged
Observable: Every test in test/ at the start of this work passes unmodified under `npm test`, and the new tests under test/ run with them.
Source: request

### C-19: The new behaviour has node:test tests under test/
Observable: `npm test` runs new test files covering due times, `?overdue=true`, the switch, the backfill and the loading of the file by both releases' rules.
Source: request

### C-20: The documentation tells operators about the new settings and the switch-on and rollback procedure
Observable: README.md or docs/operations.md names the DUE_TIMES setting, the settings of the hours, and the steps of U-4.
Source: implied: U-4 (operators must be able to carry it out); existing: README.md, "Configuration"
