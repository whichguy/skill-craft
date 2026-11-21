# Invoicing Product: Specification

Maintained requirements for the invoicing product. Product decisions are numbered `PD-<n>`; structure and
technology decisions are `AD-<n>` in `KNOWLEDGE/architecture.md` (none exist yet; this spec makes none).

## Basis and baseline

- **Request (2026-11-21):** "Set up automatic reminders for unpaid invoices."
- **Baseline:** none available. No `KNOWLEDGE/spec.md`, repository, discovery or research result existed when this
  stage ran. Every requirement below is therefore **added**; nothing is preserved or retired, and nothing is claimed
  about what the current system does. What the invoicing system, its data and its mail capability look like is an
  open prerequisite (G-1), not an observation.
- **Evidence kinds used:** *request* (the user's words), *default* (a value chosen here, recorded as an assumption in
  `## Submission`), *inference* (derived from the request plus the guides), *unknown* (listed under open gaps).
- **Vocabulary (product-neutral).** The spec fixes terms, not names in the product: *invoice* (issued bill with
  number, customer, currency, total, amount paid, due date, status, billing contact email), *status* one of
  `draft | open | partially_paid | paid | void`, *outstanding balance* = total − amount paid, *account* = the
  business that issues invoices and owns the reminder settings, *step* = one scheduled reminder of the schedule
  (identified by its position, 1-based), *step date* = invoice due date + the step's day offset, *run* = one
  daily evaluation, *today* = the calendar date of the run in the account's time zone.

## Scope and outcome map

Request outcomes (O) and where they are accepted:

| Outcome | Reading of the request | Requirements |
| --- | --- | --- |
| O-1 | "Set up": the account can turn reminders on/off and see/adjust when they go out | R-3, R-9 |
| O-2 | "automatic": reminders go out with no person acting per invoice | R-1, R-7 |
| O-3 | "reminders": a message reaches the payer; failures and results are visible | R-4, R-6, R-8 |
| O-4 | "unpaid invoices": only invoices still owing money; stop when paid; no repeats | R-2, R-5 |

**Primary requirements** (asked for directly): R-1, R-2, R-3, R-4, R-9.

**Out of scope** (domain rules the request leaves out; each bounds the R it is listed under; adding any is a new request):
late fees or interest (R-4), dispute or payment-plan handling (R-2), per-customer or per-invoice schedules, mute or
opt-out (R-3), channels other than email such as SMS, chat or letters (R-4), localisation of the message and
customer-facing templates editing (R-4), payment collection or a payment page (R-4: a pay link is shown only if the
invoice already has one), escalation to a collections agency or internal staff alerts (R-6), a configurable run
time (R-1), recurring/subscription invoices (R-2), reminders to people other than the invoice's billing contact (R-4).

## Product decisions

