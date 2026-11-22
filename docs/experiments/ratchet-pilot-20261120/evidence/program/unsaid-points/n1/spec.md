## Use cases

### U-1: A dispatcher assigns a ticket so an agent can take it
Flow: The dispatcher finds an `open` or `in_progress` ticket, then sends `PUT /tickets/:id/assignee` with `{"assignee":"dana"}`. The ticket shows `"assignee":"dana"`. A repeat with the same assignee leaves the ticket as it was. To hand the ticket to Sam, the dispatcher sends `{"assignee":"sam"}` to the same endpoint.
Source: request

### U-2: A dispatcher clears an assignment so the ticket can be picked up again
Flow: The dispatcher sends `PUT /tickets/:id/assignee` with `{"assignee":null}` for an `open` or `in_progress` ticket. The ticket shows `"assignee":null` and appears in the results of `GET /tickets?assignee=` when it meets the other filters. A well-formed request to assign or clear a `resolved` or `closed` ticket gets `409 conflict`.
Source: implied: the request's state restriction and the conflict convention in docs/api.md

### U-3: An agent receives notice that a ticket was assigned to them
Flow: After Dana is assigned ticket `T-0001`, the service's notification delivery addresses the notice to Dana and identifies `T-0001` as assigned to her. Dana can request `GET /tickets?assignee=dana&status=open` to see her open tickets.
Source: request

### U-4: An operator lists tickets to see who owns them
Flow: The operator runs `node bin/tickets.js --data FILE list` against the service's data file and reads the assignee for each listed ticket, including whether it is unassigned.
Source: request

### U-5: An operator inspects assignment history and delivery to trace a change
Flow: The operator reads `GET /tickets/:id/audit` to see who changed the assignee and the old and new values. With `WORKER_INTERVAL_MS=0`, the operator reads `GET /admin/outbox` to see the pending notice. With `DATA_FILE` set, the operator can restart the service with that file and recover the assignment and its records.
Source: existing: docs/api.md and docs/operations.md

### U-6: A maintainer runs the suite to verify assignment and existing behaviour
Flow: The maintainer runs `npm test` and sees the new `node:test` cases from `test/` run alongside the unchanged existing tests.
Source: request

## Clauses

### C-1: The service still starts through `npm start` on the port selected by `PORT`
Observable: On Node.js 22 or later, run `npm start` without installing npm dependencies. `GET /health` on the configured free port answers `200` with `{"status":"ok"}`. Unset or empty `PORT` defaults to `4180`. The accepted numeric range is `0` through `65535`, with `0` requesting an available port. Invalid values stop startup with a message naming `PORT`.
Source: existing: README.md, package.json, src/config.js, src/server.js

### C-2: A valid agent name can replace the current assignee of an open or in-progress ticket
Observable: For an `open` or `in_progress` ticket, send `PUT /tickets/:id/assignee` with JSON `{"assignee":"dana"}`. The response is successful and a subsequent `GET /tickets/:id` shows `"assignee":"dana"`, whether the previous value was `null` or another agent. The same operation targets the id in the path without changing the assignee of any other ticket.
Source: request
Open: The requester would settle the supported form of names beyond ordinary non-empty names, including whitespace-only input, trimming, case or Unicode equivalence, control characters, and any separate name length bound beyond the existing HTTP body limit. The requester would settle the exact success status and response body if clients need a fixed assignment response contract.

### C-3: A null assignee clears the assignment of an open or in-progress ticket
Observable: For an assigned `open` or `in_progress` ticket, send `PUT /tickets/:id/assignee` with JSON `{"assignee":null}`. The response is successful and a subsequent `GET /tickets/:id` shows `"assignee":null`.
Source: request
Open: The success response contract is the same open decision identified in C-2.

### C-4: The assignment endpoint refuses changes on resolved or closed tickets
Observable: Send a well-formed assignment or unassignment to an existing `resolved` or `closed` ticket. The response is `409` with error code `conflict`, including when the supplied value already equals the ticket's assignee. The permitted states are `open` and `in_progress`.
Source: implied: the request's state restriction and the state-conflict rule in docs/api.md

### C-5: Setting the assignee to the ticket's current value is a no-op in a permitted state
Observable: On an `open` or `in_progress` ticket, repeat a successful assignment to `"dana"` or submit `null` when the ticket is already unassigned. The operation succeeds without changing the ticket or its `updated` timestamp, adding an audit entry, or enqueuing a notice. If identical requests overlap while the ticket stays eligible, only the request that first changes the value has those effects.
Source: implied: the request's same-agent no-op and the no-change convention in CONTRIBUTING.md

### C-6: Assignment requests use the service's JSON object validation
Observable: An assignment request with a missing or empty body, malformed JSON, or a top-level array, string, number, boolean, or `null` receives `400 invalid`.
Source: existing: docs/api.md and src/http.js

