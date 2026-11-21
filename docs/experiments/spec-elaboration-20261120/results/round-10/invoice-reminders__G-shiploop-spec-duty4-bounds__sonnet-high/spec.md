# Invoice Reminders: product specification

Product: automatic payment reminders for unpaid invoices. This document is the maintained home of the product's
requirements; later requests add to it, they do not replace it.

## Request log

| Date | Source (verbatim) | Effect |
| --- | --- | --- |
| 2026-11-21 | "Set up automatic reminders for unpaid invoices." | Adds R-1 to R-10 and NFR-1 to NFR-8. No earlier spec existed, so nothing is preserved, changed or retired. |

Evidence limits: no repository, discovery result, research result, selected baseline or earlier spec exists. The host
invoicing system, its runtime, storage and mail transport are **unknown**. Nothing below claims observed behaviour of
any existing system. Every R- is proposed intent from the request above; every observation is `none`.
Method sources: `GUIDES/behavioral-requirements.md#behavior-model`, `#traceability-and-review`,
`GUIDES/requirements-definition.md`, `GUIDES/service-discovery.md`.

## Request outcomes and traceability

| Outcome (from the request) | Acceptance lines |
| --- | --- |
| O-1 reminders go out automatically, without a person triggering each one | AC-1.1, AC-2.1, AC-4.1, AC-6.1, AC-6.2 |
| O-2 only for invoices that are unpaid | AC-2.2, AC-2.3, AC-5.1, AC-5.2, AC-5.3 |
| O-3 "set up": the business can turn the behaviour on and control when reminders go | AC-1.1 to AC-1.4, AC-9.1 |
| Implied by O-1: the customer actually receives something usable | AC-3.1, AC-3.2, AC-3.3 |
| Implied by O-1: it keeps working and can be audited | AC-7.1, AC-8.1, AC-10.1 |

Domain rules the request leaves out are bounded under the R- they limit (see "Out of scope" under R-3, R-6, R-7, R-9).

## Actors and channels (compact trace)

| Actor | Interaction / channel | State owner | Observable outcome |
| --- | --- | --- | --- |
| Business owner (admin of the host system) | configure schedule, timezone, effective date; pause an invoice; read history (surface open: G-6) | feature-owned configuration and ledger | schedule accepted or rejected; history lists reminders |
| Scheduler (system, no screen) | daily trigger, or explicit run with an as-of instant, to the evaluation job | job; ledger | run record with counts; reminders sent |
| Job to host invoice store | read-only query for open invoices, fresh read before each send | host invoice store (authority for paid, void, balance, due date, recipient) | job never mutates invoices |
| Job to mail transport | one message per claimed step; accepted or rejected result | mail provider (delivery); ledger (our record of the result) | customer's mailbox receives the reminder |
| Customer (invoice billing contact) | receives email | none | reminder content per R-3 |

Channel choices: scheduler to job is a local scheduled call; job to invoice store is request/response; job to mail
transport is request/response where "accepted" means only that the provider took the message, not that it was
delivered or read (R-4, service boundary S-2). No queue or broker is introduced (AD-1).

## Requirements

Every R- below carries: basis, preserved/changed behaviour, source-section locators, evidence limits, pending
implementation and checks. Common to all: basis is the request of 2026-11-21 quoted above; preserved behaviour: none
(new product, no baseline); changed behaviour: none; source-section locators: no baseline source exists, method
locators are listed in the header; implementation: not started; checks: planned only, none run.

### R-1 Reminder schedule setup
Behaviour: the owner defines the reminder schedule as an ordered list of integer day offsets from an invoice's due
date (0 = due date, positive = days after, negative = days before), an `effective_from` date, and the business
timezone (IANA name). The feature is enabled only when a valid non-empty schedule and a timezone are saved.
Boundaries: offsets must be integers, strictly increasing (so at most one step per invoice per calendar day, which is
the only per-day volume bound this feature introduces). There is no cap on the number of steps and no range limit on
an offset: the request states none, and the one-per-day rule already prevents same-day repeats. `effective_from`
defaults to the date the schedule is saved, in the business timezone; the owner may set an earlier date (to include
a backlog, R-6) or a later one. Saving a schedule edit sets `effective_from` the same way, so steps whose scheduled
date is already past at the edit are not sent retroactively.
Error behaviour: an invalid schedule (non-integer, duplicate, not strictly increasing, unknown timezone name,
unparseable date; an empty list is not rejected, it simply leaves the feature disabled) is rejected with a message naming the first offending value;
the previously saved schedule stays active and unchanged. With no saved schedule or no timezone the feature is
disabled: no reminders are sent and the run record (R-10) states the reason `not-configured`. Fail closed.
Consumer outcome: the owner sees whether reminders are on, the saved schedule and `effective_from`.
Out of scope: per-customer schedules, per-invoice schedules, templates per step, business-day or holiday calendars,
late fees, escalation to collections.
Open: G-2 (no default offset values are shipped; the owner supplies them).

