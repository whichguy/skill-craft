## Use cases

### U-1: A dispatcher assigns a ticket so an agent can take responsibility for it
Flow: For an open or in-progress ticket, send `PUT /tickets/:id/assignee` with `{"assignee":"Dana Lee"}`. Read the ticket to see `"assignee":"Dana Lee"`. Send the same request again to leave the ticket as it was, or send `{"assignee":"Sam"}` to transfer it to Sam.
Source: request

### U-2: A dispatcher removes an assignment so a ticket is available again
Flow: For an open or in-progress ticket, send `PUT /tickets/:id/assignee` with `{"assignee":null}`. Read the ticket to see `"assignee":null`. A state conflict explains why the same operation is unavailable on a resolved or closed ticket.
Source: implied: by the request's unassignment operation and state restriction

### U-3: An agent receives notice so they know which ticket was assigned to them
Flow: When an assignment changes to the agent's name, the service queues a notice identifying the ticket. An operator can see the notice at `GET /admin/outbox`. With the worker enabled and delivery working, the agent receives the assignment notice through the existing notification channel.
Source: implied: by the request's notification sentence and the service's existing notification channel

### U-4: An API caller narrows the ticket queue so they can find an agent's work or unassigned tickets
Flow: Send `GET /tickets?assignee=Dana%20Lee` for Dana Lee's tickets or `GET /tickets?assignee=` for unassigned tickets. Add `status=in_progress` or `priority=urgent` to narrow the results further. Follow `next` as `cursor` with the same filters until `next` is `null`.
Source: implied: by the request's listing sentence and the existing cursor contract in docs/api.md

### U-5: An operator lists saved tickets so they can see who is responsible for each one
Flow: Run `node bin/tickets.js --data data/tickets.json list`. Read each ticket's assignee or see that it is unassigned.
Source: request

### U-6: An operator restarts the service so work can resume with the saved assignments
Flow: Run `npm start` with `PORT` and `DATA_FILE` set. After an assignment, restart with the same file and read the ticket, its history, and the outbox. A file from before the feature still opens, with its tickets unassigned.
Source: implied: by the existing restart and file compatibility promises in docs/decisions/0008-json-data-file.md

### U-7: A maintainer runs the test suite so they can verify assignment and existing behavior
Flow: Run `npm test` in the project. It runs the new `node:test` cases under `test/` with the existing cases, which pass as written.
Source: request

## Clauses

### C-1: An operator starts the service on the configured port with `npm start`
Observable: On Node.js 22 or later, with a free port selected in `PORT`, `npm start` serves the ticket API on that port. The documented default remains `4180` when `PORT` is absent or empty.
Source: existing: README.md

### C-2: The service runs without npm dependencies
Observable: On a host with Node.js 22 or later and npm, the service and CLI run from the project without installing packages.
Source: request

### C-3: A valid assignment request sets the named ticket's assignee
Observable: For an existing ticket in `open` or `in_progress`, a completed successful `PUT /tickets/:id/assignee` with `{"assignee":"Dana Lee"}` leaves `GET /tickets/:id` showing `"assignee":"Dana Lee"`, whether the previous assignee was `null` or a different agent.
Source: request
Open: The requester would settle the exact success status and response body for the assignment endpoint, including successful unassignment and no-op requests.

### C-4: A valid unassignment request clears the named ticket's assignee
Observable: For an existing ticket in `open` or `in_progress`, a completed successful `PUT /tickets/:id/assignee` with `{"assignee":null}` leaves `GET /tickets/:id` showing `"assignee":null`.
Source: request

### C-5: The assignment endpoint refuses a well-formed change request for a resolved or closed ticket
Observable: A `PUT /tickets/:id/assignee` with valid input on a ticket in `resolved` or `closed` receives HTTP 409 with `error.code` equal to `"conflict"`. The state check also applies when the submitted value equals the current value. Tickets in `open` or `in_progress` are eligible.
Source: implied: by the request's state restriction and the state-conflict convention in docs/decisions/0004-error-envelope.md

### C-6: Repeating the current assignee on an eligible ticket has no effect
Observable: On an `open` or `in_progress` ticket, PUT its current agent again or PUT `{"assignee":null}` while it is already unassigned. The request succeeds with the same ticket fields, including `updated`, and adds zero history entries or assignment notices. If two otherwise identical valid requests for a new assignee overlap on the same eligible ticket, they produce just one change.
Source: implied: by the request's same-agent rule and the no-change convention in CONTRIBUTING.md

### C-7: The assignment endpoint requires an assignee value of a permitted kind
Observable: For an eligible ticket, `{}`, `{"assignee":""}`, and an `assignee` value that is a number, Boolean, array, or object receive HTTP 400 with `error.code` equal to `"invalid"`. JSON `null` as the value clears the assignment. An ordinary non-empty name such as `"Dana Lee"` works without an email address.
Source: implied: by the request's two body forms and the invalid-field convention in docs/api.md
Open: The requester would settle name handling for leading or trailing whitespace, whitespace-only names, control characters, case or Unicode equivalence, and any name-specific length bound beyond the existing request-body limit. The same name rules govern repeat detection and filtering.

