## Use cases

### U-1: A help-desk dispatcher assigns a ticket to give an agent responsibility for it
Flow: The dispatcher sends `PUT /tickets/T-0042/assignee` with `{"assignee":"Dana"}`. The ticket shows `assignee: "Dana"`. Sending the same request again leaves the ticket as it was. Sending `{"assignee":"Sam"}` instead changes the assignee to Sam.
Source: request

### U-2: A help-desk dispatcher unassigns a ticket to return it to the unassigned queue
Flow: The dispatcher sends `PUT /tickets/T-0042/assignee` with `{"assignee":null}`. The ticket shows `assignee: null` and appears in `GET /tickets?assignee=`.
Source: request

### U-3: An agent learns that they have been assigned a ticket
Flow: A dispatcher assigns T-0042 to Dana. With notification delivery running normally, Dana receives a message that identifies T-0042 and says it was assigned to them.
Source: request

### U-4: A queue viewer filters the ticket list to find work for an agent or work without an assignee
Flow: The viewer sends `GET /tickets?assignee=Dana&status=open&priority=urgent` and sees only Dana's open urgent tickets. With `assignee=` in the same query they see only unassigned open urgent tickets. If the result spans pages, they follow `next` using the same filters.
Source: request

### U-5: An operator lists saved tickets to see who is responsible for each one
Flow: With the service saving to `DATA_FILE`, the operator runs `node bin/tickets.js list` against that file. The listing shows Dana on a ticket assigned to Dana and indicates that a ticket with no assignee is unassigned.
Source: request

### U-6: An operator restarts the service to resume work with saved assignments
Flow: The operator starts the service with `npm start`, setting `PORT` and `DATA_FILE`. A file saved before the feature still opens, with its tickets unassigned. Assignments made after the upgrade can be read after restarting with the same file.
Source: existing: docs/decisions/0008-json-data-file.md

### U-7: A maintainer runs the test suite to verify the feature and existing behavior
Flow: The maintainer runs `npm test`. The existing tests run as written alongside the new `node:test` tests under `test/`, and the suite passes.
Source: request

## Clauses

### C-1: A valid assignment sets the target ticket's assignee
Observable: On an existing `open`, `in_progress`, or `resolved` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":"Dana"}`. The request succeeds and `GET /tickets/:id` shows `"assignee":"Dana"` whether the old assignee was null or a different agent.
Source: request
Open: The requester decides the successful PUT response status and payload within the service's API conventions, including what the caller sees on a no-op.

### C-2: A valid unassignment clears the target ticket's assignee
Observable: On an assigned `open`, `in_progress`, or `resolved` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":null}`. The request succeeds and `GET /tickets/:id` shows `"assignee":null`.
Source: request

### C-3: A PUT of the current assignee is a no-op
Observable: With delivery paused, send the same valid assignment twice to a ticket that can change, or send `{"assignee":null}` to an already unassigned ticket that can change. Across the repeat or redundant PUT, the ticket including `updated`, its audit history, and the outbox are identical.
Source: request
Open: The requester decides whether a PUT of the current value on a closed ticket succeeds as a no-op or returns the closed-ticket conflict.

### C-4: Assignment accepts a non-empty agent name up to the inclusive limit of 64 characters
Observable: Assign a one-character name or a 64-character name made of ordinary letters and read it back in `assignee`. An empty string or a name of 65 ordinary letters receives HTTP 400 with `error.code` equal to `invalid`.
Source: request
Open: The requester decides how to count Unicode characters, whether to trim or otherwise normalize names, how to treat whitespace-only names, and which control characters, if any, are accepted. Those decisions apply consistently to storing, comparing, and finding agent names.

### C-5: The assignment PUT rejects malformed input through the standard invalid-request response
Observable: Send an absent or malformed JSON body, a top-level array, null or other non-object value, an object missing `assignee`, an `assignee` value of boolean, number, array or object type, or a body with an unknown field. Each receives HTTP 400 with `{"error":{"code":"invalid","message":"<human-readable message>"}}`.
Source: existing: docs/api.md

### C-6: The assignment PUT observes the configured request body limit
Observable: A valid assignment JSON body padded with JSON whitespace to exactly `MAX_BODY_BYTES` is accepted on a changeable ticket. The same request with one extra byte receives HTTP 400 `invalid`. The limit defaults to 65536 bytes.
Source: existing: README.md and src/http.js

### C-7: A valid PUT for a missing ticket returns the standard not-found response
Observable: Send a valid assignment or unassignment to an ID with no ticket. The response is HTTP 404 with `error.code` equal to `not_found` and a human-readable `error.message`.
Source: existing: docs/api.md

