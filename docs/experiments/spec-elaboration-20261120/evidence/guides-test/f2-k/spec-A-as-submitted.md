# Help desk ticket service specification

## Requirements

### R-1 Explicit requester wait

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21). Existing lifecycle and envelopes are documented in docs/api.md and CONTRIBUTING.md.

- After creating a ticket and moving it to in_progress, an agent can POST `{"to":"waiting_on_requester"}` to `/tickets/T-0001/transition`. Expect 200, waiting_on_requester in the unchanged ticket shape, and one transition audit record. An open ticket attempting this move receives 409. An unknown status receives the existing 400. Check via HTTP and audit.
- From waiting_on_requester the agent can return to in_progress when a response arrives, or resolve the ticket. The same-status move conflicts. Existing transitions and finality hold. Check the transition matrix.
- Waiting tickets are unresolved and appear in the status filter and active classification. The weekly report counts the added status with raw CLI columns unchanged. Verify the shared state registry and a filtered API read.

### R-2 Timed requester reminder

Basis: the 2026-11-21 request. Timing and repetition are defaults selected for the feature. README and decisions 6–8 describe the existing channel and persistence.

- Each uninterrupted wait becomes eligible at elapsed time greater than or equal to 72 hours (259200000 ms). `REQUESTER_REMINDER_AFTER_MS` overrides this with a positive whole number. Empty uses default and invalid values fail startup naming the variable. A title or priority update during the wait leaves its start intact. Check config and a manual-clock HTTP-to-notifier case at threshold minus one millisecond and threshold.
- At eligibility, the existing worker produces one `ticket.requester_reminder` notification addressed to the ticket's requester. The subject identifies the ticket and the body requests the missing information. A later tick and a restart preserve one logical event for that wait, even if it is dead. Leaving before eligibility suppresses it. Leaving after a failed send stops retries for that wait. Re-entering starts a new wait, including re-entry in the same millisecond. Check local JSONL output, persisted outbox, and worker tests.
- Reminder delivery uses the existing backoff, dead limit, and at-least-once contract. The relay's existing deduplication identity (key and event ID) remains stable across attempts. A failed enqueue persistence write leaves the reminder eligible to retry without publishing it. Check injected failures and release locally using synthetic contacts.
- Worker interval 0 prevents scheduled reminder creation and dispatch. Creation and resolution messages keep their existing behavior. Check the server worker configuration and the existing suite.
- The store owns waiting state and notification events. Waits end when the agent transitions out. Outbox retry cancellation applies only to pending reminders for the ended wait. Existing version 1 data remains readable and readable projections expose only the existing ticket fields and notification recipient data. No requester reply endpoint, new permissions, or separate data service is required. Actual mail relay access is outside local source verification.

## Non-functional requirements

One process owns the data file and synchronous state transitions. Use the existing single scheduler and persisted outbox; idle scans perform no writes. Existing worker cadence governs normal scheduling, with retry backoff on failure. Requesters receive messages only at the address stored on their ticket. The reminder feature adds no graphical surface. CLI/report changes follow their existing output presentation.

## Retired

None.
