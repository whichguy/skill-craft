## Use cases

### U-1: A dispatcher assigns a ticket to an agent, so the agent knows it is theirs
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` for an open ticket; gets 200 and the ticket with `"assignee": "dana"`. The agent `dana` is notified that the ticket was assigned to them.
Source: request

### U-2: A dispatcher takes a ticket off an agent
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}`; gets 200 and the ticket with `"assignee": null`.
Source: request

### U-3: An agent lists their own tickets, or the unassigned ones
Flow: `GET /tickets?assignee=dana` lists only dana's tickets; `GET /tickets?assignee=` lists only unassigned tickets; combined with `status`/`priority`, only tickets matching all of them are listed.
Source: request

### U-4: An operator sees who each ticket is assigned to on the command line
Flow: runs `node bin/tickets.js --data FILE list` (or `list --raw`) and sees each ticket's assignee.
Source: request

### U-5: An operator or support lead keeps using the service as before
Flow: existing endpoints, the data file, the weekly report and the existing tests behave as before; tickets created before this change, or loaded from an older data file, show `"assignee": null`.
Source: implied: "Everything the service already does keeps working"; existing: README.md, docs/api.md

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: for a ticket with status `open` or `in_progress`, the request answers 200 with the ticket, whose `assignee` is the given name; a later `GET /tickets/:id` shows the same value. `updated` moves to the time of the change and the other fields are unchanged.
Source: request
Open: whether surrounding whitespace in the name is trimmed (the existing text fields trim) and the longest accepted name (existing text fields have limits: requester 64, title 200); the requester of the service decides. A test checks only ordinary short names without surrounding whitespace.

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: for a ticket with status `open` or `in_progress` that has an assignee, the request answers 200 with the ticket whose `assignee` is `null`; `GET /tickets/:id` shows `null`.
Source: request

### C-3: An agent is a non-empty name; any other `assignee` value is refused
Observable: an `assignee` that is an empty string (or only whitespace), a number, a boolean, an object or an array, answers 400 with `{"error": {"code": "invalid", ...}}` and the ticket is unchanged. A body without an `assignee` field, or a body that is not a JSON object, is also 400 `invalid`.
Source: request ("an agent is a non-empty name"); existing: docs/api.md (`invalid` for a missing or wrong field)

### C-4: Unknown fields in the assignee body are refused
Observable: `{"assignee": "dana", "extra": 1}` answers 400 `invalid` and the ticket is unchanged.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)")

### C-5: Only open and in-progress tickets can be assigned
Observable: assigning (a name) a ticket whose status is `resolved` or `closed` answers 409 `conflict` in the error envelope; the ticket is unchanged and nobody is notified.
Source: request; existing: CONTRIBUTING.md (a state that does not allow the request is 409)

### C-6: Only open and in-progress tickets can be unassigned
Observable: `{"assignee": null}` for a `resolved` or `closed` ticket answers 409 `conflict`; the ticket keeps the assignee it had.
Source: request

### C-7: A ticket that does not exist answers 404
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for an id no ticket has, answers 404 `not_found` in the error envelope.
Source: existing: docs/api.md (`not_found`)

### C-8: Assigning a ticket to the agent it already has changes nothing
Observable: repeating `PUT` with the same name on an open or in-progress ticket answers 200 with the ticket; `updated` stays as it was, the audit log gets no new entry, and no second notification is made.
Source: request ("changes nothing"); existing: docs/api.md ("a request that changes nothing leaves [updated] as it was"), CONTRIBUTING.md
Open: for an assigned ticket that is `resolved` or `closed`, whether repeating its current assignee answers 409 (as C-5 says, taken here) or 200; a test does not check that case. Likewise unassigning an already-unassigned open ticket is taken as a change-nothing 200, and the requester of the service decides if it should be an error.

### C-9: Every ticket shows its `assignee`, `null` when unassigned
Observable: tickets from `POST /tickets` (201), `GET /tickets/:id`, items of `GET /tickets`, and responses of `PATCH` and `transition` all include an `assignee` key; it is `null` for a new ticket and the agent's name after an assignment. A ticket's assignee is kept when it is changed, transitioned, resolved or closed.
Source: request; implied: "Every ticket shows its assignee"

