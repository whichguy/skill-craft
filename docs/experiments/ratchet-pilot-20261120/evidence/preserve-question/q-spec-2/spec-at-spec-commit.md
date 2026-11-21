## Use cases

### U-1: A dispatcher assigns a ticket to an agent, to say who works it
Flow: They send `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. They get 200 and the ticket with `"assignee": "dana"`. A later `GET /tickets/T-0001` shows the same assignee.
Source: request

### U-2: A dispatcher unassigns a ticket, to return it to the pool
Flow: They send `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. They get 200 and the ticket with `"assignee": null`.
Source: request

### U-3: An agent is told a ticket was assigned to them, to pick up the work
Flow: After a ticket is assigned to `dana`, a notification addressed to `dana` is queued in the outbox and delivered by the worker like the existing notifications.
Source: request

### U-4: An agent or dispatcher lists tickets by assignee, to see someone's queue or the unassigned ones
Flow: `GET /tickets?assignee=dana` lists dana's tickets. `GET /tickets?assignee=` lists the unassigned tickets. `GET /tickets?assignee=dana&status=open` lists dana's open tickets only.
Source: request

### U-5: An operator reads the assignee on the command line, to see who has what
Flow: `node bin/tickets.js --data FILE list` prints a table that includes each ticket's assignee.
Source: request

### U-6: An existing client, data file or script keeps working unchanged
Flow: Callers that never mention assignees use the API, the data file, the command line and the weekly report as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For a ticket with status `open` or `in_progress`, the response is 200 with the ticket, whose `assignee` is the agent given. `GET /tickets/:id` then shows the same `assignee`. The ticket's other fields are unchanged, except that `updated` is set to the time of the change.
Source: request

### C-2: `PUT /tickets/:id/assignee` with `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For a ticket with status `open` or `in_progress` that has an assignee, the response is 200 with the ticket, whose `assignee` is `null`. `GET /tickets/:id` then shows `null`.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: A name of 1 to 64 characters is accepted, and one of exactly 64 characters is accepted. An empty string, a string of only whitespace, and a string of 65 or more characters are answered 400 `invalid` in the error envelope, and the ticket is unchanged. A leading or trailing space is not part of the name (trimmed), as for `title` and `requester`.
Source: request (bound), existing: src/tickets/validate.js (`text()` trims and counts after trimming, as the other names do)
Open: Whether other characters are allowed. A control character (tab, line break) is refused as for the other text fields, because the command line is tab-separated (README.md "Command line"). The requester would settle whether any other character or form of name is restricted.

### C-4: A body that is not a valid assignment is refused
Observable: A body that is not a JSON object, one with no `assignee` field, one whose `assignee` is neither a string nor `null` (a number, a boolean, an object, a list), and one with any field other than `assignee` are each answered 400 `invalid`, and the ticket is unchanged.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)", `invalid` is a body that is not a JSON object, or a missing or wrong field), src/tickets/validate.js

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: For a ticket with status `resolved` or `closed`, `PUT /tickets/:id/assignee` (an agent, or `null`) is answered 409 `conflict` in the error envelope, and the ticket is unchanged (assignee, `updated`, no audit entry, no notification). This holds also when the request would change nothing (the same agent, or `null` on an unassigned ticket).
Source: request, existing: docs/api.md and CONTRIBUTING.md ("the ticket's state does not allow this" is a conflict, 409)

### C-6: An unknown ticket id is not found
Observable: `PUT /tickets/T-9999/assignee`, for an id no ticket has, is answered 404 `not_found` in the error envelope.
Source: existing: docs/api.md (`not_found`: "no such ticket"), src/store.js

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: `PUT` with the agent the ticket already has answers 200 with the ticket as it was: `updated` is unchanged, no audit entry is added to `GET /tickets/:id/audit`, and no notification is added to `GET /admin/outbox`.
Source: request, existing: CONTRIBUTING.md ("A change that changes nothing is not a change: no audit entry, no notification"), docs/api.md (`updated` stays)

### C-8: Unassigning a ticket that has no assignee changes nothing
Observable: `PUT` with `{"assignee": null}` on an open or in-progress ticket with no assignee answers 200 with the ticket as it was: `updated` is unchanged, no audit entry, no notification.
Source: implied: by C-7 and by CONTRIBUTING.md ("A change that changes nothing is not a change")

### C-9: Every ticket shows its `assignee`
Observable: Every ticket in the response of `POST /tickets` (201), `GET /tickets/:id`, `GET /tickets` items, `PATCH /tickets/:id`, `POST /tickets/:id/transition` and `PUT /tickets/:id/assignee` has an `assignee` field, `null` when the ticket is unassigned. A newly created ticket has `"assignee": null`.
Source: request

### C-10: A ticket keeps its assignee when its status changes
Observable: After a ticket assigned to `dana` is moved to `resolved`, `closed`, or reopened to `open`, `GET /tickets/:id` still shows `"assignee": "dana"`. Moving a ticket along its lifecycle neither assigns nor unassigns it.
Source: implied: by the request, which names assignment only through the new endpoint and says everything else keeps working

### C-11: Assigning a ticket to an agent notifies that agent
Observable: After a ticket is assigned to an agent it did not have, `GET /admin/outbox` (with the worker off) lists a notification addressed (`to`) to that agent and naming the ticket (`ticket` is its id), and once the worker has run, the notification appears as sent, in the file `NOTIFY_FILE` names or in memory, with a subject and body that say the ticket was assigned to them. Two assignments to two different agents notify each of them.
Source: request, existing: docs/decisions/0006-notification-outbox.md (notifications are queued in the same change and delivered by the worker; request handlers never call the notifier)
Open: The wording of the subject and body, and the notification's type name, are not fixed by the request. A test checks only that it reaches the agent and names the ticket. Whether the notification is sent when an assignment follows an earlier, still undelivered one to the same agent (as in assign `dana`, unassign, assign `dana` within one worker interval) is not settled; the requester decides.

