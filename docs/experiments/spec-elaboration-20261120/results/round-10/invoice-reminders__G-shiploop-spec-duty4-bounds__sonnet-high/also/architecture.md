# Architecture decisions: Invoice Reminders

Structure and technology choices live here, never in `spec.md`. No repository, discovery or research result existed when
these were written, so every decision is bounded by that evidence limit.

## Decisions

### AD-1: Scheduled evaluation owned by a headless job, not by a screen
- Status: accepted (structure); runtime and host unresolved (see AD-4).
- Decision: reminders are produced by a scheduled job that runs once per business-timezone calendar day and also
  runs on demand with an explicit as-of instant. The job is the only trigger owner. No reminder depends on a user
  being signed in or a page being open (behavioral-requirements: background work promised independently of a screen
  needs an owner that operates without that screen).
- Alternatives: event-driven timers per invoice (rejected: more state, needs per-invoice timer recovery, no benefit
  at whole-day granularity); on-page-load triggering (rejected: fails when nobody opens the app).
- Basis: request "automatic reminders" (2026-11-21); offsets are whole days (A-1 in spec summary).
- Revalidate when: the host runtime cannot run a daily scheduled job, or offsets below one day are wanted.

### AD-2: Reminder ledger keyed by (invoice, step offset) is the idempotency authority
- Status: accepted.
- Decision: a feature-owned ledger row, created by an atomic insert-if-absent keyed on `(invoice_id, step_offset)`,
  claims a step before any email is attempted. The claim winner sends; every other run or retry skips. The ledger
  never writes to the invoice record. Email delivery is at-most-once for an ambiguous outcome (R-4).
- Alternatives: at-least-once resend after a crash (rejected: an outward duplicate to a customer cannot be recalled);
  deriving "already sent" from the mail provider's history (rejected: not an authority this feature owns).
- Revalidate when: the chosen store lacks an atomic insert-if-absent / unique key.

### AD-3: Invoice data is read-only and read fresh at send time
- Status: accepted.
- Decision: the host invoice store stays the sole authority for paid/void/balance/due date/recipient. The job
  re-reads the invoice immediately before sending and never caches invoice state across runs.
- Alternatives: snapshot invoices at scan time (rejected: a payment recorded after the scan would still produce a
  dunning email).

### AD-4: Runtime, storage, email transport: unresolved
- Status: unresolved; blocks only work that needs a concrete adapter.
- What is known: nothing about the host system, language, hosting platform, store, or mail provider (no repository,
  no discovery). Selection is a discovery prerequisite (spec gap G-1).
- Constraints any choice must meet: durable store with an atomic unique key (AD-2); a scheduler that works without
  the developer's workstation; a transport that returns an accepted/rejected result per message; a secret facility
  for mail credentials; structured logs without message bodies.
- Do not choose by familiarity. Record the chosen facility, versions, identities and checks in the environment note
  when discovery finishes.

### AD-5: Reminder surface for history and per-invoice pause: unresolved
- Status: unresolved (spec gap G-6). Constraint: reuse the host's existing invoice view or admin surface if one
  exists; add no new application shell for it.
