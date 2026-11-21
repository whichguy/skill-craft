## Use cases

### U-1: A requester or agent opens a ticket and sees when a response is due
Flow: With due times on (`DUE_TIMES=on`), they `POST /tickets` with a priority (say `high`) at 2025-09-01T08:15:00.000Z. The 201 answer shows `due` as `2025-09-02T08:15:00.000Z` (24 hours after `created`). Reading the ticket later with `GET /tickets/:id`, or finding it in `GET /tickets`, shows the same `due`, however much time has passed.
Source: request

### U-2: An agent lists the tickets that have missed their response time
Flow: With due times on, they call `GET /tickets?overdue=true`. They get the usual `{ items, next }` page holding only the tickets that are `open` or `in_progress` and whose `due` has passed. A resolved or closed ticket past its due time is not listed, and neither is an open ticket not yet due.
Source: request

### U-3: The help desk lead changes a response time without a release
Flow: They set a different number of hours for a priority in the service's configuration and restart the service. Tickets created afterwards get `created` plus the new hours as their `due`. Tickets that already exist keep the `due` they have.
Source: request

### U-4: An operator introduces due times to production without exposing anything half-done
Flow: They deploy the new release with `DUE_TIMES` not `on` and the production data file in place. The service answers exactly as 1.4.0 does. The data file now holds a due time for every ticket, including the ones that existed before. Once they have checked the file, they set `DUE_TIMES=on` and restart, and the API shows `due` and answers `overdue=true`.
Source: request

### U-5: An operator rolls back to 1.4.0
Flow: Something misbehaves, so they stop the new release and start 1.4.0 on the data file the new release wrote. It starts and shows every ticket. The operator does not edit or convert the file.
Source: request

### U-6: An operator or integrator who does nothing different sees nothing different
Flow: The command line, the weekly report, the audit log, notifications, pagination, validation and every error answer behave as before. The existing tests still pass unchanged.
Source: request

## Clauses

### C-1: Every ticket has a due time equal to its creation time plus the response time for its priority, with the defaults 4, 24, 72 and 168 hours
Observable: With the hours not configured, a ticket created at time T has a due time of T plus 4 hours when `urgent`, 24 when `high`, 72 when `normal` (also the priority when none is given) and 168 when `low`. For example, a `normal` ticket created at `2025-09-01T08:00:00.000Z` is due at `2025-09-04T08:00:00.000Z`. The due time is counted in elapsed hours (hours × 3,600,000 ms), and `created` is the instant to which the hours are added.
Source: request
### C-2: The ticket shows its due time as `due`, an ISO 8601 UTC time in the format of `created`
Observable: With due times on, the ticket object in `POST /tickets` (201), `GET /tickets/:id`, `PATCH /tickets/:id`, `POST /tickets/:id/transition`, and every item of `GET /tickets` has a `due` string such as `2025-09-02T08:15:00.000Z`, in the same format as `created` (docs/api.md, "Times"). Its other fields keep their meaning and values.
Source: request; existing: docs/api.md, "Conventions" (times)

### C-3: A ticket's due time is set once and never moves
Observable: After a ticket is created, its `due` stays the same string through a later `PATCH` of its priority, a later change of the configured hours followed by a restart, any status transition including reopening, and a restart of the service on the data file. A `PATCH` that changes the priority from `low` to `urgent` leaves `due` as it was.
Source: request

### C-4: With due times on, `GET /tickets?overdue=true` lists only open and in-progress tickets whose due time has passed
Observable: With `DUE_TIMES=on`, `GET /tickets?overdue=true` answers 200 with `{ items, next }`. Every item has status `open` or `in_progress` and a `due` earlier than the time of the request. Every ticket that meets both conditions is listed (across the pages if there are several). Tickets with status `resolved` or `closed` are never listed, whatever their due time. Items are in id order, as in any listing.
Source: request; existing: docs/api.md ("Tickets come in id order")
Open: The instant at which a ticket is exactly due (`due` equal to the current time). The loosest reading is that it is not yet overdue; the requester decides if "has passed" includes the exact instant. A check can be made at least one millisecond either side of `due`.

