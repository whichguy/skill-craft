# Help desk tickets

## Requirements

### R-1 Requester wait lifecycle

Basis: “Remind requesters when a ticket has been waiting on them for too long” (2026-11-21), and docs/api.md, Move a ticket along its lifecycle.

- An agent can transition in_progress → waiting_on_requester → in_progress. A new ticket still opens as open. Existing transitions and response shapes continue to work. A known but illegal move (including a repeated wait) returns 409. Check HTTP transitions, filter, and audit.
- The wait starts at the accepted transition; title and priority changes leave the wait start intact. Resume ends the wait. Re-entering begins a new wait even if the two transition clocks read the same instant. Check controlled time and history. A requester reply is handled through the agent's existing workflow.

### R-2 Notify the waiting requester

Basis: 2026-11-21 reminder request. Policy defaults: 72 elapsed hours, one event per wait.

- At the first worker tick on or after the threshold, a ticket still waiting gets one reminder addressed to its stored requester, with the ticket ID, title, and a request to reply. Non-waiting tickets and tickets below the threshold receive no reminder. Check rendered local JSONL output.
- REMINDER_AFTER_MS accepts a non-negative whole number of milliseconds. Unset or empty uses 259200000. Zero disables new reminders and pending reminder delivery while disabled. WORKER_INTERVAL_MS=0 disables all worker work. Invalid values fail configuration with the variable name. Check configuration and worker wiring.

### R-3 Delivery and recovery

Basis: docs/decisions/0006-notification-outbox.md and docs/decisions/0008-json-data-file.md.

- Retries follow existing outbox timing. A queued, sent, or dead reminder prevents a second enqueue for its wait across worker ticks and restart. Once work resumes, any pending reminder for that wait is withdrawn. Check failed delivery and restart with the existing V1 data format.
- Reminder scheduling leaves ticket updated and audit history alone. Existing received/resolved notifications continue to use their current rules. Check service history and full suite.
- TicketStore owns ticket and outbox state. The worker, notifier, and operator surfaces retain their existing boundaries; the stored requester and title have the same visibility and retention as existing notifications. The single process serializes scheduling and transitions. A crash during the relay handoff retains the existing at-least-once contract.

## Non-functional requirements

Use the existing process, environment configuration and data format with no dependencies. Idle reminder sweeps should avoid persistence writes and work over current waits instead of replaying history on every tick. Check implementation and persistence regression coverage. Graphical UI and external relay observation are outside this repository's surfaces.

## Retired

None.
