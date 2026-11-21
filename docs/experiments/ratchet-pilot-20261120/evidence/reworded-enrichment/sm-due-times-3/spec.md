## Use cases

### U-1: A help-desk agent sees by when each ticket must be answered
Flow: The agent creates or opens a ticket (`POST /tickets`, `GET /tickets/:id`, `GET /tickets`) and sees `due`, an ISO 8601 UTC time (like `created`): the creation time plus 4 h (urgent), 24 h (high), 72 h (normal) or 168 h (low).
Source: request

### U-2: A help-desk agent lists what is late
Flow: The agent calls `GET /tickets?overdue=true` and sees only tickets that are `open` or `in_progress` and whose `due` has passed; resolved and closed tickets never appear.
Source: request

### U-3: The help-desk lead changes the response times
Flow: The lead changes the hours for a priority in the service's settings and restarts the service, with no code change. Tickets created afterwards get the new hours; every existing ticket keeps its `due`.
Source: request

### U-4: An operator introduces due times into production safely
Flow: The operator deploys the new release with `DUE_TIMES` unset. The service answers exactly as 1.4.0 does, while the data file gains `due` for every ticket. When the file holds them, the operator sets `DUE_TIMES=on` and restarts; tickets now show `due` and `overdue=true` works.
Source: request

### U-5: An operator goes back to 1.4.0
Flow: The new release has written the data file. The operator starts 1.4.0 on that same file; it starts and shows every ticket.
Source: request

### U-6: Existing clients, scripts and operators carry on
Flow: Clients, the command line, the weekly report and the existing tests work as before.
Source: request

## Clauses

### C-1: With `DUE_TIMES=on`, every ticket shows `due`
Observable: With `DUE_TIMES=on`, every ticket object the API returns (create, get, list items, patch, transition) has a `due` field holding an ISO 8601 UTC string with milliseconds, like `created`.
Source: request

### C-2: A new ticket's due time is its creation time plus the hours for its priority
Observable: A ticket created at time T shows `due` = T + 4 h if urgent, + 24 h if high, + 72 h if normal (the default priority), + 168 h if low. For example `created` `2025-09-01T08:15:00.000Z`, priority high: `due` `2025-09-02T08:15:00.000Z`.
Source: request

### C-3: The hours for each priority can be changed without a code change
Observable: The operator sets the hours per priority through configuration (defaults 4, 24, 72, 168), restarts, and tickets created afterwards get `created` plus the configured hours. A value the service cannot use as hours stops it at start with a message naming the setting (the service's existing rule for settings).
Source: request; implied: README says every setting is an environment variable and a bad value stops the start naming it
Open: the mechanism and names of the settings (e.g. one environment variable per priority), whether fractional hours are allowed, and what range is valid. The requester decides; a build chooses and reports it.

### C-4: A ticket's due time never moves once set
Observable: After a ticket is created, changing its priority (`PATCH`), moving it through the lifecycle, changing the configured hours and restarting the service all leave its `due` unchanged.
Source: request

### C-5: `overdue=true` lists only open and in-progress tickets past their due time
Observable: With `DUE_TIMES=on`, `GET /tickets?overdue=true` lists exactly the tickets whose status is `open` or `in_progress` and whose `due` is earlier than the current time; a resolved or closed ticket past its due time, and any ticket not yet due, is not listed. Order and paging are those of `GET /tickets` (id order, `limit`, `next`/`cursor`).
Source: request
Open: a ticket whose `due` equals the current instant exactly (a build may treat it either way; tests do not probe it).

### C-6: `overdue=true` combines with the other list filters as the API documents
Observable: `GET /tickets?overdue=true&priority=urgent` lists only overdue tickets that are urgent (docs/api.md: "a ticket is listed only when it matches every filter given").
Source: implied: docs/api.md, "List tickets"; a build must not let the new filter widen the result
Open: none on the rule; note that `matchesFilters` in src/tickets/query.js currently lets a ticket pass when it matches any one filter, which contradicts the document. Whether to fix that for the existing `status` and `priority` filters is the requester's to decide; the rule above is required for the overdue combination only.

### C-7: An `overdue` value other than `true`
Observable: With `DUE_TIMES=on`, `overdue=true` is the documented way to ask. Another value is handled by the service's existing rule for query values it cannot use (400 `invalid` in the error envelope) or listed as if absent; it is never a 500.
Source: choice: the request defines only `overdue=true`
Open: whether `overdue=false` means "only tickets not overdue" or is refused; the requester decides.

### C-8: The data file holds `due` for every ticket
Observable: With `DATA_FILE` set, after the new release starts, every ticket record in the file has a `due` field, whatever `DUE_TIMES` is, including right after start before any request. A ticket created while `DUE_TIMES` is off also has its `due` in the file.
Source: request ("only once the data file holds them")

### C-9: Existing tickets get due times from their own creation time and priority
Observable: A ticket in the file without `due`, created at C with priority P, gets `due` = C + the hours for P, in the file, at the first start of the new release. Its `updated`, its audit entries and the outbox are unchanged by this.
Source: request; choice: the audit log and `updated` are not touched, since nothing about the ticket changed for the requester

### C-10: Due times already in the file are kept on later starts
Observable: Restarting the service, with the same or different hours, leaves every `due` already in the file unchanged.
Source: request ("keep them from then on")

### C-11: With `DUE_TIMES` not `on`, the service answers exactly as today
Observable: With `DUE_TIMES` unset, empty or `off`, no ticket object has a `due` field, and `GET /tickets?overdue=true` answers exactly as it does in 1.4.0 (the parameter has no effect). All other responses, the audit log, the outbox and the command line output are byte-for-byte what 1.4.0 gives.
Source: request
Open: the handling of a `DUE_TIMES` value that is neither `on`, `off` nor empty: refused at start naming the variable, or treated as off. The requester decides; only `on` turns the feature on.

### C-12: A data file written by the new release stays readable by 1.4.0
Observable: Starting 1.4.0 on a data file the new release wrote (with `due` in its tickets) succeeds and `GET /tickets` shows every ticket with its id, title, priority, requester, status, created and updated as before. The file keeps `"version": 1` and every field 1.4.0 reads, unchanged in form.
Source: request; existing: docs/decisions/0008-json-data-file.md ("must keep loading the files the previous version wrote"); 1.4.0 refuses any version other than 1

### C-13: The new release still loads a file 1.4.0 wrote
Observable: A version 1 file with no `due` fields starts the new release (C-9), and so does one where only some tickets have `due`; tickets created by 1.4.0 after a rollback get `due` at the next start.
Source: implied: U-5 then moving forward again; docs/decisions/0008
Open: 1.4.0 rewrites the file without `due`, so after a rollback and a second upgrade the due times are computed again from the hours then in force, and may differ from the earlier ones. Whether that is acceptable is the requester's to decide.

### C-14: A malformed `due` in the file is refused
Observable: A ticket record whose `due` is present but not a time stops the service at start with a message naming the record and field, like other bad records (e.g. `tickets[3].due is not a time`).
Source: existing: docs/operations.md, "The data file"; choice: same rule as `created`

### C-15: Everything already working keeps working
Observable: The existing tests pass unchanged. The ticket fields, the list order and paging, the audit log's entries (a created ticket's audit `changes` still list only title, priority, requester and status), the outbox, `list --raw` columns (id, status, priority, title) and the weekly report are as in 1.4.0 with `DUE_TIMES` off, and unchanged in these respects with it on.
Source: request

### C-16: New tests cover the new behaviour
Observable: `npm test` runs node:test tests under `test/` for C-1 to C-14 as well as the existing ones, and passes.
Source: request
