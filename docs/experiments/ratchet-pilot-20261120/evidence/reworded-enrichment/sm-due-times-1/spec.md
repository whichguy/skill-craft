## Use cases

### U-1: A requester or agent opens a ticket and sees when a response is due
Flow: They `POST /tickets` with a priority (urgent, high, normal or low). The 201 answer, `GET /tickets/:id` and the listing show `due`: the ticket's `created` plus 4 hours (urgent), 24 (high), 72 (normal) or 168 (low), as an ISO 8601 UTC time. Changing the ticket's priority later, or the configured hours, leaves `due` as it was.
Source: request

### U-2: An agent lists the tickets that have missed their due time
Flow: They `GET /tickets?overdue=true`. They get the usual page (`{ items, next }`, id order) holding only open and in-progress tickets whose due time has passed.
Source: request

### U-3: The help desk changes the response times
Flow: The operator changes the hours for one or more priorities in the service's settings and restarts the service. Tickets created afterwards get the new hours; tickets that already have a due time keep it.
Source: request

### U-4: An operator rolls the due times out to production
Flow: The operator starts the new release with `DUE_TIMES` unset. The service gives every ticket in the data file its due time and saves the file. The service answers as 1.4.0 does. Once the file holds the due times, the operator restarts with `DUE_TIMES=on`; `due` and `?overdue=true` now work.
Source: request

### U-5: An operator goes back to 1.4.0
Flow: With the data file the new release wrote, the operator starts release 1.4.0 on it. It starts and lists and shows every ticket.
Source: request

### U-6: Existing users and scripts carry on
Flow: API clients, the command line, the weekly report and the notification relay do what they did before.
Source: request

## Clauses

### C-1: With `DUE_TIMES=on`, every ticket the service answers with carries `due`
Observable: With `DUE_TIMES=on`, the ticket from `POST /tickets` (201), from `GET /tickets/:id`, from `PATCH /tickets/:id` and from `POST /tickets/:id/transition`, and every item of `GET /tickets`, has a `due` field holding an ISO 8601 UTC time string like `2025-09-01T12:00:00.000Z`.
Source: request

### C-2: A new ticket's due time is its creation time plus the hours of its priority
Observable: With default settings, a ticket created at `2025-09-01T08:00:00.000Z` has `due` of `2025-09-01T12:00:00.000Z` if urgent, `2025-09-02T08:00:00.000Z` if high, `2025-09-04T08:00:00.000Z` if normal (also when priority is omitted) and `2025-09-08T08:00:00.000Z` if low. `due` is exactly `created` plus that many hours.
Source: request

