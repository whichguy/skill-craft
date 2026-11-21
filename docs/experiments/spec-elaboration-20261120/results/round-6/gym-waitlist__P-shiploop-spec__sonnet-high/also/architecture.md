# Class Booking App: architecture decisions

Structure and technology choices only. What the product must do is in `spec.md`; nothing here is a requirement.
Numbering is `AD-<n>`. Product defaults the spec records as design decisions use `D-<n>` in `spec.md`, never `AD-`.

## Decisions

### AD-1: The waitlist lives with the booking authority

- **Status:** unresolved. The booking app's stack, store and runtime were not available to this stage (no repository, no
  discovery or research result). This is the proposed shape, to be confirmed or replaced once the baseline is recovered.
- **Decision (proposed):** waitlist entries are owned by the same server-side component and store that already own
  bookings and class capacity. Clients (member screen, any API consumer) hold only presentation state and read the
  waitlist through the booking authority.
- **Why:** R-5 and R-8 need "free a seat, promote the head, never exceed capacity" to be one consistent change; two owners
  would need cross-store coordination that the request does not justify.
- **Depends on a claim not yet verified:** that the existing store can apply the cancel and the promotion as one atomic
  unit, or serialise them per class. No primary documentation or probe was available. R-8 states the required outcome;
  the mechanism is the plan's to choose once this is checked.
- **Revalidate when:** the baseline shows bookings are held in a store with no per-class atomicity or locking, or the
  booking logic is split across clients.

### AD-2: Promotion is performed by the booking authority, not by a client or a timer

- **Status:** proposed.
- **Decision:** promotion runs inside the operation that freed the seat (member cancel, capacity increase), so there is
  no scheduled sweeper for the default policy D-1 (automatic booking, no claim window).
- **Revalidate when:** the open decision on a claim window (spec R-5, gap G-1) is resolved as "offer with deadline",
  which would introduce time-driven expiry and an owner for it.

### AD-3: Notification reuses the app's existing channel

- **Status:** unresolved. Whether the app has email, push or in-app notifications is unknown.
- **Decision (proposed):** reuse the existing channel. Introduce none for this request. If none exists, R-6 is satisfied
  by in-app status alone (see spec R-6 gap G-3).
