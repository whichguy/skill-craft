# Class Booking App — Architecture

Only structure and technology choices live here. Product behaviour lives in `spec.md`.
No repository or baseline was available when these decisions were taken (see `spec.md`
G-1), so every decision below is **provisional**: it is the best reversible default for the
behaviour in `spec.md`, and each carries the condition under which it must be re-checked
against the real system.

## Decisions

### AD-1 Waitlist state is stored with bookings, in the same authoritative store

- **Decision:** waitlist entries are persisted in the same store that owns bookings and class
  capacity. Every operation that changes a booking count or a waitlist entry (join, leave,
  cancel booking, capacity change, class cancel, promotion) commits as one atomic unit, or
  fails as one unit.
- **Why:** `spec.md` R-10 requires that a freed spot and the promotion that fills it are never
  observable apart. A second store would need a cross-store transaction or a reconciler.
- **Alternatives:** separate waitlist store with a reconciler (rejected: exposes the
  free-spot-with-waiter window); in-memory waitlist (rejected: lost on restart, and
  instances would disagree).
- **Status / revalidate:** provisional. Revalidate when discovery shows the real store. If it
  offers no multi-row atomic write or conditional write, `spec.md` G-7 stays open and R-10 is
  not ready.
- **Supports:** R-1, R-3, R-5, R-6, R-10, R-16.

### AD-2 Waitlist order is a server-assigned per-class sequence number

- **Decision:** each entry takes the next value of a per-class counter, assigned inside the
  join transaction. Order is ascending sequence. A member's position is derived at read time
  (count of Waiting entries with a lower sequence, plus one); positions are never stored or
  renumbered.
- **Why:** client clocks are untrusted and timestamps can tie; derived positions cannot go
  stale when someone ahead leaves.
- **Alternatives:** database timestamp (rejected: ties and clock skew); stored positions
  (rejected: renumbering on every leave, and a concurrent-write hazard).
- **Status / revalidate:** provisional; revalidate against the store's counter/sequence
  facility. **Supports:** R-2.

### AD-3 Promotion is synchronous; no worker, queue or scheduler

- **Decision:** promotion runs inside the transaction of the operation that freed capacity.
  Waitlist closure (R-6) is evaluated lazily, on any read or operation touching the class,
  from the class's booking-allowed predicate; no timer or job moves entries to Removed.
- **Why:** nothing in the request needs background work. A worker would add a crash window
  between "spot freed" and "waiter booked", and would need its own retry and ownership rules.
- **Alternatives:** queue-driven promotion (rejected: adds the very window R-10 forbids);
  scheduled sweep for expiry (rejected: lazy evaluation gives the same observable result
  without an owner for the job).
- **Status / revalidate:** provisional. Revalidate if (a) the real booking path cannot be
  invoked inside the freeing transaction (e.g. it calls an external payment service, see
  G-3), or (b) the owner chooses a claim-window model (assumption A-1), which would need a
  timer owner.
- **Supports:** R-3, R-5, R-6, R-10.

### AD-4 Caller identity comes only from the existing session

- **Decision:** join and leave take a class identifier; the acting member is the
  authenticated caller. A member identifier in the request body is not accepted. No new
  identity, role or sharing mechanism is introduced.
- **Why:** this makes acting on another member's entry impossible by construction (R-11).
- **Status / revalidate:** provisional on the existing auth model (G-1).
- **Supports:** R-1, R-4, R-11.

### AD-5 The member client reuses the existing UI stack and tokens

- **Decision:** waitlist UI is built from the existing client's components, spacing/type
  tokens and icon set, extended only where a state has no existing component. The light
  expressive starting point (Gemini-light look, Material 3 Expressive principles) fills only
  tokens the app does not already define; the app's own identity takes precedence. No new UI
  framework is added.
- **Alternatives:** a new component library (rejected: no gap is evidenced).
- **Status / revalidate:** provisional; revalidate when the client platform is known (G-8).
  On a native client the platform's appearance policy replaces the light-first default.
- **Supports:** R-8, R-13, R-14.

### AD-6 Member views are pull-based

- **Decision:** the client fetches waitlist status on load, on regaining focus and after each
  of its own actions. No push channel, socket or polling loop is added.
- **Why:** the request asks for no live updates, and the server rejects stale actions
  (R-17), so a stale view cannot cause a wrong outcome.
- **Alternatives:** polling or push (rejected for now; revalidate if members need live
  position, or if G-4 finds an existing push channel that makes it nearly free).
- **Supports:** R-7, R-17.

### AD-7 No new outbound notification channel

- **Decision:** promotion and removal are always visible in-app. Outbound notification (email,
  push, SMS) reuses a channel the app already has; if none exists, none is built under this
  request (G-4).
- **Supports:** R-7.
