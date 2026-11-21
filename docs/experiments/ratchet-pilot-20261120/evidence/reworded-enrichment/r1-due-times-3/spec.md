## Use cases

### U-1: A requester opens a ticket to learn its response deadline
Flow: With due times on and the default schedule in effect, the requester creates a ticket at `2025-09-01T08:15:00.000Z`. The returned ticket shows `due` at `2025-09-01T12:15:00.000Z` for urgent (4 hours), `2025-09-02T08:15:00.000Z` for high (24 hours), `2025-09-04T08:15:00.000Z` for normal (72 hours), or `2025-09-08T08:15:00.000Z` for low (168 hours). Omitting the priority gives the normal deadline. The same deadline appears when the ticket is read again.
Source: request

### U-2: A help-desk operator changes the response schedule for future assignments
Flow: The operator changes the response hours without editing code. A newly created ticket uses the effective hours for its priority. Previously assigned deadlines survive the schedule change, subsequent edits to those tickets, and a restart.
Source: request

### U-3: An agent finds overdue work to decide which tickets need attention
Flow: The agent calls `GET /tickets?overdue=true` with due times on. They see only tickets currently `open` or `in_progress` whose saved deadlines have passed. They can narrow the results with the existing filters and follow the usual page cursors. Resolving a ticket removes it from the result, and reopening it makes it eligible again using its original deadline.
Source: implied: the overdue listing in the request and the existing ticket lifecycle

### U-4: A production operator prepares existing tickets before exposing deadlines
Flow: The operator prepares the production `DATA_FILE`. Each existing ticket receives a deadline based on its saved creation time and priority. The operator establishes that the file holds the deadlines before the API exposes them with `DUE_TIMES=on`. While the flag is unset or has a value other than `on`, clients get the 1.4.0 responses. If preparation is interrupted, the operator can resume from the intact saved state after addressing the cause.
Source: request

### U-5: A production operator restores 1.4.0 to recover from a bad release
Flow: The operator stops the new service and starts 1.4.0 against the same `DATA_FILE` using `npm start` and the configured `PORT`. They can read every ticket, including tickets created while the new version was running.
Source: request

### U-6: Operators and support leads read tickets from disk to inspect the queue and report its totals
Flow: Operators use `bin/tickets.js` to list tickets or show a ticket and its history. The weekly report reads the raw list's tab-separated id, status, priority, and title columns to count tickets. Both tools continue to read the file after the service saves deadlines.
Source: existing: README.md

### U-7: A maintainer runs the test suite to verify due times and existing behavior
Flow: The maintainer runs `npm test` on the dependency-free Node.js service. The command runs the unchanged tests and the added `node:test` tests under `test/` in the same suite.
Source: request

## Clauses

### C-1: The service runs on Node.js 22 or later without npm dependencies
Observable: On a supported Node.js installation, an operator can run `npm start` without installing any packages.
Source: existing: README.md

### C-2: `npm start` serves the API on the port selected by `PORT`
Observable: With an available configured port, `GET /health` there returns `{"status":"ok"}`. The port defaults to 4180 when unset or empty, and setting 0 lets the system choose a free port. `PORT` accepts whole numbers from 0 through 65535, subject to the operating system allowing the bind.
Source: existing: src/config.js

### C-3: The default response schedule is 4 hours for urgent, 24 for high, 72 for normal, and 168 for low
Observable: With no hours override, tickets of the four priorities created at `2025-09-01T08:15:00.000Z` have the respective deadlines in U-1. When a create request omits priority, its deadline uses `normal`.
Source: request

### C-4: The help desk can change the response hours for any supported priority without a code change
Observable: An operator supplies a different schedule through the service's environment settings. Once effective, changing urgent from 4 to 6 hours gives a new urgent ticket created at `2025-09-01T08:15:00.000Z` a deadline of `2025-09-01T14:15:00.000Z`.
Source: implied: the configurable response hours in the request and the environment settings described in README.md
Open: The requester decides which durations must be supported beyond positive whole hours, including zero and fractions, and any help-desk minimum or maximum.

### C-5: An unusable response-hours setting follows the existing startup configuration error contract
Observable: Starting the service with a response-hours value it needs to use but cannot interpret reports the offending setting at startup and exits with status 2.
Source: existing: src/server.js

### C-6: A new ticket's deadline is its creation instant plus the effective response duration for its priority at creation
Observable: Subtract the returned `created` instant from the returned `due` instant. The elapsed time is the configured hours multiplied by 3,600,000 milliseconds per hour, including across calendar or daylight-saving changes. Node.js represents timestamps from −8,640,000,000,000,000 through +8,640,000,000,000,000 milliseconds from the Unix epoch, inclusive. A result outside that interval cannot be returned as a valid ticket timestamp.
Source: request
Open: The requester decides how to handle an otherwise usable schedule and creation instant whose sum is outside Node.js's timestamp range. This can also arise during preparation of an existing file.

