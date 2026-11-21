# Invoicing: automatic payment reminders (living product spec)

Status of this document: accepted intent is the request below plus the numbered decisions D-n, which are **defaults
chosen by the spec stage** (labelled as such, not user requirements). Nothing here is implemented or verified.
Structure and technology choices live in `architecture.md` (AD-n), never here.

## Request and basis

- **Request (2026-11-21):** "Set up automatic reminders for unpaid invoices."
- **Basis for every R-n below:** that request's words, 2026-11-21, plus the decision IDs it cites.
- **Baseline:** none. This run had no repository, no discovery result, no research result and no earlier spec. The
  current system is **unknown**, not absent. Every statement about an existing invoicing product is an assumption (D-2)
  or an open gap (OG-1). Preserved behaviour: none could be inspected; the plan's first step must reopen the real
  invoicing product and reconcile (preserve/modify) against it before any R-n that reads invoices is built.
- **Evidence limits:** no source was inspected. No platform, library or provider capability is claimed anywhere in this
  spec; capabilities are verified by the plan against primary documentation (architecture.md AD-6).

### Request outcomes → requirements

| Outcome from the request | Requirements | Acceptance lines |
| --- | --- | --- |
| O-1 "Set up": the business can turn reminders on and shape them | R-1, R-9 | AC-1.1–1.7, AC-9.1–9.4 |
| O-2 "automatic": reminders go out on schedule with no manual step | R-3, R-11 | AC-3.1–3.8, AC-11.1–11.4 |
| O-3 "reminders": the customer receives a useful, correct message, once | R-4, R-5, R-6 | AC-4.1–4.6, AC-5.1–5.4, AC-6.1–6.5 |
| O-4 "unpaid invoices": only invoices still owing are reminded, and reminders stop on payment | R-2 | AC-2.1–2.6 |
| O-5 (implied) the business can see and stop what is being sent in its name | R-7, R-8, R-10 | AC-7.1–7.3, AC-8.1–8.4, AC-10.1–10.3 |

**Primary requirements (what the user asked for directly):** R-1, R-2, R-3, R-4.

## Decisions and assumptions (product defaults, each open to the owner)

| ID | Default chosen | Why |
| --- | --- | --- |
| D-1 | Channel is **email only**. | Cheapest channel that reaches a customer; the request names none. |
| D-2 | The feature is added to an **existing invoicing product** that already has accounts (tenants), invoices with `id`, `number`, `status`, total, amount paid, currency, due date, date opened, customer name and billing email, and an owner-facing web UI. Reminders only **read** invoices (D-17). | The request says "invoices", implying they already exist. Unverified: OG-1. |
| D-3 | Reminders are **off until the owner turns them on**. Prefilled schedule: offsets **−3, 0, +7, +14** days relative to the due date; send time **09:00** account-local. | Customer-facing sends must not start by surprise. Offsets/time are a conventional starting point, not a requirement. |
| D-4 | **Unpaid** = status `open` (issued, not draft, not void) **and** outstanding balance (total − paid) > 0. A partial payment leaves it unpaid; the reminder states the **outstanding** amount. | Matches "unpaid"; partial payment is the common edge. |
| D-5 | A step (invoice × offset) may be sent on its **step date** or the **one following calendar day** (its window). At most **one reminder per invoice per calendar day**; if two steps are eligible, the later offset is sent and the earlier is `skipped: superseded`. | Bounded catch-up after an outage without delayed floods. |
| D-6 | Evaluation runs on a **tick at least hourly**; a step is processed at the first tick at or after the account-local send time on an eligible day. | Gives a timeliness bound without per-invoice timers. |
| D-7 | **No backfill.** A step is eligible only if its step date is **on or after** (a) the date the invoice became open and (b) the date reminders were last enabled / the offset was added to the schedule (account time zone, inclusive). | Prevents blasting a backlog of overdue customers the day the feature is enabled. |
| D-8 | **At most once per (invoice, offset)**, ever. Editing the due date or schedule never re-sends an offset already sent. | A customer-facing duplicate is worse than a missed reminder. |
| D-9 | Transient provider failure: up to **3 attempts per step**, one per tick; a definitive hard failure (invalid address) is not retried. | Bounded retry. |
| D-10 | An attempt whose outcome is **unknown** (crash or timeout after handoff) is **never resent automatically**; it is shown as `unknown`. | At-most-once beats guessing. |
| D-11 | The owner can **pause/resume reminders for one invoice** (e.g. payment plan). | Minimal override; not requested directly, droppable (OG-11). |
| D-12 | Schedule validation: 1–6 offsets, distinct integers in −30…+90; send time a whole hour 00–23. | Keeps the form and tick simple. Product bounds, not platform limits. |
| D-13 | **No customer-facing unsubscribe link** in v1; replies go to the business's address. Compliance is an open person-only item (OG-4). | Not decidable by this stage. |
| D-14 | History records live **as long as the invoice**; deleted with it. No numeric retention (OG-9). | Avoids an invented retention period. |
| D-15 | UI is **light first with a dark option**, following the light Google Gemini look with Material 3 Expressive principles, unless the host product has its own identity (OG-7). | UI visual-direction guide; precedence rule keeps host identity first. |
| D-16 | Email body is **inline text/HTML**, no PDF attachment; contains a pay link only if the host has one (OG-5). | Smaller surface. |
| D-17 | Reminders **never change** invoice status, amounts or dates. | Keeps the invoice's authority where it is. |
| D-18 | Account time zone is the host account's setting; **UTC** if the host has none (OG-3). Step dates are calendar dates in that zone. | |
| D-19 | Turning reminders on requires an **explicit confirmation** naming the schedule and earliest possible send date. | Same reasoning as D-3. |
| D-20 | The settings page's failed/unknown alert counts invoices with such a step in the last **30 days**. | A product default for R-8. |
| D-21 | Roles: changing settings needs the host's account-admin role; viewing history needs permission to view that invoice; pausing needs permission to edit it. | Least surprise; real roles unknown (OG-6). |

