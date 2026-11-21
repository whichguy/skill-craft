## Use cases

### U-1: A requester opens a ticket to learn its response deadline

Flow: With `DUE_TIMES=on`, the requester submits `POST /tickets` and sees `due` in the returned ticket. The defaults are 4 hours from creation for `urgent`, 24 for `high`, 72 for `normal` and 168 for `low`. An agent who later changes the priority still sees the original deadline.
Source: request

### U-2: An agent lists overdue tickets to see which unanswered tickets need attention

Flow: With due times enabled, the agent sends `GET /tickets?overdue=true` and pages through `open` and `in_progress` tickets whose deadlines have passed. Tickets whose deadlines have yet to pass, plus `resolved` and `closed` tickets, stay out of that list. Reopening an overdue ticket makes it eligible again.
Source: request

### U-3: A help-desk lead changes the promised response hours for future deadlines

Flow: The lead changes the settings for the relevant priorities without editing code and applies the settings. The next ticket assigned a deadline uses the configured hours for its priority. Tickets that already have deadlines keep them.
Source: request

### U-4: An operator prepares the production data file before enabling deadlines

Flow: The operator uses the new release's preparation procedure with the production `DATA_FILE` before enabling `DUE_TIMES=on`. Tickets already in the file acquire deadlines based on their own creation times and priorities. The operator verifies that preparation is complete before exposing the feature. Until then, normal API responses have their 1.4.0 behavior.
Source: request

### U-5: An operator rolls back to 1.4.0 to recover normal ticket service

Flow: The operator stops the new service and starts 1.4.0 with `npm start` on the configured `PORT`, pointing at the same `DATA_FILE`. The old release starts and the operator can page through all tickets from that file, including tickets created by the new release.
Source: request

### U-6: An operator reads saved tickets from the command line to inspect their state

Flow: The operator points `bin/tickets.js list` or `bin/tickets.js show ID` at the data file through `DATA_FILE` or `--data FILE`. The commands can read the file after deadline preparation, and running them leaves the file untouched.
Source: existing: README.md and docs/operations.md

### U-7: A support lead runs the weekly report to get counts by status and priority

Flow: The lead runs `npm run report:weekly` with `DATA_FILE` set, or runs the report script with `--data FILE` and `--json` for the dashboard. The report still reads the CLI's tab-separated ticket lines and produces the same counts for the same tickets.
Source: existing: README.md and docs/operations.md

### U-8: A maintainer runs the test suite to check deadlines alongside existing behavior

Flow: The maintainer runs `npm test`. The existing tests run as written, and the new `node:test` cases under `test/` run in the same invocation.
Source: request

## Clauses

### C-1: The service still starts through `npm start` on its configured port

Observable: On the supported Node.js runtime (22 or later), `npm start` serves `GET /health` with 200 and `{"status":"ok"}`. `PORT` accepts whole numbers from 0 through 65535 inclusive, with 0 selecting a free port and an unset or empty setting using 4180. An unusable value stops startup with a diagnostic naming `PORT`.
Source: existing: README.md, package.json, src/config.js and src/server.js

### C-2: Running the service requires no npm dependencies

Observable: With Node.js and npm available, a checkout without installed packages can start the service and use its ticket API.
Source: request

### C-3: The HTTP API retains its 1.4.0 behavior when `DUE_TIMES` is anything other than `on`

Observable: With the variable unset, empty or set to any value other than `on`, the same requests on equivalent ticket state give the 1.4.0 statuses and response bodies, even if deadlines have been stored. Ticket responses omit `due`, and an `overdue` query parameter is ignored as it was in 1.4.0, whatever its value.
Source: request

### C-4: A new ticket's deadline is calculated from its creation time using its priority's response hours

Observable: With due times enabled, creating a ticket returns 201 with `due` equal to the returned `created` plus the effective response hours at creation. With default settings and `created` equal to `2025-09-01T08:15:00.000Z`, `urgent` is due `2025-09-01T12:15:00.000Z` (4 hours), `high` at `2025-09-02T08:15:00.000Z` (24), `normal` at `2025-09-04T08:15:00.000Z` (72) and `low` at `2025-09-08T08:15:00.000Z` (168). Omitting priority uses `normal`. Creation works both with `DATA_FILE` and in memory.
Source: request

