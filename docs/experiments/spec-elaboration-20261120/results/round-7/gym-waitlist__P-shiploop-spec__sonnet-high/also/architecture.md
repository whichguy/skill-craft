# Class Booking App — Architecture

How the product is built. What it must do is in `spec.md`; neither restates the other.

**Status: the existing app's stack was not inspected (spec.md G-1). Every decision below is PROPOSED, stack-neutral, and
must be revalidated against the real code before planning relies on it. No runtime or library capability is claimed.**

## Decisions

### AD-1 Waitlist entries live in the same transactional store as bookings (proposed)
- Context: R-4 and R-8 need "free a seat" and "promote the next member" to commit together, and need a single total
  order of entries per class.
- Decision: store `WaitlistEntry` beside `Booking`, in the same store and transaction scope, with a per-class
  monotonically increasing sequence and a uniqueness rule of one entry per (member, class).
- Consequence: if the existing store cannot give atomic multi-record changes, this decision fails and the spec's R-4.5 /
  R-8 need a different mechanism. Verify first (G-1).
- Spec link: R-4, R-8, NFR-1, NFR-5.

### AD-2 Promotion runs inline with the seat-freeing operation, not in a polling job (proposed)
- Context: R-4.4 forbids an observable moment with a free seat and a waiting member.
- Decision: the code path that cancels a booking (or raises capacity) calls one shared promote-next routine inside the
  same transaction; the same routine applies the normal booking rules (R-5).
- Spec link: R-4, R-5.

### AD-3 Notifications are sent after commit through the existing notification path, deduplicated by entry id (proposed)
- Context: R-6 needs at-least-once delivery that never undoes a promotion and survives a crash after commit.
- Decision: record the pending notice in the same transaction as the promotion, deliver it afterwards, mark it sent;
  the entry id is the dedupe key. Reuse the app's current mechanism if it has one.
- Spec link: R-6, NFR-5.
