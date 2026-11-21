## Use cases

### U-1: An agent or dashboard assigns a ticket to an agent, to say who works it
Flow: `PUT /tickets/T-0007/assignee` with `{"assignee": "dana"}` on an open or in-progress ticket. Answers 200 with the ticket, whose `assignee` is `"dana"`. The agent `dana` is notified that T-0007 was assigned to them. `GET /tickets/T-0007/audit` shows the change.
Source: request

### U-2: A caller unassigns a ticket, to hand it back to the queue
Flow: `PUT /tickets/T-0007/assignee` with `{"assignee": null}` on an open or in-progress ticket. Answers 200 with the ticket, whose `assignee` is `null`.
Source: request

### U-3: An agent lists their own tickets, or the unassigned ones, to see what to work on
Flow: `GET /tickets?assignee=dana` lists only dana's tickets; `GET /tickets?assignee=` lists only unassigned tickets; `GET /tickets?status=open&assignee=dana` lists only tickets that are open and dana's.
Source: request

### U-4: An operator lists tickets on the command line, to see who has each
Flow: `node bin/tickets.js --data FILE list` prints the table; each ticket's row shows its assignee.
Source: request

### U-5: An operator restarts the service, and existing data files keep working
Flow: after a restart with `DATA_FILE` set, assigned tickets are still assigned; a data file written before this change loads and its tickets show `assignee: null`.
Source: implied: docs/decisions/0008-json-data-file.md ("a change to the format must keep loading the files the previous version wrote")

## Clauses

### C-1: Every ticket carries an `assignee`: the agent's name, or null when unassigned
Observable: `GET /tickets/:id`, every item of `GET /tickets`, and every ticket the other endpoints answer with has an `assignee` key. A newly created ticket (`POST /tickets`) has `"assignee": null`.
Source: request

### C-2: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: answers 200 with the ticket whose `assignee` is the agent's name and whose `updated` is the time of the change; a later `GET /tickets/:id` shows the same assignee. An agent already assigned is replaced by the new one (reassignment).
Source: request
Open: whether reassignment is wanted at all is not stated; the request says only that a ticket "is assigned to that agent". Loosest reading taken: an assigned ticket may be assigned to another agent. The requester would settle it.

### C-3: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: answers 200 with the ticket whose `assignee` is `null`; a later `GET /tickets/:id` shows null.
Source: request