### C-3: The hours per priority are settings, with the requested defaults
Observable: The defaults are urgent 4, high 24, normal 72 and low 168 hours. An operator can change the hours of each priority without changing any source file; a ticket created after the service is started with changed hours has `due` of `created` plus the changed hours for its priority, and the other priorities keep their defaults.
Source: request
Open: The names and form of the settings (environment variables are the service's convention, README "Configuration") and whether a change needs a restart are not decided; the requester decides. A build documents its choice (C-17), and tests of C-3 follow that documentation.

### C-4: A setting for the hours that the service cannot use stops it at start
Observable: A response-time setting that is not a whole number of hours of at least 1 stops the service at start, as other unusable settings do (exit code 2, a message on standard error naming the setting); it does not listen.
Source: implied: README "A value the service cannot use … stops it at start with a message naming the variable"
Open: Whether 0 hours is allowed, and an upper bound, are not decided; the requester decides. Tests use only clearly unusable values (text, negative numbers, empty-after-trim is "unset").

### C-5: A ticket's due time never moves when its priority changes
Observable: After `PATCH /tickets/:id` changes the priority, the response, later `GET /tickets/:id` and the listing show the same `due` as before; the same after a restart.
Source: request

### C-6: A ticket's due time never moves when the configured hours change
Observable: A ticket created under some hours, then the service restarted with other hours, shows the same `due` as before the restart, whether created before or after the data file was first written, and in the data file.
Source: request

### C-7: Other changes leave the due time alone
Observable: A change of title, a transition (including reopening a resolved ticket) and a request that changes nothing leave `due` as it was.
Source: implied: "a ticket's due time is set once"

### C-8: The overdue listing holds only open and in-progress tickets whose due time has passed
Observable: With `DUE_TIMES=on` and the clock past a ticket's `due`, `GET /tickets?overdue=true` lists that ticket if its status is `open` or `in_progress`, and does not list it if `resolved` or `closed`. A ticket whose `due` is later than now is not listed. A ticket that was overdue and then is moved to resolved leaves the list.
Source: request
Open: Whether a ticket at exactly its due instant is overdue is not decided; the requester decides. Tests do not probe that instant.

### C-9: The overdue listing is a normal listing
Observable: Its answer is `{ "items": [...], "next": <cursor or null> }`, the items in id order, `limit` and `cursor` page it, and each item is the ticket with `due`.
Source: existing: docs/api.md "List tickets", CONTRIBUTING.md "Listings are cursor pages"

### C-10: Overdue combined with other filters, and other values of `overdue`
Observable: `?overdue=true` together with `status` or `priority` lists no ticket that is not overdue and open or in progress. A value of `overdue` other than `true` is not specified.
Source: choice: the loosest reading that is certainly wanted
Open: The listing's documentation says filters combine so that a ticket must match every filter, but the code lists a ticket matching any one filter (`matchesFilters` in src/tickets/query.js). Which of the two `overdue` joins, and whether `overdue=false` or `overdue=x` is a filter, an error (400 `invalid`) or ignored, is for the requester to decide. Tests do not combine `overdue=true` with another filter beyond the stated guarantee, and do not send other values.

### C-11: The service adds due times to the tickets in the data file when it starts
Observable: Started on a data file whose tickets have no `due`, the service saves the data file with a `due` on every such ticket (any status, any priority), each being the ticket's `created` plus the hours of its priority at that start. Tickets that already have `due` keep it.
Source: request
Open: Whether a ticket whose priority was changed after creation gets the hours of its current priority (the only one the file holds) is the only reading the file allows, and is assumed; the requester decides if the audit log should be used instead.

### C-12: The data file holds the due times whatever `DUE_TIMES` says
Observable: Started with `DUE_TIMES` unset or not `on`, the service still gives the file's tickets their `due` (C-11), and a ticket created then has `due` saved in the data file; the file is readable to check it (`tickets[].due`).
Source: implied: "switched on in production only once the data file holds them"

### C-13: Due times stay once given
Observable: A second start on the file, or any number of starts, changes no `due` in it; after the start the file's `due` values equal what it held before.
Source: request

### C-14: Backfill changes nothing else
Observable: Adding due times adds no audit entry, no notification to the outbox, and leaves every ticket's `updated`, `created`, `status` and every other field as it was; the file's `version` is still 1.
Source: implied: "the tickets … get due times too"; existing: docs/decisions/0008-json-data-file.md

### C-15: Without `DUE_TIMES=on` the service answers exactly as 1.4.0 does
Observable: With `DUE_TIMES` unset, empty or any value other than `on`: no ticket in any answer has a `due` field; `?overdue=true` has no effect (the listing is the same as without it, as 1.4.0 treats an unknown query parameter); all other fields, statuses and error answers are as before.
Source: request
Open: Values of `DUE_TIMES` other than `on`, `off` or unset or empty (a refusal at start, or off) are not decided; the requester decides. Tests use unset and `on`.

### C-16: Release 1.4.0 starts on the data file the new release wrote and shows every ticket
Observable: A data file saved by the new release, with `DUE_TIMES` on or off, after creating, changing and backfilling tickets, is accepted by 1.4.0 (it starts; `GET /tickets` and `bin/tickets.js list` and `show` give every ticket with the fields 1.4.0 knows, unchanged). Data file `version` remains `1`, and no field or shape that 1.4.0 refuses is added.
Source: request
Open: When 1.4.0 rewrites the file it does not keep `due`; the new release later gives those tickets their due time again from their creation time (C-11).

### C-17: The new release is a release of its own and says what changed
Observable: `package.json` has a version other than 1.4.0 (so operators tell the two apart), CHANGELOG.md has a section for it, and README.md's configuration table names `DUE_TIMES` and the response-time settings.
Source: implied: CONTRIBUTING.md "Releases"; existing: README.md "Configuration"

### C-18: Everything the service did keeps working
Observable: The existing tests under test/ pass unmodified. Tickets' ids, ordering, audit entries (their `changes` do not list `due`), notifications, `list --raw` columns (id, status, priority, title) and the weekly report output are as before.
Source: request; existing: README.md "Command line"

### C-19: New tests cover the new behaviour
Observable: `npm test` runs tests under test/ as `node:test` for the clauses above, with the existing tests, and passes. They add no dependency.
Source: request