- AC-1.1 Positive. Given no schedule, when the owner saves offsets `[3, 10]`, timezone `UTC`, `effective_from`
  2026-03-01, then the configuration reads back exactly those values and the next run evaluates invoices under them.
  Surface: configuration read-back through the surface chosen for G-6 (until chosen: the configuration store).
  Confirmed by: automated test reading the saved configuration, then an explicit run as of 2026-03-04T00:00Z.
- AC-1.2 Failure. Saving `[10, 3]`, `[3, 3]`, `[3.5]`, `["x"]` or timezone `Mars/Base` each returns a rejection naming
  the offending value (`10` after `3` out of order, `3` duplicated, `3.5`, `"x"`, `Mars/Base`) and leaves the saved
  `[3, 10]` unchanged. Confirmed by: automated test per input asserting the error text names the value and the
  stored configuration is byte-identical before and after.
- AC-1.3 Boundary. `[]` (empty) or an absent timezone leaves the feature disabled: a run as of 2026-03-04T09:00Z with
  an eligible overdue invoice sends 0 emails and the run record says `not-configured`. `[-2, 0, 7]` is accepted.
  Confirmed by: automated test counting sends at the mail-transport fake.
- AC-1.4 Boundary. Saving a schedule on 2026-03-04 (business timezone) with no explicit date sets `effective_from` to
  2026-03-04; an explicit `effective_from` of 2026-01-01 is stored as given. Confirmed by: configuration read-back.

