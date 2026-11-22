# Help desk tickets specification

## Requirements

### R-1 Requester wait lifecycle

Basis: November 21, 2026 request for reminders on tickets waiting on their requester, and docs/api.md lifecycle. Existing tickets and transitions are preserved. A ticket in progress may enter `waiting_on_requester`; it may then resume in progress or resolve. Waiting is active and listable via the existing status filter.

- A1, local HTTP: Create T-0001, move it to in_progress, then waiting_on_requester. Both moves return 200. The wait appears in a status-filtered list, and audit records the transition and actor. A direct open-to-wait move returns 409. Resume or resolve from the waiting state returns 200. Confirm via API tests.

### R-2 Timed requester reminder

Basis: November 21, 2026 request and notification conventions in decision 6. Assumed policy: one reminder per continuous wait at or after 72 elapsed hours by default. A positive whole-number `WAITING_REMINDER_MS` overrides the delay. When the worker is off, it performs no scheduled work.

- A1, local HTTP and file notifier: Enter waiting at 08:00:00 UTC and run the worker one millisecond before the configured delay, then at the delay. Only the latter produces one reminder addressed to the ticket requester. The rendered message identifies the ticket and requests a reply. A normal edit during the wait leaves its start unchanged. Other ticket states send no reminder. Confirm via a clock-driven service check.
- A2, data file and worker: After a successful reminder, repeat ticks and reopen the persisted service. No second event for that wait appears. After exit and reentry, the next wait can send once. A pending failed attempt follows existing backoff while waiting and becomes canceled when the ticket leaves. A canceled reminder never sends after reentry. Confirm via worker and persisted service checks.
- State: the single store owns tickets, lifecycle history and outbox in the existing file. The requester receives the existing notification fields. Operators can see canceled reminders in the existing outbox report. Reminder retries preserve event identity for relay deduplication. Open limit: production relay acceptance beyond the documented JSONL interface is unobserved.

## Non-functional requirements

- Reliability: load version-1 legacy data and preserve request/response contracts other than the new status and operator outbox state. Verify baseline suite and restart test.
- Scheduling: use the configured worker interval and avoid writing state on idle ticks. Verify at the threshold and after repeated ticks with an injected clock or persistence spy.
- Privacy and observability: deliver to the stored requester, reuse existing file and operator visibility, and avoid expanding access. Verify with synthetic test data.
- No UI or new remote service is affected.

## Retired

None.
