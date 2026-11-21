## Use cases

### U-1: A requester opens a ticket so the help desk can work on it
Flow: The requester sends the usual title, requester name and optional priority to `POST /tickets`. The new ticket is `open` with `"assignee": null`. The requester still receives the ticket receipt.
Source: implied: by "every ticket shows its assignee" and the existing creation flow

### U-2: A dispatcher assigns an active ticket so an agent can take it
Flow: The dispatcher sends `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana Lee"}`, optionally naming themselves in `X-Actor`. On either an `open` or an `in_progress` ticket, they see Dana Lee as the assignee. The ticket history records who assigned it. Dana Lee receives a notification identifying the ticket.
Source: request

### U-3: A dispatcher hands off or clears a ticket so its current ownership is accurate
Flow: The dispatcher assigns an already assigned active ticket to another agent, then uses `{"assignee":null}` to clear it. Each real change is visible in the ticket and its history. Only the newly assigned agent receives the notification for the handoff.
Source: implied: by assigning to an agent and using null to unassign

### U-4: A client retries an assignment so a lost response does not duplicate work
Flow: The client repeats the same assignment on an active ticket or repeats an unassignment while the ticket is still active. The assignee, last-change time, history and outbox are unchanged by the repeat.
Source: implied: by assigning to the agent the ticket already has changing nothing

### U-5: An API client uses the name boundaries so it can distinguish valid assignments from mistakes
Flow: The client tries a one-character name and a 64-character name on an active ticket. Both are accepted. It then tries an empty or whitespace-only name, a 65-character name, a non-string other than null, an omitted field and a misspelt or extra field. These requests are refused. A body that is absent, malformed, oversized or the wrong JSON shape is refused using the existing error convention.
Source: implied: by the non-empty name of at most 64 characters and the existing JSON body rules

### U-6: A dispatcher attempts an unavailable assignment so they can tell why it was refused
Flow: The dispatcher sends a well-formed assignment or unassignment for a resolved ticket, a closed ticket or a ticket that does not exist. Inactive tickets give 409 `conflict`, including when asked to keep their current value. An absent ticket gives 404 `not_found`. Refusal leaves the ticket, history and outbox alone.
Source: implied: by the active-state restriction and the existing error convention

### U-7: An agent follows a ticket through its lifecycle so the current assignment stays visible
Flow: The agent reads an assigned ticket, edits its title or priority, and moves it through the permitted transitions. The same assignee is visible on the updated and transitioned tickets, including after resolution, closure or reopening. When a resolved ticket reopens it can be assigned again. The requester still receives the resolution notification.
Source: implied: by every ticket showing its assignee and preserving existing operations

### U-8: An agent filters the queue so they can find their own work or work nobody owns
Flow: The agent uses `GET /tickets?assignee=Dana%20Lee` for Dana Lee's tickets, `GET /tickets?assignee=` for unassigned tickets, or omits `assignee` to see both. An unknown valid name returns an empty page. An encoded name with spaces or punctuation survives query decoding. An invalid name, such as a 65-character name, produces the usual invalid response.
Source: request

### U-9: A dashboard combines filters and follows cursors so it can page through just the matching tickets
Flow: The dashboard requests `GET /tickets?status=open&priority=urgent&assignee=Dana%20Lee&limit=1`, then sends the returned cursor with the same filters. It sees only tickets satisfying all three filters, in numeric ticket order. Empty and last pages have `"next": null`. The same intersection holds if it omits any one filter or selects unassigned tickets.
Source: implied: by matching every filter given and the existing cursor contract

### U-10: An operator inspects notifications so every recipient gets the assignment made to them
Flow: With the worker disabled, the operator assigns an active ticket to Dana, then Sam, then Dana again, and checks `GET /admin/outbox`. Each real assignment has its own pending notification addressed to the new assignee. Repeating the current assignment adds none. After the worker resumes, it delivers the queued notices with the original recipients.
Source: implied: by notifying the agent for each assignment through an outbox with pending-key deduplication

### U-11: An operator handles a delivery failure so the ticket can be assigned even when the relay is unavailable
Flow: The assignment succeeds while the notification sink is unavailable. The operator sees the pending notice and its failure in the outbox. Delivery retries after the normal waits and either becomes sent or becomes dead after five failed attempts. The ticket remains assigned.
Source: existing: docs/operations.md

### U-12: An operator reads the data file from the command line so they can see who owns each ticket
Flow: The operator runs `node bin/tickets.js list` with `DATA_FILE` or `--data FILE` and sees named and unassigned tickets. The assignee is also visible in `list --raw` after the existing four columns. The operator can inspect a ticket with `show`; a support lead can run the same weekly report with the same totals. The commands leave the data file alone.
Source: implied: by the command-line listing requirement, every ticket showing its assignee and README.md's raw-column contract

### U-13: An operator upgrades an existing installation so work can continue on the same data
Flow: The operator starts the service with `npm start` using a version 1 data file written before assignment existed. The old tickets show `"assignee": null` with their existing history and notification state. They can assign an active ticket in place, with no manual migration. On a first start with no file the service starts empty.
Source: existing: docs/decisions/0008-json-data-file.md

### U-14: An operator restarts the service so recent changes and unsent notifications are kept
Flow: With `DATA_FILE` set the operator assigns or unassigns tickets, stops the process, then starts it again with the same data file. Tickets, history and pending notification recipients survive. With no `DATA_FILE`, a new process starts empty. With a malformed stored assignee or an unusable environment setting the service reports the problem at start.
Source: implied: by preserving assignments through the existing settings and persistence contract

### U-15: An operator rolls back the executable so the previous release can serve the installation
Flow: The operator keeps a copy of the current data file, checks for assignment notifications that still need the new worker, and points the previous executable at the version 1 file. It serves the existing ticket fields, history and outbox. The previous executable has no assignee field and can discard stored assignees when it rewrites the file. The operator has the copy if they need to recover assignment state.
Source: implied: by going back to the previous version while continuing with the data file

