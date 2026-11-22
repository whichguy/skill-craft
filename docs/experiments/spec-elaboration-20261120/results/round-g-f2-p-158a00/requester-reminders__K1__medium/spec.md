# Help desk ticket service: living spec

Existing behaviour (tickets, lifecycle, audit log, outbox notifications, data file, CLI, weekly report) is described by README.md, docs/api.md, docs/operations.md and decisions 0001-0008, and is preserved unless a requirement below says otherwise. This spec holds the requirements added on top of it.

## Requirements

### R-1 Reminder when a ticket waits on its requester too long
Basis: the request "Remind requesters when a ticket has been waiting on them for too long." (2026-11-21); the resolved notification's "Reply within 7 days to reopen it" (src/templates.js) shows `resolved` is the only state in which the requester must act (src/tickets/states.js). Assumption A1, not a user statement.

A ticket is *waiting on its requester* while its status is `resolved`. It has waited *too long* when the clock's time is at least REMIND_AFTER_HOURS hours after the time it last became `resolved` (the `at` of its latest transition to resolved). When that holds and the requester has not yet been reminded since that transition, the service enqueues one notification of type `ticket.reminder` for the requester, through the outbox, from a job of the background worker.

Preserved: created and resolved notifications, the lifecycle table, `updated` semantics. Changed: none of the existing behaviour. Pending: implementation and tests.

