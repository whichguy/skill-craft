# Invoicing Product: Maintained Specification

Living specification of what the product must do. Structure and technology choices live in
`architecture.md` as `AD-<n>`; this file holds requirements (`R-<n>`), non-functional requirements
(`NFR-<n>`), product decisions (`PD-<n>`) and open gaps (`G-<n>`).

Capability covered so far: **automatic payment reminders for unpaid invoices** (R-1..R-10).

## Status and sources

| Item | Value |
| --- | --- |
| Incoming request (verbatim, 2026-11-21) | "Set up automatic reminders for unpaid invoices." |
| Prior `spec.md` | None existed. No requirement is preserved, changed or retired by this run. |
| Discovery / research / baseline | None exist. No repository, code, tests, README or architecture note was available. Nothing about the current system was observed. |
| Consequence | Every behaviour below is **accepted intent derived from the request's words plus labelled defaults (PD-n)**, not a description of code. Whether invoices, customers, a web app or an email provider already exist is unknown (G-1, G-2, G-7). |
| Reference system | None. No parity or deliberate-difference mapping applies. |

Evidence kinds used in this file: **Observation** = none. **Inference** = reading of the request. **Unknown** = G-n.

### Request outcomes mapped to requirements

| # | Outcome in the request's words | Requirements |
| --- | --- | --- |
| O-1 | "automatic": reminders go out with no manual action per reminder | R-4, R-9 |
| O-2 | "reminders": the customer is told about the outstanding invoice | R-6, R-7 |
| O-3 | "for unpaid invoices": only unpaid ones, and not after payment | R-3, R-5 |
| O-4 | "set up": the account owner can turn it on and shape it, and see it working | R-1, R-2, R-8, R-10 |

### Product decisions and assumptions (defaults taken unattended; not user-stated requirements)

| ID | Decision | Rationale | Revisit if |
| --- | --- | --- | --- |
| PD-1 | Channel is email to the invoice's customer billing contact; one invoice per email, never a digest. | The request names no channel; email is the common invoice channel. | The user names another channel. |
| PD-2 | Reminders are **off** for an account until a billing manager turns them on. | They send messages to the account's customers, an outward-facing act. | The user wants default-on. |
| PD-3 | One evaluation per calendar day when the account's local clock first reaches 09:00, every day including weekends. | A fixed daily time keeps "automatic" predictable; send-time configuration was not requested. | The user wants a configurable time or business-day-only sending. |
| PD-4 | The schedule is 1 to 5 integer day-offsets relative to the due date (negative before, 0 on, positive after), each in -30..+90, no duplicates. Default when first enabled: `[1, 7, 14]`. | "Unpaid" includes overdue; the common cadence is after the due date. The bounds are product choices, not measured limits. | The user states another cadence or limits. |
| PD-5 | A reminder is never retroactive: an offset only produces reminders whose scheduled date is on or after the account-local date that offset was added or the switch was last turned on (its `added_on` date). | Avoids a surprise burst to customers when someone turns the feature on. Interim for G-3. | G-3 is decided. |
| PD-6 | If the outcome of a send is unknown (process died between claim and result), the reminder is **not** resent. | A missed reminder costs less than a duplicate dunning email; no exactly-once claim is possible. | The user prefers retry. |
| PD-7 | A transient provider failure is retried once per daily run, at most 3 attempts per reminder; a permanent rejection ends it immediately. | Bounded, visible retry using the existing daily cadence. | The user wants other limits. |
| PD-8 | Background sending acts under the account's own service authority, not the enabling user's session. "Billing manager" means a user permitted to manage billing settings of that account. | Reminders must continue if the enabler leaves or is signed out. | Role model found in G-1 differs. |
| PD-9 | Concurrent edits of settings are detected by revision; the stale save is rejected, never silently merged. | Avoids lost updates between two billing managers. | n/a |
| PD-10 | If several unsent reminders are due for one invoice in one run (after an outage), only the one with the latest scheduled date is sent; earlier ones are recorded as superseded. | At most one email per invoice per run; no stale-then-current pile-up. | n/a |
| PD-11 | One fixed English message template; no per-account or per-customer customisation. | Not requested. | n/a |
| PD-12 | The account's time zone drives "today" and 09:00; if an account has none, UTC. | Due dates are calendar dates. | G-1 shows a different source. |

### Open gaps (each also appears under the R-n it affects)

| ID | Gap | Type and owner | Interim behaviour | Affects |
| --- | --- | --- | --- | --- |
| G-1 | Where invoices, customers, billing contacts, the account time zone, user roles and the invoice status vocabulary live, and whether an invoice has a customer-visible payment link. No system was provided. | Prerequisite; product owner supplies a repo or data contract. | Logical fields used here (invoice number, status, outstanding balance, currency, due date, customer name, billing email, account name, reply-to address, time zone) and test fixtures. | R-3, R-5, R-6, R-8, R-10; wiring work is **unready** until supplied. |
| G-2 | Email sending identity and provider (sender address, domain authentication such as SPF/DKIM, credentials). | Prerequisite; owner = whoever runs the product's email domain. Real delivery cannot be verified here. | A controllable test mail sink. | R-6, R-7; real-delivery acceptance is **NOT VERIFIABLE** until supplied. |
| G-3 | Whether invoices already overdue when reminders are first turned on should get a catch-up reminder. | User decision. | PD-5: no catch-up (SC-C2 shows an invoice that never gets reminded). | R-2, R-4 |
| G-4 | Whether a customer can have several billing emails. | Folded into G-1. | One recipient address per invoice. | R-6 |
| G-5 | Legal obligations on automated dunning email (opt-out wording, jurisdiction rules). Cannot be checked here. | Unverified obligation; owner = business/legal; due before the first production enablement (product-acceptance phase). | None added. Per-customer opt-out is left out. | R-1, R-6 |
| G-6 | Retention period for reminder records and personal data; expected invoice volume. | User decision. No number is invented. | Records live as long as their invoice and are deleted with it. | NFR-1, NFR-3 |
| G-7 | Whether the settings and history surface is a graphical web UI, another UI or an API only. | Prerequisite found in G-1; default assumption: a settings panel and an invoice-detail history section in the product's existing web app. | Acceptance lines are written against the surfaces S-SET and S-HIST so they hold for either; NFR-6 applies if a graphical UI is built. | R-1, R-2, R-8, NFR-6 |

