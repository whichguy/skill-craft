# Invoice reminders: architecture

Provisional. No repository, runtime or stack was available to the spec stage (see spec.md G-0), so each
decision below is the simplest structure that satisfies spec.md and is conditional on discovery confirming that
the runtime offers the named facility. Product behaviour is in spec.md as R-<n>; this file holds structure and
technology choices only.

## Decisions

### AD-1: Periodic evaluation, not per-invoice timers
- Decision: one scheduled job runs at a fixed cadence, computes which (invoice, step) pairs are due in each
  account's local time, and attempts them. No timer or queue entry is created per invoice.
- Why: a due date or schedule edit then needs no timer cancellation; a run that was missed is recovered by the next
  run (R-4); no broker is added without a demonstrated gap.
- Serves: R-4, R-5, R-7, R-11.
- Cadence value: unresolved (G-4.1). It must be short enough that a step is attempted inside its local calendar day
  and long enough for the runtime's scheduler limits (unknown until the runtime is identified).
- Rejected: per-invoice delayed jobs (cancel/reschedule on every due-date, pause or payment change).

### AD-2: Idempotency record keyed by (invoice, step, due date)
- Decision: the reminder log (R-10) holds at most one row per Key = (invoice id, step id, due date), enforced by a uniqueness
  constraint or conditional insert in the store. A worker claims a step by inserting that row in state `claimed`
  before it calls the mail provider, and finishes it with a conditional update from `claimed` or `retrying`.
- Why: gives send-at-most-once under repeated runs, concurrent workers and redeploys (R-5) without a distributed lock.
  A crash after the claim and before the outcome is recorded leaves `claimed`, which recovery turns into `unknown`
  rather than re-sending (R-5.3).
- Precondition to verify: the chosen store supports a conditional insert or unique key. If not, discovery must
  supply an equivalent or the requirement stays unready.

### AD-3: Eligibility is re-read from the invoice system of record immediately before each send
- Decision: selection yields candidates only. Status, balance, due date, recipient address, pause flag and account
  setting are read again from their owners at the moment of the claim and again immediately before the provider call.
  Nothing in that path is cached across runs.
- Why: payment and edits race the scheduler (R-7); a stale candidate list must not cause a reminder for a paid invoice.
- Serves: R-3, R-7, R-11.

### AD-4: Sending goes through the product's existing outbound email path if there is one
- Decision: reuse the existing transactional email facility and sender identity. A new provider is introduced only if
  discovery finds none (G-8.1). The reminder subsystem stores no provider credentials in its own tables.
- Serves: R-6, R-8.

### AD-5: The reminder subsystem never writes invoice or payment records
- Decision: it reads invoices and writes only its own settings, pause flags, log rows and suppression entries. A failure
  in it cannot fail an invoice or payment write (R-13).
