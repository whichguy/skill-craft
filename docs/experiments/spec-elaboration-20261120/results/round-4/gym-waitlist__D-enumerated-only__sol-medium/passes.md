# Specification passes

## Pass 1 — The ground

Added U-1 through U-15 and C-1 through C-19 for the member journey, operator controls, capacity and failures. The workspace contains no app source, product documentation, or runtime configuration. The request supplies no numeric limits, delivery channel, operator workflow, or enrollment rules.

## Pass 2 — Prerequisites

Added C-20 through C-63 by following the request, then tracing the actors, occurrence identity, existing booking eligibility, enrollment, status, and operator view in the first-pass clauses. The new clauses were checked for prerequisites in turn. No independent identity, membership, or timetable policy is evidenced in the workspace.

## Pass 3 — Interactions

Added C-64 through C-108 after walking admission, withdrawal, allocation, capacity, closure, operator controls, reads, and the existing booking flow in overlapping and repeated order. No external delivery dependency is required by the chosen member workflow.

## Pass 4 — Runtime rules

Added C-109 through C-115 for visible behavior at the host boundaries. No binding runtime, hosting platform, service provider, release requirement, or numeric runtime limit could be identified. The clauses describe the behavior if a boundary is reached and mark the applicable rules and figures unconfirmed.

## Pass 5 — Compatibility and invariants

Added C-116 through C-135 for existing booking behavior, authorization, capacity, and rollback. Existing booking behavior is specified by comparison with the equivalent ordinary operation. No app-specific entitlement, billing, or message requirements were evidenced.

## Pass 6 — Builder read-through

Revised the definition of full to include seats owed to waiting members. Split operator controls and booking effects into individual clauses. Added C-136 through C-156 for capacity, consent, refusal feedback, existing booking effects, historical outcomes, and rollback. No evidence supplied a fixed allocation deadline.

## Pass 7 — Lifecycle and failure audit

Rechecked clause provenance against the incoming request and marked selected admission, interface, and closing-boundary decisions as choices. Clarified hold accounting, retry wording, and allocation timing. Added C-157 through C-166 for occurrence removal, bulk withdrawal, action replay, failure feedback, and ordinary booking effects. No further host-specific rules could be established.

## Pass 8 — Boundary audit

Added C-167 through C-172 after tracing the zero-capacity case, existing edits that interrupt booking, definitive versus inconclusive allocation failures, and rollback verification. No existing policy supplied a maximum class capacity, booking-window offset, or recovery time.

## Pass 9 — Cross-check of outcomes

Reconciled the listed refusal reasons with feature withdrawal, the waitlist outcome with bookings made through another path, and paused intake with visibility of history. Added C-173 and C-174 for competing terminal events and later entries behind an unresolved turn. No additional operator controls or external services were identified.

## Pass 10 — Final whole-specification pass

Read U-1 through U-15 and C-1 through C-174 from the start as a builder. Checked that each observable describes an external result, each named set has members or an explicit scope, numeric limits have a value or are identified as unconfirmed, and each wait resolves under overlapping actions. Rechecked refusal and recovery paths, operator authority, compatibility, rollback, and source labels. Verified the format, numbering, and cross-references. This pass added nothing and made no changes to spec.md.
