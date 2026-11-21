## Use cases

### U-1: A help-desk agent takes a ticket, to show it is theirs to work
Flow: Calls `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}` on an open or in-progress ticket. Gets 200 and the ticket with `"assignee": "dana"`. Dana is notified that the ticket was assigned to her/them.
Source: request

### U-2: A lead hands a ticket to someone else or takes it back, to keep the queue accurate
Flow: Calls the same endpoint with another agent's name (the ticket now shows that agent) or with `{"assignee": null}` (the ticket shows `"assignee": null`). Sending the value the ticket already has changes nothing.
Source: request

### U-3: An agent finds their work, or the unassigned work
Flow: Calls `GET /tickets?assignee=dana` and sees only Dana's tickets; calls `GET /tickets?assignee=` and sees only unassigned tickets; combines with `status`/`priority` and sees only tickets matching all of them.
Source: request

### U-4: An operator sees who has each ticket on the command line
Flow: Runs `node bin/tickets.js list` (or `list --raw`) and sees each ticket's assignee.
Source: request

### U-5: An existing client or operator keeps working as before
Flow: Creates, changes, transitions, lists, audits tickets, reads notifications, runs the CLI/weekly report and restarts the service with a data file exactly as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For a ticket with status `open` or `in_progress` and a valid agent, the response is 200 with the whole ticket, whose `assignee` is the agent exactly as given (after any normalisation C-6 allows); a later `GET /tickets/:id` shows the same.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For a ticket with status `open` or `in_progress`, the response is 200 with the ticket whose `assignee` is `null`; a later `GET /tickets/:id` shows `null`.
Source: request

### C-3: An agent is a non-empty string of at most 64 characters
Observable: An `assignee` of `""`, of 65 characters, or of a type other than string or null (number, boolean, array, object) gets 400 `invalid` in the error envelope and the ticket is unchanged; a name of exactly 1 and exactly 64 characters is accepted.
Source: request
Open: Whether surrounding whitespace is trimmed, a whitespace-only name counts as empty, and control characters (tab, line break) are refused. Existing text fields trim and refuse control characters (`src/tickets/validate.js`); the requester decides if agent names follow that rule. Tests check only the clear cases above.

### C-4: The body must be a JSON object with an `assignee` field and no other field
Observable: A body that is not a JSON object, lacks `assignee`, or has any other field gets 400 `invalid`; the ticket is unchanged.
Source: implied: docs/api.md "Unknown fields in a request body are refused (400)" and the existing endpoints' body checks
Open: Which of the 400 checks wins when a ticket is both malformed-request and in a state that refuses assignment (400 vs 409). Tests must not depend on it.

### C-5: An unknown ticket id on the assignee endpoint is 404 `not_found`
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for a ticket that does not exist, gets 404 with code `not_found`.
Source: existing: docs/api.md (errors table, "Get a ticket")

### C-6: Only open and in-progress tickets can be assigned or unassigned; resolved and closed tickets are refused
Observable: A `PUT` that would change the assignee of a `resolved` or `closed` ticket (assign to an agent other than the current one, or unassign an assigned ticket) gets 409 `conflict` in the error envelope, and the ticket's `assignee` and `updated` are unchanged.
Source: request; the 409 follows existing: CONTRIBUTING.md ("the ticket's state does not allow this is a conflict (409)")
Open: What a `PUT` that would change nothing (same agent, or null on an unassigned ticket) does on a resolved or closed ticket: 200 unchanged, or 409. The request states both rules without ordering them; the requester decides. Tests do not check it.

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: Repeating the same `PUT` on an open or in-progress ticket answers 200 with the ticket; its `updated` value is unchanged, its audit history gains no entry, and no new notification is enqueued (`GET /admin/outbox` shows no additional event).
Source: request; the no-audit/no-notification/`updated` parts follow existing: docs/api.md ("a request that changes nothing leaves [updated] as it was") and CONTRIBUTING.md ("A change that changes nothing is not a change: no audit entry, no notification")

### C-8: Unassigning an already unassigned open or in-progress ticket changes nothing
Observable: `{"assignee": null}` on an open or in-progress ticket with `assignee` null answers 200, `updated` is unchanged and no audit entry is added.
Source: implied: C-7 and CONTRIBUTING.md ("a change that changes nothing is not a change")

