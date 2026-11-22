## Use cases

### U-1: A help-desk dispatcher assigns a ticket so an agent can pick it up
Flow: The dispatcher sends `PUT /tickets/T-0042/assignee` with `{"assignee":"Dana Lee"}` for an `open` or `in_progress` ticket. Reading the ticket shows `"assignee":"Dana Lee"`. The dispatcher can send a different name to reassign it. Sending the current name again leaves the ticket as it was.
Source: request

### U-2: A help-desk dispatcher clears an assignment so the ticket returns to the unassigned queue
Flow: The dispatcher sends `PUT /tickets/T-0042/assignee` with `{"assignee":null}` for an `open` or `in_progress` ticket. A subsequent read shows `"assignee":null`. For `resolved` or `closed` tickets, the service refuses the assignment or unassignment with HTTP 409 and error code `conflict`.
Source: request

### U-3: An agent receives notice of a ticket assigned to them so they know what to pick up
Flow: When the dispatcher assigns `T-0042` to `Dana Lee`, the service queues a notice for `Dana Lee`. When delivery is enabled and succeeds, the notice identifies `T-0042` as assigned to the recipient.
Source: request

### U-4: A dashboard caller filters tickets to find an agent's work or the unassigned queue
Flow: The caller sends `GET /tickets?assignee=Dana%20Lee` for Dana Lee's tickets or `GET /tickets?assignee=` for unassigned tickets. The caller can add `status=open&priority=urgent` to narrow either result, then pass a returned `next` as `cursor` with the same filters.
Source: request

### U-5: A command-line operator lists tickets to see who has each one
Flow: The operator runs `node bin/tickets.js --data FILE list` against the service's data file. Each listed ticket shows its assignee or indicates that it is unassigned.
Source: request

### U-6: An operator inspects a ticket's history to see who changed its assignment
Flow: The operator supplies `X-Actor: sam` on an assignment change. The operator reads `GET /tickets/T-0042/audit` to see who made the change, when it happened, and the former and new assignee values.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### U-7: A service operator restarts the service to resume work with saved assignments
Flow: The operator runs `npm start` with `PORT` and `DATA_FILE` set. After a saved assignment change, the operator stops the service with `SIGTERM` and starts it again with the same file. Reading the ticket and its history shows the saved change. A pending assignment notice remains available for delivery.
Source: existing: docs/operations.md

### U-8: A maintainer runs the test suite to verify assignment behavior alongside existing behavior
Flow: The maintainer runs `npm test`. The existing tests run as written alongside the assignment tests under `test/`.
Source: request

## Clauses

### C-1: A named assignment replaces the current assignee of an active ticket
Observable: For a ticket in either `open` or `in_progress`, send `PUT /tickets/:id/assignee` with `{"assignee":"Dana Lee"}`. A subsequent ticket read shows `"assignee":"Dana Lee"` whether the old value was `null` or another agent's name.
Source: request

### C-2: A null assignment clears the assignee of an active ticket
Observable: For an assigned ticket in either `open` or `in_progress`, send `PUT /tickets/:id/assignee` with `{"assignee":null}`. A subsequent ticket read shows `"assignee":null`.
Source: request

### C-3: The assignment route refuses requests for inactive tickets
Observable: On a `resolved` or `closed` ticket, a well-formed `PUT /tickets/:id/assignee` with a name or `null` returns HTTP 409 with `error.code` equal to `conflict`, including when the submitted value already equals the current value.
Source: implied: the request permits assignment and unassignment only in open and in-progress states, and docs/api.md defines refusals based on state

### C-4: A PUT of the current assignee on an active ticket is a no-op
Observable: Repeat a successful named assignment or a successful clear with the same value on an `open` or `in_progress` ticket. The request succeeds. The ticket including `updated`, its audit history, and its notification entries show no effect from the repeat.
Source: implied: the request says assigning the current agent changes nothing, and CONTRIBUTING.md applies that rule to any unchanged value
Open: The requester decides whether case variants or differently spaced spellings denote the same agent. An exact repeat of an accepted name is always a no-op.

### C-5: An assignment PUT reports success for a valid operation on an existing active ticket
Observable: A well-formed assignment, unassignment, or repeat of the current value for an existing `open` or `in_progress` ticket receives a 2xx response.
Source: choice: callers need to distinguish an operation the service accepted from one it refused, and the request leaves the exact success response to the implementation