## Requirements

Acceptance-line format: `AC-<R>.<n> [kind] statement — Surface: … — Confirmed by: …`. Kinds: positive / failure /
boundary; a kind is omitted only where another line already covers it or is marked `n/a: <reason>`.
Surfaces: **CH-MAIL** the customer's mailbox (a test mailbox or provider-capture), **CH-SET** the reminder settings
page and the API behind it, **CH-HIST** the per-invoice reminder history view, **CH-OPS** the operational event log.
"Time-controlled test" = an automated test with an injectable clock and a stand-in email provider that records
handoffs; it proves rules, not real delivery (see NFR-2, OG-2).

Worked data used in acceptance lines (concrete and replayable; date arithmetic done by hand, see Evidence):

- **Account ACME-1** "Northwind Studio", time zone America/Chicago, schedule [−3, 0, +7, +14], send time 09:00,
  reminders enabled 2026-12-01.
- **INV-1001** total 1200.00 USD, paid 0.00, opened 2026-12-01, due **2026-12-15**, billing `billing@customer-a.example`.
  Step dates: −3 → **2026-12-12**, 0 → **2026-12-15**, +7 → **2026-12-22**, +14 → **2026-12-29**.
- **INV-1002** as INV-1001 but total 800.00, paid in full on 2026-12-14.
- **INV-1003** total 500.00, due 2026-12-15, 200.00 paid on 2026-12-20 (outstanding 300.00).
- **INV-1004** due **2026-12-10**, opened 2026-11-20, total 640.00; reminders enabled 2026-12-20. Step dates: −3 → 2026-12-07,
  0 → 2026-12-10, +7 → 2026-12-17, +14 → **2026-12-24**.
- **INV-1007** as INV-1001 (ACME-1, due 2026-12-15, opened 2026-12-01) but with an empty billing address.
- **ACME-2** schedule [0, +1], other settings as ACME-1; **INV-2001** due 2026-12-15, opened 2026-12-01.

### R-1 Enable and configure the reminder schedule (primary)

Basis: request "Set up automatic reminders", 2026-11-21; D-3, D-12, D-18, D-19. Preserved: n/a (new). Changed: adds
account-level reminder settings. Locators: none (no baseline). Pending: implementation, all checks. Unknown: OG-1, OG-3, OG-6.

Behaviour: an authorised user (R-9) of an account sees reminders **off** by default, can edit offsets and send time,
and can turn reminders on after confirming (D-19). Saving applies from the next tick. Disabling stops new sends
immediately for ticks that start after the save; an attempt already handed to the provider may complete.
Boundaries: D-12 limits; D-7 enablement date. Error behaviour: an invalid draft is rejected whole, saved settings are
unchanged, the draft stays in the form with the faulty field named. Consumer outcome: the owner can tell, from the page,
whether reminders are on, the schedule, and the send time.

- AC-1.1 [positive] Fresh account ACME-1 opens settings: state shows "Off", prefilled −3, 0, +7, +14 and 09:00. Enabling
  shows a confirmation naming that schedule and the earliest send date; confirming turns it on and the page shows "On"
  only after the server confirms (no optimistic "On"). — CH-SET — UI test + API test.
- AC-1.2 [boundary] Cancelling the confirmation leaves reminders Off and the stored settings unchanged; a reload shows Off.
  — CH-SET — UI test.
- AC-1.3 [failure] Saving offsets [0, 0] (duplicate), [] (empty), [7 entries], [91], [−31], [1.5] is each rejected with the
  offending field identified; stored settings are unchanged. Offsets [−30] and [90] and exactly 6 distinct entries are
  accepted. — CH-SET — API test of each value.
- AC-1.4 [failure] Send time 24 or "9:30" is rejected; 0 and 23 are accepted. — CH-SET — API test.
- AC-1.5 [failure] If the save request fails (server error), the page shows the error, keeps the user's draft and the
  last confirmed state label; it never shows an unsaved value as saved. — CH-SET — UI test with a forced 500.
