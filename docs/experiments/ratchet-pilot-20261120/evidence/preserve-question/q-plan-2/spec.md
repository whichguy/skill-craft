## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, to make someone responsible for it
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}`. Gets 200 and the ticket, whose `assignee` is `"dana"`. Dana is notified that the ticket was assigned to them.
Source: request

### U-2: A dispatcher unassigns a ticket, to take it off someone
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": null}`. Gets 200 and the ticket, whose `assignee` is `null`.
Source: request

### U-3: A client sees who has each ticket
Flow: Reads any ticket (`GET /tickets/:id`, `GET /tickets`, or a response that returns a ticket) and sees `assignee`: the agent's name, or `null` when unassigned, including for tickets created before this change.
Source: request

### U-4: An agent lists their own work, or the unassigned queue
Flow: `GET /tickets?assignee=dana` lists Dana's tickets; `GET /tickets?assignee=` lists unassigned tickets; combined with `status` or `priority`, only tickets matching all filters are listed.
Source: request

### U-5: An operator sees assignees on the command line
Flow: Runs `node bin/tickets.js list` and sees each ticket's assignee.
Source: request

### U-6: An operator or lead keeps using the service as before
Flow: Existing API calls, the weekly report, the data file and tests behave as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: Response 200 with the ticket, `assignee` equal to the agent given; a later `GET /tickets/:id` shows the same.
Source: request

### C-2: `PUT /tickets/:id/assignee` with `{"assignee": null}` unassigns an open or in-progress ticket
Observable: Response 200 with the ticket, `assignee` `null`; a later `GET` shows `null`.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: A 64-character name is accepted; an empty string, or a name of 65 characters, answers 400 `invalid` in the error envelope and changes nothing. A value that is neither a string nor null (a number, an object, a boolean), a body without `assignee`, or a body that is not a JSON object also answers 400 `invalid`.
Source: request (the rule); existing: docs/api.md (400 `invalid` for a missing or wrong field, malformed body)
Open: Whether surrounding whitespace is trimmed, whether a whitespace-only name counts as empty, and whether control characters are refused is not stated; the existing `requester` field trims, rejects empty-after-trim and refuses control characters, which a builder may follow. Settled by the requester. Tests check only the clear cases above.

### C-4: Extra fields in the assignee body are refused
Observable: `{"assignee": "dana", "foo": 1}` answers 400 `invalid` and changes nothing.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)")

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: For a ticket whose status is `resolved` or `closed`, a PUT of an agent name or of `null` answers 409 `conflict` in the error envelope; the ticket's assignee, `updated` and audit log are unchanged and nobody is notified.
Source: request; existing: CONTRIBUTING.md (a state that does not allow a request is 409)
Open: Order of checks when the body is invalid and the ticket is resolved/closed (400 or 409) is not stated; tests should not depend on it.

### C-6: A ticket that does not exist answers 404 on assignment
Observable: `PUT /tickets/T-9999/assignee` with a valid body answers 404 `not_found` in the error envelope.
Source: existing: docs/api.md (404 `not_found` for no such ticket)

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: The PUT answers 200 with the ticket unchanged; `updated` keeps its value, the audit log gains no entry, and no notification is enqueued or sent. The same holds for unassigning an already-unassigned ticket.
Source: request ("changes nothing"); existing: CONTRIBUTING.md and docs/api.md (a change that changes nothing: no audit entry, no notification, `updated` stays)

### C-8: Every ticket shows `assignee`, `null` when unassigned
Observable: A newly created ticket (201 response), `GET /tickets/:id`, each item of `GET /tickets`, and the responses of PATCH, transition and assignment all contain `"assignee": null` when unassigned, otherwise the agent's name.
Source: request

### C-9: Assignment and unassignment survive a restart; tickets stored before this change read as unassigned
Observable: With `DATA_FILE` set, after restarting the service, a ticket assigned to `dana` still shows `"dana"`. A data file written by the previous version (tickets with no assignee) loads without error and those tickets show `"assignee": null`.
Source: implied: README.md ("keeps its state across restarts", the file is loaded at start); a file the service refuses to load would break "everything keeps working"

### C-10: The agent a ticket is assigned to is notified that it was assigned to them
Observable: After assigning ticket T to `dana`, the outbox (`GET /admin/outbox`) holds a notification addressed `to` `dana` for that ticket, and, once the worker delivers it, the notifier records a delivery to `dana` mentioning the ticket id; it is delivered rather than ending dead for lack of a template.
Source: request; existing: docs/decisions/0006-notification-outbox.md and CONTRIBUTING.md (notifications go through the outbox, with a template)
Open: The notification's wording and subject, its `type` name, and how a mail relay maps a name to an address (the outbox `to` is the agent name as given) are not stated; the requester settles them.

