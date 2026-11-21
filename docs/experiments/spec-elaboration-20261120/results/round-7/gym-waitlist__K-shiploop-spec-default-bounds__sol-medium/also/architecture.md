# Class Booking App Architecture

## Decisions

### AD-1 Extend the existing booking authority

**Status** — Selected direction, with runtime binding and feasibility unresolved. Source is the [dated user request](spec.md#scope-and-basis) and [R-1 through R-4](spec.md#requirements).

Place authoritative waitlist state and the allocation decision within the existing booking ownership boundary. The affected booking and queue changes must share a commitment boundary that establishes the R-3 invariant. Reuse current identity, ordinary booking and cancellation, class lifecycle and authorized diagnostics where they can fulfill the specified contracts. Keep pending UI state local to the active view and reconcile through authoritative reads. A second book of record, a new identity provider, or a notification/worker subsystem would add coordination without supplying a requested outcome. The service contract avoids depending on any such component.

Dated evidence is limited to the request and abstract [desk replays](spec.md#behaviour-flows-and-replay-evidence). No provider, storage mechanism, transaction primitive, schema, service route, cache facility or cleanup hook has been established. Current definitions, accepted prior contracts and remote state are unknown. The intended change is the extension described here. Before integration, locate the real owner and all seat-changing paths, obtain the supported storage and runtime constraints from primary versioned sources or scoped probes, and determine whether the booking, consent and release operations meet the commitment boundary. Inspect actual event coverage and redacted outcomes at the existing diagnostic destination. If the premise fails, keep the dependent path open and resolve it in the existing correction route before choosing an alternative structure. The target and changed file roles are pending discovery.

### AD-2 Extend the class booking interface

**Status** — Selected direction, with actual component and appearance binding unresolved. Source is [R-5](spec.md#r-5-show-the-member-a-trustworthy-result-in-the-booking-app) and the [visual direction](spec.md#non-functional-requirements).

Extend the existing class status and primary action composition and use the ordinary booking surface for the promoted booking. An integrated status and action keeps booking and waiting in the same journey. A separate screen or toolkit would add navigation and design-system maintenance without supplying a required interaction. Reusing accessible primitives is the smaller direction if their status, focus and responsive behavior meet R-5. Evolving the existing components is the next option if those capabilities are missing. No estimate, library or framework selection can be validated without the baseline.

Inspect the actual class and booking views, theme conventions, component toolkit and supported widths. Apply the spec's visual reference to any genuinely new graphical surface within those conventions. At planning, choose the concrete composition and motion treatment, then verify the rendered focus, contrast, narrow/wide layout and pending-to-confirmed interaction in the target runtime. Revisit the reuse choice only when an observed compatibility or accessibility gap warrants it.