### C-10: The agent a ticket is assigned to is notified of it
Observable: after assigning a ticket to `dana`, `GET /admin/outbox` lists one new notification whose `to` is `dana` and `ticket` is the ticket's id, and when delivered (notifier file or in-memory deliveries) its message says that the ticket was assigned to them. It is delivered by the worker, not during the request, and is not dead after the retries (the notification kind has a message template).
Source: request; existing: docs/decisions/0006-notification-outbox.md, CONTRIBUTING.md
Open: the wording of the subject and body, decided by the help desk; tests check only recipient, ticket and that it names the assignment, not the words.

### C-11: Each different assignment is notified, even while an earlier notification is still pending
Observable: with the worker off, assigning T-0001 to `dana` then to `sam` leaves two pending notifications, one to `dana` and one to `sam`; assigning to `dana`, unassigning, and assigning to `dana` again makes the agent notified of the second assignment as well (two to `dana` once both are queued). The outbox's de-duplication by key must not swallow a real new assignment.
Source: implied: "The agent a ticket is assigned to is notified that it was assigned to them"; existing: src/outbox.js (a pending key blocks a second event)

### C-12: Unassigning, a same-agent assign and a refused request notify no one
Observable: after `{"assignee": null}`, a repeated assignment to the same agent, or any 400/404/409 answer, the outbox holds no new notification.
Source: implied: "notified that it was assigned to them"; request ("changes nothing")

### C-13: Assignment changes are written to the audit log
Observable: after assigning `dana` to T-0001 as actor `kim` (`X-Actor: kim`), `GET /tickets/T-0001/audit` has a last entry with `actor` `kim` and `changes` containing `assignee: {"from": null, "to": "dana"}`; unassigning records `{"from": "dana", "to": null}`. A change that changes nothing and a refused request add no entry.
Source: implied: README.md ("every change is on record"), CONTRIBUTING.md, docs/decisions/0007-append-only-audit-log.md
Open: the action name of the entry (for example `ticket.assigned`); tests do not check it.

### C-14: The assignee survives a restart
Observable: with `DATA_FILE` set, assign a ticket, stop the service and start it again on the same file: the ticket still shows the assignee, and a file written before this change loads with every ticket showing `null`.
Source: implied: README.md ("an optional data file, so the service keeps its state across restarts"); existing: src/persistence.js

### C-15: `GET /tickets?assignee=<agent>` lists only that agent's tickets
Observable: with tickets assigned to `dana`, `sam` and no one, `?assignee=dana` returns only dana's tickets in id order with the usual `items`/`next` shape; an agent with no tickets gives `{"items": [], "next": null}`; paging with `limit` and `cursor` keeps the filter.
Source: request

### C-16: `GET /tickets?assignee=` (empty) lists only the unassigned tickets
Observable: the response holds exactly the tickets whose `assignee` is `null`, not 400.
Source: request

### C-17: A ticket is listed only when it matches every filter given
Observable: with `?status=open&assignee=dana` only open tickets of dana are listed; `?priority=high&assignee=` lists only unassigned high-priority tickets; likewise `?status=open&priority=urgent` lists only tickets that are both (today a ticket matching either filter is listed, against docs/api.md).
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")

### C-18: The command-line listing shows each ticket's assignee
Observable: `bin/tickets.js list` prints the assignee of each ticket in its own column (the name, or a visible placeholder of the builder's choice such as `-` for none); `list --raw` adds the assignee as a further tab-separated column.
Source: request
Open: the placeholder for an unassigned ticket in the table and in `--raw`; tests check only that an assigned ticket's line contains the name.

### C-19: The first four columns of `list --raw` keep their positions
Observable: each `--raw` line still has id, status, priority and title as tab-separated columns 1 to 4, so `scripts/weekly-report.js` gives the same counts as before; an assignee name never contains a tab or line break.
Source: existing: README.md ("they must keep their positions")

### C-20: Existing behaviour and tests are unchanged
Observable: `npm test` passes with every existing test file as it is, plus the new tests under `test/`; `status` and `priority` filter validation, the error envelope and pagination answer as before.
Source: request

### C-21: New tests cover the behaviour
Observable: new `node:test` files under `test/` cover assigning, unassigning, the refusals (400, 404, 409), no-change assignment, the notification, the `assignee` filter and combined filters; `npm test` runs them with the existing ones.
Source: request

### C-22: A name that would break single-line output is refused
Observable: an `assignee` containing a tab, a line break or another control character answers 400 `invalid`.
Source: existing: src/tickets/validate.js (control characters are refused so the command line's tab-separated output holds)