## Test surfaces and fixtures (used by every acceptance line)

| Surface | Meaning |
| --- | --- |
| S-SET | Where a billing manager reads and changes reminder settings (UI or API, G-7). |
| S-HIST | The reminder history and next-reminder view of one invoice (R-8). |
| S-MAIL | The outbound email as captured at a controllable test mail sink (real provider: G-2). |
| S-RUN | The run trigger with a test-settable clock and the run record (R-9). |
| S-INV | The host invoice data, fixtures until G-1. |

**Fixtures.**
- Account ACME "Acme Studio": time zone America/Chicago (UTC-6 in January 2027, so 09:00 local is 15:00Z); reply-to `billing@acme.example`; users `alice@acme.example` and `carol@acme.example` (billing managers), `bob@acme.example` (member, no billing permission).
- Account ZED "Zed Works": America/New_York (UTC-5 in January 2027, 09:00 local is 14:00Z); billing manager `zoe@zed.example`.
- ACME invoices, all issued, USD, customer "Birch & Co" `ap@birch.example` unless stated:
  INV-1001 due 2027-01-15, total and balance 1250.00; INV-1003 draft; INV-1004 void; INV-1005 balance 0.00; INV-1006 due 2027-01-15, balance 300.00, customer "Cedar Inc" `ap@cedar.example`; INV-1007 no due date; INV-1008 due 2027-01-15, balance 0.01.
- ZED invoice INV-2001 due 2027-01-15, balance 400.00, customer "Quill Ltd" `ap@quill.example`.
- Calendar facts used: 2027-01-04 Mon, 01-12 Tue, 01-15 Fri, 01-16 Sat, 01-18 Mon, 01-20 Wed, 01-22 Fri, 01-23 Sat, 01-24 Sun, 01-29 Fri, 02-01 Mon, 02-08 Mon.
- Default schedule `[1, 7, 14]` turned on for ACME on 2027-01-04 gives INV-1001 steps on 01-16, 01-22 and 01-29 unless a scenario says otherwise. "Step" = one (invoice, offset) pair.

## Requirements

### R-1 Account reminder switch and permission

- **Basis:** request "Set up automatic reminders…" (2026-11-21), O-4; PD-2, PD-8. Added. Preserved: none. Locators: no source sections exist. Evidence limit: no system inspected; role names are assumed (G-1). Pending: implementation and all checks.
- **Behaviour:** each account has one reminders switch, default off. A billing manager can turn it on or off. While off, no reminder is sent for any invoice of the account and no new reminder record is created. Turning it on requires a valid schedule (R-2) and resets every offset's `added_on` date to that day (PD-5). Each change records who and when. A change is honoured at every later send decision, including a reminder already claimed but not yet handed to the mail provider (R-5).
- **Boundaries:** a new account is off. Turning on an account that is already on changes nothing and creates no new `added_on` dates.
- **Error behaviour:** a user without billing permission, or an unauthenticated caller, is denied; the switch and the audit entry are unchanged.
- **Consumer outcome:** S-SET shows On or Off with the last change's actor and time; S-MAIL shows nothing while off.
- **Left out:** per-customer or per-invoice opt-out, staged rollout (G-5 may force an opt-out later).
- **Unresolved:** G-3, G-5, G-7.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-1.1 | `alice@acme.example` turns ACME on at 2027-01-04 10:00 local with defaults; S-SET shows On, schedule `[1,7,14]`, changed by alice at that time, also after a restart. | `bob@acme.example` attempts it: denied, switch stays Off, no audit entry. Unauthenticated call: denied. | A fresh ACME is Off; S-RUN for 2027-01-16 with the switch Off sends nothing and creates no record. | S-SET, S-RUN, S-MAIL; automated acceptance test with a test-settable clock. |
| AC-1.2 | Alice turns ACME off on 2027-01-10; S-RUN for 2027-01-16 sends nothing. | n/a: covered by AC-1.1 denial. | Turning On while already On creates no new `added_on`: run the SC-C1 check after a redundant On and the sends are unchanged. | S-SET, S-RUN, S-MAIL; acceptance test. |
| AC-1.3 | n/a: positive case is AC-1.2. | Off set after the claim is written and before the mail handoff: no email is sent (see AC-5.4). | n/a: same cause. | Service-level test with a pause hook between claim and handoff; the hook is a test seam, not a user surface. |

### R-2 Reminder schedule

