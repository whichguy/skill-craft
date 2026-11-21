## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, so that the agent owns it
Flow: They send `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. They get 200 and the ticket, whose `assignee` is `"dana"`. Dana is notified that the ticket was assigned to them.
Source: request

### U-2: An agent or dispatcher unassigns a ticket, so that nobody owns it
Flow: They send `PUT /tickets/T-0042/assignee` with `{"assignee": null}` for an open or in-progress ticket. They get 200 and the ticket, whose `assignee` is `null`.
Source: request

### U-3: An agent finds their work, or the work nobody has taken
Flow: They call `GET /tickets?assignee=dana` and see only dana's tickets. They call `GET /tickets?assignee=` and see only unassigned tickets. They combine it with `status` or `priority` and see only tickets matching all of the filters.
Source: request

### U-4: An operator sees who holds each ticket from the command line
Flow: They run `node bin/tickets.js list` and each ticket's assignee is shown.
Source: request

### U-5: Existing callers and operators carry on unchanged
Flow: Existing requests, the weekly report, saved data files and the existing tests behave as before.
Source: request

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: For a ticket in status `open` or `in_progress`, the request answers 200 with the ticket (the same shape as `GET /tickets/:id`) whose `assignee` is the agent. A later `GET /tickets/:id` shows the same `assignee`.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For a ticket in status `open` or `in_progress` that has an assignee, the request answers 200 with the ticket whose `assignee` is `null`. A later `GET /tickets/:id` shows `null`.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: A name of 1 to 64 characters is accepted, and a name of 65 characters is refused with 400 `invalid` in the error envelope. An empty string `""` is refused with 400 `invalid`. The ticket is unchanged after a refusal. Both bounds are tested with names of exactly 64 and 65 characters.
Source: request
Open: Whether the name is trimmed first, so that `"  "` counts as empty and `" dana "` is stored as `dana`, and whether control characters are refused, as the existing `requester` check does. The existing checks in `src/tickets/validate.js` trim and refuse them, but the request does not say so for agents. The requester settles it. Tests use only plain names with no surrounding spaces and no control characters.

### C-4: A body that is not `{"assignee": <string or null>}` is refused
Observable: A body with no `assignee` field, with an `assignee` that is a number, boolean, array or object, or with an unknown extra field answers 400 `invalid` in the error envelope, and the ticket is unchanged. A body that is not a JSON object is refused as on every other endpoint.
Source: implied: the existing rules in docs/api.md that a missing or wrong field is `invalid` and that unknown fields are refused (400)

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: For a ticket in status `resolved` or `closed`, a request that would assign a different agent or unassign answers 409 `conflict` in the error envelope, and the ticket's `assignee` and `updated` are unchanged.
Source: request
Open: What a repeat request on a resolved or closed ticket answers when it asks for the value the ticket already has (the same agent, or `null` on an unassigned ticket). Tests check only a request that would change the assignee.

### C-6: A request for a ticket that does not exist is `not_found`
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for an id that does not exist, answers 404 `not_found` in the error envelope.
Source: existing: docs/api.md, errors table

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: The request answers 200 with the ticket. Its `updated` is the same as before, no new entry is added to `GET /tickets/:id/audit`, and no notification is enqueued (`GET /admin/outbox` shows no new event).
Source: request; existing: docs/api.md, "a request that changes nothing leaves [updated] as it was"

### C-8: Unassigning a ticket that has no assignee changes nothing
Observable: The request answers 200 with the ticket, `assignee` is still `null`, `updated` is the same, and no audit entry is added.
Source: implied: the same "nothing changes when nothing differs" rule that the request states for a repeated assignment and that docs/api.md states for PATCH

### C-9: Every ticket shows its `assignee`
Observable: Every ticket in `POST /tickets`, `GET /tickets/:id`, `GET /tickets` items and every response that returns a ticket has an `assignee` field, which is the agent's name or `null`. A newly created ticket has `assignee` `null`.
Source: request

### C-10: A ticket kept in a data file from before this change shows `assignee` `null`, and assignments survive a restart
Observable: With `DATA_FILE`, a ticket saved by the older service (no assignee recorded) is served after the restart with `assignee` `null`, and the service starts without error. A ticket assigned before a restart shows the same assignee after it.
Source: implied: README.md, the data file keeps state across restarts, and "Everything the service already does keeps working"

### C-11: The agent a ticket is assigned to is notified that it was assigned to them
Observable: After a change of assignee to an agent, a notification is enqueued with `to` set to that agent's name and `ticket` set to the ticket's id, and in the end it is delivered by the worker through the notifier (a line in `NOTIFY_FILE`, or in the in-memory `delivered`, whose `to` is the agent, with a `subject` and `body` that mention the ticket's id). It is visible in `GET /admin/outbox` and is not sent inside the request.
Source: request; existing: docs/decisions/0006-notification-outbox.md
Open: The type name and the wording of the notification, which the requester settles. Tests check `to`, the ticket id and that it is delivered, not the wording.

### C-12: Reassigning a ticket to a different agent notifies the new agent even while an earlier assignment notification is still pending
Observable: A ticket assigned to `dana` and then, before the worker has delivered anything, to `omar`, leaves a notification for `omar` and one for `dana`, each delivered to its own agent. The outbox's de-duplication by key must not drop the second.
Source: implied: the existing outbox keys on type and ticket (docs/decisions/0006-notification-outbox.md), so a key not made per agent would silently swallow the new agent's notification; the request says the assigned-to agent is notified

### C-13: Unassigning notifies nobody
Observable: After `{"assignee": null}`, no notification is enqueued for any agent.
Source: choice: the request notifies only "the agent a ticket is assigned to ... that it was assigned to them", and an unassignment assigns it to nobody
Open: Whether the previous agent should be told that the ticket was taken from them. The request does not ask for it, and the requester settles it.

### C-14: Each change of assignee is recorded in the audit log
Observable: After a change of assignee, `GET /tickets/:id/audit` has a new last entry whose `changes` has an `assignee` key with `from` the previous value (or `null`) and `to` the new value (or `null`), whose `actor` is the `X-Actor` header (or `system`), and whose `at` is the time of the change. The ticket's `updated` becomes that time.
Source: implied: docs/decisions/0007-append-only-audit-log.md and docs/api.md, "every change is on record"; the README says every change to a ticket is recorded
Open: The `action` name of the entry (docs/api.md lists the actions so far). Tests do not check it.

### C-15: `GET /tickets?assignee=<agent>` keeps only that agent's tickets
Observable: Only tickets whose `assignee` equals the given name are listed, in id order, in the existing page shape `{items, next}`. The match is on the whole name, exactly as given.
Source: request
Open: Whether the name is matched case-sensitively, which the request does not say. Tests use names that differ by more than case.

### C-16: `GET /tickets?assignee=` with an empty value keeps only unassigned tickets
Observable: Only tickets whose `assignee` is `null` are listed. Assigned tickets are not.
Source: request

### C-17: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only open tickets assigned to dana. `?assignee=dana&priority=high` lists only dana's high-priority tickets. `?status=open&priority=high` lists only tickets that are both open and high-priority. A ticket matching one filter but not another is not listed.
Source: request; existing: docs/api.md, "a ticket is listed only when it matches every filter given". Note: the code in `src/tickets/query.js` (`matchesFilters`) currently lists a ticket that matches any one filter, which contradicts docs/api.md. The request and the docs say every.

### C-18: The assignee filter pages like the other filters
Observable: With `assignee` and `limit`, a page holds at most `limit` matching tickets, and `next` is non-null while more matching tickets remain. Following `next` as `cursor` with the same filters walks all the matching tickets with none repeated or skipped.
Source: implied: docs/api.md, "pass it as cursor, with the same filters"

### C-19: The command-line listing shows each ticket's assignee
Observable: `node bin/tickets.js list` prints, for each ticket, its assignee's name in the table, and a recognisable placeholder in the table for an unassigned ticket, so the unassigned ticket's row is not blank in a column. The table's other columns are still shown.
Source: request
Open: The column's title, its place in the table, and the placeholder for no assignee, which the requester settles. Tests check that the name appears in the ticket's row and that an unassigned ticket's row does not show another ticket's name.

### C-20: `list --raw` keeps its columns in the positions they have
Observable: Each line of `list --raw` still has the id, status, priority and title as the 1st to 4th tab-separated columns, and `scripts/weekly-report.js` still gives the same counts for the same tickets. Any column for the assignee is added after the title and contains no tab or line break.
Source: existing: README.md, "scripts/weekly-report.js ... reads these columns by position, so they must keep their positions"
Open: Whether `--raw` shows the assignee at all. The request names "the command-line listing", and the requester settles whether that includes raw output. Tests check only that the first four columns are unchanged.

### C-21: The existing behaviour and the existing tests are unchanged
Observable: The tests in `test/` that exist now pass without being edited. `PATCH /tickets/:id` still takes only `title` and `priority`, and an `assignee` field in a PATCH or POST /tickets body is still refused as an unknown field (400).
Source: request; existing: docs/api.md, "Unknown fields in a request body are refused (400)"

### C-22: New node:test tests cover the new behaviour and run under `npm test`
Observable: `npm test` runs the new test files under `test/` along with the existing ones, and they pass.
Source: request
