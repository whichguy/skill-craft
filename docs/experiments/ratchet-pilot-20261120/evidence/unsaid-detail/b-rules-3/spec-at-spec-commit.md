## Use cases

### U-1: An agent or dispatcher assigns an active ticket to an agent, to get it worked by that person
Flow: They send `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. They get 200 and the ticket with `"assignee": "dana"`. Dana is notified that the ticket was assigned to them. The change is in the ticket's audit history.
Source: request

### U-2: A dispatcher unassigns a ticket, to put it back in the pool
Flow: They send `PUT /tickets/T-0042/assignee` with `{"assignee": null}` for an open or in-progress ticket. They get 200 and the ticket with `"assignee": null`.
Source: request

### U-3: A dispatcher repeats an assignment (a retry, a double click), to no ill effect
Flow: They send the same assignee a ticket already has. They get 200 and the unchanged ticket; nobody is notified again and the history gains no entry.
Source: request

### U-4: A caller tries to assign a ticket that is resolved or closed, or sends a bad request, and is told why
Flow: They get a 409 `conflict` for a resolved or closed ticket, a 400 `invalid` for a malformed body, a 404 `not_found` for an unknown ticket, all in the usual error envelope.
Source: implied: the request limits assignment to open and in-progress tickets; docs/api.md and CONTRIBUTING.md fix the error rules

### U-5: A dispatcher or agent lists the tickets of one agent, or the unassigned ones
Flow: They send `GET /tickets?assignee=dana` and see only Dana's tickets; `GET /tickets?assignee=` shows the unassigned tickets; with `status=open` too, only tickets matching both.
Source: request

### U-6: An operator reads the assignee on the command line
Flow: `node bin/tickets.js list` shows each ticket's assignee in the table; a ticket without one shows no name.
Source: request

### U-7: An operator or the support leads keep using what exists
Flow: Existing API calls, the existing data files (which hold no assignee), `list --raw` and `npm run report:weekly` behave as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: Assigning an open or in-progress ticket sets its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": "dana"}` on an open or in-progress ticket answers 200 with the ticket, whose `assignee` is `"dana"`; a later `GET /tickets/:id` shows `"dana"`.
Source: request

### C-2: Unassigning an open or in-progress ticket clears its assignee
Observable: `{"assignee": null}` on an open or in-progress ticket that has an assignee answers 200 with the ticket, whose `assignee` is `null`; a later `GET` shows `null`.
Source: request

### C-3: An agent is a non-empty name; anything else is invalid
Observable: A body whose `assignee` is an empty string, a string of only whitespace, or a value that is neither a string nor null (number, boolean, object, array) answers 400 `invalid` and leaves the ticket unchanged.
Source: request ("an agent is a non-empty name"); existing: src/tickets/validate.js (text fields refuse blank values)
Open: whether a name is trimmed, and its maximum length or forbidden characters. The request gives only "non-empty". The existing text fields trim, cap at 64 or 200 characters and refuse control characters; the requester decides if the same applies. Tests should use ordinary short names such as `dana`.

### C-4: The body must carry `assignee` and nothing else
Observable: A body that is not a JSON object, lacks `assignee`, or has any other field answers 400 `invalid` and leaves the ticket unchanged. (`{"assignee": null}` has the field, so it is valid.)
Source: existing: docs/api.md (unknown fields refused; body not an object is `invalid`); implied: the request defines the body as exactly `{"assignee": ...}`

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: `PUT .../assignee` with a name or with null on a resolved or closed ticket answers 409 `conflict` in the error envelope and leaves the assignee as it was.
Source: request; existing: docs/api.md and CONTRIBUTING.md ("the ticket's state does not allow this" is 409)
Open: whether repeating the assignee a resolved or closed ticket already has answers 409 or 200 unchanged. The request says only open and in-progress tickets can be assigned. Tests should not check this case.

### C-6: An unknown ticket is not found
Observable: `PUT /tickets/T-9999/assignee` for a ticket that does not exist answers 404 `not_found`.
Source: existing: docs/api.md (errors)