### C-5: `overdue=true` combines with the other listing parameters
Observable: With due times on, `?overdue=true&status=open` lists only open tickets that are overdue; `?overdue=true&status=resolved` lists nothing. `?overdue=true&priority=urgent` lists only urgent tickets that are overdue. `limit` and `cursor` page through the overdue tickets: following `next` with the same filters reaches every overdue ticket once and none twice.
Source: implied: docs/api.md, "Filters combine: a ticket is listed only when it matches every filter given"
Open: The existing listing code combines `status` and `priority` with "either matches" rather than "both match", which is not what docs/api.md says. Whether to fix that is the requester's decision. This clause asks only that `overdue` is required in addition to whatever else is given, and that a ticket which is not overdue is never listed under `overdue=true`.

### C-6: `overdue` values other than `true`
Observable: The request does not say what `overdue=false`, `overdue=` or `overdue=yes` return.
Source: choice: only `overdue=true` is required to filter; no other value is specified.
Open: Whether other values are refused as `invalid` (400), as a bad `status` is, or ignored, and whether `overdue=false` lists the tickets that are not overdue. The requester decides. A test must not assert either way.

### C-7: The hours for each priority are configuration, not code
Observable: An operator changes the hours of each of the four priorities by configuration only (README.md: "Every setting is an environment variable") and restarting the service. After the restart a ticket created at T has due T plus the configured hours for its priority. Priorities not configured keep their default hours (C-1). The setting is listed in the README's configuration table.
Source: request; existing: README.md, "Configuration"
Open: The names of the settings and whether a restart is the way a change takes effect. The loosest reading is one environment variable per priority, read at start. The requester decides the names; a check must find them in the README configuration table, not assume them.

### C-8: A value for the hours that the service cannot use stops it at start
Observable: A non-numeric value for one of the hours settings (such as `abc`) makes the service refuse to start with a message naming that variable and exit status 2, as `PORT=http` does today.
Source: existing: README.md ("A value the service cannot use stops it at start with a message naming the variable")
Open: Whether zero, a fraction or a negative number is usable. Only a value that is not a number is required to be refused.

### C-9: Existing tickets in the data file get due times from their own creation time and priority
Observable: Start the new release on a data file written by 1.4.0, whose tickets have no due time. Each ticket then has a due time equal to its own `created` plus the hours for its own priority (C-1), not the time of the start. For example, an `urgent` ticket created at `2025-08-01T10:00:00.000Z` is due at `2025-08-01T14:00:00.000Z`. This holds for tickets in every status.
Source: request
Open: The hours used are those configured when the file is first started with the new release. Whether tickets that already had a due time and lost it (C-12) are given one by the same rule is the same question; this clause assumes yes.

### C-10: Existing tickets keep their due time from then on
Observable: Once a ticket has a due time (from C-9), restarts, changes of the configured hours and `PATCH` of the priority do not change it. The due time written to the data file the first time is the one shown after any later start.
Source: request

### C-11: The data file holds every ticket's due time before due times are switched on
Observable: Start the new release once with `DUE_TIMES` unset (or any value other than `on`) on a data file that has tickets without due times, and stop it. The data file then holds a due time for every ticket, existing ones and any created while it ran, so that `DUE_TIMES=on` on the next start shows them without further preparation. The file is a JSON document whose `tickets` entries carry the due time (what key: C-13).
Source: request ("Due times are switched on in production only once the data file holds them")
Open: When the file is written. The loosest reading is that the file holds them after the service has started and stopped normally; a deploy that must be checked before switching on relies on this. The requester decides if an operator has to run a separate step instead.

### C-12: After a rollback and a new upgrade, tickets are not left without due times
Observable: A data file that 1.4.0 has written after the new release wrote it (so the file may hold tickets without `due`, such as tickets 1.4.0 created) is started on the new release. Every ticket then has a due time under C-9, and tickets that still had a `due` keep the one they had.
Source: implied: "operators must be able to go back to the current release" and "keep them from then on"
Open: 1.4.0 drops fields it does not know when it saves, so tickets that existed before the rollback may lose `due` in the file it writes. What to do with these is decided by the requester. The only requirement here is that no ticket is left without a due time and that a ticket whose `due` survived keeps it.

### C-13: The data file stays one that 1.4.0 starts on and shows every ticket from
Observable: A data file written by the new release (with `DUE_TIMES` unset, and with it `on`, with and without tickets) is accepted by 1.4.0 (release at commit `ab7b9ee`, package version 1.4.0): it starts and `GET /tickets` lists every ticket with its id, title, priority, requester, status, `created` and `updated` as the new release had them. The file's `version` is still `1`, and it has no change that 1.4.0's checks (docs/decisions/0008-json-data-file.md and `src/persistence.js`) refuse. The audit log and the outbox in it still load.
Source: request; existing: docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote"), src/persistence.js
Open: What the key for the due time is called in the file. Any key that 1.4.0 loads without refusing is acceptable.

