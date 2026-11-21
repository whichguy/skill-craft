# Invoicing: payment reminders — product specification

Status: proposed, written by the spec stage run on its own on 2026-11-21. No repository, discovery result, research
result, earlier specification or baseline existed for this run (`KNOWLEDGE/` was empty), so nothing about the invoicing
product's current behaviour was inspected. Every statement below is therefore either (a) the request's words,
(b) a recorded assumption `A-<n>`, or (c) an open gap `G-<n>`. Observations: none. Inferences: A-1..A-12. Unknowns:
G-1..G-11. A later run that has the repository must reopen G-1 first.

## Request and basis

Source `REQ-2026-11-21`: the request of 2026-11-21, verbatim: "Set up automatic reminders for unpaid invoices."
Every R-<n> below cites this as its basis (`REQ-2026-11-21`) unless it says it is derived (inferred as the minimum
needed to make the request safe) and names the assumption that carries the inference.

Request outcomes (each traced to acceptance lines in "Traceability"):

| ID | Words of the request | Meaning used here |
| --- | --- | --- |
| O-1 | "Set up" | A person with authority can turn the feature on and choose its schedule. |
| O-2 | "automatic" | Reminders go out on a schedule with no per-invoice human action. |
| O-3 | "reminders" | The customer owing the money receives a message that names the invoice and what is owed. |
| O-4 | "unpaid invoices" | Only invoices that still have money owing are reminded; paying stops the reminders. |

## Assumptions (defaults taken because nobody was available to decide)

- **A-1** "Unpaid" means overdue: issued, balance greater than zero, due date earlier than today's date in the business
  timezone, and not void, written off, draft or disputed. Pre-due reminders are not sent (see R-4 exclusions).
- **A-2** The reminder is an email to the invoice's single billing-contact address. Other channels (SMS, chat, letters)
  are out of scope.
- **A-3** Default schedule: reminders at 3, 7 and 14 days after the due date ("offsets"), sent at 09:00 in the business
  timezone. Offsets, send time and timezone are configurable (R-1). The numbers are product defaults, not platform limits.
- **A-4** The feature ships disabled. It does nothing until someone enables it.
- **A-5** No retroactive reminders: when the feature is enabled, a reminder whose scheduled instant is earlier than the
  enabling instant is never sent (R-2).
- **A-6** Configuration limits: 1 to 10 offsets, each an integer from 1 to 365 days, strictly increasing. Product limits,
  chosen to reject obvious mistakes; not derived from any platform.
- **A-7** A failed send is retried up to 3 attempts in total per invoice and offset (R-7). Product default.
- **A-8** Per-invoice pause and per-customer opt-out (R-5) are included as the smallest safeguard against reminding a
  customer in a dispute. They are derived, not asked for; the owner may drop R-5 without affecting R-1..R-4.
- **A-9** One locale for message text: English, dates as "March 11, 2027", amounts as "USD 1,200.00" (ISO currency code,
  thousands separator, two decimals). Multi-language and multi-currency formatting beyond the code prefix are out of scope.
- **A-10** The evaluator (the unattended job that decides what to send) may be run at any frequency, may run twice at
  the same time, and may be interrupted at any point. Its correctness does not depend on how often it runs.
- **A-11** Reminder history is kept as long as its invoice is kept (G-5 asks whether that is acceptable).
- **A-12** Staff who can edit invoices can configure, pause and view reminders, until a role model is known (G-7).

## Open gaps

| ID | Gap | Affects | Blocks |
| --- | --- | --- | --- |
| G-1 | The invoicing system is unknown: where invoices live, their status vocabulary, whether due dates are editable, how a payment/partial payment is recorded, whether a payment link exists. A-1 must be mapped onto the real statuses. | R-4, R-3, R-1 | Mapping of R-4 to real statuses and all end-to-end checks. Pure logic (R-2 date arithmetic, R-6 idempotency, R-7 state machine) can proceed. |
| G-2 | The email provider, sender domain/address and its credentials (alias/mechanism only, never values), and whether it supports an idempotency key and rate/daily limits. Owner: the user. | R-3, R-6, R-7, NFR-4 | The real-boundary check of R-3 (a message really arrives). Unavailable access does not mean the behaviour is absent. |
| G-3 | Legal/compliance obligations for dunning email in the user's jurisdictions (required footer, unsubscribe, sender identification). Owner: the user. | R-3, R-5 | Nothing technical; must be answered before production enablement. No content beyond R-3 is invented. |
| G-4 | Timeliness bound: how late after its scheduled instant a reminder may be sent. | NFR-1 | Planning of the evaluator's run frequency. |
| G-5 | Retention period for reminder history and the stored recipient address; erasure requests. | R-9 | A numeric retention rule; A-11 applies meanwhile. |
| G-6 | Whether the message may include a payment link/instructions. | R-3 | Only the optional line in R-3; absent in the default message. |
| G-7 | Role model: who may configure, pause and view. A-12 is the placeholder. | R-1, R-5, R-8 | Access-control checks. |
| G-8 | Owner confirmation of the defaults A-1 (overdue only), A-3 (3/7/14 at 09:00), A-5 (no retroactive reminders), A-7 (3 attempts). | R-1, R-2, R-4, R-7 | Does not block planning; a changed answer changes only the named clause. |
| G-9 | The consumer surface for configuration, pause and history (admin screen, settings file, API) is unknown. | R-1, R-5, R-8 | Choice of surface in planning after discovery; the NFR-6 interface criteria apply if a screen is added. |
| G-10 | Invoice volume and provider quota (capacity bound). | NFR-4 | A numeric capacity bound; none is invented. |
| G-11 | The runtime that executes the evaluator unattended (platform scheduler, deployment, secrets facility). It must run without the developer's workstation. | R-2, R-6, R-7 | Real-boundary check of unattended execution. |

No material requirement conflict exists. Work unready until its gap closes: R-4's status mapping (G-1), R-3's real
delivery check (G-2), the surface of R-1/R-5/R-8 (G-9), unattended execution (G-11). Independent work may proceed.

## Shared fixture (referenced by acceptance lines so each can be replayed exactly)

