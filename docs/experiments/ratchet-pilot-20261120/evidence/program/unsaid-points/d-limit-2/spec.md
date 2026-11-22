## Use cases

### U-1: A dispatcher assigns a ticket so an agent can take it
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an `open` or `in_progress` ticket. Reading the ticket shows `"assignee":"Dana"`. Sending `{"assignee":"Lee"}` instead replaces Dana with Lee. Resending the current assignment leaves the ticket unchanged.
Source: request

### U-2: A dispatcher clears an assignment so a ticket is available again
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an `open` or `in_progress` ticket. Reading the ticket shows `"assignee":null`. A request to change the assignee of a `resolved` or `closed` ticket receives a state conflict.
Source: request

### U-3: An agent receives a notice so they know which ticket was assigned to them
Flow: After a dispatcher assigns `T-0001` to Dana, the service hands off a notice addressed to Dana that identifies `T-0001` as assigned to them. An operator can inspect its delivery state at `GET /admin/outbox`.
Source: request

### U-4: A dashboard caller filters tickets to find an agent's work or unassigned work
Flow: The caller requests `GET /tickets?assignee=Dana` for Dana's tickets or `GET /tickets?assignee=` for unassigned tickets. Adding `status=open&priority=urgent` narrows either result to tickets that also satisfy both of those filters. The caller follows `next` with the same filters to see subsequent pages.
Source: request

### U-5: A command-line operator lists saved tickets to see who has each one
Flow: The operator runs `node bin/tickets.js --data FILE list` against the service's data file. Each listed ticket shows its agent or that it is unassigned.
Source: request

### U-6: A help desk reviewer reads a ticket's history to trace its assignment changes
Flow: The dispatcher supplies `X-Actor: sam` when assigning `T-0001` to Dana. The reviewer requests `GET /tickets/T-0001/audit` and sees an entry by `sam` recording the assignee change from `null` to `Dana` after the existing entries.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### U-7: A service operator restarts the API to resume work on saved tickets
Flow: The operator runs `npm start` with `PORT` and `DATA_FILE` set, makes an assignment, then stops and restarts the service with the same data file. The ticket still shows its saved assignee and its assignment history is available. A file from before assignment was added still loads, with its tickets shown as unassigned.
Source: existing: docs/decisions/0008-json-data-file.md

### U-8: A maintainer runs the test suite to verify the assignment change
Flow: The maintainer runs `npm test`. The assignment tests under `test/` run with the existing suite, which passes with its pre-change tests intact.
Source: request

## Clauses

### C-1: A valid assignment sets the named agent on an `open` or `in_progress` ticket
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` while `T-0001` is in either allowed state. `GET /tickets/T-0001` shows `"assignee":"Dana"`, whether the previous assignee was `null` or `Lee`.
Source: request

### C-2: A valid unassignment clears the assignee of an `open` or `in_progress` ticket
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` while `T-0001` is assigned in either allowed state. `GET /tickets/T-0001` shows `"assignee":null`.
Source: request

### C-3: A successful assignment request reports HTTP success
Observable: Assign, replace, clear, or resend the current assignee on an eligible ticket using the `PUT` endpoint. Each accepted request returns a `2xx` response.
Source: implied: U-1 and U-2 need a caller-visible success outcome
Open: The requester decides whether success must use a particular status or return the ticket in the response body.

### C-4: A request that would change the assignee of a `resolved` or `closed` ticket receives a state conflict
Observable: On tickets in each blocked state, send a valid `PUT` that would assign, replace, or clear the current assignee. Each reply is HTTP 409 with `error.code` equal to `conflict`.
Source: existing: docs/api.md
Open: The requester decides whether a request for the already-current value in either blocked state is also a conflict or can succeed as a no-op.

### C-5: Refused assignment requests leave the assignment state intact
Observable: After an `invalid` or `conflict` reply for an existing ticket, the ticket, its entries in `GET /tickets/:id/audit`, and the assignment notices recorded for it are the same as before the request. With the worker off, unrelated delivery activity cannot affect that comparison.
Source: implied: U-1 and U-2 restrict assignment changes to valid requests in eligible states

### C-6: An assignment request for an absent ticket receives `not_found`
Observable: Send an otherwise valid assignment or unassignment to an absent ticket ID such as `T-0042`. The reply is HTTP 404 with `error.code` equal to `not_found`.
Source: existing: docs/api.md

