# Architecture: invoicing product (payment reminders)

Only decisions that the spec stage needs to hand to planning. The stack is not observed (no repository was available),
so every decision is **proposed** and subject to the platform discovery in G-4.

## Stack

Unknown: no repository was inspected. Discovery must record the language, framework, datastore and background-work
facility. Nothing is chosen here.

## Structure

Proposed module boundary: a *reminder subsystem* that owns settings, occurrences and the processing run. It reads
invoices and payments through the product's existing data access and sends through a mail port (AD-3).

## Conventions

None established.

## Interfaces and boundaries

- Invoice and payment data: internal and read-only for the subsystem. See `spec.md` "Service-boundary contracts".
- Outbound email provider: external, unresolved (G-3).

## Real-boundary checks

- One real send through the actual provider to a controlled mailbox (spec R-3 line 8). Owner: the delivery owner. Due
  phase: `release-verify`. A recording fake does not stand in for it.
- Background processing running in the deployed runtime with no workstation (spec R-3 line 5 in the real target). Owner:
  the platform owner (G-4).

## Decisions

### AD-1: Reminder processing runs as service-side scheduled work, independent of any UI (proposed)

- **Choice.** Due occurrences are processed by background work that runs in the deployed runtime with its own service
  authority. It does not depend on a user session, a browser or a workstation.
- **Why.** Background work promised independently of a screen needs an owner that operates without that screen. It is
  required by spec R-3 ("automatic") and R-9.
- **Alternatives.** A UI-triggered or per-request check (rejected: not automatic). A developer workstation job
  (rejected: not durable).
- **Status.** Proposed. The concrete facility waits for G-4.

### AD-2: Occurrences are durable records with a unique (invoice, offset) key, and each send is preceded by an atomic claim (proposed)

- **Choice.** An occurrence record carries a status, reason and attempt count. The unique key prevents two occurrences
  for one (invoice, offset). The claim is an atomic conditional update that only one worker can win.
- **Why.** It gives R-5 (no duplicates), R-12 (survives restart) and R-7 (history from the same record).
- **Alternatives.** An in-memory schedule (rejected: lost on restart). A queue or broker (not added: there is no
  demonstrated gap).
- **Status.** Proposed. It needs a datastore that supports a conditional write (G-1, G-4).

### AD-3: Time and outbound mail are reached through two replaceable ports (proposed)

- **Choice.** The processing logic reads time from an injected clock and sends through an injected mail port, so tests
  can set the clock and record messages.
- **Why.** The spec's acceptance lines (R-2, R-3, R-9) need a controlled clock and a recording mail boundary. The real
  provider is still checked once (Real-boundary checks).
- **Alternatives.** Testing only against the real provider (rejected: not repeatable).
- **Status.** Proposed.

## Superseded

None.
