# Acceptance test report

## Preserved behaviour

- `src/app.js` — `GET /health` answered 200 JSON with `{"status":"ok"}` — `C-43 readiness, route matching, JSON errors and opt-in request logging are preserved`.
- `src/app.js` — An unknown path answered 404 `not_found` with the method and path in the message — `C-43 readiness, route matching, JSON errors and opt-in request logging are preserved`.
- `src/app.js` — An unsupported method on a known path answered 404 `not_found` and listed the supported methods — `C-43 readiness, route matching, JSON errors and opt-in request logging are preserved`.
- `src/app.js` — `LOG_REQUESTS=1` produced a standard-error line with method, path, status and duration for each request — `C-43 readiness, route matching, JSON errors and opt-in request logging are preserved`.
- `src/app.js` — The default omitted per-request logging — `C-43 readiness, route matching, JSON errors and opt-in request logging are preserved`.
- `src/app.js` — `POST /tickets` answered 201 JSON with the newly opened ticket and its assigned ID — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/app.js` — `GET /tickets/:id` answered 200 JSON for a known ID and 404 `not_found` with the ID in the message for a missing ticket — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/app.js` — The router decoded a percent-encoded ticket ID and accepted a trailing slash — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/app.js` — `GET /tickets/:id/audit` answered 200 JSON with `items` and returned 404 `not_found` for a missing ticket — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/app.js` — `MAX_BODY_BYTES` applied to existing JSON writes and accepted a body at the configured byte ceiling — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/app.js` — Malformed existing write bodies and an overlong `X-Actor` answered 400 `invalid` — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/app.js` — `PATCH /tickets/:id` answered 200 with the edited ticket, 404 for a missing ticket, and 409 for a closed ticket — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/app.js` — `POST /tickets/:id/transition` answered 200 with the transitioned ticket, 404 for a missing ticket, and 409 for a disallowed move — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/app.js` — `GET /tickets` answered 200 with `items` and `next` and returned 400 `invalid` for bad supported query values — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/app.js` — `GET /admin/outbox` answered 200 JSON and exposed the `pending`, `sent` and `dead` groups — `C-43 requester messages keep their original wording and the outbox preserves the relay fields`.
- `src/format.js` — The human `list` table displayed each row’s ID, status, priority, requester, minute-precision updated time and title — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — The human listing printed `no tickets` for an empty result and the raw empty result emitted zero bytes — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — `show ID` printed the ID and title plus status, priority, requester, created and updated — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — The `show` history gave the time, actor, action and description of field changes — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — `show` honored the `DATA_FILE` setting and a missing ID exited 1 with the not-found diagnostic — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — Missing show arguments and unusable data exited 2 with a usage or data diagnostic — `C-43 CLI show, empty list, file selection and exit behavior remain available`.
- `src/format.js` — The weekly report’s raw-list input had `id` in tab-separated column 1 — `C-41 raw fields keep positions 1 through 4 and the weekly report counts each ticket once`.
- `src/format.js` — The weekly report’s raw-list input had `status` in tab-separated column 2 — `C-41 raw fields keep positions 1 through 4 and the weekly report counts each ticket once`.
- `src/format.js` — The weekly report’s raw-list input had `priority` in tab-separated column 3 — `C-41 raw fields keep positions 1 through 4 and the weekly report counts each ticket once`.
- `src/format.js` — The weekly report’s raw-list input had `title` in tab-separated column 4 — `C-41 raw fields keep positions 1 through 4 and the weekly report counts each ticket once`.
- `src/format.js` — `npm run report:weekly -- --json` counted each row once by status and priority — `C-41 raw fields keep positions 1 through 4 and the weekly report counts each ticket once`.
- `src/persistence.js` — Unset or empty `DATA_FILE` meant in-memory state and a named missing file was created on the first save — `C-43 DATA_FILE is optional and an absent named file is created on a successful save`.
- `src/persistence.js` — `version` stayed 1 — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `savedAt` recorded the snapshot time as an ISO UTC timestamp — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `nextNumber` resumed at the saved counter so a ticket ID was never reused — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].id` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].title` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].priority` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].requester` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].status` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].created` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `tickets[].updated` survived a save and reload — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].seq` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].ticket` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].action` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].actor` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].at` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `audit[].changes` survived a save and reload with the prior history — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.nextId` resumed at the saved counter so relay IDs were never reused — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].id` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].key` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].type` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].to` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].ticket` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].data` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].status` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].attempts` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].created` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].nextAttemptAt` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].lastError` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — `outbox.events[].sentAt` survived a save and reload for existing notices — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/persistence.js` — An unusable snapshot failed startup and named the file and the invalid record or setting — `C-43 malformed existing data is refused with the affected file and record identified`.
- `src/persistence.js` — Malformed JSON, an incompatible version, duplicate IDs and ticket-counter reuse were diagnosed — `C-43 malformed existing data is refused with the affected file and record identified`.
- `src/persistence.js` — Invalid existing ticket fields, broken audit numbering or deltas, and invalid outbox state were diagnosed — `C-43 malformed existing data is refused with the affected file and record identified`.
- `src/persistence.js` — Old version 1 tickets, audit entries and pending outbox records were readable — `C-30 legacy version 1 tickets of every status look unassigned while history and outbox stay readable`.
- `src/persistence.js` — CLI readers could inspect a snapshot without writing it — `C-42 listing current and legacy data files leaves their bytes unchanged`.
- `src/store.js` — A newly created ticket had a sequential ID, open status, requested fields and matching created and updated times — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/store.js` — A creation audit entry recorded field deltas from null for title, priority, requester and status — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/store.js` — A ticket lookup or history lookup failed with not-found if that ID was absent — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/store.js` — An edit applied normalized title and requested priority, preserved creation time, and recorded who changed what and when — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — Editing to the current values left the ticket timestamp and audit and outbox records intact — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — Closed tickets refused edits with an operator-readable conflict message — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — Each allowed transition updated status and added a status-only delta and actor to the audit — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — Invalid lifecycle transitions gave a conflict and named a permitted next status where applicable — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — Audit consumers saw chronological entries for one ticket with sequence numbers from the global log — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.
- `src/store.js` — The API listed ticket IDs in numeric order and could continue a filtered list through an opaque cursor — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/store.js` — CLI list callers got the complete result across internal pages — `C-43 CLI still drains the complete list past a 100-item store page`.
- `src/store.js` — The requester received distinct ticket-created and ticket-resolved notifications with the ticket ID and title data — `C-43 requester messages keep their original wording and the outbox preserves the relay fields`.
- `src/store.js` — The store recorded delivery attempts and exposed sent notice identity, timestamps and cleared retry fields — `C-43 requester messages keep their original wording and the outbox preserves the relay fields`.
- `src/store.js` — A second resolution for a ticket with an already pending resolution notice reused the existing pending record — `C-43 the same pending resolution still deduplicates by its existing key`.
- `src/store.js` — Creation, audit, event and counters saved together into the existing version 1 snapshot — `C-43 saved version 1 records still preserve all existing fields and ticket and event counters`.
- `src/templates.js` — The creation relay subject was `[ID] We received your request` and the body named the title and ID and said the help desk would be in touch — `C-43 requester messages keep their original wording and the outbox preserves the relay fields`.
- `src/templates.js` — The resolution relay subject was `[ID] Resolved` and the body named the title and ID and said the requester could reply within 7 days — `C-43 requester messages keep their original wording and the outbox preserves the relay fields`.
- `src/templates.js` — An event with no template produced a delivery error in the existing notifier suite — `C-43 npm test passes all unchanged pre-existing tests`.
- `src/tickets/query.js` — `status` selected that lifecycle status and an unknown status returned 400 — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — `priority` selected that priority and an unknown priority returned 400 — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — An omitted page limit yielded 20 items and valid limits changed the page size — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — A limit outside 1–100 or a non-integer limit returned 400 — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — `cursor` resumed after the last result and a malformed cursor returned 400 — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — Unknown query keys, including the retired `offset`, were ignored — `C-43 unassigned-independent listing preserves the old cursor, single filters and invalid query behavior`.
- `src/tickets/query.js` — The CLI supported `list --status` and `list --priority` to restrict displayed rows — `C-40 the human list identifies each owner or unassigned ticket and applies its existing filters`.
- `src/tickets/validate.js` — Creation accepted title and requester plus optional priority, with ownership outside the create schema — `C-16 create still accepts title, requester and optional priority and refuses assignee`.
- `src/tickets/validate.js` — Editing accepted only title or priority, separately or together, with ownership outside the patch schema — `C-17 PATCH still accepts title and priority singly or together and refuses assignee`.
- `src/tickets/validate.js` — Create trimmed title and requester and defaulted missing priority to normal — `C-43 creation and retrieval preserve fields, normalization, numbering and creation audit`.
- `src/tickets/validate.js` — Create and edit title validation required single-line nonempty text through 200 characters — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/tickets/validate.js` — Create requester validation required single-line nonempty text through 64 characters — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/tickets/validate.js` — Existing priority options rejected an unrecognized value — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/tickets/validate.js` — Unknown or missing required fields and empty patches were rejected with 400 `invalid` — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/tickets/validate.js` — Transition accepted only its `to` field and rejected an unrecognized status or extra field — `C-43 the existing create, edit and transition validators preserve their input rules`.
- `src/tickets/validate.js` — PATCH trimmed a title before applying its delta and accepted an existing priority value — `C-43 PATCH and lifecycle preserve statuses, field deltas, actor, no-op, and conflict messages`.

## Failing now

- **C-6** — PUT treats `" Dana "` as a repeat of `"Dana"` but an assignee filter using the same padded spelling omits the ticket.
- **C-34** — Startup accepts a version 1 ticket with a saved assignee consisting of 65 plain letters.
- **C-40** — The human CLI displays the same ownership marker for a ticket owned by the admissible name `-` and a ticket with null ownership.
- **C-44** — `npm test` discovers and passes new API assignment cases, but executes no new CLI visibility exercise. U-6 fails at that step too.
- **C-45** — The PUT returns 500, then the running service exposes the new assignee, update time, audit entry and pending notice. A later save publishes that state and a restart exposes it, so retrying performs no new change.

## Discoveries

- Failed saves on existing ticket edits should also leave running and saved state at the last successful change | Observable: prevent replacement of the data file, issue a PATCH, then read the ticket and history | Why: the PATCH returned 500 and the immediate GET showed the rejected title. C-45 covers the assignment PUT.

## Verification

All 51 manifest commands ran and printed their item IDs. Forty-five passed. The longest took about 17 seconds.

The default-port check observes the requested bind and substitutes an ephemeral port. The interruption checks pause the child at the documented file replacement boundary and terminate it by PID. The npm suite checks use execution coverage and source inspection to identify the new test cases.
