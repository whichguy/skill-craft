# Invoicing reminders: architecture decisions

How the reminder feature is built. What it must do is in `spec.md`; neither restates the other. Decisions are `AD-<n>`.
Status: proposed by the spec stage; the plan may refine them. No stack was visible to this run (no repository), so
no technology is named and **no platform or library capability is claimed**.

## Decisions

- **AD-1 Periodic evaluation, not per-invoice timers.** A scheduled tick (at least hourly, spec D-6) evaluates all enabled
  accounts. Rationale: due dates and settings can change at any time; re-deriving "what is due" each tick keeps R-3 correct
  without cancelling or rescheduling timers. Serves R-3, R-11. Alternative rejected: one timer per invoice step.
- **AD-2 A durable step ledger with a unique (invoice, offset) key is the claim mechanism.** The unique key makes the claim
  atomic, which provides at-most-once (R-5), recovery (R-11) and history (R-8) from one record. No broker or outbox is added
  (no demonstrated dispatch gap). The chosen store must support an atomic insert-if-absent; the plan verifies that against
  the store's primary documentation before relying on it.
- **AD-3 Outbound email sits behind a small port** (handoff with idempotency key, result classification: accepted /
  transient / hard / unknown). Rationale: lets tests use a recording stand-in (NFR-2) and keeps the provider replaceable (OG-2).
- **AD-4 The clock is injected**, never read directly by the reminder logic. Rationale: time-controlled tests (NFR-2, AC-3.x).
- **AD-5 Invoice status is read from the host at send time and not cached** for the send decision. Rationale: R-2 freshness
  (spec "Service boundaries").
- **AD-6 Stack, hosting and scheduler mechanism are deferred to the plan**, chosen to match the host invoicing product
  (OG-1). Any claim the plan relies on (scheduler cadence guarantees, store atomicity, provider idempotency) needs a
  primary-documentation source or a probe result recorded in the plan.

## Not decided here

UI toolkit and concrete visual treatment (NFR-6; the plan records them as an AD with concrete choices), data-store product,
queueing, deployment topology.
