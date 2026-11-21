## Use cases

### U-1: A help-desk lead assigns a ticket to an agent, so the agent knows it is theirs to work
Flow: The lead sends `PUT /tickets/T-0007/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket (optionally with an `X-Actor` header). The answer is 200 with the ticket, whose `assignee` is `"dana"`. Later `GET /tickets/T-0007` shows the same assignee. The lead may send the same request again and nothing changes.
Source: request

### U-2: A help-desk lead takes a ticket off an agent
Flow: The lead sends `PUT /tickets/T-0007/assignee` with `{"assignee": null}` for an open or in-progress ticket. The answer is 200 with the ticket, whose `assignee` is `null`.
Source: request

### U-3: An agent is told a ticket was assigned to them
Flow: After a ticket is assigned to `dana`, a notification for `dana` about that ticket is queued with the change and delivered by the background worker, like the requester notifications.
Source: request

### U-4: An agent (or lead) lists work by assignee
Flow: `GET /tickets?assignee=dana` lists dana's tickets. `GET /tickets?assignee=` lists the unassigned ones. Adding other filters (`status=open`) narrows the list to tickets that match all of them. Every listed ticket shows its `assignee`.
Source: request

### U-5: An operator sees who each ticket is assigned to on the command line
Flow: `node bin/tickets.js --data FILE list` prints a table in which each ticket's row shows its assignee.
Source: request

### U-6: An auditor or operator can trace who changed an assignment, and the assignment survives a restart
Flow: `GET /tickets/:id/audit` lists the assignment change with the actor; with `DATA_FILE` set, restarting the service shows the same assignees.
Source: implied: docs/decisions/0007 ("every change to a ticket" is audited) and the README ("every change is on record", the data file keeps the state)

## Clauses

### C-1: Assigning an open or in-progress ticket to an agent sets its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": "dana"}` on a ticket whose status is `open` or `in_progress` answers 200 with the ticket, in which `assignee` is `"dana"`, `updated` is the time of the change, and every other field (`id`, `title`, `priority`, `requester`, `status`, `created`) is what it was. `GET /tickets/:id` then shows `assignee: "dana"`. A ticket already assigned to another agent is reassigned the same way.
Source: request

### C-2: Unassigning an open or in-progress ticket clears its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": null}` on an `open` or `in_progress` ticket that has an assignee answers 200 with the ticket, in which `assignee` is `null` and `updated` is the time of the change. `GET /tickets/:id` then shows `assignee: null`.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: A one-character name and a 64-character name are accepted (200, the assignee is that name). A 65-character name and the empty string `""` are refused with 400 `invalid` in the usual error envelope; the ticket is unchanged and no audit entry or notification results.
Source: request
Open: Whether a name made only of spaces counts as empty, and whether spaces around a name are trimmed before the length is counted or the name is stored (the existing requester and title fields are trimmed). The requester of the change decides; tests use names without surrounding spaces.

### C-4: The assignee must be a string or null
Observable: A body with no `assignee` field, or with `assignee` a number, a boolean, an array or an object, is refused with 400 `invalid`; the ticket is unchanged. A missing field is not treated as `null`.
Source: implied: the request defines only a name or null as values; existing: docs/api.md ("a missing or wrong field" is `invalid`)

### C-5: A name that is not a single line of text is refused
Observable: An assignee containing a control character (a tab, a line break) is refused with 400 `invalid`; the ticket is unchanged.
Source: implied: README "Command line" (the command-line output is tab-separated per ticket, one line each) and existing: src/tickets/validate.js (titles and requesters must be a single line)

### C-6: A body with a field other than `assignee` is refused
Observable: `{"assignee": "dana", "team": "x"}` answers 400 `invalid`; the ticket is unchanged.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)")

### C-7: Assigning on a ticket that does not exist is not found
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for an id no ticket has, answers 404 `not_found` in the error envelope.
Source: existing: docs/api.md (Errors)

### C-8: Resolved and closed tickets cannot be assigned or unassigned
Observable: On a ticket whose status is `resolved` or `closed`, a request that would change the assignee (a different agent, or `null` when it has an assignee) answers 409 `conflict` in the error envelope; the ticket's `assignee` and `updated` are unchanged and there is no audit entry or notification. The groups that behave alike are `open` and `in_progress` (allowed, C-1, C-2) and `resolved` and `closed` (refused).
Source: request
Open: What a resolved or closed ticket answers when the request asks for the value it already has (the same agent, or `null` on an unassigned ticket): 409 or 200 with nothing changed. The requester decides; either way nothing changes, and tests check only the different-value case.

