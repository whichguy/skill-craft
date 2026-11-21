# Architecture decisions

Structure and technology choices for the invoice-reminder feature. Product decisions live in `spec.md` (A-n, G-n),
never here. No repository was inspected (spec G-1), so no stack is chosen; stack-specific choices are listed as open.

## Decisions

### AD-1 Derive pending reminders at each sweep instead of storing a schedule
- **Decision:** No per-invoice "scheduled reminder" records are created. Each sweep computes eligible steps from the
  invoice (status, balance, due date, open date), the account setting and the reminder log.
- **Rationale:** Payment, void and due-date edits then take effect with no cancellation or rescheduling machinery
  (R-5), and downtime recovery is the same computation (R-3 catch-up).
- **Alternatives rejected:** pre-created jobs per invoice (must be cancelled/rewritten on every invoice edit and
  settings edit).
- **Serves:** R-2, R-3, R-5.

### AD-2 The sweep is a function of an injected clock and an injected mail provider
- **Decision:** One entry point evaluates all accounts for a given instant; the clock and the provider are parameters
  with a fake for tests.
- **Rationale:** R-10: multi-day behaviour must be checkable with no waiting; failure modes need a fake provider.
- **Serves:** R-3, R-4, R-10.

### AD-3 Log row keyed `(invoice, offset)` with atomic claim before sending
- **Decision:** A unique key plus an atomic insert/update claims a step before the provider call; the row records
  attempts and outcome.
- **Rationale:** once-only under overlapping sweeps (R-4, AC-4.6). Residual window after provider acceptance is spec G-8.
- **Serves:** R-4, R-6.

### AD-4 Dates are account-local calendar dates; instants are derived with the zone database
- **Decision:** Step dates and "today" use the account time zone (UTC fallback); the due instant is 09:00 local on
  the step date, converted with a tz database so DST is honoured.
- **Serves:** R-3 (AC-3.2, AC-3.3).

### AD-5 Sweep cadence and batching
- **Decision (default, plan may refine within spec A-5):** run at least every 60 minutes; process invoices in bounded
  batches; a failure on one invoice is isolated and recorded.
- **Serves:** R-3, R-9, R-11.

## Open architecture items (not decisions)

- Runtime, language, persistence, scheduler facility, email provider and UI stack: unknown until discovery (G-1).
- Visual treatment for R-7: chosen at planning as an AD, starting from the light expressive profile unless an
  established product identity exists.
- Batch size for R-11 and the numeric production limit: unresolved (G-4).
