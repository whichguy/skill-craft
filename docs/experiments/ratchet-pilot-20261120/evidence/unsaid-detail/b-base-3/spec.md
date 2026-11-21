## Use cases

### U-1: A help-desk lead assigns a ticket to an agent, to say who works it
Flow: The lead sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. The answer is 200 with the ticket, whose `assignee` is `"dana"`. The agent `dana` is notified that the ticket was assigned to them.
Source: request

### U-2: A lead takes an agent off a ticket
Flow: The lead sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}` for an open or in-progress ticket. The answer is 200 with the ticket, whose `assignee` is `null`.
Source: request

### U-3: A caller repeats an assignment or tries it on a ticket that is finished
Flow: Sending the assignee the ticket already has changes nothing and notifies nobody. Sending any assignment to a resolved or closed ticket is refused in the error envelope.
Source: request

### U-4: An agent finds their own tickets, or the ones nobody has
Flow: `GET /tickets?assignee=dana` lists dana's tickets; `GET /tickets?assignee=` lists the unassigned ones; with `status` or `priority` as well, only tickets matching all the filters given are listed.
Source: request

### U-5: An operator sees who has each ticket on the command line
Flow: `node bin/tickets.js --data FILE list` (and `list --raw`) shows each ticket's assignee next to it.
Source: request

### U-6: Everyone using the service before this change carries on as before
Flow: Existing calls, data files, the weekly report and the existing tests behave as they did.
Source: request

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For a ticket with status `open` or `in_progress`, the answer is 200 with the full ticket whose `assignee` is the agent's name; `GET /tickets/:id` then shows the same `assignee`, and `updated` is the time of the change.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For a ticket with status `open` or `in_progress` that has an assignee, the answer is 200 with the ticket whose `assignee` is `null`; a later `GET /tickets/:id` shows `null`.
Source: request

### C-3: An agent is a non-empty name; anything else is refused as invalid
Observable: A body whose `assignee` is an empty string, a string of only whitespace, a number, a boolean, an object or an array, a body with no `assignee` field, or a body that is not a JSON object is answered 400 with `error.code` `invalid`, and the ticket does not change. Any other field in the body is also 400 (existing rule: unknown fields are refused). A name given with surrounding whitespace is stored trimmed, as the service does for other text fields.
Source: request (non-empty name); existing: docs/api.md (unknown fields refused), src/tickets/validate.js (text fields trimmed)
Open: whether there is an upper length for a name, and whether control characters in it are refused. The service's other text fields are single-line and at most 64 characters (requester); the requester of the service would settle whether agents follow the same rule. A test must not rely on any length bound.

### C-4: Only open and in-progress tickets can be assigned or unassigned
Observable: `PUT /tickets/:id/assignee` for a ticket whose status is `resolved` or `closed`, with an agent name or with `null`, is answered 409 with `error.code` `conflict`; the ticket, its audit log and the outbox are unchanged.
Source: request; existing: CONTRIBUTING.md (a state that does not allow the request is 409)

### C-5: A ticket that does not exist answers 404
Observable: `PUT /tickets/T-9999/assignee` for an id with no ticket is answered 404 `not_found` in the error envelope.
Source: existing: docs/api.md (errors), CONTRIBUTING.md

### C-6: Assigning a ticket to the agent it already has changes nothing
Observable: A repeated `{"assignee": "dana"}` is answered 200 with the ticket unchanged (`updated` as it was); it adds no audit entry and enqueues no notification. The same holds for `{"assignee": null}` on a ticket with no assignee.
Source: request ("changes nothing"); existing: CONTRIBUTING.md (a change that changes nothing is no change: no audit entry, no notification), docs/api.md (`updated` stays)

### C-7: Every ticket shows its `assignee`, `null` when unassigned
Observable: Every ticket in the answers of `POST /tickets` (new ticket: `null`), `GET /tickets/:id`, every item of `GET /tickets`, `PATCH`, `POST .../transition` and the assignee endpoint has an `assignee` field: the agent's name or `null`. The `assignee` of a ticket is kept when it is later resolved or closed.
Source: request ("Every ticket shows its assignee"); implied: the assignee is the record of who worked it

### C-8: The agent a ticket is assigned to is notified that it was assigned to them
Observable: After a successful assignment to `dana` that changed the assignee, one notification to `dana` for that ticket appears in the outbox (`GET /admin/outbox`), and once the worker has run it is delivered (a line in NOTIFY_FILE, or `delivered` in memory) with `to` `dana`, `ticket` the ticket's id, and text that names the ticket id. It is not sent within the request: the request answers even when the worker is off. Unassigning sends no assignment notification. The requester is not sent one by this change.
Source: request
Open: the wording of the subject and body, and the `type` string, are not decided; checks may rely only on the recipient, the ticket id and that it is about an assignment.

### C-9: A reassignment is notified to the new agent even while an earlier assignment's notification is still pending
Observable: With the worker off, assigning a ticket to `dana` and then to `eli` leaves a pending notification to `eli` for that ticket in the outbox (the notification to `dana` need not be removed). Assigning to `dana`, `eli` and `dana` again changes the assignee three times, and the agent named last is notified of the last change.
Source: implied: "the agent a ticket is assigned to is notified"; existing: src/store.js (the outbox's default key `type:ticket` makes a second notification with the same key wait for the first, which would drop the new agent's notice), docs/decisions/0006-notification-outbox.md

### C-10: An assignment change is recorded in the audit log
Observable: After a change of assignee, `GET /tickets/:id/audit` has a new last entry for that ticket, with the request's actor (`X-Actor`, else `system`) and `changes` containing `assignee` with `from` (previous name or `null`) and `to` (new name or `null`). A request that changes nothing adds no entry.
Source: implied: README.md ("every change is on record"), docs/decisions/0007-append-only-audit-log.md
Open: the entry's `action` string is not decided; checks may not depend on it.

### C-11: An assignment is saved with the ticket in the data file
Observable: With `DATA_FILE` set, a service restarted on that file shows the same `assignee` for each ticket, and `bin/tickets.js` reads it from the file. A data file written before this change, whose tickets have no assignee, loads and shows every ticket with `assignee` `null`.
Source: implied: README.md ("keeps its state across restarts"); existing: src/persistence.js (names every field the file keeps)

### C-12: `GET /tickets?assignee=<agent>` lists only that agent's tickets
Observable: Only tickets whose `assignee` equals `<agent>` exactly (same letters, same case) are listed; unassigned tickets are not.
Source: request

### C-13: `GET /tickets?assignee=` (empty) lists only the unassigned tickets
Observable: Only tickets whose `assignee` is `null` are listed. The empty value is not an error.
Source: request

### C-14: A ticket is listed only when it matches every filter given
Observable: `?status=open&assignee=dana` lists only open tickets assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent (today the service lists a ticket matching any one filter, which contradicts docs/api.md and must be corrected); a ticket matching one filter but not another is not listed. Pages (`limit`, `cursor`, `next`) follow the filtered set in id order.
Source: request ("a ticket must match every filter given"); existing: docs/api.md ("Filters combine")

### C-15: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` prints, for each ticket, its assignee (the agent's name) in the row, under a header naming the column; the existing columns are still printed.
Source: request
Open: the column's position and header text, and what an unassigned ticket's cell shows (empty, `-`, `unassigned`); checks may rely only on the assigned name appearing in that ticket's row and no agent name appearing in an unassigned ticket's row.

### C-16: `list --raw` keeps its first four columns and may add the assignee after them
Observable: Each `list --raw` line still has id, status, priority, title as tab-separated columns 1 to 4, in that order, so `scripts/weekly-report.js` gives the same counts as before; the assignee, if shown in raw lines, comes after column 4 and contains no tab.
Source: existing: README.md and src/format.js (raw columns are read by position); request (the listing shows the assignee)
Open: whether the raw listing carries the assignee at all, and what an unassigned ticket shows there; the raw output must not break the report in either case.

### C-17: Everything the service did before keeps working
Observable: The existing tests under `test/` pass unchanged. A `PATCH` with an `assignee` field is still refused as an unknown field (400), and the transition, create, patch, audit and outbox behaviour is as in docs/api.md, apart from the added `assignee` field.
Source: request; existing: docs/api.md

### C-18: New tests cover the new behaviour and run with `npm test`
Observable: Files under `test/` using `node:test` test the assignee behaviour above; `npm test` runs them with the existing tests and they pass.
Source: request
