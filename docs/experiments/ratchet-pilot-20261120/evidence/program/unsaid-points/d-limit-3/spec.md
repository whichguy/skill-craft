## Use cases

### U-1: A dispatcher assigns a ticket so an agent can take responsibility for it
Flow: On an `open` or `in_progress` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":"Dana"}`. Read the ticket and see `"assignee":"Dana"`. Send `{"assignee":"Sam"}` to hand it to Sam. Repeating the request for Sam leaves the ticket unchanged.
Source: request

### U-2: A dispatcher clears an assignment so a ticket can return to the unassigned queue
Flow: On an `open` or `in_progress` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":null}`. Read the ticket and see `"assignee":null`.
Source: request

### U-3: An API client handles a refused assignment without losing the current ticket state
Flow: Try to change the assignee of a `resolved` or `closed` ticket and receive a 409 `conflict`. Use a nonexistent ticket ID with a valid body and receive a 404 `not_found`. Send a malformed body and receive a 400 `invalid`.
Source: existing: docs/api.md

### U-4: An agent receives notice so they know which ticket was assigned to them
Flow: After the dispatcher assigns the ticket to Dana, the service records a notification for Dana. With delivery running and a working destination, Dana gets a message identifying the ticket and saying it was assigned to them.
Source: request

### U-5: A queue viewer narrows the ticket list to find work for an agent or work without an assignee
Flow: Request `GET /tickets?assignee=Dana` for Dana's tickets or `GET /tickets?assignee=` for unassigned tickets. Combine either with status or priority to see only tickets meeting all criteria. Follow `next` with the same filters if another page exists.
Source: request

### U-6: An operator lists saved tickets from the command line to see who owns each one
Flow: Run `node bin/tickets.js --data FILE list` against a file containing assigned and unassigned tickets. Read the assignee or its unassigned indication on each row.
Source: request

### U-7: A support lead runs the weekly report to get the same counts after assignment is introduced
Flow: Run the existing weekly report over a data file that contains assigned tickets. It still counts each ticket by status and priority using the raw listing.
Source: existing: README.md

### U-8: An operator restarts the service to recover saved assignments and pending notices
Flow: Start with a data file written by the previous release and see its tickets as unassigned. Make an assignment with `DATA_FILE` configured. Restart with that file and see the assignment, its audit entry and its saved notification state.
Source: existing: docs/decisions/0008-json-data-file.md

### U-9: A maintainer runs the test suite to check assignment alongside existing behaviour
Flow: Run `npm test` and see the existing tests run as written alongside new `node:test` tests under `test/` for assignment.
Source: request

## Clauses

### C-1: The service is reachable on the configured `PORT` when started with `npm start`
Observable: Start the service with `PORT` set to a free port and use its ticket API on that port. An unset or empty `PORT` uses 4180. `PORT=0` lets the system select the port reported at startup.
Source: existing: README.md, src/config.js, src/server.js

### C-2: The service runs without npm dependencies on its supported Node.js runtime
Observable: On Node.js 22 or later, start the service and use ticket assignment from a checkout without installing packages.
Source: request

### C-3: A named assignment sets the assignee of an eligible ticket
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` to an `open` or `in_progress` ticket, then read it and see `"assignee":"Dana"`. This works whether the ticket was unassigned or assigned to another agent.
Source: request

### C-4: A null assignment clears the assignee of an eligible ticket
Observable: Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` to an assigned `open` or `in_progress` ticket, then read it and see `"assignee":null`.
Source: request

### C-5: An accepted assignment request reports success
Observable: A valid assignment or unassignment of an eligible ticket returns a 2xx response, including when the requested assignee is already the current value.
Source: choice: callers need a success signal and can read the ticket through the existing API
Open: The requester can settle the exact success status and whether the response returns the ticket. The existing ticket mutation endpoints return 200 with the ticket.

