## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, to get it worked by that person
Flow: They send `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` (optionally with an `X-Actor` header). They get 200 and the ticket, whose `assignee` is `"dana"`. Dana is notified that the ticket was assigned to them. The change is in the ticket's audit history.
Source: request

### U-2: An agent or dispatcher takes a ticket off someone, to leave it unowned
Flow: They send `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. They get 200 and the ticket with `assignee` null.
Source: request

### U-3: A client repeats or mistakes an assignment and is not harmed or misled
Flow: They send the assignment the ticket already has and get 200 with the ticket unchanged (nobody is notified again). They send an assignment for a resolved or closed ticket, or with a bad agent name, and get an error in the service's usual envelope; nothing changes.
Source: request; implied: by "Everything the service already does keeps working" (error envelope, no-change rule in CONTRIBUTING.md)

### U-4: A dispatcher or agent lists tickets by assignee, to see a person's queue or the unassigned queue
Flow: `GET /tickets?assignee=dana` lists dana's tickets; `GET /tickets?assignee=` lists the unassigned ones; `GET /tickets?status=open&assignee=dana` lists dana's open tickets. Each item shows its `assignee`.
Source: request

### U-5: An operator reads the assignee on the command line
Flow: They run `node bin/tickets.js --data FILE list` and see each ticket's assignee. The weekly report script keeps working.
Source: request; existing: README.md "Command line"

### U-6: An assigned agent hears about it
Flow: After the assignment, the outbox (and the `NOTIFY_FILE`, once the worker runs) holds a notification addressed to that agent that names the ticket.
Source: request; existing: docs/decisions/0006-notification-outbox.md

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For an `open` or `in_progress` ticket T-0001, `PUT /tickets/T-0001/assignee` with `{"assignee":"dana"}` answers 200 with the whole ticket, `assignee` `"dana"`, `updated` set to the time of the change; a later `GET /tickets/T-0001` and `GET /tickets` show `"dana"`. Assigning to a different agent replaces the previous one.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For an `open` or `in_progress` ticket assigned to dana, `PUT` with `{"assignee":null}` answers 200 with the ticket, `assignee` null; later reads show null.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: A name of 1 character and a name of exactly 64 characters are accepted (200). The empty string `""` and a name of 65 characters are refused with 400 `invalid` in the error envelope, and the ticket is unchanged. Names are compared exactly, character for character, when deciding "the agent it already has" and when filtering.
Source: request; existing: docs/decisions/0004-error-envelope.md
Open: Whether surrounding whitespace is trimmed before the 64-character count, whether a whitespace-only name counts as empty, and whether control characters are refused (existing `requester` and `title` trim and refuse both, in src/tickets/validate.js) are not stated by the request; the requester decides. Tests check only the bounds above with plain names.

### C-4: A body that is not a usable assignment is refused as `invalid`
Observable: A body whose `assignee` is missing, is neither a string nor null (a number, boolean, array or object), or that carries any other field answers 400 `invalid` and changes nothing. A body that is not a JSON object is 400 `invalid`, as on every endpoint.
Source: implied: by "Unknown fields in a request body are refused (400)" and the 400 rule in docs/api.md

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: For a ticket whose status is `resolved` or `closed`, `PUT` of an agent name and `PUT` of `null` each answer 409 `conflict` in the error envelope, and the ticket's `assignee`, `updated`, audit history and outbox are unchanged. Applies even when the request would change nothing (null on an unassigned resolved ticket).
Source: request; existing: CONTRIBUTING.md ("the ticket's state does not allow this" is 409)
Open: When a request is both invalid (C-3, C-4) and aimed at a resolved or closed ticket, which error wins (400 or 409) is not stated; the requester decides. Tests use a valid body for the 409 case and an open ticket for the 400 case.

### C-6: An unknown ticket id is 404
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for a ticket that does not exist, answers 404 `not_found` in the envelope.
Source: existing: docs/api.md Errors

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: Repeating `{"assignee":"dana"}` on a ticket already assigned to dana answers 200 with the ticket exactly as before (same `updated`), adds no audit entry, and enqueues no notification. The same holds for `{"assignee":null}` on an unassigned open or in-progress ticket.
Source: request; existing: CONTRIBUTING.md ("A change that changes nothing is not a change"), docs/decisions/0007-append-only-audit-log.md

### C-8: Every ticket shows its `assignee`, null when unassigned
Observable: Every ticket in `POST /tickets` (201), `GET /tickets/:id`, `GET /tickets` items, `PATCH` and `transition` responses has an `assignee` field: null for a new ticket and for any ticket never assigned (including tickets loaded from a data file saved before this change); otherwise the agent's name. Moving a ticket to `resolved` or `closed`, or patching its title or priority, leaves its `assignee` as it was.
Source: request

### C-9: A real change of assignee is written to the audit log
Observable: Assigning ticket T-0001 to dana from null adds one entry to `GET /tickets/T-0001/audit` whose `actor` is the `X-Actor` header (`system` without it) and whose `changes` contains `assignee` `{ "from": null, "to": "dana" }`; reassigning to eve gives `{ "from": "dana", "to": "eve" }`; unassigning gives `{ "from": "eve", "to": null }`. A ticket's creation entry is unchanged (its `changes` still list exactly title, priority, requester, status).
Source: implied: by docs/decisions/0007-append-only-audit-log.md ("every change to a ticket" is audited)
Open: The entry's `action` name is not fixed by the request; any non-empty string is acceptable and tests do not check it.

### C-10: The agent a ticket is assigned to is notified, through the outbox
Observable: After a change that assigns T-0001 to dana, `GET /admin/outbox` lists a notification with `to` `"dana"` and `ticket` `"T-0001"`, enqueued in the same step as the change (visible with `WORKER_INTERVAL_MS=0`, before any worker run). When the worker runs it is delivered (status `sent`, one line in `NOTIFY_FILE` with that `to`), not dead for want of a template; its rendered text names the ticket id. The request itself does not wait on or fail because of delivery.
Source: request; existing: docs/decisions/0006-notification-outbox.md, CONTRIBUTING.md (templates, handlers never call the notifier)

### C-11: Only the newly assigned agent is notified
Observable: Unassigning a ticket enqueues no notification. Reassigning from dana to eve enqueues a notification to eve and none to dana. A refused request (400, 404, 409) and a no-change request (C-7) enqueue nothing.
Source: request ("notified that it was assigned to them"); implied: by C-7

### C-12: A pending notification never swallows a different assignment's notification
Observable: With the worker off, assigning T-0001 to dana and then to eve leaves a pending notification to eve (and the one to dana may remain); assigning T-0001 to dana and T-0002 to dana leaves one pending notification per ticket. The outbox's key deduplication (default key is type plus ticket) must not drop a notification for a different agent or ticket.
Source: implied: by the request ("the agent ... is notified") and existing: docs/decisions/0006-notification-outbox.md (key deduplication)
Open: Whether assigning to dana, unassigning and assigning to dana again while the first notification is still pending yields one or two notifications to dana is not stated; either is acceptable and tests do not check it.

### C-13: The assignment survives a restart
Observable: With `DATA_FILE` set, after assigning T-0001 to dana and restarting the service on the same file, `GET /tickets/T-0001` shows `"dana"`; unassigned tickets stay null. A data file saved before this change (tickets without `assignee`) still loads and shows null for each ticket. The command line, which reads the same file, shows the assignee.
Source: implied: by README.md (the data file keeps the state across restarts) and U-5

### C-14: `GET /tickets?assignee=<agent>` keeps that agent's tickets
Observable: `GET /tickets?assignee=dana` lists exactly the tickets assigned to dana, in id order, paged with `limit`/`cursor` as before; an agent with no tickets gives `{"items":[],"next":null}`, not an error. The match is exact.
Source: request

### C-15: An empty `assignee=` keeps the unassigned tickets
Observable: `GET /tickets?assignee=` lists exactly the tickets whose `assignee` is null (and not the assigned ones), and answers 200, not 400.
Source: request

### C-16: A ticket must match every filter given
Observable: With T-0001 open+dana, T-0002 open+eve, T-0003 in_progress+dana: `?status=open&assignee=dana` lists only T-0001; `?assignee=dana&priority=high` lists only dana's high-priority tickets; `?status=open&assignee=` lists only open unassigned tickets. This holds for status and priority together too (`?status=open&priority=urgent` lists open tickets that are urgent), as docs/api.md already says; a ticket matching only one of the filters is not listed.
Source: request; existing: docs/api.md "List tickets" (the current code in src/tickets/query.js `matchesFilters` keeps a ticket that matches any one filter, which contradicts both and must be corrected)

### C-17: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` prints a table with an assignee column (header and one value per ticket): the agent's name for an assigned ticket, and a placeholder for an unassigned one; the other columns keep their existing values.
Source: request
Open: The column's header, its position in the table and the placeholder text for "unassigned" are not stated; the requester decides. Tests check only that an assigned ticket's line contains the name and that an unassigned ticket's line has no agent name in that place.