Acceptance (clock = manualClock starting 2025-09-01T08:00:00.000Z, REMIND_AFTER_HOURS=72, worker off, the job run by `worker.tick()` or the job's `run()`):
- A-1.1 positive: ticket T-0001 (requester maria@example.com, title "Printer on the 4th floor jams") created, moved to in_progress and resolved at 08:00 on 2025-09-01. Advance 72 hours, run the job: exactly one new outbox event, type `ticket.reminder`, to maria@example.com, ticket T-0001, status pending. Confirmed by a store/service test reading `GET /admin/outbox` or `store.outboxReport()`.
- A-1.2 boundary: at 71 hours 59 minutes 59 seconds after the resolve, running the job enqueues nothing; at exactly 72 hours it enqueues the reminder. Confirmed by a test advancing the clock in two steps.
- A-1.3 failure/negative: tickets in `open`, `in_progress` or `closed` are never reminded, however old (confirmed by a test with one ticket in each state, 30 days after creation, job run, no `ticket.reminder`).
- A-1.4 negative: a resolved ticket whose title was updated 10 hours after the resolve is still reminded at 72 hours after the resolve, not 72 hours after the update (confirmed by a test).
- A-1.5 failure: T-0001 resolved at 08:00, reopened (`POST /tickets/T-0001/transition` `{"to":"open"}`, permitted: resolved -> open) 24 hours later and left open: 72 hours after the resolve the job enqueues nothing. If it is then moved to in_progress and resolved again (open -> in_progress -> resolved, each permitted by the lifecycle) at 2025-09-04T09:00, the 72 hours count from that later resolve: nothing at 2025-09-07T08:59:59, one reminder at 2025-09-07T09:00:00 (confirmed by a test).

### R-2 One reminder per waiting period, safe across runs and restarts
Basis: the same request; the outbox key frees once an event is sent (src/outbox.js), so "reminded already" must not depend on it. Assumption A3.

A requester is reminded at most once for each time the ticket became `resolved`. Running the job again, any number of times, adds no second reminder, including after the first reminder was sent, after the service restarted from its data file, and when the ticket is reopened and resolved again (that later resolve starts a new waiting period and may produce one new reminder).

Acceptance:
- A-2.1 positive: after A-1.1, run the job twice more and advance a further 30 days between runs: the outbox still holds exactly one `ticket.reminder` for T-0001. Confirmed by a test.
- A-2.2 positive: after the reminder is delivered (event status `sent`), run the job again: still one reminder in total. Confirmed by a worker test delivering through `deliverOutbox`.
- A-2.3 restart: save the state to a data file after the reminder, open a new store from the file, run the job: no second reminder. Confirmed by a persistence-level test; a data file written by the current version (without any reminder data) still loads, and its resolved tickets past the threshold are reminded once.
- A-2.4 positive: T-0001 reminded at 72 hours, then reopened, moved to in_progress and resolved again (the lifecycle allows each step), then 72 hours after that second resolve: exactly one further reminder, two in total, the second newer than the first. Confirmed by a test.

### R-3 The reminder is audited and worded
Basis: decision 7 (every change on record); decision 6 (templates, outbox); CONTRIBUTING "Changes go through the store".

Sending the reminder to the outbox is one store change: it appends an audit entry for the ticket with action `ticket.reminded`, actor `system`, `at` the time of the change, and enqueues the event, saved together. It does not change the ticket's status, title, priority or `updated`. The event's `data.title` is the ticket's title. The notifier renders it with a template for `ticket.reminder`: subject `[T-0001] Waiting for your reply`, body naming the ticket and its title and saying the ticket was resolved and that replying reopens it. Without that template the delivery would go dead, so the template is required.

Acceptance:
- A-3.1 positive: after A-1.1, `GET /tickets/T-0001/audit` (docs/api.md) answers items whose last entry has action `ticket.reminded` and actor `system`, and the ticket's `updated` is unchanged from the resolve time. Confirmed by an API-level test.
- A-3.2 positive: `render` of the reminder event for T-0001 "Printer on the 4th floor jams" yields subject exactly `[T-0001] Waiting for your reply` and a body containing `T-0001`, the title and the word `reopen`. Confirmed by a unit test in test/templates or notifier tests.
- A-3.3 positive: with a notifier delivering to a NOTIFY_FILE, the worker's deliver job sends the reminder and its JSON line has `type` `ticket.reminder`, `to` maria@example.com, `ticket` T-0001. Confirmed by a worker/notifier test.
- A-3.4 n/a failure: no new error response exists; no endpoint is added.

### R-4 Configurable and switchable, and only in the worker
Basis: CONTRIBUTING "Background work runs in the worker"; decision 6; README "Configuration". Assumption A2 for the default.

`REMIND_AFTER_HOURS` sets the threshold: whole hours, default 72, from 0 to 8760 (0 turns reminders off). An unusable value (`REMIND_AFTER_HOURS=soon`, `-1`, `9000`) stops the service at start with a message naming the variable (the existing ConfigError behaviour). The reminder runs only as a job of the worker, in order after the outbox job's registration, and never inside a request; `WORKER_INTERVAL_MS=0` stops it. The README configuration table and docs/operations.md describe it.

Acceptance:
- A-4.1 positive: `loadConfig({})` has the threshold 72; `loadConfig({REMIND_AFTER_HOURS:'24'})` has 24; `'0'` has 0. Confirmed by test/config.test.js.
- A-4.2 failure: `loadConfig({REMIND_AFTER_HOURS:'soon'})`, `'-1'` and `'9000'` throw ConfigError whose message contains `REMIND_AFTER_HOURS`. Confirmed by test/config.test.js.
- A-4.3 boundary: with the threshold 0, a resolved ticket 1 year old is not reminded (confirmed by a test).
- A-4.4 positive: with WORKER_INTERVAL_MS=0 a service created with a past-threshold resolved ticket enqueues no reminder until a job is run explicitly; a request such as `GET /tickets` or `PATCH` never creates one (confirmed by a service test).
- A-4.5 positive: a service with the worker on and a short interval, the clock advanced past the threshold, enqueues the reminder on a tick (confirmed by a worker test with the job list from `createService`).
- A-4.6 doc: README.md's table and docs/operations.md (including the first-start burst above) and docs/api.md's list of audit actions and notification types mention `REMIND_AFTER_HOURS`, `ticket.reminded` and `ticket.reminder`; confirmed by reading and by the release's CHANGELOG entry and version bump to 1.5.0.

### R-5 Existing behaviour is unchanged
Basis: README, CONTRIBUTING, docs/api.md.

The 117 tests that pass before this change keep passing. The data file format stays `version: 1` and an old file loads. `bin/tickets.js list --raw` columns and the weekly report are unchanged. No dependency is added.

Acceptance:
- A-5.1 `npm test` exits 0 with every earlier test still present and passing (confirmed by comparing the count: at least 117 passing, 0 failing).
- A-5.2 `package.json` has no `dependencies` key (confirmed by reading).

## Non-functional requirements
- Performance: the job's work is a scan of the tickets once per worker tick; it runs off the request path, so request latency does not change. Excluded as a numeric bound: the service holds a small in-memory data set and no bound is stated; no number is invented.
- Reliability: covered by R-2 (restart and at-least-once delivery; the relay drops a repeated line by `key` and `id`, decision 6).
- Security and privacy: the reminder goes only to the ticket's own requester and carries only ticket id and title, as the existing notifications do. No new data is exposed. No accessibility or interface requirement: there is no UI.
- Compatibility: R-5.

## Open gaps
- First-start burst: tickets already `resolved` for longer than the threshold when the feature is first deployed (nothing closes a resolved ticket automatically) are all reminded once, on the first worker ticks, so a backlog produces one burst of mail. Accepted by default (each requester is reminded once, R-2); an operator can set REMIND_AFTER_HOURS=0 first and close stale tickets, and docs/operations.md must say so (A-4.6). Owner: help desk team.
- Threshold policy (72 hours) is an assumption (A2); the help desk may want another value; it is configurable, so the default can change without a code change. Owner: help desk team.
- The external mail relay may not know `ticket.reminder` (A4); it reads `type` as data. Owner: operators of the relay; not verifiable here.
- "Reply within 7 days to reopen it" in the resolved notice is not enforced by the service and is untouched.

## Retired
(none)
