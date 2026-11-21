## Pass 1 — Ground

Wrote the member journeys for a full class, an open class, an empty queue, a contested seat, withdrawal, retries, refusals, and a class that closes. Added the first clauses for the outcomes each journey needs. The workspace contains no booking source, product documentation, or deployment configuration. Found no stated capacity, queue limit, or runtime.

## Pass 2 — Presuppositions

Followed the incoming sentence and the first ten clauses through session identity, visibility, eligibility, capacity, ordering, consent, lifecycle, and unsuccessful requests. Added observable prerequisites and choices for policies the request leaves open. Found no app-specific validation rules or exact product capacity values to transcribe.

## Pass 3 — Operators

Added activation and verification, global and session controls, queue inspection, change history, failure investigation, correction, old-data handling, and rollback. Chose to end active places on disablement while preserving confirmed bookings. Found no supplied operator role names, existing control names, rollback environment, or retention period.

## Pass 4 — Interactions

Walked joins, withdrawals, status reads, member permissions, booking and capacity changes, eligibility, the queue, session timing, settings, operator corrections, and rollback against the actions they can affect. Added rules for stale requests, repeated delivery, competing grants, incomplete promotion, outage recovery, and session edits. Found no separate claim, notification delivery, or payment service specified to integrate.

## Pass 5 — Runtime

Checked for an app platform, hosting configuration, and product runtime constraints. The workspace tooling is separate from the booking app. Recorded readiness, request and background timeouts, possible admission limits, and live deployment prerequisites as unconfirmed where the app's platform would supply them. Found no documented platform rule or numeric runtime limit to assert.

## Pass 6 — Existing behavior and invariants

Made schedule access, direct confirmation, attendance, cancellation, and capacity preservation explicit. Added guards for privacy, restarts, duplicate charges and confirmations, member authorization, and offline use. Found no evidence for the original app's specific notification, billing, attendance, or cancellation settings.

## Pass 7 — Builder read-through

Reconciled the member outcome list with the operational history. Added discoverable closed outcomes, stale setting and withdrawal handling, account closure, schedule-window edits, lost responses after booking, and the last-seat fallback. Extended the 60-second attempt bound to continued processing while an open seat and active queue persist. Found no need to prescribe display wording, a queue position display, or a storage design.

## Pass 8 — Failure and clause boundaries

Separated operator read failures from the effect on seat allocation. Specified what happens when cancellation succeeds but promotion fails, when promotion succeeds but confirmation delivery fails, and when rollback readiness cannot be verified. Checked that ordinary booking requires its own action and that queue priority holds across booking paths. Found no additional product limit to impose on queue length or the number of sessions a member may wait for.

## Pass 9 — Lifecycle consistency

Checked retained history against live bookings and current session permissions. Clarified when a historical promotion is recorded, how other existing session-wide closures end waiting, what remains visible after a permission change, and how a member distinguishes an unreadable status from no place. Found no confirmed app-specific closed states beyond the situations already enumerated.

## Pass 10 — Partial outcomes

Extended the refreshed join control rule to cover existing session-wide closures, made the opening instant inclusive, and covered interrupted operator removal, unverified booking commits, and financial effects of failed promotion. Found no supplied compensation methods or completion times.

## Pass 11 — Convergence

Read the full specification in order from member eligibility through admission, promotion, closure, operator intervention, rollout, and rollback. Checked each outcome against its trigger, its visible result, overlapping actions, and the later reads that depend on it. Checked finite outcome lists, numeric bounds or explicit uncertainty, sources, and consecutive numbering. This pass found no missing or conflicting behavior that would change what a builder delivers and left the specification unchanged.