### C-7: An assignment request requires a JSON object with the `assignee` field
Observable: Send no body, malformed JSON, a JSON array, bare `null`, another JSON scalar, or `{}`. Each reply is HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md

### C-8: The assignment endpoint rejects unrecognized body fields
Observable: Send `{"assignee":"Dana","priority":"high"}` or a misspelling such as `{"asignee":"Dana"}`. The reply is HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md

### C-9: The assignment field accepts a non-empty agent name or JSON `null`
Observable: A name such as `"Dana Lee"` and the value `null` are accepted for an eligible ticket. The empty string `""`, numbers, booleans, arrays, and objects receive HTTP 400 with `error.code` equal to `invalid`.
Source: request
Open: The requester decides whitespace-only validity, treatment of surrounding whitespace and control characters, and any name-specific maximum. The existing request-wide byte limit applies independently.

### C-10: Assignment requests obey the service's JSON body size limit
Observable: With `MAX_BODY_BYTES` unset, a valid assignment JSON object padded with JSON whitespace to 65,536 UTF-8 bytes is within the limit. Adding one byte receives HTTP 400 with `error.code` equal to `invalid`. With `MAX_BODY_BYTES` configured, the same inclusive boundary applies at the configured byte count.
Source: existing: src/http.js

### C-11: Assignment endpoint errors use the service's JSON error envelope
Observable: On a refused `PUT`, the response has `content-type: application/json; charset=utf-8` and a JSON `error` object with a machine-readable `code` and a human-readable `message`.
Source: existing: docs/api.md

### C-12: Every ticket representation in the API includes its current `assignee`
Observable: Inspect a ticket returned by create, read, list, patch, or transition, or by the assignment endpoint if it returns a ticket. In every representation the `assignee` key holds the current agent name or JSON `null` when unassigned. The create response shows `"assignee":null` for a new ticket.
Source: request

### C-13: The create and patch endpoints continue to reject unsupported assignment input
Observable: Submit an otherwise valid `POST /tickets` or `PATCH /tickets/:id` body that includes `assignee`. Both replies are HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md

### C-14: A repeated request for the current assignee leaves the ticket unchanged
Observable: On an `open` or `in_progress` ticket assigned to Dana, repeat `{"assignee":"Dana"}`. On an eligible unassigned ticket, repeat `{"assignee":null}`. Comparing reads before and after each repeat shows the same ticket fields, including `updated`, even when the repeat is made at a later time.
Source: request
Open: The requester decides whether names that differ by case or other normalization represent the same agent for assignment, no-op detection, and filtering.

### C-15: Repeating the current assignee adds no audit entry
Observable: On an eligible ticket, send the already-current name or `null` through the assignment endpoint. The audit items are identical before and after the request.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-16: An assignment change updates the ticket's last-change time
Observable: At a later clock time, assign, reassign, or unassign an eligible ticket. Its `updated` reflects the time of the assignment change in ISO 8601 UTC.
Source: existing: docs/api.md

### C-17: Each change of assignee is appended to the ticket's audit history
Observable: Assign Dana, replace Dana with Lee, then clear Lee. `GET /tickets/T-0001/audit` retains the existing items and appends one item per change in that order, with the next log sequence numbers, the ticket ID, the action, the change time, and `changes.assignee` of `{"from":null,"to":"Dana"}`, `{"from":"Dana","to":"Lee"}`, then `{"from":"Lee","to":null}`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-18: The assignment audit entry identifies the actor under the existing `X-Actor` convention
Observable: A change with `X-Actor: sam` shows `"actor":"sam"` in the audit entry. Surrounding whitespace is trimmed. An omitted or blank header shows `"actor":"system"`.
Source: existing: src/http.js

### C-19: The assignment endpoint enforces the existing actor length bound
Observable: An otherwise valid request with a trimmed 64-character `X-Actor` is within the limit. A trimmed 65-character actor receives HTTP 400 with `error.code` equal to `invalid`.
Source: existing: src/http.js

### C-20: An assignment request leaves the ticket's lifecycle status alone
Observable: Assign or clear the assignee of an `open` or `in_progress` ticket, then read it. The ticket is still in the starting status, and its identity, title, priority, requester, and creation time remain as before.
Source: implied: U-1 and U-2 change who handles the existing ticket

