## Failing now

- C-34 — Startup accepts an explicit 65-letter assignee in a version 1 ticket record. Numeric and empty-string assignees are rejected.
- C-40 — The human CLI renders an agent named `-` and an unassigned ticket identically. The operator cannot tell which ownership the row represents.
- C-44 — `npm test` discovers five new assignment cases. None exercises assignee visibility through the command-line listing.
- C-45 — The blocked save returns 500 `internal`, but the running API exposes Lee in place of Dana, a new update time, an audit entry and a pending notice. An unrelated successful save then makes those changes survive restart. Retrying the original PUT sees Lee already assigned.

## Discoveries

- Define how nonempty filter values are compared to names stored by the assignment route after any canonicalization. | Observable: Assign a name with surrounding spaces and query with both the canonical spelling and the original spelling. | Why: The build trims the PUT value and compares the query spelling verbatim. The open identity choice affects the resulting match.

## Preserved behaviour

- `src/app.js` | GET /health returns 200 JSON with status ok | C-43 preserves health, JSON responses, method and route errors, and optional request logging
- `src/app.js` | POST /tickets accepts its existing object, passes the actor and returns the new ticket with 201 | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/app.js` | GET /tickets/:id returns the full ticket with 200 or a missing-ticket 404 | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/app.js` | PATCH /tickets/:id returns the updated ticket with 200 and reports existing invalid, conflict and missing-ticket errors | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/app.js` | POST /tickets/:id/transition returns the new ticket with 200 and reports invalid destinations and conflicts | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/app.js` | GET /tickets/:id/audit returns the ticket’s oldest-first history in items | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/app.js` | GET /tickets/:id/audit reports 404 for an unknown ticket | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/app.js` | GET /tickets returns items and next using filters and cursor | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/app.js` | GET /admin/outbox reports pending, sent and dead arrays, including an empty report on first start | C-43 preserves existing outbox states, event identities, deduplication and requester delivery wording
- `src/app.js` | Existing routes use JSON with UTF-8. Unknown paths and unsupported methods retain their 404 messages | C-43 preserves health, JSON responses, method and route errors, and optional request logging
- `src/app.js` | Configured MAX_BODY_BYTES governs existing JSON body routes. The creation route rejects oversized requests | C-43 npm test runs and passes the pre-existing case inventory with all original test files unchanged
- `src/app.js` | Existing body-changing routes read the X-Actor header and default it to system | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/app.js` | LOG_REQUESTS=1 emits method, path, status and duration. Request logging is off by default | C-43 preserves health, JSON responses, method and route errors, and optional request logging
- `src/app.js` | Malformed JSON and non-object bodies retain their original human-readable invalid messages | C-43 preserves existing request validation messages
- `src/format.js` | Human list retains the ticket ID, title, priority, status, requester and minute-precision update time | C-43 preserves CLI human listing fields, show details and history, empty list and exit codes
- `src/format.js` | Raw list retains id, status, priority and title in tab-separated columns 1 through 4 | C-41 raw consumers retain four positional fields and weekly totals count each ticket once
- `src/format.js` | The weekly report reads those positions and counts every ticket once by status and priority | C-41 raw consumers retain four positional fields and weekly totals count each ticket once
- `src/format.js` | Show prints ID and title, status, priority, requester, full created and updated times | C-43 preserves CLI human listing fields, show details and history, empty list and exit codes
- `src/format.js` | Show prints History and the earlier action, actor and human-readable field deltas | C-43 preserves CLI human listing fields, show details and history, empty list and exit codes
- `src/persistence.js` | The server and CLI can open a version 1 file with existing open, in-progress and inactive tickets | C-30 legacy tickets, including resolved and closed, are readable in the API and CLI with their records
- `src/persistence.js` | The data file retains id, title, requester, priority, status, created and updated for each ticket | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | Audit records retain seq, ticket, action, actor, at, and from/to changes | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | Outbox records retain id, key, type, to, ticket, data, state, attempts and timing/error fields | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | The document retains version 1, savedAt, nextNumber and outbox.nextId, with no temporary file after a successful save | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | Restart advances ticket numbers and outbox IDs without reuse | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | An unsupported version, bad priority, counter reuse, a gap in audit sequencing or invalid delivery state prevents startup with a diagnostic | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | Without DATA_FILE, tickets are lost when the process ends | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/persistence.js` | CLI readers expose the existing title and ownership-independent data and leave the document untouched | C-42 human and raw listing preserve bytes of assigned and legacy files
- `src/store.js` | New tickets are open with sequential IDs and the same initial created and updated timestamps | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/store.js` | Single-ticket reads expose the stored fields, and missing IDs report not_found | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/store.js` | Listing returns the first or following ID-ordered page and honors a single existing status or priority filter | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/store.js` | Title and priority edits update the change time, honor the actor and record only the changed fields | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/store.js` | A repeated edit retains updated and appends no history or outbox records. Closed tickets reject edits | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/store.js` | Tickets move open → in_progress → resolved, then either reopen or close. Closed stays final | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/store.js` | The original create, edit and transition audit actions and audit field sets remain, in global sequence order | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/store.js` | Creation and resolution create their requester notices, and a second resolution while the first notice is pending deduplicates by key | C-43 preserves existing outbox states, event identities, deduplication and requester delivery wording
- `src/store.js` | An existing delivery moves the event from pending to sent, increments attempts and clears retry metadata | C-43 preserves existing outbox states, event identities, deduplication and requester delivery wording
- `src/store.js` | A failed existing delivery is recorded for retry and eventually remains dead with its last error | C-43 npm test runs and passes the pre-existing case inventory with all original test files unchanged
- `src/store.js` | Tickets, audit and outbox survive restart from DATA_FILE, and subsequent changes advance the stored counters | C-43 preserves version 1 storage fields, monotonic identifiers, record checks and memory mode
- `src/store.js` | CLI list drains all matching pages. CLI show reads the selected ticket’s history | C-43 preserves CLI human listing fields, show details and history, empty list and exit codes
- `src/templates.js` | Received notification keeps the ticket ID in the subject and the original title and acknowledgement text in the body | C-43 preserves existing outbox states, event identities, deduplication and requester delivery wording
- `src/templates.js` | Resolved notification keeps the ticket ID in the subject and the original title and seven-day reopen instruction in the body | C-43 preserves existing outbox states, event identities, deduplication and requester delivery wording
- `src/tickets/query.js` | The status filter accepts existing states. Empty and unknown statuses are invalid | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | The priority filter accepts existing priorities and rejects unknown values | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | The API keeps the existing cursor format and reads the next page. An invalid cursor returns invalid | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | The original page size defaults to 20 and accepts integer limits from 1 through 100 | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | Unknown parameters, including retired offset, remain ignored | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | A listing with no filters includes all tickets, and the empty list remains items [] with next null | C-43 preserves original listing filters, empty pages, cursor handling and ignored parameters
- `src/tickets/query.js` | CLI status and priority options still select matching rows | C-40 the human listing shows per-ticket owner or unassigned and respects CLI filters
- `src/tickets/query.js` | Invalid status, priority, limit and cursor retain their original human-readable messages | C-43 preserves existing request validation messages
- `src/tickets/validate.js` | Creation requires a title and requester, trims both, preserves a supplied priority and defaults an omitted priority to normal | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/tickets/validate.js` | Creation accepts title and requester at 200 and 64 characters and refuses the first oversize values | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/tickets/validate.js` | Creation refuses missing, out-of-range and malformed fields or unknown keys with invalid | C-43 preserves the shape, defaults, IDs and validation of existing creation and retrieval
- `src/tickets/validate.js` | Editing accepts the original fields independently or together, validates titles and priorities and rejects empty changes and unknown fields | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/tickets/validate.js` | Lifecycle validation requires to to name an existing status and rejects extra fields | C-43 preserves legacy edit and transition rules, original audit deltas and audit sequencing
- `src/tickets/validate.js` | Missing, empty, overlong and multiline fields retain the original field-specific validation messages | C-43 preserves existing request validation messages
- `src/tickets/validate.js` | Unknown fields, empty edits and invalid lifecycle choices retain their existing messages | C-43 preserves existing request validation messages
