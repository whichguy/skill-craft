# Specification: ticket assignment

## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, so the agent knows it is theirs to work
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` (optionally with `X-Actor`). Sees 200 and the ticket with `"assignee": "dana"`. The agent `dana` is notified that the ticket was assigned to them.
Source: request

### U-2: A dispatcher unassigns a ticket, so it is back in the pool
Flow: Sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. Sees 200 and the ticket with `"assignee": null`.
Source: request

### U-3: A dispatcher or agent lists tickets by assignee, to see an agent's work or the unassigned queue
Flow: `GET /tickets?assignee=dana` lists dana's tickets. `GET /tickets?assignee=` lists the unassigned tickets. `GET /tickets?status=open&assignee=dana` lists dana's open tickets only.
Source: request

### U-4: An operator reads each ticket's assignee on the command line
Flow: Runs `node bin/tickets.js --data FILE list` (or `list --raw`) and sees each ticket's assignee.
Source: request

### U-5: An existing client or operator keeps using the service as before
Flow: Creates, lists, changes and transitions tickets, reads audit and outbox, restarts with a data file, runs the weekly report; all behave as before, and tickets also show `assignee`.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: Assigning an open or in-progress ticket sets its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": "dana"}` on a ticket whose status is `open` or `in_progress` answers 200 with the ticket, whose `assignee` is `"dana"`; `GET /tickets/:id` then also shows `"dana"`. Assigning a different agent to an already-assigned ticket replaces the assignee.
Source: request

### C-2: Unassigning an open or in-progress ticket clears its assignee
Observable: `PUT /tickets/:id/assignee` with `{"assignee": null}` on an `open` or `in_progress` ticket answers 200 with the ticket whose `assignee` is `null`; `GET` then also shows `null`.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: `{"assignee": "x"}` and an assignee of exactly 64 characters are accepted (200). An assignee of 65 characters, `""`, and a string of only whitespace are answered 400 `invalid` in the error envelope, and the ticket is unchanged with no notification.
Source: request (bound 64 and non-empty); choice: whitespace-only counts as empty, following `text()` in src/tickets/validate.js, which trims and then checks
Open: whether leading/trailing whitespace is trimmed before storing (as `title` and `requester` are) or kept. Decided by the requester; a build may do either, and tests must not depend on it.

### C-4: A body that is not a valid assignment is refused
Observable: Answered 400 `invalid`, ticket unchanged, no notification, for: a body without `assignee`; an `assignee` that is neither a string nor null (a number, boolean, object, array); a body with any other field (`{"assignee":"dana","x":1}`); a body that is not a JSON object.
Source: implied: "Unknown fields in a request body are refused (400)" and the body-must-be-object rule in docs/api.md; a missing or wrong-type field is `invalid` there too

### C-5: An assignee containing a control character (tab, line break) is refused
Observable: `{"assignee": "da\tna"}` and `{"assignee": "a\nb"}` are answered 400 `invalid` and nothing changes.
Source: implied: the command line's tab-separated output (README.md "Command line", the `CONTROL` rule in src/tickets/validate.js) must not be broken by an assignee shown in it

### C-6: Only open and in-progress tickets can be assigned or unassigned
Observable: For a ticket whose status is `resolved` or `closed`, a `PUT .../assignee` with a name or with `null` is answered 409 `conflict` in the envelope; its assignee, `updated`, audit log and outbox are unchanged. The statuses that allow it are exactly `open` and `in_progress`.
Source: request; existing: src/errors.js and CONTRIBUTING.md ("the ticket's state does not allow this" is a 409)

### C-7: An unknown ticket id is 404
Observable: `PUT /tickets/T-9999/assignee` with a valid body, where no such ticket exists, answers 404 `not_found` in the envelope.
Source: existing: docs/api.md Errors table

### C-8: Assigning the agent a ticket already has changes nothing
Observable: A second `PUT` with the same name answers 200 with the ticket; `updated` stays as it was, no audit entry is added, and no notification is enqueued.
Source: request; existing: docs/api.md ("a request that changes nothing leaves `updated` as it was"), CONTRIBUTING.md