### C-21: Assignment does not change the allowed lifecycle moves
Observable: With an assigned ticket, `open` can move to `in_progress`, `in_progress` to `resolved`, and `resolved` to `closed` or back to `open`. Other moves between the defined statuses receive HTTP 409 with `error.code` equal to `conflict`. After each accepted move, the ticket representation and assignee-filtered listing agree on the ticket's current assignment.
Source: existing: docs/api.md
Open: The requester decides any automatic assignee change on resolution, closure, or reopening, including whether a prior assignee is retained. A transition from `open` to `in_progress` is still work on the same active ticket.

### C-22: Overlapping ticket changes have effects consistent with their observed audit order
Observable: Send two competing assignment changes to an eligible ticket, or race assignment against the move from `in_progress` to `resolved`. The successful changes in the history show a coherent sequence of before and after values, and the final ticket agrees with those changes. An assignment that would change the assignee once the ticket is blocked by its status receives a conflict. Either request may take effect first.
Source: implied: U-1, U-2, and U-6 use the same ticket state

### C-23: A change to a named assignee records a notification for that agent
Observable: With `WORKER_INTERVAL_MS=0`, assign `T-0001` from `null` to Dana, then to Lee while Dana's notice is still pending. `GET /admin/outbox` shows a pending assignment notice for `T-0001` intended for Dana and another for Lee. The earlier notice cannot substitute for the notice intended for the new recipient.
Source: request
Open: The requester decides whether a later genuine return to the same agent, after an intervening reassignment or unassignment while their first notice is still pending, warrants a separate notice or can share the pending one.

### C-24: A repeated assignment to the current agent produces no new notification
Observable: Assign Dana, then repeat `{"assignee":"Dana"}` both in a run where the notice is still pending and in a run where it has already been sent. `GET /admin/outbox` shows no additional assignment notice caused by the repeat.
Source: request

### C-25: Clearing an assignee produces no assignment notification
Observable: Clear an assigned ticket with `{"assignee":null}`, or send `null` again to that eligible unassigned ticket. With the worker off, the requests add no assignment notice to `GET /admin/outbox`.
Source: implied: the request calls for notifying the agent the ticket is assigned to

### C-26: The service delivers assignment notices through its existing notification channel
Observable: With a working `NOTIFY_FILE` and a positive `WORKER_INTERVAL_MS`, assign `T-0001` to Dana. The relay feed receives a JSON line whose recipient identifies Dana, whose `ticket` is `T-0001`, and whose message says that the ticket was assigned to that recipient. The outbox records the notice as `sent`. With `WORKER_INTERVAL_MS=0`, assignment notices stay `pending` at zero attempts and no assignment line is delivered.
Source: existing: docs/operations.md
Open: The requester, with the relay operator, decides any required name-to-address mapping and any exact message wording or public notification label. The notice must reach the existing handoff with an identifiable intended agent.

### C-27: Assignment notices follow the existing retry policy on delivery failure
Observable: With the delivery destination unavailable, a valid assignment still succeeds. Its notice is `pending` after the first four failed attempts, due again after at least 1, 2, 4, and 8 seconds respectively. Restoring delivery before the next due attempt permits the notice to become `sent`. A fifth failure instead leaves it `dead` with `lastError` in `GET /admin/outbox` and ends automatic delivery attempts.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-28: Assignment leaves existing requester notifications available
Observable: Create a ticket with requester `maria@example.com`, assign it to Dana, then resolve it along the existing lifecycle. The outbox includes the `ticket.created` and `ticket.resolved` notices for `maria@example.com`.
Source: existing: docs/api.md

### C-29: An older valid data file still provides its tickets as unassigned
Observable: Start the service with a valid pre-assignment `DATA_FILE` whose ticket records lack `assignee`. The same tickets are readable with `"assignee":null`, including via `GET /tickets?assignee=`. The CLI can also list them as unassigned from that file.
Source: existing: docs/decisions/0008-json-data-file.md

### C-30: A completed change of assignee survives restart with `DATA_FILE` set
Observable: With the worker disabled, assign a ticket, then reopen the saved data in a fresh service instance. The ticket shows the assigned name and the same assignment audit entry and pending notice are present. Clear the assignee and reopen the saved data again. The ticket shows `"assignee":null`, and the clearing is still recorded in its history.
Source: existing: docs/decisions/0008-json-data-file.md

### C-31: A saved assignment has no partially committed state after an interruption
Observable: Interrupt the service during a new assignment to Dana with `DATA_FILE` set and the worker off. On restart the saved state is either the prior ticket, history, and outbox or the new assignment together with its audit entry and pending notice.
Source: existing: docs/decisions/0008-json-data-file.md

