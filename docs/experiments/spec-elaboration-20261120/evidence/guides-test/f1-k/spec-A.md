# Help desk tickets specification

## Requirements

### R-1 Waiting on the requester

Basis: “Remind requesters when a ticket has been waiting on them for too long,” November 21, 2026. The existing lifecycle is documented under docs/api.md, “Move a ticket along its lifecycle.” Add `waiting_on_requester` as an active status. Allow `in_progress → waiting_on_requester`, and from waiting allow `in_progress` or `resolved`. Preserve all existing transitions and ordinary resolution notification. A repeat of the waiting transition is a conflict.

- R-1.a. Through HTTP, create T-0001, move open → in_progress → waiting_on_requester. Both transitions return 200 and the latter appends an attributed audit entry. A second move to waiting or a direct move to closed returns 409 and adds no audit entry. From waiting either resume in_progress or resolve. Closing still requires resolution.
- R-1.b. The ticket is selectable by the waiting status in the listing and CLI. A simultaneous priority filter applies the documented intersection. Weekly report JSON counts it under waiting_on_requester and retains the original status buckets. Version 1 data files created before this feature remain readable. Verify with API, CLI, report and restart tests.

### R-2 Requester reminder

Basis: same request. One reminder per continuous waiting period is the default policy. At the first enabled worker tick at or after 72 elapsed hours in `waiting_on_requester`, send a reminder through the existing outbox and notifier to the requester's stored address. `REQUESTER_REMINDER_AFTER_MS` may override the default with a positive whole number of milliseconds. The policy uses status entry rather than any subsequent ticket edit. The message includes ticket ID and title and asks the requester to reply with needed information.

- R-2.a. Set the delay to 1000 ms. Enter waiting at time T for T-0001 with requester requester@example.test, title VPN down. At T+999 ms the sink has zero reminder lines. At T+1000 it has one matching reminder line addressed to the requester, regardless of a title or priority edit during the wait. Subsequent ticks in the same period leave the count at one. A nonwaiting ticket never qualifies. Verify via createService, real worker tick and JSONL sink.
- R-2.b. Resume before the first deadline and observe no reminder for that period. Re-enter waiting and the clock starts again. Two eligible periods have distinct reminder keys. Status transitions at the same recorded time still identify distinct periods; exercise same-time transition identity with a controlled clock. Resolving before delivery also ends the waiting period. An already-sent message remains recorded. Verify through the service worker and outbox readback.
- R-2.c. With DATA_FILE enabled, reopening the service preserves wait entry and the prior reminder's identity. A failed delivery uses existing backoff and retry limits. Sent, exhausted or cancelled reminders do not generate a new event for the same wait. Leaving waiting cancels an outstanding reminder so that the worker cannot send it later, even after re-entry. The outbox exposes the cancelled records. Worker off stops scheduled work. Verify by forcing a local notifier append failure and restarting against the data file.
- R-2.d. An unset or empty threshold uses 259200000. Invalid input causes a startup configuration error naming the variable. Verify with loadConfig tests.

The service owns the status, audit log and outbox in its existing state. Existing caller access governs API reads and mutations. The requester receives only the existing notification fields and template content for their own ticket. Worker ticks and API calls use the process's synchronous store paths. The file replaces state atomically, and the relay's key/ID deduplication covers the existing crash window between delivery and attempt recording. Reply ingestion and remote relay operation are outside the implementation scope.

## Non-functional requirements

Use Node.js 22+, no additional dependencies and the single existing worker loop per CONTRIBUTING. When enabled and healthy, the first tick at or after expiry queues and attempts delivery. A failed queue write must leave the reminder eligible for a later retry and must prevent delivery from that failed write. Check with the injected clock, temporary data file and local transport. Preserve audit and outbox traceability, the ticket shape, the raw CLI column order, and existing retry semantics. The existing terminal report keeps readable status/count spacing for the longer status. Actual mail delivery is owned by the existing relay and is beyond local acceptance.

## Retired

None.