### C-7: The assignment body requires an assignee of the correct type
Observable: `{}`, `{"assignee":""}`, and bodies with a number, boolean, array, or object for `assignee` receive `400 invalid`. A JSON `null` as the value of the field is the explicit unassignment value.
Source: implied: the request's JSON body forms and non-empty-name rule, with the name boundaries open in C-2

### C-8: The assignment endpoint refuses unknown body fields
Observable: `{"agent":"dana"}` and `{"assignee":"dana","priority":"urgent"}` receive `400 invalid`.
Source: existing: docs/api.md

### C-9: Assignment bodies are subject to the configured size ceiling
Observable: A body larger than `MAX_BODY_BYTES` receives `400 invalid`. An otherwise valid body exactly at the ceiling passes the size check. The default ceiling is `65536` bytes and the configuration accepts whole numbers from `1024` through `1048576`.
Source: existing: README.md, src/config.js, src/http.js

### C-10: An assignment request for an absent ticket reports that it was not found
Observable: Send a well-formed `PUT /tickets/T-0099/assignee` when `T-0099` does not exist. The response is `404` with error code `not_found`.
Source: existing: docs/api.md

### C-11: Assignment errors use the existing JSON error envelope
Observable: A refused assignment responds with `content-type: application/json; charset=utf-8` and a body of the form `{"error":{"code":"invalid","message":"..."}}` for a `400`, using the corresponding code for other failures. The message is a string for a person to read.
Source: existing: docs/api.md and docs/decisions/0004-error-envelope.md

### C-12: Validation or state rejection leaves the assignment records intact
Observable: On a request rejected with `400`, `404`, or `409`, compare ticket data, audit history, and notices with their state before the request, with the worker off and no other changes in flight. The rejected request leaves them unchanged and creates no ticket for an absent id.
Source: implied: refusing an assignment in U-2 and the change contract in CONTRIBUTING.md

### C-13: Every API ticket representation includes its current `assignee`
Observable: Read the ticket objects from create, detail, list, patch, and transition responses. Each includes `assignee` as the current agent name or JSON `null` if unassigned. A ticket returned by `POST /tickets` starts with `"assignee":null`. The rule also applies to any ticket object returned by the new endpoint.
Source: request

### C-14: The existing ticket mutations preserve the assignee
Observable: Assign an eligible ticket to `"dana"`, then use an allowed title or priority patch or lifecycle transition. The resulting ticket still shows `"assignee":"dana"`, including on resolving, closing, or reopening it. The existing create, patch and transition body schemas still reject extra fields, including `assignee`, with `400 invalid`.
Source: implied: the separate assignment endpoint and the existing mutation contracts in docs/api.md

### C-15: A change of assignee sets the ticket's last-change time
Observable: At a later clock time, assign, reassign, or unassign an eligible ticket. The ticket's `updated` now shows that change time in ISO 8601 UTC. Other ticket fields besides `assignee` and `updated` retain their values.
Source: existing: docs/api.md

### C-16: A change of assignee adds a single append-only audit entry
Observable: `GET /tickets/:id/audit` shows one newly appended entry per actual assignee change, in the existing oldest-first history. Its `changes.assignee` holds the actual `from` and `to` values, including `null` on the unassigned side. Earlier entries stay as they were. If changes overlap, each entry's `from` is the assignee immediately before that change in audit order.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-17: Assignment history records the actor using the existing `X-Actor` convention
Observable: A change with `X-Actor: dana` records `actor: "dana"`. The header is trimmed and a missing or blank header records `actor: "system"`. A trimmed value up to 64 characters passes the actor check. A longer one receives `400 invalid`.
Source: existing: docs/api.md and src/http.js

### C-18: A notification about an assignment is addressed to the agent assigned in that change
Observable: Change an assignee from `null` to `"dana"` or from `"dana"` to `"sam"`. With normal delivery, the configured `NOTIFY_FILE` receives a JSON line addressed to the new assignee for that change. The subject or body identifies the ticket as assigned to the recipient. No assignment notice is generated for clearing the value to `null`.
Source: request

### C-19: An assignment notice can wait in the existing outbox independently of the API request
Observable: With `WORKER_INTERVAL_MS=0`, a successful assigning request leaves the notice visible under `pending` in `GET /admin/outbox`, with the affected ticket and the new assignee as recipient, and no delivery until the worker runs. With delivery enabled, a relay failure does not turn the assignment into an API failure.
Source: existing: docs/decisions/0006-notification-outbox.md and docs/operations.md

### C-20: Distinct recipients' pending assignment notices survive reassignment
Observable: With delivery paused, assign one ticket to `"dana"` and then to `"sam"`. The outbox shows a pending assignment notice for that ticket addressed to each of them. Starting delivery sends each notice to its recorded recipient.
Source: implied: the notice requirement for both assignments in U-1 and the pending outbox contract
Open: The requester would settle whether a later actual assignment back to Dana while Dana's original notice is pending counts as the same news under the existing outbox deduplication rule or calls for another notice.

