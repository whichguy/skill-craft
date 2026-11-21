# Class Booking App Architecture

## Decisions

### AD-1 — Booking authority and recovery

**Status.** Unresolved. Prefer extending the existing booking authority and booking entry points with waitlist ordering and restart-safe allocation. Reuse ordinary booking records, eligibility logic and existing diagnostics where they satisfy the contract. Technology and runtime selection remain open.

**Basis and capability map.** [R-1](spec.md#r-1--join-the-waitlist-for-a-full-class) needs scoped durable waitlist admission. [R-2](spec.md#r-2--turn-an-opening-into-a-booking) needs one authoritative ordering of joins, competing bookings, withdrawals and capacity changes, with atomic booking-and-entry completion and recoverable open work. [R-3](spec.md#r-3--see-and-manage-ones-own-waitlist-status) needs authorized read-back via existing member surfaces. [R-4](spec.md#r-4--protect-and-end-waitlist-state) needs private state placement, lifecycle cleanup and owned diagnostics. Prefer existing authorized reads for confirmation and existing runtime-owned recovery where capable. Establish any actual cache, processor, recovery or service gap before choosing additional infrastructure.

**Evidence limits and revalidation.** The request establishes the booking product and desired change. Prior accepted intent, local definitions, current runtime state, producer contracts, effective identities, native state facilities and diagnostics are unavailable. Before selecting a structure, the booking owner must trace existing booking and capacity writers, inspect the actual state, identity and restart facilities, and confirm their behavior at the selected boundary. The operations owner checks existing event coverage, destination, quotas and retention. The UI owner inspects existing primitives and theme behavior before a concrete UI decision. A future runtime note can hold observed facts and safe receipts once a target is available. Revalidate this decision when a capacity writer, booking policy, lifecycle rule, platform constraint or permission contract changes.