### U-16: A maintainer runs the test suite so assignment and the existing service are checked together
Flow: The maintainer runs `npm test` on Node.js 22 or later with no npm dependencies. The existing tests run as written alongside new `node:test` tests under `test/` that exercise assignment.
Source: request

### U-17: A client retries a failed save so an assignment cannot be half recorded
Flow: The configured data path becomes unavailable for saving and a client attempts a real assignment. The request reports an internal error. A later read shows no partial assignment. After storage is writable, a retry records the change and its notification with the usual audit entry.
Source: implied: by making the ticket, audit and outbox change in one step

## Clauses

### C-1: PUT /tickets/:id/assignee sets the assignee of an active ticket to the supplied agent
Observable: Send `{"assignee":"Dana Lee"}` for an `open` or `in_progress` ticket. The ticket's assignee becomes `"Dana Lee"`, including when it previously held a different name.
Source: request

### C-2: PUT /tickets/:id/assignee accepts JSON null to unassign an active ticket
Observable: Send `{"assignee":null}` for an assigned `open` or `in_progress` ticket. Its assignee becomes JSON `null`.
Source: request

### C-3: Successful assignment requests answer HTTP 200
Observable: A valid set, replacement, clear or repeat on an active ticket returns status 200.
Source: choice: match the service's successful PATCH and transition responses

### C-4: A successful assignment request returns the resulting ticket
Observable: The response body is the whole current ticket, as returned by the ticket's GET endpoint.
Source: choice: match the service's other ticket mutation responses

### C-5: Every API ticket representation includes assignee
Observable: The objects from creation, individual reads, list items, edits, transitions and assignment responses each contain an `assignee` property with the current name or JSON `null` when unassigned.
Source: request

### C-6: A new ticket starts unassigned
Observable: A successful ordinary `POST /tickets` returns `"assignee":null`.
Source: implied: by the separate assignment operation and every ticket showing its assignee

### C-7: Creation continues to refuse assignee as a request field
Observable: Include `"assignee":"Dana"` or `"assignee":null` in an otherwise valid `POST /tickets` body. The response is 400 `invalid`.
Source: existing: docs/api.md

### C-8: PATCH continues to refuse assignee as a request field
Observable: Include `"assignee":"Dana"` or `"assignee":null` in `PATCH /tickets/:id`. The response is 400 `invalid`.
Source: existing: docs/api.md

### C-9: The original ticket fields are unaffected by assigning or unassigning except for updated
Observable: Compare ticket responses before and after a real assignment change. `id`, `title`, `priority`, `requester`, `status` and `created` keep their values.
Source: implied: by assigning a ticket as a change of ownership only

### C-10: A real assignment change sets updated to the time of the change
Observable: Advance the service clock and set, replace or clear an assignee. Read the ticket and see the change time in `updated`.
Source: existing: docs/api.md

### C-11: Repeating the current assignee is a no-op
Observable: Assign `"Dana"` to an active ticket that already shows `"Dana"`. A later read returns an identical ticket even after time has passed.
Source: request

### C-12: Clearing an already unassigned active ticket is a no-op
Observable: Send `{"assignee":null}` to an active ticket whose assignee is already null. A later read returns an identical ticket even after time has passed.
Source: implied: by the request's idempotency rule and the existing treatment of equal-value changes

### C-13: A no-op assignment appends no audit entry
Observable: Compare ticket history before and after sending the active ticket's current assignee, including null. The entries are identical.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-14: A no-op assignment enqueues no notification
Observable: Disable the worker and compare the outbox before and after sending the active ticket's current assignee, including null. No event is added.
Source: existing: CONTRIBUTING.md

### C-15: A no-op assignment causes no change to the data file
Observable: With the worker off and `DATA_FILE` configured, advance the clock and repeat the active ticket's current assignee. The file is unchanged by the request.
Source: existing: src/store.js

### C-16: An edit of a ticket's title or priority preserves its assignee
Observable: Edit the title or priority of an assigned ticket with the usual PATCH operation. The assignee remains the same.
Source: implied: by preserving the existing edit operation and its allowed fields

### C-17: A lifecycle transition preserves the assignee
Observable: Move an assigned ticket along any allowed transition through `in_progress`, `resolved`, `closed` or back to `open`. The response and later reads retain the assignee.
Source: implied: by the active-state restriction applying to assignment changes and the existing transitions changing status only

### C-18: An existing inactive ticket refuses a request to change its assignment
Observable: Send a different valid name or clear an assigned ticket in either `resolved` or `closed`. The response is 409 `conflict`.
Source: request

### C-19: The active-state requirement also applies to an assignment request that would leave the value equal
Observable: Send a resolved or closed ticket's current assignee, including null, to the assignment endpoint. The response is 409 `conflict`.
Source: choice: apply the state gate before the no-op rule, as PATCH does for closed tickets

### C-20: The assignment endpoint reports a missing ticket using the standard lookup error
Observable: Send an otherwise valid request to `PUT /tickets/T-0042/assignee` when that ticket does not exist, or use a decoded id such as `42` that names no ticket. The response is 404 `not_found`.
Source: existing: src/store.js

### C-21: The assignment endpoint requires an assignee field
Observable: Send `{}` to the endpoint. The response is 400 `invalid`.
Source: implied: by the request specifying two explicit body values

### C-22: The assignee value must be a string or null
Observable: A number, boolean, array or object as `assignee` gives 400 `invalid`.
Source: request

### C-23: An assignee name must be non-empty
Observable: Setting `"assignee":""` returns 400 `invalid`. A one-character name such as `"A"` is accepted on an active ticket.
Source: request

### C-24: An assignee name has a maximum length of 64 characters
Observable: Setting a name of 64 ASCII letters on an active ticket succeeds. A name of 65 ASCII letters returns 400 `invalid`.
Source: request

