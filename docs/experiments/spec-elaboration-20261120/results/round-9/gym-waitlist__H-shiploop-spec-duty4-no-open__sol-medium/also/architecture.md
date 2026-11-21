# Class Booking App Architecture

## Decisions

### AD-1 · Use the booking authority to coordinate fulfillment

**Status.** Specify one logical booking authority for the capacity, membership and booking decisions for a class occurrence. Physical placement and integration mechanism remain unresolved.

**Basis.** The waitlist extends existing booking rules and shares the same seats with ordinary booking. Coordinating through the existing booking authority makes the existing eligibility and capacity checks binding for joins and promotions and gives recovery one owner. The invariant and consumer outcomes are in [R-1](spec.md#r-1--join-the-waitlist-for-a-full-class), [R-3](spec.md#r-3--fill-a-vacancy-from-the-waitlist) and [R-5](spec.md#r-5--keep-waitlist-state-private-and-feedback-accurate).

**Placement and evidence.** Prefer reuse of existing booking-owned durable state and diagnostics where they support the specified state, permission, coordination and recovery guarantees. The booking maintainer must identify the actual runtime, owners, data stores, quota, retention, and authoritative transition and recovery paths before a physical design. The standalone stage has no runtime evidence or primary documentation identifying the app stack. Revalidate this decision if the existing authority spans independently committing systems or its facilities cannot provide a coherent outcome under retries and races. The applicable boundary checks and open prerequisites are in [Service boundaries](spec.md#service-boundaries).
