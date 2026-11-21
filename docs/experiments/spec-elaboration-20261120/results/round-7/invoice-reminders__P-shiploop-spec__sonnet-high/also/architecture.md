# Invoicing product: architecture

How the product is built. What it must do lives in `spec.md`; this file never restates it.
Decisions are `AD-<n>`. Every decision below is **proposed**: no repository, host product or stack was
available when it was written (see `spec.md` "Sources and baseline"), so the plan confirms or revises each one
after the host system is inspected.

## Decisions

### AD-1: Periodic, idempotent evaluation instead of one timer per invoice
- **Status:** proposed. **Serves:** R-4, R-5, R-6.
- **Decision:** one recurring evaluation decides, from current invoice data, the configured schedule and the
  stored reminder records, which reminders are due. It holds no in-memory per-invoice timers.
- **Why:** a restart, a missed run or a changed due date then needs no rescheduling. The next evaluation
  recomputes what is due.
- **Alternative rejected for now:** a timer per invoice. It needs rescheduling on every due-date, schedule or
  status change, and a restart loses it.
- **Cost:** lateness is bounded by the evaluation cadence. The cadence is an unresolved bound (spec N-1).

### AD-2: The reminder record is the authority for "already handled"
- **Status:** proposed. **Serves:** R-6, R-9.
- **Decision:** the durable reminder record is keyed by (invoice, step offset). Creating the record is the
  atomic claim that a step is being handled. The store must reject a second claim for the same key. Overlapping
  evaluations, restarts and retries all go through that claim.
- **Why:** an in-process lock does not stop two processes (see GUIDES service-discovery, "Runtime state
  placement"). The store's uniqueness guarantee does.
- **Open:** the store, and whether it offers a unique key or a conditional write, are unknown until the host is
  inspected (spec G-1).

### AD-3: Send through the host's existing mail facility, behind one seam
- **Status:** proposed. **Serves:** R-7, R-8, N-6.
- **Decision:** reminders go out through whatever the host product already uses for invoice email. They cross a
  single internal interface, so that non-production environments can swap in a capture sink that cannot reach a
  real customer address.
- **Open:** the provider, whether it accepts an idempotency key, and whether it reports bounces (spec G-2).
  Nothing here assumes any of those capabilities.

### AD-4: The clock is an input
- **Status:** proposed. **Serves:** R-4, N-6.
- **Decision:** evaluation takes "now" as a parameter and can be triggered with an explicit timestamp from a
  verification harness. Acceptance lines span days, so they cannot wait on a real clock.

### AD-5: Language, runtime, hosting and job runner
- **Status:** unresolved. Chosen at planning from the host product's own stack (spec G-1). Nothing in `spec.md`
  depends on the choice.
