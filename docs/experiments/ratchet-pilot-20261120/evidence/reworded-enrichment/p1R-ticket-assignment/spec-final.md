## Use cases

### U-1: A help-desk operator assigns a ticket to give an agent responsibility for it
Flow: The operator sends PUT /tickets/:id/assignee with {"assignee":"Alex Kim"} for an open or in-progress ticket. The ticket shows "Alex Kim" as its assignee. The operator can replace a previous assignee the same way. Repeating the request for the current assignee has no effect.
Source: request

### U-2: A help-desk operator clears an assignment to put the ticket back in the unassigned queue
Flow: The operator sends PUT /tickets/:id/assignee with {"assignee":null} for an open or in-progress ticket. The ticket shows "assignee":null and appears in GET /tickets?assignee=. A request to change the assignment on a resolved or closed ticket is refused.
Source: request

### U-3: An agent receives notice of a ticket assigned to them so they know which ticket to work on
Flow: An operator assigns a ticket to the agent. The agent receives a notice identifying the ticket and saying that it was assigned to them. A repeat of the same assignment while they are still the assignee produces no further notice.
Source: request

### U-4: An API client filters tickets to find an agent's work or tickets awaiting assignment
Flow: The client requests GET /tickets?assignee=Alex%20Kim for Alex Kim's tickets, or GET /tickets?assignee= for unassigned tickets. It can add status=open and priority=urgent to narrow either result to tickets meeting every supplied filter. If a page returns a next cursor, it uses that cursor with the same filters to continue.
Source: request

### U-5: An operator lists tickets on the command line to see who has each one
Flow: The operator points bin/tickets.js at the service's data file using DATA_FILE or --data FILE and runs list. Each listed row shows the agent's name or indicates that the ticket is unassigned. The weekly report continues to read the raw listing and count tickets by status and priority.
Source: implied: the command-line listing request and the raw output contract in README.md

### U-6: An auditor reads a ticket's history to trace a change of assignee
Flow: An operator changes an assignment with X-Actor: dana. The auditor reads GET /tickets/:id/audit and sees a new entry by dana with the assignee's previous and new values.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### U-7: A service operator restarts the service to resume work from saved state
Flow: The operator starts the service with an existing DATA_FILE. Tickets from before assignment was available show "assignee":null. After a new assignment is made and the service is restarted, the assignment, its history and any pending notice are still available.
Source: existing: docs/decisions/0008-json-data-file.md

### U-8: A service operator inspects the outbox to see whether an assignment notice was delivered
Flow: The operator reads GET /admin/outbox. With WORKER_INTERVAL_MS=0 the notice stays pending. With delivery running, a successful attempt moves it to sent. Repeated delivery failures lead to a dead entry the operator can inspect.
Source: existing: docs/operations.md

### U-9: A maintainer runs the tests to verify assignment without breaking the service
Flow: The maintainer runs npm test. It runs the new node:test tests under test/ along with the existing tests, which pass as written.
Source: request

## Clauses

### C-1: A valid agent name sent to PUT /tickets/:id/assignee becomes the assignee of an open or in-progress ticket
Observable: On an open or in_progress ticket, send {"assignee":"Alex Kim"} when it is unassigned or assigned to a different agent. The PUT succeeds with a 2xx status. GET /tickets/:id then shows "assignee":"Alex Kim".
Source: request
Open: The requester would settle the exact success status or whether the PUT must return the ticket representation. The existing ticket mutation endpoints return a ticket with 200.

### C-2: A null assignee sent to PUT /tickets/:id/assignee clears an open or in-progress ticket's assignment
Observable: On an assigned open or in_progress ticket, send {"assignee":null}. The PUT succeeds. GET /tickets/:id then includes "assignee":null.
Source: request

### C-3: An assignment request that changes the assignee leaves the ticket's other business fields intact
Observable: Compare the ticket before and after assigning, reassigning or clearing it. Its id, title, priority, requester, status and created values are identical.
Source: implied: PUT /tickets/:id/assignee changes who is responsible for the specified ticket

### C-4: Setting an eligible ticket's assignee to its current value changes nothing
Observable: On an open or in_progress ticket, repeat the same assignment or send {"assignee":null} when it already has a null assignee. The request succeeds, the ticket including updated reads back identically, its audit history is identical, and no new notification is queued even if the earlier notice has already been sent.
Source: request

