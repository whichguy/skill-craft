## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, to say who works it
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket. Sees 200 and the ticket with `"assignee": "dana"`. The agent `dana` is notified that the ticket was assigned to them.
Source: request

### U-2: A dispatcher unassigns a ticket, to return it to the pool
Flow: Sends `PUT /tickets/T-0042/assignee` with `{"assignee": null}`. Sees 200 and the ticket with `"assignee": null`.
Source: request

### U-3: An agent lists their own tickets, or the unassigned ones, to know what to work on
Flow: Requests `GET /tickets?assignee=dana` and sees only dana's tickets; requests `GET /tickets?assignee=` and sees only unassigned tickets; combines with `status`/`priority`, and sees only tickets matching all filters given.
Source: request

### U-4: An operator reads each ticket's assignee on the command line
Flow: Runs `node bin/tickets.js list` and sees each ticket's assignee in the table.
Source: request

### U-5: An existing client or operator keeps working unchanged
Flow: Existing endpoints, the data file, the weekly report and the existing tests behave as before, apart from what the request changes.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: PUT /tickets/:id/assignee with a valid agent name assigns an open or in-progress ticket
Observable: For a ticket with status `open` or `in_progress`, `PUT /tickets/:id/assignee` with `{"assignee": "dana"}` answers 200 with the ticket, whose `assignee` is `"dana"`; a later `GET /tickets/:id` shows `"assignee": "dana"`.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: For an `open` or `in_progress` ticket that has an assignee, `PUT` with `{"assignee": null}` answers 200 with the ticket whose `assignee` is `null`; a later GET shows null.
Source: request

### C-3: An agent is a non-empty name of at most 64 characters
Observable: `{"assignee": "<1 to 64 characters>"}` is accepted; `""` and a 65-character name are answered 400 with code `invalid` in the error envelope, and the ticket's assignee is unchanged.
Source: request
Open: Whether surrounding whitespace is trimmed, whether a whitespace-only or control-character name counts as empty, and whether length counts characters or UTF-16 units are not stated; the existing fields (`requester`, `src/tickets/validate.js`) trim, refuse control characters and count `.length`. The requester decides. Tests use plain names of 1, 64 and 65 characters and the empty string only.

### C-4: A body that is not an object with a string-or-null `assignee` is invalid
Observable: `PUT` with a body lacking `assignee`, with `assignee` a number, boolean, array or object, or with an unknown extra field, answers 400 `invalid` and changes nothing (docs/api.md: unknown fields are refused; a body that is not a JSON object is `invalid`).
Source: existing: docs/api.md "Conventions" and "Errors"

### C-5: Only open and in-progress tickets can be assigned or unassigned
Observable: `PUT` on a ticket whose status is `resolved` or `closed`, with a name or with null, answers 409 `conflict` and the assignee is unchanged, with no audit entry and no notification.
Source: request; existing: CONTRIBUTING.md (a state that does not allow a request is 409)
Open: Whether a no-op request (same assignee, or null on an already unassigned ticket) on a resolved or closed ticket answers 409 or 200 is not stated. Tests check only the case where the assignee would change.

### C-6: Assigning to the agent the ticket already has changes nothing
Observable: Repeating the same assignee answers 200 with the ticket; `updated` is as before, no new audit entry appears in `GET /tickets/:id/audit`, and no new notification is enqueued.
Source: request; existing: docs/api.md ("a request that changes nothing leaves [updated] as it was"), CONTRIBUTING.md

### C-7: Unassigning an already unassigned open or in-progress ticket changes nothing
Observable: `PUT` with `{"assignee": null}` on an unassigned open ticket answers 200 with `assignee` null, `updated` unchanged, no audit entry, no notification.
Source: implied: C-6 and the rule that a change that changes nothing is not a change (CONTRIBUTING.md)

### C-8: A ticket that does not exist is 404
Observable: `PUT /tickets/T-9999/assignee` for an unknown id answers 404 `not_found`.
Source: existing: docs/api.md "Errors"

### C-9: Every ticket shows `assignee`, null when unassigned
Observable: Every ticket in the responses of POST /tickets (new ticket: `"assignee": null`), GET /tickets/:id, GET /tickets items, PATCH, and transition has an `assignee` key, a string or null. A ticket created before this change, loaded from an existing data file with no assignee, shows `null`.
Source: request; implied: a service that keeps its state across restarts must read its old data file

### C-10: The assigned agent is notified that the ticket was assigned to them
Observable: After a successful change of assignee to `"dana"` and one worker run, one notification is delivered whose `to` is `dana` and whose text names the ticket id and says it was assigned to them. It is queued through the outbox (a request does not deliver it), so with `WORKER_INTERVAL_MS=0` it stays pending in `GET /admin/outbox`.
Source: request; existing: docs/decisions/0006-notification-outbox.md, CONTRIBUTING.md
Open: The channel for reaching an agent by name is not stated; the existing notifier takes `to` as an opaque string (requesters are emails), so the agent name is used as `to`. The requester of the service decides if agents need an address mapping. Tests check `to` equals the agent name and the text mentions the ticket id.

