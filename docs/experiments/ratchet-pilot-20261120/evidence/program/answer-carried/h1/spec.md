## Use cases

### U-1: A help-desk operator assigns or clears a ticket to record who is responsible for it
Flow: On an `open` or `in_progress` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":"dana"}`, then read the ticket to see `"assignee":"dana"`. Send the same assignment again and see no change. Send `{"assignee":null}` to clear it. The service refuses assignment and unassignment on `resolved` or `closed` tickets.
Source: request

### U-2: An agent learns that a ticket was assigned to them
Flow: An operator assigns a ticket to `dana`. Dana receives a notice identifying the ticket and saying it was assigned to them. If the operator next assigns the ticket to `sam`, Sam receives notice of their assignment even if Dana's notice was still pending when the operator made the change.
Source: request

### U-3: An API caller lists tickets to find an agent's work or find unassigned tickets
Flow: Request `GET /tickets?assignee=dana` for Dana's tickets or `GET /tickets?assignee=` for unassigned tickets. Add `status=open&priority=urgent` to either query to narrow it to open, urgent tickets. Read `assignee` on each returned ticket and reuse any `next` cursor with the same filters to continue.
Source: request

### U-4: A command-line operator lists saved tickets to see who is responsible for each
Flow: Run `node bin/tickets.js --data FILE list` with a data file containing assigned and unassigned tickets. Read the agent on an assigned ticket's row and see when a ticket is unassigned.
Source: request

### U-5: A support lead runs the weekly report to get the existing ticket counts
Flow: Run `node scripts/weekly-report.js --data FILE --json` on a file with both assigned and unassigned tickets. The report still gives the total and counts by status and priority.
Source: existing: README.md

### U-6: An auditor reads a ticket's history to see who changed its assignment
Flow: Use `X-Actor: lee` to set the assignee to `dana` on an unassigned ticket. Read `GET /tickets/:id/audit` to see the change from `null` to `"dana"` attributed to `lee`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### U-7: A service operator restarts the service to resume work on saved tickets
Flow: Start with `npm start` using `PORT` and `DATA_FILE`. An existing file can contain tickets created before assignment was available. Read one as unassigned, assign it, then restart with the same file. Read back the saved assignee and find the assignment's history and notification record.
Source: existing: docs/operations.md

### U-8: A maintainer runs the test suite to verify assignment alongside the existing service
Flow: Run `npm test` to run the existing tests unchanged alongside new `node:test` tests under `test/` covering assignment behavior.
Source: request

## Clauses

### C-1: The service remains runnable without installing npm dependencies
Observable: Run `npm start` on the supported Node.js runtime (22 or later) with npm available and no installed npm dependencies. The service can start.
Source: request

### C-2: The service started by `npm start` listens on the configured `PORT`
Observable: Set `PORT` to a free port and run `npm start`. `GET /health` on that port returns `{"status":"ok"}`. The configured range is 0 through 65535 inclusive. At 0 the system selects a free port. An unset or empty value defaults to 4180. A value outside the range stops startup with an error naming `PORT`.
Source: existing: src/config.js

### C-3: A valid named assignment sets the ticket's assignee in either eligible status
Observable: For an existing ticket in each of `open` and `in_progress`, send `PUT /tickets/:id/assignee` with `{"assignee":"dana"}`. The request succeeds and a subsequent `GET /tickets/:id` shows `"assignee":"dana"`, including when the ticket previously showed a different agent.
Source: request
Open: The requester would settle the accepted name syntax and which spellings identify the same agent, including case, surrounding whitespace, whitespace-only strings, control characters and Unicode normalization. Assignment, same-agent detection and lookup need to agree on agent identity.

### C-4: A valid unassignment clears the ticket's assignee in either eligible status
Observable: For an assigned ticket in each of `open` and `in_progress`, send `PUT /tickets/:id/assignee` with `{"assignee":null}`. The request succeeds and a subsequent `GET /tickets/:id` shows `"assignee":null`.
Source: request