- **C-1 configuration**: reminders enabled at instant `2027-03-01T15:00:00Z`; offsets `[3, 7, 14]`; send time `09:00`;
  timezone `America/New_York`; sender `Billing <billing@example.test>`.
- **Clock**: "run at T" means one evaluator invocation with the clock fixed at instant T (UTC).
- **Mail transport**: a recording test double that accepts every message unless an acceptance line scripts a result. It
  records recipient, subject, body and the idempotency key of each call.
- **Date facts** (calendar arithmetic, hand-computed; see Evidence): in 2027 daylight saving time starts on Sunday
  2027-03-14 at 02:00 local. Before it, `America/New_York` is UTC-5 (09:00 local = 14:00Z); from it, UTC-4 (09:00 local =
  13:00Z). 2027-03-01 is a Monday; February 2027 has 28 days.
- **Invoices** (all currency USD, contact `ap@example.test`, status open, balance equals total unless stated):

| Invoice | Due date | Balance | Used by |
| --- | --- | --- | --- |
| INV-1001 | 2027-03-11 (Thu) | 1,200.00 | R-2, R-3, R-4, R-6, R-8 |
| INV-1002 | 2027-03-16 (Tue) | 800.00 | R-2 catch-up |
| INV-1003 | 2027-02-20 (Sat) | 450.00 | R-2 no retroactive |
| INV-1004 | 2027-02-26 (Fri) | 300.00 | R-2 enabling boundary |
| INV-1007 | 2027-03-11 | 500.00 | R-2 due date change |
| INV-1008 | 2027-03-11 | 640.00 | R-5 pause |
| INV-1009..INV-1012 | 2027-03-11 | 100.00 each | R-7 failures |

Scheduled instants for due date 2027-03-11 under C-1: offset 3 → 2027-03-14 09:00 EDT = `2027-03-14T13:00:00Z`; offset 7 →
2027-03-18 = `2027-03-18T13:00:00Z`; offset 14 → 2027-03-25 = `2027-03-25T13:00:00Z`. (A converter that applied the
winter offset UTC-5 to 2027-03-14 would give 14:00Z and fail the boundary lines of R-2.)

## Requirements

### R-1 Configure automatic reminders  *(primary)*

Basis: `REQ-2026-11-21` ("Set up"). Added; nothing preserved (no baseline: G-1). Pending: implementation and every check.
Behaviour: an authorised person (A-12, G-7) can read and change the reminder configuration: enabled flag (default off,
A-4), offsets (default `[3,7,14]`, A-3), send time (default `09:00`), timezone (default: the business/account timezone,
or `America/New_York` in the fixture). Enabling records the enabling instant E (the most recent enabling action).
Boundaries: offsets 1..10 entries, each integer 1..365, strictly increasing (A-6); send time `HH:MM` 24-hour; timezone a
valid IANA name. A configuration change takes effect at the next evaluator run; a run already in progress keeps the
configuration it read when it started.
Error behaviour: an invalid value is rejected with a message naming the field; the stored configuration is unchanged.
Consumer outcome: after setup the stored configuration reads back exactly as submitted.
Out of scope (bounded domain rules): per-customer schedules, per-invoice schedules, templates, languages.
Open: G-7 roles, G-9 surface.

- **R-1.AC1 positive.** Surface: configuration surface (G-9; test via its API/command layer). Submit C-1 with enabled
  true at `2027-03-01T15:00:00Z`; read back: enabled true, offsets `[3,7,14]`, time `09:00`, timezone `America/New_York`,
  E = `2027-03-01T15:00:00Z`. Confirmed by: automated test, exact-value assertion on the read-back.
- **R-1.AC2 positive (defaults).** Fresh installation, nothing submitted: read back enabled false, offsets `[3,7,14]`,
  time `09:00`. Run at `2027-03-14T13:00:00Z` with INV-1001 overdue: zero messages recorded by the transport. Confirmed by:
  automated test with the recording transport.
- **R-1.AC3 failure.** Each submission is rejected and the stored configuration stays as C-1: offsets `[]`; `[0]`; `[7,3]`;
  `[3,3]`; `[366]`; an 11-entry list `[1,2,3,4,5,6,7,8,9,10,11]`; `[2.5]`; time `25:00`; time `9am`; timezone `Mars/Base`.
  Each returns an error naming the field (`offsets`, `send_time`, `timezone`). Confirmed by: automated table test, assert
  rejection, field name and unchanged read-back for every row.
- **R-1.AC4 boundary.** Accepted: offsets `[1]`; `[365]`; the 10-entry list `[1,2,3,4,5,6,7,8,9,10]`; time `00:00`;
  time `23:59`. Confirmed by: same table test.
- **R-1.AC5 positive (disable).** With C-1 and INV-1001, disable at `2027-03-14T12:59:00Z`; run at `2027-03-14T13:00:00Z`:
  zero messages, zero reminder records for INV-1001. Re-enable at `2027-03-20T10:00:00Z` (E replaced): run at
  `2027-03-25T13:00:00Z` sends offset 14 for INV-1001 only (offsets 3 and 7 instants are earlier than the new E, recorded
  `skipped: before_enablement`). Confirmed by: automated test.
- **R-1.AC6 boundary (change takes effect next run).** Change send time from `09:00` to `10:00` at `2027-03-14T12:00:00Z`;
  run at `2027-03-14T13:00:00Z` sends nothing for INV-1001 (its instant is now `14:00:00Z`); run at `2027-03-14T14:00:00Z`
  sends offset 3. Confirmed by: automated test.

### R-2 Schedule reminders from the due date  *(primary)*

Basis: `REQ-2026-11-21` ("automatic"). Added. Pending: implementation and checks.
Behaviour: for each in-scope invoice (R-4) and each configured offset d, the scheduled instant is the invoice's due date
plus d days, at the send time, in the configured timezone, converted to UTC using that timezone's rules for that date.
At an evaluator run at time T, an offset is *due* when its instant ≤ T and no reminder record exists for (invoice,
offset). Rules:
1. *No retroactive reminders (A-5).* A due offset whose instant < E (the enabling instant) is recorded `skipped:
   before_enablement` and never sent.
2. *Catch-up.* If several offsets are due at once, only the one with the largest offset is processed for sending (R-3, R-4,
   R-5, R-7); each other due offset is recorded `skipped: superseded`. At most one message per invoice per run.