### C-25: Assignee input is trimmed before assignment validation
Observable: Setting `"  Dana Lee  "` stores `"Dana Lee"`. A string made entirely of whitespace gives 400 `invalid`. Surrounding whitespace does not count toward the length limit.
Source: choice: follow the existing requester-name convention

### C-26: Assignee length uses the same units as requester length
Observable: A name made of 32 copies of a supplementary Unicode character such as `😀` fits the limit. A name of 33 copies exceeds it and gives 400 `invalid`.
Source: choice: measure JavaScript string length in UTF-16 code units, as src/tickets/validate.js does for requester names

### C-27: An assignee name uses the service's single-line text convention
Observable: An internal ASCII control character in the assignee name, U+0000 through U+001F or U+007F, gives 400 `invalid`, including internal tabs and line breaks.
Source: choice: apply the existing single-line name rule so a name cannot split a row or a column in raw output

### C-28: An agent name does not require registration or an email address
Observable: Assign a ticket to a well-formed name such as `"Dana Lee"` that has never appeared in the service. The request succeeds on an active ticket.
Source: implied: by the request defining an agent as a name

### C-29: The assignment endpoint refuses additional body fields
Observable: Send an otherwise valid assignee with any extra key, such as `{"assignee":"Dana","status":"closed"}`. The response is 400 `invalid`.
Source: existing: docs/api.md

### C-30: Body-reading errors use the normal JSON object rule on the assignment route
Observable: An absent or whitespace-only body, invalid JSON, or a top-level array, string, number, boolean or `null` gives 400 `invalid`.
Source: existing: src/http.js

### C-31: The existing byte limit applies to the assignment request body
Observable: The configured `MAX_BODY_BYTES` counts the whole body in UTF-8 bytes. A valid body padded with JSON whitespace up to exactly the limit passes the size check. A body one byte over returns 400 `invalid`.
Source: existing: src/http.js

### C-32: The standard actor length limit applies to assignment requests
Observable: Send a valid assignment with an `X-Actor` of 64 ASCII characters, then try one of 65. The first passes the actor check. The second returns 400 `invalid`.
Source: existing: docs/api.md

### C-33: The assignment route accepts a trailing slash
Observable: A well-formed `PUT /tickets/T-0001/assignee/` behaves like the same request without the closing slash.
Source: existing: src/router.js

### C-34: The assignment route decodes its id path parameter
Observable: `PUT /tickets/T%2D0001/assignee` operates on `T-0001`.
Source: existing: src/router.js

### C-35: The assignment route rejects an undecodable id path parameter
Observable: `PUT /tickets/%E0%A4%A/assignee` returns 400 `invalid` for malformed percent-encoding.
Source: existing: src/router.js

### C-36: The assignment path uses the normal error for an unsupported method
Observable: Send GET or POST to `/tickets/T-0001/assignee`. The response is 404 `not_found`.
Source: existing: src/app.js

### C-37: An invalid or refused assignment request leaves the ticket unchanged
Observable: Compare a ticket read before and after any rejected request for it. Every value is the same.
Source: implied: by refusing the action in U-5 and U-6

### C-38: An invalid or refused assignment request appends no audit entry
Observable: Compare the audit history before and after a 400, 404 or 409 from the assignment endpoint. No entry is added.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-39: An invalid or refused assignment request enqueues no notification
Observable: With the worker off, compare the outbox before and after a 400, 404 or 409 from the assignment endpoint. No event is added.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-40: Rejected assignment requests do not change the saved file
Observable: With the worker off and `DATA_FILE` configured, compare the document before and after a rejected assignment. The request leaves the file unchanged.
Source: implied: by refusing assignment without applying a store change

### C-41: HTTP responses use the existing JSON content type
Observable: Both a successful assignment and a rejected assignment return `content-type: application/json; charset=utf-8`.
Source: existing: docs/api.md

### C-42: Assignment errors use the standard error envelope
Observable: A failed request returns JSON with `error.code` for clients and a string `error.message` for people.
Source: existing: docs/decisions/0004-error-envelope.md

### C-43: Unexpected assignment faults use the internal error response
Observable: Cause an unexpected service exception while handling the request. The client receives HTTP 500 with `error.code` equal to `internal`, with no exception details in the response.
Source: existing: docs/decisions/0004-error-envelope.md

### C-44: Unexpected assignment faults are logged
Observable: Cause an unexpected fault while handling assignment. The service logs the failed request to standard error even with request logging off.
Source: existing: src/app.js

### C-45: Assignee validation messages identify the assignee field
Observable: A missing or invalid assignee field produces an error message that identifies `assignee`.
Source: existing: src/tickets/validate.js

### C-46: An unknown-field error identifies the unrecognized key
Observable: With an otherwise valid assignment body containing `owner` as an extra key, the error message includes `owner`.
Source: existing: src/tickets/validate.js

### C-47: Request validation precedes the assignment lookup
Observable: Attempt assignment with a malformed body or an overlong X-Actor for a ticket that has never existed. The result is 400 `invalid` for the malformed input.
Source: existing: src/app.js

### C-48: A real assignment change is recorded as one audit entry
Observable: After setting, replacing or clearing the assignee, `GET /tickets/:id/audit` has one new entry identifying that change.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-49: The audit change records the old and new assignee
Observable: In order, assign Dana to an unassigned ticket, reassign it to Sam, then clear it. The three new entries contain `changes.assignee` equal to `{"from":null,"to":"Dana"}`, `{"from":"Dana","to":"Sam"}` and `{"from":"Sam","to":null}` respectively.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-50: Audit entries use the existing identity and time fields
Observable: An assignment's audit entry includes the ticket id in `ticket`, a non-empty `action` identifying the kind of change and the change time in `at`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-51: The assignment audit actor comes from X-Actor
Observable: Assign with `X-Actor: sam` to an agent named Dana. The audit entry's `actor` is `"sam"`. Surrounding whitespace in the header is trimmed.
Source: existing: src/http.js