### C-8: The assignment endpoint refuses malformed JSON bodies
Observable: An absent or blank body, malformed JSON, or a top-level JSON scalar, `null`, or array receives HTTP 400 with `error.code` equal to `"invalid"`.
Source: existing: src/http.js

### C-9: The assignment endpoint refuses unknown body fields
Observable: Sending `{"assignee":"Dana Lee","status":"resolved"}` to the assignment endpoint receives HTTP 400 with `error.code` equal to `"invalid"`.
Source: existing: docs/api.md

### C-10: The assignment endpoint honors the configured request-body size limit
Observable: A body above `MAX_BODY_BYTES` receives HTTP 400 with `error.code` equal to `"invalid"`. A body exactly at the limit is eligible for normal validation. The default is 65,536 bytes. The configuration accepts limits from 1,024 through 1,048,576 bytes inclusive.
Source: existing: src/http.js and src/config.js

### C-11: A valid assignment request for an absent ticket receives the standard not-found response
Observable: With valid input, `PUT /tickets/T-0042/assignee` receives HTTP 404 with `error.code` equal to `"not_found"` when no such ticket exists.
Source: existing: docs/decisions/0004-error-envelope.md

### C-12: Assignment errors follow the API's JSON error envelope
Observable: A rejected assignment request returns JSON of the form `{"error":{"code":"<code>","message":"<message>"}}` with a human-readable message. An unexpected service fault receives HTTP 500 with `error.code` equal to `"internal"`, without details of the fault in the message.
Source: existing: docs/decisions/0004-error-envelope.md

### C-13: Rejection for invalid input, a missing ticket, or a forbidden state leaves assignment state untouched
Observable: Compare ticket reads, history, and outbox before and after an assignment request rejected with 400, 404, or 409. There is no change to a ticket, no history entry, and no notice from the rejected request.
Source: implied: by the assignment prerequisites and the service's existing handling of rejected ticket changes

### C-14: Each API ticket representation includes its current `assignee`
Observable: A ticket returned by creation, detail, listing, title or priority edit, lifecycle transition, or an assignment response that returns a ticket contains `assignee` as the agent's name or JSON `null`. A ticket created with the existing creation request starts with `"assignee":null`.
Source: request

### C-15: Changing the assignee updates the ticket's last-change time
Observable: On assignment, reassignment, or unassignment that changes the value, `GET /tickets/:id` shows `updated` as the time of the change in the existing ISO 8601 UTC form.
Source: existing: docs/api.md

### C-16: Assignment changes preserve ticket fields unrelated to assignment
Observable: Compare ticket reads before and after assignment, reassignment, or unassignment. The only fields that can differ are `assignee` and `updated`.
Source: implied: by the assignment endpoint's single-field operation

### C-17: An edit or lifecycle transition preserves the current assignee
Observable: Edit a ticket's title or priority or move it through an allowed lifecycle transition, including resolution, closure, or reopening. The ticket's `assignee` keeps the same name or `null`, including after it ceases to be eligible for assignment changes.
Source: implied: by the request's state restriction and preservation of existing ticket operations

### C-18: Existing mutation request bodies still reject an `assignee` field
Observable: Adding `assignee` to an otherwise valid create, patch, or transition body receives HTTP 400 with `error.code` equal to `"invalid"`.
Source: existing: docs/api.md

### C-19: Every actual assignment change appends one history entry
Observable: After assignment, reassignment, or unassignment, `GET /tickets/:id/audit` retains the earlier entries in oldest-first order and adds one entry in the existing audit format. Its `changes.assignee` has `from` and `to` with the actual old and new values, including JSON `null` where applicable.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-20: Assignment history follows the existing actor convention
Observable: An actual change records the trimmed `X-Actor` value as `actor`, or `"system"` when the header is absent or blank. A trimmed actor of 64 characters passes actor validation. A longer one receives HTTP 400 with `error.code` equal to `"invalid"`.
Source: existing: src/http.js

### C-21: A newly assigned agent receives notice of their assignment
Observable: With working delivery, a change from `null` or a different agent to `"Dana Lee"` sends Dana Lee an assignment notice identifying the ticket. If the ticket is transferred from Dana Lee to Sam before the worker runs, each agent can receive notice of their own assignment. The notice for Sam is due even while Dana Lee's is pending.
Source: request
Open: When the same ticket returns to the same agent while their earlier assignment notice is pending, the requester would settle whether that pending notice can cover both assignments or each needs its own notice.

### C-22: An unassignment does not create an assignment notice
Observable: Clearing a previously assigned ticket with `{"assignee":null}` adds no assignment notice for that operation to `GET /admin/outbox`.
Source: implied: by the request's notification trigger, which requires an agent being assigned