### C-7: Assigning to the agent a ticket already has changes nothing
Observable: The same `{"assignee": "dana"}` sent again on a ticket assigned to `dana` answers 200 with the ticket; `updated` is unchanged, the ticket's audit history gains no entry, and no notification is enqueued. The same holds for `{"assignee": null}` on an unassigned open or in-progress ticket.
Source: request; existing: CONTRIBUTING.md and docs/api.md (a change that changes nothing leaves no audit entry and no notification, `updated` stays)

### C-8: A change of assignee updates the ticket and is audited
Observable: When the assignee changes, `updated` becomes the time of the change and `GET /tickets/:id/audit` gains one entry whose `changes` holds `assignee` with its `from` (null or the previous name) and `to` (the new name or null), and whose actor is the `X-Actor` header or `system`.
Source: implied: every change to a ticket is audited with its before and after (docs/api.md, decision 7, CONTRIBUTING.md)
Open: the entry's `action` value is not decided; tests should check `changes` and the actor, not the action name.

### C-9: Every ticket shows its assignee
Observable: Every ticket the API returns (create, get, list items, patch, transition, assignment) has an `assignee` field: `null` for a new ticket and for any ticket never assigned, including tickets loaded from a data file saved before this change.
Source: request

### C-10: The assignee survives a restart
Observable: With `DATA_FILE` set, after the service is stopped and started again on the same file, a ticket assigned to `dana` still shows `"dana"`, and one unassigned shows `null`; `bin/tickets.js` reading that file shows the same.
Source: implied: README.md (the data file keeps the state across restarts); the command line reads the data file

### C-11: An old data file still loads
Observable: A data file whose tickets have no `assignee` field loads without error, and its tickets show `assignee` null.
Source: request ("Everything the service already does keeps working"); existing: src/persistence.js (version 1 files)

### C-12: The agent is notified when a ticket is assigned to them
Observable: After a change that assigns a ticket to `dana`, one notification addressed to `dana` is enqueued (visible in `GET /admin/outbox` with `to` `"dana"` and `ticket` the ticket's id) and, once the worker runs, delivered by the notifier. Its text says the ticket was assigned to them and names the ticket.
Source: request
Open: the notification's `type` and its exact wording are not decided; tests should check `to`, `ticket`, that it is delivered (not dead) and that the text contains the ticket id. How an agent name maps to a delivery address is not decided; the name is used as the address.

### C-13: Reassigning notifies only the new agent; unassigning notifies no one
Observable: Changing a ticket from `dana` to `sam` enqueues a notification to `sam` and none to `dana`; `{"assignee": null}` enqueues no notification.
Source: request ("notified that it was assigned to them"); choice: the request names notification only for the agent assigned to
Open: whether the previous agent or the requester should be told of a reassignment or unassignment; the requester decides. A build may add such notices only if no test of C-12 or C-13 is broken by them.

### C-14: A second assignment is not lost behind a pending notification
Observable: With the worker off, assigning a ticket to `dana` and then to `sam` leaves a notification to `sam` pending alongside the one to `dana`; assigning to `dana`, then `sam`, then `dana` again leaves a pending notification for `dana` that reflects the latest assignment (at least one pending to `dana` and one to `sam`).
Source: implied: C-12 and the outbox's key rule (docs/decisions/0006: a pending event with the same key absorbs a new one, and the existing key is per type and ticket, which would drop the second agent's notice)

### C-15: A failed notification does not fail or undo the assignment
Observable: The assignment answers 200 and persists whether or not the notifier works; delivery happens only in the worker, and with `WORKER_INTERVAL_MS=0` the notification stays pending.
Source: existing: docs/decisions/0006-notification-outbox.md and CONTRIBUTING.md

### C-16: `GET /tickets?assignee=<agent>` keeps that agent's tickets
Observable: Only tickets whose assignee is exactly `<agent>` are listed, in id order and in cursor pages as before; a name nobody holds gives `{"items": [], "next": null}`.
Source: request
Open: whether the match ignores case or surrounding spaces is not decided; tests use the same spelling the ticket was assigned with.