### C-5: Any attempt to change the assignee of a resolved or closed ticket is a conflict
Observable: Send a valid PUT that would set a different agent or clear an existing assignee on a resolved or closed ticket. The response is HTTP 409 with error.code "conflict". The ticket keeps its previous assignee. The eligible states are open and in_progress.
Source: existing: docs/api.md
Open: The requester would settle whether a valid PUT for a resolved or closed ticket that already holds the requested value returns conflict or succeeds with no effect.

### C-6: An assignment request for a missing ticket returns not_found
Observable: Send a well-formed PUT /tickets/T-0042/assignee when T-0042 does not exist. The response is HTTP 404 with error.code "not_found".
Source: existing: docs/api.md

### C-7: The assignment endpoint rejects invalid JSON bodies or assignee values
Observable: HTTP 400 with error.code "invalid" results from an absent, blank or malformed JSON body, a JSON array or scalar body including bare null, an object missing assignee, an object with an extra field, or an assignee value that is an array, object, boolean, number, empty string or a string of 65 ordinary ASCII letters. In an otherwise valid request to an eligible ticket, names of exactly 1 and 64 ordinary ASCII letters are accepted, as is the explicit value null for clearing.
Source: implied: the request's JSON object and name bounds under the request-body conventions in docs/api.md
Open: The requester would settle whether to trim or reject whitespace-only names, whether names can contain control characters or line breaks, and how to count characters in non-ASCII names. The existing title and requester fields are trimmed single-line text and use JavaScript string length.

### C-8: The assignment endpoint honors the existing request body size limit
Observable: A valid assignment body padded with JSON whitespace to exactly MAX_BODY_BYTES bytes is accepted on an eligible ticket. At one byte over, the response is HTTP 400 with error.code "invalid". The default limit is 65,536 bytes.
Source: existing: src/http.js

### C-9: The assignment endpoint applies the existing X-Actor length limit
Observable: With an otherwise valid assignment request, a trimmed X-Actor of 64 ASCII letters is accepted. A trimmed X-Actor of 65 ASCII letters gets HTTP 400 with error.code "invalid".
Source: existing: src/http.js

### C-10: A rejected assignment has no effects of an accepted change
Observable: After a request refused for invalid input, a missing ticket or a disallowed state, no ticket has changed. The audit and outbox show no entry caused by the rejected request.
Source: implied: refusal means the assignment did not take place

### C-11: Assignment errors use the service's JSON error envelope
Observable: The caller receives application/json; charset=utf-8 with an error object containing the status's string code and a human-readable message. The conventions are invalid for 400, not_found for 404, conflict for 409 and internal for 500. An internal fault has a generic message.
Source: existing: docs/decisions/0004-error-envelope.md

### C-12: Every ticket returned by the HTTP API includes its current assignee
Observable: Inspect the ticket from POST /tickets, GET /tickets/:id, items in GET /tickets, PATCH /tickets/:id or POST /tickets/:id/transition. Each ticket object includes assignee, with the current agent's name or the JSON value null. A newly created ticket shows null.
Source: request

### C-13: Existing title and priority edits or lifecycle transitions preserve the ticket's assignee
Observable: After assigning a ticket, edit its title or priority or take an allowed lifecycle step. The response ticket retains its assignee, including on resolution, closing or reopening. A ticket with a null assignee keeps null through the same operations.
Source: existing: src/store.js

### C-14: A change of assignee updates the ticket's last-change time
Observable: Make a real assignment change after the original updated time, including a change to null. The ticket's updated field gives the change time in ISO 8601 UTC.
Source: existing: docs/api.md

### C-15: Each change of assignee appends one audit entry
Observable: GET /tickets/:id/audit shows the new entry after the existing entries, which are preserved. The new entry has the ticket id, change time and next sequence position in the whole log. Its changes.assignee has from and to values for the assignment, reassignment or clearing, using null for an unassigned side.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-16: An assignment audit entry identifies the actor under the existing header convention
Observable: Change the assignee with X-Actor: dana and see "actor":"dana" in the new history entry. A header with outer spaces records its trimmed value. An omitted or blank header records "actor":"system".
Source: existing: src/http.js

### C-17: Assignment eligibility uses the ticket state when the change takes effect
Observable: Race a PUT changing the assignee against a transition from in_progress to resolved. Either the assignment took effect while in_progress and appears before the transition in history, or the transition took effect first and the PUT is refused with 409 conflict without changing the assignee.
Source: implied: only open and in-progress tickets can have their assignment changed

