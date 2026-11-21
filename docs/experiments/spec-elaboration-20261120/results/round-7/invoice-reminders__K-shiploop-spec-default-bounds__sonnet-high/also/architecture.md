# Architecture

Status: proposed. No repository was inspected, so every decision is conditional on the host stack (spec G-1) and is
confirmed or replaced by the plan.

## Decisions

- **AD-1 Periodic evaluation over per-invoice timers.** A scheduled run, at least every 60 minutes (spec A-4), computes
  which steps are due from current invoice data and the policy. Why: it makes catch-up (R-4 L3), pause/resume (R-9) and due-date
  changes (R-3 L4) fall out of one rule, needs no timer cleanup when an invoice is paid, and recovers from missed runs.
  Alternative rejected: one scheduled job per invoice step (must be cancelled or rewritten on payment, pause, due-date change).
- **AD-2 Durable reminder record with a unique key claim.** The record keyed `(invoice id, due date, offset)` is inserted by
  an atomic unique-key operation; the inserter wins the right to send. Why: gives at most one send under parallel runs
  (R-4 L2) and keeps the `sending` claim age for R-4 L4. Depends on the host store supporting unique-key insert (G-1); if it
  cannot, the plan raises a new decision.
- **AD-3 Additive storage.** `paused` and `eligible_from` are added to the invoice; if the host's invoice schema cannot be
  extended, they live in a side store keyed by invoice id. Why: smallest change to the host's existing data.
- **AD-4 Mail provider behind a narrow outbound port.** The run calls a `send(message) -> accepted | transient failure |
  permanent rejection` port; the provider is selected later (G-3). Why: lets tests use a capture sink and scripted failures
  (spec NFR-8) and keeps provider choice out of the requirements.
- **AD-5 Injected clock.** Runs take `now` as an argument. Why: R-3, R-4 and R-7 are defined by instants; they cannot be
  checked deterministically against wall-clock time.
- **AD-6 (reserved for the plan)** Concrete visual treatment of S-set and S-hist when they are a graphical UI (spec NFR-9).
