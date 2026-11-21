## Use cases

### U-1: An agent or lead assigns a ticket to an agent, to say who works it
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` on an open or in-progress ticket. Gets 200 and the ticket with `"assignee": "dana"`. Later `GET /tickets/T-0001` shows the same.
Source: request

### U-2: An agent or lead unassigns a ticket, to hand it back to the pool
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. Gets 200 and the ticket with `"assignee": null`.
Source: request

### U-3: An assigned agent learns a ticket is theirs
Flow: After the assignment, a notification addressed to `dana` about T-0001 is delivered through the existing notification path (outbox, then worker, then notifier), and shows in `GET /admin/outbox`.
Source: request

### U-4: An agent finds their own work, or the unassigned work
Flow: `GET /tickets?assignee=dana` lists only dana's tickets. `GET /tickets?assignee=` lists only the unassigned ones. `GET /tickets?status=open&assignee=dana` lists only open tickets assigned to dana.
Source: request

### U-5: An operator sees who has each ticket on the command line
Flow: Runs `node bin/tickets.js --data FILE list` and sees each ticket's assignee beside it (empty or a marker for unassigned).
Source: request

### U-6: An existing client or operator keeps working unchanged
Flow: Creating, listing, changing, transitioning, auditing, notifying, persisting, the weekly report and the existing tests behave as before.
Source: request

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: Answers 200 with the whole ticket, whose `assignee` is the given name. `GET /tickets/:id` afterwards shows the same `assignee`. `updated` becomes the time of the change.
Source: request
Open: whether the name is stored exactly as sent or trimmed of surrounding whitespace, as the existing text fields (title, requester) are. Settled by the requester. Tests use names without surrounding whitespace.

### C-2: `PUT /tickets/:id/assignee` with `{"assignee": null}` unassigns an open or in-progress ticket
Observable: Answers 200 with the ticket, whose `assignee` is `null`. `GET /tickets/:id` afterwards shows `null`. Unassigning a ticket that has no assignee changes nothing (200, `updated` unchanged, no audit entry).
Source: request (the no-op follows from the existing rule that a change that changes nothing is not a change, CONTRIBUTING.md)

### C-3: An agent is a non-empty name; any other `assignee` value is refused
Observable: `""`, a number, a boolean, an array, an object, or a body with no `assignee` field is answered 400 `invalid` in the error envelope, and the ticket is unchanged. A body that is not a JSON object is 400 `invalid` as it already is elsewhere. An unknown extra field in the body is 400 `invalid` (docs/api.md, Conventions).
Source: request (non-empty name); existing: docs/api.md (unknown fields, envelope)
Open: whether a whitespace-only name, a name with control characters (tab, line break), or a name longer than some maximum is refused. The existing text fields refuse whitespace-only, control characters and over-length (requester: 64). The requester decides which apply to an agent name and what the maximum is. A test checks only `""`, non-string values and a missing field.

### C-4: Only open and in-progress tickets can be assigned or unassigned
Observable: Assigning or unassigning a `resolved` or `closed` ticket is answered 409 `conflict` in the error envelope, and the ticket's `assignee` and `updated` are unchanged. This holds when the request would change nothing (the same agent, or `null` on an unassigned ticket).
Source: request
Open: where the status check falls against body validation when both fail (a closed ticket with an invalid body: 400 or 409). Settled by the requester. Tests do not combine them.

### C-5: An unknown ticket id on `PUT /tickets/:id/assignee` is 404 `not_found`
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for a ticket that does not exist, is 404 with code `not_found`.
Source: existing: docs/api.md (not_found for no such ticket)

### C-6: Assigning a ticket to the agent it already has changes nothing
Observable: The answer is 200 with the ticket unchanged. `updated` stays, the audit log gains no entry, and no notification is enqueued (`GET /admin/outbox` lists no new event).
Source: request; existing: CONTRIBUTING.md (a change that changes nothing is not a change)

### C-7: Every ticket shows `assignee`, `null` when unassigned
Observable: A new ticket from `POST /tickets` shows `"assignee": null`. `GET /tickets/:id` and every item of `GET /tickets` carry an `assignee` field. A ticket that was created before this change, loaded from an existing data file, shows `"assignee": null`; such a data file still loads.
Source: request; implied: a ticket from an existing data file must still load (existing: README.md, DATA_FILE)

### C-8: An assignment survives a restart when a data file is configured
Observable: With `DATA_FILE` set, assign a ticket, stop and start the service on the same file: `GET /tickets/:id` shows the same `assignee`. An unassigned ticket still shows `null`.
Source: implied: the README says the service keeps its state across restarts with the data file

### C-9: An assignment or unassignment that changes the assignee is audited
Observable: `GET /tickets/:id/audit` gains one entry for it, with `changes` holding `assignee` with its value before and after (`null` when unassigned), the actor from `X-Actor` or `system`, and the time. A request that changes nothing adds none.
Source: implied: every change to a ticket is on record (README.md; existing: docs/decisions/0007-append-only-audit-log.md)
Open: the `action` name of the entry (for example `ticket.assigned`). Free for the builder; tests do not check it.

### C-10: The agent a ticket is assigned to is notified that it was assigned to them
Observable: After an assignment that changes the assignee to `dana`, the outbox holds a notification addressed to `dana` for that ticket (`to` is `dana`, `ticket` is the id) and the worker delivers it through the notifier. The text names the ticket. The notification is enqueued with the change, not sent inside the request, and the request does not fail if delivery would.
Source: request; existing: docs/decisions/0006-notification-outbox.md
Open: whether an agent name that is not an email address can be delivered by the mail relay; `to` is the name as given. Settled by the requester or the relay's owner.

### C-11: Reassigning a ticket from one agent to another notifies the new agent
Observable: With T-0001 assigned to `dana`, assigning it to `omar` enqueues a notification to `omar`. This holds even if an earlier assignment notification for the same ticket is still pending: the new agent's notification is not dropped. Two different agents are each notified for their own assignment.
Source: implied: "the agent a ticket is assigned to is notified"; the outbox drops a second event with the same key while the first is pending (existing: docs/decisions/0006-notification-outbox.md)

### C-12: Unassigning notifies no one
Observable: After `{"assignee": null}` on an assigned ticket, no notification is enqueued, and the previous agent is not notified.
Source: choice: the request only says the agent assigned to is notified that it was assigned
Open: whether the previous agent, or the requester, should hear of an unassignment or reassignment. Settled by the requester. Adding such a notification would not break C-12's absence only if the requester decides it.

### C-13: `GET /tickets?assignee=<agent>` lists only that agent's tickets
Observable: Only tickets whose `assignee` equals `<agent>` appear. The match is exact on the name as stored. Tickets appear in id order and the `limit` and `cursor` paging work as before with this filter.
Source: request
Open: whether the match ignores letter case. Tests use one case.

### C-14: `GET /tickets?assignee=` (empty value) lists only the unassigned tickets
Observable: Only tickets whose `assignee` is `null` appear, including when the request has the empty `assignee=` and no other filter. A ticket with an assignee does not appear.
Source: request

### C-15: A ticket must match every filter given
Observable: With `status=open&assignee=dana`, only tickets that are both open and assigned to dana are listed. The same holds for any two or three of `status`, `priority` and `assignee`: a ticket that matches only one of them is not listed. With no filter, every ticket is listed.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given"). The existing `matchesFilters` in `src/tickets/query.js` lists a ticket that matches any one filter, which contradicts this; the contradiction is fixed here, and the existing tests must still pass as they are.

### C-16: Filters accepted before still behave as before
Observable: `status` and `priority` filters, their `invalid` errors for a value that is not a status or a priority, `limit` (1 to 100, default 20) and `cursor` behave as in docs/api.md. An `assignee` filter value is never `invalid`: any text is a name, and a name nobody has gives an empty `items` and `next` null.
Source: existing: docs/api.md; request (assignee filter)

### C-17: The command-line `list` shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` prints a table with an assignee column showing the name for an assigned ticket, and a visible placeholder (for example `-`, not the text `null`) for an unassigned one. `show ID` also shows the assignee. `list` still reads without writing the data file.
Source: request (listing); choice: `show` is added as the same information on the single-ticket view
Open: the column's title, position and the placeholder text. Tests look for the agent's name on the ticket's row, and that an unassigned row does not contain `null`.