### C-9: Unassigning an already-unassigned ticket changes nothing
Observable: `{"assignee": null}` on an open ticket with no assignee answers 200 with the ticket; `updated` unchanged, no audit entry, no notification.
Source: choice: the same "a change that changes nothing is not a change" rule (CONTRIBUTING.md) applied to the request's null case, which the request does not spell out

### C-10: Every ticket shows its assignee
Observable: Every ticket in every response (create, get, list items, patch, transition, assignee) has an `assignee` field: `null` for a ticket never assigned, including a new one, else the agent's name.
Source: request

### C-11: A real assignment notifies the new assignee
Observable: After a `PUT` that changes the assignee to `"dana"`, the outbox (`GET /admin/outbox`) holds a notification whose `to` is `"dana"`, whose `ticket` is the ticket's id and whose type tells it is an assignment; once the worker runs, the notifier delivers it to `dana`. Its text tells the agent that the ticket was assigned to them and names the ticket.
Source: request
Open: the notification's type name, subject and wording are not specified; the requester may fix them. Tests may check only `to`, `ticket` and that it is distinct from `ticket.created` / `ticket.resolved`.

### C-12: Reassigning notifies the new agent even when an earlier assignment notification is still pending
Observable: With the worker off, assigning a ticket to `"dana"` and then to `"sam"` leaves a pending notification to `sam` for that ticket (the one to `dana` may remain). The outbox's dedupe by key (src/outbox.js) must not swallow it.
Source: implied: "The agent a ticket is assigned to is notified"; existing: src/outbox.js (a pending event with the same key hides a new one, and the default key is type plus ticket)

### C-13: Unassigning, a no-op, or a refused request sends no notification
Observable: After `{"assignee": null}`, after a repeated same-name assignment, and after any 400/404/409 answer, the outbox holds no new event.
Source: request ("the agent a ticket is assigned to is notified that it was assigned to them" names assignment only); choice: nothing is asked for on unassignment
Open: whether the previous assignee should be told when unassigned or reassigned away; not asked for, so not required, the requester may add it.

### C-14: A real assignment change is audited
Observable: After a change of assignee, `GET /tickets/:id/audit` has a new last entry whose `changes` contains `assignee` with `from` (previous name or null) and `to` (new name or null), whose `actor` is the `X-Actor` header (or `system`), and the ticket's `updated` is the time of the change.
Source: implied: existing: CONTRIBUTING.md / docs/decisions/0007-append-only-audit-log.md ("every change to a ticket" is audited, through the store)
Open: the entry's `action` name is not fixed (the existing ones are `ticket.created`, `ticket.updated`, `ticket.transitioned`); tests must not check it.

### C-15: A change of assignee, its audit entry and its notification happen together and survive restart
Observable: With `DATA_FILE` set, after an assignment the file holds the assignee, the audit entry and the pending notification; after restarting the service the ticket still shows the assignee, the audit entry and the notification remain.
Source: implied: existing: README.md ("saves the data file in one step"), src/persistence.js, which lists the ticket's fields by name and would otherwise drop `assignee`

### C-16: A data file written before this change loads, with every ticket unassigned
Observable: A data file whose tickets have no `assignee` field loads without error and each such ticket shows `"assignee": null`; it is saved with the field after the next change.
Source: implied: "Everything the service already does keeps working"; existing: docs/operations.md and src/persistence.js (the file format is versioned and validated at start)

### C-17: `GET /tickets?assignee=<agent>` keeps that agent's tickets
Observable: Only tickets whose `assignee` equals the value exactly are listed (in id order, as pages with `next`); an agent nobody is assigned to gives `{"items": [], "next": null}`. The value is not checked against the 64-character limit.
Source: request; choice: exact comparison
Open: whether the match ignores case; the requester decides. Tests use names that differ by more than case.

### C-18: `GET /tickets?assignee=` (empty) keeps the unassigned tickets
Observable: Lists exactly the tickets whose `assignee` is `null`. It is not an error and not "no filter".
Source: request