### C-6: The assignment PUT requires a JSON object with the assignment field
Observable: An absent body, malformed JSON, a top-level array, `null` or other non-object JSON, an object missing `assignee`, or an object with any field other than `assignee` returns HTTP 400 with `error.code` equal to `invalid`.
Source: implied: the request specifies an assignee object, and docs/api.md requires object bodies and refusal of unknown fields

### C-7: The assignment value must be null or a non-empty agent name
Observable: With an existing active ticket, `{"assignee":null}` and `{"assignee":"Dana Lee"}` are valid. `{"assignee":""}` and values of type number, boolean, object, or array receive HTTP 400 with `error.code` equal to `invalid`.
Source: request
Open: The requester decides whether to trim surrounding whitespace, how to treat whitespace-only values or line and tab characters, and whether to set a name-specific length bound beyond the existing whole-body limit. The title and requester limits apply to their own fields.

### C-8: The existing body size limit applies to the assignment PUT
Observable: The service accepts a valid assignment object at the configured `MAX_BODY_BYTES` boundary, including when padded with JSON whitespace. One byte above that boundary yields HTTP 400 with `error.code` equal to `invalid`. The default is 65,536 bytes.
Source: existing: README.md and src/http.js

### C-9: The assignment PUT reports a missing ticket through the existing error contract
Observable: A well-formed assignment PUT to a ticket id absent from the service returns HTTP 404 with `error.code` equal to `not_found`.
Source: existing: docs/api.md

### C-10: Assignment errors use the service's JSON envelope
Observable: A refused assignment request returns JSON with `content-type: application/json; charset=utf-8` and `{"error":{"code":"<code>","message":"<human-readable message>"}}`. An unexpected service fault returns HTTP 500 with code `internal` and the message `internal error`.
Source: existing: docs/api.md and src/errors.js

### C-11: A rejected assignment request has no assignment effects
Observable: With delivery disabled, compare the ticket, its audit history, and the outbox before and after a malformed or state-conflicting assignment PUT. The request leaves all three as they were.
Source: implied: the assignment conditions in the request and the existing validation and conflict behavior in docs/api.md

### C-12: Each ticket returned by the HTTP API has its current assignee
Observable: Inspect a ticket object returned by creation, detail, listing, patch, transition, or any assignment response that returns a ticket. Its `assignee` is the current agent name or JSON `null` when unassigned. A newly created ticket shows `"assignee":null`.
Source: request

### C-13: An assignment change leaves the ticket's other business fields intact
Observable: Compare ticket reads across a successful assignment change. The id, title, priority, requester, status, and creation time have the same values before and after.
Source: implied: U-1 and U-2 target the assignment of an existing ticket

### C-14: A real assignment change advances the ticket's last-change time
Observable: Assign, reassign, or clear at an observably later time than the previous change. A ticket read shows `updated` as the time of the assignment change, in the existing UTC ISO 8601 format.
Source: existing: docs/api.md

### C-15: Each real assignment change appends one entry to the ticket's history
Observable: After assigning, reassigning, or clearing, `GET /tickets/:id/audit` shows one new entry at the end, with the next global sequence number, ticket id, change time, an action describing the change, and `changes.assignee` containing the previous value as `from` and the new value as `to`. Unassigned values in the entry are JSON `null`. Earlier entries remain as they were.
Source: existing: docs/decisions/0007-append-only-audit-log.md
Open: The requester can specify the assignment action label if a consumer needs a fixed value. Existing audit action labels retain their meanings.

### C-16: The assignment audit identifies the actor under the existing header convention
Observable: Make separate real assignment changes with `X-Actor: sam` and with the header absent or blank. The new entries record `actor` as `sam` and `system`, respectively. A trimmed header of 64 characters is accepted. At 65 characters the PUT receives HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md and src/http.js

### C-17: Existing ticket write bodies keep their supported fields
Observable: Supplying `assignee` in a creation, patch, or transition body yields HTTP 400 with `error.code` equal to `invalid` under the existing unknown-field rule.
Source: existing: docs/api.md and src/tickets/validate.js

### C-18: Patching ticket details preserves its current assignment
Observable: Assign a ticket, then use `PATCH /tickets/:id` to change its title or priority where that patch is allowed. The ticket still shows the same assignee.
Source: implied: docs/api.md limits the patch to title and priority