### C-12: Unassigning or a no-op assignment sends no notification
Observable: A request that unassigns a ticket, or one that assigns the agent the ticket already has, adds no notification to the outbox. A refused request (400, 404, 409) adds none either.
Source: request ("The agent a ticket is assigned to is notified that it was assigned to them"), existing: CONTRIBUTING.md
Open: Whether the previous assignee should be told they were unassigned or replaced is not asked for; the requester would decide. None is required.

### C-13: An assignment change is on the ticket's audit record
Observable: After a change of assignee, `GET /tickets/:id/audit` has a new last entry with the `actor` from the `X-Actor` header (`system` without it) and `changes` that holds `assignee` with its value `from` before and `to` after (`null` for unassigned). The existing entries are unchanged.
Source: existing: docs/api.md and docs/decisions/0007-append-only-audit-log.md ("Every change to the ticket"), CONTRIBUTING.md
Open: The `action` name of the entry is not settled; a test must not check it.

### C-14: The assignee survives a restart, and a data file without assignees still loads
Observable: With `DATA_FILE` set, a ticket assigned to `dana` shows `"assignee": "dana"` after the service is stopped and started again on the same file. A data file written before this change, whose tickets have no `assignee`, loads without error and its tickets show `"assignee": null`.
Source: implied: by "Every ticket shows its assignee" and "Everything the service already does keeps working", existing: docs/operations.md (the data file keeps the whole state; an old file must not stop the service)

### C-15: `GET /tickets?assignee=<agent>` lists that agent's tickets
Observable: Only tickets whose `assignee` is exactly the agent given are listed, in id order and paged as before, whatever their status. The match is exact: `assignee=dan` does not match `dana`.
Source: request
Open: Whether the case of the name matters (`Dana` and `dana`) is not stated; the requester decides. A test must use names that differ by more than case.

### C-16: `GET /tickets?assignee=` (empty) lists the unassigned tickets
Observable: Only tickets whose `assignee` is `null` are listed, with the response a 200 and not `invalid`.
Source: request

### C-17: A ticket must match every filter given
Observable: `GET /tickets?status=open&priority=urgent` lists only tickets that are open and urgent; `?assignee=dana&status=open` lists only dana's open tickets; `?assignee=&priority=high` lists only unassigned high-priority tickets. A ticket that matches one filter but not another is not listed. Paging with `limit` and `cursor` over a filtered listing gives the same tickets, no ticket twice, none missed.
Source: request, existing: docs/api.md ("a ticket is listed only when it matches every filter given")
Open: None, but note: today `matchesFilters` in src/tickets/query.js lists a ticket that matches any one of several filters (it contradicts docs/api.md). The request requires every filter; the existing tests check only single filters and keep passing.

### C-18: The existing filters, limit and cursor behave as before
Observable: `status` and `priority` filter as before and a value that is not a status or a priority is 400 `invalid`; `limit` is a whole number from 1 to 100, 20 when absent, and anything else is 400 `invalid`; a cursor the service did not issue is 400 `invalid`; a parameter the service does not know is ignored. With no `assignee` parameter, tickets are not filtered by assignee, assigned or not.
Source: existing: docs/api.md ("List tickets"), test/query.test.js, test/api.test.js

### C-19: The command-line table shows each ticket's assignee
Observable: `node bin/tickets.js list` prints in its table a column titled `ASSIGNEE` (or the equivalent heading) whose cell for each ticket is the assignee's name, and some visible mark (not an empty cell, so the columns still align) for an unassigned ticket. The existing columns ID, STATUS, PRIORITY, REQUESTER, UPDATED and TITLE are still shown, with the same values. `show` is not required to change. The command line still never writes the data file.
Source: request, existing: README.md ("Command line"), bin/tickets.js
Open: The column's place in the table, its exact heading and the mark for unassigned are not fixed; a test looks for the agent's name in the row of that ticket and not in the rows of the others.

### C-20: `list --raw` keeps its first four columns in place
Observable: Each line of `list --raw` still has tab-separated id, status, priority and title as its first four columns, in that order, so `scripts/weekly-report.js` gives the same counts on the same data and `npm run report:weekly` still works on a data file with assigned tickets.
Source: existing: README.md and scripts/weekly-report.js ("they must keep their positions"), src/format.js
Open: Whether `--raw` also shows the assignee is not stated ("the command-line listing" may mean the table only). A fifth column after the title is allowed and so is none; the requester decides. A name with tabs cannot occur (C-3).

### C-21: What the service already does keeps working
Observable: The existing tests under test/ pass without being edited. Creating, changing, transitioning, reading, auditing, the outbox, notifications of "received" and "resolved" (to the requester), the error envelope and codes, the data file and `GET /health` behave as documented in docs/api.md and docs/operations.md. Creating or changing a ticket without assignment sends no assignment notification.
Source: request, existing: docs/api.md, docs/operations.md, test/

### C-22: New tests for the new behaviour run with `npm test`
Observable: `npm test` runs node:test files under test/ that cover the new behaviour (assign, unassign, the refusals, the notification, the filter, the command-line column), together with the existing tests, and exits 0 when they all pass. No dependency is added to package.json.
Source: request, existing: CONTRIBUTING.md (no dependencies; "a change of behaviour comes with a test of it")