### C-5: The assignment endpoint acknowledges success according to the API's JSON conventions
Observable: A valid PUT on an eligible ticket, including a repeat of its current assignment, produces a successful response conforming to the service's JSON response convention. The caller can read the resulting ticket using `GET /tickets/:id`.
Source: existing: docs/api.md
Open: The requester or API consumers would settle the new endpoint's exact success status and response payload. The existing API documents success payloads for its individual endpoints.

### C-6: A resolved or closed ticket refuses an assignment request
Observable: On a `resolved` or `closed` ticket, a well-formed PUT with a valid agent name or with `null` returns HTTP 409 with `error.code` equal to `"conflict"`, even if the requested value is already present. The ticket's stored assignment remains as it was.
Source: request

### C-7: A well-formed assignment request for a missing ticket returns `not_found`
Observable: Send a valid assignment body to `PUT /tickets/T-0099/assignee` when `T-0099` does not exist. The response is HTTP 404 with `error.code` equal to `"not_found"`.
Source: existing: docs/api.md

### C-8: The assignment endpoint refuses malformed input as `invalid`
Observable: On an eligible ticket, a PUT with an absent body, malformed JSON, a non-object body (including JSON `null` or an array), a missing `assignee`, a non-null value of a non-string type, `"assignee":""`, or an extra body field returns HTTP 400 with `error.code` equal to `"invalid"`. A JSON object with just `"assignee":null` is valid input.
Source: existing: docs/api.md

### C-9: The assignment endpoint honors the configured request-body size limit
Observable: Count the entire PUT body in bytes. At `MAX_BODY_BYTES` a well-formed body such as a valid assignment padded with JSON whitespace is eligible for normal processing. Above that limit the response is HTTP 400 with `error.code` equal to `"invalid"`. The default is 65536 bytes. Startup accepts a configured limit from 1024 through 1048576 bytes inclusive and rejects limits outside that range.
Source: existing: src/http.js and src/config.js

### C-10: Assignment errors use the service's JSON error envelope
Observable: A rejected assignment request returns JSON with an `error` object containing a string `code` and a human-readable string `message`. An unexpected service fault returns HTTP 500 with `error.code` equal to `"internal"` and a message that does not expose fault details.
Source: existing: docs/decisions/0004-error-envelope.md

### C-11: A rejected assignment request creates no record of an assignment change
Observable: After a PUT refused for invalid input, missing ticket or ineligible status, compare the affected ticket if present, its history and the outbox with the state before the request. The refusal adds no assignment change or notice.
Source: existing: CONTRIBUTING.md

### C-12: Every API ticket representation includes its current `assignee`
Observable: Inspect a ticket returned by create, get, list, patch or lifecycle transition, and any ticket representation returned by the assignment endpoint. The `assignee` field contains the current agent's name as a JSON string, or JSON `null` for an unassigned ticket. A newly created ticket shows `"assignee":null`.
Source: request

### C-13: A change to the assignee leaves the other ticket data intact apart from the change timestamp
Observable: Compare a ticket before and after assignment or unassignment. Its id, title, priority, requester, status and creation time remain the same.
Source: implied: U-1 changes who is responsible for an existing ticket

### C-14: Other ticket changes preserve the assignee
Observable: Assign an eligible ticket, then edit its title or priority or move it along any permitted lifecycle transition. Reading the ticket still shows that agent, including on resolution, closure or reopening. Editing or moving a ticket that was unassigned leaves its assignee `null`.
Source: existing: docs/api.md

### C-15: An effective assignee change updates the ticket's last-change time
Observable: If the clock has advanced since the previous change, assign, reassign or unassign the ticket and read it back. The ticket's `updated` is the time of the assignee change, as an ISO 8601 timestamp in UTC.
Source: existing: docs/api.md

### C-16: Setting the assignee to its current value is a no-op on an eligible ticket
Observable: Assign `dana`, wait until a distinct timestamp is possible, then send the same assignment while the ticket is eligible. The full ticket including `updated` is unchanged, its history has no new entry and the outbox has no new notice from the repeat. The same is true of sending `null` to an eligible ticket already showing `null`. Two simultaneous valid PUTs setting an eligible ticket to the same new agent have the effect of one change followed by a no-op.
Source: request

