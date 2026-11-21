## Use cases

### U-1: An agent or operator assigns a ticket to an agent, to make clear who works it
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. Sees 200 and the ticket with `"assignee": "dana"`. Dana is notified that the ticket was assigned to them.
Source: request

### U-2: An agent or operator unassigns a ticket
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": null}` for an open or in-progress ticket. Sees 200 and the ticket with `"assignee": null`.
Source: request

### U-3: A caller repeats an assignment and nothing changes
Flow: Sends the same `{"assignee": "dana"}` again. Sees 200 and the same ticket; no new audit entry, no second notification, `updated` unchanged.
Source: request

### U-4: A caller lists one agent's tickets, or the unassigned ones
Flow: `GET /tickets?assignee=dana` lists dana's tickets; `GET /tickets?assignee=` lists the unassigned ones; combined with `status` or `priority`, only tickets matching all filters are listed.
Source: request

### U-5: An operator sees assignees on the command line
Flow: Runs `node bin/tickets.js list` and sees each ticket's assignee.
Source: request

### U-6: Existing users and tools keep working
Flow: Creating, changing, transitioning, listing, auditing tickets, the notifications, the data file, `list --raw` and the weekly report behave as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: Assigning an open or in-progress ticket sets its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": "dana"}` on a ticket whose status is `open` or `in_progress` answers 200 with the ticket, whose `assignee` is `"dana"`; a later `GET /tickets/:id` shows the same. The ticket's `updated` is the time of the change.
Source: request

### C-2: A null assignee unassigns an open or in-progress ticket
Observable: `{"assignee": null}` on an assigned open or in-progress ticket answers 200 with `assignee` null; a later `GET /tickets/:id` shows null.
Source: request

### C-3: An assignee is a non-empty name of at most 64 characters
Observable: A 64-character name is accepted; a 65-character name, an empty name, and a value that is neither a string nor null (a number, `true`, an object, an array) answer 400 with error code `invalid`, and the ticket is unchanged.
Source: request
Open: Whether surrounding whitespace is trimmed or a whitespace-only name counts as empty, and whether control characters are refused, is not stated. The existing `requester` field trims, refuses blank and refuses control characters (src/tickets/validate.js); the requester of the request decides whether an assignee follows it. Tests check only names with no surrounding whitespace or control characters.

### C-4: A body without a usable `assignee` is invalid
Observable: A body that is not a JSON object, has no `assignee` key, or has any other field answers 400 `invalid` and changes nothing.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)"; a body that is not a JSON object is `invalid`); implied: the `assignee` key is the only thing the endpoint takes.

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: `PUT /tickets/:id/assignee` on a `resolved` or `closed` ticket, with a name or with null, answers 409 `conflict` in the error envelope, and the ticket's assignee, `updated` and audit are unchanged.
Source: request
Open: Whether a no-op request on a resolved or closed ticket (null on an unassigned one, or the name it already has) is answered 409 or 200 is not stated; the request says only open and in-progress tickets can be assigned or unassigned. Tests for no-ops use open or in-progress tickets only.

### C-6: An unknown ticket id is not found
Observable: `PUT /tickets/T-9999/assignee` for a ticket that does not exist answers 404 `not_found`.
Source: existing: docs/api.md (`not_found`)

### C-7: Assigning to the agent already assigned changes nothing
Observable: A request giving the ticket the assignee it already has (including null for an unassigned ticket) answers 200 with the ticket; `updated` is unchanged, no audit entry is added, and no notification is enqueued.
Source: request; existing: docs/api.md (a request that changes nothing leaves `updated` as it was)

### C-8: Every ticket shows its assignee
Observable: Every ticket in `POST /tickets` (201), `GET /tickets/:id`, `GET /tickets` items, `PATCH` and transition responses has an `assignee` key: a string, or null when unassigned. A new ticket has `null`.
Source: request

### C-9: The assignee survives a restart
Observable: With `DATA_FILE` set, after assigning a ticket and restarting the service on the same file, the ticket still shows the assignee. A data file written before this change (tickets with no `assignee`) loads, and its tickets show `assignee` null.
Source: implied: "Every ticket shows its assignee" with the optional data file in README.md; existing: src/persistence.js keeps only the fields it names.

