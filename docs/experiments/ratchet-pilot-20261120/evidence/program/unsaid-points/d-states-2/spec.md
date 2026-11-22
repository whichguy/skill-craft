## Use cases

### U-1: A help-desk dispatcher assigns a ticket to give an agent ownership
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an open ticket. A subsequent ticket read shows `"assignee":"Dana"`. Sending the same assignment again leaves the ticket as it was. Sending `{"assignee":"Sam"}` transfers the assignment to Sam.
Source: request

### U-2: A help-desk dispatcher clears an assignment to return a ticket to the unassigned queue
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an assigned open ticket. A subsequent ticket read shows `"assignee":null`. The ticket is eligible for `GET /tickets?assignee=`.
Source: request

### U-3: An agent receives notice of a ticket assignment so they know what was assigned to them
Flow: A dispatcher assigns an open ticket to Dana. Under normal notification delivery, Dana receives a notice that identifies the ticket and says it was assigned to them.
Source: request

### U-4: An API caller filters the queue to find tickets with the desired assignment
Flow: The caller uses `GET /tickets?assignee=Dana` for Dana's tickets or `GET /tickets?assignee=` for unassigned tickets. With `?assignee=Dana&status=open&priority=urgent` the caller sees only Dana's urgent open tickets. If more matches remain, the caller follows `next` as `cursor` with the same filters.
Source: request

### U-5: An operator lists tickets to see who owns each one
Flow: The operator runs `node bin/tickets.js --data FILE list` against the service's data file. Each listed ticket shows its assigned agent or indicates that it is unassigned.
Source: request

### U-6: An operator restarts the service to resume work with saved tickets
Flow: The operator starts the service with `DATA_FILE` set. Tickets from an older file without assignees appear unassigned. After the operator restarts the service using the same file, saved assignments are still visible.
Source: existing: docs/decisions/0008-json-data-file.md

## Clauses

### C-1: A valid assignment sets the ticket's assignee to the named agent
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an existing `open`, `in_progress`, or `resolved` ticket. A subsequent `GET /tickets/T-0001` shows `"assignee":"Dana"` whether the ticket started unassigned or assigned to another agent.
Source: request

### C-2: An explicit JSON null clears the ticket's assignee
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an assigned ticket in `open`, `in_progress`, or `resolved`. A subsequent `GET /tickets/T-0001` shows `"assignee":null`.
Source: request

### C-3: The assignment endpoint acknowledges a successful request with an HTTP success status
Observable: A valid PUT on an open ticket returns a 2xx status, including when the request leaves its assignee as it was.
Source: choice: Callers need to distinguish success from failure. The request leaves the particular success status and response shape to the build.

### C-4: Every ticket object returned by the API includes its current assignee
Observable: A freshly created ticket contains `"assignee":null`. The ticket objects from create, get, list, patch, transition, and any PUT response that returns a ticket always include `assignee` as the current agent name or JSON null.
Source: request

### C-5: Assignment changes preserve the ticket's fields outside the assignment and its modification time
Observable: Compare the ticket before and after assigning, reassigning, or unassigning it. Its `id`, `title`, `priority`, `requester`, `status`, and `created` are identical.
Source: implied: U-1 and U-2 change ownership only.

### C-6: Existing ticket edits preserve the current assignee
Observable: Assign Dana, change the ticket title or priority with `PATCH /tickets/:id`, or move it along a permitted lifecycle transition with `POST /tickets/:id/transition`. The ticket still shows `"assignee":"Dana"` after each operation.
Source: implied: U-1 changes ownership through the assignment endpoint while existing edits retain their documented scope.

### C-7: The assignment endpoint accepts only JSON objects within the existing request body limit
Observable: An absent or empty body, malformed JSON, a top-level array, null or scalar, or a body larger than `MAX_BODY_BYTES` returns 400 `invalid`. The default is 65,536 bytes. A valid JSON object padded to exactly the configured byte limit is eligible for acceptance.
Source: existing: src/http.js

### C-8: The assignment endpoint rejects unknown body fields
Observable: A PUT body such as `{"assignee":"Dana","owner":"Dana"}` returns 400 `invalid`.
Source: existing: docs/api.md

### C-9: The assignment endpoint requires an explicit assignee value
Observable: A body of `{}` returns 400 `invalid`. A value given as a number, boolean, array, or object also returns 400 `invalid`. Explicit JSON null is a valid value for unassignment.
Source: implied: The request's two PUT bodies require a name string or explicit null.

### C-10: An agent name is non-empty with an inclusive maximum of 64 characters
Observable: For an open ticket, names made of 1 or 64 ASCII letters are accepted. The empty string or a name made of 65 ASCII letters returns 400 `invalid`.
Source: request
Open: The requester can specify name handling beyond these boundaries, including leading or trailing whitespace, whitespace-only names, control characters, and how to count non-ASCII characters. The existing text rules name other fields.