### C-9: Every ticket shows `assignee`, `null` when unassigned
Observable: Every ticket object returned by `POST /tickets` (201), `GET /tickets/:id`, `GET /tickets` items, `PATCH`, `transition` and the assignee endpoint has an `assignee` field: `null` for a new ticket and for any never-assigned or unassigned ticket, otherwise the agent's name.
Source: request

### C-10: A real assignment change updates the ticket's `updated` time
Observable: After a `PUT` that changes the assignee, the ticket's `updated` is the time of the change (not earlier than before it).
Source: implied: docs/api.md `updated` "when it last changed"

### C-11: A real assignment change is recorded in the audit log
Observable: After a `PUT` that changes the assignee, `GET /tickets/:id/audit` gains exactly one entry at the end, for that ticket, whose `changes` has an `assignee` key with `{from, to}` (previous and new value, `null` for none) and no other key, whose `actor` is the `X-Actor` header value or `system` without it. Earlier entries are unchanged.
Source: implied: README.md ("every change is on record"), docs/api.md (audit log, `X-Actor`), CONTRIBUTING.md ("Every change to a ticket ... appends the audit entry")
Open: The entry's `action` name (e.g. `ticket.assigned`). Tests accept any action name for the new entry.

### C-12: The agent a ticket is assigned to is notified that it was assigned to them
Observable: After a `PUT` that assigns a ticket to agent A (from unassigned or from another agent), a notification addressed to A, naming the ticket's id, is enqueued in the outbox and, once the worker runs, delivered to the notifier (a line in `NOTIFY_FILE` with `to` equal to A and `ticket` equal to the ticket id). The notification can be delivered, not dead for lack of a template.
Source: request
Open: The notification's `type` name, subject and wording, and how an agent name maps to an address (`to` is the agent's name as given unless the requester says otherwise).