- **Basis:** request, O-4; PD-4, PD-5, PD-9. Added. Evidence limit and pending as R-1.
- **Behaviour:** the schedule is a set of day-offsets from the due date. Default `[1, 7, 14]` when first enabled. Each offset carries `added_on`, the account-local date it was added, or the date the switch was last turned on, whichever is later. A saved change applies from the next run; reminder records already made are kept; removing an offset drops its not-yet-sent reminders. S-SET lists offsets ascending. Settings carry a revision.
- **Boundaries:** 1 to 5 entries; each integer in -30..+90; 0 means the due date itself; no duplicates.
- **Error behaviour:** any invalid list is rejected with the offending field named and nothing is saved; the previous schedule stays. A save carrying a stale revision is rejected with a conflict message and nothing is saved.
- **Consumer outcome:** S-SET read-back equals what was saved; later runs follow it.
- **Left out:** weekday-aware or business-day offsets, per-customer schedules.
- **Unresolved:** G-3.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-2.1 | Save `[7, -3, 1]`: read-back is `[-3, 1, 7]`. | Reject, with nothing saved, each of: `[]`, `[7, 7]`, `[7.5]`, `["x"]`. | Accept `[-30, 0, 90, 1, 2]` (five entries, both bounds, zero). Reject `[-31]`, `[91]` and `[1,2,3,4,5,6]`. | S-SET; acceptance test through the real settings surface. |
| AC-2.2 | alice and carol both load revision 3 of ACME's settings; alice saves `[1, 7]` (revision 4). | carol then saves `[2]` with revision 3: rejected with the conflict message; the schedule stays `[1, 7]`. | n/a: one conflict shape. | S-SET; acceptance test with two sessions. |
| AC-2.3 | On 2027-01-20 add offset 30 to ACME's `[1,7,14]`: INV-1001 gets a step scheduled 2027-02-14 that S-RUN sends on that date. | n/a: covered by AC-2.1. | On 2027-01-20 add offset 3 (scheduled 2027-01-18, before `added_on`): S-RUN for 2027-01-21 sends nothing for it. Removing offset 14 on 2027-01-25 means S-RUN for 2027-01-29 sends no +14 reminder. | S-SET, S-RUN, S-MAIL. |

### R-3 Which invoices are unpaid and remindable

- **Basis:** request, O-3 ("unpaid invoices"); PD-1. Added. Evidence limit: the invoice status vocabulary is unknown (G-1). Pending: all.
- **Behaviour:** an invoice is remindable when its account's switch is on, it is issued (not a draft), not void or cancelled, its outstanding balance is greater than zero, and it has a due date. Not-yet-due invoices are remindable (a negative offset applies to them). The remindable test is re-evaluated against current invoice data at every decision.
- **Boundaries:** balance 0.01 is remindable; 0.00 and any credit (negative) balance are not.
- **Error behaviour:** an invoice that is not remindable is never emailed and gets no reminder record; S-HIST states the reason (R-8).
- **Consumer outcome:** S-MAIL contains emails only for remindable invoices.
- **Left out:** disputed or in-collections statuses (their policy depends on G-1), late fees or interest.
- **Unresolved:** G-1.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-3.1 | INV-1001 (issued, 1250.00) receives its due reminders (see SC-A). | With every step date reached, S-RUN produces nothing for INV-1003 (draft), INV-1004 (void), INV-1005 (0.00) and INV-1007 (no due date). | INV-1008 (balance 0.01) is emailed on 2027-01-16; a balance reduced to 0.00 before 2027-01-22 yields no email on that date. | S-INV, S-RUN, S-MAIL; acceptance test using the fixtures. |

### R-4 Daily evaluation and sending

- **Basis:** request, O-1 ("automatic"); PD-3, PD-5, PD-10, PD-12. Added. Evidence limit: no scheduler or runtime known. Pending: all.
- **Behaviour:** once per account-local calendar day, when the account's local clock first reaches 09:00, the system evaluates every remindable invoice of every account with the switch on. A step's scheduled date is the due date plus the offset, as an account-local calendar date. A step is eligible if `added_on` is on or before its scheduled date, its scheduled date is on or before the run date, and it has no final record. For each invoice, only the eligible step with the latest scheduled date is sent; the other eligible steps are recorded as superseded without sending (PD-10). A step is sent at most once; running again on the same day sends nothing new. Evaluation needs no user session.
- **Boundaries:** the run fires once when the local clock reaches 09:00, not before; turning the switch on after that moment waits for the next day's run; a step whose scheduled date is before its `added_on` is never sent.
- **Error behaviour:** a failure on one invoice never stops the others (R-7).
- **Consumer outcome:** S-MAIL gets at most one email per invoice per day. Days-overdue text is computed from the send date (R-6).
- **Left out:** weekend or holiday skipping, configurable send time, manual "send now", per-customer timing.
- **Unresolved:** G-3 (backlog at enablement).

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-4.1 | SC-A: INV-1001 emails on 2027-01-16 (Saturday) and 2027-01-22, and no INV-1001 email on any other day to 2027-01-28. | n/a: the miss is AC-4.2. | Clock moves from 2027-01-16 14:59:59Z to 15:00:00Z: no run before, exactly one run at 15:00:00Z (ACME, 09:00 CST). | S-RUN, S-MAIL; acceptance test with a test-settable clock. |
| AC-4.2 | SC-B: no run happens 2027-01-16 to 2027-01-23; the run on 2027-01-24 sends one email (the +7 step, "9 days overdue"); the +1 step is recorded superseded. | n/a: covered. | n/a: covered. | S-RUN, S-MAIL, S-HIST. |
| AC-4.3 | SC-C1: switch turned on 2027-01-22 08:00 local; the 09:00 run sends the +7 reminder. | SC-C2: turned on 2027-01-22 10:00 local; nothing that day; 2027-01-23 09:00 sends +7 ("8 days overdue"). SC-C3: turned on 2027-01-31, every step date is past, so no email is ever sent for INV-1001 (G-3). | In SC-C1 and SC-C2 the +1 step (2027-01-16) is never sent, as it precedes `added_on`. | S-SET, S-RUN, S-MAIL. |
| AC-4.4 | n/a: positive case is AC-4.1. | A second trigger of the 2027-01-16 run, after it completed, sends no further email and adds no records. | n/a: same cause. | S-RUN, S-MAIL; acceptance test. |

