## Use cases

### U-1: An agent or dispatcher assigns a ticket to an agent, so that the agent knows it is theirs to work
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` for an open or in-progress ticket and gets 200 with the ticket, whose `assignee` is `"dana"`. Dana is notified that the ticket was assigned to them.
Source: request

### U-2: A dispatcher unassigns a ticket, so that it returns to the pool
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}` for an open or in-progress ticket and gets 200 with the ticket, whose `assignee` is `null`.
Source: request

### U-3: A dispatcher lists a given agent's tickets, or the unassigned ones, to see who has what
Flow: requests `GET /tickets?assignee=dana` and sees only dana's tickets; requests `GET /tickets?assignee=` and sees only unassigned tickets; adds `status` or `priority` and sees only tickets matching all filters given.
Source: request

### U-4: An operator sees each ticket's assignee on the command line
Flow: runs `node bin/tickets.js --data FILE list` and sees the assignee of every ticket in the listing.
Source: request

### U-5: An existing client or operator keeps using the service as before
Flow: creates, changes, transitions, lists, audits and reads tickets, runs the command line and the weekly report, and restarts the service with a data file, with the results documented in README.md and docs/api.md.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: `PUT /tickets/:id/assignee` with `{"assignee": "<agent>"}` assigns an open or in-progress ticket to that agent
Observable: for an existing ticket whose status is `open` or `in_progress`, the response is 200 with the ticket (same shape as `GET /tickets/:id`) whose `assignee` is the agent's name; a following `GET /tickets/:id` shows the same `assignee`. Assigning a ticket that already has another agent replaces that agent.
Source: request

### C-2: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: for an existing `open` or `in_progress` ticket, the response is 200 with the ticket whose `assignee` is `null`; a following `GET /tickets/:id` shows `null`.
Source: request

### C-3: An agent is a non-empty name; any other `assignee` value is refused as `invalid`
Observable: an `assignee` that is the empty string, a string of only whitespace, a number, a boolean, an array or an object is answered 400 with `{"error": {"code": "invalid", ...}}`, and the ticket is unchanged. A body that is not a JSON object, a body without an `assignee` field, and a body with any field other than `assignee` are likewise 400 `invalid` (existing rules: docs/api.md "Unknown fields", src/http.js).
Source: request ("an agent is a non-empty name"); existing: docs/api.md, src/http.js, src/tickets/validate.js
Open: whether surrounding whitespace is trimmed and whether names have a maximum length or forbidden characters is not stated. A name of 1 to 64 printable characters without surrounding whitespace must be accepted and stored as given; behaviour beyond that is the requester's to settle.

