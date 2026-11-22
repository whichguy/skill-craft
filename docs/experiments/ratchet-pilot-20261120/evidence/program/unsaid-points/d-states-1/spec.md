## Use cases

### U-1: A help-desk dispatcher sets the owner of a ticket
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an open ticket. Reading the ticket shows `"assignee":"Dana"`. Sending the same assignment again leaves the ticket as it was. The dispatcher can replace Dana with another agent, or send `{"assignee":null}` to leave the ticket unassigned.
Source: request

### U-2: An API caller corrects an assignment request that the service refuses
Flow: The caller sends `{"assignee":""}` for an existing open ticket and sees 400 `invalid`. With a valid body for a nonexistent ticket, the caller sees 404 `not_found`. The caller can correct the request without having changed the ticket's assignment.
Source: implied: the assignment input rules and the API error conventions in docs/api.md

### U-3: An agent learns that a ticket was assigned to them
Flow: A dispatcher assigns `T-0001` to Dana. With normal notification delivery running, a notice addressed to Dana identifies `T-0001` and says it was assigned to them.
Source: request

### U-4: An API client finds tickets by ownership
Flow: The client calls `GET /tickets?assignee=Dana` for Dana's tickets or `GET /tickets?assignee=` for unassigned tickets. Adding `status=open&priority=urgent` narrows the results to tickets that also meet those filters. If `next` is present as a cursor, the client follows it with the same filters.
Source: request

### U-5: An operator reads ownership from the command-line listing
Flow: The operator runs `node bin/tickets.js --data FILE list` against a saved data file and can tell who owns each assigned ticket and which tickets are unassigned.
Source: request

### U-6: An operator checks that an assignment was recorded
Flow: After changing a ticket's assignee, the dispatcher or operator reads `GET /tickets/:id/audit` to see who changed it and the old and new assignees. With the worker off, the operator can see an assignment notice awaiting delivery at `GET /admin/outbox`.
Source: existing: docs/api.md

### U-7: An operator restarts the service with its saved ticket data
Flow: The operator starts the service with `npm start`, a configured `PORT`, and the same `DATA_FILE` as before. The API still shows saved assignments, and a ticket from a pre-assignment data file shows `"assignee":null`.
Source: implied: every ticket shows its assignee, including the tickets the service already saves across restarts

### U-8: A maintainer runs the assignment checks with the existing suite
Flow: The maintainer runs `npm test` and sees the new assignment checks run alongside the unchanged existing tests, with both passing.
Source: request

## Clauses

### C-1: A valid named assignment sets the identified ticket's assignee.
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an `open`, `in_progress`, or `resolved` ticket. A subsequent `GET /tickets/T-0001` shows `"assignee":"Dana"` whether the prior assignee was `null` or a different agent.
Source: request

### C-2: An explicit null assignee clears the identified ticket's assignment.
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an assigned `open`, `in_progress`, or `resolved` ticket. A subsequent `GET /tickets/T-0001` shows `"assignee":null`.
Source: request

### C-3: The assignment endpoint acknowledges accepted operations using the API's JSON response convention.
Observable: A valid assignment or unassignment accepted by `PUT /tickets/:id/assignee` returns a success status with a JSON response. A caller can confirm the resulting assignee by reading the ticket.
Source: existing: docs/api.md
Open: The requester decides the specific success status and JSON body callers can rely on for this endpoint.

### C-4: Setting an assignee to its current value leaves the ticket unchanged.
Observable: On a ticket eligible for assignment, repeat a PUT naming its current agent, or send `{"assignee":null}` when it is already unassigned. The ticket representation is identical before and after, including `updated`, even when time has advanced.
Source: implied: assigning the current agent changes nothing, and docs/api.md defines updated as the time the ticket last changed

### C-5: A closed ticket's assignment cannot be changed.
Observable: For a `closed` ticket, a valid PUT that would set, replace, or clear its assignee returns 409 `conflict`. The other ticket states are `open`, `in_progress`, and `resolved`.
Source: existing: docs/api.md
Open: The requester decides whether a valid PUT of the value a closed ticket already has is acknowledged as a no-op or refused as a conflict. The ticket stays unchanged either way.

### C-6: The assignee field accepts a non-empty agent name of at most 64 characters or JSON null.
Observable: A valid request for an eligible ticket accepts `"D"`, a name of exactly 64 plain letters, or `null`. It rejects an omitted field, `""`, 65 plain letters, or a number, boolean, array, or object in place of the value with 400 `invalid`.
Source: request
Open: The requester decides how to count characters when Unicode counts differ and how to handle surrounding whitespace, whitespace-only values, and control characters. The existing requester-field validation is a precedent.

### C-7: The assignment endpoint applies the API's request-body rules.
Observable: An absent, blank, or malformed JSON body, a top-level JSON value other than an object (including `null` or an array), or an object containing a field other than `assignee` receives 400 `invalid`. The same error applies above `MAX_BODY_BYTES` (65536 bytes by default, configurable from 1024 through 1048576 bytes). A valid body exactly at the configured limit passes the size check.
Source: existing: docs/api.md, README.md, src/http.js, and src/config.js