### C-9: Assigning a ticket to the agent it already has changes nothing
Observable: `PUT` with the name the open or in-progress ticket already has answers 200 with the ticket as it was; `updated` is unchanged, no audit entry is added and no notification is enqueued.
Source: request

### C-10: Unassigning a ticket that has no assignee changes nothing
Observable: `PUT` with `{"assignee": null}` on an open or in-progress ticket whose `assignee` is `null` answers 200 with the ticket as it was; `updated` is unchanged and no audit entry is added.
Source: existing: CONTRIBUTING.md ("A change that changes nothing is not a change: no audit entry, no notification") and docs/api.md ("a request that changes nothing leaves [updated] as it was")

### C-11: Every ticket shows its assignee, null when unassigned
Observable: The ticket in the answers of `POST /tickets` (new tickets), `GET /tickets/:id`, every item of `GET /tickets`, `PATCH`, `POST /tickets/:id/transition` and the `PUT` has an `assignee` field: `null` for a ticket never assigned or since unassigned, otherwise the agent's name.
Source: request

### C-12: Tickets from a data file written before this change load as unassigned
Observable: A data file whose tickets have no `assignee` field starts the service; each of those tickets shows `assignee: null` and is in the `assignee=` (unassigned) listing; the CLI lists them without error.
Source: implied: "Everything the service already does keeps working"; existing: docs/operations.md (the data file is kept across restarts) and README ("Configuration")

### C-13: An assignment survives a restart
Observable: With `DATA_FILE` set, a ticket assigned to `dana` shows `assignee: "dana"` after the service is stopped and started again on the same file, and `bin/tickets.js --data FILE list` shows it. An unassignment survives the same way.
Source: implied: README (the data file keeps the state across restarts) and the request (the assignee is part of the ticket)

### C-14: Moving or editing a ticket does not change its assignee
Observable: `POST /tickets/:id/transition` (for example `in_progress` to `resolved`, and `resolved` back to `open`) and `PATCH /tickets/:id` leave the ticket's `assignee` as it was; a resolved ticket still shows the agent it had.
Source: implied: "Every ticket shows its assignee"; a ticket changes its assignee only through the request that names it

