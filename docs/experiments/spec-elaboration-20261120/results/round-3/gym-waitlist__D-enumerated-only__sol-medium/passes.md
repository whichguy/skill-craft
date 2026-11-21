## Pass 1 — The ground

Wrote 12 use cases and 15 clauses covering a first join, status, withdrawal, openings, direct booking, refusals, heavy demand, interruptions, and operator rollout, observation, class changes, and rollback. The workspace contains no app source or deployment description, so the pass found no existing screens, settings, platform limits, or literal user-facing values to carry over.

## Pass 2 — What the requirements take for granted

Added C-16–C-38 after tracing occurrence identity, member access, eligibility, admission, and the path from waiting to an actual booking. Chose an in-app claimable offer, FIFO priority, an offer window of up to 15 minutes, and a deployment-wide admission pause. The request supplied no eligibility thresholds, booking cutoff offset, reference format, or notification channel.

## Pass 3 — Where the parts meet

Added C-39–C-67 after crossing join, direct booking, cancellation, capacity, reschedule, claim, decline, expiry, eligibility, and outage recovery. Set priority in races, hold ownership, capacity accounting, deadline boundaries, replay behavior, and the end of each open obligation. Found no additional seat-allocation actor or external notification dependency in the request.

## Pass 4 — Runtime rules

Added C-68–C-72 for session validity, external confirmation, platform refusals, delayed offer availability, and production prerequisites. The existing booking app is the only runtime context the request identifies. The pass found no platform, service, deployment configuration, or documented platform limit from which to name a vendor or assert a figure. The affected clauses flag those facts as unconfirmed.

## Pass 5 — Existing behavior and invariants

Added C-73–C-90 for discovery, confirmation, cancellation and capacity compatibility, empty initial waitlists, occurrence isolation, seat counts, access control, charge boundaries, replay safety, and rollback compatibility. The workspace still supplied no existing contract for eligibility, payment, capacity, cancellation, or roles, so these clauses preserve those rules by comparison instead of assigning new values.

## Pass 6 — Build review

Clarified the offer and incident flows, occurrence identification, waiting counts, and stale claim behavior. Added C-91–C-107 to make rollback readiness observable, state the pause boundary, handle unknown outcomes and stale retries, settle failed claims, use a consistent deadline clock, and make allocation without a returning member explicit. Found no additional host payment terms, timer precision, or retry limits to quantify.

## Pass 7 — Cross-check against booking and operations

Added C-108–C-116 after checking every use case against the clauses. Covered full availability when the last seat is held, access to a claim from ordinary booking, the one-seat member scope, rejected edits, permanent removal, the final rollback gate, settings across restarts, concurrent offer endings, and access changes. Revised the flows to show the outcomes members and operators can actually see. Found no requirements for guest waitlists, queue-position display, or historical waitlist views.

## Pass 8 — Permissions, counts, and refusal boundaries

Added C-117–C-120 for spare seats during an unresolved eligibility check, definitive access loss, claim refusal outcomes, and unavailable operator counts. Removed the operator count from the implied duplicate-join observable, clarified the admission and replay boundaries, and made the held-seat and pending-seat rules agree. The pass found no confirmed identifier format or runtime retry limits.

## Pass 9 — Read-through against examples

Corrected the repeat-join observable so it returns the deadline currently in force after a reschedule. Made tie stability observable using a revocation followed by a fresh opening, and made the booking-status and rollback comparisons explicit. Added C-121 for an uncertain admission-setting change. Found no further choice about how simultaneous joins must be ordered.

## Pass 10 — Final verification

Read the whole specification again against the member and operator flows. Checked each observable, the admission and offer states, the seat counts at capacity boundaries, retries arriving after state changes, privacy on refused actions, the rollback gate, and the distinction between explicit choices and unconfirmed host rules. Verified sequential numbering, required fields, and clause references. This pass found no missing or conflicting behavior and made no changes to the specification.