### C-18: `list --raw` keeps its first four columns in place
Observable: Each `list --raw` line still has id, status, priority and title as tab-separated columns 1 to 4, so `scripts/weekly-report.js` (and `--json`) gives the same counts as before.
Source: existing: README.md "Command line" (columns must keep their positions)
Open: Whether `list --raw` also carries the assignee (as a further column after the title) is not stated; "the command-line listing" most plausibly means the table. Tests check only columns 1 to 4.

### C-19: Existing behaviour is preserved
Observable: Everything else in docs/api.md behaves as before: PATCH still refuses an `assignee` field (400 unknown field); status and priority filters, validation errors, pagination, transitions, the resolved notification and the created notification are unchanged; the existing tests under `test/` pass unmodified.
Source: request

### C-20: New behaviour has node:test tests under `test/`
Observable: `npm test` (`node --test`) runs new test files or cases under `test/` covering the assignment endpoint, the filter and the command-line listing, together with the existing tests, and all pass.
Source: request

### C-21: The `X-Actor` rules apply to the assignment endpoint
Observable: `PUT /tickets/:id/assignee` records the `X-Actor` header (trimmed) as the audit actor, `system` when absent or blank; an `X-Actor` longer than 64 characters is 400 `invalid` and changes nothing.
Source: existing: docs/api.md Conventions ("The actor"), src/http.js `actorOf`

