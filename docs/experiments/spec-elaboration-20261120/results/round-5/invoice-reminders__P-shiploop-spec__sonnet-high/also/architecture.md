# Architecture decisions — Invoicing reminders

All entries are **proposed** and must be revalidated against the real repository and runtime (none were available when
written). They serve `KNOWLEDGE/spec.md`; product behaviour is defined there, not here.

## Decisions

### AD-1 Periodic evaluation pass, not per-invoice timers
- Status: proposed (revalidate when G-9 is answered).
- Decision: one recurring background pass (at least hourly, A-8) scans businesses with reminders `on`, derives each
  invoice's latest due offset from its due date, and sends. Nothing is scheduled per invoice.
- Why: offsets derive from the due date, so due-date changes, payments and voids need no timer cancellation; recovery after
  downtime is the same code path as normal operation (spec R-2 outage case, R-9). Reuse an existing scheduler if the
  runtime has one; add none otherwise without a demonstrated gap.
- Alternatives considered: per-invoice delayed jobs (rejected: must be cancelled or rebuilt on every edit/payment); a
  broker or queue (rejected: no demonstrated dispatch gap; spec needs only durable claims).
- Revalidate if: the runtime has no unattended scheduling facility, or invoice volume makes a full scan too slow.

### AD-2 Durable slot record with a uniqueness rule is the idempotency authority
- Status: proposed (store capability unknown).
- Decision: the reminder slot record keyed (invoice id, offset) is created as a claim before the provider call, relying on
  an atomic uniqueness/conditional-create guarantee of the existing store; final outcomes are written conditionally on
  the claim. Provider idempotency keys may be added but are never relied on (G-5).
- Why: R-5 requires no duplicates across overlapping passes and restarts without exactly-once assumptions.
- Owner/location: the invoice's data store; invoice and setting stores are read, not copied.
- Revalidate if: the store cannot provide a unique/conditional write; then a lock or lease design is needed and R-5's check
  must be re-planned.

### AD-3 Clock and mail facility behind replaceable boundaries
- Status: proposed.
- Decision: evaluation takes the current time and the business time-zone conversion from an injectable clock, and sends
  through an adapter around the product's existing mail facility.
- Why: NFR-6, and the controlled-clock and mail-double checks in TC-4..TC-20; also keeps the facility swappable.
- Revalidate if: the product has no mail facility (then a prerequisite item to establish one comes before R-3's checks).

### AD-4 Message templates are code-owned constants for this scope
- Status: proposed.
- Decision: the subject and body templates in R-3 are fixed constants versioned with the product, not editable data.
- Why: schedule and wording editing are out of scope; this avoids a template store and its security surface.
- Revalidate if: the user asks for editable wording or localisation.