3. *Due date change.* Instants are always derived from the invoice's current due date. Records already written stay
   (a sent offset is never sent again, even if the new due date would make it due again).
4. *Nonexistent local time.* If the send time does not exist on that date (daylight-saving gap), the instant is the send
   time shifted forward by the gap length (02:30 → 03:30 local on 2027-03-14).
Error behaviour: an unreadable timezone configuration cannot occur (R-1 validates); the evaluator treats an invoice with
no due date as out of scope and logs `reminder.skipped` reason `no_due_date`.
Consumer outcome: reminders arrive on the scheduled local date and time, including across a daylight-saving change.
Out of scope (bounded domain rules): pre-due reminders; escalation tiers; late fees or interest; weekend or holiday
avoidance (a reminder due on a Saturday is sent on that Saturday).
Preserved: none known (G-1). Open: G-4 timeliness, G-11 runtime.

- **R-2.AC1 positive.** C-1, INV-1001. Run at `2027-03-14T13:00:00Z`: exactly one message recorded, to `ap@example.test`,
  subject `Reminder: Invoice INV-1001 is 3 days overdue`; reminder record (INV-1001, 3) state `sent`. Then run at
  `2027-03-18T13:00:00Z`: one more message, "7 days overdue". Then run at `2027-03-25T13:00:00Z`: one more, "14 days
  overdue". Total 3 messages. Confirmed by: automated test, recording transport, fixed clock.
- **R-2.AC2 boundary (instant and daylight-saving).** C-1, INV-1001. Run at `2027-03-14T12:59:59Z`: zero messages. Run at
  `2027-03-14T13:00:00Z`: one message. (A fixed UTC-5 conversion would place the instant at 14:00:00Z and fail both runs.)
  Confirmed by: automated test.
- **R-2.AC3 boundary (before the change).** C-1, INV-1003 (due 2027-02-20), enabled `2027-03-01T15:00:00Z`. Offset 3
  instant `2027-02-23T14:00:00Z` and offset 7 instant `2027-02-27T14:00:00Z` are before E: run at `2027-03-01T15:00:00Z`
  records both `skipped: before_enablement` and sends nothing. Offset 14 instant is 2027-03-06 09:00 EST = `2027-03-06T14:00:00Z`:
  run at `2027-03-06T13:59:59Z` sends nothing; run at `2027-03-06T14:00:00Z` sends one message "14 days overdue". Confirmed
  by: automated test.
- **R-2.AC4 boundary (enabling instant).** C-1, INV-1004 (due 2027-02-26). Offset 3 instant = 2027-03-01 09:00 EST =
  `2027-03-01T14:00:00Z`, which is 1 hour before E (`15:00:00Z`): recorded `skipped: before_enablement`, not sent. Offset 7
  instant `2027-03-05T14:00:00Z`: sent at that run. Variation: if E were exactly `2027-03-01T14:00:00Z`, offset 3 is not
  before E and is sent at the first run (the comparison is `instant < E`, so equality sends). Confirmed by: automated test
  with both E values.
- **R-2.AC5 positive (catch-up).** C-1, INV-1002 (due 2027-03-16; instants 03-19, 03-23, 03-30 at `13:00:00Z`). No run
  between `2027-03-19T13:00:00Z` and `2027-03-24T23:59:59Z`. First run at `2027-03-25T13:00:00Z`: offsets 3 and 7 are
  due; exactly one message is recorded, subject `Reminder: Invoice INV-1002 is 9 days overdue` (25 March minus 16 March =
  9 days, the actual lateness, not the offset); record (INV-1002, 7) `sent`; record (INV-1002, 3) `skipped: superseded`;
  offset 14 has no record. Run at `2027-03-30T13:00:00Z`: one message "14 days overdue"; (INV-1002, 14) `sent`. Confirmed
  by: automated test.
- **R-2.AC6 failure/boundary (due date change).** C-1, INV-1007 (due 2027-03-11), offset 3 sent at
  `2027-03-14T13:00:00Z`. On `2027-03-15T10:00:00Z` the due date is edited to `2027-03-20` (permitted if the invoicing
  system allows editing an unpaid invoice's due date: G-1). Run at `2027-03-18T13:00:00Z`: zero messages (offset 7 is now
  `2027-03-27T13:00:00Z`); offset 3 is not re-sent (record exists). Run at `2027-03-27T13:00:00Z`: one message "7 days
  overdue"; run at `2027-04-03T13:00:00Z`: one message "14 days overdue". Confirmed by: automated test.
- **R-2.AC7 boundary (gap).** Send time `02:30`, timezone `America/New_York`, invoice due `2027-03-11`, offset 3 →
  instant is 03:30 EDT = `2027-03-14T07:30:00Z`: run at `2027-03-14T07:29:59Z` sends nothing; run at `2027-03-14T07:30:00Z`
  sends. Confirmed by: automated test.
- **R-2.AC8 n/a (autumn overlap).** n/a: a local time that occurs twice at the autumn change is not specified, because the
  request needs no rule for it; the chosen timezone library's behaviour is accepted and recorded in the plan as an unknown,
  not as a requirement.

### R-3 Send the reminder message  *(primary)*

Basis: `REQ-2026-11-21` ("reminders"). Added. Pending: implementation and checks; real delivery check needs G-2.
Behaviour: a due, eligible offset (R-2, R-4, R-5) produces one email from the configured sender to the invoice's billing-contact
address. Subject: `Reminder: Invoice <number> is <n> day(s) overdue`, `n` = whole days between the due date and the
send date in the configured timezone, `day` singular when n = 1. Body (plain text, A-9) contains in order: a greeting line,
`Invoice: <number>`, `Amount due: USD <balance>`, `Due date: <Month D, YYYY>`, `Days overdue: <n>`, and a closing line with the
sender name. The amount is the invoice's current balance at send time, not its original total. The message carries an
idempotency key equal to the reminder record ID (R-6).
Error behaviour: a missing or syntactically invalid contact address yields no provider call and the record `skipped:
no_recipient`; the invoice's other offsets are unaffected.
Consumer outcome: the customer receives an email that identifies the invoice and what is still owed.
Out of scope (bounded domain rules): payment link or instructions (G-6; none in the default message); attachments (no PDF of
the invoice); replies handling; open/click tracking; customer-visible unsubscribe handling (G-3); multiple recipients.
Open: G-2, G-3, G-6.