### C-18: The command-line `list` accepts an `assignee` filter
Observable: `list --assignee dana` shows only dana's tickets; `list --assignee ""` shows only the unassigned ones; it combines with `--status` and `--priority` by C-15.
Source: choice: the request says the command-line listing shows the assignee, not that it filters
Open: whether the command line gets this filter at all. Settled by the requester; the clause may be dropped.

### C-19: `list --raw` keeps the positions of its existing columns
Observable: Each raw line still has id, status, priority and title in columns 1 to 4 separated by tabs, so `scripts/weekly-report.js` and `npm run report:weekly` give the same counts as before.
Source: existing: README.md ("Command line": the columns must keep their positions)
Open: whether `--raw` also carries the assignee, and if so it must be placed after the title (column 5) so that positions 1 to 4 stay. Tests only check columns 1 to 4.

### C-20: Existing behaviour and tests are unchanged
Observable: `npm test` passes the existing test files unmodified, together with the new ones under `test/`. `PATCH /tickets/:id` still takes only `title` and `priority` (an `assignee` field there is 400 for an unknown field). A ticket's status transitions keep its assignee and send the same notifications as before (the requester is told on received and on resolved).
Source: request; existing: docs/api.md

### C-21: The documentation names the new behaviour
Observable: `docs/api.md` describes the endpoint, the `assignee` field of the ticket, the `assignee` list filter and the new audit and notification behaviour; `README.md` describes the command-line change; `CHANGELOG.md` has an entry.
Source: existing: CONTRIBUTING.md ("a change of behaviour comes with a test"; releases list changes in CHANGELOG.md)
