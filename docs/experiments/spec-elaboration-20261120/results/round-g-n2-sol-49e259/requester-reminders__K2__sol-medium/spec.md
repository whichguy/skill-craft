# Help desk tickets specification

## Requirements

### R-1 Record when a ticket waits on its requester

Basis is “Remind requesters when a ticket has been waiting on them for too long.” (2026-11-21), with the explicit waiting-status default. Extend docs/api.md, “Move a ticket along its lifecycle.” Preserve the other transitions and the existing ticket shape.

- An agent uses the existing transition endpoint and its actor header. in_progress can enter waiting_on_requester. waiting_on_requester can return to in_progress when work resumes or move to resolved when resolved without a reply. Each successful transition records its actor, status change and UTC time through the existing audit contract. The new status works in ticket reads, status filtering and the CLI report. Verify with loopback HTTP and the CLI over saved data.
- Sending an unrecognized spelling such as WAITING_ON_REQUESTER returns 400 invalid. Sending waiting_on_requester from open, closed, or waiting_on_requester returns 409 conflict and does not restart the clock. Verify status, error code and unchanged audit.
- A wait begins on entry and ends on exit. Title and priority edits preserve its start. Reentry begins a separate wait even at the same timestamp. There is no reply endpoint to detect incoming mail, so agents resume the ticket explicitly. Verify with the audited transition sequence and clock.

### R-2 Remind the waiting ticket's requester

Same request basis as R-1. Default policy is one reminder per continuous wait at 72 elapsed hours. Preserve ADR 6 and the existing requester identity and notification envelope.

- On the first worker poll at or after the threshold, a ticket still waiting produces one ticket.requester_reminder for its recorded requester. Its subject identifies the ticket and its body asks the requester to reply with the requested information. Inspect the outbox and the JSON relay line. At one millisecond before the boundary there is no reminder. Open, in_progress, resolved and closed tickets are ineligible.
- Set REQUESTER_REMINDER_HOURS to a decimal whole number from 1 to 2501999792 elapsed hours, the greatest whole-hour value that converts to a safe integer in milliseconds. Unset and blank select 72. Zero, fractional, negative and out-of-range values cause configuration failure naming the variable. Use the config tests to check defaults, valid overrides and rejection. WORKER_INTERVAL_MS=0 disables automatic scheduling and delivery, verified over loopback.
- The reminder uses existing title/requester validation and JSON serialization, without a new free-text input or recipient. It preserves the existing per-request body limits and the configured worker cadence.

### R-3 Preserve a wait's reminder across restart and cancellation

Same request basis as R-1 and ADRs 6–8. The store owns the wait and outbox under a single-process data file. Operators can inspect the existing outbox view. A relay append is the delivery boundary.

- Repeated polls and a DATA_FILE restart produce a single event for a continuing wait through pending, sent or dead outcomes. A later wait has its own event key. Verify at the same time, across restarts and after failure. Existing version 1 files load without migration or inferred waits.
- If delivery fails, retain existing backoff and dead handling. If the wait ends first, block future attempts for that episode and show cancelled for a pending reminder in the outbox. Previously sent deliveries remain visible. The existing relay deduplicates the same id and key if append succeeds before the service records it. Verify retry, cancellation and reentry using a temporary failing relay path and saved outbox data.
- If saving a new reminder fails, it is ineligible for relay delivery until successfully persisted. Verify with a failing save and retry. With no DATA_FILE, the same rules apply within the lifetime of the process.

### R-4 Preserve unaffected contracts

Basis is docs/api.md, README “Command line” and accepted ADRs 4–8. Creation and resolution notifications, their retry/reporting behavior, normal responses and audit history remain. Existing CLI raw columns keep their order, and the weekly report recognizes the waiting status. Verify the original suite and the saved-file consumer test.

## Non-functional requirements

Use the existing synchronous worker and storage ownership, with zero production dependencies. In a healthy service a due reminder is eligible on the next scheduled tick. An idle reminder scan does not rewrite the data file. Recipient information follows the same ticket and outbox surfaces and retention as current notifications. Test timing with the manual clock, failed persistence with a controlled fault, and delivery with local JSONL. No graphical interface or new network service is involved.

## Questions settled

- Q1 Result. The requester gets a reply prompt and operators see pending, sent, dead or cancelled reminder outcomes (R-2, R-3).
- Q2 Authority. An agent records or ends the wait through the existing transition and audit interface, and the worker uses the saved requester (R-1, R-2).
- Q3 Existing machinery. The feature reuses the worker, audit, version 1 data file, outbox, notifier and retry/backoff (R-2, R-3).
- Q4 Hostile and odd input. Existing body and field limits apply, malformed status/threshold values fail through existing validation, and relay content is serialized as JSON (R-1, R-2).
- Q5 Value forms. The exact new status is waiting_on_requester, time is elapsed from the ISO UTC transition, and the threshold is a positive whole number of hours with blank or missing selecting 72 (R-1, R-2).