- AC-1.6 [boundary] Disabling then re-enabling on 2026-12-20 sets a new enablement date (D-7): INV-1004's steps dated before
  2026-12-20 do not send (see AC-3.5). Offsets already `sent` stay `sent`. — CH-SET + CH-MAIL — time-controlled test.
- AC-1.7 [boundary] Two users saving different schedules at once: the later save wins whole (no field mix), and the page of the
  earlier saver shows the stored result after its response. — CH-SET — API test with two interleaved saves.

Left out (domain rules): per-customer or per-invoice schedules, editable email templates, SMS/other channels.
Open gap: OG-3 (zone source), OG-6 (who counts as authorised). State/data: settings record per account, owner = this
feature, changed by R-1, read by ticks; before/after invariant: always a complete valid schedule; recovery: a failed save
leaves the previous record.

### R-2 Which invoices are reminded (primary)

Basis: request "unpaid invoices", 2026-11-21; D-4, D-17. Preserved: n/a. Changed: adds the selection rule. Pending: all
checks. Unknown: OG-1 (real status and payment fields).

Behaviour: an invoice is a candidate only while it is unpaid (D-4) **at the moment of sending** (the invoice source is
re-read after claim and before handoff, R-5). A paid, void or draft invoice gets no reminder; reminders stop permanently
once outstanding is 0. Reminders never modify the invoice (D-17). Consumer outcome: customers who have paid are not asked
to pay.

- AC-2.1 [positive] INV-1001 (open, outstanding 1200.00) is a candidate on its step dates (AC-3.1). — CH-MAIL — time-controlled test.
- AC-2.2 [failure] INV-1002 (fully paid 2026-12-14): the 2026-12-15, 2026-12-22 and 2026-12-29 steps send nothing; only the
  2026-12-12 reminder exists in history. — CH-MAIL + CH-HIST — time-controlled test.
- AC-2.3 [boundary] Payment recorded after the last read but before provider handoff may still produce one reminder (accepted
  residual window, D-17 prevents any status change); payment recorded before the post-claim re-read produces none and the
  step ends `skipped: paid`. — CH-HIST — test with a payment injected between claim and re-read.
- AC-2.4 [boundary] INV-1003 (partial payment, outstanding 300.00) still gets its 2026-12-22 reminder stating 300.00 outstanding. — CH-MAIL — test.
- AC-2.5 [failure] Draft and void invoices receive no reminder even when their due date matches a step date. — CH-MAIL — test per status.
- AC-2.6 [boundary] An invoice that is `open` with outstanding exactly 0.00 is not reminded; outstanding 0.01 is. — CH-MAIL — test.

