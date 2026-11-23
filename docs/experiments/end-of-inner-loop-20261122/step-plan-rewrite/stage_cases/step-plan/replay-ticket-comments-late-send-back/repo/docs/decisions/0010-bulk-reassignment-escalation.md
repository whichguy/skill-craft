# 10. Bulk reassignment and escalation

Status: Accepted

## Context

Agents need to transfer active work, and urgent tickets left unassigned need attention. Notification delivery and state
already belong to the store and outbox, with scheduled work in the worker.

## Decision

Bulk reassignment uses the same assignment effects for each active ticket and saves the resulting state together.
The worker selects open, unassigned urgent tickets strictly older than the configured age and records an escalation
marker, audit entry and outbox event together. The on-call notification does not assign the ticket. Missing markers in
version 1 files mean not yet escalated. ONCALL is optional and worker interval zero disables this job.

## Consequences

With DATA_FILE configured, the marker and outbox survive restart; otherwise state is in memory only. Delivery retries
follow the existing outbox policy. The worker's polling interval adds delay after the age threshold, and restoring an
older backup restores its older escalation state.
