# Class Booking App: Architecture

How the product is built. What it must do is in [spec.md](spec.md); neither restates the other.

**Evidence limit:** no repository was inspected when these decisions were written (spec G-1, G-5). The stack, store and
hosting are unknown, so each decision below states a constraint and how the plan must confirm it against the real
system. Nothing here is verified.

## Decisions

### AD-1 Promotion is atomic with the event that frees the spot
Serves R-4, R-5, R-7. Freeing a spot (cancellation, capacity raise) and booking the next eligible waiting member form
one indivisible unit in the component that owns capacity, so no reader or competing booking can observe or use the
gap. Alternatives: a separate background promoter (leaves a window and needs its own recovery) or optimistic retry by
clients (unfair). **Unproven claim:** the actual store can make this unit atomic (a transaction or an equivalent
per-class lock); the plan must confirm it from the store's documentation or a probe, and if it cannot, raise a spec
conflict instead of weakening R-7. Revisit when the store changes.

### AD-2 The waitlist lives in the booking system's own store
Serves R-1, R-2, R-7. Waitlist entries sit beside the bookings and capacity they must agree with; no new service,
queue or cache is added. Positions are derived from a stored join order, not stored as mutable numbers. Alternatives: a
separate waitlist service (adds a consistency boundary for no requirement). Revisit if the booking store cannot hold the
data.

### AD-3 Time comes from an injectable clock
Serves R-1, R-6, NFR-9. The booking-close boundary is evaluated against a clock the tests can control; closing an entry
at the boundary is applied on read or by a schedule, and reads must treat a closed class's entries as ended either way.

### AD-4 Notices are sent after commit through the existing mechanism
Serves R-8. Delivery runs after the state change commits and never inside the atomic unit of AD-1; a failure is logged
and does not roll anything back. The member-visible status is read from state, not from the notice. A new channel is
added only if the spec's G-2 shows none exists and the user asks for one.

### AD-5 Repair
Serves R-7 recovery. One idempotent routine re-evaluates a class (free spots versus Waiting entries) using the same
promotion code path as AD-1, callable after an interrupted operation or migration. It adds no second promotion rule.

### AD-6 Additive interface
Serves R-9, NFR-8. Waitlist data is added to existing responses and new operations (join, leave) are separate; existing
operations and fields keep their meaning, so older clients keep working.
