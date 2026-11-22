# Help desk ticket service specification

## Requirements

### R-1 Record a requester wait

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21) and docs/api.md, “Move a ticket along its lifecycle.” The service had no equivalent signal at 710aff7. Policy assumption: agents explicitly set and clear the wait using ordinary transitions.

- A transition request with `{"to":"waiting_for_requester"}` from `in_progress` returns 200 and a ticket with that status. From `waiting_for_requester`, `{"to":"in_progress"}` resumes work. Existing transitions stay valid and closed stays final. A recognized but disallowed move returns 409; an unrecognized or malformed status returns 400. Verify with HTTP and the full transition table.
- The wait is active and can be queried by its exact lower-case status. Entry and exit are ordinary audited transitions with the existing actor attribution, timestamp and before/after status. Title and priority edits remain allowed. Verify via GET filters, PATCH and GET audit. Existing agent access and actor policy apply; no new actor authentication or inbound reply integration is required.
- Version-1 files from earlier releases continue to load with their original lifecycle state. Verify with the existing persistence and compatibility suite.

### R-2 Remind the requester while the ticket remains waiting

Basis: same request, docs/operations.md “Notifications,” and ADR 6. Policy assumption: one reminder per uninterrupted wait after 72 elapsed hours, no recurring sends.

- For `T-0001` transitioned to waiting at 2026-01-05T12:00:00.000Z, the worker may deliver the reminder on its first tick at or after 2026-01-08T12:00:00.000Z. At one millisecond before it must not deliver. A title or priority edit during the wait leaves the deadline unchanged. Verify with an injected clock and the real JSONL notifier.
- The reminder goes to the ticket's stored requester and includes the ticket ID and a request to reply so work can continue. The normal outbox inspection exposes the pending and sent event. A restart or repeat tick leaves the same pending event or sent record; a new wait can send a new reminder. Verify via HTTP, file restart, worker tick and outbox response.
- Resuming work removes an unsent reminder, including one awaiting retry. When a delivery fails while the ticket remains waiting, existing retry/dead behavior applies and operators can inspect the error. File and process failures follow the established relay deduplication model by key and id. Verify with injected notifier failures and persisted state. Existing creation and resolution notices retain their behavior.
- The configured worker is the only sender; interval zero stops automatic dispatch. Verify with a disabled service and existing worker lifecycle tests. The service-side result is the JSONL handoff. Production relay and inbound reply processing are external.

## Non-functional requirements

- Reliability and compatibility (R-1 and R-2): keep ticket lifecycle and queued reminder consistent across ordinary restart, use the current data document and dependency-free Node runtime, and preserve the API error envelope. Verify with the saved fixture and HTTP regressions.
- Scheduling (R-2): enqueue once with the wait and dispatch through existing polling. The first worker tick at or after the deadline is eligible under normal operation. No separate timer, hosted dependency or added load target.
- Privacy and operability (R-2): use the existing requester channel and outbox visibility. Carry only the intended ticket and recipient data in the established payload. Existing operational retention and audit policy apply. Inspect case output and the notification template.
- Rendered UI and accessibility checks do not apply because the change ships an API workflow and plain-text notification.

## Retired

None.

## Questions settled

- Q1 Result. Valid transitions return a ticket, invalid ones return existing API errors, and pending or failed delivery is visible in the outbox (R-1, R-2).
- Q2 Authority. An agent using the existing transition endpoint can start or end a wait and its reminder; the existing worker delivers to the stored requester (R-1, R-2).
- Q3 Existing machinery. The ticket audit records each wait and the existing worker/outbox holds one reminder per wait; standard limits, retries and disablement apply (R-1, R-2).
- Q4 Hostile and odd input. Existing request limits, status validation, JSONL encoding and error envelope apply (R-1, R-2).
- Q5 Forms of a value. The API takes the documented lower-case status, stores UTC timestamps and measures 72 elapsed hours with server time (R-1, R-2).