### C-11: Each distinct assignment is notified, even close together
Observable: Assigning T to `dana`, then (before the worker runs) to `lee`, then to `dana` again, leaves a notification for `lee` as well as for `dana`; a reassignment to a different agent is never swallowed by an earlier pending notification about the same ticket. Re-assigning to the agent already assigned (C-7) enqueues nothing.
Source: implied: C-10 for every assignment; existing: docs/operations.md (a pending notification with the same key swallows a repeat)
Open: Whether the first agent is told it was taken off, and whether `dana` twice in a row while pending is one notification or two, is not stated; the requester settles it. Tests should not assert either.

### C-12: Unassigning notifies nobody
Observable: After `{"assignee": null}` on an assigned ticket, no new notification is enqueued.
Source: choice: the request says only that the agent assigned to is notified of assignment; a notification on unassignment is not asked for.

### C-13: An assignment change is audited
Observable: `GET /tickets/:id/audit` gains one entry for each effective assignment or unassignment, showing `assignee` with its value before and after (`null` when none), with the actor from `X-Actor` or `system`.
Source: existing: docs/decisions/0007-append-only-audit-log.md and CONTRIBUTING.md (every change is audited)
Open: The entry's `action` name is not stated; the requester settles it. Tests should not depend on it.

### C-14: A change of assignee updates the ticket's `updated` time
Observable: After an effective assignment or unassignment, `updated` is the time of the change.
Source: existing: docs/api.md (`updated`: when it last changed)

### C-15: `GET /tickets?assignee=<agent>` lists only that agent's tickets
Observable: Only tickets whose `assignee` equals the value are listed, in id order, in the usual cursor pages; the match is on the whole name.
Source: request
Open: Whether the match is case-sensitive is not stated; tests use names that differ by more than case.

### C-16: `GET /tickets?assignee=` (empty value) lists only unassigned tickets
Observable: Only tickets whose `assignee` is `null` are listed; no assigned ticket appears.
Source: request

### C-17: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only open tickets assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent (not tickets that are open or urgent).
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")

### C-18: The assignee filter accepts any text and does not by itself make the request invalid
Observable: `?assignee=nobody` answers 200 with `items` empty when no ticket is assigned to `nobody`. Existing filter checks (`status`, `priority`, `limit`, `cursor` invalid → 400) are unchanged.
Source: choice: unlike status and priority there is no fixed set to check against, and the request gives no error case.

### C-19: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js list` prints an ASSIGNEE column holding each ticket's assignee, with an unassigned ticket shown as a visible placeholder (not the word `null` required; not blank-shifting other columns); the existing columns remain.
Source: request
Open: The placeholder for unassigned and the column's position in the table are not stated; the requester settles them.

### C-20: The command-line `list --raw` output keeps its existing columns in place
Observable: Each `list --raw` line still begins with id, status, priority, title as tab-separated fields 1–4 with the same values, so `scripts/weekly-report.js` (and `--json`) gives the same counts as before.
Source: existing: README.md ("so they must keep their positions")
Open: Whether `--raw` also shows the assignee (e.g. as a fifth field) is not stated; the request says "the command-line listing". The requester settles it. Tests check only fields 1–4.

### C-21: Existing behaviour and tests are preserved
Observable: Every test in `test/` that exists now passes unmodified; PATCH of title/priority, transitions, creation notifications, resolved notifications, the audit log, pagination, errors and the data file behave as documented. `PATCH` does not accept `assignee` (unknown field, 400).
Source: request; existing: docs/api.md

### C-22: New tests cover the new behaviour and run under `npm test`
Observable: New `node:test` files under `test/` cover assignment, unassignment, validation, state refusal, no-op, notification, the listing filters (including combination) and the command-line column; `npm test` runs them with the existing tests and all pass.
Source: request

### C-23: A new ticket's audit entry keeps listing title, priority, requester and status, from null
Observable: `GET /tickets/:id/audit` for a just-created ticket shows a `ticket.created` entry whose `changes` hold exactly `title`, `priority`, `requester` and `status`, each from `null`; the entry does not list `assignee`.
Source: existing: src/store.js (CREATED_FIELDS) and test/api.test.js

### C-24: A request with a method a path does not answer keeps answering 404 `not_found` naming the methods it does answer
Observable: `DELETE /tickets/T-0001` answers 404 `not_found` as before; `GET /tickets/T-0001/assignee` answers 404 `not_found` whose message names the methods that path answers (now `PUT`).
Source: existing: src/app.js (notFound) and src/router.js (methodsFor)

### C-25: The command line's filters, `show` and exit codes keep working
Observable: `list --status S` and `list --priority P` still filter; `show ID` still prints the ticket and its history (and may show the assignee); exit codes stay 0 done, 1 no such ticket, 2 usage or data file problem; the command line never writes the data file.
Source: existing: bin/tickets.js and README.md ("Command line")

### C-26: A ticket keeps its assignee when it is resolved, reopened or closed
Observable: Moving an assigned ticket by transition does not change its `assignee`, adds no assignment audit entry and sends no assignment notification.
Source: implied: C-21 (transition changes only status) and C-5 (assignment is refused only for resolved/closed, nothing asks for it to be cleared)