Left out (domain rules): late fees, interest, credit-note handling beyond outstanding balance, disputes (use pause, R-7),
multi-currency conversion (the invoice's own currency is shown). Open gap: OG-1.

### R-3 When a reminder is due (primary)

Basis: request "automatic", 2026-11-21; D-3, D-5, D-6, D-7, D-8, D-18. Preserved: n/a. Changed: adds timing. Pending: all
checks. Unknown: OG-3, OG-12 (the numeric tick interval is a D-6 default).

Behaviour: step date = due date + offset (calendar days, account zone). A step becomes processable at the first tick at
or after the account-local send time on its step date, and stays processable through the end of the next calendar day (D-5).
It is eligible only under the no-backfill rule (D-7). At most one reminder per invoice per day; later offset wins.
Editing the due date moves unsent steps; an offset already sent is not resent (D-8). Removing an offset cancels it if unsent.
Consumer outcome: customers get each reminder once, around the intended day.

- AC-3.1 [positive] ACME-1/INV-1001, time-controlled: a tick at 2026-12-12 14:59 UTC (08:59 CST) sends nothing; a tick at 15:00 UTC
  (09:00 CST) sends one email (−3). Likewise one email each on 2026-12-15, 2026-12-22, 2026-12-29 at 15:00 UTC; none on other days. — CH-MAIL — time-controlled test.
- AC-3.2 [boundary] A second tick at 2026-12-12 16:00 UTC sends nothing further for INV-1001. — CH-MAIL — test.
- AC-3.3 [boundary] Catch-up: scheduler not running on 2026-12-22; resumes 2026-12-23 15:00 UTC → the +7 reminder is sent then.
  Resumes 2026-12-24 15:00 UTC → +7 is not sent, history shows `skipped: not-run`, and the +14 step still sends on 2026-12-29. — CH-MAIL + CH-HIST — test.
- AC-3.4 [boundary] ACME-2/INV-2001, scheduler down on 2026-12-15, resumes 2026-12-16 15:00 UTC: offsets 0 and +1 are both eligible;
  exactly one email (+1) is sent and offset 0 is `skipped: superseded`. — CH-MAIL + CH-HIST — test.
- AC-3.5 [boundary] No backfill: INV-1004, reminders enabled 2026-12-20: no email on 2026-12-20 for the 12-07, 12-10, 12-17 steps;
  one email on 2026-12-24 (+14). A step dated the enablement day itself is eligible: enabling at 10:00 local on a step date sends at the next tick. — CH-MAIL — test.
- AC-3.6 [boundary] An invoice opened after a step date (opened 2026-12-14 with due 2026-12-15 on ACME-1) gets no −3 reminder and
  gets 0, +7, +14. — CH-MAIL — test.
- AC-3.7 [boundary] Due date of INV-1001 moved from 2026-12-15 to 2026-12-22 after the −3 reminder was sent: no second −3; the remaining
  steps follow the new date (0 → 2026-12-22). — CH-MAIL — test.
- AC-3.8 [boundary] Time-zone gap: account in America/Chicago with send time 02:00 on 2027-03-14 (that local hour does not exist): the step is
  processed at the first tick whose local time is at or after the gap, i.e. 08:00 UTC (03:00 CDT), and sent once. Not machine-checked, see Evidence. — CH-MAIL — test.

Left out: business-day calendars, holidays, per-customer time zones. Open gap: OG-3, OG-12.
State/data: the step ledger (R-5) is the only record of "sent"; the date rule is derived from invoice due date + settings and
holds no state of its own.

### R-4 Reminder email: recipient and content (primary)

Basis: request "reminders", 2026-11-21; D-1, D-13, D-16, D-17. Preserved: n/a. Pending: all checks. Unknown: OG-2, OG-5.

Behaviour: one email to the invoice's billing address, from the business's sender identity with Reply-To the business's address.
Three wording variants chosen by the invoice's position on the **send day**: before due, due today, overdue (days overdue stated).
Content: business name, customer name, invoice number, outstanding amount with currency, due date, days until/past due, pay link only
if the host has one (OG-5), and the business's contact line. No attachments. Money formatted in the invoice currency. The invoice's
**current** values at send time are used. Consumer outcome: a customer can identify the invoice and the amount without logging in.

- AC-4.1 [positive] INV-1001 on 2026-12-12: subject contains "INV-1001" and "due in 3 days"; body states 1200.00 USD outstanding and due date 2026-12-15, addressed to billing@customer-a.example. — CH-MAIL — time-controlled test asserting subject, recipient and body fields (not just "an email arrived").
- AC-4.2 [positive] Variants: 2026-12-15 body says "due today"; 2026-12-22 says "7 days overdue". — CH-MAIL — test.
- AC-4.3 [boundary] INV-1003 on 2026-12-22 states 300.00, not 500.00. — CH-MAIL — test.
- AC-4.4 [failure] Billing address empty or syntactically invalid at evaluation: no handoff; the step is not claimed (still processable within its window); at window end it resolves `skipped: no-recipient`. If the owner corrects the address while the window is open, the next tick sends. — CH-HIST + CH-MAIL — test: INV-1007 on ACME-1: nothing on 2026-12-12; address fixed 2026-12-13 10:00 UTC (04:00 CST) → sent at the 2026-12-13 15:00 UTC tick (09:00 CST, still inside the −3 window 12-12..12-13); if never fixed → `skipped: no-recipient` once 2026-12-13 has ended.
- AC-4.5 [boundary] Customer name or business name containing `<script>`, `"`, `&` or non-ASCII (e.g. "Zoë & Sons <x>") renders as inert text in the HTML part and intact in the text part. — CH-MAIL — test.
- AC-4.6 [boundary] Amount/currency formatting: 1234567.80 USD renders unambiguously with the currency code; zero-decimal currency (JPY 5000) renders without decimals. — CH-MAIL — test.

Left out: attachments, editable templates, localization of wording (single language; OG-13), payment collection. Open gap: OG-2 (sender
domain and authentication, person-only), OG-4 (compliance wording), OG-5 (pay link).

### R-5 At-most-once sending and concurrency

Basis: request "reminders" (a customer must not be nagged twice for one step); D-8, D-10. Pending: all checks. Unknown: none beyond OG-1.

Behaviour: before any handoff the system **claims** the step (invoice × offset) in a durable ledger; a claim for an existing
(invoice, offset) record is refused, so concurrent or repeated ticks never both send. After the claim the invoice is
re-read (R-2) and the handoff happens only if still valid. Evaluation uses the settings as saved when the claim is made. Reminders
never change the invoice. Consumer outcome: one email per step.

- AC-5.1 [positive] Two ticks run simultaneously for INV-1001 on 2026-12-12 → exactly one handoff and one ledger record (`sent`). — CH-MAIL + CH-HIST — concurrency test with two workers against the real ledger store (not a mock).
- AC-5.2 [boundary] A process restart between claim and handoff does not cause a second send: the stale claim resolves per R-11 (`unknown`), never re-sent. — CH-HIST — test killing the worker at that point.
- AC-5.3 [failure] If the invoice source cannot be read at the post-claim re-read, no email is sent, the claim is released (step back to unclaimed) and the next tick retries within the window. — CH-OPS + CH-MAIL — test with source failing.
- AC-5.4 [boundary] Settings saved while a tick is mid-run: steps already claimed complete under the old settings; the next claims use the new ones. — CH-MAIL — test.

Left out: exactly-once delivery (not promised; see R-6). State/data: ledger is the owner of step state; key (invoice, offset) unique;
partial effect = claim without outcome → R-11.

### R-6 Delivery failure, unknown outcome and bounces

Basis: request "reminders"; D-9, D-10. Pending: all checks. Unknown: OG-2 (provider semantics), OG-10 (bounce callbacks).

Behaviour: "sent" means the provider **accepted** the message, not that the customer read it. Transient provider failure: retry on later
ticks up to 3 attempts per step while the window is open; then `failed`. Definitive hard failure (e.g. invalid recipient): `failed` at once, no retry.
Unknown outcome: `unknown`, never auto-resent. If the provider later reports a bounce, `sent` becomes `bounced` (only where OG-10 holds).
Consumer outcome: the owner can see which customers were probably not reached.

- AC-6.1 [positive] Stand-in provider accepts → ledger `sent`, one attempt recorded with the provider's message identifier. — CH-HIST — test.
- AC-6.2 [failure] Stand-in rejects transiently on the 09:00, 10:00 and 11:00 local ticks of 2026-12-12 → after the third, `failed` (3 attempts); a 12:00 tick sends nothing. Accepting on the second attempt → `sent` with attempts = 2. — CH-HIST — test.
- AC-6.3 [failure] Hard reject (address does not exist) → `failed` after 1 attempt, no retry on the next tick. — CH-HIST — test.
- AC-6.4 [failure] Window ends (2026-12-13 end of day) while a step is still in retry → `failed` with reason window-expired; no send on 2026-12-14. — CH-HIST — test.
- AC-6.5 [boundary] Provider timeout after handoff (outcome unknown) → `unknown`, no resend on later ticks, visible to the owner; bounce callback (if available) on a `sent` record → `bounced`; a callback for an unknown message id is ignored and logged. — CH-HIST + CH-OPS — test; callback part blocked until OG-10.

Left out: delivery/open tracking, automatic escalation to another channel. Open gap: OG-10.

### R-7 Pause and resume reminders for one invoice

Basis: D-11 (design decision supporting "set up reminders", not requested directly). Pending: all checks. Droppable: OG-11.

Behaviour: an authorised user can pause an invoice. While paused no step is claimed; a post-claim re-read that finds it paused releases the claim.
Resuming makes steps whose window is still open processable again; steps whose windows passed while paused resolve `skipped: paused` and are not revived.
Pausing never alters invoice data (D-17).

- AC-7.1 [positive] INV-1001 paused on 2026-12-14, resumed 2026-12-23 15:00 UTC → +7 (window 12-22..12-23) is sent on resume; 0 is `skipped: paused`. — CH-MAIL + CH-HIST — test.
- AC-7.2 [boundary] Paused through the whole window of a step: history shows `skipped: paused` for it; resume later → the next step sends normally. — CH-HIST — test.
- AC-7.3 [failure] A user without rights to edit invoices cannot pause (R-9); state unchanged. — CH-SET — API test.

### R-8 Reminder history and failure visibility

Basis: O-5 (implied), D-14. Pending: all checks.

Behaviour: each invoice shows its reminder history: per offset, state (`sent`, `failed`, `unknown`, `bounced`, `skipped: <reason>`), time, attempts, recipient
address used. The account's settings page shows a count of invoices with a `failed` or `unknown` step in the last 30 days (D-20).
Empty history shows an explanatory empty state. Loading and error states are distinct.

- AC-8.1 [positive] INV-1001 after 2026-12-12: history lists "−3 · sent · 2026-12-12 09:00 CST · 1 attempt · billing@customer-a.example". — CH-HIST — UI test.
- AC-8.2 [boundary] Invoice with reminders on but nothing yet due: empty state reads that the next reminder is scheduled for 2026-12-12; with reminders off the empty state says reminders are off. — CH-HIST — UI test.
- AC-8.3 [failure] History fetch fails → error state with retry; the page does not show a stale or empty list as if it were truth. — CH-HIST — UI test with forced failure.
- AC-8.4 [boundary] Failed/unknown count: 0 hides the alert; 1 shows singular wording; a step older than 30 days is not counted. — CH-SET — test.

### R-9 Access control and tenant isolation

Basis: request implies customer-facing sends under an account's name; OG-6. Pending: all checks. Unknown: OG-6 (role mapping), default D-21: settings need the host's account-admin
role; viewing history needs permission to view that invoice; pausing needs permission to edit it.

- AC-9.1 [failure] A user lacking the admin role cannot change or enable settings (CH-SET returns forbidden, stored settings unchanged). — API test.
- AC-9.2 [failure] A user of account B requesting account A's invoice history gets not-found (no existence signal), and ticks for account A never read or write account B's records. — API test + ledger query test.
- AC-9.3 [positive] Admin of ACME-1 can enable, edit, pause and view. — API test.
- AC-9.4 [boundary] A user whose permission is revoked mid-session is refused on the next request (authority is checked per request, not cached in the page). — API test.

### R-10 Personal data, logging and retention

Basis: reminder emails carry customer names, addresses and amounts. D-14. Pending: all checks. Unknown: OG-9 (numeric retention), OG-4.

State of personal data: shown in the email (CH-MAIL) and in history to authorised users (R-9); stored in the ledger as invoice id, offset, state, timestamps, attempts,
provider message id and a **recipient-address snapshot**; the rendered body is **not** stored. Logs and CH-OPS events never contain the body, customer name or full address
(address masked as first character + domain). Removal: ledger rows are deleted with their invoice and with the account; customer data erasure in the host also removes the address snapshot.

- AC-10.1 [positive] After AC-4.1 runs, captured logs and CH-OPS events contain "INV-1001", offset −3 and outcome `sent`, and the masked address `b***@customer-a.example`; they contain none of the strings `billing@`, "1200.00", or any body sentence. — CH-OPS — test grepping captured logs for those exact strings.
- AC-10.2 [boundary] Deleting INV-1001 in the host removes its ledger rows and snapshots; history for it returns not-found. — CH-HIST — test.
- AC-10.3 [failure] A failing log sink must not stop sending nor leak the address into the error path. — CH-OPS — test with a failing sink.

### R-11 Scheduler operation, recovery and observability

Basis: request "automatic"; D-6, D-10. Pending: all checks. Unknown: OG-8 (volume, alert thresholds), OG-12.

Behaviour: the tick is idempotent and safe to run overlapping (R-5). A tick that dies mid-way leaves unprocessed work for the next tick. A claim in `sending` older than **one tick
interval** with no outcome resolves to `unknown` (no resend). Each tick emits start/finish events with counts (evaluated, sent, skipped, failed, unknown), and the time of the last completed
tick is readable by an operator.

- AC-11.1 [positive] A tick over ACME-1 emits `tick_started` and `tick_finished` with counts matching the ledger (e.g. sent=1 for 2026-12-12). — CH-OPS — test.
- AC-11.2 [failure] A tick killed after processing half the due steps: the next tick sends the rest, none twice. — CH-MAIL — test.
- AC-11.3 [boundary] A claim in `sending` for 59 minutes stays `sending`; at one interval (60 minutes, D-6) it resolves `unknown`. — CH-HIST — time-controlled test.
- AC-11.4 [failure] One account's failure (e.g. bad settings record) is logged and does not stop other accounts in the same tick. — CH-OPS — test.

## Flows, states and transitions

**F-1 Tick:** scheduler → for each enabled account → candidate steps (R-3) → claim (T-1) → re-read invoice (R-2) → handoff to provider → record outcome (T-2…). Serves R-2, R-3, R-5.
**F-2 Enable:** admin edits draft → confirmation (D-19) → server validates and saves → page shows server-confirmed state. Serves R-1.
**F-3 Failure/retry:** transient failure → `retry` → next tick re-claim until 3 attempts or window end. Serves R-6.

Step entity (per invoice × offset), durable, owner = this feature. States: *(unclaimed)* initial; `sending`; `retry`; `sent`, `failed`, `unknown`, `skipped:<reason>` terminal; `bounced` terminal.

| T-ID | R | Before | Trigger/guard | After | Failure/recovery |
| --- | --- | --- | --- | --- | --- |
| T-1 | R-5 | unclaimed | eligible (R-2, R-3, valid recipient), claim unique succeeds | `sending` | claim refused → no-op |
| T-2 | R-6 | `sending` | provider accepts | `sent` | — |
| T-3 | R-6 | `sending` | transient reject, attempts < 3, window open | `retry` | — |
| T-4 | R-6 | `retry` | next tick, window open, still unpaid | `sending` (attempts+1) | — |
| T-5 | R-6 | `retry` | window ends | `failed` (window-expired) | — |
| T-6 | R-2 | `retry` | invoice now paid/void | `skipped:paid` / `skipped:void` | — |
| T-7 | R-6 | `sending` | hard reject, or 3rd transient reject | `failed` | — |
| T-8 | R-11 | `sending` | no outcome after one tick interval | `unknown` | not resent |
| T-9 | R-3 | unclaimed | window ends, no send | `skipped:not-run` / `paused` / `no-recipient` (last suppression observed) | — |
| T-10 | R-3 | unclaimed | later step eligible same day | `skipped:superseded` | — |
| T-11 | R-5 | `sending` | re-read shows paid/void | `skipped:paid` / `skipped:void` | — |
| T-12 | R-5 | `sending` | re-read shows paused, no recipient, or source unreadable | unclaimed (claim released) | next tick retries |
| T-13 | R-6 | `sent` | bounce callback (if OG-10) | `bounced` | unknown id ignored |

Forbidden/no-op events: claim on any existing record (no-op, nothing sent); a callback or tick against a terminal state (no state change); editing history (not offered).

## State, data and lifecycle

| State | Owner/location | Who may read | Simultaneous change | Ends/removal | Runtime quotas |
| --- | --- | --- | --- | --- | --- |
| Reminder settings (per account) | this feature, durable store | authorised account users (R-9) | last full save wins; no field mixing | deleted with the account | unresolved: OG-8 |
| Step ledger (per invoice × offset) | this feature, durable store; unique (invoice, offset) | authorised users of that account only (R-9) | atomic unique claim (R-5) | deleted with invoice/account (D-14) | unresolved: OG-8 |
| Pause flag (per invoice) | this feature | invoice editors | last write wins | with invoice | — |
| Invoice data | **host invoicing product** (authority); read-only here (D-17) | as host | host rules | host | — |
| Draft settings form | browser memory only | the user | n/a | on navigation | — |

Identity/sharing/persistence additions beyond these: none. Platform mapping is a plan decision (AD-6).

## Service boundaries (verifiable contracts)

- **Invoice source (host):** authority for status, amounts, due date, recipient. Freshness: read at post-claim, immediately before handoff; no cached status used for the send decision.
  Revocation analogue: payment/void between claim and handoff handled by the re-read (AC-2.3). Incremental state: none held. Async: none. Unreadable → release claim (AC-5.3).
- **Email provider:** acceptance ≠ delivery. Handoff carries an idempotency key (invoice, offset) **if** the provider supports one (unknown, OG-2); the product does not rely on it (D-10). Completion: bounce callbacks optional (OG-10).
- **Scheduler trigger:** sole initiator of ticks; the durable step ledger is the recovery owner (AD-2). Owned events: `tick_started`, `tick_finished`, per-step `reminder_sent|failed|skipped|unknown|bounced` (R-11, R-10).
- Inapplicable: caching/authorization-freshness of cached data (no cache), cross-service event coverage beyond the above.

## Non-functional requirements

- **NFR-1 Timeliness.** Operating condition: scheduler healthy, provider up. A step due on a day is handed to the provider within **one tick interval (default 60 min, D-6)** after the account-local send time. Verified: time-controlled test (AC-3.1). Bound for a catch-up is D-5, not a latency promise.
- **NFR-2 Testability.** The clock and the email provider are replaceable in tests; every AC marked "time-controlled test" must run without waiting real time and without sending real mail. Verified: the tests exist. Real-provider smoke test to a test mailbox is a separate, person-gated check (OG-2); a stand-in alone never proves real delivery.
- **NFR-3 Reliability/durability.** Ledger and settings survive process restart; a restart never produces a second send (AC-5.2). Availability target: **unresolved** (OG-8), invented none.
- **NFR-4 Scale and quotas.** Invoices per account, accounts per tick, provider rate limit: **unresolved** (OG-8). Constraint without a number: a tick that cannot finish all work leaves the rest claimable by the next tick (AC-11.2), and respects provider rate limits when known.
- **NFR-5 Security/privacy.** R-9, R-10. Credentials for the provider are secret configuration, never in the ledger, logs or client.
- **NFR-6 Interface quality (the owner-facing settings and history UI).** Reference: light Google Gemini look and feel with Material 3 Expressive principles (D-15), unless the host product's identity (OG-7) takes precedence. Observable criteria, each checked on the rendered page in a browser at 360 px and 1280 px width:
  (a) one spacing scale and one type scale, a palette with a light theme as default and a dark option, tokens used consistently;
  (b) designed empty (AC-8.2), loading, error (AC-1.5, AC-8.3) and success states, not blank or raw text;
  (c) no horizontal scroll at 360 px or 1280 px;
  (d) visible keyboard focus on every control, text/control contrast at WCAG AA (4.5:1 text, 3:1 large text and controls);
  (e) motion only to explain a state change, disabled when the user prefers reduced motion;
  (f) one icon set;
  (g) the primary action (turn on / save) has the strongest visual weight on the settings page; the schedule is the focal element; the pending/saved state is always labelled.
  Concrete treatment is chosen by the plan (an AD). Verified: browser checks with screenshots, an automated contrast check, a keyboard-only pass.
- **NFR-7 Compatibility/operations.** Supported runtimes and deploy path: **unresolved** until OG-1. Exclusion: no separate availability SLA, load-test environment or new dependency is required by this request; reason: unspecified volume, small background job.
- **NFR-8 Observability.** R-11 events; operator-readable last-completed-tick time; alert thresholds unresolved (OG-8).

## Open gaps and unresolved decisions

| ID | Gap | Under | Effect |
| --- | --- | --- | --- |
| OG-1 | The real invoicing product: data model (status values, payments, due date, recipient), accounts, UI, stack. No repository was supplied. | R-1…R-11 | Work that reads invoices or adds UI is **unready** until the plan's first item inspects the product and reconciles D-2. Spec behaviour stays valid. |
| OG-2 | Email provider, sender domain, SPF/DKIM/DMARC, idempotency-key support. Person-only. | R-4, R-6 | Real-delivery check cannot run; stand-in tests proceed. |
| OG-3 | Source of the account time zone; D-18 default is the host setting else UTC. | R-1, R-3 | Non-blocking. |
| OG-4 | Compliance/legal wording and whether an opt-out is required in the target jurisdictions. Person-only. | R-4, R-10 | Non-blocking for build; blocks production enablement until reviewed. |
| OG-5 | Whether a pay link exists in the host. | R-4 | AC-4.1 body check omits the link if none. |
| OG-6 | Role mapping for "authorised" (D-21 default). | R-1, R-7, R-9 | Non-blocking. |
| OG-7 | Whether the host has a visual identity to inherit. | NFR-6 | Non-blocking; D-15 applies if none. |
| OG-8 | Volume, availability target, provider rate limit, alert thresholds. No bound invented. | NFR-3, NFR-4, NFR-8, R-11 | Dependent capacity/alert checks stay unready; behaviour checks proceed. |
| OG-9 | Numeric retention for history. D-14 ties it to the invoice. | R-10 | Non-blocking. |
| OG-10 | Provider bounce callbacks available? | R-6 | `bounced` (T-13, AC-6.5 part) unready. |
| OG-11 | Owner confirmation that per-invoice pause (R-7) is wanted. | R-7 | Droppable; nothing else depends on it except AC-4.4/T-9 reason labels. |
| OG-12 | Owner confirmation of the hourly tick and one-day catch-up window (D-5, D-6). | R-3, R-11 | Non-blocking. |
| OG-13 | Languages of the email. Default: one language. | R-4 | Non-blocking. |

## Retired

None. This is the first specification; there were no earlier R-n.

## Evidence

- Inspected: the incoming request only; ShipLoop guides under `GUIDES/` named in `GUIDES/README.md` (requirements-definition, behavioral-requirements, service-discovery, current-system-baseline, project-knowledge, platforms/ui.md#light-expressive-starting-point).
- Walked by hand from the stated start (dates, windows, supersede, no-backfill, retry counts, 60-minute stale-claim): INV-1001 steps 12-12/12-15/12-22/12-29; INV-1004 steps 12-07/12-10/12-17/12-24 and enablement 12-20 → only 12-24 eligible;
  ACME-2 offsets [0, +1] with outage 12-15 → at 12-16 both eligible, one sent; ACME-1 09:00 CST = 15:00 UTC (UTC−6 in December). Each action was checked against the rule that permits it (D-5, D-7, T-1…T-13). Reachability: the enabling actor (admin, R-9) can reach the start under D-21; whether the real product has that role is OG-6.
- **NOT-REPLAYED:** a machine check of the date and time-zone arithmetic was attempted (a small script) but running it was not approved in this unattended run, so the arithmetic above is hand-computed. The DST case in AC-3.8 (2027-03-14, second Sunday of March 2027; 02:00 CST skips to 03:00 CDT = 08:00 UTC) is likewise unchecked by machine. Both stay open for the plan's first test.
- No ordered procedure was run against a product (none exists); no command is documented here, so no exit code is recorded. The `backchain-check` command does not exist in this run (duty 11 left out).

## Submission

- **summary:** First spec for automatic invoice-payment reminders, written without a repository, discovery or research result. 11 requirements (R-1…R-11) with acceptance lines, a step-state machine (T-1…T-13), state/lifecycle, service contracts, and NFRs including a polished-UI requirement. Core outcome: an owner turns reminders on (off by default); each unpaid invoice gets an email on a schedule relative to due date (default −3, 0, +7, +14 days at 09:00 account-local), at most once per step, never to paid/void/draft invoices, with no backfill on enablement. **Assumptions recorded (D-1…D-21):** email only; reminders attach to an existing invoicing product (read-only toward invoices); hourly tick; one-day catch-up window; ≤3 attempts; unknown outcomes are never resent; per-invoice pause; UI light-first with dark option (Gemini/M3 Expressive reference); no customer unsubscribe link in v1. **Open:** OG-1 the real invoicing product is unknown, which keeps any work that reads invoices or builds UI unready until the plan inspects it; OG-2 email provider/domain and OG-4 compliance are person-only; OG-8 volume/availability/rate-limit bounds are unresolved and none were invented; OG-10 bounce callbacks. No material requirement conflict. Date and time-zone arithmetic is hand-computed (NOT-REPLAYED by machine).
- **primary:** R-1, R-2, R-3, R-4
- **evidence_refs:** KNOWLEDGE/spec.md (sections R-1…R-11, Flows, State, Service boundaries, Non-functional requirements, Open gaps); KNOWLEDGE/architecture.md (AD-1…AD-6); GUIDES/requirements-definition.md; GUIDES/behavioral-requirements.md (#behavior-model, #traceability-and-review); GUIDES/service-discovery.md (#verification); GUIDES/current-system-baseline.md (#planning-and-review-handoff); GUIDES/project-knowledge.md (#maintained-product-requirements); GUIDES/platforms/ui.md (#light-expressive-starting-point). No backchain receipt (command absent).