### C-11: An assignment request for a ticket that does not exist returns 404
Observable: Send a valid PUT body for an unused ticket ID. The response status is 404 with `error.code` equal to `not_found`.
Source: existing: docs/api.md

### C-12: A closed ticket refuses an actual assignment change
Observable: Close an unassigned ticket and try to assign it, or close an assigned ticket and try to replace or clear its assignee. The PUT returns 409 `conflict`. The statuses eligible for an actual assignment change are `open`, `in_progress`, and `resolved`.
Source: existing: docs/api.md
Open: The requester can settle whether a same-value PUT on a closed ticket acknowledges the no-op or returns the closed-ticket conflict. The ticket remains unchanged either way.

### C-13: Assignment errors use the service's JSON error envelope
Observable: A rejected assignment response has `content-type: application/json; charset=utf-8` and a body containing `{"error":{"code":"<code>","message":"<human-readable message>"}}`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-14: A rejected assignment leaves the prior assignment state intact
Observable: Read the ticket, audit history, and outbox before and after an invalid or closed-ticket PUT with delivery disabled. The ticket, history, and outbox entries are identical. A valid PUT targeting a missing ticket creates no ticket or associated audit or outbox entry.
Source: implied: U-1 and U-2 act only on a valid change to an eligible ticket.

### C-15: A real change of assignee updates the ticket's modification time
Observable: After the clock has advanced past the ticket's previous `updated` value, assign, reassign, or unassign the ticket. A subsequent read shows `updated` as the change time in UTC ISO 8601.
Source: existing: docs/api.md

### C-16: Repeating an assignment value leaves the ticket unchanged
Observable: Assign Dana, then send `{"assignee":"Dana"}` again after the clock has advanced. The whole ticket, including `updated`, is identical. The same holds when sending `{"assignee":null}` to an already unassigned open ticket.
Source: request

### C-17: An actual assignment change appends one audit entry
Observable: `GET /tickets/:id/audit` shows one new last entry after each assignment, reassignment, or unassignment. Its `changes.assignee` records the previous and new values as `{"from":null,"to":"Dana"}`, `{"from":"Dana","to":"Sam"}`, or `{"from":"Sam","to":null}` as applicable. The entry has the ticket ID, the change time, an action describing the change, and the next sequence number in the whole log. Earlier entries retain their contents.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-18: The audit entry attributes an assignment change to the request actor
Observable: A PUT making a change with `X-Actor: dispatcher` records `"actor":"dispatcher"`. An absent or blank header records `"actor":"system"`. The service trims the header. A 64-character trimmed actor is accepted and one of 65 characters returns 400 `invalid`.
Source: existing: src/http.js

### C-19: A same-value assignment request adds no audit entry
Observable: After assigning Dana, compare the ticket history before and after sending `{"assignee":"Dana"}` again. It is identical. Clearing an already unassigned ticket likewise adds no entry. If two valid requests overlap while setting the same new assignee, the history shows only one change to that assignee.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-20: A new assignment records a notification for the incoming agent
Observable: With `WORKER_INTERVAL_MS=0`, assigning an unassigned ticket to Dana makes an assignment notice for Dana and that ticket visible in `pending` at `GET /admin/outbox`. Reassigning it to Sam before delivery makes a notice for Sam and that ticket visible too.
Source: implied: U-3 requires the recipient of each new assignment to be notified through the existing notification path.
Open: When the same ticket returns to the same agent while an earlier notice for that agent and ticket is still pending, the requester can settle whether the pending notice suffices or the later assignment needs a separate notice.

### C-21: A same-value assignment request creates no additional notification
Observable: Compare the outbox before and after repeating a PUT for the ticket's current assignee. There is no additional entry, whether the original notice is pending or sent.
Source: existing: CONTRIBUTING.md

### C-22: Clearing an assignment creates no assignment notification
Observable: With the worker off, compare the outbox before and after sending `{"assignee":null}` to clear a named assignee. No new assignment notice appears.
Source: implied: U-2 leaves no incoming agent for the notice in U-3.

### C-23: The service delivers assignment notices through its normal notification channel
Observable: With the worker enabled and a writable `NOTIFY_FILE`, a due assignment notice produces a JSON line addressed to the assigned agent in `to`, identifying the ticket in `ticket`, with a message saying the ticket was assigned to the recipient. `GET /admin/outbox` records the delivery under `sent`.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-24: Failed assignment notification delivery follows the existing retry policy
Observable: Make the notification destination fail. An accepted assignment remains visible, while its pending notice shows failed attempts and becomes eligible to retry after 1, 2, 4, then 8 seconds after the respective failures. A fifth failed attempt leaves it in `dead` with `lastError` visible. Restoring the destination while the notice is pending allows the next due attempt to deliver it.
Source: existing: docs/operations.md