### C-23: Assignment notices use the service's background delivery contract
Observable: With `WORKER_INTERVAL_MS=0`, a successful assignment leaves its notice pending at `GET /admin/outbox`, addressed to the new assignee for that ticket. With the worker enabled, due notices are delivered through the existing channel. With `NOTIFY_FILE` set, successful delivery appends a JSON line containing `to`, `ticket`, `subject`, and `body`, then the notice is observable as sent. Without a file, delivery uses the existing in-memory channel.
Source: existing: docs/decisions/0006-notification-outbox.md and src/notifier.js

### C-24: An assignment notice follows the existing delivery failure policy
Observable: When delivery fails, the assignment still stands. The outbox shows the notice pending with the error and the next attempt due after 1, 2, 4, and 8 seconds respectively after failures one through four. After the fifth failure, the notice is dead and visible at `GET /admin/outbox`. A restart after delivery but before its result was saved may retry the same notice with its existing delivery identity.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-25: The saved state contains each assignment change as one complete change
Observable: With `DATA_FILE` set, restart after a successful assignment change to see the stored name or `null`, its audit entry, and the corresponding outbox record when a notice was due. If the process is interrupted during the save, a restart loads the complete state before or after the change. A pending notice survives a restart with the worker off.
Source: existing: docs/decisions/0008-json-data-file.md
Open: If saving fails while the service keeps running, the requester would settle whether a subsequent read in that process shows the previous or the complete attempted change. The existing durable-state guarantee still applies.

### C-26: A saved ticket from before assignment support loads as unassigned
Observable: Start with a valid version-1 data file produced before the feature. Tickets that lack `assignee` appear with `"assignee":null` in API reads, match `GET /tickets?assignee=`, and appear unassigned in the CLI listing.
Source: existing: docs/decisions/0008-json-data-file.md

### C-27: A saved ticket with an invalid assignee is refused at startup
Observable: With `DATA_FILE` pointing to an otherwise valid file, a saved `assignee` of the wrong JSON type other than `null`, or an empty string, stops startup with a diagnostic identifying the offending ticket field. A missing `assignee` is the legacy case in C-26.
Source: existing: docs/operations.md and src/persistence.js

### C-28: A named assignee filter keeps tickets assigned to that agent
Observable: With current assignments to Dana Lee, to another agent, and to no one, `GET /tickets?assignee=Dana%20Lee` lists only the matching tickets. This filter can match any of the four ticket states. A name with no matching tickets yields `{"items":[],"next":null}`.
Source: request

### C-29: An empty assignee filter keeps unassigned tickets
Observable: `GET /tickets?assignee=` lists only tickets with `"assignee":null`, regardless of their status unless a status filter is also given.
Source: request

### C-30: Omitting the assignee filter leaves both assigned and unassigned tickets eligible
Observable: With both kinds of ticket present, `GET /tickets` without `assignee` can return both kinds, subject to the other filters and paging.
Source: implied: by the distinction between an omitted filter and the explicit `assignee=` filter

### C-31: A ticket must match all supplied listing filters
Observable: `GET /tickets?status=in_progress&priority=urgent&assignee=Dana%20Lee` returns only in-progress urgent tickets assigned to Dana Lee. A ticket matching only a subset is excluded. The same intersection applies to any combination of distinct filter names, including `status` with `priority` alone and with an empty assignee filter.
Source: request
Open: The requester would settle the interpretation of repeated `assignee` query keys. The existing status and priority parser reads the first value for each of those keys.

### C-32: The assignee filter participates in existing cursor paging
Observable: `GET /tickets` pages the matching tickets in numeric id order, with a default `limit` of 20 and accepted whole-number limits from 1 to 100 inclusive. Each page is `{"items":[...],"next":...}`, with `next` equal to `null` when no matching item remains. Reuse the returned cursor with the same filters to continue after the last id returned, even if that ticket no longer matches. An invalid limit, cursor, status, or priority still receives HTTP 400 with `error.code` equal to `"invalid"`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-33: The CLI's `list` table shows the assignee of each displayed ticket
Observable: Run `node bin/tickets.js list` with `DATA_FILE` set, or use `--data FILE`. For each row, an operator can identify the ticket's current agent or see that it is unassigned. A listing with zero matching tickets still prints `no tickets`.
Source: request
Open: The requester would settle whether the machine-readable `list --raw` mode must also expose the assignee. Its existing positional contract applies either way.

### C-34: Machine-readable CLI listings preserve the fields used by existing consumers
Observable: `list --raw` still emits one tab-separated line per ticket, with id, status, priority, and title in columns 1 through 4 respectively. Assignments do not change the weekly report's counts for the same set of tickets, statuses, and priorities.
Source: existing: README.md and scripts/weekly-report.js

### C-35: The CLI listing remains read-only
Observable: Run `list` or `list --raw` against a saved data file containing tickets with assignments. The command does not change that file.
Source: existing: docs/operations.md

### C-36: The existing tests pass as written
Observable: Running `npm test` with the existing test files as supplied passes the pre-existing cases.
Source: request

### C-37: The assignment behavior is covered by the default test command
Observable: `npm test` discovers and runs the new `node:test` tests under `test/` together with the existing suite.
Source: request
