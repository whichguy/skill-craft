# Help desk ticket service specification

## Requirements

### R-1 Explicit requester wait

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21), the lifecycle in docs/api.md and the append-only audit rule in decision 7. Add `waiting_on_requester` as an active status. The existing transition endpoint allows in_progress → waiting_on_requester → in_progress or resolved. Existing transitions remain valid, a known but disallowed move fails with 409, unknown statuses fail with 400, and closed stays final. Confirm through real HTTP transition and filter, and the lifecycle matrix.

- Current ticket status is visible by GET, list filter and CLI. A transition has one normal audit entry with the entry time and actor. The weekly report counts the new status, keeping raw column positions. Confirm through HTTP, audit JSON and CLI report against the saved file.

### R-2 Requester reminder after elapsed time

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21). Default policy is 72 elapsed hours and one reminder event per continuous wait. Each worker tick considers the current wait from its entry transition. A wait aged exactly the threshold qualifies. Title and priority edits do not reset the clock. Other statuses, including resolved during its reopen window, are ineligible. Verify with manual time through the server worker and real notifier JSONL boundary.

- Use the ticket's requester and identify the ticket and action needed in a dedicated message. Repeated ticks, including after successful delivery or terminal failure, do not create a second event for the same wait. A new wait has a new threshold and can produce its own event. Verify recipient, type, subject, reply instruction, and event counts across multiple ticks and re-entry.
- Reminder processing leaves the ticket updated timestamp and audit history as they were immediately before the tick. Verify through GET and audit responses.

### R-3 Durable delivery and cancellation

Basis: accepted decisions 6, 7 and 8 and the requester-reminder request on 2026-11-21. State belongs to the single TicketStore writer. Audit history and durable outbox events must let the worker recover wait timing and reminder identity over restart. Older version 1 files remain readable. The existing worker and notifier retry and keep sent/dead records. Exiting a wait removes only its still-pending reminder so a later retry cannot ask for a response after the wait has ended. Subsequent re-entry is independent. A scheduling save failure must leave no unpersisted reminder for delivery and a later tick can retry. Verify via restart, retry cancellation, save fault injection, and outbox observation.

- Local completion is a line written to the notifier's JSONL output. The existing relay contract deduplicates at-least-once deliveries by key and id under decision 6. Relay mailbox delivery is outside the local check. The outgoing recipient is the existing ticket requester, and the operator outbox uses its existing access surface and data shape.

### R-4 Operator override

Basis: README.md configuration conventions and decision 6. Set `REQUESTER_REMINDER_HOURS` to a nonnegative whole number of hours. Unset or empty selects 72. Zero disables new reminder scheduling, with previously queued events continuing on their existing delivery path. Malformed or out-of-range input fails startup config validation. `WORKER_INTERVAL_MS=0` stops scheduled work, including reminders and delivery. Verify config parsing and service worker behavior.

## Non-functional requirements

- Compatibility: retain existing API envelopes, ticket field shape, create and resolve notices, CLI raw positions, Node 22+ and standard-library-only runtime. Prior data loads as version 1. Check the unchanged suite contracts and a restart case.
- Operability: existing outbox state and worker diagnostics expose reminder outcomes. Tick work is proportional to current waits plus the existing outbox work, with no additional write on an idle scan. JSON file remains single-writer. Use review and a save-count fault test to confirm scheduling behavior.
- The existing terminal report uses plain text; the longer status label and its count remain separated and readable. Browser layout, browser accessibility and network service targets are outside this change.

## Retired

None.