| ID | Decision | Basis | Alternative | Revalidate when |
| --- | --- | --- | --- | --- |
| PD-1 | Reminders go to the **customer** (the invoice's billing contact), sent on behalf of the account | inference: a reminder for an *unpaid* invoice is dunning; default | internal reminder to the account's staff | user says the audience is staff |
| PD-2 | Default schedule is three steps at **0, +7, +14** days from the due date | default | −3/+3/+10; a longer tail | account feedback or support data on response |
| PD-3 | One evaluation **run per calendar date**, at 09:00 in the account time zone (UTC if none set) | default | hourly runs | needed latency below one day |
| PD-4 | A step may be sent only during its **grace window**: step date through step date + 2 days (3 runs) | default; limits stale or bursty sends after outage or late import | wider window | outage tolerance requirement appears |
| PD-5 | **At most 3 delivery attempts** per step, one per run | default; bounds retries (R-6) | more attempts with backoff | provider failure rate observed |
| PD-6 | Settings are **account-wide**; one settings document replaced as a whole, with a revision check | default; the request names no per-customer need | per-field merge | concurrent admins complain |
| PD-7 | Failure window: duplicates are preferred over silent misses (**at-least-once** if a crash lands between provider acceptance and recording) | default | at-most-once | duplicate reminders cause complaints |

## Requirements

Acceptance-line key: **P** positive, **F** failure, **B** boundary, each present only where it says something the
others do not (else `n/a: reason`). **Surface** is where it is observed; **Confirm** is how. The reminder log (R-8) and
the outbound message are the consumer surfaces; the concrete interface through which the log and settings are read is
open (G-2). Plan and test stages choose a real interface; until then Confirm names the observation, not a tool.

Shared example fixture (**FX**), used by the replayable cases below. Account settings are the defaults (enabled,
steps 0/+7/+14, time zone UTC, run at 09:00 UTC) unless a case overrides them. Step dates for due date 2026-12-01 are
step 1 = 2026-12-01, step 2 = 2026-12-08, step 3 = 2026-12-15.

| Invoice | Total (USD) | Paid | Status | Due | Billing email |
| --- | --- | --- | --- | --- | --- |
| INV-1001 | 1200.00 | 0.00 | open | 2026-12-01 | ap@example.com |
| INV-1002 | 500.00 | 0.00 | open | 2026-12-01 | b@example.com |
| INV-1003 | 300.00 | 0.00 | open (imported 2026-12-10) | 2026-12-01 | e@example.com |
| INV-1004 | 300.00 | 0.00 | open | 2026-12-01 | *(none)* |
| INV-1005 | 100.00 | 0.00 | open | 2026-12-01 | c@example.com |
| INV-1006 | 50.00 | 0.00 | open | 2026-12-01 | g@example.com |

### R-1 Automatic daily reminder run *(primary)*

**Basis:** request 2026-11-21 ("automatic reminders"); PD-2, PD-3. **Change:** added. **Locators:**
behavioral-requirements.md#incoming-events-connections-and-state-agreement (scheduled initiator),
service-discovery.md#asynchronous-cooperation (work owned without a screen). **Evidence limit:** the scheduler and
mail capability of the runtime are unverified (G-1). **Pending:** implementation, checks.

**Behaviour.** Once per calendar date, at the run time (PD-3), the system evaluates every invoice and, for each step
whose step date has arrived and whose grace window (PD-4) is open, sends that step's reminder if the invoice is
eligible (R-2) and the step is still unsent (R-5). No person triggers a reminder per invoice. The run works without
any screen being open; its owner is the system, not a user session.
**Boundaries.** A step is due from 09:00 on its step date; a run before the step date sends nothing. A run that
finds no eligible work completes with no effect. Two runs for the same date are harmless (R-5). The run's "today"
uses the time zone in settings; the date, not the clock instant, decides eligibility.
**Error behaviour.** If a run fails or the system is down at 09:00, the next run (or recovery run on the same date)
picks up steps still inside their grace window; steps past it are never sent late (R-7). A failure on one invoice
does not stop evaluation of the others.
**Consumer outcome.** The payer receives the reminder on the step date; the account sees the result in the log (R-8).

- **R-1.A1 (P):** INV-1001, runs on 2026-11-30 and 2026-12-01. The 11-30 run sends nothing; the 12-01 run sends exactly
  one reminder, to ap@example.com, and the log has one entry (step 1, `sent`, 2026-12-01). *Surface:* outbound message and log.
  *Confirm:* run the evaluation with the clock set to each date against a recording mail sink and read the log.
- **R-1.A2 (F):** two invoices, the first one's send raises an error. The run still evaluates and sends the second.
  *Surface:* outbound messages and log. *Confirm:* sink fails for one recipient only; both log entries exist.
- **R-1.A3 (B):** the run's "today" in a non-UTC time zone. With time zone `America/Chicago` and clock instant
  2026-12-02T03:00Z (still 2026-12-01 in Chicago) the step dated 2026-12-02 is **not** yet due. *Surface:* log.
  *Confirm:* same procedure with the clock fixed at that instant. (Requires a runtime that exposes time-zone rules: G-1.)

### R-2 Eligibility: only invoices that still owe money *(primary)*

**Basis:** request ("unpaid invoices"); PD-1. **Change:** added. **Out of scope here:** disputes, payment plans,
subscription/recurring invoices. **Locators:** requirements-definition.md#state-and-data-change-assessment.
**Evidence limit:** the real status vocabulary and the way payments are recorded are unverified (G-1). **Pending:**
implementation, checks.

**Behaviour.** An invoice is eligible when its status is `open` or `partially_paid`, its outstanding balance is
greater than zero, it has a due date, and reminders are enabled (R-9). `draft`, `paid` and `void` invoices are never
reminded. Eligibility is **re-checked immediately before each send**, so a payment, a void or a disable that
happened after the run began suppresses the send. A reminder already delivered is not recalled when payment arrives
later. A partially paid invoice is reminded for its outstanding balance only.
**Boundaries.** Outstanding balance exactly 0.00 is not eligible; 0.01 is. Pre-due steps (negative offsets) are sent
to unpaid invoices that are not yet due. If the due date is edited, unsent steps are recomputed from the new date;
sent steps stay sent (R-5).
**Error behaviour.** If the invoice record cannot be read at the re-check, no email is sent for that step in this run
and the attempt is not counted; it is retried on the next run inside the grace window.
**Consumer outcome.** A customer who has paid is not chased; a customer who still owes receives a reminder.

- **R-2.A1 (P):** INV-1002 (500.00) with 200.00 paid on 2026-12-03 (status `partially_paid`). The step-2 reminder on
  2026-12-08 is sent and states outstanding 300.00 USD. *Surface:* message body. *Confirm:* read the recorded message.
- **R-2.A2 (F):** INV-1001 is marked `paid` (1200.00) on 2026-12-05. On 2026-12-08 no email is sent and the log gains no
  entry. *Surface:* sink and log. *Confirm:* run on 12-08; sink empty; log still one entry (step 1).
- **R-2.A3 (B):** status flips to `paid` after the run selected INV-1001 for its 12-01 step but before the send.
  No email is sent. *Surface:* sink. *Confirm:* inject the status change between selection and send in a test double;
  this boundary needs a seam that can pause the run between the two points (G-3).
- **R-2.A4 (B):** a `draft` invoice and a `void` invoice with due date 2026-12-01 and balance > 0 receive nothing on
  2026-12-01. *Surface:* sink. *Confirm:* run on 12-01 over those two fixtures.

### R-3 Reminder schedule: default and configuration *(primary)*

**Basis:** request ("Set up"); PD-2, PD-6. **Change:** added. **Out of scope here:** per-customer/per-invoice schedules,
muting. **Evidence limit:** who may change account settings, and through which interface, is unverified (G-2).
**Pending:** implementation, checks.

**Behaviour.** The account has one schedule: an ordered list of day offsets from the due date (negative = before).
Default `[0, 7, 14]`. The account may replace the list. Valid when: 1 to 5 offsets; each an integer from −30 to +90;
each at least 3 days after the previous one (strictly increasing). The *effective bounds* 5, −30, +90, 3 are
**defaults** chosen here: 5 caps the messages one invoice can ever receive (R-5), −30/+90 keep step dates in a
plausible billing horizon, and a gap of 3 keeps grace windows (PD-4) from overlapping. Settings are read at run
start; a change applies from the next run. Settings are replaced as a whole document with a revision check (PD-6).
**Boundaries.** `[0,3,6,9,12]` (5 steps, gap exactly 3) and `[-30,90]` (both range limits) are accepted;
`[0,3,6,9,12,15]` (6 steps), `[-31]`, `[91]`, `[0,2]` (gap 2), `[0,7,7]` (duplicate), `[]` (empty; to stop reminders
use R-9) are rejected.
**Error behaviour.** A rejected update changes nothing and names the field and rule violated. An update carrying a
stale revision is rejected with a conflict outcome and changes nothing; the caller must re-read.
**Consumer outcome.** The account can read the current schedule and the step dates it implies, and sees new
reminders follow a changed schedule.

- **R-3.A1 (P):** a new account reads `[0, 7, 14]`, enabled. Updating to `[−3, 5, 12]` is accepted and the next run
  for an invoice due 2026-12-01 treats 2026-11-28, 2026-12-06, 2026-12-13 as step dates. *Surface:* settings read.
  *Confirm:* read settings, then run on 11-28 and observe step 1 sent. *Interface:* G-2.
- **R-3.A2 (F):** submit `[0,2]` → rejected, field `steps[1]`, rule "at least 3 days after the previous step";
  stored schedule still `[0,7,14]`. Submit with a stale revision → conflict, nothing changed. *Surface:* settings
  write result and read. *Confirm:* write then read.
- **R-3.A3 (B):** the eight boundary cases listed under Boundaries produce exactly: accept (`[0,3,6,9,12]`), accept (`[-30,90]`),
  then reject for `[0,3,6,9,12,15]`, `[-31]`, `[91]`, `[0,2]`, `[0,7,7]`, `[]`. *Surface:* settings write result. *Confirm:* one write per case, then read.
- **R-3.A4 (B):** a settings change made while a run is in progress does not alter that run's schedule; the next run
  uses it. *Surface:* log. *Confirm:* change settings between run start and a later send via the test seam (G-3).

### R-4 Reminder message content and recipient *(primary)*

**Basis:** request ("reminders"); PD-1. **Change:** added. **Out of scope here:** other channels, localisation,
template editing, late fees, a payment page. **Evidence limit:** the invoice's contact field, any existing pay link
and the real sender identity are unverified (G-1). **Pending:** implementation, checks.

**Behaviour.** The recipient is the invoice's billing contact email, read at send time (so an email added after an
earlier no-recipient skip is used by later steps). The message is from the account, with the account's contact for
replies, and has a plain-text part and an HTML part. It states: account name, customer name, invoice number, the
outstanding balance with its currency, the due date, and whether the invoice is due on that day, due in N days, or
N days overdue; plus the invoice's pay link if the invoice has one. Subject: `Reminder: Invoice <number> <due phrase>`.
It does not number the reminders ("second reminder") and carries no late fee text. Only invoice fields appear, escaped
for the HTML part.
**Boundaries.** Amounts keep the invoice currency and two decimals. Due phrase: step date = due date → "is due
today"; before → "is due on 2026-12-01"; after → "was due on 2026-12-01 (9 days overdue)". Customer or account names
containing markup characters appear as literal text.
**Error behaviour.** No billing email → the step is skipped and logged `skipped:no-recipient` (terminal for that
step; later steps are re-evaluated). A syntactically invalid address counts as a failed attempt (R-6).
**Consumer outcome.** The payer can identify the invoice and the amount owed and knows how to pay.