### C-6: The assignee value in an assignment request must be a name or JSON null
Observable: The request accepts an ordinary non-empty agent name such as `"Dana Lee"`, or JSON `null` to clear the assignment. An omitted `assignee`, the empty string, numbers, booleans, arrays and objects are refused with 400 `invalid`.
Source: request
Open: The requester can settle how spaces, whitespace-only values, control characters and case affect name validity or identity, and whether a name-specific length bound is needed. The existing body byte limit still applies.

### C-7: Assignment requests follow the API's JSON object requirement
Observable: A body with no JSON value, malformed JSON, or a top-level array, string, number, boolean or null returns 400 `invalid`. The unassignment value is null inside the object.
Source: existing: docs/api.md

### C-8: Assignment requests reject unknown body fields
Observable: A body such as `{"assignee":"Dana","owner":"Sam"}` returns 400 `invalid`, including when the required field is valid.
Source: existing: docs/api.md

### C-9: Assignment requests respect the configured request-body size limit
Observable: With the default `MAX_BODY_BYTES=65536`, a valid JSON assignment body padded to 65,536 bytes reaches ordinary validation. One padded to 65,537 bytes returns 400 `invalid`. A configured byte limit replaces the default.
Source: existing: README.md, src/http.js

### C-10: A valid assignment request for a nonexistent ticket returns 404
Observable: Send a valid named assignment or unassignment to a ticket ID that does not exist and receive 404 `not_found`.
Source: existing: docs/api.md

### C-11: Changing the assignee of an inactive ticket is refused
Observable: A well-formed request that would assign, reassign or unassign a `resolved` or `closed` ticket returns 409 `conflict`. The two other ticket states, `open` and `in_progress`, permit the change.
Source: request
Open: The requester can settle whether an otherwise valid request repeating the current assignee, including null, in `resolved` or `closed` receives 409 or a successful no-op. Either response leaves the assignment untouched.

### C-12: Assignment errors use the existing API envelope
Observable: On a refusal, the JSON response has the form `{"error":{"code":"<code>","message":"<human-readable text>"}}`, with the HTTP status corresponding to its code. An unexpected service fault returns 500 `internal` without exposing its cause in the response.
Source: existing: docs/decisions/0004-error-envelope.md

### C-13: A refused assignment has no assignment effect
Observable: After a validation, missing-ticket or state refusal, the caller sees the same ticket data, and the operator sees no audit entry or notification from the refused request.
Source: implied: U-3

### C-14: Repeating the current assignee is a no-op
Observable: In `open` or `in_progress`, repeat the current agent name or send `{"assignee":null}` when already unassigned. The ticket, including `updated`, stays as it was. The request adds no audit entry or notification.
Source: existing: CONTRIBUTING.md, docs/api.md

### C-15: Ticket representations include the current assignee
Observable: Read ticket objects from `POST /tickets`, `GET /tickets/:id`, `GET /tickets`, `PATCH /tickets/:id` or `POST /tickets/:id/transition`. Each contains `assignee` with the current agent name or JSON `null`. The same holds if the assignment response includes a ticket object.
Source: request

### C-16: A newly created ticket starts unassigned
Observable: Create a ticket with the existing `POST /tickets` body and receive a 201 ticket with `"assignee":null`.
Source: implied: the assignment endpoint sets the agent and every unassigned ticket shows null

### C-17: The existing create and patch bodies keep their accepted fields
Observable: Supplying an `assignee` field to `POST /tickets` or `PATCH /tickets/:id` returns 400 `invalid` under their unknown-field rule.
Source: existing: docs/api.md

### C-18: Assignment leaves unrelated ticket fields intact
Observable: Compare the ticket before and after a successful change of assignee. Its `id`, `title`, `priority`, `requester`, `status` and `created` values are identical.
Source: implied: U-1 and U-2 change who owns the ticket

### C-19: A change of assignee sets the ticket's last-change time
Observable: After changing or clearing an assignee at a later time than the previous change, read the ticket and see `updated` reflect the assignment change in the existing UTC timestamp format.
Source: existing: docs/api.md

### C-20: Other ticket edits preserve its assignee
Observable: Patch the title or priority of an assigned ticket and read the same assignee afterward.
Source: existing: docs/api.md

