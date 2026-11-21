## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, to get it worked by that person
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. Sees 200 and the ticket with `"assignee": "dana"`. Dana is notified that the ticket was assigned to her/them.
Source: request

### U-2: A dispatcher unassigns a ticket, to return it to the pool
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. Sees 200 and the ticket with `"assignee": null`.
Source: request

### U-3: An agent lists the tickets assigned to them, or the unassigned ones, to find work
Flow: Sends `GET /tickets?assignee=dana` and sees only dana's tickets; sends `GET /tickets?assignee=` and sees only unassigned tickets; combines with `status` or `priority` and sees only tickets matching all of them.
Source: request

### U-4: An operator lists tickets on the command line, to see who has what
Flow: Runs `node bin/tickets.js --data FILE list` and sees each ticket's assignee in its row.
Source: request

### U-5: An existing client or operator keeps using the service as before
Flow: Creates, changes, transitions, lists and reads tickets, reads audit and outbox, runs `list --raw` and the weekly report, and starts the service on an existing data file, with the same results as before apart from the added `assignee` field.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For a ticket with status `open` or `in_progress`, the response is 200 with the ticket whose `assignee` is the given name; a following `GET /tickets/:id` shows the same `assignee`.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For a ticket with status `open` or `in_progress` and an assignee, the response is 200 with `"assignee": null`; a following `GET /tickets/:id` shows null.
Source: request

### C-3: An agent name is a non-empty string of at most 64 characters; 64 is accepted, 65 is refused
Observable: `{"assignee": "<64 characters>"}` answers 200; `{"assignee": ""}` and a 65-character name answer 400 with error code `invalid` in the usual envelope and change nothing (ticket unchanged, no audit entry, no notification).
Source: request
Open: Whether the name is trimmed first, whether a whitespace-only name counts as empty, and whether control characters are refused (existing `title`/`requester` fields trim and refuse control characters) is not stated; the requester decides. Tests should use plain names without surrounding spaces and treat only `""` as certainly invalid.

### C-4: A body that is not a valid assignee request is refused with 400 `invalid`
Observable: A body with no `assignee` field, an `assignee` that is neither a string nor null (e.g. `5`, `true`, `{}`), or any other field besides `assignee`, answers 400 `invalid` and changes nothing.
Source: implied: docs/api.md states malformed fields are `invalid` and unknown body fields are refused with 400.

### C-5: Only open and in-progress tickets can be assigned or unassigned; other tickets answer 409 `conflict`
Observable: For a ticket whose status is `resolved` or `closed`, a PUT with a valid agent or with null answers 409 `conflict` in the error envelope, and the ticket's `assignee` and `updated` stay as they were. An unknown ticket id answers 404 `not_found`.
Source: request (states); existing: docs/api.md (error codes 404/409)
Open: When a request is both for a resolved/closed ticket and repeats the ticket's current assignee (or null on an unassigned ticket), whether the answer is 409 or a 200 no-op is not stated; the requester decides. Tests check 409 only for a change of assignee.

### C-6: Assigning a ticket to the agent it already has changes nothing
Observable: The response is 200 with the ticket unchanged; `updated` is unchanged; no audit entry is added; no notification is enqueued.
Source: request; existing: docs/api.md (a request that changes nothing leaves `updated`, no audit entry)

### C-7: Unassigning an unassigned open or in-progress ticket changes nothing
Observable: `{"assignee": null}` on an open or in-progress ticket with no assignee answers 200 with the ticket unchanged, `updated` unchanged, no audit entry.
Source: implied: C-6 and the existing rule that a request that changes nothing leaves no trace.

### C-8: Every ticket shows its `assignee`, null when unassigned
Observable: Every ticket in `POST /tickets` (201), `GET /tickets/:id`, `GET /tickets` items, `PATCH` and transition responses has an `assignee` field: null for a new ticket, otherwise the agent's name. A ticket keeps its assignee across `PATCH` and lifecycle transitions.
Source: request; implied: assignment is meant to persist while the ticket moves on.
Open: Whether resolving or closing a ticket should clear its assignee is not stated; this spec keeps it (the request does not ask for clearing).

### C-9: The assignee survives a restart, and a data file written before this change still loads
Observable: With `DATA_FILE`, after assigning and restarting the service, `GET /tickets/:id` shows the same assignee. A data file whose tickets have no `assignee` field starts the service, and those tickets show `"assignee": null`.
Source: implied: docs/operations.md (state is kept across restarts; existing files must remain usable); existing: src/persistence.js.