- **R-4.A1 (P):** INV-1001 on 2026-12-01: To `ap@example.com`; subject `Reminder: Invoice INV-1001 is due today`; body
  contains `INV-1001`, `1200.00 USD`, `2026-12-01`. *Surface:* recorded message. *Confirm:* assert on recorded
  subject, recipient, both parts.
- **R-4.A2 (F):** INV-1004 (no email) on 2026-12-01: nothing sent; log entry step 1 `skipped:no-recipient`. After the
  email `f@example.com` is added, the 2026-12-08 run sends step 2 to it. *Surface:* sink and log.
- **R-4.A3 (B):** INV-1003 (imported 2026-12-10) sends on 12-10 with subject `Reminder: Invoice INV-1003 was due on
  2026-12-01 (9 days overdue)`; a customer named `A<b>&Co` renders as literal `A<b>&Co` in the HTML part (escaped).
  *Surface:* recorded message.

### R-5 No duplicate reminders; per-invoice cap

**Basis:** request ("reminders" must be sane); PD-2, PD-7. **Change:** added. **Locators:**
service-discovery.md#asynchronous-cooperation (duplicate, crash, atomic final write). **Pending:** implementation, checks.

**Behaviour.** Each (invoice, step) is sent at most once to a successful outcome: once a step is `sent`, `failed` or
`skipped`, it is terminal and is never re-evaluated, however often runs repeat or overlap or the due date or settings
later change. An invoice therefore receives at most as many reminders as the schedule has steps (maximum 5, R-3).
Before sending, a run atomically claims the (invoice, step) so two overlapping runs cannot both send. If the system
stops after the provider accepted a message but before the outcome is recorded, the claim is retried as a new attempt
on a later run (PD-7): a duplicate is possible in that window, bounded by the 3-attempt limit; no exactly-once claim is made.
**Boundaries.** Re-running the same date, or running twice at once, yields one message per step. Changing the
schedule after step 1 was sent does not resend step 1; a *new* step that lies in the grace window is sent.
**Error behaviour.** A claim that cannot be recorded means no email is sent for that step in this run.
**Consumer outcome.** A customer never receives the same step twice in normal operation.