### C-21: Lifecycle transitions preserve the ticket's assignee
Observable: Assign an open ticket, move it through `in_progress`, `resolved` and `closed`, then read its current assignee. It is the agent originally assigned. The permitted `resolved` to `open` transition likewise preserves the assignee.
Source: existing: docs/api.md, src/store.js

### C-22: Competing ticket updates have a consistent order
Observable: If assignment overlaps a transition out of `in_progress`, the result is consistent with one operation preceding the other: a completed assignment survives the transition, or the transition wins first and the attempted change of assignee conflicts. The audit history reflects the order of the successful changes.
Source: implied: the state restriction in U-1 and the append-only history of ticket changes

### C-23: Each change of assignee appends one audit entry
Observable: In `GET /tickets/:id/audit`, find one new entry after each real assignment, reassignment or unassignment, with a new sequence number, the ticket ID, an action, the time of the change and `changes.assignee` as `{"from":<previous value>,"to":<new value>}`. Use JSON null for an unassigned side. Earlier entries remain as recorded.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-24: The audit entry for a change of assignee identifies the caller
Observable: Set `X-Actor: dispatcher` and see `"actor":"dispatcher"` on the new entry. Surrounding whitespace is trimmed. An absent or blank header records `"actor":"system"`.
Source: existing: docs/api.md, src/http.js

### C-25: Assignment requests respect the existing actor length limit
Observable: A trimmed `X-Actor` of 64 characters is accepted for an otherwise valid assignment, while 65 characters returns 400 `invalid`.
Source: existing: docs/api.md, src/http.js

### C-26: A new named assignment records a notification for the newly assigned agent
Observable: With `WORKER_INTERVAL_MS=0`, assign `T-0001` to Dana. After success, `GET /admin/outbox` shows a pending assignment notice for `T-0001` destined for Dana. If a different agent is assigned before delivery, the existing pending notice for Dana does not stand in for the notice to the different agent.
Source: request
Open: The requester can settle whether another assignment of the same ticket to Dana after an intervening reassignment or unassignment coalesces with a notice to Dana that is still pending. The outbox already coalesces pending notices it treats as the same.

### C-27: Clearing an assignee enqueues no assignment notice
Observable: With the worker off, clear an assigned ticket and see no additional assignment notification in `GET /admin/outbox`.
Source: implied: the assignment notice is for the agent a ticket is assigned to

### C-28: A due assignment notification tells its recipient which ticket was assigned to them
Observable: With delivery enabled and a writable `NOTIFY_FILE`, find a JSON line for the assignment addressed to the assigned agent. The message identifies the ticket and conveys that it was assigned to the recipient.
Source: request
Open: The requester or relay operator can settle any mapping needed from an agent name to a separate delivery address. The existing delivery boundary is the service's notifier.

### C-29: Assignment notice delivery uses the configured background schedule
Observable: With `WORKER_INTERVAL_MS=0`, an assignment succeeds and its pending notice causes no delivery output. With delivery enabled, a due notice is eligible at the next worker run, at the configured interval of 500 ms by default. A failing notification destination does not turn the assignment into an API failure.
Source: existing: docs/decisions/0006-notification-outbox.md, README.md

### C-30: Assignment notice delivery failures follow the existing retry policy
Observable: In `GET /admin/outbox`, observe a failed assignment notification remain pending with the next attempt scheduled 1 s, 2 s, 4 s or 8 s after the first through fourth failures respectively. After a fifth failure it is retained as `dead` with `lastError` and is no longer retried.
Source: existing: docs/operations.md

### C-31: A recorded delivery of an assignment notice is not retried
Observable: Once delivery is recorded, `GET /admin/outbox` shows the notice under `sent`. Further worker runs do not send that recorded event again. A send interrupted before it is recorded may be repeated after restart under the existing delivery contract.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-32: Assignment-related state is saved as one consistent change
Observable: With `DATA_FILE` configured, restart after a successful change and read the new assignee, its audit entry and, for a named assignment, its saved notification record. If interrupted during the save, the file contains the complete prior state or the complete new state.
Source: existing: docs/decisions/0008-json-data-file.md, docs/decisions/0006-notification-outbox.md