### C-15: Each assignment change is one audit entry
Observable: A request that changes the assignee adds one entry to `GET /tickets/:id/audit`, after the earlier entries, whose `changes` is `{ "assignee": { "from": <old assignee or null>, "to": <new assignee or null> } }`, whose `ticket` is the id, whose `actor` is the `X-Actor` header value (`system` without it) and whose `at` is the time of the change. An `X-Actor` longer than 64 characters is refused 400 `invalid`, as everywhere.
Source: implied: docs/decisions/0007 (every change to a ticket is recorded; changes list each field's before and after); existing: docs/api.md (the actor)
Open: The entry's `action` name (such as `ticket.assigned`) is not fixed by the request or the audit decision; tests do not check it.

### C-16: Assignment changes made one after another leave a consistent history
Observable: When several `PUT`s to the same ticket with different agents are sent at the same time, each answers 200 or 409 per the ticket's state, the ticket ends with the assignee of the last change applied, and the ticket's audit entries form a chain in which each entry's `from` equals the previous entry's `to` (starting from `null`).
Source: implied: decision 7 (no change without an entry, in the same step) and the request's rule that a repeated assignment changes nothing

### C-17: Assigning a ticket queues a notification for the assigned agent
Observable: After a `PUT` that assigns `T-0007` to `dana`, `GET /admin/outbox` lists (pending while the worker is off) an event for ticket `T-0007` whose `to` is `dana`, queued by that request. The notification is not sent inside the request.
Source: request; existing: docs/decisions/0006 (a change enqueues its notification with the change; request handlers never call the notifier)
Open: Whether the agent's name is a deliverable address or the relay maps it to one. The help desk's operators decide; the event's `to` is the agent's name.

### C-18: The assignment notification is delivered and says which ticket
Observable: With the worker running, the event of C-17 ends `sent` (not `dead`, even after its retries), and the delivered message (the line in `NOTIFY_FILE`, or the notifier's in-memory deliveries) is for `dana`, names ticket `T-0007` and says the ticket was assigned to them. The wording is free.
Source: request; existing: src/templates.js (an event type without a template goes dead)

### C-19: Reassigning before the first notification is sent still notifies the new agent
Observable: With the worker off, assign `T-0007` to `dana`, then to `sam`: the outbox holds an event to `sam` about `T-0007` (the pending event for `dana` does not swallow it).
Source: implied: the request (the agent a ticket is assigned to is notified) against decision 6 (a second notification with a pending key is dropped); a default key of the type and ticket alone would drop `sam`'s

### C-20: Two tickets assigned to the same agent notify them twice
Observable: With the worker off, assign `T-0007` and then `T-0008` to `dana`: the outbox holds one event to `dana` for each of the two tickets.
Source: implied: the request (each assignment notifies); decision 6 (keys make the same news once, not different news)

### C-21: Only a new assignee is notified
Observable: A `PUT` that unassigns (`null`), that repeats the current agent (C-9), or that is refused (C-3 to C-8) enqueues no assignment notification. A reassignment from `dana` to `sam` enqueues an event to `sam` and none to `dana`, and none to the requester.
Source: request ("the agent a ticket is assigned to is notified that it was assigned to them"); existing: CONTRIBUTING.md (no change, no notification)

### C-22: `GET /tickets?assignee=<agent>` keeps that agent's tickets
Observable: Only tickets whose `assignee` equals `<agent>` are listed, in id order (all statuses, resolved and closed included, unless another filter says otherwise). The comparison is the exact name as stored. A name no ticket has lists nothing: 200 with `items: []` and `next: null`.
Source: request
Open: What a filter value over 64 characters, or with surrounding spaces, does (matches nothing, or 400 `invalid`, or is trimmed). The requester decides; tests use ordinary names.

### C-23: `GET /tickets?assignee=` keeps the unassigned tickets
Observable: With an empty `assignee` parameter (`/tickets?assignee=`), only tickets whose `assignee` is `null` are listed, in id order, including tickets in any status that were never assigned or were unassigned.
Source: request

### C-24: Without the `assignee` parameter the listing is not filtered by assignee
Observable: `GET /tickets` and `GET /tickets?status=open` list assigned and unassigned tickets alike.
Source: implied: the request ("gains a filter"); existing: docs/api.md

### C-25: A ticket must match every filter given
Observable: `GET /tickets?status=open&assignee=dana` lists only open tickets assigned to dana (not dana's in-progress tickets, nor other agents' open tickets); `?status=open&priority=urgent` lists only open tickets that are urgent; `?assignee=&status=in_progress&priority=high` lists only unassigned, in-progress, high-priority tickets.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")

### C-26: The assignee filter pages like the other filters
Observable: With `?assignee=dana&limit=2`, a page holds at most 2 of dana's tickets and `next` is a cursor (null on the last page); passing `next` as `cursor` with `assignee=dana` returns the following tickets, and the pages together hold each of dana's tickets once, in id order.
Source: existing: docs/api.md ("List tickets"), CONTRIBUTING.md ("Listings are cursor pages")

### C-27: The listing's other filter and limit rules stay as they are
Observable: `status=done`, `priority=critical`, `status=` and a `limit` outside 1 to 100 are still 400 `invalid`; `status` and `priority` filters alone still list as before.
Source: existing: docs/api.md, test/query.test.js, test/api.test.js

### C-28: The command-line table shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` prints a table with a column for the assignee, headed with a title containing `ASSIGNEE`; the row of a ticket assigned to `dana` shows `dana`; the row of an unassigned ticket shows no agent's name. The existing columns and the `--status` and `--priority` filters still work.
Source: request
Open: How an unassigned ticket's cell reads (empty, `-`, `unassigned`); the requester decides. Tests check only that it names no agent.

### C-29: The first four columns of `list --raw` keep their positions
Observable: Each `list --raw` line still starts with id, status, priority and title separated by tabs, as the weekly report reads them by position; `node scripts/weekly-report.js --data FILE --json` gives the same counts as before for the same tickets, whether or not they are assigned.
Source: existing: README.md "Command line"
Open: Whether `list --raw` also shows the assignee, as a fifth tab-separated column after the title. The requester decides ("the command-line listing" may mean the table only); tests do not require a fifth column and do not forbid one.

### C-30: Everything the service already does keeps working
Observable: Creating, reading, patching, transitioning, auditing, the outbox, the health check, the requester notifications (created, resolved), the data file and the command line behave as docs/api.md and README.md describe; the requester of a new ticket is still told it was received and the requester of a resolved ticket is still told it was resolved, once each.
Source: request

### C-31: The existing tests pass unchanged
Observable: The test files that exist before this change are not edited, and `npm test` runs them and they pass.
Source: request

### C-32: New behaviour has node:test tests under test/, run by `npm test`
Observable: Test files under `test/` that use `node:test` cover the assignment endpoint (assign, unassign, the length bound, state refusals, the no-op, unknown ticket), the notification, the `assignee` filter with combined filters, and the command-line listing; `npm test` runs them together with the existing ones and exits 0.
Source: request
