# 6. Notifications through an outbox

Date: 2025-05-12
Status: Accepted

## Context

Requesters want to hear that their ticket arrived and when it is resolved. Sending mail inside the request that changes
the ticket would make the API as slow and as unreliable as the mail relay, which is down for maintenance most Sunday
nights; a request that failed after the change was saved would leave the change made and the requester never told, and
one that retried would tell them twice.

## Decision

We will record each notification in an outbox as part of the change that causes it, and deliver it in the background.

- The store method that makes a change also enqueues its notification (`TicketStore.notify`), in the same step as the
  ticket and its audit entry, and the data file saves them together.
- A worker inside the server process (`src/worker.js`) runs every `WORKER_INTERVAL_MS` and delivers the due
  notifications through the notifier. Request handlers never call the notifier.
- A failed delivery is retried with a doubling backoff; after five failed attempts the notification is dead and stays in
  the outbox for an operator (`GET /admin/outbox`).
- Each notification has a key. Enqueueing a key that is still pending changes nothing, so the same news is not queued
  twice.
- The worker is the service's one background loop. Any other work that runs on a schedule is a job of the worker, not a
  timer of its own and not a side effect of a request, so `WORKER_INTERVAL_MS=0` stops all background work. Tests use
  that to look at what a change enqueued.

## Consequences

- Requests stay fast and never fail because of mail.
- Delivery is at least once: if the process dies between sending and recording the send, the notification goes out again
  after the restart. The relay drops a line it has already seen by its `key` and `id`.
- Notifications arrive up to one worker interval late.
- Each kind of notification needs a template (`src/templates.js`); an event with no template goes dead after its
  retries.