### C-10: Changing the assignee is recorded in the ticket's audit history
Observable: A PUT that changes the assignee adds one entry to `GET /tickets/:id/audit`, with the actor from `X-Actor` (or `system`), and `changes` containing `assignee` with `from` (previous name or null) and `to` (new name or null).
Source: implied: README ("every change is on record"), docs/decisions/0007 (audit of every change).
Open: The entry's `action` string is not stated (a new value such as `ticket.assigned` is expected); the requester decides. Tests check `changes`, not the action name.

### C-11: Assigning a ticket to an agent notifies that agent that it was assigned to them
Observable: After a PUT that changes the assignee to an agent, a notification addressed to that agent's name, about that ticket, appears in `GET /admin/outbox` (pending, or sent once the worker runs, and written to `NOTIFY_FILE` with that recipient) and says the ticket was assigned. It is enqueued by the change itself, not sent inside the request.
Source: request; existing: docs/decisions/0006 (notifications go through the outbox, with a template per type)
Open: The notification type name and wording are not stated; the requester decides. The agent name is used as the recipient as given.

### C-12: Reassigning to a different agent notifies the new agent even if an earlier assignment notification is still pending
Observable: Assign T-0001 to `dana`, then (before the worker delivers) to `sam`: the outbox has a notification for `sam` as well as the one for `dana`. Assigning back to an agent whose earlier notification is still pending does not need a second one.
Source: implied: the outbox deduplicates by key while pending (docs/decisions/0006); a key that ignores the agent would drop the new agent's notification.

### C-13: Unassigning, no-op requests and refused requests send no assignment notification
Observable: After `{"assignee": null}`, a repeated assignment to the same agent, or a 400/404/409 response, the outbox holds no new notification.
Source: implied: request notifies only "the agent a ticket is assigned to ... that it was assigned"; C-6.

### C-14: `GET /tickets?assignee=<agent>` lists only that agent's tickets
Observable: Only tickets whose `assignee` equals the given name exactly are in `items`, in id order, paged as before (`limit`, `cursor`, `next` work with the filter).
Source: request; existing: docs/api.md (pages in id order)

### C-15: `GET /tickets?assignee=` (empty value) lists only unassigned tickets
Observable: Only tickets whose `assignee` is null are listed.
Source: request

### C-16: A ticket is listed only when it matches every filter given
Observable: `?assignee=dana&status=open` lists only dana's open tickets; `?status=open&priority=urgent` lists only open tickets that are urgent; a ticket matching one filter but not the other is not listed. `?assignee=` with `status=in_progress` lists only unassigned in-progress tickets.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")
Open: none for the rule itself. Note for builders: the current `matchesFilters` in src/tickets/query.js keeps a ticket that matches any one filter; the documented and requested rule is all of them. The existing test files only exercise single filters.

### C-17: An `assignee` filter with no matching ticket gives an empty list, not an error
Observable: `?assignee=nobody` answers 200 with `{"items": [], "next": null}`.
Source: implied: the filter takes any name (unlike `status`, which is checked against a fixed set); existing: test for `status=closed` empty list.

### C-18: The command-line `list` shows each ticket's assignee
Observable: `bin/tickets.js list` prints an assignee column in the table, giving the agent's name for assigned tickets and a visibly distinct non-name placeholder or blank for unassigned ones. `list` with no tickets still prints `no tickets`.
Source: request
Open: The column's position, heading and the unassigned marker are not stated; the requester decides. Tests check that an assigned ticket's row contains the name.

### C-19: `list --raw` keeps its existing columns in their positions
Observable: Each raw line still has id, status, priority, title as tab-separated columns 1–4, so `scripts/weekly-report.js` and `npm run report:weekly` give the same counts as before.
Source: existing: README.md ("they must keep their positions"), scripts/weekly-report.js
Open: Whether `--raw` also gives the assignee (as a fifth column, after the title) is not stated; the requester decides. If added, it must be after column 4.

### C-20: Existing API behaviour is unchanged by the change
Observable: `PATCH /tickets/:id` still refuses `assignee` as an unknown field (400) — assignment is only through the new endpoint; creating a ticket still refuses `assignee` in the body; all the existing tests in `test/` pass unmodified; existing error codes, ids, audit and outbox behaviour for create, update, transition are as documented in docs/api.md, apart from the added `assignee` field.
Source: request ("its existing tests must still pass as they are"); existing: docs/api.md
Open: Whether `POST /tickets` may accept an initial assignee is not asked for; this spec does not allow it.

### C-21: New tests under `test/` cover the new behaviour and run with `npm test`
Observable: `npm test` runs node:test files in `test/` covering assignment, unassignment, the refusals, the no-op, notification, the filters and the command-line listing, together with the existing tests, and exits 0.
Source: request