- **R-5.A1 (P):** INV-1001, two runs on 2026-12-01 (sequential): one message and one log entry. *Surface:* sink and log.
- **R-5.A2 (B):** two runs started concurrently on 2026-12-01: exactly one message. *Surface:* sink. *Confirm:* start both
  against a shared store and a recording sink, assert count = 1 (needs concurrent runs: G-3).
- **R-5.A3 (F):** crash after provider acceptance, before recording: the next run within grace re-attempts (attempt 2),
  so two messages exist; the log shows `sent` once and the attempt count 2. Marked as the accepted window, not a defect.
  *Surface:* sink and log. *Confirm:* fault injection between send and record (G-3).

### R-6 Delivery failure and bounded retry

**Basis:** request ("reminders" reach the payer; failures not silent); PD-4, PD-5. **Change:** added. **Out of scope
here:** escalation, staff alerts. **Evidence limit:** the provider's error contract is unverified (G-1). **Pending:**
implementation, checks.

**Behaviour.** A send is *sent* only when the mail provider accepts the message; acceptance proves hand-off, not
inbox delivery or reading, and is recorded as such. A rejected or errored send is an attempt failure. A step is retried
once per later run while inside its grace window, up to 3 attempts in total (PD-5); after the third failure the step is
terminal `failed` and never retried. Each attempt is logged with its outcome and a failure category (no provider
payload, no message body).
**Boundaries.** With grace days 0, 1, 2 and 3 attempts the final attempt falls on step date + 2; no attempt on step
date + 3. A later step is independent of an earlier step's failure.
**Error behaviour.** If recording the outcome fails, see R-5 (at-least-once window).
**Consumer outcome.** The account can see which reminders failed and why (category only).