### C-52: The assignment audit actor defaults to system
Observable: Make a real assignment with no `X-Actor`, or with a blank one. The audit entry's `actor` is `"system"`.
Source: existing: src/http.js

### C-53: The audit sequence continues across all tickets
Observable: Change the assignees of two different tickets interleaved with another ticket change. The events have successive global `seq` values starting at 1 for a fresh log.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-54: Each ticket's audit feed stays in chronological log order
Observable: Read `GET /tickets/:id/audit` after several operations on several tickets. Its `items` contain only the requested ticket's entries, oldest first.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-55: Audit history stays append-only
Observable: Compare previous entries before and after setting, replacing or clearing an assignee and restarting with the same data file. Previous entries appear unchanged.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-56: Ticket creation keeps its existing audit payload
Observable: For a newly created ticket, `ticket.created` still records only `title`, `priority`, `requester` and `status`, from null to their creation values.
Source: existing: test/store.test.js

### C-57: A real assignment to a name enqueues one assignment notification
Observable: With the worker off, set an active ticket's assignee to a new name. Exactly one new event for that assignment appears under `pending` in `GET /admin/outbox`.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-58: The assignment notification addresses the newly assigned agent
Observable: When the previous assignee, new assignee, requester and X-Actor are different, the assignment notification's `to` is the new assignee's name.
Source: request

### C-59: The agent's notification identifies the ticket
Observable: The delivered notice identifies the assigned ticket by its id, such as `T-0001`.
Source: implied: by telling the agent which ticket was assigned to them

### C-60: The delivered notice tells the recipient that the ticket was assigned to them
Observable: Read the delivered subject and body. They communicate assignment to the recipient.
Source: request

### C-61: An assignment notification is distinguishable from existing notification kinds
Observable: Its `type` in the outbox and the notification sink identifies an assignment event, distinct from `ticket.created` and `ticket.resolved`.
Source: implied: by using the existing typed notification contract for a new kind of notice

### C-62: Unassigning does not enqueue a notification
Observable: With the worker off, clear an assigned ticket. Compare the outbox before and after. There is no new event.
Source: implied: by the request providing a notification only for the agent a ticket is assigned to

### C-63: Distinct assignments to different agents can both be pending for one ticket
Observable: With delivery paused, assign the same ticket first to Dana, then to Sam. Both agents have a pending assignment notice for that ticket.
Source: implied: by each newly assigned agent being notified even if an earlier notice is still pending

### C-64: A later real assignment to a former assignee has its own notification
Observable: With delivery paused, assign the same ticket to Dana, then change it to Sam or clear it, then assign it to Dana again. Dana has a pending notice for each of the two assignments to Dana.
Source: implied: by the request's no-op applying only when the ticket already has that assignee

### C-65: Queued assignment notices keep their original recipients
Observable: With the worker off, assign a ticket to Dana and then give it to Sam or clear it. When delivery resumes, the original notice goes to Dana.
Source: implied: by the assignment event recording who was assigned at the time of the change

### C-66: The outbox continues to deduplicate a key while its event is pending
Observable: Enqueue a key that is still pending. The existing event stays in place with its original values.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-67: Completing a delivery frees its outbox key for later enqueueing
Observable: The outbox allows a key to be enqueued as a new event when the prior event with that key is sent or dead.
Source: existing: src/outbox.js

### C-68: The service delivers assignment notifications through the existing worker
Observable: With the worker enabled, the worker delivers a due assignment event through the notifier, without any notifier call from the assignment request.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-69: The worker-off setting prevents assignment deliveries
Observable: With `WORKER_INTERVAL_MS=0`, the assignment event remains pending without a delivery.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-70: A new assignment notification is due immediately
Observable: Inspect a newly queued event before the first worker tick. It has `status: "pending"`, `attempts: 0` and a `nextAttemptAt` equal to its `created` time.
Source: existing: src/outbox.js

### C-71: Delivery failure does not make the assignment request fail
Observable: Assign a ticket with a notification sink that fails to accept deliveries. The assignment request succeeds and the ticket remains assigned while the worker reports failures.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-72: Failed assignment deliveries use the existing backoff
Observable: The first four consecutive failed attempts set the next attempt due at 1, 2, 4 and 8 seconds after the respective failure times. A worker tick before the due time does not retry the event. The existing exponential backoff has a five-minute cap.
Source: existing: docs/operations.md

### C-73: An assignment delivery becomes dead after five failures
Observable: After the fifth failure, the event stays in `dead` with `attempts: 5` and `nextAttemptAt: null`. Subsequent ticks do not deliver it.
Source: existing: src/outbox.js

### C-74: A delivery failure is visible on the outbox event
Observable: A failed assignment event has a `lastError` describing the failure, truncated after the first 500 string characters by the existing outbox.
Source: existing: src/outbox.js

### C-75: The worker logs a warning when an assignment notification becomes dead
Observable: After permanently failing delivery, the operator sees the warning for the event on standard error.
Source: existing: src/worker.js

### C-76: A successfully delivered event remains in the sent outbox history
Observable: After successful delivery, the event remains in `sent`, with a delivery timestamp in `sentAt`, attempts including the successful attempt, `lastError: null` and `nextAttemptAt: null`.
Source: existing: src/outbox.js

### C-77: Retrying delivery after a crash keeps the same notification identity
Observable: When a process dies after writing a delivery but before saving the sent state, the pending event can be delivered again after restart with the same `key` and `id` for relay deduplication.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-78: The configured notification file receives one JSON line per delivery
Observable: Read `NOTIFY_FILE` after assignment delivery. The appended line has the existing fields `at`, `id`, `key`, `type`, `to`, `ticket`, `subject` and `body`.
Source: existing: src/notifier.js

### C-79: Without a notification file the notifier keeps deliveries in memory
Observable: Leave `NOTIFY_FILE` unset. The notifier's delivered records include the assignment message and no notification file is created.
Source: existing: README.md

