# Class Booking App — Architecture decisions

How the product is built. What it must do is in `spec.md`; neither restates the other.
All entries are **proposed**: the existing app was not inspected (spec G-1), so each one is conditional on that baseline and must be revalidated first.

## Decisions

### AD-1 Waitlist entries live in the same authority and transaction scope as bookings
- **Status:** proposed (unresolved until baseline, G-1).
- **Decision:** store waitlist entries in whatever store already owns bookings, and perform cancel+promote, capacity-raise+promote, join and leave as single transactions (or the closest atomic/conditional primitive the store offers) scoped per class session.
- **Why:** spec R-5 and R-9 require that a cancellation and its promotion commit together and that no overbooking or free-place-beside-waiter state is ever visible. A second store or an eventually consistent copy cannot give that without a cross-system protocol.
- **Alternatives considered:** a separate waitlist service/queue (rejected: needs cross-system recovery for no demonstrated need); client-side waitlist (rejected: not authoritative).
- **Revalidate when:** the existing store turns out not to support per-class atomic units. Then R-9 needs a different mechanism (conditional writes with a revision on the class row) and this AD must change.
- **Evidence limit:** no primary documentation consulted; the claim that the store supports transactions is **unverified** and a probe is due in discovery (owner: discovery run).

### AD-2 Promotion runs inline with the cancel, not in a background worker
- **Status:** proposed.
- **Decision:** promotion happens in the same request/transaction as the event that frees a place; notification is dispatched after commit, keyed by waitlist entry id so retries are idempotent. No queue, broker or outbox is added.
- **Why:** spec R-5 and its invariant I-3; a worker would open a window where a place is free beside a waiter. The only asynchronous work is the best-effort notification (R-6).
- **Revalidate when:** notification volume or an existing channel's latency forces dispatch off the request path; then a durable dispatch record keyed by entry id is the first thing to add.

### AD-3 UI structure for the waitlist surfaces (slot reserved)
- **Status:** unresolved. The UI toolkit and design tokens are unknown (G-1, G-10).
- **Decision:** to be chosen at planning: reuse the existing component library and tokens; apply the light expressive starting point (spec R-15) only where the existing identity leaves a choice open; a concrete treatment (type scale, palette tokens for light and dark, shape hierarchy, icon set) is recorded here at plan time, not adjectives.
- **Revalidate when:** the baseline is recovered.