### C-8: A closed ticket cannot acquire, replace, or lose an assignee
Observable: Close an unassigned or assigned ticket through the existing lifecycle, then send a valid PUT that would change its assignee. The response is HTTP 409 with `error.code` equal to `conflict` and a human-readable `error.message`. This applies to `closed`. The other statuses are covered by C-1 and C-2, and an unchanged value is covered by C-3.
Source: existing: docs/api.md and docs/decisions/0004-error-envelope.md

### C-9: Invalid or refused assignment requests leave no assignment effects
Observable: With delivery paused, compare a ticket if present, its audit history if present, and the outbox before and after a PUT rejected as `invalid`, `not_found`, or `conflict`. Each comparison is equal.
Source: implied: by U-1 and U-2 changing an existing ticket through a valid request

### C-10: An assignment operation changes ownership independently of other ticket fields
Observable: Compare the ticket before and after a successful change of assignee. The differences are confined to `assignee` and `updated`.
Source: implied: by the request to set only the ticket's assignee

### C-11: A change of assignee counts as the ticket's last update
Observable: At a later clock time than the ticket's prior `updated` value, assign, reassign, or unassign the ticket. Its `updated` value is the time of that change in the existing UTC ISO 8601 format.
Source: existing: docs/api.md

### C-12: Every ticket returned by the API includes its current assignee
Observable: Ticket JSON returned by create, get, list, patch, or transition includes `assignee`. A newly created ticket or a ticket that has been unassigned shows JSON null. An assigned ticket shows the agent name, including after a title or priority edit or a lifecycle transition.
Source: request

### C-13: Every effective change of assignee has one append-only audit entry
Observable: Read `GET /tickets/:id/audit` after assigning, reassigning, or unassigning. Each effective change adds one entry at the end, with the ticket ID, next whole-log `seq`, action, timestamp, actor, and `changes.assignee` giving `from` and `to`. An assignment from null to Dana shows `{"from":null,"to":"Dana"}`, and clearing Dana shows `{"from":"Dana","to":null}`. Earlier entries compare equal before and after.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-14: An assignment audit entry attributes the change to the existing request actor
Observable: An effective PUT with `X-Actor: Sam` records `actor: "Sam"` in the audit entry. An absent or blank header records `"system"`. The header is trimmed and a 64-character ASCII actor is accepted, while one of 65 ASCII characters receives HTTP 400 `invalid`.
Source: existing: docs/api.md and src/http.js

### C-15: An effective assignment notifies the agent who received it
Observable: With working delivery and `NOTIFY_FILE` set, assign T-0042 to Dana. The notification output for that assignment is addressed to Dana and conveys that T-0042 was assigned to them. Reassigning it to Sam generates the corresponding notice for Sam, including when Dana's notice was still pending at the time of reassignment. Assigning it to Dana again after her previous notice was sent also generates a notice for Dana.
Source: request
Open: The requester decides whether a new effective assignment of the same ticket to the same agent while that agent's earlier assignment notice is still pending must generate a separate notice or can share the pending notice.

### C-16: Clearing the assignee produces no assignment notification
Observable: With delivery paused, clear an assigned ticket using `{"assignee":null}`. Comparing `GET /admin/outbox` before and after shows zero new assignment notifications, even if the ticket already had one pending.
Source: implied: by the request to notify the agent a ticket is assigned to

### C-17: Assignment notifications follow the existing background delivery control
Observable: With `WORKER_INTERVAL_MS=0`, a new assignment succeeds with a pending notice in `GET /admin/outbox` for the ticket and its new agent. No delivery occurs while the worker is off. With background delivery enabled and working, the due notice becomes `sent`, and a configured `NOTIFY_FILE` receives a JSON line for the delivery.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-18: Failed assignment deliveries follow the existing retry policy
Observable: With delivery failing, an assignment request still succeeds. Its notice remains `pending` after failures one through four, becoming eligible for the next attempt after 1, 2, 4, and 8 seconds respectively. Recovery before the fifth failed attempt allows a later attempt to mark it `sent`. A fifth failure leaves it `dead` with the last error visible in `GET /admin/outbox`.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-19: An effective assignment change is durable as one complete change when DATA_FILE is set
Observable: After a successful assign, reassign, or unassign, restart with the same `DATA_FILE`. The new assignee value, its corresponding audit entry, and any notice that the change queued are all present, with the notice retaining its recorded delivery state. If the process is interrupted during the save, the restarted service can show the state before or after that change, each as a complete state.
Source: existing: docs/decisions/0008-json-data-file.md

### C-20: Pending assignment delivery resumes from its saved state
Observable: Queue an assignment with `DATA_FILE` set and delivery paused, then restart with delivery enabled and working. The saved due notice is delivered. As with existing notices, an interruption after delivery but before the send is recorded can cause the same notice to be delivered again.
Source: existing: docs/decisions/0006-notification-outbox.md and docs/decisions/0008-json-data-file.md