- **R-6.A1 (P):** INV-1005, provider accepting: step 1 → `sent` on 2026-12-01 with attempt count 1.
- **R-6.A2 (F):** INV-1005, provider rejecting every call, runs on 12-01, 12-02, 12-03, 12-04: attempts on 12-01, 12-02,
  12-03 are logged `attempt-failed`, `attempt-failed`, `failed` (terminal); the 12-04 run makes no attempt. *Surface:*
  log and sink call count (3).
- **R-6.A3 (B):** after that, provider healthy on 2026-12-08: step 2 is sent (independent). *Surface:* sink and log.

### R-7 Missed runs, late invoices and the grace window

**Basis:** request ("automatic"); PD-4. **Change:** added. **Pending:** implementation, checks.

**Behaviour.** A step is sent only while `step date ≤ today ≤ step date + 2` (PD-4). A step whose window has closed
unsent is **never sent**, and creates no log entry (it simply expires); steps still ahead proceed normally. Therefore an
outage, a re-enable (R-9) or a late import never produces a burst of old reminders: at most the steps whose window is open
are sent, and since steps are at least 3 days apart (R-3) at most one window is open at a time.
**Boundaries.** Age 2 days → sent; age 3 days → not sent. An invoice first seen on 2026-12-10 with due date 2026-12-01
and default schedule: step 1 (12-01) expired, step 2 (12-08, age 2) is sent that day, step 3 (12-15) is future.
**Error behaviour.** n/a: no new failure mode beyond R-1 and R-6.
**Consumer outcome.** Late data causes one relevant reminder, not a flood.

- **R-7.A1 (P):** INV-1003 (imported 2026-12-10) → run 12-10 sends one message (step 2, 300.00 USD); run 12-15 sends step 3.
- **R-7.A2 (B):** INV-1006 with the system disabled on 12-01, 12-02, 12-03 and enabled again for the 12-04 run: nothing is sent
  on 12-04 (step 1 age 3); the same fixture re-enabled for the 12-03 run would send step 1. *Surface:* sink.
- **R-7.A3 (F):** n/a: expiry is by design silent; failures inside the window are R-6.

### R-8 Reminder log (history)

**Basis:** request ("set up" implies visibility, outcome O-3); PD-6. **Change:** added. **Evidence limit:** where the log is
shown (invoice view, report, API) is open (G-2). **Pending:** implementation, checks.

**Behaviour.** For each invoice the system keeps a log of reminder attempts: step number, date, recipient email, outcome
(`sent`, `attempt-failed`, `failed`, `skipped:no-recipient`), attempt count and, for failures, a failure category. It is
read-only, in date order, durable across restarts, and visible only to users who can already view that invoice. It is
deleted when the invoice is deleted and otherwise kept for the life of the invoice. Message bodies are not stored.
**Boundaries.** An invoice never reminded has an empty log, shown as an empty state ("No reminders sent yet"), not an error.
**Error behaviour.** A user without access to the invoice gets no log content and no hint that entries exist.
**Consumer outcome.** The account can answer "did we remind this customer, when, and did it work?".