### R-5 Stop and adjust when payment or invoice data changes

- **Basis:** request, O-3; PD-8, PD-10. Added. Evidence limit: payment events come from the host (G-1). Pending: all.
- **Behaviour:** immediately before handing a reminder to the mail provider, the system re-reads the invoice and the account switch; if the invoice is no longer remindable (paid in full, voided, balance 0) or the switch is off, nothing is sent and the step is recorded as cancelled with its reason. After a full payment, remaining steps are never sent. After a partial payment, reminders continue and state the outstanding balance at send time. If the due date changes, unsent steps follow the new due date; a step already sent stays sent (identity is (invoice, offset)). A reminder already handed to the provider cannot be recalled.
- **Boundaries:** a payment recorded after the mail handoff does not retract the email; a payment recorded between claim and handoff stops it.
- **Error behaviour:** if the re-read fails, nothing is sent and the step stays unsent for the next run (counts as a transient failure under R-7).
- **Consumer outcome:** S-MAIL shows no email after the payment time; S-HIST shows "not sent: invoice paid".
- **Left out:** automatic "payment received" or "disregard" notices.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-5.1 | SC-A: a full payment is recorded on 2027-01-25; 2027-01-29 sends nothing; S-HIST says the +14 step was not sent because the invoice is paid. | n/a: covered. | INV-1006 (+1 sent 01-16) voided on 2027-01-21: no 2027-01-22 email for it. | S-INV, S-RUN, S-MAIL, S-HIST. |
| AC-5.2 | SC-D: the 2027-01-16 email states 1,250.00 USD; a 500.00 payment on 2027-01-20 makes the 2027-01-22 email state 750.00 USD. | n/a: covered. | n/a: covered. | S-MAIL. |
| AC-5.3 | SC-I: the due date moves from 2027-01-15 to 2027-01-25 on 2027-01-17, after the +1 reminder was sent; no email on 2027-01-22; +7 is sent 2027-02-01 and +14 on 2027-02-08. | The +1 step is not sent again for the new due date. | n/a: same cause. | S-INV, S-RUN, S-MAIL. |
| AC-5.4 | n/a: positive case is AC-5.1. | Payment recorded after the claim and before the handoff (pause hook): no email, step cancelled "invoice paid". | Payment recorded after the handoff: the email stays sent, no record changes. | Service-level test with a pause hook; S-MAIL and S-HIST. |

### R-6 Reminder message

- **Basis:** request, O-2; PD-1, PD-11. Added. Evidence limit: sender identity is unknown (G-2); payment link unknown (G-1). Pending: all.
- **Behaviour:** the email goes to the invoice's customer billing address. Reply-To is the account's reply-to address. It has a plain-text part and an HTML part. Subject: `Reminder: invoice {number} from {account name} is due {date}` before the due date, `... is due today` on it, `... was due {date}` after, with `{date}` written like "January 15, 2027". Required body fields: customer name, invoice number, outstanding balance as `1,250.00 USD`, due date, timing line (`due in N days`, `due today`, `1 day overdue`, `N days overdue`, counted from the send date to the due date), account name, the reply-to address. A payment link appears only if the host provides one (G-1). Every inserted value is escaped for HTML and stripped of line breaks in headers.
- **Boundaries:** singular "1 day"; 0 is "due today"; the timing line uses the send date, not the step's scheduled date.
- **Error behaviour:** an unusable recipient is handled by R-7.
- **Consumer outcome:** S-MAIL shows the message.
- **Left out:** attachments, custom wording, other languages, CC to the account, payment-link generation.
- **Unresolved:** G-1, G-2, G-5.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-6.1 | The 2027-01-16 email for INV-1001: To `ap@birch.example`, Reply-To `billing@acme.example`, subject `Reminder: invoice INV-1001 from Acme Studio was due January 15, 2027`, body shows `1,250.00 USD`, `1 day overdue`, both text and HTML parts. | Customer name `Birch & <b>Co</b>` appears escaped in the HTML part. Account name `Acme\r\nBcc: evil@x.example` yields a one-line subject and no Bcc header. | With schedule `[-3,1,7]` the 2027-01-12 email says `is due January 15, 2027` and `due in 3 days`; an offset-0 run says `due today`; the SC-B email says `9 days overdue`; the SC-A 2027-01-22 email says `7 days overdue`. | S-MAIL; acceptance test inspecting captured messages. |