### C-21: Failed assignment delivery uses the existing outbox retry policy
Observable: With the worker running, cause delivery of an assignment notice to fail. The first four failures leave it pending, due again after `1`, `2`, `4`, and `8` seconds respectively and attempted on a worker tick. Success moves it to `sent`. The fifth failure moves it to `dead` with the failure available as `lastError` in `GET /admin/outbox`.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-22: A saved assignment change survives restart as a whole
Observable: With `DATA_FILE` set, a successful assignment, reassignment, or unassignment is visible after a restart from that file, including its corresponding audit entry and any notice the change caused. If the process stops during the file update, reopening the file shows either the preceding saved state or the complete change. A pending notice resumes delivery with the worker enabled under the existing at-least-once policy, so a crash after sending but before recording the send can replay the same notice.
Source: existing: docs/decisions/0008-json-data-file.md and docs/decisions/0006-notification-outbox.md

### C-23: Pre-assignment data files remain usable
Observable: Start the server or run the CLI against a valid version 1 data file written before assignment existed. Tickets without an assignee are unassigned and are returned by `GET /tickets?assignee=` when no other filter excludes them. Existing ticket data, history, and notifications are retained without assigning an agent or generating a notice on load.
Source: existing: docs/decisions/0008-json-data-file.md

### C-24: `GET /tickets?assignee=<agent>` selects tickets currently assigned to that agent
Observable: With tickets assigned to `"dana"`, tickets assigned to `"sam"`, and unassigned tickets, `GET /tickets?assignee=dana` returns only Dana's tickets across the pages, regardless of status when no status filter is supplied. Reassigning a ticket from Dana to Sam removes it from Dana's results in a fresh listing. A name with no matching tickets yields `{"items":[],"next":null}`.
Source: request
Open: The requester would settle the handling of repeated `assignee` parameters. Name matching follows the supported name rules left open in C-2.

### C-25: `GET /tickets?assignee=` selects currently unassigned tickets
Observable: With a mix of assigned and unassigned tickets, `?assignee=` includes only tickets whose `assignee` is `null`, including a ticket whose assignment was cleared.
Source: request

### C-26: Omitting the assignee filter leaves both assigned and unassigned tickets eligible
Observable: Send `GET /tickets` without `assignee`. Both assigned and unassigned tickets appear in the results when they match the other filters.
Source: implied: the request gives `assignee=` a specific filtering meaning

### C-27: A listed ticket must match every supplied ticket filter
Observable: `GET /tickets?assignee=dana&status=open&priority=urgent` lists only tickets satisfying all three filters. The same rule applies with `assignee=` for the unassigned subset and to `status` with `priority` when `assignee` is omitted. The existing status filters are `open`, `in_progress`, `resolved`, and `closed`. The existing priority filters are `low`, `normal`, `high`, and `urgent`. A supplied status or priority outside its set still receives `400 invalid`.
Source: request

### C-28: The assignee filter participates in existing cursor pagination
Observable: A list page contains `items` in numeric ticket id order and `next` as an opaque cursor or `null`. The page fills up to `limit` with matching tickets and has `next: null` exactly when no further matching ticket remains. Pass the previous `next` as `cursor` with the same filters to see matching tickets after the last id served, using current ticket values for that page. `limit` defaults to 20, accepts whole numbers from 1 through 100, and gives `400 invalid` outside that range. An invalid cursor still gives `400 invalid`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-29: The CLI listing shows the current assignee of each listed ticket
Observable: Run `node bin/tickets.js --data FILE list` or use `DATA_FILE` with the same command. In the table, an operator can tell which rows are assigned to Dana or Sam and which are unassigned. The existing `--status` and `--priority` options remain usable. A table listing with no matching tickets still prints `no tickets`.
Source: request
Open: The requester and operators would settle any required display for an unassigned value. The requester and raw-output consumers would settle whether `--raw` also exposes the assignee and, if so, how new values are represented while meeting C-30.

### C-30: The CLI preserves the positional contract used by raw-list consumers
Observable: `list --raw` still emits one tab-separated row per listed ticket, with `id`, `status`, `priority`, and `title` in columns 1 through 4 respectively. Assigned names cannot cause an extra ticket row or shift any of those columns. For the same ticket data, `npm run report:weekly` and the report's `--json` mode still count each ticket once under its existing status and priority.
Source: existing: README.md and scripts/weekly-report.js

### C-31: The new test cases run through the existing test command
Observable: `npm test` discovers and runs new `node:test` cases under `test/` that exercise the new assignment behaviour.
Source: request

### C-32: Existing service behaviour continues to pass the unchanged test suite
Observable: Run `npm test`. All tests present before the feature still run and pass with their original assertions.
Source: request