### C-4: Only open and in-progress tickets can be assigned or unassigned
Observable: for a ticket whose status is `resolved` or `closed`, a `PUT` of an agent name or of `null` is answered 409 with code `conflict` and the ticket's `assignee` and `updated` are unchanged. This holds when the request would change nothing (the same agent, or `null` on an unassigned ticket).
Source: request; existing: docs/api.md "conflict" (the ticket's state does not allow it)
Open: whether a no-op request on a resolved or closed ticket is 409 or 200 is not stated; the request's sentence is read as refusing every assign or unassign there.

### C-5: A request for a ticket that does not exist is 404 `not_found`
Observable: `PUT /tickets/T-9999/assignee` with a valid body, for an id that no ticket has, is answered 404 with code `not_found`.
Source: implied: every ticket route answers an unknown id this way (docs/api.md, "Errors")
Open: which error wins when a request is both malformed and for an unknown or closed ticket is not stated; no check relies on it.

### C-6: Assigning a ticket to the agent it already has changes nothing
Observable: the answer is 200 with the ticket as it was; `updated` is unchanged, `GET /tickets/:id/audit` gains no entry, and no notification is enqueued (`GET /admin/outbox` lists no new event).
Source: request; existing: CONTRIBUTING.md ("A change that changes nothing is not a change"), docs/api.md ("updated ... a request that changes nothing leaves it as it was")

### C-7: Unassigning a ticket that has no assignee changes nothing
Observable: for an open or in-progress ticket with `assignee` `null`, `{"assignee": null}` is answered 200 with the ticket as it was; `updated` is unchanged and the audit log gains no entry.
Source: implied: C-6's rule applied to the unassign request; existing: CONTRIBUTING.md

### C-8: Every ticket shows its `assignee`, `null` when unassigned
Observable: the ticket object in `POST /tickets` (201), `GET /tickets/:id`, every item of `GET /tickets`, `PATCH /tickets/:id` and `POST /tickets/:id/transition` responses, and the `PUT` response has an `assignee` key, `null` for a new ticket.
Source: request

### C-9: An assignee survives a restart of a service that has a data file; a data file written before this change still loads
Observable: with `DATA_FILE` set, after an assignment and a restart of the service, `GET /tickets/:id` shows the same `assignee`; and the command line, which reads the data file, shows it. A data file whose tickets have no `assignee` field loads, and those tickets show `assignee` `null`.
Source: implied: the data file keeps state across restarts (README.md, docs/decisions/0008-json-data-file.md) and every ticket shows its assignee; existing: README.md ("Everything ... keeps working")
Open: whether the data file `version` number changes is an internal matter; a file written by the previous version of the service must still load.

### C-10: The agent a ticket is assigned to is notified that it was assigned to them
Observable: after a successful assignment that changes the assignee, the service enqueues a notification addressed (`to`) to the agent's name, for that ticket, of a kind that has a template, so that it is delivered (appears under `sent` in `GET /admin/outbox` and, with `NOTIFY_FILE`, as one line in that file with a subject and body naming the ticket) and does not end up `dead`. The response to the `PUT` does not wait for delivery. With the worker off (`WORKER_INTERVAL_MS=0`) the notification stays `pending`.
Source: request; existing: docs/decisions/0006-notification-outbox.md, CONTRIBUTING.md ("A new kind of notification needs a template")
Open: the subject and wording of the message are not stated; the requester has not said whether a name that is not an email address can be delivered by the relay.

### C-11: Reassigning a ticket before the earlier notification was sent still notifies the new agent
Observable: assign T-0001 to `dana`, then (worker off, so the first notification is still pending) assign it to `lee`: the outbox holds a pending notification to `dana` and one to `lee`; the second is not swallowed by the first's deduplication key. Assigning it back to `dana` afterwards while a notification to `dana` is still pending does not queue a second one to `dana` for that ticket.
Source: implied: "the agent a ticket is assigned to is notified" must hold for every assignment; existing: src/outbox.js (a pending event with the same key absorbs a new one)

### C-12: Unassigning a ticket sends no notification
Observable: after `{"assignee": null}` that changes the ticket, the outbox gains no event.
Source: choice: the request notifies only "the agent a ticket is assigned to ... that it was assigned to them"; an unassign assigns nobody.

### C-13: Assignment does not notify the requester
Observable: an assignment adds no outbox event addressed to the ticket's requester.
Source: choice: the request names only the assigned agent as notified.

### C-14: A change of assignee is recorded in the ticket's audit log
Observable: `GET /tickets/:id/audit` gains one entry for each assignment, reassignment or unassignment that changes the assignee, with the actor from `X-Actor` (or `system`), and `changes.assignee` holding `{ "from": <previous assignee or null>, "to": <new assignee or null> }`; the ticket's `updated` becomes the time of that change.
Source: implied: "every change is on record" (README.md) and CONTRIBUTING.md ("Changes go through the store ... appends the audit entry"); existing: docs/api.md "A ticket's history"
Open: the entry's `action` name is not stated (`ticket.assigned` is a reasonable choice); checks must not depend on it.

### C-15: `GET /tickets?assignee=<agent>` keeps only that agent's tickets
Observable: every item returned has `assignee` equal to `<agent>` exactly (same characters, case-sensitive); tickets of other agents and unassigned tickets are absent. A name no ticket has gives `{"items": [], "next": null}`, not an error. The filter applies to tickets of every status.
Source: request

### C-16: `GET /tickets?assignee=` (empty value) keeps only unassigned tickets
Observable: every item returned has `assignee` `null`; assigned tickets are absent. This differs from omitting the parameter, which applies no assignee filter.
Source: request

### C-17: A ticket is listed only when it matches every filter given
Observable: `?status=open&priority=urgent` lists only tickets that are open and urgent; `?status=open&assignee=dana` lists only open tickets of dana; `?assignee=&priority=high` lists only unassigned high-priority tickets. A ticket that matches one filter but not another is absent.
Source: request ("a ticket must match every filter given"); existing: docs/api.md "Filters combine"
Open: none for the rule; note for planning: the current `matchesFilters` in src/tickets/query.js keeps a ticket that matches any one filter, which contradicts the documented rule and must be corrected.

### C-18: The assignee filter works with paging
Observable: with `assignee` (including empty) and `limit`, pages follow id order, `next` is null on the last page, and passing `next` as `cursor` with the same filters yields the following matching tickets with none repeated or skipped.
Source: implied: docs/api.md "List tickets" and decision 5, which apply to every listing

### C-19: The command-line listing shows each ticket's assignee
Observable: `node bin/tickets.js --data FILE list` (table) shows, for each ticket, its assignee's name, and a visible placeholder of the implementer's choice for an unassigned ticket, under a header naming the column. `list --assignee <agent>` is not required.
Source: request
Open: the column's header, position and the placeholder for unassigned are not stated; checks look for the agent's name on the ticket's row and must not depend on the rest.

### C-20: `list --raw` keeps its first four columns in place
Observable: each `list --raw` line still has id, status, priority and title as tab-separated columns 1 to 4, so `scripts/weekly-report.js` and its `--json` counts give the same results as before. Whether `--raw` also shows the assignee is not required; if it does, it is after column 4.
Source: existing: README.md ("they must keep their positions"), scripts/weekly-report.js

### C-21: Existing behaviour is unchanged
Observable: the existing test suite passes without any edit to existing test files; the endpoints and error rules in docs/api.md behave as documented. In particular `PATCH /tickets/:id` still refuses `assignee` as an unknown field (400), `POST /tickets` does not accept `assignee`, transitions do not change the assignee (a resolved or reopened ticket keeps its assignee), and an assignment does not change the ticket's `status`.
Source: request; existing: docs/api.md

### C-22: New tests cover the new behaviour and run with `npm test`
Observable: new `node:test` files under `test/` cover the assignment endpoint, the filter, the notification and the command-line listing; `npm test` runs them with the existing tests and all pass; no dependency is added to `package.json`.
Source: request; existing: CONTRIBUTING.md

### C-23: Two assignments in sequence leave the later one in force
Observable: for two successive `PUT`s to the same ticket, the last one answered is what `GET /tickets/:id` shows, and each one that changed the assignee has its own audit entry, in order.
Source: implied: requests are handled one at a time through the store, which is synchronous (src/store.js)

## Rules and edge cases

- Who may be assigned: a non-empty name; wrong types, empty and whitespace-only names are 400 (C-3). Trimming and a length limit are not settled (C-3 Open).
- Which statuses: `open` and `in_progress` allow assign and unassign; `resolved` and `closed` give 409, even for a no-op (C-4).
- Unknown ticket: 404 (C-5). Unknown or missing body fields, non-object bodies: 400 (C-3).
- No-op: same agent, or unassign of an unassigned ticket, changes nothing: no audit entry, no notification, `updated` kept (C-6, C-7).
- Reassignment from one agent to another: replaces; audit records from and to; the new agent alone is notified (C-1, C-11, C-14). The notification deduplication key must not hide a different agent's notification (C-11).
- Unassign: no notification (C-12).
- Missing `assignee` in old data and new tickets: `null` (C-8, C-9).
- Filter: exact, case-sensitive match; empty value means unassigned; absent means no filter; unknown name gives an empty page, not an error; all filters must match (C-15 to C-17). An `assignee` filter value is never `invalid`.
- Lifecycle: resolving, closing or reopening keeps the assignee (C-21); the assignee of a resolved or closed ticket cannot be changed (C-4).
- Paging: filters and cursors work together (C-18).
- Persistence: the assignee is saved and loaded; old files still load (C-9).
- Command line: the assignee is shown; raw column positions are kept (C-19, C-20).
- Not settled by the request or by what is here: the maximum length and character rules of an agent name, the order in which a malformed request and an unknown or closed ticket are reported, and the wording of the notification (see the Open lines of C-3, C-5 and C-10).
