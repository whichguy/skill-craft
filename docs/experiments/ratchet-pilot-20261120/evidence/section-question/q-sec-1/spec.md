## Use cases

### U-1: A dispatcher or agent assigns a ticket to an agent, to make clear who works it
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` (optionally with `X-Actor`). Gets 200 and the ticket, whose `assignee` is `"dana"`. Dana is notified that the ticket was assigned to her/them.
Source: request

### U-2: A dispatcher unassigns a ticket, to return it to the pool
Flow: sends `PUT /tickets/T-0001/assignee` with `{"assignee": null}`. Gets 200 and the ticket with `assignee` null.
Source: request

### U-3: An agent lists their own tickets, or the unassigned ones, to find work
Flow: `GET /tickets?assignee=dana` lists only dana's tickets; `GET /tickets?assignee=` lists only unassigned tickets; `GET /tickets?status=open&assignee=dana` lists dana's open tickets.
Source: request

### U-4: An operator sees who each ticket is assigned to on the command line
Flow: runs `node bin/tickets.js --data FILE list` and sees an assignee for every ticket.
Source: request

### U-5: Existing callers, data files and scripts keep working
Flow: tickets created before this change, data files saved before it, the weekly report and every existing endpoint behave as before.
Source: request ("Everything the service already does keeps working")

## Clauses

### C-1: Assigning sets the ticket's assignee
Observable: for an open or in-progress ticket, `PUT /tickets/:id/assignee` with `{"assignee":"dana"}` answers 200 with the full ticket whose `assignee` is `"dana"`; a following `GET /tickets/:id` also shows `"dana"`. `updated` is set to the time of the change.
Source: request

### C-2: Assigning to a different agent than the current one replaces the assignee
Observable: a ticket assigned to `dana` that receives `{"assignee":"lee"}` answers 200 and shows `assignee` `"lee"`.
Source: implied: the request only forbids a change for the same agent and limits assignment by status, not by current assignee.

### C-3: null unassigns
Observable: `{"assignee": null}` on an open or in-progress ticket answers 200 with `assignee` null, and a following GET shows null.
Source: request

### C-4: An agent is a non-empty string of at most 64 characters
Observable: `assignee` of 1 and of 64 characters is accepted (200). An empty string, a string of 65 characters, and any value that is not a string or null (number, boolean, object, array) answer 400 with `{"error":{"code":"invalid",...}}`, and the ticket is unchanged.
Source: request
Open: whether surrounding whitespace is trimmed before counting (as titles and requesters are), whether a whitespace-only name counts as empty, and whether control characters are refused. The existing text fields trim and refuse blank and multi-line values (`src/tickets/validate.js`); the request does not say. The requester decides. Tests check only the values stated above, plus a plain name such as `dana`.

### C-5: The body must carry the `assignee` field and nothing else
Observable: a body without `assignee`, a body that is not a JSON object, or a body with any other field answers 400 `invalid`; the ticket is unchanged.
Source: existing: docs/api.md ("Unknown fields in a request body are refused (400)", a body that is not a JSON object is `invalid`)

### C-6: Only open and in-progress tickets can be assigned or unassigned
Observable: for a ticket whose status is `resolved` or `closed`, a PUT of an agent or of null answers 409 with code `conflict`; the ticket, its audit log and the outbox are unchanged. Open and in_progress tickets accept both.
Source: request
Open: what a no-op request (same agent, or null on an unassigned ticket) on a resolved or closed ticket answers: 409 (the status refuses first) or 200. Tests do not check that combination.

### C-7: Assigning a ticket to the agent it already has changes nothing
Observable: the PUT answers 200 with the ticket as it was; `updated` is unchanged, no audit entry is added, no notification is enqueued.
Source: request

### C-8: Unassigning an already unassigned open or in-progress ticket changes nothing
Observable: `{"assignee":null}` on an unassigned open ticket answers 200, `updated` unchanged, no audit entry, no notification.
Source: implied: "A request that changes nothing is not a change" (CONTRIBUTING.md) and the request's no-op rule for assignment.

### C-9: A missing ticket is 404
Observable: `PUT /tickets/T-9999/assignee` for a ticket that does not exist answers 404 `not_found`.
Source: existing: docs/api.md (error table)

### C-10: Every ticket shows `assignee`
Observable: every ticket in a response (create 201, GET one, GET list items, PATCH, transition, PUT) has an `assignee` key: null for a new or never-assigned ticket, otherwise the agent's name.
Source: request

### C-11: A new ticket starts unassigned
Observable: `POST /tickets` answers 201 with `assignee` null; `POST /tickets` with an `assignee` field is still refused as an unknown field (400), assignment being done only through the PUT.
Source: implied: "Every ticket shows its assignee (null when unassigned)"; existing: docs/api.md (unknown fields refused).

### C-12: The assignee survives a restart, and older data files still load
Observable: with `DATA_FILE`, after assigning and restarting the service, the ticket still shows its assignee. A data file saved before this change, whose tickets have no assignee, loads and shows `assignee` null for each ticket.
Source: implied: the service "keeps its state across restarts" (README.md); existing: src/persistence.js, which lists the ticket fields it keeps.

### C-13: A change of assignee is recorded in the audit log
Observable: assigning, reassigning or unassigning (when it changes something) adds one entry to `GET /tickets/:id/audit` with `changes.assignee` = `{from, to}` (from null for a first assignment, to null for an unassignment), `actor` from `X-Actor` or `system`, and exactly one entry per change.
Source: existing: docs/decisions/0007-append-only-audit-log.md ("every change to a ticket" is recorded)
Open: the `action` name of the entry (not specified; clients should not rely on it).

### C-14: The newly assigned agent is notified of the assignment
Observable: after a PUT that assigns ticket T to agent `dana`, one notification appears in `GET /admin/outbox` (pending, then sent once the worker runs) addressed `to` `"dana"` and with `ticket` `T`; when delivered, the notifier's line is addressed to `dana` and its subject or body names the ticket id and says it was assigned. It is not sent inside the request.
Source: request
Open: the exact wording of the message, and how an agent name maps to a mail address (the notification's `to` is the agent's name as given), are for the requester.

### C-15: Reassigning notifies the new agent, even if the earlier assignment's notification is still pending
Observable: assign `dana`, then `lee` before the worker runs: the outbox holds a notification for `lee` as well as the one for `dana`. Assigning dana, then lee, then dana again while the first is pending does not lose the final assignment's news: dana is notified of the latest assignment at least once.
Source: implied: "The agent a ticket is assigned to is notified"; existing: docs/decisions/0006-notification-outbox.md (a key still pending suppresses a new enqueue, so the key must not make one assignment hide another).

### C-16: Unassigning and no-op requests notify nobody
Observable: `{"assignee":null}`, a same-agent PUT, and a rejected PUT (400, 404, 409) add nothing to the outbox. 
Source: implied: the request notifies only "the agent a ticket is assigned to"; C-7.

### C-17: A rejected assignment changes nothing
Observable: after a 400, 404 or 409 answer from the PUT, the ticket (including `updated`), the audit log and the outbox are as before.
Source: existing: CONTRIBUTING.md ("no change is ever half recorded"), docs/decisions/0004-error-envelope.md

### C-18: A status transition or a PATCH leaves the assignee as it is
Observable: after assigning `dana`, `PATCH` of the title or a transition to `in_progress` or `resolved` keeps `assignee` `"dana"`.
Source: choice: the request says nothing about clearing on status change; keeping the value is the least change and is what "everything the service already does keeps working" implies.

### C-19: `assignee=<agent>` keeps only that agent's tickets
Observable: `GET /tickets?assignee=dana` lists exactly the tickets whose `assignee` is `"dana"`, in id order, as pages (`items`, `next`), and `?assignee=dana&limit=1&cursor=...` pages through them with the same filter. Matching is by the exact name.
Source: request
Open: whether the match ignores letter case (`Dana` vs `dana`). Tests use names differing by more than case.

### C-20: An empty `assignee=` keeps only unassigned tickets
Observable: `GET /tickets?assignee=` lists exactly the tickets whose `assignee` is null. A filter with an agent name that nobody holds answers 200 with `{"items":[],"next":null}`.
Source: request

### C-21: A ticket must match every filter given
Observable: `?status=open&assignee=dana` lists only open tickets assigned to dana; `?status=open&priority=urgent` lists only open tickets that are urgent; `?status=open&assignee=` lists open unassigned tickets. A ticket matching only one of the filters is not listed.
Source: request; existing: docs/api.md ("a ticket is listed only when it matches every filter given").
Note for the build: `matchesFilters` in `src/tickets/query.js` today keeps a ticket that matches any one filter (`some`), which contradicts docs/api.md; the request requires all, so this changes with the new filter.

### C-22: Without an `assignee` parameter the listing is not filtered by assignee
Observable: `GET /tickets` and `?status=open` list assigned and unassigned tickets alike.
Source: implied: "`GET /tickets` gains an `assignee` filter"; existing: docs/api.md.

### C-23: The command-line `list` table shows each ticket's assignee
Observable: `bin/tickets.js list` prints a header cell and, for each ticket, the agent's name, or a stand-in for unassigned.
Source: request
Open: the column's position and title, and what text stands for "unassigned". Tests find the name of an assigned ticket in its row and do not rely on the stand-in.

### C-24: `list --raw` keeps columns 1 to 4 (id, status, priority, title) in place
Observable: for every ticket, the first four tab-separated fields of `list --raw` are id, status, priority and title, as before, so `scripts/weekly-report.js` gives the same counts and its `--json` output the same shape. Any assignee is shown after these, if at all.
Source: existing: README.md ("they must keep their positions"), scripts/weekly-report.js
Open: whether `--raw` shows the assignee at all (the request says "the command-line listing"). If it does, it is a fifth column, with a stand-in for unassigned that needs a decision.

### C-25: The command line `list` gains no write ability and `show` still works
Observable: `list` and `show` never change the data file; `show T-0001` still prints and exits 0 for a ticket with or without assignee, and exit codes are as before (0, 1 no such ticket, 2 usage/data problem). `list` against a data file saved before this change works.
Source: existing: bin/tickets.js header, README.md

### C-26: Existing behaviour and tests stay as they are
Observable: every test under `test/` that exists now passes unmodified; the new tests are in new or added files (`node:test`, under `test/`), run by `npm test`, using no dependency.
Source: request

## Preserved behaviour

- The error envelope and codes (`invalid` 400, `not_found` 404, `conflict` 409): src/errors.js, docs/decisions/0004-error-envelope.md. New errors use it (C-4, C-5, C-6, C-9).
- Existing endpoints, their statuses and bodies, except that tickets gain `assignee`: docs/api.md, test/api.test.js. Single-field status and priority filters, bad filter values (`status=done` is 400), `limit` 1 to 100 and cursors: src/tickets/query.js, test/query.test.js. An empty `status=` is still 400.
- Unknown parameters in the listing are ignored: test/query.test.js.
- Handlers call one store method, never change tickets or the notifier directly; the change, audit entry, notification and save happen together: CONTRIBUTING.md, src/store.js.
- Notifications go only through the outbox and the worker; `WORKER_INTERVAL_MS=0` stops delivery: docs/decisions/0006-notification-outbox.md. Existing `ticket.created` and `ticket.resolved` notifications to requesters are unchanged: src/templates.js, test/notifier.test.js.
- The audit log is append-only and numbered from 1; a no-op writes no entry and leaves `updated`: docs/decisions/0007-append-only-audit-log.md.
- The data file format version 1 and its checks; a closed ticket cannot be changed (PATCH 409): src/persistence.js, src/store.js. Whether a data file with an invalid `assignee` is refused at start is not settled here.
- `X-Actor` handling (at most 64 characters, else 400): src/http.js.
- `list --raw` column positions and the weekly report: README.md, scripts/weekly-report.js (C-24).
- Whether status transitions of an assigned ticket (e.g. resolved, closed) should clear the assignee is not settled by the existing files; C-18 keeps it.
- No dependencies, CommonJS: CONTRIBUTING.md.