### C-33: Data files from before ticket assignment still load
Observable: Start from a valid version 1 file written before assignment was available. Tickets that have no stored assignee appear as `"assignee":null` in the API, with their existing history and outbox retained.
Source: existing: docs/decisions/0008-json-data-file.md

### C-34: The assignee name filter selects tickets assigned to that agent
Observable: With Dana's tickets, Sam's tickets and unassigned tickets present, `GET /tickets?assignee=Dana` selects Dana's tickets. The filter applies to the current assignee in any ticket state. A name containing a space can be sent as an encoded query value, such as `assignee=Dana%20Lee`.
Source: request

### C-35: The empty assignee filter selects unassigned tickets
Observable: `GET /tickets?assignee=` selects tickets with `"assignee":null`, including new tickets, cleared tickets and tickets loaded from an older file. A request omitting `assignee` does not filter by assignment.
Source: request

### C-36: The ticket API applies all supplied ticket filters together
Observable: With `GET /tickets?status=open&priority=urgent&assignee=Dana`, each returned ticket has all three values. With `assignee=` in place of `assignee=Dana`, the third condition is an unassigned ticket. A ticket failing any supplied filter is excluded, including when the only filters are status and priority.
Source: request
Open: The requester can settle how repeated `assignee` parameters are handled. The existing status and priority parser uses the first value of each parameter.

### C-37: Filtered ticket results keep the existing cursor page contract
Observable: For a stable set of matching tickets, follow `next` as `cursor` with the same filters. The `items` are in numeric ticket ID order, with no gaps or repeats among those matches. Each page before the last is full. With no matching items left, `next` is null, including the empty result `{"items":[],"next":null}`. A limit of 1 or 100 is accepted, an omitted limit means 20, and a non-integer or a value outside 1–100 returns 400 `invalid`.
Source: existing: docs/api.md, docs/decisions/0005-cursor-pagination.md

### C-38: The human-readable CLI listing shows the assignee for each ticket
Observable: Run `node bin/tickets.js --data FILE list` against a file with assigned and unassigned tickets. Each displayed row identifies the agent or visibly indicates an unassigned ticket. Existing status and priority options still select the rows to display.
Source: request

### C-39: The raw CLI listing represents each ticket's assignee
Observable: Run `node bin/tickets.js --data FILE list --raw` and read the assignee or an unassigned value on each ticket's line. The listing remains one tab-separated line per ticket.
Source: request

### C-40: The raw CLI listing preserves the positions of the existing columns
Observable: In `list --raw`, tab-separated fields 1 through 4 remain `id`, `status`, `priority` and `title`, in that order.
Source: existing: README.md

### C-41: The weekly report still counts each listed ticket
Observable: Run the existing report with `--json` against a data file containing assigned and unassigned tickets. The output still gives the total and counts by status and priority for all tickets.
Source: existing: scripts/weekly-report.js, README.md

### C-42: The current assignment is visible in the CLI's full ticket view
Observable: Run `node bin/tickets.js --data FILE show T-0001`. The ticket details identify its assigned agent or indicate that it is unassigned, even if its history still contains an earlier assignment.
Source: implied: every ticket shows its assignee and src/format.js describes the CLI detail view as the ticket in full

### C-43: Existing service behaviour remains available after adding assignment
Observable: Existing callers can still create, read, edit, transition and list tickets, read ticket history, inspect the outbox and check service health. The existing requester notifications still go to the requester when a ticket is created or resolved.
Source: request

### C-44: The existing tests pass as written
Observable: Run `npm test` and see the pre-existing tests pass without changes to those tests.
Source: request

### C-45: The test suite runs new assignment tests with the existing tests
Observable: Run `npm test` and see it discover and run new `node:test` tests under `test/` for the assignment behaviour.
Source: request