### C-8: The assignment endpoint reports a nonexistent ticket using the existing not-found error.
Observable: A PUT with a valid body for an ID that names no ticket returns 404 `not_found`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-9: Assignment errors use the existing API envelope.
Observable: An assignment error contains `{"error":{"code":"<code>","message":"<human-readable message>"}}` with the corresponding HTTP status. For example, requesting an assignment with `{"assignee":""}` returns 400 with `error.code` equal to `"invalid"`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-10: A refused assignment creates no assignment change or effects.
Observable: After an assignment is refused for invalid input, a missing ticket, or a closed ticket, reads of ticket state, audit history, and the outbox show no change attributable to that request.
Source: implied: U-2 and the audit and outbox rules for ticket changes

### C-11: Every API representation of a ticket includes its current assignee.
Observable: In ticket objects returned by create, detail, list, patch, and transition requests, `assignee` is present as the assigned agent's name or JSON `null`. In the create response for a new ticket it is `null`. If the assignment endpoint returns a ticket, the same representation applies there.
Source: request

### C-12: Setting the assignee leaves the ticket's other business fields alone.
Observable: Before and after assigning, reassigning, or unassigning a ticket, compare `id`, `title`, `priority`, `requester`, `status`, and `created`. They retain their values.
Source: implied: U-1 changes ownership of the identified ticket

### C-13: Existing ticket edits preserve its assignee.
Observable: After a successful title or priority patch or a permitted lifecycle transition, the ticket shows the same `assignee` as before that operation, including when it was `null`.
Source: implied: existing operations keep working and their documented changes are limited to their own fields

### C-14: A real assignee change updates the ticket's last-change time.
Observable: After setting, replacing, or clearing an assignee at a later time, the ticket's `updated` shows that change time in the existing UTC ISO 8601 format.
Source: existing: docs/api.md

### C-15: Every real assignee change is traceable in the ticket's audit history.
Observable: `GET /tickets/:id/audit` shows one new entry, after the previous entries, under the next sequence number in the whole log. It identifies the ticket, records the change time and the actor, and contains `changes.assignee` with the actual `from` and `to` values, using JSON `null` on the unassigned side. The actor is the trimmed `X-Actor` value or `system` when absent or blank.
Source: existing: docs/decisions/0007-append-only-audit-log.md and src/http.js

### C-16: Assignment requests apply the existing actor-header limit.
Observable: An otherwise valid PUT with a trimmed `X-Actor` of 64 plain letters passes the actor check. With 65 it returns 400 `invalid`.
Source: existing: docs/api.md and src/http.js

### C-17: An assignment no-op appends no audit entry.
Observable: With the assignee already set to the submitted value, repeat the PUT and compare `GET /tickets/:id/audit` before and after. The history is identical.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-18: A new assignment creates a notice addressed to the newly assigned agent.
Observable: With `WORKER_INTERVAL_MS=0`, a first assignment to Dana on `T-0001` appears in `GET /admin/outbox` as a pending assignment notice for `T-0001` addressed to Dana. Reassigning the ticket to Sam creates a pending notice for Sam even if the earlier notice is still waiting.
Source: implied: U-3 and docs/decisions/0006-notification-outbox.md
Open: The requester decides whether a notice still waiting for a superseded assignment should be delivered, and whether to coalesce pending notices if a ticket leaves an agent and returns to that same agent before delivery.

### C-19: An assignment notice tells the assigned agent which ticket was assigned to them.
Observable: With delivery enabled and a writable `NOTIFY_FILE`, the service appends a JSON line addressed to the assigned agent that identifies the ticket and conveys that it was assigned to them.
Source: request
Open: The requester and mail-relay operator decide whether agent names need to resolve to separate delivery addresses for receipt beyond the service's notification handoff.

### C-20: An assignment no-op creates no assignment notice.
Observable: With the worker off, submit the same agent as the current assignee, including an immediate duplicate of the original successful PUT. The assignment notices in `GET /admin/outbox` do not increase. Repeating the PUT after the original notice has been sent also creates no new notice.
Source: request

### C-21: Unassigning a ticket creates no new-assignment notice.
Observable: Clear an assignee with `{"assignee":null}` while the worker is off. No new notice claiming that the ticket has been assigned appears in `GET /admin/outbox`.
Source: implied: U-3 calls for notifying the agent who receives an assignment

### C-22: Assignment succeeds independently of delivery availability.
Observable: When a valid PUT changes the assignee with the worker off or the notification destination unavailable, the caller can successfully set and read the assignee. Delivery happens through the existing background delivery path.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-23: An assignment notice follows the existing delivery retry policy.
Observable: With the worker enabled, an unsuccessful delivery remains `pending` until its next attempt, due after 1, 2, 4, or 8 seconds respectively for the first through fourth failures, with attempts made on worker ticks. Successful delivery is reported as `sent`. The fifth failure leaves the notice `dead` with its last error visible in `GET /admin/outbox`.
Source: existing: docs/operations.md

