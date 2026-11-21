# Class Booking App: Architecture

Structure and technology decisions for the class waitlist (see `spec.md`). The app's stack, store and UI toolkit are **unobserved**
(spec OG-2), so every decision here is **proposed**: it states what the spec's requirements need and the capability it assumes.
Each assumed capability is unverified and must be confirmed against the real system before planning relies on it.

## Decisions

### AD-1 The waitlist lives in the same authoritative store as bookings

- **Serves**: R-3, R-9, R-10, R-13. **Status**: proposed.
- **Decision**: the waitlist entry (class ID, member ID, join order) is an additive entity in the existing booking store. No new datastore, cache or service.
- **Why**: promotion must be atomic with the seat release (AD-2), which needs one consistency boundary. A separate store would need a cross-system operation and its own recovery (service-discovery: assign authority per entity; no cross-system transaction can be assumed).
- **Alternatives**: separate store or queue service (rejected: needs reconciliation for no benefit at this size); client-side storage (rejected: other members' operations decide the order).
- **Assumed, unverified**: the existing store can hold a new entity and offers transactions or conditional writes. **Revalidate** when the baseline names the store; if it has neither, AD-2's fallback applies.

### AD-2 Promotion runs inside the releasing operation, with no queue or worker

- **Serves**: R-3, R-4, R-9.I3, R-9.I5. **Status**: proposed.
- **Decision**: cancel, capacity raise and staff removal call one shared "release seat and promote" routine that, in one atomic unit, frees the seat, selects the first eligible entry in join order, creates the booking and removes the entry. Per-class serialisation comes from the store (row or conditional write on the class's seat count), not from an in-process lock.
- **Why**: avoids any state in which a seat is free while an eligible member waits, and avoids a second actor that could race with direct bookings.
- **Fallback** if the platform cannot give atomicity: perform release then promotion with a reconcile step (`promote-if-possible`) run at the start of every read or booking operation on that class, so R-9.I5 is restored before anyone can observe or exploit the gap. Outcome of an interrupted run is then eventually consistent, which R-9.A4 must be updated to say.
- **Alternatives**: background worker draining a queue (rejected: adds a failure mode and a delay between release and promotion; a one-process lock would not protect other writers).
- **Assumed, unverified**: as AD-1.

### AD-3 The cutoff is evaluated at read and promotion time

- **Serves**: R-8, R-13. **Status**: proposed.
- **Decision**: "open" is computed from the class's close time (existing booking-close time, else start; spec DEC-2) at every join and promotion and every read. Entries after cutoff are inert; physical removal is best-effort housekeeping after class end.
- **Why**: correctness does not depend on a scheduler running exactly at the cutoff instant.
- **Alternatives**: scheduled job that closes lists at the cutoff (rejected as the correctness mechanism: a late or missed job would allow a post-cutoff promotion). A job may still do housekeeping.
- **Revalidate**: clock source. Cutoff comparisons use the store or service clock, not a client clock; confirm the existing app's convention.

### AD-4 Notices are sent after commit through the existing channel

- **Serves**: R-7. **Status**: proposed.
- **Decision**: after the atomic unit commits, hand one notice per promotion to the app's existing booking-confirmation channel. The send is outside the atomic unit; its failure is logged (class ID, member ID, outcome) and never rolls back a booking.
- **Why**: the booking is the source of truth; acknowledgement from the channel means "accepted", not "seen".
- **Alternatives**: transactional outbox (not adopted by default: costs a table and a relay; revisit if losing a notice after a crash is judged unacceptable, spec R-13 accepted risk).
- **Open**: channel identity (spec OG-1).

### AD-5 Positions are derived, not stored

- **Serves**: R-1, R-5, R-6, R-9.I4. **Status**: proposed.
- **Decision**: store a join order (a monotonically increasing sequence per class, assigned by the store); the position shown is the entry's rank among current entries for that class, computed on read.
- **Why**: leave, promote and class cancel would otherwise rewrite many rows; derived ranks stay contiguous by construction.
- **Alternatives**: stored position column renumbered on each change (rejected: more writes and a place for I4 to break). A timestamp alone is not used as the order because equal timestamps tie.

### AD-6 The UI extends existing components and uses request/response only

- **Serves**: R-5, R-12, DEC-6. **Status**: proposed.
- **Decision**: add waitlist states as variants of the existing class card/detail and My-bookings list; read via the app's existing fetch path; no sockets, polling or push. Visual identity is inherited; the fallback visual reference (light Gemini look, Material 3 Expressive principles, light first with a dark option) applies only if discovery finds no established identity, and its concrete tokens are then recorded as a further AD.
- **Alternatives**: real-time push (rejected for now, DEC-6); a new UI toolkit (rejected: no evidenced gap).
- **Unverified**: that the app has a web UI at all; if not, the platform's conventions replace the browser checks in R-12.

## Not decided here

Stack, store product, schema names, endpoint shapes, notification provider, error-code spellings: these follow the existing app once the baseline is recovered. Choosing them now would be invention.