### R-7 Delivery outcomes and failure handling

- **Basis:** request, O-2; PD-6, PD-7. Added. Evidence limit: provider behaviour unknown (G-2). Pending: all.
- **Behaviour:** each reminder step ends in one recorded state: sent (accepted by the provider, **not** proof of delivery), failed, skipped, superseded, cancelled, or unknown-outcome. A transient provider failure keeps the step eligible and is retried at the next run, at most 3 attempts in total, then failed. A permanent rejection is failed at once. A blank or malformed recipient is skipped and the step is final. An unknown outcome is never resent (PD-6). A failure for one invoice never blocks the rest of the run. The attempt count is kept per step.
- **Boundaries:** the third transient failure is final; success on the third attempt is "sent" with 3 attempts. A later step coming due ends earlier unfinished steps as superseded.
- **Error behaviour:** outage of the whole provider yields failed or retried steps and a completed run, not a crashed run.
- **Consumer outcome:** S-HIST shows each state with the attempt count and the time.
- **Left out:** bounce, delivery or open tracking, so a later bounce is not visible; other channels.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-7.1 | Provider fails transiently on 01-16 and succeeds on 01-17: one email, state sent, attempts 2. | SC-F: transient failures on 01-16, 01-17, 01-18: state failed after attempt 3, nothing on 01-19, and 01-22 still sends +7. A permanent rejection on 01-16: failed after 1 attempt, no retry on 01-17. | Success on the third attempt: sent, attempts 3. SC-F2: failures on 01-16 and 01-17, then 01-22 sends +7 and the +1 step is recorded superseded. | S-RUN, S-MAIL, S-HIST; provider failures scripted at the test mail sink. |
| AC-7.2 | SC-E: INV-1001 has no billing email on 01-16: step skipped (no recipient), nothing on 01-17 after the address is fixed, 01-22 sends +7 to `ap@birch.example`. | n/a: covered. | n/a: covered. | S-INV, S-RUN, S-MAIL, S-HIST. |
| AC-7.3 | SC-G: the process is killed after the 01-16 claim of INV-1001; after recovery the step shows unknown-outcome and 01-17 sends nothing; 01-22 sends +7. | n/a: covered. | A failure for INV-1001 on 01-16 does not stop INV-1006 from being emailed in the same run. | S-RUN, S-MAIL, S-HIST; fault injection at a test seam. |

### R-8 Reminder history and next reminder

- **Basis:** request, O-4 (see that the setup works); PD-8. Added. Evidence limit: surface kind unknown (G-7). Pending: all.
- **Behaviour:** for each invoice, S-HIST lists its reminder records (offset, scheduled date, state, attempt count, time, recipient used), newest first, and the next reminder: the date of the next run expected to send, or the reason there is none ("reminders are off", "invoice paid", "invoice void", "no due date", "no further reminders scheduled"). It is visible to users who may view that invoice in that account.
- **Boundaries:** an invoice with no records shows an empty state. Next reminder is the later of the earliest eligible step's scheduled date and the next run's date.
- **Error behaviour:** a user of another account asking for the invoice gets "not found", not "forbidden".
- **Consumer outcome:** S-HIST.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-8.1 | In SC-A, on 2027-01-17 S-HIST shows the +1 record "sent", attempts 1, recipient `ap@birch.example`, and next reminder 2027-01-22; on 2027-01-23 next is 2027-01-29. | `zoe@zed.example` requests INV-1001's history: "not found". | Before any send, empty state, next reminder 2027-01-16; after payment: "none: invoice paid"; switch off: "none: reminders are off". | S-HIST; acceptance test. |

### R-9 Run independence, overlap and recovery

- **Basis:** request, O-1; PD-6. Added. Evidence limit: runtime unknown. Pending: all.
- **Behaviour:** reminders are produced without any user session, screen or developer machine being active. Two runs for the same day that overlap (duplicate trigger, two instances) send each step at most once in total. A run that dies part-way is completed by the next trigger without repeating finished work, and its unfinished claims become unknown-outcome after a recovery threshold (numeric value unresolved: set in planning, must exceed the longest provider call, AD-2). Every run leaves a run record: start, end, state (completed or aborted), and per-account counts of considered, sent, skipped, superseded, cancelled, failed.
- **Boundaries:** a run still going when the next day's trigger fires does not cause a duplicate send.
- **Error behaviour:** an aborted run is shown as aborted.
- **Consumer outcome:** S-RUN's run record.
- **Left out:** an alert for a missed run (NFR-4: unresolved).

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-9.1 | A completed 2027-01-16 run for ACME (due steps: INV-1001, INV-1006, INV-1008) records 3 sent and the totals match S-MAIL. | Two simultaneous triggers for 2027-01-16: S-MAIL holds exactly one email per invoice (3 in all) and the combined counts sum to 3 sent. | The run is killed after INV-1001 and before INV-1006: the run record says aborted; the next trigger sends INV-1006 and INV-1008 only. | S-RUN, S-MAIL; fault injection and a test-settable clock. |

### R-10 Account isolation and authority

- **Basis:** request, O-4; PD-8. Added. Evidence limit: tenancy model unknown (G-1). Pending: all.
- **Behaviour:** each reminder uses only its own account's switch, schedule, time zone, name and reply-to. An email carries one invoice of one account. Users read and change only their own account's settings and history. Background sending continues under the account's authority if the enabling user is deactivated.
- **Boundaries:** two accounts with different time zones and schedules run in the same wall-clock hour without interference.
- **Error behaviour:** cross-account access is denied (settings) or "not found" (invoices).
- **Consumer outcome:** S-SET, S-HIST, S-MAIL.

