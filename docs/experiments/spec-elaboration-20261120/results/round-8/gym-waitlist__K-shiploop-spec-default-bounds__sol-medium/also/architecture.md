# Class Booking App Architecture

## Decisions

### Reuse the booking authority

**AD-1.** Proposed structure, pending inspection of the app. Extend the existing authority for booking and class capacity to own the waitlist and allocation. Reuse the ordinary booking domain path and existing operational destination wherever the inspected contracts support R-1 through R-4. This keeps allocation and direct booking under the same consistency boundary. The client consumes authorized booking snapshots and presents local action state. The feature requires no separate notification service.

The existing authority, callers, storage guarantees, recovery facilities and operational destination are unknown. The booking maintainer must verify that the chosen path can serialize competing actions and recover a committed vacancy after interruption. If the current boundary cannot support those invariants, revise this decision before implementation. The client maintainer must inspect existing UI primitives and theme conventions before selecting the concrete visual treatment. [Contracts and cases](spec.md#service-boundary-contracts) provide the requirements for those decisions.