### C-18: Overlapping requests to set the same assignee produce a single change
Observable: Send two otherwise valid PUT requests for "Alex Kim" to the same eligible ticket currently held by someone else or by no one. With no intervening mutation, the ticket ends assigned to Alex Kim, with one assignee audit entry and one new assignment notice.
Source: implied: assigning a ticket to its current agent changes nothing

### C-19: A new assignment produces a notice for the agent who received it
Observable: With delivery available, assign T-0001 to an agent. The notice identifies T-0001 and conveys that the ticket was assigned to the recipient. If T-0001 is then assigned to a different agent, the new agent's notice is addressed to that agent even if the earlier notice is pending.
Source: request
Open: The requester or the operator of the existing mail relay would settle how a supplied agent name identifies its delivery recipient if the relay needs an address different from the name. The request accepts ordinary names as assignees.

### C-20: Clearing a ticket produces no new assignment notice
Observable: Clear an assigned ticket with {"assignee":null}. There is no new outbox entry announcing an assignment for that change.
Source: implied: the request calls for a notice to the agent a ticket is assigned to

### C-21: A newly assigned ticket has an outbox entry for the assignment when the change succeeds
Observable: With WORKER_INTERVAL_MS=0, assign a ticket and see its assignment notice pending in GET /admin/outbox as soon as the PUT has succeeded. It identifies the ticket and recipient and remains pending while delivery is off. When a different agent is assigned while the first notice is pending, the new agent has their own notice.
Source: existing: docs/decisions/0006-notification-outbox.md
Open: The requester would settle whether two distinct assignments of the same ticket to the same agent may share one pending notice if an unassignment or a different assignee came between them. This is separate from a repeat PUT that made no change.

### C-22: Delivery of an assignment notice uses the existing notification output
Observable: With delivery enabled and a writable NOTIFY_FILE, a delivered assignment appears as a JSON line identifying its ticket and recipient with the message that it was assigned. GET /admin/outbox shows the delivery as sent. With no NOTIFY_FILE, successful in-memory delivery is still reflected as sent.
Source: existing: docs/operations.md

### C-23: Notification delivery failure does not make an assignment fail
Observable: With a working ticket store and an unavailable notification destination, an eligible assignment still succeeds and is visible on the ticket. Delivery failure is visible through the outbox.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-24: A failed assignment notice follows the existing outbox retry schedule
Observable: When delivery fails, GET /admin/outbox shows the notice pending with its attempt count and lastError. The next attempts are due 1, 2, 4 and 8 seconds after failures one through four, respectively, and run on worker ticks. After the fifth failure the entry stays dead with its lastError and is no longer retried.
Source: existing: docs/operations.md

### C-25: Assignment notices retain the existing at-least-once behavior on interruption during delivery
Observable: If the process stops after emitting a notice but before its send is recorded in DATA_FILE, the same notice can be emitted again after restart with the same key and id. A notice already recorded as sent is not due again.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-26: The existing requester notices still go to the requester
Observable: Creating a ticket produces the ticket.created notice for its requester. Resolving it, including when assigned to an agent other than the requester, produces the ticket.resolved notice for the requester.
Source: existing: docs/api.md

### C-27: A saved assignment change survives restart as a whole
Observable: With DATA_FILE, restart after a successful assignment, reassignment or clearing. The assignee value and audit entry survive. Any notice queued for the change still has its recorded delivery state. If the process is interrupted during the save, the recovered file represents the state before or after the change, without a partial assignment, history or outbox update.
Source: existing: docs/decisions/0008-json-data-file.md

### C-28: A data file from before ticket assignment remains usable
Observable: Start the service with a valid data file written by the previous version, whose ticket records have no assignee. The existing tickets load with assignee null, appear under GET /tickets?assignee=, and retain their existing data, history and outbox entries.
Source: existing: docs/decisions/0008-json-data-file.md

### C-29: The named assignee filter returns tickets assigned to the requested agent
Observable: With tickets assigned to Alex Kim, tickets assigned to other agents, and unassigned tickets, GET /tickets?assignee=Alex%20Kim returns only Alex Kim's tickets, subject to any other filters or paging. If there is no ticket for that ordinary name, the result is {"items":[],"next":null}.
Source: request
Open: The requester would settle whether case, whitespace or Unicode variants identify the same agent for filtering or repeat assignment. The requester would also settle the query behavior for out-of-range names or repeated assignee keys.