| Acceptance | Positive | Failure | Boundary | Surface / confirmation |
| --- | --- | --- | --- | --- |
| AC-10.1 | ACME `[1,7,14]` (on 01-04) and ZED `[3]` (on 01-04), after SC-A to 01-17: on 2027-01-18 ZED's 14:00Z run emails `ap@quill.example` ("3 days overdue", Zed Works) and ACME's 15:00Z run sends nothing. | `zoe@zed.example` cannot read or change ACME's settings: denied. | alice is deactivated on 2027-01-20: the 2027-01-22 ACME reminder still goes out. | S-SET, S-RUN, S-MAIL. |

## Worked scenarios (SC)

Each is replayable from the fixtures. Actions and outcomes were walked by hand against the rules cited; see Evidence.

| ID | Start and actions | Expected result | Rules relied on |
| --- | --- | --- | --- |
| SC-A | Alice turns ACME on 2027-01-04 with defaults (R-1, R-2). Runs daily. A full payment is recorded 2027-01-25. | Emails to `ap@birch.example` on 01-16 (+1, "1 day overdue", 1,250.00 USD) and 01-22 (+7, "7 days overdue"); none on 01-29; +14 never sent. | R-1, R-3, R-4, R-5 |
| SC-B | As SC-A, but no run occurs 01-16 to 01-23. | 01-24: one email, +7, "9 days overdue"; +1 recorded superseded. | R-4, PD-10 |
| SC-C1 | ACME off; alice turns it on 2027-01-22 08:00 local. | 01-22 09:00 sends +7 ("7 days overdue"); +1 never sent. | R-4, PD-5 |
| SC-C2 | Same but turned on 2027-01-22 10:00. | Nothing on 01-22; 01-23 09:00 sends +7 ("8 days overdue"). | R-4, PD-5 |
| SC-C3 | Turned on 2027-01-31. | No email ever for INV-1001 (G-3 interim). | PD-5 |
| SC-D | As SC-A; a 500.00 payment on 2027-01-20. | 01-16 email 1,250.00 USD; 01-22 email 750.00 USD. | R-5 |
| SC-E | INV-1001 has no billing email on 01-16; fixed 01-17 before the run. | +1 skipped, final; 01-17 nothing; 01-22 sends +7. | R-7 |
| SC-F | Provider transient failure 01-16, 01-17, 01-18. | +1 failed after 3 attempts; 01-19 nothing; 01-22 sends +7. | R-7, PD-7 |
| SC-F2 | Transient failure 01-16 and 01-17. | 01-22 sends +7; +1 superseded with 2 attempts. | R-4, R-7 |
| SC-G | Process killed after the 01-16 claim, recovered before 01-17. | +1 unknown-outcome, never resent; 01-22 sends +7. | R-7, R-9, PD-6 |
| SC-I | After the 01-16 +1 send, due date moved to 2027-01-25 on 01-17. | 01-22 nothing; 02-01 sends +7; 02-08 sends +14; +1 not resent. | R-5 |

Actors are authorised as stated: enabling and editing are done by billing managers (alice, carol) allowed by R-1; payments, voiding and due-date changes are host-system actions on S-INV outside this feature; run triggers are the system's own.

## Step state and transition ledger

States of one step (the (invoice, offset) pair): *eligible* (implicit, no record), *in-progress*, then final: *sent*, *failed*, *skipped*, *superseded*, *cancelled*, *unknown-outcome*; *failed-retry* is in-progress that returns to eligible. Owner: the system, durable.

| T-ID | R | Before | Trigger and guard | After and observation | Failure / recovery | Cases |
| --- | --- | --- | --- | --- | --- | --- |
| T-1 | R-4 | eligible | run reaches the step; it is the latest eligible one of its invoice; recipient present | in-progress (claim recorded; claim is atomic) | duplicate claim loses and sends nothing | AC-9.1 |
| T-2 | R-4 | eligible | run reaches the step; a later eligible step exists | superseded, not sent | n/a | AC-4.2, SC-F2 |
| T-3 | R-5 | in-progress | re-read says not remindable or switch off | cancelled with reason, not sent | re-read failure: back to eligible (counts as an attempt) | AC-5.4, AC-1.3 |
| T-4 | R-7 | in-progress | provider accepts | sent (attempts n) | n/a | AC-4.1 |
| T-5 | R-7 | in-progress | provider transient failure and attempts < 3 | eligible again, attempts n | retried next run | AC-7.1 |
| T-6 | R-7 | in-progress | transient and attempts = 3, or permanent rejection | failed | visible in S-HIST | AC-7.1 |
| T-7 | R-7 | eligible | recipient blank or malformed | skipped, final | fix applies to later steps only | AC-7.2 |
| T-8 | R-7, R-9 | in-progress | recovery threshold passed with no result | unknown-outcome, final, never resent | n/a | AC-7.3 |
| T-9 | R-4 | any final state | same step reached again (same or later run, any trigger) | unchanged, no email | n/a | AC-4.4 |

Ignored events: payment or void on a step already final changes no record. A due-date change leaves final steps untouched (AC-5.3).

## State and data assessment