### C-5: The help desk can configure the response hours for each priority without editing code

Observable: Applying supported environment settings for `urgent`, `high`, `normal` and `low` changes the hours used for subsequent deadline assignments. Where settings are unset or empty, the defaults are 4, 24, 72 and 168 hours respectively.
Source: request
Open: The help-desk owner decides the supported duration range and precision, including whether zero or fractional hours are accepted, subject to the timestamp limits.

### C-6: An unusable response-hours setting is diagnosed when starting with that setting in use

Observable: Starting the service with an unusable response-hours setting that it needs for deadline assignment fails with a diagnostic naming the setting, consistent with the existing startup configuration errors.
Source: existing: README.md and src/config.js

### C-7: An assigned `due` uses the API's UTC timestamp convention

Observable: `due` is an ISO 8601 UTC timestamp with millisecond precision, for example `2025-09-01T12:15:00.000Z`. The service's date range runs from `-271821-04-20T00:00:00.000Z` to `+275760-09-13T00:00:00.000Z`, inclusive (±8,640,000,000,000,000 milliseconds from the Unix epoch). A result outside that range cannot be served as a valid assigned deadline.
Source: existing: docs/api.md and the Node.js date range verified with a runtime probe
Open: The help-desk owner decides how an operator should handle an otherwise valid legacy ticket whose calculated deadline falls outside the representable range.

### C-8: Every HTTP ticket representation includes its assigned `due` when due times are enabled

Observable: The ticket returned by create, get, patch or transition, or as an item in any ticket listing, shows the same stored `due` for that ticket. This includes tickets in all four states, `open`, `in_progress`, `resolved` and `closed`.
Source: request

### C-9: Clients cannot supply the server-assigned deadline in ticket request bodies

Observable: Sending a `due` field in an otherwise valid create, patch or transition body gets HTTP 400 with `error.code` equal to `invalid`, just like other fields outside the endpoint's input.
Source: existing: docs/api.md and src/tickets/validate.js

### C-10: An assigned deadline stays fixed for that ticket

Observable: After a change to the configured hours, a priority patch, a title patch or an allowed status transition, including reopening, the ticket still has its original `due` whenever displayed. For example, an urgent ticket assigned a four-hour deadline keeps that deadline after a change to `low` or to the configured urgent hours.
Source: request

### C-11: The new release retains assigned deadlines across data-file saves

Observable: A successful create with due times enabled and `DATA_FILE` set is readable after restarting, even if the previous process stopped before a graceful shutdown. Ticket edits, outbox saves and shutdown saves retain assigned deadlines. Restarting the new release with due times disabled, saving further changes, and re-enabling due times still reveals the same assigned deadlines.
Source: implied: the deadline is set once and tickets keep it from then on

### C-12: The enabled overdue listing matches exactly the active tickets whose deadlines have passed

Observable: In an enabled service, `GET /tickets?overdue=true` with no other filter selects only `open` and `in_progress` tickets whose `due` is earlier than the service's time for the request. A ticket due at that instant is excluded, and becomes eligible one millisecond later if still active. A past-due ticket leaves the matches when resolved and stays out when closed. Reopening a past-due resolved ticket returns it to the matches using its original deadline.
Source: request

### C-13: Omitting `overdue` keeps ordinary ticket listing selection

Observable: With due times enabled, a listing without `overdue` includes tickets according to the existing listing rules regardless of their deadlines. With no filters it lists tickets of all statuses and priorities. With both legacy filters, the shipped 1.4.0 listing accepts a match on either `status` or `priority`.
Source: existing: src/tickets/query.js
Open: The API owner decides which enabled-mode `overdue` values other than the single `true` request are accepted, including `false`, empty values, case variants and repeated parameters, and how accepted values affect selection.

