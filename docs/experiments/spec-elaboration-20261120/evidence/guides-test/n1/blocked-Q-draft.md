# Requester reminder specification draft

S1 asks for a requester-facing notification when a ticket has waited on the requester too long. See current-system-baseline.md and research.md for the existing boundaries and the live local probe.

## R-1 Recognize a requester wait

Proposed: An agent can enter waiting_on_requester from in_progress through the existing status transition API. When the needed reply arrives through the existing support channel, the agent transitions back to in_progress. If a different workflow supplies the signal, revise the entry and exit criteria before acceptance. A ticket merely being open or in_progress carries no wait signal.

Acceptance to verify through the transition API, ticket read-back and audit: a permitted entry starts a wait; an unrelated edit leaves the start intact; an allowed exit ends it; a legal re-entry starts a new wait, even within the same clock millisecond. Unknown values, invalid transitions and oversized bodies follow the existing error contract. Existing persisted tickets contain no waiting status and need no inferred backfill. The status filter, CLI raw layout and report counts must still work.

## R-2 Remind the recorded requester

Proposed policy: on the first worker tick at or after 72 elapsed hours, create one logical reminder per continuous wait. Pending user decision on threshold and cadence. The message identifies the ticket and asks the recorded requester to send the information the help desk needs. Existing notification channels and worker controls apply.

Acceptance to verify using local HTTP transitions, a manual clock, admin outbox read-back and synthetic JSONL output: immediately before the cutoff there is no reminder; at the cutoff one reminder targets the ticket's requester; additional ticks and a restart create no second logical reminder during the same wait. An exited wait is ineligible, including retries for an earlier wait. A separate wait becomes eligible after its own threshold. Existing retry and process-crash delivery semantics remain applicable. Starting with the worker disabled produces no scheduled reminders.

## Observable limits

All checks run in a single service process per data file. Persisted reminder metadata must load with original version-1 ticket files. Recipient data is reused from the ticket and stays inside the current notification and operator boundaries. Follow the established worker interval for scheduling and the existing backoff for retry. The local file check proves delivery to relay input. Production inbox receipt requires access to the mail relay and an authorized target.

## Pending decisions

The requested outcome is clear. The owner needs to choose the event or API state that starts and ends a requester wait, and the notification threshold and cadence. The repository cannot settle those business rules. The draft is held outside the committed spec until those choices are established.