- **R-8.A1 (P):** after R-1.A1, INV-1001's log has exactly one entry: step 1, 2026-12-01, `ap@example.com`, `sent`, attempts 1.
- **R-8.A2 (F):** a user without access to INV-1001 requests its log: denied, no entries returned.
- **R-8.A3 (B):** INV-1002 before any run: empty log; after the invoice is deleted its entries are gone.

### R-9 Enable / disable *(primary)*

**Basis:** request ("Set up"); PD-6. **Change:** added. **Out of scope here:** per-customer or per-invoice mute. **Evidence
limit:** who may change settings is unverified (G-2). **Pending:** implementation, checks.

**Behaviour.** The account has an `enabled` flag; reminders are on by default once the feature exists (PD-2 default schedule).
When `enabled` is false, no reminder is sent. The flag is re-read **before each send** so a disable stops an in-flight run
promptly. Disabling and re-enabling does not send backlogs (R-7). Updating `enabled` follows the same revision rule as R-3.
**Boundaries.** Disable during a run: sends after that moment do not happen; sends already handed to the provider stand.
**Error behaviour.** A stale-revision change is rejected with conflict; only an authorized user may change it, else denied
with no effect.
**Consumer outcome.** The account can stop and restart reminders with predictable results.

- **R-9.A1 (P):** set `enabled=false` on 2026-11-30; the 12-01 run sends nothing; set `enabled=true` on 12-02; the 12-02 run
  sends step 1 (age 1, inside grace) for INV-1001. *Surface:* sink, settings read.
- **R-9.A2 (F):** an unauthorized user attempts to disable → denied; flag unchanged.
- **R-9.A3 (B):** disable between two sends of one run → second send does not occur (needs the test seam, G-3).

## Walkthrough record (item 10)

The sequential cases R-1.A1, R-2.A1, R-2.A2, R-3.A3, R-4.A3, R-5.A1, R-6.A2, R-6.A3, R-7.A1, R-7.A2 and R-9.A1 were walked **by
hand** from the stated start against the rules in this spec: step date = due + offset; eligible = status ∈ {open,
partially_paid} ∧ balance > 0 ∧ enabled; send only if step unsent ∧ 0 ≤ today − step date ≤ 2; attempts ≤ 3.
Recomputed: default step dates 2026-12-01 / 12-08 / 12-15; R-6.A2 attempts on 12-01, 12-02, 12-03 then none on 12-04, step 2
sends 12-08; INV-1003 on 12-10 → step 1 age 9 expired, step 2 age 2 sent, on 12-15 step 3 age 0 sent; INV-1006 re-enabled
12-04 → step 1 age 3 not sent; R-3.A3 verdicts accept/accept/reject/reject/reject/reject/reject/reject. A small guard-checking
model of these rules was written, but the sandbox refused to execute it, so **no run is claimed**:
`NOT-REPLAYED: execution of the check model was not permitted; hand-walked only`. This leaves the replay open (G-3's
check owner: test-spec stage, due before implement). R-1.A3, R-2.A3, R-3.A4, R-5.A2, R-5.A3 and R-9.A3 are
`NOT-REPLAYED`: they need seams (pausable run, fault injection, concurrent runs, time-zone rules) not yet confirmed to exist.

## State and data assessment

| State | Owner / location | Read by | Lifetime / removal | Change rule |
| --- | --- | --- | --- | --- |
| Reminder settings (`enabled`, `steps`, `revision`, time zone) | the account; durable, in the product's existing account-settings store (G-2) | the run (system), users who may view settings | until the account is closed | whole-document replace; stale revision → conflict (PD-6) |
| Step state per (invoice, step): `pending → claimed → sent | failed | skipped:no-recipient` | the reminder feature; durable (must survive restart or duplicates result) | the run | removed with the invoice | atomic claim; terminal states immutable (R-5) |
| Reminder log | derived from step attempts; durable | users who can view the invoice (R-8) | life of invoice | append-only |
| Invoice data (status, balance, due date, contact) | existing invoicing system | **observed only** by this feature; never modified | n/a | n/a |

Invariants. Before and after every run: no step is `sent` twice normally (R-5); a step in a terminal state never changes;
log entries equal the attempts made; invoice data is unchanged by the feature. Recovery: an interrupted run leaves steps
`claimed` or `pending`; the next run within grace re-attempts (counts as an attempt). Unknowns: how "claimed" is made atomic
and where state lives are structure choices for the plan (AD- later), not decided here. Target identities: the account's
invoices only; no cross-account effects.