### C-80: The outbox endpoint keeps its existing state groups
Observable: `GET /admin/outbox` answers 200 with `pending`, `sent` and `dead` arrays, each containing the notifications in that state, including the assignment kind.
Source: existing: docs/api.md

### C-81: Ticket creation still enqueues the requester's receipt
Observable: Create a ticket with the worker off. The existing `ticket.created` event addresses the requester and uses the same ticket-based key.
Source: existing: test/store.test.js

### C-82: Ticket resolution still enqueues the requester's existing notice
Observable: Resolve an assigned ticket. The existing `ticket.resolved` notice addresses its requester. Reopening and resolving again while the same resolution notification is pending leaves just that one resolution notification pending.
Source: existing: test/store.test.js

### C-83: Omitting the assignee filter imposes no assignment restriction
Observable: List tickets without an `assignee` parameter. Assigned and unassigned tickets remain eligible under the other filters.
Source: implied: by GET /tickets gaining an optional filter

### C-84: A named assignee filter selects that agent's tickets
Observable: `GET /tickets?assignee=Dana%20Lee` returns tickets assigned to `"Dana Lee"`. Tickets assigned to another agent or unassigned do not appear.
Source: request

### C-85: An empty assignee filter selects unassigned tickets
Observable: `GET /tickets?assignee=` returns tickets with `"assignee":null`, including old tickets loaded with that default.
Source: request

### C-86: An assignee filter uses the decoded query value
Observable: After assigning a ticket to `"A+B & C"`, the filter `?assignee=A%2BB%20%26%20C` matches that ticket.
Source: existing: src/app.js

### C-87: The assignee filter interprets non-empty values as assignment names
Observable: Each non-empty decoded value uses the same name parsing and validation as a name sent to PUT. A value that fails that validation answers 400 `invalid`.
Source: choice: give callers one interpretation for names entered through assignment or search

### C-88: Agent names compare case-sensitively
Observable: If `Dana` and `dana` occur on different tickets, searching for either returns its own tickets. Changing a ticket from one to the other is a real assignment.
Source: choice: compare stored names the same way the existing ticket filters compare string values

### C-89: The text null in the assignee query means the agent named null
Observable: A ticket assigned to `"null"` matches `?assignee=null`. An unassigned ticket does not match that query.
Source: implied: by the request reserving only the empty query value for unassigned tickets

### C-90: A repeated assignee query parameter follows the existing single-value parameter convention
Observable: `?assignee=Dana&assignee=Sam` uses Dana, the first value, the same way the current `status` and `priority` parameters are read.
Source: choice: retain the existing duplicate-parameter convention for the new filter

### C-91: A ticket must satisfy every supplied filter
Observable: With status, priority and assignee supplied, a ticket that fails any one is excluded. The same rule holds for any pair, including just status and priority, and when assignee selects unassigned tickets.
Source: request

### C-92: The status filter continues to accept only the four lifecycle statuses
Observable: `status=open`, `in_progress`, `resolved` and `closed` each select the corresponding status. A supplied empty or unknown status answers 400 `invalid`, even alongside an assignee filter.
Source: existing: docs/api.md

### C-93: The priority filter continues to accept only the four priorities
Observable: `priority=low`, `normal`, `high` and `urgent` each select the corresponding priority. A supplied empty or unknown priority answers 400 `invalid`, even alongside an assignee filter.
Source: existing: docs/api.md

### C-94: Unrecognized list query parameters remain ignored
Observable: Adding `offset=40` or `sort=title` to a ticket listing request does not affect the result.
Source: existing: test/query.test.js

### C-95: Ticket list results stay in numeric id order
Observable: A listing with matching ids `T-9999` and `T-10000` returns `T-9999` first. Assignment time does not affect order.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-96: Ticket lists retain the cursor response shape
Observable: A successful list answers 200 with `{"items":[...],"next":<cursor or null>}` and no `total`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-97: The page size remains 20 by default
Observable: With more than 20 matching tickets and no `limit`, the first page contains 20 tickets.
Source: existing: docs/api.md

### C-98: The requested page size remains a whole number from 1 through 100
Observable: `limit=1` and `limit=100` work. `limit=0`, `101`, `2.5`, `-1`, `ten` and an empty value answer 400 `invalid`.
Source: existing: docs/api.md

### C-99: Ticket filters run before paging
Observable: Interleave matches and nonmatches by id. The page contains up to `limit` matching items, including matches beyond the first `limit` unfiltered tickets.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-100: A follow-up page starts strictly after the preceding cursor's id
Observable: Follow `next` with the same filters. It returns only matching items beyond the last item of the preceding page in numeric id order, even if that item no longer matches after a reassignment.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-101: A next cursor exists only when another matching ticket remains
Observable: `next` is null on a last page, including a full last page, or when no tickets match. An empty result has `items: []`. A nonfinal page supplies a cursor the client can pass back unchanged.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-102: An unusable cursor still answers invalid
Observable: An empty cursor, malformed cursor, unsupported cursor version or cursor with an invalid ticket sort key gives 400 `invalid` even with an assignee filter.
Source: existing: src/pagination.js and src/store.js

### C-103: The operator's table listing shows each assignee
Observable: Run `node bin/tickets.js list` on a file with assigned and unassigned tickets. The table shows each assigned agent's name and visibly distinguishes an unassigned ticket.
Source: request

### C-104: The table listing retains the existing ticket information
Observable: The table still displays the id, status, priority, requester, last-change time and title for each listed ticket.
Source: existing: src/format.js

### C-105: The raw listing includes the assignee
Observable: Run `node bin/tickets.js list --raw` on a file with assigned tickets. Each assigned ticket's line includes its agent's name as a separate column.
Source: request

### C-106: Raw listing preserves the positions of its original columns
Observable: Split a raw row on tabs. Columns 1 through 4 are still id, status, priority and title, respectively.
Source: existing: README.md