### C-30: The empty assignee filter returns unassigned tickets
Observable: GET /tickets?assignee= includes tickets with assignee null and excludes tickets assigned to any agent, subject to other filters or paging. After a ticket's assignment is cleared, it qualifies for this filter.
Source: request

### C-31: Omitting the assignee filter imposes no restriction on assignment
Observable: With both assigned and unassigned tickets on one page, GET /tickets without assignee includes both when they pass any other supplied filters.
Source: implied: the request specifies assignee filtering only when the parameter is supplied

### C-32: Each ticket in a filtered list satisfies every supplied filter
Observable: GET /tickets?assignee=Alex%20Kim&status=open&priority=urgent includes only open urgent tickets assigned to Alex Kim. With assignee=, it includes only open urgent unassigned tickets. GET /tickets?status=open&priority=urgent also requires both filters when assignee is omitted.
Source: request

### C-33: Cursor pages contain matching tickets in ticket id order
Observable: Request a small page with an assignee filter and matching tickets interleaved by id with nonmatches. The page fills up to its limit with matches in numeric ticket id order. Passing next as cursor with the same filters continues strictly after the last id shown, applying the filters to current ticket values. The response shape is {"items":[...],"next":...}, with next null when no matches remain, including on an empty page.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-34: The list with an assignee filter keeps the existing page-size bounds
Observable: With a valid assignee filter, the default limit is 20. Whole-number limits from 1 through 100 inclusive are accepted. Zero, 101, negative, fractional, empty or nonnumeric limits return HTTP 400 with error.code "invalid".
Source: existing: docs/api.md

### C-35: An invalid cursor is refused in a list with an assignee filter
Observable: Send GET /tickets?assignee=Alex%20Kim&cursor=abc. The response is HTTP 400 with error.code "invalid".
Source: existing: docs/api.md

### C-36: The command-line table shows each listed ticket's assignee
Observable: With a service data file containing a mix of assigned and unassigned tickets, run node bin/tickets.js list using DATA_FILE or --data FILE. The table associates each assigned row with its agent's name and indicates the absence of an assignee for unassigned rows. The existing --status and --priority options still select the listed tickets.
Source: request
Open: The requester would settle whether the machine-readable list --raw also needs to expose assignee. The existing raw fields retain their positions either way.

### C-37: The command-line raw listing preserves its existing field positions
Observable: Run node bin/tickets.js list --raw against data with assigned and unassigned tickets. There is one tab-separated line per ticket, with id, status, priority and title in positions 1, 2, 3 and 4 respectively. The weekly report still yields the same counts by status and priority for the same tickets regardless of assignee.
Source: existing: README.md

### C-38: The command-line listing can be used without changing the service's data file
Observable: Run list against a valid DATA_FILE with assigned and unassigned tickets. Comparing the data file before and after the command shows identical contents.
Source: existing: docs/operations.md

### C-39: The existing npm start command serves the API on the configured PORT
Observable: Run npm start with a free PORT and GET /health on the port where it listens. The response is {"status":"ok"}. PORT=0 lets the system choose a free port, which appears in the startup log. With PORT unset or empty, the configured default is 4180.
Source: existing: README.md

### C-40: The service runs without installing npm dependencies
Observable: On Node.js 22 or later, a checkout without installed npm packages can start the service and use the assignment endpoint.
Source: existing: README.md

### C-41: Existing tests still pass as written
Observable: Running npm test reports all pre-existing tests passing, with their files and assertions intact.
Source: request

### C-42: The test suite includes new node:test coverage for ticket assignment behavior
Observable: The test/ directory contains new node:test tests exercising the assignment API, the effects of assignment changes, assignee filtering and the command-line listing.
Source: request

### C-43: The npm test command runs the new tests alongside the existing tests
Observable: A single npm test run discovers and runs both the newly added assignment tests under test/ and the existing suite.
Source: request

### C-44: A failed save leaves an assignment available to retry
Observable: With DATA_FILE enabled, an otherwise valid assignment change fails because the service cannot replace its data file. The PUT returns HTTP 500 with error.code "internal". The live ticket, its audit history and the outbox show no effects of the failed PUT. Once saving works again, retrying the same request makes the change and it survives restart.
Source: implied: U-7 requires a saved assignment to survive restart, and U-1 and U-3 require that retrying a change and repeating a completed assignment have different effects
