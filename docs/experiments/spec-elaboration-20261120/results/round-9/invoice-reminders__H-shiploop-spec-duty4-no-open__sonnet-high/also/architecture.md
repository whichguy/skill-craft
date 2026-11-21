# Invoice Reminders — Architecture Decisions

How the product is built; what it must do is in `KNOWLEDGE/spec.md`. Decisions are `AD-<n>`.
**All decisions below are proposed, not accepted:** no repository, host runtime or environment was inspected for this
run (spec OG-2), so each one must be revalidated against the host before the plan relies on it.

## Decisions

### AD-1 Scheduled evaluation as a pure function, no queue or broker
- **Status:** proposed. **Serves:** R-3, R-6, R-7, NF-2, NF-6, NF-9.
- **Decision:** reminder logic is one evaluation function of (settings, invoice snapshot, ledger, `as-of` instant),
  invoked by the host runtime's native daily scheduler at the local send time and, for verification, with an explicit
  instant. Each invoice's step is processed and committed independently. No message broker, outbox or per-invoice timer.
- **Alternatives:** per-invoice timers or events on invoice change (more moving parts, harder to catch up after
  downtime); a broker (no demonstrated dispatch gap, `service-discovery.md#asynchronous-cooperation`).
- **Revalidate when:** the host runtime has no durable scheduler (then use that platform's guide for its native
  option), or invoice volume (NF-3) makes a single pass too slow.

### AD-2 Durable reminder ledger with a datastore-enforced claim
- **Status:** proposed. **Serves:** R-6, R-7, R-8, NF-2.
- **Decision:** settings, ledger and run records live in the same durable store the host already uses for application
  data. The claim for (invoice, offset, mode) is an atomic insert on a uniqueness rule enforced by the store, not an
  in-process lock. Invoices stay in the invoicing system of record and are only read.
- **Alternatives:** file store or in-memory lock (not safe for overlapping runs or external writers).
- **Revalidate when:** the store cannot offer an atomic conditional insert; then define the real reconciliation rule
  and test it.

### AD-3 Email behind a delivery adapter
- **Status:** proposed, provider unresolved (OG-1). **Serves:** R-5, R-6, NF-1, NF-6.
- **Decision:** one adapter interface returns `accepted`, `rejected` (definitive; permanent or transient) or `unknown`
  (no answer within the call limit). A capturing implementation serves tests; the live implementation takes its
  credential from the platform secret facility. No credential in settings, ledger or logs.
- **Revalidate when:** a provider is chosen; check its documented accept/reject/timeout semantics and quota.

### AD-4 Operator screens inside the host UI
- **Status:** proposed. **Serves:** R-2, R-8, NF-7.
- **Decision:** the settings and history screens extend the host product's existing UI toolkit, tokens and operator
  authentication; no parallel UI stack. If the host has no UI, the screens are reconsidered (spec D-13).
- **Visual direction:** if the host has no established identity, the light Gemini-style profile with Material 3
  Expressive principles from `GUIDES/platforms/ui.md#light-expressive-starting-point`, light first with a dark option;
  the concrete tokens, type scale and focal treatment (schedule editor with live preview) are chosen at planning and
  recorded here.
- **Revalidate when:** the host baseline is inspected.

### AD-5 Time handling and clock injection
- **Status:** proposed. **Serves:** R-3, NF-4, NF-6.
- **Decision:** account time zone stored as an IANA name and resolved with the platform's tz database; "local date" and
  next-run instants derive from it; the clock is injected so tests set `as-of`.
- **Revalidate when:** the host runtime's tz support differs; confirm the DST expectations in spec AC-3.5 against the
  tz database.
