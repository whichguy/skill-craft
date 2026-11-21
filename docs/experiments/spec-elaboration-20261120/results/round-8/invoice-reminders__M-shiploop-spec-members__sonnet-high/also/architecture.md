# Invoicing — Payment Reminders: Architecture

How the reminder capability is built. What it must do lives in `spec.md` (`R-<n>`); this file records structure and
technology decisions only. No repository existed when these were written, so every decision is **proposed**, conditional
on gap G-1 (invoice source), G-2 (mail provider) and G-11 (scheduler runtime), and open to revision by planning.

## Decisions

### AD-1 Daily batch run, not per-invoice timers
- **Status:** proposed. **Serves:** R-3, R-4, R-12.
- **Decision:** one scheduler-triggered run per day evaluates all eligible invoices against the run's local date. No per-invoice
  timers, no queue or broker.
- **Why:** step dates are calendar dates, so a daily pass is sufficient; a missed pass self-heals through R-3's catch-up rule;
  nothing is lost when state is the durable step records. **Alternative rejected:** per-invoice scheduled jobs — more state to keep consistent
  with invoice edits (payment, due-date change) for no timing benefit.
- **Constraint:** the run takes its evaluation instant and account time zone as inputs (no direct wall-clock reads) so AC-3.x can run with a fake clock.

### AD-2 Step record with a unique (invoice, offset) key as the at-most-once guard
- **Status:** proposed; depends on the durable store chosen after G-1. **Serves:** R-6, R-8.
- **Decision:** the claim is an insert that fails if (invoice, offset) already exists; the claim is written before the provider call.
  Abandoned claims are resolved as `sent-unknown` (T-5). Provider idempotency keys, if available, are additive, not relied on.
- **Why:** gives overlapping-run and restart safety without distributed locking. **Open:** the abandonment timeout (R-12) and
  whether the chosen store supports an atomic unique insert; if it does not, planning must pick another guard and re-verify AC-6.2.

### AD-3 Ports for the invoice source, mail provider and clock
- **Status:** proposed. **Serves:** R-2, R-5, R-7, R-8, R-16.
- **Decision:** the reminder logic depends on three interfaces — `InvoiceSource` (read-only), `Mailer`, `Clock` — with real adapters and test fakes.
  The reminder component never writes invoice data.
- **Why:** keeps the invoicing system the sole authority for status/balance (spec §9), and lets all lower-layer acceptance lines run without a provider.

### AD-4 Provider credentials in the platform secret facility
- **Status:** proposed. **Serves:** R-13. Credentials are never stored in the settings record, history, logs or this repository.

### AD-5 Settings and history exposed through a small read/write API plus an admin page
- **Status:** proposed, conditional on G-8 (host UI). **Serves:** R-1, R-9, R-15.
- **Decision:** one admin-only API (settings read/save with version check; history and run reads) that the settings/history page consumes; the
  page reuses the host product's UI toolkit if one exists, otherwise the plan selects one against R-15. No new UI stack is added when a host stack exists.
- **Why:** the API is the lower-layer test surface; the page is the consumer surface.

## Not decided here
Language/runtime, storage engine, scheduler product, mail provider and UI toolkit — all pending discovery of the host system (G-1, G-2, G-8, G-11).