### C-24: A configured data file preserves the effects of a completed assignee change across restart.
Observable: Restart with the same `DATA_FILE` after a successful set, replacement, or clear. The API shows the saved assignee and the corresponding audit entry. With delivery disabled, a pending notice created by the change is still visible in the outbox. Without `DATA_FILE`, the service starts with empty state as before.
Source: existing: docs/decisions/0008-json-data-file.md

### C-25: An interrupted save cannot leave a partial assignment change in the data file.
Observable: After interruption during an assignee change with `DATA_FILE` configured and delivery disabled, reopening the file recovers the state from before the change or the state after it, with the assignee, its audit entry, and any notice created by the change from the same saved state.
Source: existing: docs/operations.md

### C-26: Earlier valid data files remain usable when ticket records lack an assignee.
Observable: Start the service or run the CLI on a valid pre-assignment version-1 file. The stored tickets are available with their existing fields intact and are treated as unassigned.
Source: existing: docs/decisions/0008-json-data-file.md

### C-27: A present saved assignee must be a valid assignee value.
Observable: Start with an otherwise valid `DATA_FILE` whose ticket has an invalid `assignee`, such as a number. The service refuses to start and identifies the offending record. A missing field in an older file takes the unassigned default.
Source: existing: docs/decisions/0008-json-data-file.md and docs/operations.md

### C-28: A named assignee filter selects tickets assigned to the specified agent.
Observable: With tickets assigned to Dana and Sam and an unassigned ticket, `GET /tickets?assignee=Dana` selects only Dana's tickets. The selection reflects changes of ownership made before the request.
Source: request
Open: The requester decides how name identity treats case and Unicode normalization for filtering and repeat assignments, what to do with nonempty filter text that cannot name an agent, and what repeated `assignee` parameters mean.

### C-29: An empty assignee filter selects unassigned tickets.
Observable: `GET /tickets?assignee=` selects only tickets whose `assignee` is JSON `null`, including newly created, cleared, and previously saved unassigned tickets.
Source: request

### C-30: Omitting the assignee parameter leaves ownership out of the filter.
Observable: With no `assignee` query parameter, assigned and unassigned tickets can both appear if they satisfy the other listing criteria.
Source: implied: the request adds an assignee filter to GET /tickets

### C-31: An API listing keeps only tickets that match every supplied filter.
Observable: `GET /tickets?status=open&priority=urgent&assignee=Dana` selects tickets meeting all three conditions. Dropping the assignee condition still requires both status and priority. Using `assignee=` makes being unassigned the assignee condition.
Source: request

### C-32: Assignee-filtered results use the existing cursor paging contract.
Observable: Each page is `{"items":[...],"next":<cursor or null>}` in numeric ticket-ID order. With `limit` absent, a page holds up to 20 matches. Limits 1 through 100 are accepted, and values outside that whole-number range yield 400 `invalid`. Following `next` with the same filters continues after the prior page's last ticket ID. A page can fill from matching tickets even when intervening IDs do not match. `next` is `null` when there are no further matches, including an empty result with `"items":[]`.
Source: existing: docs/decisions/0005-cursor-pagination.md and docs/api.md

### C-33: The command-line table displays each listed ticket's assignee.
Observable: Run `node bin/tickets.js --data FILE list` against a file containing assigned and unassigned tickets. Each assigned row identifies its agent, and an operator can distinguish rows with no assignee.
Source: request
Open: The requester decides whether the machine-readable `list --raw` output must also expose ownership. Its existing column positions are required either way.

### C-34: The command-line ticket detail includes its assignee.
Observable: Run `node bin/tickets.js --data FILE show T-0001`. The full ticket detail shows the current agent or indicates that the ticket is unassigned.
Source: implied: every ticket shows its assignee, and src/format.js describes show as a full ticket view

### C-35: The established raw-list fields keep their positions.
Observable: `list --raw` still emits one tab-separated line per listed ticket with ID, status, priority, and title as columns 1 through 4 respectively. The weekly report can still count tickets by status and priority for files containing assignments.
Source: existing: README.md

### C-36: Existing clients can still use the service's prior operations.
Observable: From `npm start`, a client can use the existing create, read, edit, lifecycle, audit, outbox, and health routes. Operators can use the existing read-only CLI commands and listing options, including `--status` and `--priority`. Existing requester notices for creation and resolution still reach the requester through the configured delivery path.
Source: request

### C-37: The service starts on its configured port without installed npm dependencies.
Observable: In a checkout on Node.js 22 or later with no installed packages, run `npm start` with a free `PORT` value. The command starts `src/server.js`, and the API responds at that port. With `PORT=0` the service reports the port assigned by the system.
Source: request

### C-38: The existing test suite passes as written.
Observable: Run `npm test` with the original tests unchanged. The existing cases pass.
Source: request

### C-39: The normal test command includes the new assignment tests.
Observable: Running `npm test` discovers and passes the new `node:test` tests under `test/` covering assignment, unassignment, unchanged repeats, ticket representations, notification, filtering, and the CLI listing.
Source: request