- **R-3.AC1 positive.** C-1, INV-1001, run at `2027-03-14T13:00:00Z`: the transport records one call with recipient
  `ap@example.test`, from `billing@example.test`, subject exactly `Reminder: Invoice INV-1001 is 3 days overdue`, and a body
  containing the lines `Invoice: INV-1001`, `Amount due: USD 1,200.00`, `Due date: March 11, 2027`, `Days overdue: 3`.
  Confirmed by: automated test, exact string assertions (a substring such as "INV-1001" alone is not sufficient).
- **R-3.AC2 boundary (singular).** Offsets `[1]`, invoice due `2027-03-11`: the instant is 2027-03-12 09:00 EST (UTC-5, before the
  daylight-saving change) = `2027-03-12T14:00:00Z`. Run at `2027-03-12T13:59:59Z`: zero messages. Run at
  `2027-03-12T14:00:00Z`: subject `Reminder: Invoice INV-1001 is 1 day overdue`, body `Days overdue: 1`. Confirmed by:
  automated test.
- **R-3.AC3 failure (no recipient).** INV-1001 with the contact address empty, then with `not-an-address`: run at
  `2027-03-14T13:00:00Z`: zero transport calls; record (INV-1001, 3) `skipped: no_recipient` each time; run at
  `2027-03-18T13:00:00Z` after the address is corrected to `ap@example.test` sends offset 7. Confirmed by: automated test.
- **R-3.AC4 real boundary.** Against the real provider's sandbox or a test mailbox, one reminder for a synthetic invoice
  arrives at a mailbox the tester controls, from the configured sender, with the same subject and body as AC1. Confirmed by:
  manual/real-boundary check, owner the user (credentials G-2), due at product acceptance. Until G-2 closes this line is
  `NOT-VERIFIED (blocked: access)`, not passed and not removed.

### R-4 Remind only while money is owed  *(primary)*

Basis: `REQ-2026-11-21` ("unpaid invoices"). Added. Pending: implementation and checks; status mapping needs G-1.
Behaviour: an invoice is in scope when, at the evaluator's read, its status is open (issued), balance > 0, due date <
today in the business timezone, and it is not void, written off, draft or disputed (A-1; mapped to real statuses in
planning). The evaluator re-reads the invoice from the invoicing system immediately before claiming a send (R-6) and never
uses a cached or earlier-run copy for the decision. An invoice that is out of scope at that read yields no message and no new
record. A partial payment leaves the invoice in scope with the reduced balance.
Boundaries: balance exactly 0.00 is out of scope; balance 0.01 is in scope; due date equal to today is not overdue.
Error behaviour: if the invoicing system cannot be read, nothing is sent for that invoice in this run and the failure is
logged `reminder.failed` reason `invoice_unreadable`; later runs proceed normally.
Consumer outcome: a customer who has paid is not reminded.
Out of scope (bounded domain rules): reopened or reversed payments (reminders continue per existing records; no special
handling); credit notes; refunds; payment-plan invoices.
Known limit: a payment recorded after the evaluator's re-read but before the provider accepts the message does not stop that
message (the window is the provider call; R-6 bounds it to one message).
Open: G-1.

- **R-4.AC1 positive.** C-1, INV-1001 balance 1,200.00, run at `2027-03-14T13:00:00Z`: sent (as R-2.AC1). Confirmed by:
  automated test.
- **R-4.AC2 positive (partial payment).** Continue INV-1001 after its offset-3 message: a payment of 600.00 is recorded on
  `2027-03-16T10:00:00Z` (a permitted action of the invoicing system, not of this feature; balance becomes 600.00). Run at
  `2027-03-18T13:00:00Z`: one message "7 days overdue", body `Amount due: USD 600.00`. Confirmed by: automated test with the
  invoice fixture changed between runs.
- **R-4.AC3 failure/boundary (paid).** Continue: the remaining 600.00 is paid on `2027-03-20T10:00:00Z` (balance 0.00,
  status paid). Run at `2027-03-25T13:00:00Z`: zero messages, no record (INV-1001, 14). Confirmed by: automated test,
  assertion of zero transport calls and zero records.
- **R-4.AC4 boundary (payment races the instant).** A fresh INV-1001 copy (balance 1,200.00): paid in full at
  `2027-03-14T12:59:59Z`; run at `2027-03-14T13:00:00Z`: zero messages. Paid at `2027-03-14T13:00:01Z` after the run's
  message was accepted: the message stands (known limit above). Confirmed by: automated test; the second half documents
  the limit and asserts one message.
- **R-4.AC5 failure (other statuses).** Separate runs at `2027-03-14T13:00:00Z` for an invoice with each status — void,
  written off, draft, disputed — each otherwise like INV-1001: zero messages, zero records. Confirmed by: automated table
  test, using the real status names found in discovery (G-1).
- **R-4.AC6 boundary (overdue).** Offsets `[1]`, invoice due `2027-03-14`; run at `2027-03-14T13:00:00Z` sends nothing (due date equals today; offset 1 instant is
  `2027-03-15T13:00:00Z`); run at `2027-03-15T13:00:00Z` sends "1 day overdue". Confirmed by: automated test.
- **R-4.AC7 failure (read error).** The invoice read throws at the run at `2027-03-14T13:00:00Z`: zero messages, no
  record, one `reminder.failed` log with reason `invoice_unreadable` and invoice `INV-1001`; the next run at
  `2027-03-14T14:00:00Z`, read succeeding, sends offset 3 (still due, no record). Confirmed by: automated test.

### R-5 Pause and opt out  *(derived, A-8)*

Basis: derived from `REQ-2026-11-21` ("unpaid invoices") as the minimum safeguard against reminding a customer in a dispute;
droppable under A-8. Added. Pending: implementation and checks.
Behaviour: staff (A-12) can put one invoice on hold and release it, and can mark a customer "no reminders". The state at the
evaluation decides: when an offset is due and the invoice is on hold, or its customer is opted out, the offset is recorded
`skipped: paused` or `skipped: opted_out`, and is never sent later; releasing the hold only affects later offsets.
Error behaviour: holding an invoice that is already held, or releasing one that is not, is a no-op that reports the current
state and changes nothing.
Consumer outcome: staff can silence reminders for one invoice or one customer without disabling the feature.
Out of scope (bounded domain rules): customer self-service unsubscribe (G-3); timed holds; bulk operations.
Open: G-3, G-7, G-9.

