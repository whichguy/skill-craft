# Invoicing: payment reminders — architecture

Status: proposed by the spec stage on 2026-11-21 with no repository to inspect. Structure and technology choices live here, never
in `spec.md`. Everything below is provisional until a run with the repository confirms the stack (spec gap G-1) and the runtime
(G-11); a confirmed contradiction supersedes the decision it contradicts.

## Stack

Unknown: language, framework, store, mail provider and scheduler are not yet discovered (spec G-1, G-2, G-11). Reuse what the
invoicing product already uses for storage, email and scheduled jobs before adding anything (AD-3). No new dependency is
decided here except the one named in AD-4.

## Structure

Proposed modules (names are placeholders for the plan to fit to the repository): a pure scheduling module (due offsets and instants
from due date, configuration and clock); an evaluator that orchestrates one run (F-1 in the spec); a reminder-record store port; a
mail transport port; an invoice-reader port. Pure logic carries no I/O so the date arithmetic is testable with a fixed clock.

## Conventions

The evaluator takes the clock as a parameter; no module reads the system time directly. Instants are stored and compared in UTC.
Log events are `reminder.sent`, `reminder.failed`, `reminder.skipped`; they never carry a recipient address or message body.

## Interfaces and boundaries

Invoice store (read-only for this feature), reminder store (owned), mail provider (external), scheduler (platform). Contracts are in
the spec's "Service boundaries".

## Real-boundary checks

- Real mail delivery to a mailbox the tester controls (spec R-3.AC4). Owner: the user (provider credentials, G-2). Due: product acceptance.
- Unattended execution of the evaluator by the real scheduler without the developer's workstation (G-11). Owner: the user/deploying
  operator. Due: product acceptance.
- Concurrency uniqueness against the real reminder store (spec R-6.AC2): a local in-process lock does not prove it. Owner: implementer. Due: test stage.

## Decisions

- **AD-1 Periodic idempotent evaluator rather than one timer per invoice.** Choice: a job that, at each run, derives what is due from
  the invoice data, configuration and clock, and sends what has no record. Why: survives downtime and restarts (catch-up, spec R-2),
  needs no per-invoice scheduling state that can drift when due dates change (R-2.AC6), and is correct at any run frequency (A-10).
  Alternatives: per-invoice delayed jobs (rejected: drift on due-date edits, lost on restart); event-driven on payment only
  (rejected: reminders are time-driven). Status: proposed.
- **AD-2 Reminder record with a unique key (invoice, offset), created atomically before the send, with a lease.** Why: the record is
  both the idempotency guard and the durable work state, so no broker or outbox is needed (no dispatch gap shown). A `sending` record is
  re-claimable only after the lease expires; the provider call carries the record ID as idempotency key. The production lease length is a
  plan decision and must exceed the provider call timeout (to be taken from the provider's documentation, G-2). Alternatives: in-process
  lock (rejected: does not protect against a second process); send-then-record (rejected: a crash after send duplicates). Status: proposed.
- **AD-3 Reuse the product's existing email and scheduling facilities.** Why: add a new facility only for an unmet need. If none exists,
  the plan records the choice as a new AD. Credentials live in the platform's secret facility (alias recorded here, never the value).
  Status: proposed, pending discovery.
- **AD-4 Time zone rules come from the platform's IANA time zone database through a maintained library, never fixed offsets.** Why: spec
  NFR-5 and R-2.AC2/AC3/AC7 depend on daylight-saving correctness. The library's handling of a nonexistent local time (spec R-2.AC7) is
  an unverified claim to probe in planning with the exact expected instant `2027-03-14T07:30:00Z`. Status: proposed, claim unverified.
- **AD-5 Mail and invoice reads sit behind ports; tests use a recording transport double.** Why: lets every acceptance line in the spec
  run with a fixed clock and scripted provider results, while the real-boundary checks above cover what a double cannot. Status: proposed.

## Superseded

None.
