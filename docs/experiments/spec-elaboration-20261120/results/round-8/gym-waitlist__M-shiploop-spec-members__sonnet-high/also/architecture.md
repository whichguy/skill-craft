# Class Booking App: architecture

Structure and technology choices only. Product behaviour lives in `spec.md`. Every decision here is **proposed**,
because the existing app could not be inspected (spec OG-1); the plan confirms or revises each against the recovered
baseline. None names a library, language or product.

## Decisions

### AD-1 Promotion happens inside the seat-release commit
- **Serves:** R-3, NFR-1, NFR-2 (invariants I-1, I-2).
- **Decision:** the backend frees the seat and promotes the first `Waiting` entry in one transactional unit that also
  serialises all changes to that class (per-class ordering). Nothing observable exists between release and promotion.
- **Alternatives considered:** (a) a background sweeper that promotes after the fact: simpler to bolt on but violates I-2
  for an unbounded window and needs an invented delay bound; kept only as the fallback if the store cannot give
  atomicity. (b) a client-driven claim: rejected, clients are not authority.
- **Unverified claim:** that the existing store supports the needed transaction or per-class lock. No source or probe is
  available; this is spec OG-7. Resolve with the store's primary documentation or a bounded probe before plan.

### AD-2 Notification is dispatched after commit, at-least-once, deduped by promotion id
- **Serves:** R-6, NFR-6.
- **Decision:** the promotion commit also records a promotion id (and a pending-notification record); a dispatcher
  sends after commit and marks the record sent; redelivery carries the same promotion id so the channel receives one
  effective notification. A failure never rolls back the promotion.
- **Alternatives:** sending inside the transaction (rejected: a slow or failing channel would block seats and hold
  locks); fire-and-forget without a record (rejected: lost on crash, no retry).
- **Unknown:** what the existing channel offers for dedupe (OG-4).

### AD-3 Waitlist entries are a separate entity owned by the booking backend
- **Serves:** R-2, R-4, R-5, R-7, NFR-4.
- **Decision:** a waitlist entry `(class id, member id, backend-assigned sequence, status, timestamps)` is stored
  beside, not inside, the confirmed-booking records, so existing booking reads and the capacity count are unchanged
  (R-8) and a rollback removes only the new entity. Position is derived from the sequence at read time, not stored.
- **Alternatives:** a "waitlisted" status on the booking record (rejected: it risks counting waitlisted rows against
  capacity in existing queries).
- **Unknown:** the existing data model (OG-1); revisit if the baseline shows a status-based design already in place.

### AD-4 Class close is applied by the component that owns booking cutoff
- **Serves:** R-7.
- **Decision:** expiry reuses whatever mechanism already enforces the booking cutoff, with expiry evaluated lazily at
  read and write time against the close time as well as by any existing scheduled work, so a late-running job cannot
  let a promotion happen after close.
- **Unknown:** whether any scheduler exists (OG-1, OG-5).

### AD-5 Reuse the existing UI stack and tokens
- **Serves:** NFR-8.
- **Decision:** the waitlist UI is built from the existing components, tokens and build; no new UI framework or parallel
  stack. Where the app lacks a token or component, extend it from the light expressive starting point in
  `GUIDES/platforms/ui.md`. Concrete treatment is recorded by the plan.
- **Unknown:** the existing UI stack (OG-1).
