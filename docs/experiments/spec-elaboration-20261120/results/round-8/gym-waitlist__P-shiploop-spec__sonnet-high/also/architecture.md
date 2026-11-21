# Class Booking App: Architecture

How the product is built. What it must do lives in `spec.md`; neither restates the other. Decisions are `AD-<n>`.
Stack, framework and data store are **unknown** (spec G-1): nothing is chosen here that depends on them.

## Decisions

### AD-1 Promotion is atomic with the release of the spot, inside the booking authority

- **Decision:** a cancellation that frees a spot and the promotion of the first eligible waitlist entry commit as one
  unit in the same authoritative store that holds bookings. The waitlist lives in that store, not on a client.
- **Why:** it makes invariant I-2 true at rest and makes a failure leave nothing half done (spec R-4, R-6).
- **If the store cannot give atomicity (unknown, G-1):** an idempotent repair promotes whenever booked < capacity and
  the list is non-empty, and runs after every cancel; spec R-4.A3 and R-6.A2 remain the acceptance lines.
- **Consequences:** joins, leaves, direct bookings and cancels per class serialize through the same guard.
- **Status:** proposed; confirm against the real store at plan time.

### AD-2 No new queue, broker or service; notification after commit

- **Decision:** the feature adds no service or message broker. A notification is attempted after the promotion
  commits, through the app's existing channel (spec G-3); failure is recorded and never rolls the booking back.
- **Why:** promotion is synchronous inside the cancel; only notification is async and best-effort (spec R-5).
- **Status:** proposed.

### AD-3 Client reads authoritative state; no push

- **Decision:** the member surface re-reads state on load, focus and after own actions; no sockets or polling are added.
- **Why:** the request does not require live updates; stale views are corrected by the authority on action (spec R-10).
- **Status:** proposed; revisit if G-2 changes promotion to an offer with a timed window.

## Pending

Concrete stack, data model, UI tokens (spec NFR-6) and test tooling are chosen at plan time after G-1 is closed.