### C-17: `GET /tickets?assignee=` (empty) keeps the unassigned tickets
Observable: With the parameter present and empty, only tickets whose assignee is null are listed. Without the parameter the assignee does not filter.
Source: request

### C-18: A ticket must match every filter given
Observable: With several of `status`, `priority` and `assignee`, a ticket is listed only if it matches all of them: `?status=open&assignee=dana` lists no resolved ticket of Dana's and no open ticket of anyone else; `?status=open&priority=urgent` lists only open urgent tickets.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given"). The current `matchesFilters` in src/tickets/query.js keeps a ticket that matches any one filter; that contradicts the documented rule and must be corrected.

### C-19: The assignee filter pages like the others
Observable: With `limit` and `cursor`, a filtered listing pages through only the matching tickets, `next` null on the last page.
Source: existing: docs/api.md (cursor pages with the same filters)

### C-20: The command-line table shows each ticket's assignee
Observable: `node bin/tickets.js list` prints a column titled `ASSIGNEE` holding the agent's name, and nothing (blank) for an unassigned ticket; the other columns still print and align.
Source: request
Open: the column's position and the text for unassigned (blank or a dash) are not decided; tests find the name on its ticket's row and the title `ASSIGNEE`.

### C-21: `list --raw` keeps its first four columns
Observable: Each `list --raw` line still has id, status, priority, title as tab-separated columns 1 to 4 in that order, so `npm run report:weekly` gives the same counts as before.
Source: existing: README.md and scripts/weekly-report.js (read by position)
Open: whether `--raw` also shows the assignee, as a fifth column after the title, is not decided; the request says "the command-line listing", which may or may not include `--raw`. A build may append it only after the title.

### C-22: Existing behaviour and tests are unchanged
Observable: The existing tests pass unmodified; creating, patching, transitioning, auditing, the outbox, health and the existing filters behave as documented, and a ticket created or changed otherwise gets no assignee change.
Source: request

### C-23: New behaviour has node:test tests that `npm test` runs
Observable: `npm test` runs new test files under `test/` covering the assignment endpoint, the filter, notification and the command-line column, together with the existing ones, with no dependency added.
Source: request

## Rules and edge cases

- Who may be assigned: only open and in-progress tickets (C-1, C-2, C-5). Resolved and closed are refused in both directions; the repeat-on-resolved case is open (C-5).
- Agent value: non-empty string or null; blank, whitespace-only and non-string values refused (C-3). Trimming, maximum length and forbidden characters are not settled by the request (open in C-3). The existing 64-character actor and requester limits are the nearest precedent, not a requirement.
- Body: exactly one field, `assignee`, required (C-4). Check order for a request with several faults is not settled; a test should combine at most one fault.
- Missing ticket: 404 (C-6).
- Repeated and no-op assignments: nothing changes, no audit, no notice, `updated` stays (C-7).
- Reassignment and unassignment: notice only to a new agent (C-13); whether others are told is open.
- Duplicate notices through the outbox key: C-14.
- Persistence and old files: C-10, C-11. Filtering of tickets without an `assignee` field must treat them as unassigned (C-9, C-17).
- Filters: empty value means unassigned, absence means no filter (C-17); AND across filters (C-18); an assignee filter never raises `invalid`, because any string is a possible name (C-16). The filter's case and whitespace handling is not settled (C-16).
- Pagination bounds are unchanged: `limit` 1 to 100, default 20 (C-19).
- Command line: assignee column (C-20); raw columns keep positions (C-21).
- Concurrency: requests are handled one change at a time by the store; two assignments at once end with the later one in effect, each audited. Not separately specified.
- Not settled and not specified: assigning on ticket creation, an `assignee` filter on the command line, an assignee in the PATCH body (still refused as an unknown field, C-22), the assignee shown by `show`, the status of an assigned ticket changing, and any authorization of who may assign.