### C-21: Previously saved tickets without an assignee load as unassigned
Observable: Start with an existing version 1 data file written before ticket assignment was added. Its tickets, history and notification records are available as before, and each of those tickets shows `"assignee":null` and matches `GET /tickets?assignee=` until assigned.
Source: existing: docs/decisions/0008-json-data-file.md

### C-22: Saved assignee values are subject to the existing startup validation
Observable: Start with an otherwise valid data file containing a ticket whose `assignee` is a JSON boolean, number, array or object, an empty string, or a name of 65 ordinary letters. Startup fails with a diagnostic identifying the ticket record and its assignee field. A missing field from a legacy ticket is accepted as in C-21, and an explicit null is valid.
Source: existing: docs/operations.md and docs/decisions/0008-json-data-file.md

### C-23: Overlapping assignment changes have the effects of one order of execution
Observable: With background delivery paused, issue two valid PUTs for the same ticket without waiting for the first response. The final ticket, the order of audit entries with their before and after values, and the assignment notices agree with applying the two requests in some serial order. Two simultaneous PUTs of the same new name yield one effective change.
Source: implied: by U-1 and the audit record of each effective change

### C-24: A named assignee filter selects tickets assigned to that agent
Observable: With tickets assigned to Dana, assigned to Sam, and unassigned, `GET /tickets?assignee=Dana` returns Dana's tickets. A valid name that has no matching ticket gives `{"items":[],"next":null}`.
Source: request
Open: The requester decides the treatment of nonempty query values that fall outside the accepted name rules, including returning `400 invalid` or an empty result.

### C-25: An empty assignee filter selects unassigned tickets
Observable: `GET /tickets?assignee=` returns tickets with `assignee: null` and excludes assigned tickets. With the parameter omitted, either kind of ticket can be included subject to the other query parameters.
Source: request

### C-26: HTTP list filters combine by intersection
Observable: For a request with a single value per supplied filter, every returned ticket satisfies each supplied `status`, `priority`, and `assignee` constraint. For `?status=open&priority=urgent&assignee=Dana`, exclude tickets that match only one or two of those constraints. The same rule applies when `assignee=` selects unassigned tickets and when only `status` and `priority` are supplied.
Source: request
Open: The requester decides how repeated query keys are interpreted for the new assignee filter.

### C-27: An assignee-filtered list pages the matching tickets under the existing cursor contract
Observable: Request matching tickets interspersed in numeric ticket ID order with nonmatching tickets. The JSON response contains `items` and `next`. A page holds up to `limit` matches in ID order, with a default of 20 and a valid range of 1 through 100 inclusive. Pass `next` as `cursor` with the same filters to resume after the previous page's last ID. `next` is null when no further match remains, including an empty result or an exactly full final page.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-28: The command-line table identifies each listed ticket's current assignee
Observable: Run `node bin/tickets.js list` against the data file using `DATA_FILE` or `--data FILE`. Each assigned row identifies its agent and the display distinguishes an unassigned row. The existing empty table listing still reports `no tickets`.
Source: request
Open: The requester decides the printed representation of an unassigned ticket.

### C-29: The raw command-line listing exposes the assignee within the existing row contract
Observable: Run `node bin/tickets.js list --raw` against a file containing assigned and unassigned tickets. Each ticket occupies one tab-separated line. Positions 1 through 4 still contain id, status, priority, and title respectively, and the line also identifies the assignee or indicates that it is unassigned.
Source: implied: by U-5 and the raw listing contract in README.md
Open: The requester decides the representation of an unassigned ticket in raw output and the encoding of any accepted name containing a row or column delimiter.

### C-30: The weekly report still counts tickets regardless of assignment
Observable: Run `npm run report:weekly -- --json` on the same data before and after changing only assignees. The total, by-status counts, and by-priority counts are the same.
Source: existing: README.md and scripts/weekly-report.js

### C-31: The service still starts on the configured port with npm start
Observable: Run `npm start` with `PORT` set to a free port. `GET /health` on that port returns `{"status":"ok"}`. The documented default when `PORT` is unset or empty remains 4180.
Source: request

### C-32: Running the service still requires no npm dependencies
Observable: In a checkout with supported Node.js and no installed packages, run `npm start`; the service starts without a package install.
Source: request

### C-33: The existing tests still pass as written
Observable: Run `npm test` with the existing files under `test/` unchanged. All their tests pass.
Source: request

### C-34: npm test runs new node:test coverage for the assignment feature
Observable: Run `npm test` and see passing new tests under `test/` covering the assignment behavior alongside the existing suite. The new files use `node:test`.
Source: request