### C-14: The new release still loads files written by 1.4.0
Observable: A data file written by 1.4.0 (version 1, no due times) starts on the new release, which shows every ticket, audit entry and outbox notification it held. Starting with a file with no tickets, and with no file at all, works as before.
Source: existing: docs/decisions/0008-json-data-file.md ("must keep loading the files the previous version wrote"); implied: U-4

### C-15: With `DUE_TIMES` not `on`, the API answers exactly as 1.4.0 does
Observable: With `DUE_TIMES` unset, empty, or any value other than `on`, a ticket in any response has exactly the fields it has in 1.4.0 (`id`, `title`, `priority`, `requester`, `status`, `created`, `updated`) and no `due`. `GET /tickets?overdue=true` is answered as if the parameter were not given (all tickets, as 1.4.0 does for an unknown parameter). Status codes, bodies, pagination and errors are the same as 1.4.0's for the same requests.
Source: request
Open: Whether `on` is case-sensitive (`ON`, `On`). The loosest reading is that exactly `on` switches due times on and the request's wording is `on`; the requester decides about other spellings. A check should use `on` and unset only.

### C-16: Switching on is a restart with `DUE_TIMES=on`, and switching off the same
Observable: Starting the same data file with `DUE_TIMES=on` shows `due` and answers `overdue=true`; starting it again with the variable unset hides `due` and ignores `overdue` again. The `due` values shown are the ones in the data file in both cases.
Source: implied: U-4 and C-15 (the setting is read from the environment like the others, README.md, "Configuration")

### C-17: Creating a ticket with due times off still records its due time
Observable: With `DUE_TIMES` unset, a ticket created through `POST /tickets` is answered without `due` (C-15), but a data file written afterwards holds its due time from the time of creation and its priority, so that switching on later shows it.
Source: implied: "Due times are switched on in production only once the data file holds them"

### C-18: Giving every ticket a due time is not a change to the ticket
Observable: Starting the new release on a file with tickets without due times does not change any ticket's `updated`, `status`, `priority` or `title`, adds no audit entry (`GET /tickets/:id/audit` returns the same entries as before the start) and enqueues no notification (`GET /admin/outbox` is unchanged).
Source: implied: docs/api.md ("`updated` ... when it last changed"), CONTRIBUTING.md ("A change that changes nothing is not a change: no audit entry, no notification")

### C-19: Creating a ticket does not change its audit entry or notification because of due times
Observable: `GET /tickets/:id/audit` for a new ticket holds one `ticket.created` entry whose `changes` list is the same as in 1.4.0, and one notification is enqueued as in 1.4.0, whether `DUE_TIMES` is `on` or not.
Source: choice: the request asks for neither; keeping 1.4.0's audit and notification output is what "everything the service already does keeps working" requires.
Open: Whether `due` should be recorded in the audit log is for the requester to decide; it is not required.

### C-20: Everything else the service does keeps working, and the existing tests pass unchanged
Observable: `npm test` passes with every file in `test/` as it is now, together with the new tests. Creating, reading, listing with `status`, `priority`, `limit` and `cursor`, `PATCH`, transitions, the audit endpoint, the outbox endpoint, `/health`, the validation errors in the envelope, and the worker's notifications answer as in 1.4.0.
Source: request

### C-21: The command line and the weekly report keep working on a data file that holds due times
Observable: `node bin/tickets.js list`, `list --raw` and `show` on a data file that holds due times print what they print for 1.4.0: `list --raw` keeps its columns (id, status, priority, title) in their positions, so `scripts/weekly-report.js` gives the same counts. They never write the file.
Source: existing: README.md ("Command line"), src/format.js
Open: Whether `show` or `list` should print the due time, and whether that depends on `DUE_TIMES`. The request does not ask for it, so it is not required; the requester decides.

### C-22: The new behaviour is tested and documented
Observable: `npm test` runs new `node:test` files under `test/` that cover the due time, the `overdue` listing, the configurable hours, the data file (including a file that holds no due times) and the `DUE_TIMES` switch. They need no network and no dependency, use a free port, and leave no process running. The README's configuration table lists the new settings, and `docs/api.md` describes `due` and `overdue`.
Source: request ("Add node:test tests under test/ for the new behaviour"); implied: CONTRIBUTING.md ("a change of behaviour comes with a test of it", release and changelog notes)
