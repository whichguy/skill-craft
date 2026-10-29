# node-tickets (fixture, digest in cases.json): facts the `ticket-assignment` and `ticket-escalation` requests depend on

Hand-compiled from the fixture on 2026-10-28; never shown to a subject. The fixture is
`test/shiploop_e2e/fixtures/node-tickets`; the requests are the `ticket-assignment` prompt and its follow-on
`ticket-escalation` in `test/shiploop_e2e/cases.json`. Each latent fact (LA for the first request, LB for the follow-on) is
something the request depends on and does not name. The check IDs are the held-out checks that read it
(`test/shiploop_e2e/checks/ticket_assignment_accept.py`, `ticket_escalation_accept.py`); their calibration is in
`test/shiploop-e2e-brownfield-tickets.test.py`. A later analysis reads a run's knowledge home against these rows: did
discovery record the fact, did the spec or the plan keep it, and did the follow-on run inherit it or relearn it.

## Latent facts

| ID | Fact | Evidence (file, symbol) | Why it matters, and to which request | Checks |
|---|---|---|---|---|
| LA1 | Every error answers in one envelope, `{"error": {"code", "message"}}`, with `invalid` 400, `not_found` 404, `conflict` 409; a state that does not allow a change is a 409, never a 400. Handlers throw, `src/app.js` answers. | `docs/decisions/0004-error-envelope.md`; `src/errors.js` `toResponse`, `ConflictError`; `src/http.js` `sendError`; `CONTRIBUTING.md` "Every error through the envelope" | assignment: the new endpoint's 400 for a bad agent, 409 for a resolved or closed ticket and 404 for an unknown one | `assignee-validation`, `assign-state-and-missing` (and `ticket-lifecycle-unchanged` for the existing routes) |
| LA2 | Notifications are enqueued in the outbox as part of the store change and delivered later by the worker; handlers never call the notifier. A key deduplicates while pending, and `TicketStore.notify`'s default key is type and ticket, so a reassignment while the first notification waits needs a key of its own. A type with no template in `src/templates.js` goes dead after five attempts. `WORKER_INTERVAL_MS=0` keeps events pending. | `docs/decisions/0006-notification-outbox.md`; `src/store.js` `TicketStore.notify`; `src/outbox.js` `Outbox.enqueue`; `src/templates.js` `render`; `src/worker.js` `deliverOutbox`; `CONTRIBUTING.md` "Notifications only through the outbox" | assignment: "the agent ... is notified" must be an outbox event to that agent, delivered once | `assignee-notified` (and `notifications-unchanged`) |
| LA3 | Every change goes through a `TicketStore` method, which appends one audit entry with the `X-Actor` actor (`system` without one) and `changes: {field: {from, to}}`. A change that changes nothing adds no entry and leaves `updated`. | `docs/decisions/0007-append-only-audit-log.md`; `src/store.js` `TicketStore.apply`; `src/audit.js` `AuditLog.append`; `src/http.js` `actorOf`; `CONTRIBUTING.md` "Changes go through the store" | assignment: each assignment audited with before and after; "changes nothing" means no entry and no notification | `assign-audited`, `assign-same-agent-noop` |
| LA4 | Listings are cursor pages, `{items, next}`, `limit` 20 by default and at most 100; filtering happens before paging, so a page holds `limit` matches and `next` is null exactly when no match is left. | `docs/decisions/0005-cursor-pagination.md`; `src/pagination.js` `paginate`; `src/store.js` `TicketStore.list`; `src/tickets/query.js` `parseListQuery` | assignment: the `assignee` filter must page like the others | `assignee-filter-pages` (and `listing-unchanged`) |
| LA5 | Filters combine: a ticket is listed only when it matches every filter given. The base breaks this: `matchesFilters` uses `some`, so `?status=open&priority=urgent` lists every open ticket and every urgent one. Its tests try one filter at a time. | `docs/api.md` "List tickets"; `src/tickets/query.js` `matchesFilters`; `test/query.test.js`, `test/api.test.js` (single filters only) | assignment: "a ticket must match every filter given" needs the defect fixed; adding `assignee` to the same function inherits it | `filters-combine` |
| LA6 | `list --raw` prints tab-separated id, status, priority, title, and `scripts/weekly-report.js` reads them by position, so they must keep their positions; no test covers either. | `README.md` "Command line"; `src/format.js` `RAW_COLUMNS`, `rawLine`; `scripts/weekly-report.js` `count` | assignment: "the command-line listing shows each ticket's assignee" must not insert a column before title | `cli-raw-columns` (and `cli-shows-assignee` for the request's own sentence) |
| LA7 | The data file keeps only the fields the record functions name; a field added to a ticket and not to them is lost at the next restart. | `docs/decisions/0008-json-data-file.md`; `src/persistence.js` `ticketRecord`, `readTicket` | assignment: the assignee must survive a restart | `assignee-persists` (and `restart-keeps-state`) |
| LA8 | Files the previous version wrote must keep loading, and a field they lack takes its default; the base's tests pin the format at version 1. A ticket saved before the change must load as unassigned (null), not refused and not without the field. | `docs/decisions/0008-json-data-file.md` "A field older files do not have takes its default"; `src/persistence.js` `fromDocument`; `test/persistence.test.js` "a version this service does not read" | assignment: "Every ticket shows its assignee (null when unassigned)" for the tickets already in the data file | `old-data-loads`, `old-tickets-unassigned` |
| LB1 | As LA1, for the reassignment endpoint: 400 `invalid` for the same agent twice or a malformed body. | as LA1 | escalation: `from` and `to` "must be two different agents" | `reassign-validation` |
| LB2 | As LA2, and the worker is the service's one background loop: scheduled work is a job of `src/worker.js`, never a timer of its own and never a side effect of a request, and `WORKER_INTERVAL_MS=0` stops all of it. | `docs/decisions/0006-notification-outbox.md` (the last bullet of its decision); `CONTRIBUTING.md` "Background work runs in the worker"; `src/worker.js` `Worker`, `deliverOutbox`; `src/server.js` `createService` | escalation: "notified that the ticket was escalated" runs in the background, through the outbox; reassignment notifies "as for a single assignment" | `worker-off-is-quiet`, `escalation-notifies-oncall`, `reassign-notifies` |
| LB3 | As LA3, for each ticket a bulk reassignment moves. | as LA3 | escalation: one audit entry per moved ticket | `reassign-audited` |
| LB4 | As LA7: the data file is the only state that outlives a restart (`DATA_FILE`), and the outbox is in it. An escalation recorded only in memory is sent again after a restart. | `docs/decisions/0008-json-data-file.md`; `src/persistence.js` `toDocument`; `src/outbox.js` (events stay after they are sent) | escalation: "at most once, even across restarts of the service" | `escalation-at-most-once` |
| LB5 | What the first run had to learn (LA1-LA8 and the request's assignment) must still hold after the second run. | the first run's delivery | escalation: "Everything the service already does keeps working, assignment included" | `existing-api-kept`, `assignment-kept`, `assignment-listing-kept`, `assignment-notified-kept`, `assignment-persists-kept`, `cli-raw-columns-kept`; the retention checks of `ticket-escalation` in cases.json |

## The requests' own sentences

These are named by the requests; the table keeps them so every check has a row.

| Sentence | Checks |
|---|---|
| assignment: assign and unassign, open and in-progress only, every ticket shows its `assignee` | `assign-and-unassign`, `assign-state-and-missing` |
| assignment: an agent is a non-empty name of at most 64 characters | `assignee-validation` |
| assignment: assigning the agent it already has changes nothing | `assign-same-agent-noop` |
| assignment: `assignee=<agent>` and the empty `assignee=` | `assignee-filter` |
| assignment: the command-line listing shows each ticket's assignee | `cli-shows-assignee` |
| escalation: `POST /tickets/reassign` moves open and in-progress tickets and answers `{moved, ids}` in id order | `reassign-moves` |
| escalation: open, unassigned, urgent, older than `ESCALATE_AFTER_MINUTES` minutes; only with `ONCALL` | `escalation-notifies-oncall`, `escalation-rules` |

## Existing behaviour no request names

| Behaviour | Evidence | Checks |
|---|---|---|
| Create, read, change and the lifecycle (open, in_progress, resolved, closed; resolved reopens; closed is final; a resolved ticket can still change) | `docs/api.md`; `src/tickets/states.js` `TRANSITIONS`; `src/store.js` `TicketStore.update` (`isFinal`) | `ticket-lifecycle-unchanged`, `existing-api-kept` |
| Ticket ids `T-0001` and on, never reused, also after a restart | `docs/decisions/0002-prefixed-sequential-ids.md`; `src/tickets/ids.js`; `src/persistence.js` `fromDocument` | `restart-keeps-state`, `old-data-loads` |

## Decision records

The fixture's `docs/decisions/` holds eight records, an index and a template. A run's knowledge home should link the records the
touched flows rest on (design 4.4: indexed broadly, materialized narrowly), list the superseded one as superseded, and not take
the template for a decision.

| Record | Status | Decision | Touches |
|---|---|---|---|
| `0001-record-decisions.md` | Accepted | decisions are recorded in `docs/decisions/`, never edited once accepted, superseded by a new record | both: a new decision gets a record (design D4) |
| `0002-prefixed-sequential-ids.md` | Accepted | ids `T-` and a number padded to four digits, in order, never reused | neither directly; LA8 (next number kept) |
| `0003-offset-pagination.md` | Superseded by 5 | `offset` and `limit` with `total` | neither: a superseded record, not to be followed |
| `0004-error-envelope.md` | Accepted | one error envelope, four codes; a state conflict is 409 | LA1, LB1 |
| `0005-cursor-pagination.md` | Accepted | opaque cursors, `{items, next}`, limit 20 to 100, filter before paging | LA4 |
| `0006-notification-outbox.md` | Accepted | notifications through an outbox and a worker; the worker is the one background loop | LA2, LB2 |
| `0007-append-only-audit-log.md` | Accepted | every change audited with actor and before and after; no change, no entry | LA3, LB3 |
| `0008-json-data-file.md` | Accepted | the whole state in one JSON file; record functions name every field; older files keep loading | LA7, LA8, LB4 |
| `README.md` | (index) | the list of records and their status | none: the index |
| `template.md` | (template) | the shape of a record | none: a template, not a decision |