### C-25: Saved assignment changes survive a restart
Observable: With `DATA_FILE` set, assign a ticket to Dana, restart using the same file, and read `"assignee":"Dana"`. Clear the assignment, restart again, and read `"assignee":null`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-26: A saved assignment change is recoverable as one whole change
Observable: With `DATA_FILE` set and the worker off, interrupt the process during an assignment from null to Dana. On loading the same file, either the old unassigned state is visible or Dana is the assignee with the corresponding audit entry and pending notice. A completed assignment is already saved by the time the caller receives success.
Source: existing: docs/decisions/0008-json-data-file.md

### C-27: Previously valid data files without assignees open with their tickets unassigned
Observable: Start the service using a valid pre-assignment data file. Its tickets are still present with `"assignee":null`, so they qualify for `GET /tickets?assignee=`. Their existing ticket IDs, fields, and history are retained.
Source: existing: docs/decisions/0008-json-data-file.md

### C-28: Saved tickets with an invalid assignee value are reported as invalid data
Observable: Start with a data file containing a ticket with an `assignee` value of `42`, `""`, or a name made of 65 ASCII letters. The service refuses to start and identifies the offending record. A missing field in a pre-assignment file is eligible for the unassigned default.
Source: existing: docs/decisions/0008-json-data-file.md

### C-29: A named assignee filter selects that agent's tickets
Observable: Given tickets assigned to Dana, assigned to Sam, and unassigned, `GET /tickets?assignee=Dana` returns Dana's tickets only. A valid ordinary name with no matching tickets returns `{"items":[],"next":null}`.
Source: request
Open: The requester can specify how spelling variants are matched, such as case differences or Unicode normalization, and what to do with a non-empty filter value outside the accepted name rules or repeated `assignee` query keys.

### C-30: An explicitly empty assignee filter selects unassigned tickets
Observable: In the same mixed queue, `GET /tickets?assignee=` returns only tickets with `"assignee":null`.
Source: request

### C-31: Omitting the assignee filter imposes no assignment condition
Observable: With both assigned and unassigned tickets matching any other filters, `GET /tickets` without `assignee` includes both kinds across its pages.
Source: implied: U-4 adds a filter that applies when the caller gives it.

### C-32: Listing filters combine by intersection
Observable: On `GET /tickets?assignee=Dana&status=open&priority=urgent`, a ticket appears only if assigned to Dana, open, and urgent. With `assignee=`, the assignment condition is unassigned. With only `status` and `priority` supplied, both must still match.
Source: request

### C-33: Assignee-filtered listings use the existing cursor pagination over matching tickets
Observable: In a queue with matches interleaved among nonmatches, `GET /tickets?assignee=Dana&limit=2` returns the first two matching tickets in numeric ID order when at least two exist. Reuse the opaque `next` as `cursor` with the same filters to continue after the last returned ID even if that ticket no longer matches. The response has `items` and `next`, with `next:null` when no matches remain, including on an empty page. The page size defaults to 20. Limits from 1 to 100 inclusive are accepted, while a limit outside that range, a non-integer limit, or a malformed cursor returns 400 `invalid`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-34: The operator's ticket listing shows each listed ticket's assignee
Observable: Run `node bin/tickets.js --data FILE list` for a file with assigned and unassigned tickets. The listing associates Dana with Dana's ticket and distinguishes an unassigned row from an assigned row.
Source: request
Open: The requester can settle whether this display is also required in `list --raw`. The documented columns used by existing consumers apply in either case.

### C-35: The raw CLI listing preserves the positional fields used by existing consumers
Observable: `node bin/tickets.js --data FILE list --raw` prints one line per listed ticket, with tab-separated fields 1 through 4 holding ID, status, priority, and title respectively, even for assigned tickets.
Source: existing: README.md

### C-36: The weekly report continues to count all listed tickets by status and priority
Observable: Run `node scripts/weekly-report.js --data FILE --json` on a known set of assigned and unassigned tickets. Its `total`, `byStatus`, and `byPriority` match the counts from the saved tickets.
Source: existing: scripts/weekly-report.js

### C-37: Starting the service still honors the configured port
Observable: Set `PORT` to an available port and run `npm start`. `GET /health` at that port returns `{"status":"ok"}`.
Source: request

### C-38: The service still runs without installing npm dependencies
Observable: In a checkout with Node.js 22 or later and no installed packages, `npm start` starts the service and serves ticket requests.
Source: request

### C-39: Existing service behavior remains compatible outside the requested changes
Observable: Existing ticket operations, requester notices, operator commands, and API error responses still meet the behavior documented in `README.md`, `docs/api.md`, and `docs/operations.md` wherever assignment changes leave that behavior in place.
Source: request

### C-40: The unchanged existing test suite passes
Observable: Run `npm test` with the original test files unchanged. The original cases pass.
Source: request

### C-41: The standard test command runs the new assignment tests
Observable: New `node:test` cases under `test/` exercise assignment and unassignment, same-value requests, the assignee shown in tickets, assignment notices, assignee filtering, and CLI display. `npm test` runs them alongside the original suite.
Source: request
