# Help desk ticket service: living spec

Basis for R-1..R-5: the request "Remind requesters when a ticket has been waiting on them for too long." (2026-11-21), plus the defaults in RUN notes research.md (Q1-Q6 of intake). Existing behaviour (API shapes, lifecycle, created/resolved notifications, outbox retry/dead, data file version 1) is preserved.

## Requirements

### R-1 A resolved ticket that waits too long gets one reminder
A ticket is waiting on its requester while its status is `resolved` (src/tickets/states.js; the resolved notice asks the requester to reply to reopen, src/templates.js). Assumption: no new status. Pending: implementation and tests.
- Positive: a ticket resolved at T0 whose status is still `resolved` at T0 + REMINDER_AFTER_HOURS (default 72h) has exactly one pending `ticket.reminder` outbox event addressed to its requester after the next worker tick. Confirmed by a worker/store test with `manualClock`: create, move to in_progress and resolved, advance 72h, `worker.tick()`, read the outbox.
- Boundary: at T0 + 71h59m no reminder; at exactly T0 + 72h a reminder (threshold is inclusive). Confirmed by the same test.
- Failure: a ticket that is open, in_progress or closed is never reminded, however old. Confirmed by a test per status.
- Boundary (reply window): the resolved notice promises "Reply within 7 days to reopen it" (src/templates.js), so no reminder is sent once 7 days (168h) have passed since the resolve time; the reminder window is [REMINDER_AFTER_HOURS, 168h). This also means the first worker tick after this release sends nothing for tickets resolved long ago. Confirmed by tests: resolved at T0 and first tick at T0 + 167h gives one reminder; first tick at T0 + 168h and at T0 + 10 days gives none.
- Resolve time is the `at` of the ticket's last audit entry `ticket.transitioned` with `status.to === 'resolved'`, not `ticket.updated` (a resolved ticket can still be edited). Confirmed by a test that edits the title after 60h and still gets the reminder at 72h from resolve.

### R-2 One reminder per resolved period, across ticks and restarts
- Positive: further ticks after the reminder, even once it is sent, enqueue nothing more. Confirmed by a test that ticks, delivers (notifier), advances 24h, ticks again: still one event for that period.
- Positive: after a restart (state saved and reloaded through the persistence module) no second reminder is enqueued. Confirmed by a persistence round-trip test.
- Boundary: a ticket reopened (resolved to open) and resolved again starts a new period: reminded again 72h after the new resolve, not before. Confirmed by a test.
- Failure: a ticket reopened or closed before the threshold is not reminded. Confirmed by a test.

### R-3 The reminder's content and recipient
- Positive: the event type is `ticket.reminder`, `to` is the ticket's requester, `ticket` is its id, and the rendered message has subject `[<id>] Waiting on you` and a body naming the ticket title and saying it can be reopened by replying. Confirmed by a template test and a notifier test reading the NOTIFY_FILE line.
- Failure: delivery follows the outbox rules unchanged (retry with backoff, dead after 5). Confirmed by existing outbox tests plus one with a failing notifier.
- A reminder is not a ticket change: no audit entry, `updated` unchanged. Confirmed by a store test.

### R-4 Runs only in the background worker, configured by one setting
- Positive: the check is a job of the worker; no timer of its own and no request does it. Confirmed by a worker test with the job registered, and by a test that an API request enqueues no reminder.
- Positive: `REMINDER_AFTER_HOURS` sets the threshold (a number greater than 0 and less than 168, the reply window of R-1; default 72). Confirmed by a config test; README table updated.
- Failure: an unusable value (`abc`, `0`, `-1`, `168`, `500`) stops start with a message naming `REMINDER_AFTER_HOURS`. Confirmed by a config test.
- Boundary: `WORKER_INTERVAL_MS=0` turns reminders off with the rest of the background work. Confirmed by a test.

### R-5 Existing behaviour is preserved
- Created and resolved notifications, the lifecycle table, API responses, the audit log, the data file format (version 1; old files load) and the existing 117 tests are unchanged. Confirmed by `npm test` staying green and a test that loads a data file with no reminder events.
- Documentation: CHANGELOG section and version bump (1.5.0), README config row, docs/operations.md note, ADR 0009 for the reminder design (CONTRIBUTING.md). Confirmed by reading them.

## Non-functional requirements
- Compatibility: no new dependency (Node stdlib, CONTRIBUTING.md); verified by package.json unchanged.
- Performance: the job scans all tickets each tick; at current size acceptable, no numeric bound invented. Excluded with that reason.
- Security/accessibility/UI: excluded: no UI, no new input or endpoint, recipient is the existing requester field.
- Data: no new stored ticket field; the reminder lives in the outbox and persists with it. Invariant: at most one event per (ticket, resolve time) key, before and after restart (R-2).

## Open gaps
- Assumption: outbox events are never pruned (none found in src/outbox.js); owner: test-strategy, verified by the restart test in R-2.
- Assumption: threshold 72h, the 168h reply-window ceiling and the message wording are defaults, not user decisions.

## Retired
(none)