### C-22: A listing filter with an empty value stays refused for `status` and `priority`
Observable: `GET /tickets?status=` and `GET /tickets?priority=` still answer 400 `invalid`; only `assignee=` with an empty value is meaningful (C-15). Query parameters the listing does not know are still ignored. A value of `assignee` that names nobody (`assignee=nobody`, or one longer than 64 characters) is not an error: it lists nothing.
Source: existing: test/query.test.js, src/tickets/query.js

### C-23: A resolved ticket can still be patched; only assignment is refused for resolved
Observable: `PATCH /tickets/:id` on a `resolved` ticket still changes its title or priority (200), and is refused (409) only for `closed`, as today; the 409 of C-5 for `resolved` applies to the assignee endpoint only.
Source: existing: src/store.js `update`, docs/api.md "Change a ticket"

### C-24: A data file whose ticket carries an unusable assignee is refused at load
Observable: A data file in which a ticket's `assignee` is present and is neither null nor a non-empty string (for example a number or `""`) is refused with the data-file error naming the field, and the service does not start; a ticket with no `assignee` or with null loads as unassigned. Every other refusal of the data file is unchanged.
Source: existing: src/persistence.js ("Loading checks each record"), docs/decisions/0008-json-data-file.md

### C-25: `show` and the audit entries print as before, with the new field added
Observable: `node bin/tickets.js show ID` still prints the ticket's existing lines and its history; a history line for an assignment reads with the existing `field from -> to` pattern. Exit codes and usage of the command line (0, 1 no such ticket, 2 usage or data file) are unchanged; `list --status`, `--priority` and `--raw` still work.
Source: existing: bin/tickets.js, src/format.js, README.md "Command line"
