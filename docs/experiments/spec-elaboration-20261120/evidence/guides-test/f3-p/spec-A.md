# Help desk tickets: living spec

Product: the IT help desk's ticket service (Node >= 22, no dependencies). Existing behaviour is documented in README.md, docs/api.md and docs/decisions/; this spec records the requirements added by shiploop runs. Baseline: commit dd15402, `npm test` 117 pass.

## Requirements

### R-1 Remind a requester when a resolved ticket has waited on them too long

Basis: request of 2026-11-21 "Remind requesters when a ticket has been waiting on them for too long." The lifecycle has no waiting-on-requester status, so by assumption (A1) a ticket waits on its requester while it is `resolved` (the resolved notice already says "Reply within 7 days to reopen it"), and "too long" is 7 days (A2). Evidence: src/tickets/states.js, src/templates.js, docs/shiploop/environment.md.

Behaviour: the worker, on each tick, finds every ticket that is `resolved`, whose latest resolve time (`at` of its latest audit entry with `changes.status.to = 'resolved'`; not `ticket.updated`) is at least 7 days (604800000 ms) before the clock's now, and that has no audit entry with action `ticket.reminded` later in the log (higher `seq`) than that resolve entry. Order is by `seq`, never by timestamp, because a stopped clock gives entries the same time. A resolved ticket with no resolve entry in the log (a hand-edited data file) is not reminded. For each, it enqueues one `ticket.reminder` notification to the ticket's `requester` and appends one audit entry `ticket.reminded`, actor `system`, empty `changes`, in the same store step (saved together). The audit entry shows in GET /tickets/:id/audit like any other.

Acceptance lines (confirmed by tests in test/ with `manualClock`, worker off, calling `worker.tick()` or the store method directly):
- R-1.1 Positive: ticket T-0001 created, moved open -> in_progress -> resolved (open -> resolved is not a legal transition) at 2025-09-01T08:00:00Z; clock advanced 7 days exactly; one job run yields exactly one pending outbox event `{type: 'ticket.reminder', to: <requester>, ticket: 'T-0001', key: 'ticket.reminder:T-0001'}` and one audit entry `ticket.reminded` with actor `system`. Observed in `store.outboxReport()` / GET /admin/outbox and `store.history`.
- R-1.2 Boundary: at 7 days minus 1 ms after resolve, no event and no audit entry.
- R-1.3 One reminder: running the job again (also after the reminder is delivered/sent, and at 30 days) enqueues nothing more and appends no second `ticket.reminded`.
- R-1.4 Only waiting tickets: at 30 days after creation, a ticket still `open`, a ticket `in_progress`, and a ticket resolved at day 0 and closed at day 1 each get no event and no `ticket.reminded` entry.
- R-1.5 Resolve time is the resolve, not the last edit: a PATCH of the title of a resolved ticket at day 6 does not delay the reminder; it is still due at day 7 after the resolve.
- R-1.6 Reopen: T-0001 resolved at day 0, reopened (resolved -> open) at day 3, taken in_progress and resolved again at day 4: no reminder at day 7 (3 days since the new resolve); one reminder at day 11, counted from the new resolve; none more after that, even though an earlier resolution exists.
- R-1.7 Restart: with a data file, a ticket reminded before a restart is not reminded again after reloading (the audit entry persists; no data-file format change, `VERSION` stays 1).
- R-1.8 Worker off: a service built with `WORKER_INTERVAL_MS=0` holding a ticket resolved 30 days ago: `worker.start()` returns false and the outbox stays empty (no timer, no side effect of a request or of a GET /admin/outbox); an explicit `worker.tick()` then enqueues exactly one reminder (so the job is wired, not absent).
- R-1.9 Delivery: the notifier renders `ticket.reminder` to subject exactly `[T-0001] Waiting for your reply` and body exactly `Ticket T-0001 "VPN drops every hour" has been waiting for your reply for 7 days since it was resolved. Reply to reopen it.` for a ticket titled `VPN drops every hour` reminded at exactly 7 days; the number is the whole days elapsed since the resolve (floor): a worker that first ticks at 10.5 days says 10; an event of this type is never dead for want of a template.
- R-1.10 Order and isolation: the job (named `remind-requesters`) is listed before `deliver-outbox` in `src/server.js`, and the enqueued event is due immediately, so at the 7-day tick one `worker.tick()` returns reports for both jobs and `deliver-outbox` reports `sent: 1`. A `remind-requesters` job that throws is logged by the Worker and `deliver-outbox` still runs (existing Worker behaviour; confirmed by a test with a failing job ahead of deliver-outbox).

Left out (bounds): no new ticket status, field, API endpoint or configuration variable; no reminder for open/in_progress tickets (waiting on the agent); no repeat reminders; no auto-close; no change to the created/resolved notifications.

Open gaps: A1 and A2 are product defaults chosen without a person; owner: the requester of this run; if changed (another status, another period), R-1 changes in place. Pending: implementation, tests, decision record 0009, CHANGELOG 1.5.0.

### R-2 Preserved behaviour

Basis: CONTRIBUTING.md and docs/api.md at dd15402. Every existing API response (a ticket's audit list gains `ticket.reminded` entries only), the lifecycle, `list --raw` column positions, the weekly report, the data file's version and readability of existing data files, and the `ticket.created` / `ticket.resolved` notifications are unchanged. Acceptance: the 117 baseline tests still pass unmodified (`npm test`, exit 0), plus the new ones.

## Non-functional requirements

- Dependencies: none added (`package.json` unchanged except the version); confirmed by diff.
- Conventions: through the store, notification through the outbox with a template, scheduled work as a worker job (CONTRIBUTING.md); confirmed by code review and R-1.8.
- Performance, security, accessibility, UI: excluded; the work has no interface and no stated bound.

## Retired

None.