### C-14: The overdue condition remains mandatory when other ticket filters are supplied

Observable: With `overdue=true`, adding only `status=open` restricts the overdue matches to open tickets, adding only `priority=urgent` restricts them to urgent tickets, and adding only `status=resolved` or `status=closed` returns no matches. With both legacy filters supplied, no result can be resolved, closed or due at or after the time of the request.
Source: implied: U-2 and the existing listing filters in docs/api.md
Open: The API owner decides whether an overdue ticket must match either or both of `status` and `priority` when both are supplied with `overdue=true`. Release 1.4.0 implements either in src/tickets/query.js, while docs/api.md specifies both.

### C-15: Overdue listings use the existing cursor page contract

Observable: With due times enabled, overdue matches fill `items` in ascending numeric ticket ID order, including `T-9999` before `T-10000`. The page limit defaults to 20 and accepts whole numbers 1 through 100 inclusive. `next` is an opaque cursor if further matching tickets remain. Passing it as `cursor` with the same filters starts after the preceding page's last ID, even if that ticket stops matching. The last page has `next: null`. With no matches the response is `{"items":[],"next":null}`.
Source: existing: docs/api.md and docs/decisions/0005-cursor-pagination.md

### C-16: Errors on the affected HTTP routes retain the existing error contract

Observable: Errors have a JSON `error` object with a `code` and a human-readable `message`. An invalid list filter, limit or cursor returns 400 `invalid`, a missing ticket returns 404 `not_found`, a well-formed change the ticket's lifecycle disallows returns 409 `conflict`, and an unexpected service failure returns 500 `internal` with a generic message.
Source: existing: docs/api.md and docs/decisions/0004-error-envelope.md

### C-17: Every previously saved ticket without a deadline gets one based on its own creation time and priority

Observable: Given a valid 1.4.0 data file, preparation fills in the missing deadlines for `open`, `in_progress`, `resolved` and `closed` tickets. The calculation uses each ticket's own `created` plus the configured response hours for the priority used in its assignment. For example, a ticket created at `2025-09-01T08:15:00.000Z` whose priority has always been `high` gets `2025-09-02T08:15:00.000Z` with default hours, even if it is prepared months later.
Source: request
Open: For an older ticket whose priority changed before its first deadline is assigned, the help-desk owner decides whether to use the priority saved on the ticket at assignment or its original priority from history.

### C-18: Operators can complete deadline preparation before turning on the feature

Observable: With `DUE_TIMES` unset or elsewhere than `on`, the operator can prepare the production data file and verify that all saved tickets have retained deadlines. The result holds when the file is reopened, including if the original file needs no assignments or contains a mix of assigned and unassigned tickets.
Source: implied: U-4 and the requirement to switch on in production only once the data file holds deadlines
Open: The operator and help-desk owner decide when tickets created while the feature is disabled receive their first deadline. The supported rollout procedure must account for them before exposing due times.

### C-19: Production exposes due times only after its data file contains the assigned deadlines

Observable: A service with `DUE_TIMES=on` and a prepared `DATA_FILE` shows the saved deadlines on startup. If the file contains tickets missing deadlines, the service does not expose deadline-bearing responses or an overdue listing until all those deadlines are durably assigned.
Source: request
Open: The operator decides how an attempted enabled start with an incomplete file is handled, for example by requiring preparation first or completing preparation before serving enabled requests.

### C-20: Deadline preparation can be retried without losing saved state

Observable: If preparation of a usable file is interrupted or a write fails, the file still opens as a complete snapshot with all the tickets present at the last successful save. After the underlying problem is resolved, the operator can retry preparation. Each still-missing deadline is assigned, and each already saved deadline is retained even if the retry uses different hours.
Source: implied: U-4 and the whole-file crash behavior in docs/decisions/0008-json-data-file.md

### C-21: An unusable saved record retains the existing data-file failure diagnostic