### C-4: An agent is a non-empty name; any other `assignee` value is refused as invalid
Observable: a body whose `assignee` is the empty string, is only whitespace, is not a string and not null (a number, boolean, object, array), is absent, or contains a control character (tab, line break), or a body that is not a JSON object, answers 400 with `{"error":{"code":"invalid", ...}}`, and the ticket is unchanged (no audit entry, no notification, `updated` as before). A body with a field other than `assignee` is also 400 (existing rule on unknown fields).
Source: request ("an agent is a non-empty name"); existing: docs/api.md (unknown fields refused 400), src/tickets/validate.js (text fields are trimmed, no control characters, because the command line's output is tab-separated)
Open: whether surrounding whitespace is trimmed (the existing text fields trim) or kept as given, and whether there is a maximum length (requester is limited to 64, title to 200), are not stated; the requester would settle both. A test must use only plain names without surrounding whitespace and well under 64 characters.

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: `PUT /tickets/:id/assignee` (with a name or with null) on a resolved or closed ticket answers 409 `conflict`, and the ticket's assignee, `updated`, audit log and outbox are unchanged. On an open or in-progress ticket the request is accepted (C-2, C-3).
Source: request; existing: docs/decisions/0004-error-envelope.md (a state that does not allow a request is 409, never 400)

### C-6: An unknown ticket id is 404
Observable: `PUT /tickets/T-9999/assignee` for a ticket that does not exist answers 404 `not_found`.
Source: existing: docs/api.md, errors table (no such ticket is 404)

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: answers 200 with the ticket as it was: `updated` is unchanged, no audit entry is added, no notification is enqueued.
Source: request; existing: docs/decisions/0007-append-only-audit-log.md (a request that changes nothing adds no entry)

### C-8: Unassigning a ticket that is already unassigned changes nothing
Observable: on an open or in-progress ticket with `assignee` null, `{"assignee": null}` answers 200 with the ticket unchanged: `updated` unchanged, no audit entry, no notification.
Source: choice: the request states the no-change rule only for assigning the same agent; treating the same-state unassign alike follows the existing rule for requests that change nothing (docs/api.md, PATCH)

### C-9: An assignment or unassignment that changes the ticket is recorded in the audit log
Observable: `GET /tickets/:id/audit` gains one entry for the change, with `changes` containing `assignee` as `{ "from": <previous assignee or null>, "to": <new assignee or null> }`, `actor` from the `X-Actor` header (or `system`), and `at` the change time; the entry's `seq` continues the log's numbering. The ticket's `updated` becomes the change time.
Source: implied: docs/decisions/0007-append-only-audit-log.md (every change to a ticket is recorded)
Open: the entry's `action` name is not stated (`ticket.assigned` would fit the existing naming); tests must not check it.

### C-10: The agent a ticket is assigned to is notified that it was assigned to them
Observable: after a change that assigns a ticket to agent `dana`, the outbox (`GET /admin/outbox`) holds one new pending notification addressed `to` `"dana"` for that ticket, which the worker delivers like any notification (with `NOTIFY_FILE`, one JSON line whose `to` is `dana`, with text that names the ticket's id). It is enqueued in the same step as the change, never by the request handler directly. A request that is refused (C-4, C-5, C-6) or changes nothing (C-7) enqueues none.
Source: request; existing: docs/decisions/0006-notification-outbox.md (notifications are enqueued with the change and delivered by the worker; each type needs a template, or the event goes dead)
Open: the wording of the message and the outbox `type` name are not stated; tests must not check them. Whether the agent's name is usable as a delivery address by the mail relay is not stated.

### C-11: Notifying the new agent is not lost to an earlier notification still pending
Observable: assigning T-0007 to `dana` and then, before the worker has delivered, to `eli`, leaves a pending notification `to` `dana` and one `to` `eli`; assigning T-0007 to `dana`, unassigning, and assigning to `eli` while `dana`'s is pending leaves one to `eli` too. A ticket's earlier pending notification (for example "received" to the requester, or "resolved") is unaffected, and an assignment does not suppress or replace it.
Source: implied: U-1 and docs/decisions/0006-notification-outbox.md (a pending notification with the same key swallows a later one: the key must tell assignments to different agents, and from other events, apart)

### C-12: Unassigning notifies no one
Observable: after `{"assignee": null}` on an assigned ticket, the outbox holds no new notification.
Source: choice: the request notifies only the agent assigned to; no other notification is asked for
Open: whether the previous assignee should be told they were unassigned or replaced is not stated; the requester would settle it. The loosest reading, none, is taken, and a test must not require either.

### C-13: Other changes leave the assignee as it is
Observable: `PATCH /tickets/:id` (title, priority) and `POST /tickets/:id/transition` (including to `resolved` or `closed`) do not change `assignee`; a resolved or closed ticket still shows its last assignee. `PATCH` and `POST /tickets` with an `assignee` field are still 400 (unknown field); the assignee is changed only through `PUT /tickets/:id/assignee`.
Source: implied: "Everything the service already does keeps working"; existing: docs/api.md ("Unknown fields ... are refused")

### C-14: `GET /tickets?assignee=<agent>` keeps only that agent's tickets
Observable: with tickets assigned to `dana` and `eli` and some unassigned, `?assignee=dana` lists exactly dana's tickets, in id order, paged as usual (`limit`, `cursor`, `next`). The match is on the exact name; an agent with no tickets gives `{"items":[],"next":null}`, not an error.
Source: request
Open: whether the match ignores letter case is not stated; the requester would settle it. A test must use names that differ in more than case.

### C-15: `GET /tickets?assignee=` (empty value) keeps only unassigned tickets
Observable: `?assignee=` lists exactly the tickets whose `assignee` is null, in id order, across the resolved and closed ones as well; no 400.
Source: request

### C-16: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only tickets that are open and assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent (the second case already stated in docs/api.md); `?status=open&assignee=` lists only open unassigned tickets. A ticket matching only one of two filters is not listed.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given")
Note: the current `matchesFilters` in src/tickets/query.js lists a ticket that matches any one filter, which contradicts docs/api.md; the clause states what is required.

### C-17: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js list` prints, for each ticket, its assignee's name in a column titled with the word ASSIGNEE (or equivalent heading); an unassigned ticket shows a placeholder, not the text `null` required. The existing columns remain.
Source: request
Open: the placeholder for unassigned and the column's position are not stated; tests must find the agent's name on the ticket's row and must not require a specific placeholder.

### C-18: `list --raw` keeps the positions of its existing columns
Observable: each `list --raw` line still begins with id, status, priority, title, tab-separated, in that order, so `scripts/weekly-report.js` gives the same counts as before; if an assignee column is added to raw it comes after them.
Source: existing: README.md "Command line" (`scripts/weekly-report.js` reads these columns by position)
Open: whether the raw listing shows the assignee at all is not stated ("the command-line listing" most plainly means the table); the requester would settle it.

### C-19: The assignee survives a restart, and older data files still load
Observable: with `DATA_FILE`, an assigned ticket is assigned after the service is stopped and started; the command line, reading the file, shows it. A data file written before this change (tickets without an `assignee`) loads without error, and its tickets show `"assignee": null`. A file with an `assignee` that is neither a non-empty string nor null stops the service at start with a message, like any other invalid record.
Source: existing: docs/decisions/0008-json-data-file.md (a field added to a ticket is added to persistence's record functions; the format must keep loading the previous files; loading checks every record)

### C-20: Existing behaviour and tests are preserved
Observable: `npm test` passes the existing tests unmodified together with the new ones under `test/`; the audit entry of a new ticket still lists title, priority, requester and status, not assignee; the notifications "received" and "resolved" go as before.
Source: request

## Rules and edge cases

- Who may be assigned: any non-empty single-line name; no list of known agents exists, so an unknown name is accepted (C-4). Length limit and trimming: not settled (C-4 Open).
- States: open and in-progress accept assignment and unassignment; resolved and closed refuse both with 409, including a same-agent or null-to-null request (C-5). Order of checks when a request is both malformed and on a closed ticket: not settled; tests must not combine them.
- Invalid input: empty, whitespace-only, non-string, absent key, control characters, extra fields, non-object body, all 400 (C-4); a body too large or not JSON is handled by the existing rules (docs/api.md).
- No-change cases: same agent, null to null (C-7, C-8); none changes `updated`, the log or the outbox.
- Same agent twice in a row, reassignment, assign-unassign-assign sequences: audit and notification outcomes in C-9, C-11, C-12.
- Notification dedupe: key must distinguish agents and events (C-11).
- Filters: empty value means unassigned; combine with AND; exact match (C-14 to C-16); an assignee filter is never invalid. Cursor paging with the filter uses the existing rules.
- Persistence and old files: C-19. Command line: C-17, C-18.
- Concurrency: the service handles one change at a time through the store, so two simultaneous assignments leave the last one applied, with an audit entry for each change; nothing more is required.
- Not settled by the request or the code: reassignment (C-2), whether the old agent is told (C-12), message wording (C-10), name length and trimming (C-4), case sensitivity (C-14), raw listing (C-18).