### C-19: The existing lifecycle remains available to assigned tickets
Observable: An assigned ticket can still take the existing moves `open -> in_progress`, `in_progress -> resolved`, `resolved -> closed`, and `resolved -> open` from their respective starting states. Other well-formed moves still receive HTTP 409 with `error.code` equal to `conflict`. A move to `in_progress` preserves the assignee.
Source: existing: docs/api.md and src/tickets/states.js
Open: The requester decides whether entering `resolved` or `closed` affects an assignment automatically, or whether reopening restores a prior assignment. The assignment PUT eligibility follows the ticket's current status.

### C-20: Overlapping assignment and lifecycle writes observe a consistent ticket state
Observable: Race a valid assignment PUT with a transition of the same ticket from `in_progress` to `resolved`. The resulting replies and history agree with an order in which either the PUT changed the active ticket before the transition or the PUT received 409 `conflict` after the transition. Neither request applies half of a change.
Source: implied: the request makes assignment eligibility depend on status, and README.md requires ticket changes to take effect as a unit

### C-21: A real assignment to a named agent queues notice to that agent
Observable: With `WORKER_INTERVAL_MS=0`, set a ticket's assignee to `Dana Lee`. `GET /admin/outbox` shows a pending assignment notice for that ticket with `to` equal to `Dana Lee`.
Source: implied: the request requires notification, and docs/decisions/0006-notification-outbox.md records notices at the time of the change
Open: The requester decides whether returning to the same agent after a clear or reassignment needs a separate notice when an earlier notice for that agent and ticket is still pending. The existing outbox can deduplicate the same pending notice.

### C-22: Reassigning to a different agent produces an independent notice to the new agent
Observable: With the worker off, assign a ticket to `Dana Lee`, then to `Sam`. The outbox shows notices for that ticket addressed to each agent, even though Dana Lee's notice was still pending when Sam became the assignee.
Source: implied: the request requires the agent a ticket was assigned to to be notified of that assignment

### C-23: Clearing an assignment queues no assignment notice
Observable: With the worker off, clear an assigned ticket with `{"assignee":null}`. The outbox contains no new assignment notice from that request.
Source: implied: the request directs assignment notices to the newly assigned agent, and clearing leaves no assignee

### C-24: The existing notification delivery path tells the recipient which ticket was assigned to them
Observable: With the worker enabled and a writable `NOTIFY_FILE`, assign a ticket to `Dana Lee`. The delivered JSON line has `to` equal to `Dana Lee` and identifies the ticket. Its message communicates that the ticket was assigned to the recipient. The corresponding outbox entry reaches `sent`.
Source: implied: U-3 and the delivery contract in docs/operations.md
Open: The requester can specify notification wording or a stable event type label if recipients or downstream consumers need one.

### C-25: Assignment notice delivery failures follow the existing outbox recovery rules
Observable: With a delivery failure, the accepted assignment remains visible. The outbox retries after 1, 2, 4, and 8 seconds of backoff, with attempts made on worker ticks. After the fifth failed attempt the entry stays visible in `dead` with `lastError`. Restoring delivery before the last attempt allows the pending entry to reach `sent`. After a crash between delivery and recording it, the same event may be delivered again with the same `key` and `id`.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-26: Assignment notices preserve the existing requester notices
Observable: Create a ticket, assign it to an agent, then transition it to `resolved` via `in_progress`. The outbox includes the existing `ticket.created` and `ticket.resolved` notices addressed to the requester, even when the requester and assignee are different.
Source: existing: docs/api.md and docs/decisions/0006-notification-outbox.md

### C-27: A named assignee filter lists tickets for that agent
Observable: With tickets assigned to `Dana Lee` and `Sam` plus an unassigned ticket, `GET /tickets?assignee=Dana%20Lee` returns Dana Lee's tickets only. A name with no matching tickets yields an empty `items` list.
Source: request
Open: The requester decides whether matching treats case or surrounding whitespace as significant beyond the exact accepted name, and how to handle multiple occurrences of the new `assignee` query parameter.

### C-28: An explicitly empty assignee filter lists the unassigned tickets
Observable: With both assigned and unassigned tickets, `GET /tickets?assignee=` returns only those whose `assignee` is JSON `null`, including a ticket whose assignment was cleared.
Source: request

### C-29: Omitting the assignee filter leaves tickets eligible regardless of assignee
Observable: With a named assignment and an unassigned ticket, `GET /tickets` can return both. The same is true with a `status` or `priority` filter when both tickets match it.
Source: implied: U-4 distinguishes requesting unassigned tickets from omitting the assignee filter