### C-107: The raw assignee is the fifth column
Observable: Split a raw row on tabs. Column 5 contains the assignee.
Source: choice: append the new field after the columns the weekly report already consumes

### C-108: The raw assignee column uses an empty value for an unassigned ticket
Observable: The assignee cell of an unassigned ticket's tab-separated row is the empty string.
Source: choice: represent no name without reserving a valid name as a sentinel

### C-109: The raw listing retains one tab-separated line per ticket
Observable: The raw command produces one line per matching ticket, with no header. An empty result produces no lines.
Source: existing: README.md and bin/tickets.js

### C-110: The empty table keeps its existing output
Observable: With no matching tickets, `bin/tickets.js list` prints `no tickets` and exits successfully.
Source: existing: bin/tickets.js

### C-111: The CLI list returns all eligible tickets
Observable: List more than 100 matching tickets. Both table and raw output include every matching ticket exactly once.
Source: existing: bin/tickets.js

### C-112: The CLI list stays in numeric ticket id order
Observable: When `T-9999` and `T-10000` both match, both list modes show `T-9999` first.
Source: existing: bin/tickets.js

### C-113: The CLI's existing list filters continue to work
Observable: Run `list --status open --priority urgent`. It shows the open urgent tickets with their assignees. Either option also works on its own.
Source: existing: README.md and docs/api.md

### C-114: The existing single-ticket CLI display includes the assignee
Observable: Run `node bin/tickets.js show T-0001` for an assigned or unassigned ticket. The ticket details show its current assignment as well as the existing history.
Source: implied: by every ticket showing its assignee and the CLI's full-ticket display

### C-115: The CLI show command retains the existing ticket details
Observable: Inspect a ticket with `show`. Its id, title, status, priority, requester, creation time, last-change time and history are still displayed.
Source: existing: src/format.js

### C-116: The CLI still reads DATA_FILE or the --data FILE override
Observable: A configured `DATA_FILE` works for list and show. Providing `--data FILE` selects that file in preference to `DATA_FILE`.
Source: existing: bin/tickets.js

### C-117: Operator CLI exit statuses remain compatible
Observable: A successful command or help exits 0, `show` for a missing ticket exits 1, and a usage or data file error exits 2.
Source: existing: bin/tickets.js

### C-118: The CLI remains read-only
Observable: Compare the data file before and after list, list with `--raw`, or show. The file is unchanged.
Source: existing: README.md

### C-119: The weekly report preserves its status and priority counts
Observable: Run the text report and the report with `--json` on the same ticket set before and after setting assignees. The total and the counts by status and priority are the same.
Source: existing: scripts/weekly-report.js

### C-120: The weekly dashboard keeps its existing report fields
Observable: The report with `--json` still returns `total`, `byStatus` and `byPriority`.
Source: existing: scripts/weekly-report.js

### C-121: The weekly report remains read-only
Observable: Run `npm run report:weekly` or the report script with `--json`. The data file remains byte-for-byte unchanged.
Source: existing: docs/operations.md

### C-122: With DATA_FILE set, an assignment change is saved with its audit and outbox effects
Observable: Read the data file after a successful real assignment change, before stopping the process. One complete document contains the new assignee value and its corresponding audit entry plus the notification for a change to a name.
Source: existing: docs/decisions/0008-json-data-file.md

### C-123: A failed assignment save leaves no partial live change
Observable: Force the configured data-file write to fail before it replaces the existing file. After the assignment request fails, ticket reads, history and outbox still show the state before the request.
Source: implied: by applying the assignment and its effects together in U-17

### C-124: The data file remains a whole-state atomic replacement
Observable: A copy taken during a save or a restart after an interrupted save sees a complete state from before or after the change. It cannot contain a new assignee with a missing corresponding audit or outbox record.
Source: existing: docs/decisions/0008-json-data-file.md

### C-125: A completed assignment save leaves no temporary data file
Observable: After a successful assignment save, the data folder contains the configured file without a temporary file left by that save.
Source: existing: test/persistence.test.js

### C-126: The legacy data file loads through the normal entry points
Observable: Start the service or run the CLI on a valid version 1 file from before assignment without editing it. The ticket records, audit and outbox are readable.
Source: existing: docs/decisions/0008-json-data-file.md

### C-127: A legacy ticket record with no assignee loads as unassigned
Observable: Read a ticket whose saved record lacks the `assignee` property. The API presents `"assignee":null`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-128: Loading an old ticket does not create assignment history
Observable: Open a legacy file and read the old ticket's audit feed. It contains exactly its saved entries.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-129: Loading an old ticket does not enqueue a retroactive notice
Observable: With the worker off, open a legacy file. The outbox contains only its saved events in their saved states.
Source: implied: by defaulting old tickets to unassigned without an assignment operation

### C-130: Assignment state survives a restart
Observable: Persist tickets with a name and after clearing to null. Restart on the same file. GET returns those values for every ticket, including an assigned ticket that became resolved or closed.
Source: implied: by the normal data-file guarantee applying to the current assignee

### C-131: Assignment history survives a restart
Observable: Restart with the same file after real assignment changes. The recorded assignee changes remain in the audit feed with their saved sequence numbers.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-132: Assignment notification state survives a restart
Observable: Open the same file after restart. Assignment events keep their ids, keys, recipients and delivery state, including any scheduled retry. A pending due event can be delivered by the restarted worker.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-133: A present malformed assignee in a stored ticket is rejected
Observable: In an otherwise valid saved file, give a ticket a non-null assignee that cannot represent a valid name, such as an object, an empty string, 65 ASCII letters or a name with an internal tab. Starting on the file fails and names the file and the affected record's `tickets[i].assignee` field.
Source: existing: docs/decisions/0008-json-data-file.md

### C-134: Version 1 remains the data-file version
Observable: Successful saves with assignment still produce a document with `"version":1` and the existing ticket, audit, outbox and counter collections in their existing locations.
Source: existing: test/persistence.test.js