Observable: If the production file cannot be used because a record is invalid, the operator sees the file path, the record and the reason for refusal. For example, `tickets[3].priority` equal to `critical` still prevents startup.
Source: existing: docs/operations.md and src/persistence.js

### C-22: Deadline preparation preserves the original ticket data

Observable: For tickets matched by ID before and after preparation, `id`, `title`, `priority`, `requester`, `status`, `created` and `updated` are unchanged by preparation alone. The next ticket created still uses the saved sequence, so no ticket number is reused.
Source: implied: U-4 and the saved ticket identity rules in docs/decisions/0002-prefixed-sequential-ids.md

### C-23: Existing ticket history stays intact when due times are assigned

Observable: After preparation or normal ticket activity in the new release, previously recorded entries are still returned by `GET /tickets/:id/audit` with their original sequence numbers, order, actor, time, action and changes. Ordinary edits and transitions still appear in the history as before.
Source: existing: docs/decisions/0007-append-only-audit-log.md
Open: The help desk's audit owner decides whether deadline assignment at creation or during preparation is itself shown in the enabled audit view. Any new audit detail must preserve existing entries and the disabled API responses.

### C-24: Deadline assignment and expiry leave the existing notification behavior in place

Observable: With the worker stopped, preparing saved deadlines or advancing time past a deadline leaves the existing pending, sent and dead outbox entries unchanged and adds no notification by itself. Creating and resolving a ticket still enqueue the existing `ticket.created` and `ticket.resolved` notifications respectively, with the existing deduplication for a key that is already pending.
Source: existing: docs/operations.md and docs/decisions/0006-notification-outbox.md

### C-25: Release 1.4.0 can start on the production data file written by the new release

Observable: Stop the new service and start the unmodified 1.4.0 release with `DATA_FILE` pointing to the same file, without converting it or restoring a backup. The old release reaches `GET /health` and can list every ticket by paging through `GET /tickets`. This includes assigned and newly created tickets after enablement. The file remains acceptable to the 1.4.0 reader, which requires version 1.
Source: request
Open: The operator and help-desk owner decide whether a later re-upgrade must recover the original deadlines after 1.4.0 itself rewrites the file. Its writer retains only the fields it knows, including on a normal shutdown.

### C-26: The human-readable CLI still reads the production data file without changing it

Observable: Using `DATA_FILE` or `--data FILE`, `bin/tickets.js list` displays saved tickets and accepts the existing status and priority options, while `bin/tickets.js show ID` displays the saved ticket and its history. Both commands work on files with assigned deadlines and leave the file unchanged.
Source: existing: README.md and docs/operations.md
Open: The help-desk owner decides whether `due` also appears in the human-readable `show` or `list` output and, if so, when the CLI displays it.

### C-27: The CLI's raw listing preserves its ticket columns

Observable: `bin/tickets.js list --raw` still emits one tab-separated line per matching ticket with `id`, `status`, `priority` and `title` as the four columns in that order, including when tickets have assigned deadlines. With no matches it emits no ticket lines.
Source: existing: README.md and src/format.js

### C-28: The weekly report continues to count tickets from the production data file

Observable: The report run as `npm run report:weekly` or with `scripts/weekly-report.js` still reports the same total and counts by status and priority for the same saved tickets after deadlines are assigned. The dashboard's `--json` output still provides `total`, `byStatus` and `byPriority`.
Source: existing: README.md and scripts/weekly-report.js

### C-29: `npm test` runs the new deadline behavior tests

Observable: New tests covering due-time behavior are present under `test/` and run via `node:test` in the normal `npm test` invocation.
Source: request

### C-30: The existing test suite passes as written

Observable: `npm test` also runs and passes the preexisting tests without edits to them.
Source: request

### C-31: A creation that fails because a deadline cannot be assigned leaves no new ticket or related records

Observable: With due times enabled, if a create request fails because its deadline cannot be assigned, later reads and restarts show no ticket, creation history entry or creation notification from that request. Tickets that already existed remain intact.
Source: implied: U-1 and C-7, since a failed deadline calculation must leave the requester and agents with a consistent ticket list