### R-2 Daily evaluation and eligibility
Behaviour: once per business-timezone calendar day the job evaluates every invoice and decides, per invoice, whether
a reminder step is due. An invoice is eligible only if all hold at evaluation time: it has an outstanding balance
greater than zero, its status is not draft, void or written off, it has a due date, and it is not paused (R-9).
The business-timezone calendar date of the as-of instant is "today"; "step N is due" means due date + N days is on or
before today and on or after `effective_from`.
Boundaries: the day boundary is local midnight in the business timezone, not UTC. Invoices with no due date are never
reminded (recorded as skipped `no-due-date` in the run counts). An invoice with a zero or negative balance (credit)
is not eligible.
Error behaviour: if the invoice store cannot be read, the run sends nothing, records `source-unavailable`, and leaves
all steps due for the next run (nothing is lost, R-6). A single invoice that fails to evaluate does not stop the
others.
Consumer outcome: customers of eligible overdue invoices receive reminders; no one else does.
Out of scope: multi-currency conversion (amounts are shown in the invoice's own currency, unconverted); grouping
several invoices of one customer into one email.
Open: G-1 (invoice source, status vocabulary mapping and field names unknown).

- AC-2.1 Positive. Fixture: schedule `[3, 10]`, `effective_from` 2026-03-01, timezone `UTC`; invoice INV-1001, status
  open, due 2026-03-01, balance 250.00 USD, contact `ap@example.com`. A run as of 2026-03-04T09:00Z sends exactly one
  email for INV-1001 step 3. Surface: mail-transport fake (outbox). Confirmed by: automated test asserting one
  message, recipient, step, ledger row `sent`.
- AC-2.2 Failure. The same fixture with INV-1002 status `void`, INV-1003 status `draft`, INV-1004 balance 0.00, and
  INV-1005 with no due date: a run as of 2026-03-04T09:00Z sends nothing for them; run counts show 4 skipped with
  reasons. Confirmed by: automated test over all four.
- AC-2.3 Boundary (timezone). Timezone `UTC`, run as of 2026-03-03T23:59:59Z: nothing sent (local date 2026-03-03,
  step 3 falls on 2026-03-04). As of 2026-03-04T00:00:00Z: step 3 sent. With timezone `Pacific/Auckland` (UTC+13 on
  that date), 2026-03-03T11:00:00Z is local 2026-03-04T00:00 and step 3 is sent, whereas the same instant under `UTC`
  sends nothing. Confirmed by: automated test with injected clock, three runs.
- AC-2.4 Failure. Invoice store unreachable during a run as of 2026-03-04T09:00Z: 0 sent, run record
  `source-unavailable`, and a later run as of 2026-03-04T15:00Z with the store back sends INV-1001 step 3 once.
  Confirmed by: automated test with a store fake that fails once.

### R-3 Reminder message and recipient
Behaviour: each reminder is one email to the invoice's billing contact address, taken from the invoice's customer
record at send time. It states: business name, invoice number, outstanding balance with currency, due date
(`YYYY-MM-DD`), and the timing line computed from true age (today minus due date in the business timezone), not from
the step offset. It also carries a plain-text body. If the host exposes a payment link for the invoice it is included,
otherwise the message omits it.
Default wording (A-8, reversible): subject `Reminder: invoice INV-1001 is 3 days overdue`; `... is due today` at age 0;
`... is due in 2 days` when due date is in the future; singular `1 day`.
Boundaries: one invoice per email; one recipient address; no CC or BCC to the owner.
Error behaviour: a missing or syntactically invalid recipient address means no send; the step is recorded
`skipped_no_recipient` with no retry for that step (a later step uses the then-current address). A mail-transport
rejection follows R-7.
Consumer outcome: the customer can tell which invoice, how much, since when, and whom to contact.
Out of scope: localization, per-customer tone, attachments (such as a PDF of the invoice), open or click tracking, SMS
or other channels, customer opt-out or unsubscribe handling beyond R-9's owner-side pause.
Open: G-4 (sender identity, reply-to and payment link availability are unknown prerequisites).

- AC-3.1 Positive. For AC-2.1's send, the outbox message has recipient `ap@example.com`, subject
  `Reminder: invoice INV-1001 is 3 days overdue`, and body (text part) containing `INV-1001`, `250.00 USD`,
  `2026-03-01`, `3 days overdue`. Confirmed by: automated test with exact-string assertions on each.
- AC-3.2 Failure. INV-1006 with no contact address, run as of 2026-03-04T09:00Z: 0 emails, ledger row for step 3
  `skipped_no_recipient`; a malformed address `ap@` behaves the same. On 2026-03-05 the owner fixes the address: still
  0 emails for step 3 (no retry); on 2026-03-11 step 10 is sent to the fixed address. Confirmed by: automated test
  across the three dates.
- AC-3.3 Boundary. Timing line: age 0 gives `is due today`; age 1 gives `is 1 day overdue`; due in 2 days gives
  `is due in 2 days` (schedule `[-2, 0, 7]`, due 2026-03-01, run as of 2026-02-27). A balance of 100.00 on an invoice
  of 250.00 (partial payment) shows `100.00 USD`, never 250.00. Confirmed by: automated test, exact-string match.

### R-4 At most one reminder per invoice per step
Behaviour: before any email is attempted the job atomically claims `(invoice, step offset)` in the ledger. Only the
claim winner sends. A step in state `sent`, `sending`, `unknown`, `skipped_missed` or `skipped_no_recipient` is never
sent again. A `sending` claim made on an earlier business-timezone calendar day than today, with no recorded result,
becomes `unknown` and is never resent automatically (A-5: an unrecallable duplicate to a customer is worse than a
missed reminder). A `sending` claim made today is left alone: another run may still be working.
Boundaries: re-running the job the same day, two overlapping runs, and a crash between claim and recording are all
covered; the identity is the step offset, so editing the schedule does not re-send a step already sent under the same
offset.
Error behaviour: if the ledger cannot be written, no email is sent for that step (claim first, send second).
Consumer outcome: a customer never receives the same step twice; the owner sees `unknown` steps listed for manual
follow-up.
Out of scope: guaranteeing exactly-once delivery by the mail provider (the feature cannot observe it, S-2).

- AC-4.1 Positive. Fixture of AC-2.1. After step 3 is sent as of 2026-03-04T09:00Z, a second run as of
  2026-03-04T15:00Z sends 0 emails and the ledger still has exactly one row for `(INV-1001, 3)`.
- AC-4.2 Failure (concurrency). Two runs started together as of 2026-03-04T09:00Z against one ledger send exactly one
  email in total; the loser's counts show 1 skipped `already-claimed`. Confirmed by: automated test with two
  concurrent workers against the real ledger store (a single-threaded fake does not satisfy this line).
- AC-4.3 Failure (crash). Claim written, process killed before the result is recorded, restart the same day (as of
  2026-03-04T15:00Z): 0 further emails, row still `sending`. Run as of 2026-03-05T09:00Z: row becomes `unknown`, 0
  emails for step 3, and nothing blocks step 10 on 2026-03-11. Confirmed by: automated test with an injected crash
  after the claim.
- AC-4.4 Failure (ledger down). Ledger write fails: 0 emails, run record shows `ledger-unavailable` for that
  invoice. Confirmed by: automated test with a failing ledger fake.
- AC-4.5 Boundary. Schedule edited from `[3, 10]` to `[3, 7, 10]` after step 3 was sent: step 3 is not re-sent;
  step 7 becomes due only if its date is on or after the new `effective_from`.

### R-5 Stop when no longer unpaid
Behaviour: the job re-reads the invoice immediately before each send (AD-3). If at that moment the invoice has no
outstanding balance, or is void, written off, or paused, nothing is sent and no further reminders are produced for it.
A partial payment reduces the balance that is shown and does not stop reminders while any balance remains. An invoice
that is later reopened (balance above zero again) resumes under R-2 and R-6 rules, with already-recorded steps still
in force.
Boundaries: the check is per send, not per run, so a payment recorded between the scan and the send stops that send.
Error behaviour: if the fresh read fails, that invoice is skipped this run (`source-unavailable`) and stays due.
Consumer outcome: a customer who has paid is not chased.

- AC-5.1 Positive. INV-1001 paid in full on 2026-03-02: runs on 2026-03-04 and 2026-03-11 send 0 emails.
- AC-5.2 Failure (race). INV-1001 is selected as due at 09:00Z on 2026-03-04, a payment of 250.00 is recorded before
  the send step, the fresh read sees balance 0.00: 0 emails, no ledger `sent` row. Confirmed by: automated test whose
  store fake changes the balance between scan and fresh read; the check in the product must be real (the fake cannot
  be what stops the send).
- AC-5.3 Boundary. Balance 250.00 reduced to 100.00 on 2026-03-02: step 3 on 2026-03-04 is sent showing `100.00 USD`;
  balance 0.00 on 2026-03-10: step 10 on 2026-03-11 is not sent.

### R-6 Timing window, catch-up and backlog
Behaviour: a step is eligible when its scheduled date (due date + offset) is on or before today and on or after
`effective_from`. If several steps are eligible and unrecorded at one evaluation (for example after missed days), only
the latest eligible step is sent; each earlier one is recorded `skipped_missed` and never sent. After the last step
has been recorded no further reminders are produced for that invoice (the schedule is finite).
Boundaries: steps scheduled before `effective_from` are never sent; a newly saved schedule does not mass-mail existing
overdue invoices unless the owner sets `effective_from` back (A-3, a deliberate safeguard against an outward burst).
Error behaviour: a missed run is recovered by the next run with no manual step.
Consumer outcome: reminders arrive on or just after their scheduled day, at most one per invoice per day.
Out of scope: sending every missed step; resuming a step after a later one has been sent.

- AC-6.1 Positive. Fixture schedule `[3, 10]`, INV-1001 due 2026-03-01, `effective_from` 2026-03-01. Runs on
  2026-03-04 (step 3 sent), 2026-03-11 (step 10 sent), 2026-03-12 (nothing), and every later day (nothing).
- AC-6.2 Failure (missed days). No run until 2026-03-12T09:00Z: exactly one email, step 10, subject
  `Reminder: invoice INV-1001 is 11 days overdue`; ledger has `(INV-1001, 3) skipped_missed` and `(INV-1001, 10) sent`.
- AC-6.3 Boundary (backlog). INV-1007 due 2026-01-01, `effective_from` 2026-03-01, run as of 2026-03-04T09:00Z: 0 emails
  (step dates 2026-01-04 and 2026-01-11 precede `effective_from`). With `effective_from` 2026-01-01: one email, step 10,
  `... is 62 days overdue`, and step 3 recorded `skipped_missed`. (2026-03-04 minus 2026-01-01 = 62 days.)
- AC-6.4 Boundary (dates). A step landing exactly on `effective_from` is eligible; one day earlier is not.

### R-7 Send failure and retry
Behaviour: when the mail transport rejects or errors, the step is recorded `failed` with the reason, no `sent`
state, and it is retried on each following daily run while it remains the latest eligible step and the invoice is still
eligible. When a later step becomes eligible the failed step is no longer retried and stays `failed`; the later step
is sent under R-6. Retries use the same claim identity (conditional change `failed` to `sending`), so a retry cannot
duplicate a step that actually succeeded.
Boundaries: for any step that has a following step, the retry window is bounded by the schedule itself (it ends the
day before the next step's scheduled date), so no new numeric limit is introduced. **For the last step the retry
bound is open (G-3)**; work on that clause is unready, and the rest of R-7 is ready.
Error behaviour: the mail-transport credentials missing or invalid fail the whole run with `transport-unavailable`;
no step is marked `sent`; steps stay due for the next run.
Consumer outcome: a transient outage delays the reminder rather than dropping it; the owner can see failed steps.

- AC-7.1 Positive. Step 3 rejected by the transport on 2026-03-04, accepted on 2026-03-05: one email delivered on
  2026-03-05, ledger `sent`, attempts recorded as 2.
- AC-7.2 Failure. Transport rejects step 3 on 2026-03-04 and every day through 2026-03-10: attempts on each of those
  seven days, state `failed`. On 2026-03-11 step 10 is the latest eligible step: step 10 is sent, step 3 is not retried.
- AC-7.3 Boundary. Transport accepted the message but the response was lost (timeout): outcome is unknown, handled as
  AC-4.3 (`unknown`, not resent).
- AC-7.4 NOT SPECIFIED until G-3 is resolved: last-step retries after 2026-03-11 with continuing failures.

### R-8 Reminder history is visible to the owner
Behaviour: for any invoice the owner can see each ledger row: step offset, scheduled date, state (`sent`, `failed`,
`unknown`, `sending`, `skipped_missed`, `skipped_no_recipient`), attempt count, last-attempt timestamp, the mail
provider's accepted-message identifier when present. `unknown` and `failed` rows are distinguishable at a glance and
can be listed across invoices.
Boundaries: read-only; no edit or manual resend in this scope.
Error behaviour: an invoice with no reminders shows an empty history, not an error.
Consumer outcome: the owner can answer "did the customer get a reminder, and when?" without reading logs.
Open: G-6 (the surface: host invoice view, report, or API).

- AC-8.1 Positive. After AC-6.1, the history of INV-1001 lists `(3, sent, 2026-03-04)` and `(10, sent, 2026-03-11)`.
  Failure. `unknown` and `failed` rows appear in the cross-invoice list after AC-4.3 and AC-7.2.
  Boundary. INV-1008 with no reminders returns an empty list. Surface: the G-6 surface; until chosen, the ledger read
  interface. Confirmed by: automated read test plus one real-surface check when G-6 is decided.

### R-9 Pause and resume reminders for one invoice
Behaviour: the owner can pause reminders for a single invoice (for example one in dispute) and resume them. A paused
invoice is not eligible (R-2) and no steps are recorded for it while paused. On resume, R-6 applies as if the days
had been missed: only the latest eligible step is sent on the next run, earlier ones are `skipped_missed`.
Boundaries: pause state belongs to this feature, keyed by invoice id; the host invoice is not modified (A-7).
Error behaviour: pausing an unknown invoice id is rejected with a not-found error and changes nothing; pausing an
already-paused invoice is a no-op with a success response.
Consumer outcome: a disputed invoice is not chased while paused.
Out of scope: customer-level pause, bulk pause, scheduled pause end date.

- AC-9.1 Positive. Pause INV-1001 on 2026-03-02; runs on 2026-03-04 send 0 emails for it; resume on 2026-03-12: next run
  sends step 10 only (subject `... is 11 days overdue`; 2026-03-12 minus 2026-03-01 = 11) and step 3 is `skipped_missed`.
  Failure. Pause `INV-9999` (absent) returns not-found and the pause set is unchanged.
  Boundary. Pausing twice leaves one pause record; resuming a not-paused invoice is a no-op.
  Confirmed by: automated test over the three cases.

### R-10 Run record and observability
Behaviour: every run, including a disabled run, writes one run record: run id, as-of instant, business date, outcome,
counts of invoices evaluated, sent, skipped by reason, failed, unknown, and any run-level failure reason
(`not-configured`, `source-unavailable`, `transport-unavailable`, `ledger-unavailable`). Run-level failures are
visible in the same place as history (R-8).
Boundaries: log lines and run records never contain the email body, and recipient addresses are masked
(`a***@example.com`). Required run records are not removed by log-level changes.
Error behaviour: if the run record cannot be written the run still completes its sends (the ledger is the send
authority) and the failure is reported to the platform's error output; sending is never blocked by diagnostics.
Consumer outcome: an operator can tell from the record whether yesterday's run happened and what it did, and a
missing run is detectable (no record for a business date).
Open: G-6 (whether an owner notification on a failed or missing run is wanted, and over which channel).

- AC-10.1 Positive. After AC-6.1's 2026-03-04 run the record has evaluated >= 1, sent = 1, outcome `ok`. Failure. After
  AC-2.4 the record shows `source-unavailable`. Boundary. After AC-1.3 the record shows `not-configured`, sent = 0.
  Privacy check: captured log output of AC-3.1's run contains neither the body text `3 days overdue` nor the full
  address `ap@example.com`; it contains `a***@example.com`. Confirmed by: automated test over captured log output.

## Non-functional requirements

Basis for all NFRs: the request (2026-11-21) and the lifecycle duties of `GUIDES/requirements-definition.md`. No bound
below is invented; a bound with no supporting evidence is listed as unresolved.

- NFR-1 Reliability and restart. The daily run must complete correctly without the developer's workstation and without
  any user session; after a process or host restart the next run recovers all unsent due steps (R-6, R-4). Pass
  criterion: AC-4.3 and AC-2.4 pass against the deployed runtime, not only a local fake. Verification: restart test on
  the real runtime once AD-4 is resolved.
- NFR-2 Testability. Evaluation takes an explicit as-of instant and timezone so every AC- above is replayable without
  waiting; the mail transport and invoice source are replaceable at their boundary only (the claim, re-check and
  eligibility logic run for real). Pass criterion: AC-2.3 passes using an injected clock.
- NFR-3 Privacy and security. Personal data handled: customer name, email address, invoice amounts. The ledger stores
  invoice id, step, state, timestamps, attempt count, provider message id and a masked address, never the body or the
  full address. Credentials for the mail transport come from the platform's secret facility, never from code, the
  ledger or logs. Only the owner role can read history, change the schedule, or pause an invoice. Retention of ledger
  and run records is open (G-7). Verification: AC-10.1 privacy check; an authorization test that a non-owner request
  to AC-1.1, AC-8.1 and AC-9.1 surfaces is refused with no change.
- NFR-4 Volume and runtime limits. **Unresolved** (G-5): the number of invoices, the mail provider's send quota and rate,
  and the runtime's maximum job duration are unknown, so no numeric bound is stated. Observable behaviour that does
  not need a number: invoices are processed in a deterministic order (due date ascending, then invoice id); if a run
  stops early at any runtime or provider limit, every unprocessed invoice's due steps stay unrecorded and are handled
  by the next run under R-6, none is lost or duplicated, and the run record says `incomplete` with the count
  remaining. Verification: a test that stops a run after N invoices and finishes it with a second run.
- NFR-5 Operability. Run records (R-10) are the operational interface; a business date with no run record is the
  signal that the scheduler failed. Alerting channel is open (G-6). Rollback: disabling the feature is clearing the
  schedule (R-1), which stops all sends from the next run; sent emails cannot be recalled.
- NFR-6 Compatibility. Unresolved (G-1): supported runtime, language, store and mail provider are unknown. No
  compatibility claim is made.
- NFR-7 Interface quality (conditional). The request names no interface, and the surface for history, configuration and
  pause is open (G-6). If the plan delivers a graphical interface for them, this requirement applies in full:
  a deliberately designed, polished interface, not unstyled scaffolding, with a consistent visual system (spacing and
  type scales; a palette with a light and a dark theme, light first); designed empty, loading and error states (the
  empty history of AC-8.1, a pending save, a rejected schedule of AC-1.2); a layout that works at 360 px and 1280 px
  with no horizontal overflow; visible focus states and WCAG AA contrast; motion only where it explains a change and
  honoring reduced motion; one icon set. Visual reference and starting appearance: the light Gemini-like Material 3
  Expressive profile in `GUIDES/platforms/ui.md#light-expressive-starting-point`, yielding to any established host
  product identity and platform conventions, which take precedence. If the host already has an invoice view, the new
  surfaces inherit its identity. If the surface is an existing admin screen or an API only, this is n/a for that
  surface. The plan chooses the concrete treatment.
- NFR-8 Message accessibility and deliverability. The email has a plain-text body (R-3). Authentication of the sender
  domain and a deliverability target are unknown prerequisites (G-4); no deliverability rate is claimed.

## State and data assessment

| Resource | Owner and location | Changed / observed | Before and after invariant | Recovery | Checks |
| --- | --- | --- | --- | --- | --- |
| Invoice records (balance, status, due date, contact) | host invoicing system (G-1) | observed only | never written by this feature; reads always fresh | n/a (no writes) | AC-5.2; contract test that no write call is made |
| Schedule configuration (offsets, `effective_from`, timezone) | this feature, durable store (AD-4) | changed by owner | after a rejected save the old value is byte-identical; after an accepted save the value is valid per R-1 | last good value retained on any rejected save | AC-1.1 to AC-1.4 |
| Reminder ledger, key `(invoice id, step offset)` | this feature, durable store with a unique key (AD-2) | created by the job | at most one row per key; a `sent` row is never changed back; `failed` can go to `sending` only by conditional change | `sending` older than today becomes `unknown` | AC-4.1 to AC-4.5, AC-7.1 to AC-7.3 |
| Pause set, key invoice id | this feature, same store | changed by owner | at most one record per invoice | none needed (idempotent set and clear) | AC-9.1 |
| Run records | this feature, same store or the platform log | created by every run | one record per run | write failure never blocks sending (R-10) | AC-10.1 |
| Sent email | mail provider and customer mailbox | created, cannot be recalled | n/a | compensation limit: none; a mistaken send cannot be undone | AC-2.1, AC-4.2 |

Unknowns (not guessed): store type and its transactional guarantees (an atomic unique insert and a conditional update
are required by AD-2; if the store cannot give them the plan must raise it); the invoice store's concurrency behaviour
for the fresh read; whether the host has native pause or on-hold status (A-7 revalidation).
No migration of existing data is needed beyond creating the feature's own tables; existing host data is untouched.
Concurrent runs are the contention case: independent invoices do not contend, the shared hot spot is the single
configuration record, read-only during a run.

## Service boundaries

| Boundary | Current authority | Freshness and revocation | Incremental state | Async completion and recovery | Owned event coverage |
| --- | --- | --- | --- | --- | --- |
| S-1 Job to host invoice store | host store is the only authority for paid, void, balance, due date and recipient | no cache; re-read immediately before each send, so a payment recorded after the scan stops the send (R-5); the runtime identity must have read-only access (G-1: whether it does is unknown, not assumed) | none: no invoice state is kept between runs | synchronous request and response; an unavailable read leaves the step due (AC-2.4) | run record counts; `source-unavailable` |
| S-2 Job to mail transport | the transport's "accepted" is the only success signal we can hold; delivery and bounces are not observed | n/a | the ledger records `sending` before the call and the result after | an accepted message may still bounce; a lost response is `unknown` and not resent (AC-4.3, AC-7.3); delivery events and bounce handling are out of scope (the request does not ask; revalidate if bounces to the same address become a problem) | per-step state in the ledger; run record `transport-unavailable`; logs without bodies |
| S-3 Scheduler to job | the platform scheduler (AD-4) | each run takes its own as-of instant; a late trigger changes nothing but timing | none | a missed trigger is detectable by an absent run record and recovered by the next run (R-6) | run record per business date |
| S-4 Owner to configuration, history, pause | the owner role of the host (G-1) | every request is authorized against the current role at request time; not cached | none | synchronous | rejected-save and refused-access outcomes are logged without values of secrets |

No service is added beyond these; no queue, broker or cache is introduced (AD-1, AD-3).

## State and information lifecycle

| State | Owner and location | Who may read | Simultaneous changes | What ends it | Runtime quotas met |
| --- | --- | --- | --- | --- | --- |
| Schedule configuration | this feature's store | owner role | last accepted save wins; each save is validated whole, so no partial schedule exists | replaced by a later save; cleared by the owner (disables the feature) | unknown (G-5) |
| Ledger rows | this feature's store | owner role; never exposed to customers | unique key plus conditional updates (AD-2); losers skip | removed with the invoice if the host deletes it; otherwise retention open (G-7) | unknown (G-5) |
| Pause set | this feature's store | owner role | idempotent set and clear; last write wins | resume, or removal with the invoice | unknown |
| Run records | this feature's store or platform log | owner role and operators | append-only, one per run | retention open (G-7) | log volume: one record per day |
| Recipient email address and amounts | host store (source); copied only into the outgoing email | the recipient; the host's own readers | n/a | ledger keeps only a masked address; nothing else is stored | n/a |
| Mail credentials | platform secret facility | job runtime identity only | n/a | rotated by the platform | n/a |

Personal data: the full address is shown only inside the outgoing message; stored only as a masked form in the ledger
and logs; kept as long as the ledger row (G-7); removed with the invoice or by the retention decision. No customer
identity, sharing or login is added; the feature uses the host's owner role as is. Interaction premises for any UI:
the component set is the host's, the interaction model is read-then-act with truthful pending state (a save shows
`Saving` until the store confirms, then the read-back values; a rejected save keeps the draft visible with the error),
the skin is the host's (NFR-7).

## Flows and transition ledger

Flows: F-1 configure (R-1); F-2 daily run (R-2, R-4, R-5, R-6, R-7, R-10); F-3 pause and resume (R-9); F-4 read history (R-8).

F-2 sequence: scheduler triggers the job with an as-of instant; job reads configuration (disabled if absent: record
`not-configured`, stop); job lists candidate invoices; for each, in due-date-then-id order: fresh read and R-5 check,
compute eligible steps, claim latest step (T-1) or record skips (T-5); send; record result (T-2, T-3); finish with the
run record. Branches: source unreadable (stop, `source-unavailable`); ledger write fails (skip invoice,
`ledger-unavailable`); transport rejects (T-3).

Ledger-row state machine: absent, `sending`, `sent`, `failed`, `unknown`, `skipped_missed`, `skipped_no_recipient`.
Initial: absent. Terminal: `sent`, `unknown`, `skipped_missed`, `skipped_no_recipient`; `failed` accepts retry (T-6) until superseded.

| ID | R- / F- | Before | Trigger and guard | Operation | After | Failure and recovery | Case |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-1 | R-4 / F-2 | absent | run; step is the latest eligible; fresh read shows eligible; recipient valid | atomic insert of the claim | `sending` | insert rejected means another run owns it: skip, no email | AC-4.2, AC-4.4 |
| T-2 | R-4, R-3 / F-2 | `sending` | transport accepted | record result and message id | `sent` | result write fails: row stays `sending`, becomes `unknown` next day | AC-2.1, AC-4.3 |
| T-3 | R-7 / F-2 | `sending` | transport rejected | record reason and attempt count | `failed` | retried by T-6 | AC-7.1, AC-7.2 |
| T-4 | R-4 / F-2 | `sending` | claim made on an earlier business date, no result | mark | `unknown` | never auto-resent; listed for the owner | AC-4.3 |
| T-5 | R-6 / F-2 | absent | an earlier eligible step exists when a later one is eligible | insert | `skipped_missed` | none | AC-6.2 |
| T-6 | R-7 / F-2 | `failed` | still the latest eligible step; invoice eligible | conditional change to `sending`, increment attempts | `sending` | conditional failure means skip | AC-7.1 |
| T-7 | R-3 / F-2 | absent | recipient missing or invalid | insert | `skipped_no_recipient` | none | AC-3.2 |
| T-8 | R-5 / F-2 | absent | fresh read shows no balance, void, written off, or paused | nothing | absent | none | AC-5.1, AC-5.2 |

Forbidden and invalid events: a send for a step in any terminal state is refused with no effect (R-4); sending when
the feature is disabled does nothing and records `not-configured`; a `sent` row cannot be reopened. A repeated run is a
no-op for already recorded steps, not a repeat of side effects.

## Open gaps

- G-1 (R-2, R-5, R-8, S-1, S-4, NFR-6): the host invoicing system, its runtime, store, status vocabulary, due date, recipient
  fields, owner role and the job's identity and read access are unknown. No discovery ran. Needed before any adapter is
  built. Planning can proceed against an abstract invoice-source contract with exactly these fields: invoice id, number,
  status, due date, outstanding balance, currency, billing contact address, optional payment link.
- G-2 (R-1): the default offset values. The user did not say how many reminders or on which days, and no evidence in
  hand supports a value. Until the owner supplies it the feature stays disabled (fail closed, AC-1.3). Acceptance runs
  against the fixture schedules `[3, 10]` and `[-2, 0, 7]`, which are test inputs, not shipped defaults.
- G-3 (R-7): retry bound for the last step. Unknown. Affects only AC-7.4.
- G-4 (R-3, NFR-8): sender identity (from and reply-to address, authenticated domain), whether the host gives a payment
  link, and message branding. Prerequisite for real sends; acceptance with a transport fake is unaffected.
- G-5 (NFR-4): invoice volume, mail provider quota and rate, runtime maximum duration.
- G-6 (R-8, R-10, NFR-5, NFR-7): surface for configuration, history and pause, and whether a failed or missing run should
  notify the owner and how.
- G-7 (NFR-3): retention period for ledger and run records.

## Retired

None. No earlier requirement existed.

## Evidence of replay (duty 10)

Cases AC-2.1, AC-2.3, AC-6.1 to AC-6.3, AC-5.1, AC-1.3, AC-3.2 and AC-9.1 were walked by hand from their stated start.
Start reachable: the owner saves a schedule (R-1, owner role per G-1) before any run; each run is permitted only after
that save (R-2 disables otherwise). Recomputed results: 2026-03-04 minus 2026-03-01 = 3 days; 2026-03-11 minus
2026-03-01 = 10; 2026-03-12 minus 2026-03-01 = 11; 2026-03-04 minus 2026-01-01 = 62 (31 + 28 + 3); 2026-03-03T11:00Z
at UTC+13 = 2026-03-04T00:00 local (Auckland is on daylight time until April 2026, a platform fact not probed here).
A reference simulation of the selection rules (`RUN/scratch/sim.py`, 13 cases) was written but **NOT-REPLAYED: running
it was not approved in this session**, so none of its results are claimed. These cases stay open until a
run exists; the hand-derived expectations are not an execution result. Weaker-stand-in guard: AC-4.2, AC-4.3, AC-5.2,
NFR-1 and NFR-4 each require the real ledger, the real re-check or the real runtime; a fake that supplies the
expected outcome does not satisfy them. No command is documented by this spec, so no command check applies. No
earlier accepted version exists, so no requirement was dropped or weakened. Claims about the runtime or a library:
none are relied on (AD-4 is unresolved); the Auckland offset above is the single platform fact and is flagged unprobed.

## Submission

summary: Wrote KNOWLEDGE/spec.md (R-1 to R-10, NFR-1 to NFR-8, state and data assessment, service boundaries, lifecycle,
flows and transition ledger) and KNOWLEDGE/architecture.md (AD-1 to AD-5). No repository, discovery, research or baseline
existed; the host system is unknown, so all behaviour is proposed and the host-dependent parts are open prerequisites.
Open items that keep dependent work unready: G-1 host system and invoice-source fields (blocks adapters, not the abstract
contract), G-2 default schedule values (feature ships disabled), G-3 last-step retry bound (only AC-7.4), G-4 sender
identity and payment link, G-5 volume and quota, G-6 surfaces and alerting, G-7 retention.
Assumptions (value, basis, alternatives, revalidation):
- A-1 (R-1, R-2): offsets are whole days and the job runs once per business-timezone day. Basis: invoice due dates are
  calendar dates; one evaluation a day is sufficient. Alternatives: hourly evaluation, minute offsets. Revalidate if a
  sub-day reminder is wanted.
- A-2 (R-1): no cap on step count or offset range; the strictly-increasing rule gives at most one reminder per invoice
  per day. Basis: derived from A-1, the request states no cap, and no evidence supports a numeric one. Alternative: a
  numeric cap (value not invented). Revalidate after a misconfiguration incident.
- A-3 (R-6): `effective_from` defaults to the save date so enabling does not mass-mail the existing overdue backlog.
  Basis: an unrequested outward burst to customers cannot be undone; the owner can set the date back. Alternative:
  sweep the backlog on enable. Revalidate if the owner expects backlog chasing by default.
- A-4 (R-6): only the latest due step is sent after missed days; earlier ones are `skipped_missed`. Alternative: send
  all missed steps (a burst of reminders). Revalidate on owner feedback.
- A-5 (R-4): an ambiguous outcome is `unknown` and never resent; a `sending` claim from an earlier business date becomes
  `unknown` (no timeout value is invented). Alternative: at-least-once resend. Revalidate if the transport can report
  delivery idempotently.
- A-6 (R-7): retry window equals the schedule gap for non-final steps; the final-step bound is open (G-3). No numeric
  retry count invented.
- A-7 (R-9): pause is feature-owned and keyed by invoice id, minimal safeguard for automatic customer mail. Alternative:
  map to a host on-hold status. Revalidate when G-1 shows what the host has.
- A-8 (R-3): default subject and body wording as in R-3. Reversible text.
- A-9 (R-2): no run time of day is fixed; it is a deployment setting, since any time yields the required once-a-day
  behaviour. Tests supply the as-of instant.
primary: R-1, R-2, R-3, R-5, R-6
evidence_refs: KNOWLEDGE/spec.md; KNOWLEDGE/architecture.md; GUIDES/behavioral-requirements.md#behavior-model;
GUIDES/behavioral-requirements.md#traceability-and-review; GUIDES/behavioral-requirements.md#actors-channels-and-state-ownership;
GUIDES/requirements-definition.md (NFR and state and data assessment); GUIDES/service-discovery.md#verification;
GUIDES/platforms/ui.md#light-expressive-starting-point; RUN/scratch/sim.py (written, NOT-REPLAYED).