## Service boundaries (this spec's contracts)

- **Invoice source (read-only authority):** the feature reads status, balance, due date and contact at run time and again
  before each send (R-2); no cache of invoice status is trusted across the send (freshness over speed, since a stale `open`
  would chase a paid customer). Revocation of a user's access takes effect on the next read of the log (R-8).
- **Mail provider (outbound, asynchronous outcome):** acceptance ≠ delivery (R-6); no delivery receipts are required; bounce
  handling is out of scope. Retry and duplicate behaviour are R-5/R-6.
- **Scheduler (system initiator):** owns the daily run independent of any screen (R-1); missed run recovery is R-7.
- Event coverage owned by this feature: each attempt is observable in the log (R-8); there is no external event stream.
  Concerns not applicable: incremental sync, subscriptions, incoming webhooks.

## Non-functional requirements

- **NF-1 Reliability and integrity** (R-1, R-5, R-6): a run never changes invoice data; each step's terminal state is durable;
  a failed run recovers per R-1/R-7. Verification: restart-between-runs and crash-window cases above. *Status:* accepted
  behaviour; no numeric availability target (none was requested and none is invented).
- **NF-2 Privacy and security** (R-4, R-8): the customer's email is shown only in the log (users with invoice access) and the
  outbound message to that address; it is **not written to application logs** (logs carry invoice number, step, outcome,
  failure category only); message bodies are not retained; log entries are removed with the invoice. Only invoice fields are
  placed in the message and they are escaped (R-4.A3). Authorization for settings and log reads follows existing account
  roles (G-2). Verification: inspect application log output of a run for the fixture addresses (expected none); access-denied
  cases R-8.A2, R-9.A2.
- **NF-3 Capacity and performance:** *unresolved bound.* Invoice volume and provider rate limits are unknown, so no run duration
  or throughput number is set. Required behaviour instead: sends not completed in a run remain `pending` and continue on the
  next run while the grace window is open; none is lost silently within the window and none is repeated. Missing evidence:
  expected invoices per run, provider quota (G-1). Does not block work that does not depend on volume.
- **NF-4 Observability:** each run records start, end and counts (evaluated, sent, failed, skipped) in application logs without
  personal data; a run that did not occur on a date is detectable by the absence of that record. Verification: run twice, read run records.
- **NF-5 Testability / determinism:** the run takes its notion of "today" and the time zone from an injectable clock, and the mail
  provider is replaceable by a recording sink, so the cases above can be replayed exactly. (A requirement on observability of
  behaviour, not a technology choice.)
- **NF-6 Message accessibility and rendering:** the email has a plain-text part carrying all facts; the HTML part is legible at
  320 px width with no horizontal scroll, text/background contrast meets WCAG AA in light and in dark rendering (no hard-coded
  background that makes dark clients unreadable), the pay link is a text link, not an image-only control. No motion or icon
  set applies to an email. Verification: render a recorded message at 320 px and at 800 px in a light and a dark client
  profile; automated contrast check on text colors.
- **NF-7 User interface (conditional):** the request does not ask for a screen, so none is specified. If settings (R-3, R-9)
  or the reminder log (R-8) are surfaced in a screen, it must be a deliberately designed interface, not scaffolding: a consistent
  visual system (spacing and type scales, a palette with a light and a dark theme); designed empty ("No reminders sent yet"),
  loading and error states; a layout working at 360 px and 1280 px with no horizontal overflow; visible focus states and WCAG AA
  contrast; motion only where it explains a change and honouring reduced motion; one icon set; truthful async feedback for saving
  settings (saving → saved / conflict / rejected-with-field) and never a timer-driven "saved". **Visual reference:** inside an
  existing product, inherit its identity; for a new screen start from the *light expressive* profile (light Gemini look with
  Material 3 Expressive principles; light first with a dark option; per
  `platforms/ui.md#light-expressive-starting-point`). The plan chooses the concrete treatment and records it as an AD.
  Verification: rendered check at both widths in both themes, keyboard-only pass, contrast check, reduced-motion check.
- **NF-8 Compatibility / retention:** settings and log retention follow R-8 (life of invoice); no other retention period is
  invented.

## Information lifecycle summary