- **R-5.AC1 positive/boundary.** C-1, INV-1008 (due 2027-03-11). Put on hold at `2027-03-13T10:00:00Z`; released at
  `2027-03-16T10:00:00Z`. Run at `2027-03-14T13:00:00Z`: zero messages, record (INV-1008, 3) `skipped: paused`. Run at
  `2027-03-18T13:00:00Z`: one message "7 days overdue"; run at `2027-03-25T13:00:00Z`: one message "14 days overdue".
  Confirmed by: automated test.
- **R-5.AC2 boundary (hold lands at the instant).** Put on hold at `2027-03-14T12:59:59Z`: run at `2027-03-14T13:00:00Z`
  records `skipped: paused`. Put on hold at `2027-03-14T13:00:01Z` after the message was accepted: the message stands.
  Confirmed by: automated test.
- **R-5.AC3 positive (customer opt-out).** Mark the customer of INV-1001 "no reminders" at `2027-03-01T16:00:00Z`: runs at
  the three instants record (INV-1001, 3/7/14) `skipped: opted_out`, zero messages. Confirmed by: automated test.
- **R-5.AC4 failure (repeat).** Hold twice, then release twice: the second hold and second release each report the current
  state; no duplicate hold record exists. Confirmed by: automated test.

### R-6 Never send the same reminder twice; tolerate overlapping and interrupted runs  *(primary)*

Basis: `REQ-2026-11-21` ("automatic": unattended runs must not annoy customers). Added. Pending: implementation and checks.
Behaviour: at most one reminder message is handed to the provider per (invoice, offset). The evaluator claims (invoice,
offset) by atomically creating a reminder record in state `sending` with a lease before the provider call; if a record
already exists the evaluator does not send. The provider call carries the record ID as idempotency key. A record left in
`sending` after its lease has expired (a crash) is retried with the same key (R-7); before the lease expires no other run
may call the provider for it.
Error behaviour: if the claim cannot be written, nothing is sent.
Consumer outcome: the customer gets each scheduled reminder once.
Known limit: exactly-once delivery is not promised. If the provider lacks idempotency-key support (G-2) and the first call's
outcome was unknown, a duplicate message is possible.

- **R-6.AC1 positive (repeat run).** C-1, INV-1001. Run at `2027-03-14T13:00:00Z` then at `2027-03-14T13:05:00Z`: 1 message
  total, 1 record (INV-1001, 3) `sent`. Confirmed by: automated test.
- **R-6.AC2 boundary (concurrent runs).** Two evaluator runs started at the same time at `2027-03-14T13:00:00Z` against the
  same store: total 1 transport call for (INV-1001, 3), 1 record. Confirmed by: automated concurrency test against the real
  store implementation (a single-process lock in the test does not count; the uniqueness must come from the store).
- **R-6.AC3 failure (crash after claim).** The transport double is scripted to terminate the evaluator after receiving the
  call (outcome unknown). The record stays `sending`; the first call was at `2027-03-14T13:00:00Z`. The test sets the lease to 10
  minutes (production length: AD-2); a lease is expired when T ≥ claim time + lease. Run at `2027-03-14T13:09:59Z`: zero
  calls. Run at `2027-03-14T13:10:00Z`: one call with an idempotency key identical to the first call's key.
  With a double that deduplicates by key: 1 message total. Confirmed by: automated test asserting the two keys are equal
  (a test that only counts messages would pass with a non-stable key).
- **R-6.AC4 failure (claim fails).** The store rejects the claim write: zero transport calls and a `reminder.failed` log
  reason `claim_failed`. Confirmed by: automated test.

### R-7 Failed sends are retried a bounded number of times and stay visible  *(primary)*

Basis: `REQ-2026-11-21` ("automatic" and "reminders": a reminder that silently fails is not a reminder). Added. Pending:
implementation and checks.
Behaviour: states of a reminder record: `sending`, `sent`, `failed`, `skipped`. A transient provider failure (timeout,
throttling, 5xx) leaves the record retryable; each later evaluator run while the offset is still current retries, up to 3
attempts in total (A-7). A permanent rejection (address rejected) makes the record `failed` at once. Retrying ends when the
attempt count reaches 3, the invoice leaves scope (R-4), or a later offset of the same invoice becomes due (the earlier one
is then `failed` with reason `superseded_by_next_step` if not yet sent). A failed offset does not block later offsets.
Provider throttling that returns "retry later" does not consume an attempt and is retried on the next run.
Consumer outcome: transient trouble does not lose reminders; persistent trouble is visible to staff (R-8).
Out of scope: bounce and complaint events after acceptance (see Service boundaries); manual "resend".

- **R-7.AC1 positive.** INV-1009; transport scripted: timeout, timeout, accept. Runs at `2027-03-14T13:00:00Z`,
  `T14:00:00Z`, `T15:00:00Z`: 3 calls, 1 message accepted, record `sent` with attempts = 3. Confirmed by: automated test.
- **R-7.AC2 boundary (exhaustion).** INV-1010; transport scripted timeout ×4. Runs at `13:00`, `14:00`, `15:00`, `16:00` Z on
  2027-03-14: 3 calls total, record `failed` attempts = 3, reason `retries_exhausted`; the run at `16:00Z` makes no call.
  Run at `2027-03-18T13:00:00Z`: offset 7 is sent normally. Confirmed by: automated test.
- **R-7.AC3 failure (permanent).** INV-1011; transport scripted: permanent rejection. Run at `2027-03-14T13:00:00Z`: record
  `failed`, attempts = 1, reason `rejected`; run at `14:00Z`: no call. Confirmed by: automated test.
- **R-7.AC4 boundary (next step supersedes).** INV-1012; transport scripted timeout on the first call at
  `2027-03-14T13:00:00Z`; no run until `2027-03-18T13:00:00Z`: at that run offset 3 is recorded `failed` with reason
  `superseded_by_next_step` (attempts = 1) and no retry call is made for it; offset 7 is sent. Confirmed by: automated test.