### C-7: With due times on, every ticket returned by the HTTP API includes its deadline as `due`
Observable: A successful create, get, patch, or transition response, or an item in any ticket listing, contains a `due` timestamp in the API's ISO 8601 UTC convention, such as `2025-09-01T12:15:00.000Z`. This applies to `open`, `in_progress`, `resolved`, and `closed` tickets.
Source: request

### C-8: `due` is a service-assigned field
Observable: Supplying `due` in a create, patch, or transition body gives HTTP 400 with `error.code` set to `invalid`, as for other fields those bodies do not accept.
Source: implied: the request assigns deadlines from creation time and priority, and docs/api.md rejects unknown body fields

### C-9: A ticket edit leaves an assigned deadline fixed
Observable: Changing a title or priority, or moving a ticket through its lifecycle including reopening it, leaves the same `due` value in the response and on a subsequent read.
Source: request

### C-10: A response-hours change leaves previously assigned deadlines fixed
Observable: After a schedule change takes effect, a previously assigned ticket still has the same `due` even if a new ticket of that priority receives a different response duration.
Source: request

### C-11: Without `DUE_TIMES=on`, the API answers as in 1.4.0
Observable: With `DUE_TIMES` unset, empty, or set to a value other than `on`, equivalent requests against equivalent ticket state return the existing status codes and bodies, including ticket representations without `due`. This holds even when the data file already contains deadlines.
Source: request

### C-12: While due times are off, `overdue` is ignored in ticket listings
Observable: `GET /tickets?overdue=true`, or the same request with any other `overdue` value, produces the same listing as omitting the parameter, with all other query parameters held fixed.
Source: existing: src/tickets/query.js

### C-13: With due times on, `overdue=true` selects exactly the active tickets whose deadlines have passed
Observable: At the listing time, a ticket qualifies if its saved `due` is earlier than that time and its current status is `open` or `in_progress`. A ticket due at that instant or later is excluded. `resolved` and `closed` tickets are excluded regardless of time. As time advances past a deadline, a still-active ticket qualifies on a fresh request without any ticket edit.
Source: request

### C-14: The overdue filter narrows each existing ticket filter
Observable: With due times on, `?overdue=true&status=open` returns only overdue open tickets, `?overdue=true&status=resolved` has no matches, and `?overdue=true&priority=urgent` returns only overdue urgent tickets. A ticket that fails the overdue check can never appear even if both other filters are supplied.
Source: implied: U-3 and the list filters in docs/api.md
Open: The requester decides how `status` and `priority` combine with each other when both accompany `overdue=true`. The API docs promise intersection for the existing filters, while 1.4.0 actually returns their union.

### C-15: Omitting `overdue` leaves the ordinary listing's filter behavior intact
Observable: With the flag on or off, ordinary listings include matches of any status or due date unless excluded by the existing filters. In 1.4.0, `?status=open&priority=urgent` includes tickets matching either filter, including an open low ticket and an in-progress urgent ticket.
Source: existing: src/tickets/query.js
Open: The requester decides which supplied `overdue` forms besides a single `true` should be accepted, ignored, or rejected when the feature is on, including `false`, empty or malformed values, and repeated parameters. Any form rejected as invalid uses the existing HTTP 400 `invalid` envelope.

### C-16: The overdue listing retains numeric ticket-ID order
Observable: Matching tickets appear in ascending ID number, so `T-9999` precedes `T-10000` even if the latter has an earlier deadline.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-17: The overdue listing retains the existing page-size rule for matching tickets
Observable: A page holds up to the requested number of matching tickets. Omitting `limit` gives 20. Whole-number limits 1 through 100 are accepted including both endpoints. A value outside that range, or a value such as `2.5` or an empty value, returns HTTP 400 `invalid`. Nonmatching tickets do not take up page slots.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-18: The overdue listing retains the existing cursor pagination contract
Observable: The response is `{ "items": [...], "next": ... }`. With the same filters, passing an issued `next` as `cursor` starts after the last ticket ID served. The final page has `next: null`, including when it is full. No matches gives `{"items":[],"next":null}`. A malformed cursor such as `abc` returns HTTP 400 `invalid`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-19: Preparation assigns missing deadlines to tickets in a 1.4.0 production data file
Observable: A valid existing file can be prepared for the new release. A saved high-priority ticket with `created` equal to `2025-09-01T08:15:00.000Z` receives `2025-09-02T08:15:00.000Z` under the default schedule, even if its `updated` time differs. Preparation uses each ticket's stored priority and the effective hours when the missing deadline is assigned. This includes tickets in all four statuses.
Source: request