### C-17: Each effective assignee change appends one entry to the ticket's history
Observable: Read `GET /tickets/:id/audit` after assignment, reassignment or unassignment. Each effective change adds one entry after the previous entries with the ticket id, the next sequence position in the whole log, an action identifying the change, its time, its actor and `changes.assignee` with `from` and `to` containing the previous and new values. Unassigned values in these changes are JSON `null`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-18: Assignment audit entries follow the existing `X-Actor` convention
Observable: On an effective assignee change, `X-Actor: lee` records `"actor":"lee"`, surrounding whitespace is removed, and a missing or blank header records `"actor":"system"`. A trimmed actor of length 64 is accepted. A trimmed actor longer than 64 UTF-16 code units yields HTTP 400 `invalid`.
Source: existing: src/http.js

### C-19: The service directs an assignment notice to the agent who gained the ticket
Observable: After a successful change to `"dana"`, the corresponding record in `GET /admin/outbox` is for that ticket and directed to Dana. If another valid PUT changes the assignee to `"sam"` while Dana's notice is pending, there is also a notice for Sam's assignment. An assignment notice for one ticket does not satisfy the requirement to notify about a different ticket. Once an earlier notice is sent, a later fresh assignment of that ticket to the same agent after an intervening assignee change produces a new notice.
Source: request
Open: The requester or notification operator would settle how agent names map to delivery destinations. The requester would settle whether two genuine assignments of the same ticket to the same agent each need their own notice when the earlier equivalent notice is still pending, as when assigning Dana, then Sam, then Dana again with the worker off.

### C-20: Unassigning a ticket creates no assignment notice
Observable: With the worker off, clear an assigned ticket using `{"assignee":null}`. The outbox has no new notice announcing an assignment from that request.
Source: implied: the notice in the request is for the agent a ticket is assigned to

### C-21: The assignment notice tells the recipient which ticket was assigned to them
Observable: With delivery enabled and a writable `NOTIFY_FILE`, a successful delivery appends a JSON line for the assigned agent and ticket. Its message communicates that the identified ticket was assigned to the recipient. With no `NOTIFY_FILE`, delivery is kept in memory according to the existing notification behavior and the outbox records it as sent.
Source: existing: docs/operations.md

### C-22: Assignment notices honor the existing worker control
Observable: With `WORKER_INTERVAL_MS=0`, a successful assignment leaves its notice pending in `GET /admin/outbox` without delivering it. With a positive worker interval and a working destination, a due notice is delivered in the background and appears under `sent`. When the setting is unset or empty, the worker runs at the default interval of 500 ms.
Source: existing: docs/operations.md and README.md

### C-23: The normal notification retry policy applies to assignment notices
Observable: With delivery failing, the outbox shows a pending notice with the failure recorded. It is eligible for retry after 1, 2, 4 and 8 seconds following failures one through four respectively. After the fifth failure the notice is `dead` with `lastError` and no further automatic attempts. Successful delivery marks it `sent`. A delivery failure does not undo the assignment.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-24: A pre-assignment data file still loads its tickets
Observable: Start the service or run the command-line listing using a valid file previously written by the service that lacks `assignee` on its ticket records. The existing tickets are available as unassigned with their other data intact.
Source: existing: docs/decisions/0008-json-data-file.md

### C-25: A saved assignment change survives a restart as one complete change
Observable: With `DATA_FILE` set, make an assignment change and restart with the same file. The ticket, its assignment history and any notice caused by the change survive. If the process is interrupted during the change, loading the file gives the state before or after the whole change. A saved pending notice can still be delivered after restart. An interruption after sending but before recording delivery can cause another delivery attempt for that same notice.
Source: existing: docs/decisions/0008-json-data-file.md and docs/decisions/0006-notification-outbox.md

### C-26: A saved ticket's assignee is subject to the data file's record checks
Observable: Start the service with an otherwise valid data file whose ticket has an explicit `assignee` value of a number, boolean, array or object. Startup fails with a diagnostic identifying the offending record. A missing field in an older file remains eligible for the unassigned default.
Source: existing: docs/operations.md