Per state: owner and location, readers, concurrency, end-of-life and quotas are in `## State and data assessment`. Personal
data held by this feature: customer email in the log (shown to invoice viewers; stored with the log; not in application logs;
removed with the invoice). No secrets are stored by the feature itself; credentials of the mail capability are owned by the
platform/provider facility and are out of this spec. Runtime quotas (mail rate, storage) are unknown (NF-3, G-1). No identity,
sharing or persistence beyond these was added.

## Open gaps

- **G-1 (R-1, R-2, R-4, R-6, NF-3), open prerequisite:** no repository or running system was available, so these are unverified:
  an invoice store exposing status, outstanding balance, due date and billing email; a daily scheduler with time-zone support;
  an outbound mail capability with a recorded acceptance outcome; invoice volume and provider quotas. *Owner:* the plan stage's
  first work item (inspect the target runtime and invoice data; record the result as the baseline). *Due:* before any work item
  that consumes these. *Effect:* affected work stays unready; behaviour above stands as the target. Unavailable access is not
  evidence these are absent.
- **G-2 (R-3, R-8, R-9, NF-2, NF-7), open prerequisite:** the interface through which an account reads/changes settings and reads
  the log, and which roles may do so, is unknown. *Owner:* plan stage / product owner. *Due:* before work on those surfaces.
  *Effect:* settings/log work unready; the run (R-1, R-2, R-4–R-7) can proceed with a stub defaults store.
- **G-3 (cases marked NOT-REPLAYED), unverified check:** test seams for a pausable run, fault injection, concurrent runs and
  injectable clock/time zone are not confirmed. *Owner:* test-spec stage. *Due:* before implement.

No decision currently requires the user: every unstated value above is a recorded default (PD-1…PD-7, bounds in R-3).

## Retired

None. (No earlier requirement existed.)

## Submission

**summary:** Added a specification for automatic reminders on unpaid invoices: R-1 daily automatic run, R-2 eligibility and
re-check before send, R-3 schedule and configuration with validation bounds, R-4 message content and recipient, R-5 no duplicates
and per-invoice cap, R-6 failure and bounded retry, R-7 missed runs / late invoices / grace window, R-8 reminder log, R-9
enable/disable. No baseline existed, so nothing is preserved or retired. NFRs: reliability, privacy/logging, capacity
(unresolved, no invented bound), observability, testability, email accessibility, conditional UI. No AD was needed.

*Assumptions (each a default, reversible):*

| For | Value | Basis | Alternatives | Revalidate when |
| --- | --- | --- | --- | --- |
| R-1/R-3 | audience = customer (PD-1) | reminder of an *unpaid* invoice | staff-facing | user states otherwise |
| R-3 | default steps 0/+7/+14 (PD-2) | common dunning cadence; no source in request | −3/+3/+10 | account feedback |
| R-1 | run daily at 09:00 account time zone (PD-3) | daily is the coarsest cadence matching date-based steps | hourly | latency need |
| R-3 | max 5 steps, offsets −30…+90, min gap 3 days | cap on messages per invoice needed for safety; gap = grace size | other limits | volume/complaints |
| R-7 | grace window 3 days (PD-4) | avoids bursts of stale reminders after outage/late import | wider | outage tolerance requirement |
| R-6 | max 3 attempts, one per run (PD-5) | bounds retries inside grace | backoff | provider failure data |
| R-5 | at-least-once in the crash window (PD-7) | a missed reminder costs more than a rare duplicate | at-most-once | duplicate complaints |
| R-3/R-9 | account-wide settings, whole-document replace with revision check (PD-6) | request names no finer scope | per-customer | per-customer need |
| R-8 | log kept for life of invoice | no retention stated; avoids inventing a period | fixed retention | compliance requirement |

**primary:** R-1, R-2, R-3, R-4, R-9.

**evidence_refs:** KNOWLEDGE/spec.md (this file; every requirement section R-1…R-9, `## State and data assessment`,
`## Service boundaries`, `## Non-functional requirements`, `## Open gaps`); GUIDES/requirements-definition.md;
GUIDES/behavioral-requirements.md#behavior-model and #traceability-and-review and #actors-channels-and-state-ownership;
GUIDES/service-discovery.md#asynchronous-cooperation and #verification; GUIDES/platforms/ui.md#light-expressive-starting-point;
GUIDES/current-system-baseline.md#planning-and-review-handoff (no baseline was available to reopen); GUIDES/project-knowledge.md#maintained-product-requirements.
The incoming request (2026-11-21) is the only product source. No backchain graph was written (duty 11 omitted here).