### C-20: Production exposes due times only after the data file holds the required deadlines
Observable: An operator can take an existing production file from no saved deadlines to saved deadlines with no deadline visible before the file is ready and `DUE_TIMES=on` is in effect. At the first enabled response for an existing ticket, the deadline is already recoverable from the saved data. Successful ticket creations after cutover likewise have saved deadlines when the API returns them.
Source: request
Open: The requester decides how operators initiate preparation and confirm readiness, including whether setting `DUE_TIMES=on` on an unprepared file waits for preparation or requires a prior operation. The requester also decides whether feature-on operation without a configured `DATA_FILE` is supported outside production.

### C-21: The new release preserves an assigned deadline through subsequent saves of the data file
Observable: After a deadline is saved, a ticket edit, an outbox delivery that saves the file, or a shutdown while the feature is off leaves that deadline available after the new release restarts with the feature on. Repeating preparation on a file that already holds deadlines preserves those deadlines.
Source: implied: the request says tickets keep their due times from first assignment

### C-22: Preparing deadlines preserves each ticket's existing record
Observable: Before and after preparation, the data file contains the same ticket IDs and their same titles, priorities, requesters, statuses, creation times, and update times. The next created ticket continues the saved numbering sequence.
Source: existing: docs/decisions/0008-json-data-file.md

### C-23: Preparing deadlines preserves the existing append-only ticket history
Observable: Previously recorded entries returned by `GET /tickets/:id/audit` retain their original sequence numbers, actor, timestamp, action, and changes. A ticket creation, edit, or transition keeps its existing audit record for the ordinary ticket fields.
Source: existing: docs/decisions/0007-append-only-audit-log.md
Open: The requester decides whether first assignment of `due` should appear in enabled audit output, including in the creation entry or as a new entry for a backfilled ticket.

### C-24: Deadline preparation preserves the existing notification workflow
Observable: With `WORKER_INTERVAL_MS=0`, preparing deadlines leaves the existing pending, sent, and dead outbox entries intact and queues no notification. Creating or resolving a ticket still enqueues its existing requester notification, subject to the existing pending-key deduplication.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-25: A save made while preparing or serving deadlines leaves a whole production data file
Observable: If a save is interrupted, the retained file represents either the state before that save or the complete state after it, including tickets, audit history, and outbox. The preparation operation leaves already committed ticket changes in place.
Source: existing: docs/decisions/0008-json-data-file.md

### C-26: The operator can retry incomplete preparation
Observable: After an interrupted preparation or a failed write, the operator can address the cause and retry against the intact file. Tickets that still lack deadlines receive them, and deadlines committed before the interruption retain their values.
Source: implied: U-4 and the request's one-time assignment rule

### C-27: The existing invalid-data-file startup behavior still applies
Observable: A file with an existing invalid record, such as a ticket whose priority is `critical`, is refused at startup with a diagnostic identifying the file and record. The service exits with status 2 before listening.
Source: existing: docs/operations.md
Open: The requester decides how operators should recover if an already stored deadline is corrupt, as distinct from a legacy ticket whose deadline is absent.

### C-28: Release 1.4.0 can serve every ticket from the production file written by the new release
Observable: After the new release prepares old tickets and saves new ones, stop it and start unmodified 1.4.0 on the same file. The file remains readable under 1.4.0's version-1 rules. Paging through its ordinary listing shows all saved ticket IDs, and looking up any one of them returns the saved ticket through the 1.4.0 API.
Source: request
Open: The requester decides whether re-upgrading after 1.4.0 has itself rewritten the file must recover the original deadlines. The 1.4.0 writer keeps only the fields it knows.

### C-29: The operator CLI can read tickets from files with saved deadlines
Observable: With `DATA_FILE` or `--data FILE`, `list` still returns the matching tickets for its existing options and `show ID` still presents the named ticket and its history. Valid files written by 1.4.0 remain usable by both commands.
Source: existing: README.md
Open: The requester decides whether the human-readable `list` table or `show` must display the deadline, and whether the production visibility flag should govern any such display.

### C-30: The operator CLI remains read-only
Observable: Running `list` or `show` leaves the selected data file unchanged, whether or not it contains saved deadlines.
Source: existing: docs/operations.md

### C-31: `list --raw` retains its documented tab-separated ticket record
Observable: Each matching ticket occupies one line with the four columns id, status, priority, and title in that order, including when deadlines are present.
Source: existing: README.md

### C-32: The weekly report still counts tickets from the saved file
Observable: For the same tickets, `npm run report:weekly` returns the same totals by status and priority before and after deadline preparation. Its `--json` output still supplies `total`, `byStatus`, and `byPriority`.
Source: existing: scripts/weekly-report.js

### C-33: The existing tests pass unchanged
Observable: Run `npm test` and observe the original tests pass with their checked-in files unchanged.
Source: request

### C-34: `npm test` runs new due-time coverage alongside the existing suite
Observable: The added `node:test` tests reside under `test/` and run with the existing tests in a single `npm test` invocation. Their assertions cover the new required behavior regardless of how a build answers the open points.
Source: request