### C-30: The ticket listing applies the intersection of the supplied filters
Observable: A request such as `GET /tickets?assignee=Dana%20Lee&status=open&priority=urgent` includes the tickets that match all three values. Tickets failing any one are excluded. The rule also holds with `assignee=` or with only `status` and `priority`.
Source: request

### C-31: Existing status and priority filters retain their valid values
Observable: `GET /tickets` accepts `open`, `in_progress`, `resolved`, or `closed` for `status`, and `low`, `normal`, `high`, or `urgent` for `priority`. Other values, including empty ones, yield HTTP 400 with `error.code` equal to `invalid`, including when an assignee filter is present.
Source: existing: docs/api.md

### C-32: The assignment filter participates in the existing cursor pagination
Observable: Query a mixed list with an assignee filter and a small `limit`. Each response has `items` in numeric ticket-id order, up to `limit` matching tickets. Pass a returned opaque `next` as `cursor` with the same filters to continue strictly after the last ticket returned. `next` is JSON `null` when no matching tickets remain, including when none matched in the first place. The default limit is 20. Limits 1 and 100 are valid, while values outside that inclusive whole-number range and malformed cursors yield HTTP 400 with `error.code` equal to `invalid`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-33: A saved assignment change survives a restart as a complete change
Observable: With `DATA_FILE` set and the worker off, set or clear an assignee and restart using the same file. Ticket reads, audit history, and pending notices show the saved change together. If the process is interrupted during the save, the next start sees the complete prior or complete new state.
Source: existing: docs/decisions/0008-json-data-file.md and docs/operations.md

### C-34: Files saved before assignment support still load with unassigned tickets
Observable: Start with a valid pre-assignment version-1 data file lacking the assignee field on its tickets. Previously saved tickets still appear with their original values and `"assignee":null`. Their existing history and outbox entries remain readable. The CLI can list these tickets from the same file.
Source: existing: docs/decisions/0008-json-data-file.md

### C-35: A saved assignee outside the permitted value type is reported as an invalid record
Observable: Change a saved ticket's assignee to a number, boolean, object, array, or empty string. Startup with that `DATA_FILE` fails with a diagnostic identifying the file and the offending ticket field. A missing field in an otherwise valid older record is accepted as unassigned.
Source: existing: docs/operations.md and docs/decisions/0008-json-data-file.md

### C-36: The default CLI listing shows the assignee of every listed ticket
Observable: Run `node bin/tickets.js --data FILE list` or set `DATA_FILE` and run `node bin/tickets.js list`. Rows for assigned tickets identify their agents, and rows for unassigned tickets indicate that there is no assignee. Existing status and priority options still select the matching tickets for the listing.
Source: request
Open: The requester decides whether the listing requirement also includes `list --raw`. The human-readable column placement and unassigned marker need no fixed spelling or position.

### C-37: The CLI's raw listing preserves the fields used by existing consumers
Observable: Run `node bin/tickets.js --data FILE list --raw` on a mix of assigned and unassigned tickets. There is one tab-delimited row per listed ticket, with id, status, priority, and title occupying positions 1 through 4. The weekly report still counts the same tickets by status and priority, regardless of their assignees.
Source: existing: README.md and scripts/weekly-report.js

### C-38: The CLI's full ticket view shows the current assignee
Observable: Run `node bin/tickets.js --data FILE show T-0042` for an assigned or unassigned ticket. The detail view identifies the current agent or indicates that there is no assignee.
Source: implied: every ticket shows its assignee, and src/format.js describes show as the full ticket view

### C-39: Reading the data file through the CLI leaves it unchanged
Observable: Compare the data file before and after a `list`, `list --raw`, or `show` command. The command leaves its contents unchanged.
Source: existing: README.md

### C-40: The existing npm start command serves the API on the configured port
Observable: On Node.js 22 or later, run `npm start` with `PORT` set to a free port. The service answers HTTP requests there without a dependency installation. An unset or empty `PORT` uses the existing default of 4180, while `PORT=0` lets the system pick a free port.
Source: existing: README.md, package.json, and src/server.js

### C-41: Existing tests pass as written
Observable: Run `npm test`; the pre-existing tests pass with their source unchanged.
Source: request

### C-42: The normal test command runs the added assignment tests
Observable: Run `npm test`; Node's test runner discovers and executes the new assignment coverage under `test/` in the same run as the existing tests.
Source: request