- **R-7.AC5 boundary (throttle).** Transport scripted: "retry later" ×2 then accept. Three runs one hour apart: 1 message,
  attempts counter 1 (throttle responses did not consume attempts). Confirmed by: automated test.
- **R-7.AC6 positive (leaves scope).** INV-1009 with the first call timing out at `2027-03-14T13:00:00Z`; the invoice is paid
  at `2027-03-14T13:30:00Z`; run at `14:00:00Z`: no call; the record ends `failed` with reason `no_longer_eligible`.
  Confirmed by: automated test.

### R-8 Staff can see what was sent, skipped and failed  *(derived from R-3/R-7)*

Basis: `REQ-2026-11-21` ("reminders": an automatic action must be inspectable). Added. Pending: implementation and checks.
Behaviour: for each invoice, staff can list reminder records: offset, scheduled instant (UTC), state, reason (for `skipped`
and `failed`), attempts, instant of last attempt, and the recipient address used. Every state change also emits one log event
`reminder.sent`, `reminder.failed` or `reminder.skipped` carrying invoice number, offset, record ID, reason and attempt
count, and never the recipient address or the message body. A failure to write a log event does not change the send result.
Consumer outcome: "did the customer get reminded?" and "why not?" are answerable without reading code.
Open: G-7, G-9.

- **R-8.AC1 positive.** After R-2.AC5 (INV-1002): history lists (INV-1002, 3) `skipped` reason `superseded`; (INV-1002, 7)
  `sent`, attempts 1, scheduled `2027-03-23T13:00:00Z`, recipient `ap@example.test`; (INV-1002, 14) `sent`. Confirmed by: the
  history surface (G-9) via automated test comparing all fields exactly.
- **R-8.AC2 failure/boundary (log hygiene).** Captured log output for the run at `2027-03-14T13:00:00Z` (INV-1001) contains
  one `reminder.sent` event with `INV-1001`, offset 3 and the record ID, and contains neither `ap@example.test` nor the string
  `1,200.00`. Confirmed by: automated test over captured log output.
- **R-8.AC3 failure (log sink down).** The log sink throws on write; the run still sends the message and records `sent`.
  Confirmed by: automated test.
- **R-8.AC4 n/a (unauthorised reader).** Authorisation of history reads depends on the role model: `n/a until G-7`, then
  one negative line is added (an account without invoice access receives a denial and no records).

### R-9 State, ownership and personal data of reminders  *(derived, state and information lifecycle)*