### C-10: The assigned agent is notified that the ticket was assigned to them
Observable: After assigning to `"dana"`, the outbox (`GET /admin/outbox`) holds a notification whose `to` is `"dana"` and whose `ticket` is the ticket's id, of a type that says the ticket was assigned, and the background worker delivers it (in `NOTIFY_FILE`, or in memory) with a subject and body that name the ticket. It is enqueued in the same change as the assignment, not sent inside the request.
Source: request; existing: docs/decisions/0006-notification-outbox.md, CONTRIBUTING.md (handlers never call the notifier)
Open: What an agent's notification address is (the request names agents only by name, and the outbox's `to` is a free string) and the wording of the message are not stated. The name is used as `to`; the requester of the request decides if a mapping to addresses is wanted.

### C-11: Notifications for different assignments are not merged or lost
Observable: Assigning a ticket to `"dana"` and then, before the first notification is delivered, to `"lee"` leaves a notification for each of them; and assigning to dana, unassigning, then assigning to dana again while the first is still pending still ends with dana notified of the later assignment or already holding a pending one for it. No assignment to an agent that changes the ticket leaves that agent without a notification.
Source: implied: C-10 with docs/decisions/0006-notification-outbox.md (same-key notifications wait for the pending one instead of being queued twice; default key is type and ticket)

### C-12: Unassigning and no-op requests notify no one
Observable: `{"assignee": null}` enqueues no notification; a no-op (C-7) enqueues none; a refused request (C-3, C-4, C-5, C-6) enqueues none.
Source: implied: the request notifies "the agent a ticket is assigned to" only when it is assigned to them.
Open: Whether the previous assignee should be told they were unassigned or replaced is not asked for; none is required.

### C-13: A change of assignee is on the audit record
Observable: A request that changes the assignee adds one entry to `GET /tickets/:id/audit` for that ticket, with `changes` holding `assignee` as `{ "from": <old or null>, "to": <new or null> }` and the actor from `X-Actor` (or `system`). A request that changes nothing adds none.
Source: implied: README.md ("every change is on record"), docs/decisions/0007-append-only-audit-log.md
Open: The entry's `action` name is not stated; tests accept any non-empty action.

### C-14: `GET /tickets?assignee=<agent>` keeps that agent's tickets
Observable: Only tickets whose assignee equals the given name exactly are listed, in id order and paged as before.
Source: request
Open: Whether the name match ignores case is not stated; tests use names that differ by more than case.

### C-15: An empty `assignee=` keeps the unassigned tickets
Observable: `GET /tickets?assignee=` lists exactly the tickets whose assignee is null, in any status.
Source: request

### C-16: Without an `assignee` parameter the listing is not filtered by assignee
Observable: `GET /tickets` with no `assignee` lists assigned and unassigned tickets alike.
Source: implied: the filter is added, not required; existing: docs/api.md

### C-17: A ticket must match every filter given
Observable: `GET /tickets?status=open&assignee=dana` lists only open tickets assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent (not tickets that match one of them); with `limit` and `cursor`, the pages together hold exactly the tickets matching all filters.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")
Open: Today `matchesFilters` in src/tickets/query.js keeps a ticket that matches any one filter, contradicting the docs; the request requires all, which is taken here.

### C-18: The command-line listing shows each ticket's assignee
Observable: `node bin/tickets.js list` prints each ticket's assignee in its row, with an assigned ticket showing the name and an unassigned ticket showing something that is not another ticket's name (a dash or empty).
Source: request
Open: The column's title, position and the marker for unassigned are not stated.

### C-19: The raw listing keeps its columns by position
Observable: `list --raw` still prints id, status, priority, title as the first four tab-separated columns, so `scripts/weekly-report.js` gives the same counts as before.
Source: existing: README.md ("Command line"), src/format.js (RAW_COLUMNS)
Open: Whether `list --raw` should also show the assignee is not stated; if it does, it must come after the title.

### C-20: Existing behaviour is unchanged
Observable: The existing tests in test/ pass unmodified. Create, `PATCH` (title and priority only; an `assignee` field there is still refused as unknown), transition, audit, error envelope, pagination, the `status` and `priority` filters (including `invalid` for a bad value), `/health`, `/admin/outbox`, the creation and resolution notifications to requesters, and the data file behave as in docs/api.md.
Source: existing: docs/api.md, README.md; request

### C-21: New tests cover the new behaviour and run with `npm test`
Observable: `npm test` runs new node:test files under test/ together with the existing ones, and they pass.
Source: request