### C-135: The previous release can open a data file saved by the assignment release
Observable: Stop the assignment release, then start the previous release on a copy of the resulting version 1 file. The previous service can read existing ticket fields, history and outbox through its original endpoints without a file conversion.
Source: choice: keep changes additive within the file shape already accepted by the previous loader

### C-136: Rollback instructions explain what an old data-file writer does to assignees
Observable: The operator instructions say to keep a copy of the current file before rollback. They explain that the preceding release ignores the assignee field and drops it if it saves the file, so upgrading again from that rewritten file shows those tickets as unassigned.
Source: implied: by the rollback in U-15 and the old loader and writer keeping only known ticket fields

### C-137: Rollback instructions explain pending assignment notices
Observable: The operator instructions say the preceding release cannot render assignment notifications. They explain that the new worker can process them before rollback, or that starting the old release with `WORKER_INTERVAL_MS=0` leaves pending events in place until a compatible worker runs.
Source: implied: by rolling back with a pending new notification kind and the old template behavior

### C-138: Starting with a missing data file remains supported
Observable: Set `DATA_FILE` to a path that does not exist. The service starts with an empty ticket list and saves the first change at that path.
Source: existing: src/persistence.js

### C-139: Without DATA_FILE the service retains state only for the running process
Observable: Assign an active ticket with `DATA_FILE` unset or empty, then start a fresh process under the same settings. The new process has no saved tickets or assignment events.
Source: existing: README.md

### C-140: Ticket numbers continue from the saved counter
Observable: Restart after assignments and open another ticket. Its id uses the next ticket number, and assigning or clearing existing tickets has consumed no ticket number.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-141: The loader still rejects a document that would reuse a ticket number
Observable: Start on a file whose `nextNumber` is less than or equal to an existing ticket number. Startup fails with the reason.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-142: The loader still rejects a document that would reuse an outbox id
Observable: Start on a file whose `outbox.nextId` is less than or equal to a saved notification id. Startup fails with the reason.
Source: existing: src/persistence.js

### C-143: The loader still refuses a gap in the global audit sequence
Observable: Start on a file whose audit `seq` no longer runs consecutively from 1. Startup fails with the reason.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-144: The loader still refuses unsupported data versions
Observable: Start on a version 2 document. Startup reports that version 1 is the supported version.
Source: existing: test/persistence.test.js

### C-145: Unusable data files stop startup with the existing diagnostics
Observable: Start on an unreadable or non-JSON file, or a file with an invalid existing ticket, audit or outbox record. The service exits with status 2 and reports the file and reason on standard error, identifying the bad record for record validation failures.
Source: existing: docs/operations.md and src/server.js

### C-146: npm start still runs the service through src/server.js
Observable: Run `npm start` with existing settings. It starts the ticket API without any new required option.
Source: request

### C-147: PORT still selects the listen port
Observable: Supply `PORT` from 0 through 65535. A free nonzero port is used as given, while 0 lets the operating system choose a free port.
Source: existing: src/config.js

### C-148: The default listen port is still 4180
Observable: With `PORT` unset or empty, the service uses 4180.
Source: existing: README.md

### C-149: MAX_BODY_BYTES retains its existing setting range
Observable: Numeric `MAX_BODY_BYTES` values from 1024 through 1048576 are supported.
Source: existing: src/config.js

### C-150: The default maximum request body size is still 65536 bytes
Observable: With `MAX_BODY_BYTES` unset or empty, a request body may be up to 65536 bytes.
Source: existing: README.md

### C-151: WORKER_INTERVAL_MS retains its existing setting range
Observable: Numeric worker intervals from 0 through 3600000 milliseconds are supported.
Source: existing: src/config.js

### C-152: The default worker interval is still 500 milliseconds
Observable: With `WORKER_INTERVAL_MS` unset or empty, the worker runs on a 500-millisecond interval.
Source: existing: README.md

### C-153: Invalid numeric configuration still stops startup
Observable: Start with a non-integer or out-of-range value for `PORT`, `MAX_BODY_BYTES` or `WORKER_INTERVAL_MS`. Startup exits with status 2 and names the invalid variable.
Source: existing: README.md and src/server.js

### C-154: Existing request logging covers the assignment route
Observable: With `LOG_REQUESTS=1`, successful and rejected assignment requests each produce their ordinary request line on standard error. With the setting unset or empty, request lines are disabled.
Source: existing: README.md

### C-155: Graceful shutdown lets in-flight requests finish
Observable: Send SIGTERM while a request is in flight. The request can complete before the process exits successfully.
Source: existing: docs/operations.md

### C-156: Graceful shutdown stops background delivery
Observable: Send SIGTERM. The worker stops running its delivery jobs during shutdown.
Source: existing: docs/operations.md

### C-157: Graceful shutdown saves the whole state
Observable: After SIGTERM with `DATA_FILE` configured, the saved state reflects the ticket changes that finished before shutdown.
Source: existing: docs/operations.md

### C-158: Health remains available at its existing endpoint
Observable: `GET /health` while the service is serving returns 200 with `{"status":"ok"}`.
Source: existing: docs/api.md

### C-159: Creating a ticket keeps its existing success response status
Observable: `POST /tickets` with valid input answers 201 with the new ticket.
Source: existing: docs/api.md

### C-160: New ticket status remains open
Observable: Create a ticket through the existing POST endpoint. Its `status` is `"open"`.
Source: existing: docs/api.md

### C-161: Omitted creation priority still defaults to normal
Observable: Create a ticket without a priority. Its `priority` is `"normal"`.
Source: existing: docs/api.md

### C-162: Title validation still requires non-empty text
Observable: Creation rejects a missing title, and creation or edit rejects an empty or non-string title with 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-163: A title remains limited to 200 characters
Observable: A title of 200 ASCII characters fits on creation or edit. A title of 201 ASCII characters returns 400 `invalid`.
Source: existing: docs/api.md