### C-13: Assigning to agent B while an earlier assignment notification (to A or to B) is still pending does not lose B's notification
Observable: With the worker off (`WORKER_INTERVAL_MS=0`), assign a ticket to A, then to B: the outbox holds a pending notification addressed to B for that ticket (in addition to A's). Assign A, then B, then A again before delivery: A is notified again for the second assignment or is still covered by one pending notification to A; no agent's most recent assignment is left without a pending or sent notification to them.
Source: implied: C-12 with existing: docs/operations.md and src/outbox.js (a pending notification with the same key swallows a later one; the default key is type and ticket)

### C-14: Unassigning notifies nobody
Observable: After `{"assignee": null}` on an assigned ticket, no new outbox event is added.
Source: choice: the request asks only for notification of the agent assigned to; adding one on unassign is not requested

### C-15: A rejected assignment (400, 404, 409) changes nothing and notifies nobody
Observable: After any refused `PUT`, the ticket (including `assignee` and `updated`), its audit history and the outbox are as before.
Source: implied: CONTRIBUTING.md ("Changes go through the store ... no change is ever half recorded")

### C-16: `GET /tickets?assignee=<agent>` keeps only that agent's tickets
Observable: Only tickets whose `assignee` equals `<agent>` exactly are listed; an agent with no tickets, or a name no ticket has, yields `{"items": [], "next": null}` with 200 (no 400).
Source: request; the empty-result outcome is choice: the request names no validity rule for the filter value, unlike `status`/`priority`
Open: Whether matching ignores letter case; exact (case-sensitive) matching is assumed and tests use names differing by more than case.

### C-17: `GET /tickets?assignee=` (empty value) keeps only unassigned tickets
Observable: With `?assignee=`, items are exactly the tickets whose `assignee` is `null`; tickets with an agent are absent.
Source: request

### C-18: A ticket is listed only when it matches every filter given
Observable: `?status=open&assignee=dana` lists only tickets that are open and Dana's; `?status=open&priority=urgent` lists only tickets that are both open and urgent (a ticket matching only one of them is not listed); `?assignee=&priority=high` lists only unassigned high-priority tickets.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given"). Note: `matchesFilters` in src/tickets/query.js currently keeps a ticket matching ANY filter (`some`), contradicting the documented rule; it must be AND.

### C-19: The assignee filter works with pagination
Observable: With `assignee` (including empty) and `limit`, pages follow `{items, next}` in id order; passing `next` as `cursor` with the same filters yields the following matching tickets, with none missed or repeated.
Source: implied: docs/api.md ("pass it as cursor, with the same filters")

### C-20: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` prints, for each ticket, the assignee's name; a header names the column; existing columns stay.
Source: request
Open: The header text and how an unassigned ticket is shown (blank, `-`, ...); the requester decides. Tests check only that an assigned ticket's row contains the agent's name, not how an unassigned ticket is shown.

### C-21: `list --raw` keeps its first four columns in place and shows the assignee after them
Observable: Each raw line is tab-separated with id, status, priority, title as columns 1–4 exactly as now; the assignee, when assigned, is the 5th column. `scripts/weekly-report.js` gives the same counts as before.
Source: implied: README.md ("scripts/weekly-report.js ... reads these columns by position, so they must keep their positions") and src/format.js `RAW_COLUMNS`
Open: How an unassigned ticket's 5th column appears (empty or a placeholder).

### C-22: The assignee survives a restart with a data file, and a data file from before this change still loads
Observable: With `DATA_FILE` set, assign, stop and restart the service: the ticket still shows the agent. A data file whose tickets have no `assignee` field loads without error and those tickets show `"assignee": null`. The command line reads the assignee from the data file.
Source: implied: README.md/docs/operations.md (state kept across restarts; at start a file the service cannot use stops it) and src/persistence.js (every ticket field is named in `ticketRecord`)

### C-23: Other changes leave the assignee alone
Observable: `PATCH` (title/priority) and `transition` on an assigned ticket (including to `resolved` or `closed`, and reopening) keep `assignee` as it was; `PATCH` with an `assignee` field is still 400 (unknown field).
Source: implied: no sentence of the request asks that any other change touches the assignee; existing: docs/api.md (unknown fields refused)
Open: Whether resolving/closing a ticket should clear its assignee is not asked and not decided.

### C-24: The assignee endpoint answers other methods as the existing router does
Observable: `GET /tickets/T-0001/assignee` gets 404 `not_found` in the envelope, as other unsupported method/path pairs do.
Source: existing: src/app.js (`notFound`), docs/api.md

## Preserved behaviour

Each of these must not change (the existing tests in `test/` keep passing unmodified):

- Error envelope `{"error": {"code", "message"}}` with codes `invalid` 400, `not_found` 404, `conflict` 409, `internal` 500 (docs/api.md, src/errors.js, decision 4).
- Ticket ids, id-ordered cursor pages with `limit` 1–100 (default 20), `status` and `priority` filters and their 400 on bad values, a bad cursor 400 (src/tickets/query.js, docs/api.md, test/query.test.js).
- Creating a ticket answers 201, status `open`, requester notified `ticket.created`; resolving notifies the requester; the `ticket.created` audit entry lists the fields title, priority, requester, status (src/store.js `CREATED_FIELDS`) — these are not changed by this work.
- `PATCH` rules (closed ticket 409, no-op changes nothing) and the lifecycle `open→in_progress→resolved→closed`, `resolved→open` (src/tickets/states.js).
- The audit log is append-only and keeps its existing actions; `X-Actor` handling (src/audit.js, docs/api.md).
- The outbox: keyed de-duplication of pending events for existing notification types, retries and dead handling, `GET /admin/outbox` shape (src/outbox.js, docs/operations.md). Handlers never call the notifier; notifications go only through the outbox and the worker (CONTRIBUTING.md); `WORKER_INTERVAL_MS=0` stops delivery.
- Data file format: existing fields stay, loads of old files succeed (src/persistence.js); the service stays dependency-free (CONTRIBUTING.md, package.json).
- CLI: `list --status/--priority/--raw`, `show`, exit codes 0/1/2, read-only access to the data file; `list --raw` columns 1–4 (README.md, bin/tickets.js, src/format.js, scripts/weekly-report.js).
- `GET /health`, `GET /admin/outbox`, request body limit, unknown-field refusal.
- Not settled by what is here: whether `show` on the command line should display the assignee, and whether the CLI `list` gets an `--assignee` filter. Neither is asked; they are left as they are today.