| State | Owner and location | Read by | Simultaneous change | Ends | Runtime limits met |
| --- | --- | --- | --- | --- | --- |
| Account reminder settings (switch, offsets with `added_on`, revision, who/when) | The account; durable application data | Billing managers of that account (write); system (read) | Revision check, stale save rejected (PD-9) | With the account | Unknown (G-1) |
| Reminder step records (state, attempts, time, recipient used, reason) | The system; durable, keyed by (invoice, offset), unique | Users who can view that invoice; system | Atomic claim; a second claimant loses | With the invoice, no earlier removal (retention: G-6) | Unknown |
| Run records (counts, start, end, state) | The system; durable | Operators | Append-only per run | Retention unresolved (G-6) | Unknown |
| Invoice data, customer contact | Host invoicing data (G-1); this feature only reads | n/a | Re-read before every send (R-5) | Not owned | n/a |

- **Invariants before and after:** at most one email per (invoice, offset) ever; at most one per invoice per run; a final state never reverts; no record exists for a non-remindable invoice.
- **Personal data:** the customer's email and name appear in the email and the step record (recipient used), shown to the account's own authorised users. Logs hold account id, invoice id, offset and outcome, never the address, body or credentials. Removal: with the invoice; erasure on a customer's request and the retention period are G-5/G-6.
- **Recovery:** after a restart, settings and records persist; unfinished claims resolve through T-8.
- **Unknown:** quotas and storage limits of the target runtime; they block nothing now.

## Service boundaries

| Boundary | Contract |
| --- | --- |
| Invoice data (G-1) | Authority: the host invoicing data. Freshness: read at evaluation and again right before every send; nothing is cached between those reads. Revocation or payment is seen at the next read; a payment after the handoff is not recalled (R-5). Incremental state: none consumed. Async: none. Events owned: none. |
| Mail provider (G-2) | Authority for acceptance only: "accepted" is the sole success signal (R-7). Idempotency: the claim record is the identity; no exactly-once claim. A timeout or crash after the call is unknown-outcome (T-8). Delivery or bounce events are not consumed (left out). Credentials are held by the platform's secret facility, never in settings, records or logs. |
| Run trigger | Authority: the system clock in the account's time zone. Overlap, missed runs and recovery: R-4, R-9. Independent of any screen. |
| Owned event coverage | Step records (R-7) and run records (R-9) are the owned operation events. Login or authentication events: n/a. |

## Non-functional requirements

Basis for all: request (2026-11-21) plus the quality screen in the requirements-definition guide. No performance, load or availability target was stated and none is invented.

| ID | Quality | Operating condition and requirement | Bound or observable criterion | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-1 | Capacity and timing | Daily run over all accounts' invoices. | **Unresolved bound:** invoice volume and the run's time budget (G-6). Observable now: a run that outlasts the next trigger causes no duplicate send and shows in the run record (AC-9.1). | Acceptance test (overlap) now; load check once the volume is known | Open |
| NFR-2 | Reliability and integrity | Restart, crash, duplicate trigger. | After a restart the settings and records equal their pre-restart values (AC-1.1); at most one email per step (AC-9.1, AC-7.3); catch-up after downtime (AC-4.2). | Acceptance and fault-injection tests | Planned |
| NFR-3 | Security and privacy | Customer personal data, cross-account separation. | Denial and "not found" cases (AC-1.1, AC-8.1, AC-10.1); escaping and header-safe fields (AC-6.1); a log assertion that no address, body or credential appears in logs for AC-4.1's run; no secrets in settings or records. **Unresolved:** retention period (G-6) and legal obligations (G-5, owner business/legal, due at product acceptance). | Acceptance tests; log inspection; G-5 not checkable here | Partly open |
| NFR-4 | Operability and observability | Operators must be able to tell whether the daily run happened. | The run record (R-9) and step records (R-7) are retrievable. **Unresolved:** who is alerted when no run completed in a day, and through what (needs an owner and an alerting facility). | Inspection of records; alert check once owned | Partly open |
| NFR-5 | Testability and compatibility | Tests must be repeatable. | The run's clock can be set by a test; sent mail can be captured and made to fail on cue; fixtures above are loadable. **Unresolved:** supported runtime and platform limits (no baseline, G-1). | The acceptance suite itself | Planned |
| NFR-6 | Interface quality (applies to every graphical surface this feature adds: settings and history, if G-7 resolves to a UI) | See below. | See below. | Browser check at 360 px and 1280 px in both themes; contrast measurement; keyboard walk-through | Planned |
| NFR-7 | Excluded | Localisation, availability SLA, accessibility of the email beyond the plain-text part. | Justification: none requested; behaviour after downtime is covered by catch-up (AC-4.2); the text part is in AC-6.1. | n/a | Excluded with reason |