### C-19: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only open tickets assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent. A ticket that matches one filter but not the other is not listed. The same holds with `limit` and `cursor` across pages.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given"). Today `matchesFilters` in src/tickets/query.js lists a ticket matching any one filter, which contradicts the document; this clause makes the document true.

### C-20: The command-line listing shows each ticket's assignee
Observable: `bin/tickets.js list` prints the assignee name of each assigned ticket in the table (under an `ASSIGNEE` heading, or one that says so), and something that is not a name for an unassigned ticket. `list --raw` carries the assignee too.
Source: request
Open: how an unassigned ticket looks (blank, `-`, ...) and where in the table. Tests check only that an assigned ticket's row contains its agent's name and that an unassigned ticket's row contains no agent name.

### C-21: `list --raw` keeps columns 1–4 in place
Observable: Each `list --raw` line still has id, status, priority, title as its first four tab-separated columns; anything new comes after them, so `scripts/weekly-report.js` gives the same counts as before.
Source: existing: README.md "Command line", scripts/weekly-report.js

### C-22: The command-line `list` with `--status` / `--priority` filters, and `show`, work as before
Observable: `list --status open`, `list --priority urgent` (both together: only tickets matching both, per C-19), `list --raw`, `show ID` and the exit codes 0/1/2 behave as today. `show` may also display the assignee.
Source: existing: bin/tickets.js, README.md

### C-23: Creating, patching and transitioning tickets work as before
Observable: `POST /tickets`, `PATCH /tickets/:id` (a closed ticket still 409), `POST /tickets/:id/transition`, audit and outbox behave as in docs/api.md; creating still notifies the requester (`ticket.created`) and resolving still notifies the requester (`ticket.resolved`). Transitioning or patching an assigned ticket leaves its assignee as it is, and `PATCH` still refuses an `assignee` field (unknown field, 400): assignment goes only through the new endpoint.
Source: existing: docs/api.md, src/tickets/validate.js; request ("keeps working")
Open: whether resolving or closing a ticket should clear its assignee; the request says nothing, so it stays.

### C-24: Existing tests pass unchanged and the new behaviour has tests
Observable: `npm test` passes with every file already in test/ unmodified, and with new `node:test` files under test/ covering the clauses above.
Source: request

### C-25: No dependencies are added
Observable: `package.json` lists no `dependencies`; the service runs on Node's standard library.
Source: existing: CONTRIBUTING.md, README.md

## Preserved behaviour

- Error envelope `{"error": {"code", "message"}}` with 400/404/409/500 (src/errors.js, docs/api.md): C-3 to C-7 use it.
- Ticket ids, id-ordered cursor pages (`items`, `next`), page limits 1–100, default 20; invalid `status`/`priority` filter values are 400 (src/tickets/query.js, test/query.test.js). Unknown query parameters are still ignored.
- `status`/`priority` filter semantics for a single filter (test/query.test.js, test/api.test.js); only the combination changes (C-19).
- Unknown body fields refused; `X-Actor` recorded, `system` default, at most 64 characters (src/http.js).
- A change that changes nothing leaves `updated`, audit and outbox alone (docs/api.md, CONTRIBUTING.md).
- Changes only through the store; handlers never call the notifier; notifications go through the outbox, delivered by the worker; `WORKER_INTERVAL_MS=0` stops it (CONTRIBUTING.md, decision 6).
- Lifecycle table (src/tickets/states.js) and closed being final; PATCH refuses closed tickets (docs/api.md).
- Data file validated at start, and old files still load (src/persistence.js, docs/operations.md): C-16.
- The command line only reads and never writes the data file; `list --raw` column positions (README.md, scripts/weekly-report.js).
- `/health`, `/admin/outbox` unchanged (docs/api.md). Existing tests (test/*.test.js) must pass as they are.
- Not settled by what is here: whether the shape of a ticket stored in the data file is relied upon by outside tools (the mail relay reads NOTIFY_FILE lines, whose shape is unchanged); docs/api.md, README.md and CHANGELOG.md are not required by the request to be updated.