### C-164: A title remains a single line
Observable: A title with an internal tab, newline or other ASCII control character returns 400 `invalid` on creation or edit.
Source: existing: src/tickets/validate.js

### C-165: Title input continues to be trimmed
Observable: Sending a valid title with surrounding whitespace stores the trimmed title.
Source: existing: src/tickets/validate.js

### C-166: Requester validation still requires non-empty text
Observable: Giving a missing, empty or non-string requester on creation returns 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-167: A requester remains limited to 64 characters
Observable: A requester of 64 ASCII characters fits on creation. A requester of 65 ASCII characters returns 400 `invalid`.
Source: existing: docs/api.md

### C-168: A requester remains a single line
Observable: A requester with an internal tab, newline or other ASCII control character returns 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-169: Requester input continues to be trimmed
Observable: Sending a valid requester with surrounding whitespace on creation stores the trimmed requester.
Source: existing: src/tickets/validate.js

### C-170: Existing ticket priorities remain the four documented values
Observable: The creation and edit endpoints accept `low`, `normal`, `high` and `urgent` when a priority is supplied. Any other supplied priority returns 400 `invalid`.
Source: existing: docs/api.md

### C-171: Individual ticket reads still return the ticket with status 200
Observable: `GET /tickets/:id` for an existing ticket returns 200 with that ticket.
Source: existing: docs/api.md

### C-172: Individual ticket reads still report absent tickets as not found
Observable: `GET /tickets/:id` for a missing ticket returns 404 `not_found`.
Source: existing: docs/api.md

### C-173: An existing patch can still edit title or priority
Observable: On a ticket that is not closed, give a new title, a new priority or both. The PATCH endpoint returns the resulting ticket with status 200.
Source: existing: docs/api.md

### C-174: PATCH still rejects an empty patch
Observable: Send `{}` to `PATCH /tickets/:id`. It returns 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-175: PATCH still refuses closed tickets
Observable: Send a valid patch to a closed ticket. It returns 409 `conflict`.
Source: existing: docs/api.md

### C-176: A no-op PATCH still preserves the last-change time
Observable: Patch an editable ticket to its existing values. The response has the prior `updated` time.
Source: existing: docs/api.md

### C-177: A no-op PATCH still appends no audit entry
Observable: Patch an editable ticket to its existing values. Its audit feed gains no entry.
Source: existing: docs/api.md

### C-178: Lifecycle transitions keep their existing allowed moves
Observable: `open` can move to `in_progress`, `in_progress` to `resolved`, and `resolved` to `closed` or `open`. Each allowed move answers 200 with the resulting ticket.
Source: existing: docs/api.md

### C-179: Disallowed moves between known statuses still give a lifecycle conflict
Observable: Any other move between recognized states answers 409 `conflict`, including any move out of `closed`.
Source: existing: docs/api.md

### C-180: Unknown transition states still produce invalid
Observable: Send `{"to":"done"}` to the transition endpoint. It returns 400 `invalid`.
Source: existing: docs/api.md

### C-181: Ticket times keep their existing UTC format
Observable: Newly generated ticket and audit times use ISO 8601 UTC, for example `2025-09-01T08:15:00.000Z`.
Source: existing: docs/api.md

### C-182: Ticket ids retain the existing canonical form
Observable: Create successive tickets. Their ids have the `T-` prefix and the sequential positive number padded to at least four digits, such as `T-0001` and `T-10000`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-183: Ticket assignment adds no npm dependencies
Observable: On Node.js 22 or later, the service and test suite run using the standard library without installing packages.
Source: request

### C-184: The existing tests continue to pass as written
Observable: Run the unchanged pre-assignment test files through `npm test`. Their assertions all pass.
Source: request

### C-185: New behaviour has node:test coverage under test/
Observable: `npm test` discovers new `node:test` coverage for assignment, including validation, state restrictions, no-ops, audit and notifications, list filtering, persistence and CLI output, in the same run as the existing suite.
Source: request

### C-186: HTTP tests use the existing isolated service setup
Observable: Assignment HTTP tests use a free port and leave the worker disabled when asserting queued state, except when exercising delivery.
Source: existing: CONTRIBUTING.md and test/helpers.js

### C-187: A retry after a failed save can perform the assignment
Observable: After an assignment fails because the data file cannot be saved, restore normal file access and retry with the same input. The request performs the assignment as a real change.
Source: implied: by failed changes being unapplied in U-17

### C-188: Overlapping identical assignment requests have the same effect as sequential repeats
Observable: While delivery is paused, send the same new assignee in two overlapping PUT requests for one active ticket. Both succeed, with one effective assignment in the history and one new assignment event.
Source: implied: by repeating the same assignment changing nothing after the first request takes effect

### C-189: The API reference describes assignment
Observable: The API reference describes the assignee ticket field, the assignment endpoint and the assignee list filter so a caller can use them without inspecting source code.
Source: implied: by extending the ticket API documented in docs/api.md

### C-190: The CLI reference describes the raw assignee field
Observable: The command-line documentation describes where scripts can read the assignee in raw output and how unassigned tickets appear there.
Source: implied: by extending the documented raw columns consumed by operators and scripts

### C-191: A failed assignment save leaves the saved state and identifiers unchanged
Observable: After a failed assignment save before the data file is replaced, the previous document remains readable and unchanged. The next successful assignment receives the same next audit sequence and notification id it would have received without the failure.
Source: implied: by U-17 requiring the failed assignment to leave no partial record and the retry to record the change with its usual audit entry and notification

### C-192: An accepted assignee name can be represented in an encoded query and the raw listing
Observable: An assignee string with an unpaired Unicode surrogate, such as `"\uD800"`, returns 400 `invalid`. A name with a valid surrogate pair that fits the length limit is accepted and retains the same name in a URL-encoded filter and the raw listing.
Source: implied: by U-8 and U-12 requiring the stored name to round-trip through the URL query and the UTF-8 raw listing, both of which replace an unpaired surrogate
