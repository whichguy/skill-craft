## Pass 1 — the ground

Wrote eight flows covering first and repeat joins, empty and populated queues, openings, refusal, recovery, rollout, shutdown, existing data, and rollback. Added the plain observable behaviours. Found no project checkout, booking documentation, or runtime declaration in the supplied workspace, and no explicit bounds or wording in the request.

## Pass 2 — presuppositions

Worked through the request and Pass 1 clauses for occurrence identity, member identity, authorization, eligibility, states, ordering, deadlines, queue size, and the rollout setting. Repeated the check for the newly introduced offer and entry states. Found no basis for assuming new membership rules, a separate waitlist size cap, or deployment-specific roles or cutoff values.

## Pass 3 — interactions

Crossed joins, withdrawals, claims, direct booking, expiry, notices, cancellations, schedule and capacity edits, eligibility changes, and rollout changes. Added allocation priority, outcomes for conflicting actions, stale and repeated requests, and recovery from failed or late availability processing. Found no declared external messaging provider or booking completion integration to specify by name.

## Pass 4 — runtime rules

Checked clock and time-zone authority, session expiry, hosted request failure, resource ceilings, background progress, and live-deployment prerequisites. Documented what the existing booking app and its eventual deployment can constrain. Found no named stack, hosting limits, provider rules, or confirmed numeric runtime limits in the supplied materials.

## Pass 5 — preservation and invariants

Added preservation of existing reservations and cancellation behavior, consistency across booking paths, payment boundaries, privacy, capacity safety, and rollout and rollback guarantees. Found no evidence of app-specific pricing, cancellation windows, role names, or alternative booking surfaces to hard-code.

## Pass 6 — first builders' read

Tightened the generic member-status clause, separated charge retry safety from pricing, and distinguished expiration from withdrawal. Added observable rollout and inspection states, notice publication, the assignment bound, outage behavior, actionable refusals, and end states after account deletion and ordinary booking. Found no basis for prescribing text, queue rank for members, operator overrides, or a new retention policy.

## Pass 7 — timing, dependencies, and readback

Rechecked existing checkout holds, eligibility outages, cutoff races, rollback-setting retries, and cancellation while offer processing is down. Added rules for missing availability updates, timed recovery, first terminal outcomes, and read-only status checks. Clarified when the 60-second window applies. Found no evidence of an existing hold duration or a new product-level queue limit.

## Pass 8 — failure and capacity readback

Checked every flow and clause again with unmet dependencies and stale data in mind. Specified what uncertain eligibility means for queue priority, how public availability counts commitments, when holds end, and what an operator sees when the queue cannot be verified. Restricted historical replay results to data the member can still access. Found no additional public availability fields to require.

## Pass 9 — cross-check of capacity and closure

Read back offer deadlines, capacity reductions, and the member's and operator's views after closure. Made ordinary holds count in a capacity reduction, fixed which deadline survives repeated rescheduling, specified how an unknown eligibility result affects its queue, and made the member's closed outcome findable. Found no need for a new booking status or a separate history view.

## Pass 10 — use-case trace

Traced the visible actions in each use case back to clauses. Added the path from an already-confirmed waitlist result to ordinary booking controls. Found no other actions in the flows without a corresponding observable rule.

## Pass 11 — final builders' read

This whole-specification pass added no builder-relevant behavior. Reread all eight use cases and 145 clauses for observable outcomes, single behaviors, complete state and control lists, numeric bounds, source attribution, and consistency across failures, races, recovery, and rollback. Checked the required section order, field labels, source references, and consecutive numbering. No application or deployment evidence surfaced to confirm the runtime limits.