### C-32: The non-empty `assignee` filter selects the named agent's tickets
Observable: With tickets assigned to Dana, Lee, and no agent, `GET /tickets?assignee=Dana` lists Dana's tickets only. A name with no matching tickets yields `{"items":[],"next":null}`. A URL-encoded name such as `Dana%20Lee` can select tickets assigned to `Dana Lee`.
Source: request
Open: The requester decides how to interpret repeated `assignee` parameters with different values. Name equivalence follows the same decision as C-14.

### C-33: The empty `assignee=` filter selects unassigned tickets
Observable: `GET /tickets?assignee=` includes new unassigned tickets, older tickets with no saved assignee, and tickets cleared with `{"assignee":null}`. It excludes tickets with a current agent name.
Source: request

### C-34: Omitting `assignee` leaves assigned and unassigned tickets eligible for listing
Observable: With an assigned and an unassigned ticket matching `status=open`, both are eligible for `GET /tickets?status=open` and appear when its pages are read.
Source: implied: the request adds an optional filter to the existing listing

### C-35: `GET /tickets` requires every supplied ticket filter to match
Observable: With tickets that satisfy different subsets of the criteria, `GET /tickets?status=open&priority=urgent&assignee=Dana` returns only open, urgent tickets assigned to Dana. The same intersection applies with `assignee=` or with any subset of the three filter types, including `status` with `priority` alone.
Source: request

### C-36: Assignee-filtered listings keep the existing cursor page contract
Observable: Request a small page from a mixture of matching and nonmatching tickets. `items` is filled with matching tickets in ascending numeric ID order up to `limit`. If more matches remain, pass the opaque `next` as `cursor` with the same filters to continue after the last returned ID. When no later match remains, including when the page is exactly full or empty, `next` is `null`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-37: Assignee-filtered listings retain the existing query validation
Observable: With `assignee=Dana`, a request without `limit` uses 20 items per page, and `limit=1` through `limit=100` are accepted whole-number sizes. Zero, values above 100, non-whole-number input, and malformed cursors receive HTTP 400 with `error.code` equal to `invalid`. The allowed statuses are `open`, `in_progress`, `resolved`, and `closed`, and the allowed priorities are `low`, `normal`, `high`, and `urgent`. Values outside those sets receive the same error.
Source: existing: docs/api.md

### C-38: The command-line table listing displays the current assignee for each ticket
Observable: Run `node bin/tickets.js --data FILE list` on saved tickets assigned to Dana and Lee and on an unassigned ticket. The operator can associate each named assignee or unassigned indication with its ticket.
Source: request
Open: The requester decides whether the assignee must also appear in `list --raw` or `show`. The table label, placement, and unassigned display text may be chosen by the builder.

### C-39: The raw CLI listing preserves the existing positional fields
Observable: `node bin/tickets.js --data FILE list --raw` still emits one line per ticket with id, status, priority, and title in the first four tab-separated columns, including for assigned tickets. The weekly report can still count the same rows by status and priority using those positions.
Source: existing: README.md

### C-40: Existing CLI listing options preserve their ticket selection
Observable: Against a file containing open non-urgent tickets, urgent tickets in another status, and tickets matching neither, `list --status open --priority urgent` still includes the open or urgent tickets. Each option alone still selects by its own field.
Source: existing: bin/tickets.js and src/tickets/query.js

### C-41: The service still starts from `npm start` using `PORT`
Observable: On the documented Node.js 22 or later runtime, run `npm start` with `PORT` set to a free port. `GET /health` on that port returns HTTP 200 with `{"status":"ok"}`, and the assignment route is available on the same service.
Source: request

### C-42: The service requires no npm dependencies
Observable: In a checkout without installed packages, the documented Node.js runtime can start the service and exercise ticket assignment using `npm start` without installing packages.
Source: request

### C-43: The existing tests pass as supplied
Observable: Run `npm test` with the pre-change test files unchanged. The existing tests pass.
Source: request

### C-44: Assignment behavior has `node:test` coverage under `test/`
Observable: Run `npm test` and see new cases under `test/` execute through `node:test` for assignment, unassignment, state eligibility, repeated assignment, ticket representations, notifications, filtering, and CLI listing as part of the same run as the existing suite.
Source: request