**NFR-6 criteria (observable).**
1. Visual reference and starting appearance: the light expressive starting point of the UI visual-direction guide (the light Gemini look with Material 3 Expressive principles: airy tonal rounded surfaces, friendly precise type, a restrained saturated accent). Precedence: an established product identity or platform convention in the host product wins (G-1), as do explicit visual constraints. A new web UI starts light with a dark option. The concrete treatment is chosen in planning.
2. One visual system: a spacing scale, a type scale and a palette defined as tokens with a light and a dark theme. Check: both themes render every state below.
3. The primary activity has the strongest weight: the switch and the schedule editor in settings, the record list in history.
4. Designed states: empty (history "No reminders yet"; settings Off with an explanation and a "Turn on" action), loading (visible progress, controls truthful), error (a failed save keeps the unsaved edits, names the problem and offers retry, and stays on screen until resolved, not only a transient toast), conflict (AC-2.2 message with a reload action). Saving shows "Saving" and shows "Saved" only after the read-back confirms it.
5. Layout works at 360 px and 1280 px with no horizontal scroll.
6. Keyboard focus is visible on every control; text contrast meets WCAG 2.x AA (4.5:1 normal text, 3:1 large text and controls); controls have accessible names; status changes are announced politely.
7. Motion only where it explains a change (adding or removing a schedule offset, a record appearing), and none under `prefers-reduced-motion`.
8. One icon set.
- Component, interaction and skin premises: components are a switch, an offset editor (add and remove chips with a numeric field), a record list; interaction keeps a draft separate from the confirmed state and never lets a late response overwrite a newer edit; skin is the tokens above.

## Self-check findings (duty 10)

- Replayable steps: every SC and AC names concrete invoices, dates, addresses and values.
- Ordered procedures walked from their start: the actor (alice, a billing manager) can turn the switch on (R-1); each run action is allowed by the state the previous one left (R-4 eligibility, R-5 re-read); payments, voids and due-date changes are host actions on S-INV; the oracle is the captured mail and S-HIST. Results are in the table below.
- Stand-in risk: AC-4.1 asserts exact dates, counts and body fields, not only "an email was sent"; AC-1.3 and AC-5.4 need a test seam, named as such.
- Documented commands: none are documented, so none to run.
- Dropped requirements: none (no prior version).
- Platform claims: none that a decision depends on, apart from calendar and time-zone offsets (America/Chicago is UTC-6 and America/New_York UTC-5 in January 2027; no DST change falls in the scenario dates).

| Case | Method | Recomputed result | Status |
| --- | --- | --- | --- |
| SC-A | Hand walk against R-3 to R-5 | Sent 01-16 (+1) and 01-22 (+7); 01-29 none | NOT-REPLAYED: a reference script was written but its execution was not approved in this environment, so no run result is claimed |
| SC-B | Hand walk | 01-24 sends +7 only, +1 superseded, "9 days overdue" | NOT-REPLAYED (same reason) |
| SC-C1/C2/C3 | Hand walk | 01-22 sends +7; 01-23 sends +7 ("8 days overdue"); none | NOT-REPLAYED |
| SC-D, SC-E, SC-F, SC-F2, SC-G, SC-I | Hand walk | As tabled | NOT-REPLAYED |

These stay open until replayed by a check that applies each action only where a rule permits it.

## Traceability

| Outcome | R | Acceptance lines |
| --- | --- | --- |
| O-1 automatic | R-4, R-9 | AC-4.1..4.4, AC-9.1 |
| O-2 reminders reach the customer | R-6, R-7 | AC-6.1, AC-7.1..7.3 |
| O-3 only unpaid, stop on payment | R-3, R-5 | AC-3.1, AC-5.1..5.4 |
| O-4 set up and see it | R-1, R-2, R-8, R-10 | AC-1.1..1.3, AC-2.1..2.3, AC-8.1, AC-10.1 |

Primary requirements (the request's direct asks): R-1, R-2, R-3, R-4, R-5, R-6.
Product-acceptance may accept one of these left unverified only with a passed lower-layer test.
Verification due phases: acceptance tests at test and product-acceptance; G-2 real-delivery check and G-5 at product-acceptance and before production enablement.

## Retired

None.

## Submission

- **summary:** First specification for an invoicing product's payment-reminder capability, derived only from the request "Set up automatic reminders for unpaid invoices." (2026-11-21); no repository, baseline, discovery or earlier spec existed. It defines ten requirements (R-1..R-10), seven non-functional requirements, 12 product decisions and a step state ledger. Assumptions taken unattended: PD-1..PD-12 (email channel; off by default; daily at 09:00 account time; offsets `[1,7,14]` with bounds; non-retroactive; at-most-once on unknown outcome; 3 attempts; latest-step-only catch-up; fixed English template; UTC if no time zone). **Open:** G-1 invoice and account data source (affected wiring unready), G-2 email provider (real delivery unverifiable), G-3 backlog policy (user decision), G-5 legal obligations (owner business, due at product acceptance), G-6 retention and volume, G-7 UI surface kind; NFR-1 and NFR-4 bounds unresolved. All scenario oracles are hand-walked and marked NOT-REPLAYED. No material requirement conflict was found. `backchain-check` does not exist here (duty 11 omitted).
- **primary:** R-1, R-2, R-3, R-4, R-5, R-6
- **evidence_refs:** `KNOWLEDGE/spec.md` (all requirement sections R-1..R-10, NFRs, State and data assessment, Service boundaries, Worked scenarios); `KNOWLEDGE/architecture.md` (AD-1..AD-5); guides used: `GUIDES/requirements-definition.md`, `GUIDES/behavioral-requirements.md` (behavior model, traceability, interaction design), `GUIDES/service-discovery.md`, `GUIDES/current-system-baseline.md#planning-and-review-handoff`, `GUIDES/platforms/ui.md#light-expressive-starting-point`, `GUIDES/project-knowledge.md#maintained-product-requirements`. The incoming request is the only product source; no receipt from any check exists.