### C-11: Unassigning, a repeated assignment and a refused request send no notification
Observable: After `{"assignee": null}`, a repeat of the current assignee, or any 400/404/409 answer, the outbox holds no new event.
Source: implied: the request notifies "the agent a ticket is assigned to" only; CONTRIBUTING.md (no change, no notification)
Open: Whether the previous assignee should be told they were unassigned is not requested and is not done.

### C-12: A reassignment to a different agent notifies the new agent even while an earlier assignment notification is still pending
Observable: Assigning T-0001 to `dana`, then (before the worker runs) to `lee`, results in a notification delivered to `lee`; the outbox's dedup, which by default keys on type and ticket, must not swallow it.
Source: implied: C-10 for every assignment, and docs/decisions/0006 (a key dedups pending events)
Open: Whether the earlier pending notification to `dana` is still delivered or withdrawn is not stated; tests require only that `lee` is notified.

### C-13: Each change of assignee is recorded in the audit log
Observable: A change of assignee adds one entry to `GET /tickets/:id/audit` whose `changes` holds `assignee` with its `from` and `to` (null for none), and whose actor is the `X-Actor` header or `system`.
Source: implied: README ("every change is on record"), CONTRIBUTING.md, decision 7
Open: The action name of the entry is not stated; tests check the `changes` only.

### C-14: A change of assignee updates the ticket's `updated` time
Observable: After a real change, `updated` is the time of the change; created and other fields are unchanged.
Source: existing: docs/api.md ("updated: when it last changed")

### C-15: GET /tickets?assignee=<agent> keeps that agent's tickets
Observable: `?assignee=dana` lists only tickets whose assignee is exactly `dana` (every status), in id order and in pages as before, with `next` as before.
Source: request

### C-16: An empty `assignee=` keeps the unassigned tickets
Observable: `GET /tickets?assignee=` lists only tickets whose `assignee` is null.
Source: request

### C-17: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only open tickets of dana; `?status=open&priority=urgent` lists only open tickets that are urgent (not tickets that are open or urgent). With no filter every ticket is listed.
Source: request; existing: docs/api.md "List tickets"
Open: The current `matchesFilters` in `src/tickets/query.js` passes a ticket matching any one filter, which contradicts docs/api.md and this request; the request's "must match every filter" is taken as binding for all filters. The existing tests do not exercise two filters at once, so they stay passing.

### C-18: An `assignee` filter value is not validated against a name rule
Observable: `?assignee=nobody-at-all` answers 200 with an empty `items` and `next` null, not 400.
Source: choice: a filter on a name that has no tickets is an empty result, the loosest behaviour; the request lists no error for it
Open: Whether a filter value longer than 64 characters is `invalid` or an empty list is not stated; tests do not check it.

### C-19: The command-line `list` table shows each ticket's assignee
Observable: `node bin/tickets.js list` prints an `ASSIGNEE` column holding the agent's name for an assigned ticket and a visible placeholder (not the text of another ticket's value) for an unassigned one; `show ID` is not required to change.
Source: request
Open: The placeholder text for unassigned (`-`, empty, `null`) is not stated; tests check only that an assigned ticket's row contains its agent's name and that the header names the assignee.

### C-20: `list --raw` keeps its existing columns in their positions
Observable: Columns 1 to 4 of every `list --raw` line stay id, status, priority, title, tab-separated, so `scripts/weekly-report.js` gives the same counts as before.
Source: existing: README.md "Command line", src/format.js
Open: Whether `--raw` also shows the assignee (and in which column, if so only after the title) is not stated. A build may append it after the title or leave it out; tests check only columns 1 to 4.

### C-21: The command line's `list` can read a data file that has no assignees
Observable: `list` and `list --raw` on a data file written before this change print every ticket without error, the assignee shown as unassigned.
Source: implied: C-9 and README ("optional data file")

### C-22: The assignment survives a restart
Observable: With `DATA_FILE` set, after the service is stopped and started again, the ticket shows the same `assignee`, and notifications still pending are still pending.
Source: existing: README.md "Configuration" (state saved after every change)

### C-23: Existing behaviour and tests are preserved
Observable: Every test in test/ that exists now passes unchanged; the endpoints, error envelope, ids, pagination, audit and notifications of creating and resolving tickets behave as in docs/api.md, apart from the added `assignee` field on tickets.
Source: request

### C-24: New behaviour has node:test tests under test/, run by `npm test`
Observable: `npm test` runs the new test files together with the existing ones and passes; no package is added to package.json.
Source: request; existing: CONTRIBUTING.md ("No dependencies")
