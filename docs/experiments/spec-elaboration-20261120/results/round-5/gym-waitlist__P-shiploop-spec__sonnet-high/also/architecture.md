# Class Booking App: architecture

How the product is built. What it must do lives in `spec.md` (R-<n>); neither restates the other.
Decisions are AD-<n>. No repository or discovery result existed when these were written, so every
decision is **proposed**, not observed, and revalidates once spec gap G-1 (stack, store, transaction
guarantees) is answered.

## Decisions

### AD-1 Waitlist entries live in the same authority as bookings and seat counts
- Status: proposed (revalidate on G-1). Serves R-5, R-8, NFR-CONSISTENCY.
- Decision: store entries beside bookings and sessions so that "release seat, promote head, create
  booking" is one transaction or one conditional write, serialised per session.
- Alternatives: a separate waitlist service/store (rejected: needs cross-system compensation and breaks
  I-2/I-4 on partial failure); client-side queue (rejected: no authority, privacy).
- Evidence limits: transaction support of the existing store is unknown. If it has none, the
  reconciliation sweep in AD-2 is required and AC-8.3 tests it.
- Revalidate when: the store, hosting runtime or its quotas are learned.

### AD-2 Promotion is part of every seat-releasing operation; no worker, no timer
- Status: proposed. Serves R-5, R-6, R-11 (default D-1).
- Decision: one shared "release seat" code path runs promotion; cancel, staff removal and capacity
  increase all call it. Skipping ineligible heads happens inside it. Notifications are dispatched
  after the commit. If AD-1's store is not transactional, add a per-session repair step that runs
  before any join, direct booking or listing of that session (not a background scheduler).
- Consequence: no async completion to recover and no owner for abandoned work. If spec gap G-6
  resolves to offer-with-claim-window, this decision is superseded and a timer owner is required.

### AD-3 No realtime push; the client reads authoritative state
- Status: proposed. Serves R-10.
- Decision: state and position are read on load and after the member's own actions. No sockets,
  polling loop or cache of waitlist data is introduced; any later cache is keyed by authenticated
  member and bypassed on writes.
- Revalidate when: a freshness requirement is added.

### AD-4 Position is derived, not stored
- Status: proposed. Serves R-3, T-3.
- Decision: store a monotonically increasing join order per session; position = 1 + count of Waiting
  entries with a smaller order. Removing an entry then needs no renumbering.

### AD-5 Notification through the existing channel, after commit, failure isolated
- Status: unresolved (spec G-3). Serves R-9.
- Decision: reuse whatever the app uses today; dispatch after the promotion commits; a failure is
  logged with session and entry ids and never rolls back the booking.

### AD-6 UI: inherit the existing identity
- Status: proposed. Serves NFR-UI. New components follow the app's existing tokens; if none can be
  recovered, adopt the light expressive starting point with a dark option (concrete tokens chosen in the
  plan). Not applicable: any technology choice here, which depends on G-1.