### C-27: A non-empty `assignee` filter selects the named agent's tickets
Observable: With tickets assigned to `dana` and `sam` and others unassigned, `GET /tickets?assignee=dana` lists the tickets assigned to Dana, whatever their status or priority if no other filters were supplied. A valid name with no matching tickets yields `{"items":[],"next":null}`.
Source: request
Open: The requester would settle how repeated `assignee` parameters in one URL are interpreted. The agent identity rules on C-3 also apply when comparing a filter name.

### C-28: An empty `assignee=` filter selects unassigned tickets
Observable: `GET /tickets?assignee=` includes tickets showing `"assignee":null` and excludes tickets showing an agent name. Newly created, explicitly unassigned and older tickets loaded without an assignee all qualify.
Source: request

### C-29: Omitting `assignee` leaves assignment out of the filter
Observable: With eligible results in both assignment states, `GET /tickets` without an `assignee` parameter can list both assigned and unassigned tickets, subject to other supplied filters and pagination.
Source: implied: the request adds a filter with distinct behavior when supplied as an empty value

### C-30: A ticket must match every supplied list filter
Observable: With tickets that differ in status, priority and assignee, `GET /tickets?status=open&priority=urgent&assignee=dana` includes only tickets matching all three. Using `assignee=` instead selects only open, urgent unassigned tickets. Combining just `status` and `priority` likewise requires both to match.
Source: request

### C-31: Assignment-filtered listings use the existing cursor pages over matching tickets
Observable: Interleave matching and nonmatching tickets and list with an assignee filter and `limit=2`. The page has up to two matching tickets in numeric ticket id order. If more matches remain after the last id on the page, the caller can pass the opaque `next` as `cursor` with the same filters to resume after that id. With no matches remaining, `next` is `null`. The page size is 20 when omitted. The accepted limits are whole numbers from 1 through 100 inclusive, with other or empty values returning HTTP 400 `invalid`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-32: The command-line list table shows each ticket's assignment
Observable: Run `node bin/tickets.js --data FILE list` with saved assigned and unassigned tickets. Each displayed row identifies its agent, such as `dana`, or makes clear that the ticket is unassigned. An empty result still prints `no tickets`.
Source: request

### C-33: Raw listing preserves the weekly report's input contract
Observable: Run `node bin/tickets.js --data FILE list --raw`. Each listed ticket still occupies one line, with id, status, priority and title in tab-separated columns 1 through 4 respectively. Running the weekly report over the same file still counts those tickets by status and by priority.
Source: existing: README.md
Open: The requester, with raw-output consumers, would settle whether the assignment display requirement also calls for an assignee in `list --raw`. The existing column positions apply either way.

### C-34: Command-line listing stays read-only
Observable: Compare the data file before and after listing it through `--data FILE` or `DATA_FILE`. Listing does not alter the saved file, including when reading a file written before the assignment feature.
Source: existing: docs/operations.md

### C-35: Existing service operations remain available under their established contracts
Observable: Existing callers can still create, read, edit and transition tickets, read history and outbox reports, and receive the existing requester notices for creation and resolution. The command-line `show` command can still retrieve a ticket and its history. These operations retain their existing outcomes subject to the ticket field and listing changes above.
Source: request
Open: The requester would settle whether the command-line `show` details should also present a separate current-assignee field. The request explicitly calls for display in the listing.

### C-36: The existing tests pass unchanged
Observable: Run `npm test` with the existing tests intact. Those tests still pass.
Source: request

### C-37: The test suite runs new assignment coverage
Observable: The new behavior is covered by `node:test` tests under `test/`. Running `npm test` discovers and runs them with the existing suite.
Source: request

### C-38: An agent name can have at most 40 characters
Observable: On an eligible ticket, a PUT with an otherwise valid 40-character agent name succeeds. An otherwise valid 41-character agent name returns HTTP 400 with `error.code` equal to `"invalid"`.
Source: answer
