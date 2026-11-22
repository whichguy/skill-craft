# Help desk tickets specification

## Requirements

### R-1 Requester-waiting lifecycle

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21). Adds an explicit agent-controlled waiting status. Preserves the lifecycle and errors under docs/api.md / Move a ticket along its lifecycle. Current UI coverage is through HTTP and operator tools.

- C-1: From `in_progress`, POST `/tickets/T-0001/transition` with `{"to":"waiting_on_requester"}` returns 200 and an audited status change at the current UTC time. The same route with `{"to":"in_progress"}` resumes work. From waiting, resume to `in_progress` before resolving. The existing `in_progress` → `resolved` → `closed` and `resolved` → `open` paths remain. From `open`, going directly to waiting is a 409. The existing active classification continues to describe `open` and `in_progress`. Verify HTTP responses and audit.
- C-2: GET `/tickets?status=waiting_on_requester` and the CLI status filter show waiting tickets. The weekly report counts them using the same status name. The ticket object and raw CLI column order are preserved. Verify against a waiting ticket written through the API and a persisted local data file.

### R-2 Timed reminder

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21). Default policy: 72 elapsed hours, configurable in positive whole milliseconds via `REQUESTER_REMINDER_DELAY_MS`, and one reminder per uninterrupted wait. docs/operations.md / Notifications and ADR 6 govern delivery and failure.

- C-3: The worker queues `ticket.requester_reminder` for the ticket's requester on the first running tick at or after the delay, measured from the entry transition. A title or priority edit does not reset it. Before the boundary and outside the waiting state there is no reminder. Verify through HTTP, a controlled clock, and the notifier's JSON line containing the ticket ID and a request to reply.
- C-4: A pending, sent, or dead reminder satisfies the one-reminder limit. Repeat ticks and a restart keep the same period identity. Leaving waiting cancels a pending retry. Re-entering establishes a fresh period even if status changes share a timestamp. Verify with failed notifier writes, restart, and multiple wait periods.
- C-5: With `WORKER_INTERVAL_MS=0`, the service neither schedules nor delivers automatically. Unset or empty delay uses the default. Invalid delay stops startup with the config setting named. Verify service worker state and config parsing.
- A reminder does not change ticket fields or create an audit entry. The ticket and transition audit are the wait authority. Sent and dead outbox entries are retained for operations. The persisted outbox is the durable record for retry and duplicate prevention. The notifier delivers at least once under crash recovery as in ADR 6.
- Agent records that a requester reply ended the wait by changing status. A requester reply channel is outside this service. Production relay observation remains outside local source delivery.

## Non-functional requirements

- Timing uses the UTC clock, with first healthy tick at or after the configured elapsed delay. Verify exact-boundary observations without waiting real hours.
- No additional process, production endpoint, dependency, or requester data transfer. Use the existing notifier recipient and template boundary. A version-1 data file from before this change opens normally. Check older fixtures and a restarted service.
- Scan work is bounded by ticket wait state and existing outbox processing. A tick with no new reminders does not rewrite the state file. Check through a save spy and code review.
- This change adds no user interface. The established HTTP and terminal formats apply. No external access or browser verification is required.

## Retired

None.