Basis: `REQ-2026-11-21`; required by the lifecycle assessment, in proportion to the request. Added. Pending: implementation
and checks. See "State and data assessment" for the full table.
Behaviour: reminder records and configuration are owned by the invoicing product (not by the mail provider, not by the
developer's machine) and survive evaluator restarts. The record stores the recipient address used (a snapshot) so history is
accurate after a contact change. Records live as long as their invoice (A-11). Deleting an invoice removes its records;
erasing a customer's personal data removes the snapshot addresses on that customer's records (the records remain with the
address replaced by `erased`). Logs never hold recipient addresses (R-8.AC2).
Consumer outcome: reminders neither re-send after a restart nor leak addresses into logs.
Open: G-5 retention.

- **R-9.AC1 positive (restart).** After R-2.AC1's first run, discard the evaluator process and construct a new one over the
  same store; run at `2027-03-14T13:05:00Z`: zero new messages, record (INV-1001, 3) still `sent`. Confirmed by: automated test.
- **R-9.AC2 positive (snapshot).** After offset 3 is sent to `ap@example.test`, the contact is changed to `ap2@example.test`;
  history still shows `ap@example.test` for offset 3; the offset 7 message at `2027-03-18T13:00:00Z` goes to
  `ap2@example.test`. Confirmed by: automated test.
- **R-9.AC3 failure/boundary (deletion and erasure).** Delete INV-1001: its records are gone and a run sends nothing for it.
  Separate case: erase the customer of INV-1002: the records' recipient reads `erased`; the status and offsets remain.
  Confirmed by: automated test.
- **R-9.AC4 n/a (retention number).** Retention period: `n/a until G-5`; A-11 applies and is the stated default.

## Non-functional requirements

- **NFR-1 Timeliness.** Unresolved bound (G-4); no number is invented. Observable meaning today: a reminder is never sent
  before its scheduled instant (R-2.AC2) and is sent at the first run at or after it. The evaluator's run frequency is a
  plan decision once G-4 is answered. Verification: R-2 acceptance lines; a bound, when given, becomes a timed check.
- **NFR-2 Reliability and recovery.** Operating conditions: overlapping, repeated and interrupted evaluator runs (A-10);
  provider timeouts and outages. Required response: R-6 and R-7. Verification: R-6.AC2/AC3, R-7 lines, R-9.AC1. Unattended
  execution without the developer's workstation: G-11, verified against the real runtime at product acceptance.
- **NFR-3 Privacy and security.** The recipient address and invoice amounts are personal/financial data; they appear in the
  customer's email, the reminder record (R-9) and nowhere in logs (R-8.AC2). The mail provider credential lives in the
  platform's secret facility; only its alias and mechanism are recorded in `architecture.md`; no value appears in the repo,
  spec, logs or history. Access to configuration, pause and history follows G-7. Verification: R-8.AC2; a secret-scan of the
  diff at test; access-control checks after G-7.
- **NFR-4 Capacity and provider limits.** Unresolved (G-2, G-10): volume and provider rate limits are unknown, so no bound
  is invented. Required behaviour under throttling is fixed by R-7.AC5. Verification: a load figure, when given, becomes a
  bounded test with the recording double and a real-boundary rate check in the sandbox.
- **NFR-5 Time correctness.** All instants are computed with the IANA time zone rules of the configured zone and stored as UTC
  instants. Verification: R-2.AC2, R-2.AC3, R-2.AC7 (daylight-saving boundaries, exact instants).
- **NFR-6 Interface quality (applies only if planning adds a screen, G-9).** If the configuration, pause or history surface is
  a new graphical page, it needs: a consistent visual system (spacing and type scales; a light palette with a dark theme);
  designed empty (no reminders yet), loading and error states; a layout that works at 360 px and 1280 px wide with no
  horizontal overflow; visible keyboard focus and WCAG AA contrast (4.5:1 body text); motion only to explain a change and
  disabled under `prefers-reduced-motion`; one icon set. Visual reference (new web UI, no established identity known: G-1): the
  light Gemini look with Material 3 Expressive principles (UI visual-direction guide, "light expressive starting point");
  starting appearance light with a dark option; the plan records concrete tokens in an AD. An existing product identity or
  platform convention found in discovery takes precedence. Verification: rendered check at both widths in both themes,
  keyboard walk, contrast measurement. If no screen is built, this line is excluded for that reason.
- **NFR-7 Email accessibility.** The message has a plain-text body (R-3), no information carried by colour or images alone. If
  an HTML part is added later it needs AA contrast and a text alternative. Verification: R-3.AC1 asserts the plain-text part.
- **NFR-8 Compatibility and operability.** Runtime and language are unknown (G-1, G-11) and recorded in `architecture.md` after
  discovery. Operator-visible failures: R-8. Rollback: disabling the feature (R-1.AC5) stops all sending; sent messages cannot
  be recalled.
- **Exclusions with reasons.** Availability target: not specified by the request and the feature is a background job whose
  outage delays reminders (R-2 catch-up covers recovery); no target invented. Internationalisation: A-9.

## State and data assessment

| State | Owner and location | Who may read / write | Concurrent changes | Ends and removal | Quotas |
| --- | --- | --- | --- | --- | --- |
| Reminder configuration (enabled, offsets, time, timezone, E) | Invoicing product's settings store (location: G-1) | read/write: staff, A-12 | last write wins; a run uses the snapshot read at its start | lives until the product is removed; disabling keeps it | none known |
| Reminder record (invoice, offset) → state, reason, attempts, lease, recipient snapshot, scheduled instant | Invoicing product's store; created by the evaluator | read: staff who can read the invoice; write: evaluator only | unique key (invoice, offset) decides; claim is atomic (R-6) | removed with the invoice; recipient replaced on customer erasure (R-9) | none known |
| Hold flag per invoice; opt-out flag per customer | Invoicing product's store | read/write: staff | idempotent set/clear; the state at evaluation decides (R-5) | removed with the invoice/customer | none |
| Invoice status, balance, due date, contact | Invoicing system (authority; G-1) | evaluator reads only | the evaluator never writes these | not owned here | none |
| Message in flight | Mail provider | n/a | idempotency key | provider's own retention (G-2) | provider limits (G-2, G-10) |

Before/after invariants: for every (invoice, offset) at most one record exists; a record in `sent` never returns to another state;
the evaluator changes no invoice field; disabling or pausing never deletes records. Recovery: a `sending` record past its lease is
retried with the same key (R-6.AC3). Personal data: the recipient address is shown in the customer's email and staff history, stored
in the record snapshot, never logged, kept as long as the invoice (A-11/G-5), removed on invoice deletion or customer erasure (R-9.AC3).
Add no identity, sharing or persistence beyond this: no new user accounts, no customer-facing login.

## Service boundaries

- **Invoice store (authority for status, balance, due date, contact).** Current authority: re-read immediately before each
  send; no cache (R-4). Freshness versus revocation: a payment, void or hold made before the read stops the send; one made after
  the provider accepted the message cannot recall it (R-4.AC4, R-5.AC2). Incremental state: the evaluator writes only reminder
  records and leaves other invoice changes untouched. Event coverage: none consumed; the evaluator polls by evaluation.
- **Mail provider (external).** Completion: acceptance by the provider is recorded as `sent`; delivery, bounce and complaint
  events are not consumed (out of scope, and whether the provider offers them is G-2). Idempotency key = record ID. Unknown
  outcome and crash: R-6.AC3. Throttling: R-7.AC5. Owned events: `reminder.*` logs (R-8); the provider's own delivery logs are
  reused for delivery questions and need access (G-2).
- **Scheduler/trigger (platform).** The unattended job invoking the evaluator, which is idempotent and tolerates overlap (R-6).
  Completion needs no return value. Recovery: the next run catches up (R-2 rule 2). Runtime unknown (G-11).
- Inapplicable: user-session cache and authorization revocation (no customer login), inbound webhooks (none consumed), a message
  queue or broker (no demonstrated dispatch gap; the reminder record is the durable work state).

## Flows and transitions

**F-1 Evaluator run** (actors: scheduler → evaluator → invoice store → reminder store → mail provider → customer; satisfies R-2..R-9).
1. Scheduler starts the evaluator at time T. 2. Evaluator reads the configuration snapshot; if disabled, stop (R-1.AC5).
3. For each candidate invoice, compute due offsets with instants ≤ T and no record (R-2). 4. Record `skipped: before_enablement` for
those earlier than E; record `skipped: superseded` for all but the largest remaining. 5. Re-read the invoice (R-4); if out of scope,
stop for it. 6. Check hold/opt-out (R-5) and recipient (R-3): record `skipped` with reason. 7. Atomically create the record `sending`
with a lease (T-1); if one exists, stop (R-6). 8. Call the provider with the idempotency key. 9. On acceptance set `sent` (T-2); on
transient failure keep retryable (T-4); on permanent rejection set `failed` (T-5). 10. Emit the log event (R-8).

| T | Before | Trigger and guard | After | Requirement | Cases |
| --- | --- | --- | --- | --- | --- |
| T-1 | no record | offset due, in scope, not held, recipient valid, claim wins | `sending` (attempt 1, lease) | R-6 | R-6.AC1, AC2 |
| T-2 | `sending` | provider accepts | `sent` | R-3, R-7 | R-2.AC1, R-7.AC1 |
| T-3 | no record | due but before E / superseded / held / opted out / no recipient | `skipped` (reason) | R-2, R-3, R-5 | R-2.AC3, AC5, R-5.AC1, R-3.AC3 |
| T-4 | `sending` | transient failure, attempts < 3, still current and in scope | `sending` retryable (attempt+1) | R-7 | R-7.AC1, AC5 |
| T-5 | `sending` | permanent rejection, or attempts = 3, or next offset due, or invoice left scope | `failed` (reason) | R-7 | R-7.AC2, AC3, AC4, AC6 |
| T-6 | `sending`, lease expired | later run | `sending` (retry with same key) | R-6, R-7 | R-6.AC3 |
| T-7 | `sent`, `failed`, `skipped` | any later run | unchanged (terminal; no resend) | R-6 | R-6.AC1, R-9.AC1 |

Forbidden or ignored events: a repeat run on a terminal record is a no-op (T-7) that changes no data and sends nothing; a hold
or release on an invoice already in that state is a no-op (R-5.AC4).

## Traceability

| Request outcome | Requirements | Acceptance lines |
| --- | --- | --- |
| O-1 set up | R-1 | R-1.AC1..AC6 |
| O-2 automatic | R-2, R-6, R-7, R-9 | R-2.AC1..AC7, R-6.AC1..AC4, R-7.AC1..AC6, R-9.AC1 |
| O-3 reminders | R-3, R-8 | R-3.AC1..AC4, R-8.AC1..AC3 |
| O-4 unpaid invoices | R-4, R-5 | R-4.AC1..AC7, R-5.AC1..AC4 |

Scope: everything above traces to O-1..O-4; R-5, R-8 and R-9 are derived and labelled so, with R-5 droppable (A-8). Domain rules
the request leaves out are listed under the R they bound (R-1 templates, R-2 pre-due/escalation/late fees, R-3 attachments/payment
link, R-4 reversals, R-5 self-service unsubscribe, R-7 manual resend).

## Evidence and limits

- Nothing was executed: no product exists and no repository was provided. No acceptance line is claimed as passed.
- The calendar arithmetic of the fixture (weekdays, daylight-saving date 2027-03-14, UTC conversions) was computed by hand
  and cross-checked by counting days (February 2027 has 28 days; 2027-03-01 is a Monday). A Python recomputation was attempted
  but the command was not approved in this environment, so it is `NOT-REPLAYED: tool run not permitted`; the planning stage
  should recompute each instant with the chosen runtime's timezone library before the tests are written.
- Walks of ordered procedures from their stated start (reachability checked against the spec rules): the INV-1001 sequence
  (R-2.AC1 → R-4.AC2 → R-4.AC3) — offset 3 sent at 03-14T13:00Z with balance 1,200.00; payment 600.00 on 03-16 (an invoicing-system
  action, assumed permitted, G-1); offset 7 on 03-18 sees 600.00; remaining payment 03-20; offset 14 on 03-25 finds balance 0.00
  and sends nothing. Recomputed result matches the lines as written. The INV-1002 catch-up (R-2.AC5): due 03-16, runs absent
  03-19..03-24, first run 03-25 finds offsets 3 (03-19) and 7 (03-23) due, sends 7 with "9 days overdue" (25 − 16), skips 3;
  offset 14 (03-30) not yet due. The INV-1008 hold (R-5.AC1) and INV-1007 due-date change (R-2.AC6) walk likewise. The R-2.AC6 start
  needs the invoicing system to allow editing an unpaid due date (G-1): recorded as an open prerequisite, not assumed true.
- Weaker-stand-in check: exact subject/body strings (R-3.AC1), equal idempotency keys (R-6.AC3), exact instants on both sides
  of each boundary, and zero-call/zero-record assertions are required, so a hardcoded value, a count-only test or a title-only
  test would not pass.
- No documented command exists yet; none was run. No prior accepted version exists, so no requirement was dropped or weakened.
- No platform or library claim is relied on except that an IANA-zone-aware library resolves a nonexistent local time forward and
  that the provider may support an idempotency key; both are marked unverified (R-2.AC7 and G-2) and are probes for planning.

## Retired

None. No earlier requirement existed.

## Submission

- `summary`: Specification for automatic reminders on unpaid invoices, written without any repository, discovery or baseline
  (all current-system behaviour unknown; G-1 first for the next run). Nine requirements R-1..R-9 with replayable acceptance
  lines on a shared dated fixture (daylight-saving boundary included), eight non-functional requirements, state/data and
  service-boundary assessments, a flow and transition ledger. Material requirement conflicts: none open. Open gaps: G-1 invoicing
  system and statuses (blocks R-4's mapping and end-to-end checks), G-2 mail provider and credentials (blocks the real delivery
  check R-3.AC4, left `NOT-VERIFIED`), G-3 compliance, G-4 timeliness bound, G-5 retention, G-6 payment link, G-7 roles, G-8
  confirmation of the defaults, G-9 consumer surface, G-10 volume/quota, G-11 unattended runtime. Assumptions recorded for open choices:
  A-1 overdue only; A-2 email to the billing contact; A-3 offsets 3/7/14 days at 09:00 business timezone; A-4 ships disabled;
  A-5 no retroactive reminders; A-6 configuration limits; A-7 three attempts; A-8 pause/opt-out included and droppable; A-9 English,
  single format; A-10 evaluator runs at any frequency, may overlap; A-11 history kept with the invoice; A-12 invoice editors manage
  reminders. Architecture decisions are AD-1..AD-5 in `architecture.md`. Duty 11 omitted (no `backchain-check` here).
- `primary`: R-1, R-2, R-3, R-4, R-6, R-7. (R-6 and R-7 are what makes "automatic" safe, so they are listed with the directly
  requested outcomes: set up, schedule, send, only unpaid.) R-5, R-8 and R-9 are derived.
- `evidence_refs`: `KNOWLEDGE/spec.md` (sections: Request and basis, Assumptions, Open gaps, Shared fixture, Requirements R-1..R-9,
  Non-functional requirements, State and data assessment, Service boundaries, Flows and transitions, Traceability, Evidence and
  limits); `KNOWLEDGE/architecture.md` (Decisions AD-1..AD-5); sources used: the request `REQ-2026-11-21`; guides
  `GUIDES/behavioral-requirements.md` (Behavior model, Traceability and review, Actors/channels/state ownership),
  `GUIDES/requirements-definition.md`, `GUIDES/service-discovery.md` (Runtime state placement, Asynchronous cooperation,
  Observability coverage, Verification), `GUIDES/platforms/ui.md` (light expressive starting point). No discovery, research,
  baseline or backchain receipt exists.
