# Specification: automatic reminders for unpaid invoices

Working assumptions about the host product (the working directory is empty, so none of this is inherited from code): it is a multi-user invoicing product. A *workspace* is one business account. A workspace has *members* with roles (Admin, Member, Viewer), *customers*, and *invoices*. An invoice has a number, a customer, a currency, a total, a due date (a calendar date, no time of day), zero or more billing email addresses, and one *state*. Invoice states are: Draft, Open, Partially paid, Paid, Void, Written off. Each invoice has a customer-facing page reachable by link, on which the customer can view and pay it. Admins and Members can edit invoices and customers; Viewers can only look. A customer's payment can be started but not yet confirmed (for example a bank debit). Anything the host product does that this document does not mention keeps working as it does today.

## Use cases

### U-1: An Admin turns reminders on for the first time, to stop chasing late payers by hand
Flow: The Admin opens the workspace's Reminders settings and sees reminders Off. They enter the reminder contact email, accept or edit the proposed schedule (default: 3 days before the due date, on the due date, then 3, 7, 14 and 30 days after), send hour (default 09:00) and timezone, and press Turn on. The page shows On, a count of open invoices that are in scope, and the date and time of the first reminder that will go out.
Source: request

### U-2: A customer receives a reminder about an unpaid invoice and pays it
Flow: On a scheduled day the customer receives an email from the business naming the invoice, the amount still owed, the due date and how late or early it is. They follow the link in the email to the invoice page and pay. They get no more reminders for that invoice.
Source: request

### U-3: A customer settles an invoice by any route and the reminders stop
Flow: The invoice is paid in full, voided, written off or fully credited (by the customer online, by the business recording a bank transfer, or by a credit note). No further reminder is sent for it, and its history shows that reminders ended and why.
Source: implied: "unpaid invoices" — an invoice that is no longer unpaid must not be chased.

### U-4: A customer who has paid part of an invoice is reminded of the remainder
Flow: The customer paid part of an invoice. The next scheduled reminder shows the amount still owed, not the original total, and also shows the original total.
Source: implied: "unpaid" covers partly paid invoices.

### U-5: A business member pauses reminders on one invoice, and later resumes them
Flow: A member opens the invoice, presses Pause reminders, optionally enters a resume date and a note, and the invoice shows Paused. No reminder goes out while paused. On resume (pressed by a member, or reached by the resume date) the invoice shows its next scheduled reminder.
Source: implied: a business needs to stop chasing one customer (dispute, promised payment) without turning the feature off.

### U-6: A business member sends a reminder right now
Flow: A member opens an unpaid invoice, presses Send reminder now, and sees it queued; shortly after, the history shows it sent to the named recipients.
Source: implied: automatic reminders are not enough when a member speaks to a customer and wants an immediate one.

### U-7: A business member finds out what was sent, to whom, and why something was not sent
Flow: The member opens an invoice's reminder history, or the workspace-wide reminder log, and sees every reminder decision with its date, step, recipients and outcome; they filter the log to Failed to find the one that went wrong.
Source: implied: someone must be able to answer "did the customer get a reminder?".

### U-8: A customer asks not to be sent any more reminders for an invoice
Flow: The customer follows the "stop reminders" link in a reminder, sees a confirmation page naming the invoice, presses the button on it, and sees that reminders for the invoice have stopped. The business sees that in the invoice's history.
Source: implied: recipients of repeated automatic email must have a way out.

### U-9: A reminder cannot be delivered
Flow: The delivery provider reports a failure for a reminder. Temporary failures are retried a bounded number of times; permanent failures (a bad address) are not. A member sees the reminder as Failed with a reason, in the invoice history and the workspace log.
Source: implied: "automatic reminders" depend on an outside email system that can fail.

### U-10: An Admin changes the schedule, send hour, timezone, note or contact email
Flow: The Admin edits the settings and saves. The page shows the saved values and each open invoice shows its new next reminder time. Reminders already sent are not sent again, and no flood of catch-up reminders follows the change.
Source: implied: the schedule is configurable because a schedule that suits one business does not suit another.

### U-11: An Admin sends themselves a test reminder to see what customers will get
Flow: The Admin presses Send test reminder, picks (or is given) one invoice, and receives within minutes at their own address an email marked as a test that looks exactly as the real one would. No customer receives anything and no history of a real reminder is created.
Source: implied: turning on a feature that emails customers needs a way to check it worked first.

### U-12: An Admin turns reminders off, or goes back to earlier settings
Flow: The Admin presses Turn off; reminders that have not yet gone out are cancelled and the page shows Off. Or the Admin opens the settings history, picks an earlier version and presses Restore; the settings revert and the history records the restore.
Source: implied: a feature that can be turned on must be able to be turned off and undone.

### U-13: A business already has invoices, some overdue, on the day reminders are first turned on
Flow: The Admin turns reminders on. Open invoices that are not yet overdue get their remaining scheduled reminders; invoices already past one or more steps do not receive those past steps in a burst.
Source: implied: this feature is added to a product that already holds invoices.

### U-14: A business member edits an invoice that has reminders scheduled
Flow: The member changes the due date, the amount, the billing email, the customer, or the state (void, reinstate, reopen after a reversed payment). The next reminder reflects the change; no reminder is sent that is wrong for the invoice's new situation.
Source: implied: invoices change after they are issued.

### U-15: A business member stops reminding one customer on all their invoices
Flow: The member opens the customer, switches on "Do not send reminders", and all of that customer's invoices show Excluded; switching it off resumes reminders.
Source: implied: the same need as U-5 at customer level.

### U-16: A platform operator watches reminders run, finds the one that went wrong, and stops them all if something is going badly
Flow: The operator opens the operations view, sees the counts of queued, sent, skipped and failed reminders per day and the age of the oldest queued reminder, drills to one failed reminder, and, if needed, presses Emergency stop, after which no reminder email leaves for any workspace.
Source: implied: whoever runs a feature that emails real customers on its own needs to observe and halt it.

### U-17: A platform operator recovers after the reminder system was down
Flow: The scheduler or the email provider was unavailable for hours. When service returns, reminders that were due are sent late, once each, with no duplicates, and reminders that were due more than 48 hours earlier are not sent at all but are shown as Skipped.
Source: implied: any scheduled job misses its time sometimes.

## Clauses

### C-1: Reminders are Off for every workspace until an Admin turns them on.
Observable: Before an Admin turns reminders on for a workspace, no reminder email is sent for any of its invoices, however overdue; the Reminders settings page shows Off. This holds for workspaces that already exist when the feature ships.
Source: choice: emailing a business's customers without the business having asked is not reversible, so default Off.

### C-2: Turning reminders on requires a valid reminder contact email.
Observable: If the reminder contact email is empty or is not a syntactically valid email address, pressing Turn on is refused with a message naming that field; the page still shows Off. While reminders are On, saving an empty or invalid contact email is refused in the same way.
Source: implied: U-1 — replies from customers need somewhere to go (C-31).

### C-3: The workspace's reminder settings are exactly these six: On/Off, schedule, send hour, timezone, reminder contact email, custom note.
Observable: The Reminders settings page shows and allows editing these six and no others; each change is recorded with who made it and when (C-67).
Source: implied: U-1 and U-10 name them.

### C-4: The schedule is a list of steps; each step is a whole number of days relative to the invoice's due date: negative is before, 0 is on the due date, positive is after.
Observable: The Admin enters steps such as -3, 0, 7; a step of -3 produces a reminder three calendar days before the due date, 0 on the due date, 7 seven calendar days after.
Source: implied: U-1 — "3 days before … 7 after".

### C-5: A schedule holds 1 to 10 steps, each between -30 and +180 inclusive, with no two steps equal.
Observable: Saving a schedule with 0 steps, 11 steps, a step of -31 or 181, a non-whole number, or a repeated step is refused with a message naming the problem; nothing is saved and the previous schedule stays in force.
Source: choice: bounds keep the cadence reasonable and stop a runaway number of emails per invoice; the request gives none.

### C-6: The first time reminders are turned on, the proposed schedule is -3, 0, 3, 7, 14, 30.
Observable: A workspace that has never saved a schedule sees exactly those six steps pre-filled on the settings page.
Source: choice: a common cadence; the request gives none.

### C-7: The send hour is a whole hour 0 to 23 in the workspace timezone, default 9.
Observable: With send hour 9 and timezone Europe/London, a step due on 12 March is due at 09:00 London time on 12 March. Values outside 0–23 or not whole are refused with a message and nothing is saved.
Source: choice: a time of day must be fixed somehow; the request is silent.

### C-8: The timezone is an IANA timezone name; for a workspace with no timezone already, the default is UTC.
Observable: The settings page shows the timezone; saving a name that is not a valid IANA timezone is refused with a message.
Source: choice: due dates are dates, so the reminder moment needs a zone; the request is silent.

### C-9: The custom note is optional plain text of at most 500 characters, and when present appears at the end of every reminder's body.
Observable: A 500-character note is accepted and appears at the end of the reminder email; a 501-character note is refused with a message and nothing is saved; with no note, the reminder has no such paragraph.
Source: choice: lets a business add its own words (for example bank details); the request is silent.

### C-10: A step's scheduled moment is the invoice's due date plus the step's offset in calendar days, at the send hour in the workspace timezone.
Observable: Due date 2027-03-12, step +7, send hour 9, zone UTC: the step's scheduled moment is 2027-03-19 09:00 UTC. A due date plus offset that crosses a month end or a leap day lands on the calendar date a calendar would show.
Source: implied: U-1 — steps are "N days" from the due date.

### C-11: Only invoices in the states Open or Partially paid are eligible for reminders.
Observable: An invoice in Open or Partially paid with a due date and an outstanding balance above zero receives its scheduled reminders; invoices in any other state do not.
Source: implied: "unpaid invoices".

### C-12: Invoices in Draft, Paid, Void or Written off, and invoices in any state this list does not name, never receive a reminder.
Observable: No reminder email is sent for an invoice in any of those states, scheduled or manual, even if a step falls due.
Source: implied: U-3 — those are the states in which the invoice is not unpaid and awaiting payment; an unnamed state is not eligible until someone classifies it.

### C-13: An invoice whose outstanding balance is zero or less never receives a reminder, whatever its state field says.
Observable: An Open invoice fully covered by a credit note receives no reminder.
Source: implied: U-3 — "unpaid" is about money still owed.

### C-14: When an invoice stops being eligible, its remaining reminders are cancelled and its history shows one entry "Reminders ended" with the reason.
Observable: The reason is one of: paid, void, written off, balance cleared, returned to draft, deleted, other state. The invoice's reminder status shows Ended with that reason; no further email is sent.
Source: implied: U-3.

### C-15: Just before a reminder is handed to the email provider, the invoice's current state and balance are checked, and nothing is sent if the invoice is no longer eligible.
Observable: An invoice paid at 09:00:10 whose reminder was due at 09:00:00 and had not yet been handed over sends nothing; the reminder's entry shows Cancelled and the history shows Reminders ended: paid.
Source: implied: U-3 — a payment arriving between scheduling and sending must win.

### C-16: A payment recorded after the email was handed to the email provider cannot recall that email.
Observable: A customer who paid minutes earlier can still receive a reminder that was already handed over; the history entry shows the send time so a member can see it predates the payment.
Source: implied: U-3 — a limit of email, stated so it is not mistaken for a bug.

### C-17: Each step is sent at most once for a given invoice and due date.
Observable: Across restarts, retries, duplicated scheduler runs and several servers running at once, the customer receives one email for invoice 1042, step +7, due date 2027-03-12, never two. A change of the invoice's due date makes its steps new (C-52).
Source: implied: U-2, U-17 — duplicate reminders are the worst failure of this feature.

### C-18: A reminder is addressed to the invoice's billing email addresses, at most five, and if the invoice has none, to the customer's primary email address.
Observable: An invoice with billing emails a@x.com and b@x.com sends one email addressed to both. An invoice with seven billing emails sends to the first five in the order the invoice lists them; the history lists exactly the recipients used. An invoice with no billing email and a customer primary email of c@x.com sends to c@x.com.
Source: choice: the request does not say who is reminded; the invoice's billing contacts are who the invoice was sent to; five is a cap so one mis-entered list cannot send to dozens.

### C-19: A reminder is sent as one message to all its recipients, not one message per recipient.
Observable: Two recipients on an invoice receive one email each copy of which lists both in the To line; the history shows one entry.
Source: choice: one history entry and one count per decision; the request is silent.

### C-20: If an invoice has no recipient address, its due steps are recorded as Skipped with reason "no recipient" and nothing is sent.
Observable: The history shows, for each due step, an entry Skipped — no recipient; the invoice's reminder status says there is no recipient.
Source: implied: C-18 takes for granted that there is an address.

### C-21: Every reminder shows: the business name as sender, the invoice number, the customer name, the outstanding balance with its currency, the due date, the number of days before or after the due date, a link to the invoice page, a stop-reminders link, the business's reply contact, and the custom note when set.
Observable: A reminder for invoice 1042, customer "Acme Ltd", outstanding 1,250.00 USD, due 12 March 2027, sent 19 March 2027, shows "1042", "Acme Ltd", "1,250.00 USD" (or an equally unambiguous amount-plus-currency form), the due date, "7 days overdue", the two links, the contact email and the note. Where payments have been applied it also shows the original total (C-23).
Source: implied: U-2 — the customer must know what, how much, since when, and how to pay.

### C-22: The subject line and opening sentence of a reminder say which of three situations applies: due in the future (step below 0), due today (step 0), or overdue (step above 0), and carry the invoice number.
Observable: A step -3 reminder's subject contains the invoice number and says it is coming due; a step 0 reminder says it is due today; a step 7 reminder says it is overdue.
Source: implied: U-2 — a reminder before the due date reads differently from a dunning notice.

### C-23: When the invoice is partly paid, the reminder shows the outstanding balance and also the original total.
Observable: Total 1,250.00 USD with 500.00 paid: the reminder states 750.00 USD outstanding and 1,250.00 USD total.
Source: implied: U-4.

### C-24: The amount in a reminder is the invoice's outstanding balance at the moment of sending, not at scheduling.
Observable: If a credit note reduces an invoice from 1,250.00 to 1,000.00 after the step was scheduled and before it sent, the email states 1,000.00.
Source: implied: U-4, U-14.

### C-25: The number of days in a reminder is the count of calendar days between the due date and the send date in the workspace timezone.
Observable: A reminder sent on 2027-03-19 for due date 2027-03-12 says 7 days overdue; one sent 2027-03-09 says due in 3 days; one sent on the due date says due today.
Source: implied: C-21.

### C-26: A reminder's invoice link opens that invoice's customer page without a login, cannot be guessed from the invoice number, and works for one invoice only.
Observable: Following the link in a reminder for invoice 1042 shows invoice 1042 with its pay action; editing the link or changing the number in it does not show another invoice.
Source: implied: U-2 — "follow the link and pay"; and C-106 — no leaking of other invoices.

### C-27: Opening the invoice link for an invoice that is no longer unpaid shows its current status and does not fail.
Observable: For a Paid invoice the page says it is paid; for a Void invoice, that it is void; for a Written off invoice, that it is closed; none shows an error.
Source: implied: C-16 — customers open the link from old emails after paying.

### C-28: Opening a reminder's stop-reminders link shows a confirmation page naming the invoice and changes nothing until the visitor presses the button on that page.
Observable: A mail scanner that fetches the link does not stop the reminders; a person who opens it and presses "Stop reminders" does.
Source: implied: U-8; choice: confirmation step because mail security scanners open links automatically.

### C-29: Once a customer confirms stopping, that invoice receives no further reminders, scheduled or manual, and the business cannot switch them back on for that invoice.
Observable: The invoice's reminder status shows "Stopped by customer" with the time; Send reminder now is refused with that reason; no scheduled step sends; Resume and switching a customer's exclusion off do not revive them. The stop applies to that invoice only, not to the customer's other invoices.
Source: choice: honouring the recipient's request is more important than the business's convenience; scope limited to one invoice because the link names one invoice.

### C-30: Confirming a stop for an invoice that is already settled, or already stopped, shows a page saying no more reminders will be sent and does not fail.
Observable: The page shows a neutral message; no error is displayed.
Source: implied: C-28 — links in old emails are opened late and twice.

### C-31: The reminder email's From shows the business name on the platform's own sending address, and its Reply-To is the workspace's reminder contact email.
Observable: A customer replying to a reminder writes to the reminder contact email; the platform does not read or act on replies.
Source: implied: U-2 — the customer must be able to answer the business; choice: the platform sends on its own domain so that authentication holds (C-89).

### C-32: Reminder emails are written in English.
Observable: Every fixed phrase in a reminder is English, whatever the customer or the currency.
Source: choice: the request is silent on language; one language is the loosest that serves.

### C-33: A member who may edit invoices can pause reminders on one invoice, optionally with a resume date and a note of at most 200 characters.
Observable: The invoice shows Paused, with who paused it, when, the note and the resume date if given. A note of 201 characters is refused with a message and the invoice is not paused.
Source: implied: U-5.

### C-34: While an invoice is paused, each step that falls due is recorded as Skipped with reason "paused" and nothing is sent.
Observable: History shows a Skipped — paused entry per due step.
Source: implied: U-5.

### C-35: A paused invoice resumes when a member presses Resume or at the start of the resume date in the workspace timezone, and steps whose moment fell during the pause are not sent after the resume.
Observable: Paused 1 March, resumed 10 March: a step due 5 March is logged Skipped — paused and never sent late; a step due 12 March sends on 12 March; the invoice shows its next scheduled reminder.
Source: implied: U-5 — resuming must not release a burst of old reminders.

### C-36: A member who may edit invoices can send a reminder now for one invoice.
Observable: Pressing Send reminder now shows "Queued"; the reminder is handed to the email provider within 5 minutes under normal operation and the history shows a Manual entry with recipients and outcome.
Source: implied: U-6.

### C-37: A manual reminder is refused if the invoice has had any reminder sent or queued (scheduled or manual) in the last 24 hours.
Observable: The refusal message states the time the last reminder was sent and when another is allowed; nothing is sent.
Source: choice: stops accidental double-clicks and two members both pressing the button; 24 hours because scheduled steps are at least a day apart.

### C-38: A manual reminder is also refused when any of these holds: the invoice is in an ineligible state (C-12), its balance is zero or less, it has no recipient, the customer stopped reminders for it, every recipient address is suppressed, the workspace's reminders are Off or suspended, or an operator stop is active.
Observable: The refusal names the first reason that applies; nothing is queued. Being paused, or the customer being excluded, does not refuse a manual reminder.
Source: choice: a manual send is a deliberate act of a member and may override their own pause, but not the customer's wish or the facts.

### C-39: A manual reminder does not use up a scheduled step and does not change when the scheduled steps are sent.
Observable: After a manual reminder on day 5, the step due on day 7 still sends on day 7 (subject to C-37 not applying to scheduled sends).
Source: choice: keeps the schedule predictable; the request is silent.

### C-40: A manual reminder uses the same message as a scheduled one and picks its before/today/overdue wording (C-22) from the invoice's due date compared with today; for an invoice with no due date it uses neutral wording and shows no due date or day count.
Observable: A manual reminder sent 2 days after the due date says overdue and "2 days overdue"; one for an invoice with no due date says only that payment is outstanding.
Source: implied: U-6, C-22.

### C-41: Each invoice shows its reminder history, newest first, readable by every member whose role can view the invoice; each reminder decision is one entry.
Observable: A reminder entry shows the date and time, its kind (a scheduled step with its offset, or Manual with the member who pressed the button), the recipients (for Skipped entries, those that would have received it), and the outcome with its reason (C-43). Events that are not reminders appear in the same history (C-111).
Source: implied: U-7.

### C-42: The workspace has one reminder log of all invoices, filterable by outcome, by date range, by customer and by invoice number, in pages of 50 entries.
Observable: Filtering by outcome Failed shows only Failed entries; filtering by invoice number 1042 shows only that invoice's; the 51st entry appears on page 2.
Source: implied: U-7 — "find the one thing that went wrong"; choice: page size 50.

### C-43: Every reminder entry has exactly one outcome from: Queued, Sent, Delivered, Bounced, Complaint, Failed, Cancelled, Skipped, Deferred; a Skipped entry has exactly one reason from: paused, customer excluded, customer stopped, no recipient, all recipients suppressed, payment pending, missed, superseded, operator stop; a Deferred entry has exactly one reason from: daily limit, operator stop.
Observable: The log and the invoice history display one outcome per entry and, for Skipped and Deferred, one of those reasons; no other outcome or reason appears. Queued means accepted for sending and not yet handed to the email provider; Cancelled means a Queued or Deferred reminder that was not handed over because the workspace was turned off or suspended or the invoice became ineligible; Deferred is temporary and becomes Sent, Skipped or Failed.
Source: implied: U-7 — and a closed list is what lets a person filter and trust it.

### C-44: Sent means the email was accepted by the email provider; Delivered, Bounced and Complaint are later results reported by the provider for that same email, and the entry shows the one with the latest event time.
Observable: An entry shows Sent until the provider reports; then Delivered, Bounced or Complaint. A report that arrives twice changes nothing further; a report that arrives after a report with a later event time does not replace it.
Source: implied: U-7, U-9 — acceptance is not delivery.

### C-45: A temporary failure to hand a reminder to the email provider is retried up to 3 times, each at least 10 minutes after the last attempt, and never later than 24 hours after the scheduled moment (for a manual reminder, after the moment it was queued).
Observable: History shows the attempts; after the fourth failed attempt, or at 24 hours, the entry is Failed with the provider's reason. Before each retry the invoice is checked again (C-15).
Source: choice: a bounded retry keeps a provider hiccup from losing the reminder and stops an endless loop; the request is silent.

### C-46: A permanent failure (address rejected, mailbox does not exist, domain does not exist) is not retried.
Observable: A rejection at handover makes the entry Failed at once with the provider's reason; a bounce reported after acceptance makes it Bounced (C-44); no second attempt is made for the same step.
Source: implied: U-9.

### C-47: A step that ended Failed is not sent again later; the next step proceeds as scheduled.
Observable: A Failed step +3 does not reappear on day 4; the step +7 still sends on day 7. A member can use Send reminder now.
Source: choice: a late reminder for a missed step would arrive out of step with its wording; the request is silent.

### C-48: An address that produced a hard bounce, a permanent rejection at handover or a spam complaint is suppressed for the workspace: no reminder is addressed to it until an Admin clears it.
Observable: An Admin sees a Suppressed addresses list in the Reminders settings with the address, the reason and the date, and a Clear control. A reminder to an invoice with two recipients, one suppressed, goes to the other only.
Source: implied: U-9 — repeated sends to bounced or complaining addresses damage the sender and annoy the recipient.

### C-49: When every recipient of a due step is suppressed, the step is recorded as Skipped with reason "all recipients suppressed".
Observable: History shows Skipped — all recipients suppressed; nothing is sent.
Source: implied: C-48.

### C-50: Each invoice shows one reminder status from: Scheduled (with the date and time of the next reminder), Paused, Excluded (customer), Stopped by customer, Not scheduled — no due date, Not scheduled — no recipient, Not scheduled — draft, Ended (with the reason from C-14), All steps done, Off (workspace reminders off or suspended).
Observable: An invoice shows exactly one of those at any time, and it matches what the system will do next.
Source: implied: U-5, U-7 — a person looking at an invoice must be able to tell what will happen.

### C-51: An invoice with no due date gets no scheduled reminders.
Observable: Its status reads "Not scheduled — no due date"; a manual reminder is possible meanwhile; setting a due date moves it to Scheduled (C-52, C-53); removing the due date cancels its remaining steps and moves it back to that status.
Source: implied: C-4 — steps are relative to a due date that must exist.

### C-52: No reminder is sent for a step whose scheduled moment is earlier than the latest of these events for that invoice: reminders turned on for the workspace; the workspace reactivated after a suspension; the schedule, send hour or timezone saved; the invoice's due date changed; the invoice becoming eligible again (issued from Draft, reinstated from Void, reopened from Paid or Written off, for example after a payment is reversed); the invoice resumed from a pause; the customer's exclusion switched off; reminders restored after a platform rollback (C-88).
Observable: Reminders turned on on 20 March for an invoice due 12 March with steps 0, 7, 14: the step 0 moment (12 March) and step 7 moment (19 March) are earlier and are never sent; the step 14 moment (26 March) is later and is sent on 26 March. A step whose moment is exactly the event's moment is still eligible. Such steps are not entered in the history, because they never fell due.
Source: implied: U-10, U-13 — a configuration change must not release a burst of back-dated reminders; choice: the list of events is the list of times an invoice's situation changes under the system's own hands.

### C-53: A step is identified by the invoice, its due date and its offset, so changing the due date makes every step new for that invoice.
Observable: Invoice due 12 March had step 0 sent on 12 March; its due date is moved to 30 April; step 0 sends again on 30 April and step -3 on 27 April if those moments are later than the change (C-52). Changing the send hour after step 0 was sent that day does not send step 0 again.
Source: implied: U-14 — a customer given more time should be reminded about the new date, and a changed setting should not repeat a sent reminder.

### C-54: A step that is late is still sent if it is no more than 48 hours past its scheduled moment, and otherwise is recorded as Skipped with reason "missed".
Observable: After a 5-hour outage a step due 3 hours before restart is sent on restart. After a 4-day outage a step due 3 days before restart is logged Skipped — missed and not sent.
Source: choice: U-17 — a reminder two days late is still useful, two weeks late is wrong in its wording; 48 hours.

### C-55: When more than one step of one invoice is due to be sent at the same time, only the step with the largest offset is sent and each other is recorded as Skipped with reason "superseded".
Observable: After an outage that spans steps 0 and 3 of an invoice and both are within 48 hours, one email goes out (step 3's); the log shows step 0 as Skipped — superseded.
Source: implied: U-17 — the customer must not receive several reminders at once.

### C-56: Under normal operation a scheduled reminder is handed to the email provider within 15 minutes after its scheduled moment, for up to 5,000 reminders due in the same workspace on the same day.
Observable: With send hour 9 and an invoice eligible at 09:00, the history shows Sent by 09:15 on an ordinary day.
Source: choice: "automatic" needs an expectation of promptness; 15 minutes and 5,000 are decided values, unconfirmed against any real platform capacity.

### C-57: A workspace has at most 5,000 scheduled reminder emails (not manual, not test) handed to the email provider per calendar day in its timezone; the rest are recorded as Deferred with the reason "daily limit" and handled on the next day.
Observable: The 5,001st due reminder of the day shows Deferred — daily limit; the next day it is sent if it is within 48 hours of its scheduled moment (C-54), otherwise Skipped — missed.
Source: choice: protects the sending reputation shared by all workspaces from a misconfiguration; 5,000 is a decided figure and is unconfirmed.

### C-58: Only Admins can change the workspace's reminder settings, turn reminders on or off, send test reminders, clear suppressed addresses, and restore earlier settings.
Observable: A Member or Viewer opening the Reminders settings sees them read-only with no save controls; the same action attempted through any other interface is refused with a "not permitted" message and changes nothing.
Source: implied: U-1, U-10, U-12 — "turn it on, configure it"; choice: Admin because the settings send email in the business's name.

### C-59: A Member can pause, resume and send reminders for an invoice and switch a customer's exclusion; a Viewer cannot.
Observable: A Viewer pressing Pause reminders is refused with a "not permitted" message, whatever the interface, and the invoice is unchanged.
Source: implied: U-5, U-6, U-15.

### C-60: Only members of the workspace can see its reminder history, log and settings; customers see only the emails and pages sent to them.
Observable: A member of another workspace opening an invoice's history address gets "not found"; a customer's reminder links never show history.
Source: implied: U-7 — and C-106 (no leaking).

### C-61: When an Admin turns reminders on, the page shows the number of invoices in scope (those in Open or Partially paid with a due date) and the date and time of the first reminder that will go out, before the Admin confirms.
Observable: The confirmation reads, for example, "42 open invoices; first reminder 21 Nov 2026 09:00 (Europe/London)". If no reminder is scheduled, it says so.
Source: implied: U-1 — "know that it worked"; U-13.

### C-62: An Admin can send a test reminder, at any time including while reminders are Off, for a chosen invoice of the workspace; it goes only to the Admin's own account email and is marked as a test in its subject.
Observable: The Admin receives within 5 minutes an email whose subject begins "[Test]", with the real data of the chosen invoice and the current settings (note, contact email), and with wording picked as for a manual reminder. No other address receives anything. A workspace with no invoice uses a clearly labelled sample invoice. During an operator stop the test is refused with a message.
Source: implied: U-11; choice: the sample invoice because a new workspace has nothing real to test with.

### C-63: A test reminder leaves no entry in the invoice's history or the workspace log, does not count toward the 24-hour manual limit (C-37), the daily limit (C-57) or any step, and its stop-reminders link changes nothing.
Observable: After a test, the invoice's history is unchanged; pressing the stop button on the page opened from the test email shows that this was a test and the invoice is unchanged.
Source: implied: U-11 — "no customer receives anything and no history".

### C-64: An Admin can send at most 10 test reminders per hour.
Observable: The 11th in an hour is refused with a message and the time at which another is allowed.
Source: choice: keeps the test button from being used to send mail in bulk; 10 per hour.

### C-65: Turning reminders off stops, within 1 minute, any further reminder from leaving the workspace, and cancels reminders queued but not yet handed to the email provider.
Observable: After Turn off, the page shows Off and every invoice shows status Off; queued reminders show Cancelled and never reach Sent; the log shows one workspace entry "Reminders turned off by <Admin>".
Source: implied: U-12.

### C-66: Turning reminders on again after Off sends no reminder for steps whose moment passed while Off.
Observable: Off for a week and on again: no backlog arrives; steps whose moment is later than the moment of turning on proceed (C-52).
Source: implied: U-12, U-13.

### C-67: Saving any reminder setting records a version: who, when, and the values before and after; Admins can list these versions, newest first, for the last 24 months.
Observable: The settings history shows, for example, "Sam changed send hour 9 → 8, 20 Nov 2026 10:14".
Source: implied: U-12 — undo needs a record; choice: 24 months.

### C-68: An Admin can restore an earlier version, which sets schedule, send hour, timezone, reminder contact email and custom note back to that version's values, subject to the same validation as a save, and records itself as a new version; it does not change On/Off.
Observable: Pressing Restore on a version shows the values it will set; after confirming, the settings show those values and the history shows "Restored version of <date>". If a value would fail today's validation, the restore is refused with a message naming it.
Source: implied: U-12 — "go back to the version before".

### C-69: Saving settings that were changed by someone else since the Admin loaded the page is refused, and the message names who changed them and when.
Observable: Two Admins load the page; the first saves; the second's save is refused with "Changed by <first Admin> at <time>; reload to see current settings"; nothing is overwritten.
Source: choice: prevents two Admins silently overwriting each other.

### C-70: A change to the settings takes effect for all open invoices within 1 minute, and the next-reminder time shown on each invoice reflects it.
Observable: After saving send hour 9 → 15, an invoice's next reminder time shows 15:00 within a minute, subject to C-52 and C-53.
Source: implied: U-10.

### C-71: The send-time check (C-15) also covers: the invoice being paused, the customer being excluded, the customer having stopped reminders, the workspace being Off or suspended, and an operator stop being active.
Observable: An invoice paused at 08:59:50 sends nothing for a step due at 09:00:00 that had not yet been handed to the email provider, and the history shows Skipped — paused.
Source: implied: U-5, U-12, U-16 — a control pressed must beat a send that has not yet happened.

### C-72: Two members pressing Send reminder now for the same invoice at the same time produce one reminder, and the second sees the refusal of C-37.
Observable: One Manual entry exists; the second member is shown the time the first was queued.
Source: implied: U-6, C-17.

### C-73: A scheduled step that falls due within 24 hours after a manual reminder is still sent.
Observable: Manual reminder at 15:00 on day 5; the step due at 09:00 on day 6 is sent at 09:00 on day 6.
Source: choice: manual reminders never change the schedule (C-39).

### C-74: A member who may edit invoices can switch "Do not send reminders" on or off for a customer; while it is on, every invoice of that customer shows Excluded and each due step is recorded as Skipped with reason "customer excluded".
Observable: The customer page shows the switch and who set it and when; the invoices' statuses read Excluded; switching it off applies C-52 and the invoices show Scheduled with their next reminder.
Source: implied: U-15.

### C-75: When several reasons for skipping apply to one due step, the recorded reason is the first of this order: customer stopped, customer excluded, paused, no recipient, all recipients suppressed, payment pending.
Observable: An invoice that is paused and whose customer is excluded logs Skipped — customer excluded.
Source: choice: a single reason per entry (C-43) needs a single rule; customer's decision first.

### C-76: A step that falls due while a payment on the invoice has been started but not yet confirmed or failed is recorded as Skipped with reason "payment pending" and is not sent later.
Observable: The history shows Skipped — payment pending; if the payment then fails, the invoice's next step still sends on its day.
Source: implied: C-15 — a customer who is paying should not be chased; choice: the skipped step is not replayed (C-47).

### C-77: Each of a customer's unpaid invoices gets its own reminder email, never a combined one.
Observable: A customer with three invoices due the same day receives three emails, each naming one invoice.
Source: choice: no digest — keeps each message about one invoice with one pay link and one stop link (C-29).

### C-78: Archiving a customer does not stop reminders for that customer's unpaid invoices; deleting an invoice does.
Observable: An invoice of an archived customer still shows Scheduled; a deleted invoice's reminders end with reason "deleted" (C-14), and its history stays visible in the workspace log for the retention period (C-86).
Source: choice: an archived customer still owes; the request is silent.

### C-79: A change to an invoice's billing email addresses or its customer is used by the next reminder sent.
Observable: Changing a recipient from a@x.com to b@x.com at 10:00 means a reminder due at 11:00 goes to b@x.com only.
Source: implied: U-14.

### C-80: Reopening an invoice (for example after a payment reversal) makes it eligible again under C-52, and its history shows that reminders restarted.
Observable: A Paid invoice reopened on 5 March with all steps in the past receives no scheduled reminder, its status reads "All steps done", and a member can send a manual reminder; if later steps exist they send.
Source: implied: U-14.

### C-81: The platform operator has an Emergency stop for all workspaces and a stop per workspace; while a stop is active no reminder email is handed to the email provider and each due step is recorded as Deferred with the reason "operator stop".
Observable: Within 1 minute of pressing it, the operations view shows the stop as active and no new Sent entries appear; due steps show Deferred — operator stop.
Source: implied: U-16 — undoing a mistake made by a system that runs alone.

### C-82: Releasing an operator stop requires choosing Send or Discard for the deferred reminders; Send hands them over subject to C-54 and C-55, and Discard records each as Skipped with reason "operator stop".
Observable: After Discard, the deferred entries read Skipped — operator stop and nothing is sent; after Send, entries within 48 hours of their moment are Sent and older ones Skipped — missed.
Source: choice: after a mistaken send the operator must be able to drop the backlog, after an outage to flush it.

### C-83: The operations view shows, per day and per workspace, the number of reminders in each outcome and the age of the oldest queued reminder, and lets the operator find an individual reminder by workspace, invoice number, recipient address or entry identifier.
Observable: Searching a recipient address shows each reminder to it, with workspace, invoice, outcome and reason.
Source: implied: U-16 — "find the one thing that went wrong".

### C-84: An alert reaches the operators within 5 minutes when the oldest queued reminder is more than 60 minutes past its scheduled moment, or when more than 10% of at least 20 reminders handed to the email provider in the last hour failed.
Observable: A provider failing 100% triggers an alert within 5 minutes of the 20th failure.
Source: implied: U-16; choice: thresholds 60 minutes, 10%, 20 reminders — decided, not derived.

### C-85: The operator can list, for any workspace and time window, every reminder sent with its time, invoice number and recipients.
Observable: The list shows time, invoice number, recipients and outcome for each reminder sent in the window.
Source: implied: U-16 — a sent email cannot be recalled (C-16), so the list is the only remedy for a mistaken send.

### C-86: Reminder history, the log and settings versions are kept for 24 months after the entry's date, then deleted.
Observable: An entry dated 25 months ago is not shown anywhere; an entry dated 23 months ago is.
Source: choice: bounds data retention; the request is silent; 24 months.

### C-87: Releasing this feature changes no existing workspace, customer or invoice data: no invoice changes state, no recipient is added, and no customer is excluded or stopped by it.
Observable: Before and after release every invoice has the same state, balance, due date and billing emails; each shows reminder status Off.
Source: implied: U-13 — carrying on with data that exists from before.

### C-88: Rolling the feature back at platform level stops all reminders, loses no settings, history, pauses, exclusions or stops, and when the feature is restored no reminder is sent for a moment that passed during the rollback.
Observable: While rolled back no reminder email leaves and the Reminders page is unavailable; after a restore, a workspace's settings, histories and pauses are as they were, and no reminder is sent for a moment that fell in between (C-52).
Source: implied: "go back to the version before".

### C-89: Reminder emails are sent from a sending domain whose SPF, DKIM and DMARC checks pass in the recipient's mail system, and no reminder is sent to any real customer until that is so.
Observable: The received message's authentication headers show SPF, DKIM and DMARC as pass.
Source: implied: runtime — mail providers reject or junk unauthenticated mail, and the feature's whole purpose is that the mail is read; this is a precondition for leaving a development environment.

### C-90: Outside production, no reminder is ever delivered to a real customer address; every reminder goes to a sandbox inbox instead and its subject says so.
Observable: In a staging environment with real customer addresses loaded, no such address receives mail; the sandbox inbox receives it, with the subject marked as non-production.
Source: implied: runtime — before this ships beyond development, data copied from production must not cause real mail.

### C-91: Saving settings, pressing Send reminder now and pressing Send test reminder return within 2 seconds, showing Queued, and do not wait for the email provider.
Observable: With the provider taking 30 seconds to respond, the page still answers within 2 seconds.
Source: implied: runtime — an outside provider can be slow and request time limits apply; choice: 2 seconds.

### C-92: If the email provider does not answer a handover within 30 seconds, that attempt counts as a temporary failure (C-45).
Observable: With a provider that never answers, the entry shows a failed attempt after 30 seconds and the retry rules of C-45 apply.
Source: implied: runtime — outside calls time out; choice: 30 seconds.

### C-93: When the email provider's own sending rate limit is reached, reminders wait as Queued and are handed over as the limit allows; they are not dropped and not counted as failures.
Observable: With a limit lower than the number due, the excess shows Queued and drains over time; none shows Failed for that cause. The 15-minute promise of C-56 holds only while the due volume is within the provider's limit. The provider's limit figure is unconfirmed.
Source: implied: runtime — providers cap sending rate.

### C-94: The scheduler evaluates due steps at least every 5 minutes.
Observable: A step due at 09:00 is evaluated no later than 09:05.
Source: choice: supports the 15-minute promise (C-56); the request is silent.

### C-95: When the send hour does not exist on a day in the workspace timezone (a clock change skips it), the reminder is due at the first moment of that day at or after it that does exist; when it occurs twice, it is due at its first occurrence only.
Observable: Send hour 2 in a zone that jumps from 02:00 to 03:00 sends at 03:00 that day; in a zone that repeats 01:00–02:00, hour 1 sends once, at the first 01:00.
Source: implied: runtime — time zones change their clocks, and C-17 forbids two sends.

### C-96: Provider reports of delivery, bounce or complaint are accepted only if they are authentic; an unauthentic report changes nothing.
Observable: A forged bounce notice for a recipient does not suppress that address and does not change any entry.
Source: implied: C-44, C-48 — the report URL is public; otherwise anyone could suppress a customer's address.

### C-97: A payment recorded late, with a payment date in the past, ends reminders from the moment it is recorded and alters no earlier history entry.
Observable: A payment dated Friday but recorded Monday: a reminder sent on Saturday stays in the history as sent; no reminder is sent from Monday on.
Source: implied: C-15, C-16 — the system can only act on what it knows.

### C-98: A reminder's invoice link and stop-reminders link keep working for as long as the invoice's history is kept (C-86).
Observable: A link from a reminder sent 20 months earlier opens its page; for a reminder from 25 months earlier the link shows a "no longer available" page and no invoice data.
Source: choice: customers open old emails late; tying link life to retention bounds the data.

### C-99: The workspace's Reminders page shows, for the last 7 days, the number of reminders Sent, Failed and Skipped and the time of the last reminder sent; the Failed number opens the log filtered to Failed.
Observable: After a day of reminders, the page shows the counts and the date of the last one; pressing the Failed count opens the log with the Failed filter applied.
Source: implied: U-1, U-7 — an Admin must see that the feature is working and see failures without searching.

### C-100: Saving settings and turning reminders on remain within 2 seconds for a workspace of up to 100,000 open invoices, with the effect on the invoices applying within 1 minute (C-70).
Observable: A workspace with 100,000 open invoices saves a schedule within 2 seconds, and all its invoices show the new next reminder within 1 minute. The 100,000 figure is a decided bound and is unconfirmed.
Source: choice: runtime — a bound is needed; the request is silent.

### C-101: Any email suppression or do-not-email preference the host product already holds for an address or customer is honoured: such a customer is treated as excluded (C-74) and such an address as suppressed (C-48).
Observable: A customer previously marked do-not-email by the business never receives a reminder after release; the log shows Skipped — customer excluded.
Source: implied: C-87 — existing data and the choices already made in it must still hold.

### C-102: Whether further legal footer content (such as a postal address) is required in reminder emails in the jurisdictions where the businesses' customers live is unconfirmed; a business can add its own through the custom note (C-9).
Observable: A custom note containing a postal address appears at the end of the reminder.
Source: implied: runtime — rules on commercial and transactional email vary by country; this ships with sender identity and a stop link (C-21), and the remainder awaits confirmation.

### C-103: Reminders never block, delay or fail recording a payment, voiding, editing or issuing an invoice.
Observable: With the email provider down and the scheduler stopped, a payment can still be recorded and the invoice becomes Paid at once.
Source: implied: "what must not change" — the existing invoicing flow does not depend on reminders.

### C-104: Sending an invoice to a customer for the first time and any invoice emails that exist today keep working as they do today and are not counted as reminders.
Observable: The initial invoice email is sent as before and produces no entry in the reminder history.
Source: implied: C-87.

### C-105: Reminders never change an invoice's state, amounts, due date, billing emails or customer.
Observable: After any number of reminders, an invoice's fields are unchanged except its reminder history and status.
Source: implied: what must not change.

### C-106: A reminder, a reminder link, a reminder page or a history view never shows any data of another invoice, another customer or another workspace.
Observable: Following the links of a reminder for invoice 1042 never shows invoice 1043 or another customer's name; a member of workspace A never sees an entry of workspace B.
Source: implied: C-26, C-60 — the thing that must never happen.

### C-107: A reminder is only ever addressed to the invoice's billing addresses or the customer's primary address (C-18), and a test reminder only to the Admin who requested it.
Observable: No reminder is delivered to any address that was not on the invoice or customer at send time, or the requesting Admin for a test.
Source: implied: C-18, C-62 — never email the wrong person.

### C-108: Every rule here — eligibility, permissions, limits, pauses, exclusions, stops, the 24-hour manual limit — applies identically through every interface that can cause or change a reminder (the web pages, any programmatic interface, bulk actions and imports).
Observable: An invoice paused in the web page is also not sent when the same action was done through the programmatic interface; a Viewer is refused through each interface.
Source: implied: what must never happen — a rule enforced in one path and not another.

### C-109: A customer's confirmed stop (C-29) is honoured on every path, including a reminder already queued and a manual reminder.
Observable: A reminder queued at 08:59 for a customer who confirms the stop at 08:59:30 is not sent (C-71); a manual reminder after the stop is refused.
Source: implied: U-8 — never contact someone against their stated wish.

### C-110: No reminder history entry is lost when an invoice is voided, settled or deleted, or when its customer is archived; entries are removed only at the end of the retention period.
Observable: A deleted invoice's entries still appear in the workspace log until 24 months after their dates.
Source: implied: U-7, C-86 — data lost on the way.

### C-111: Besides reminder entries, an invoice's history records these events, each with who and when: Paused (with note and resume date), Resumed (by a member, or automatically), Stopped by customer, Reminders ended (with reason), Reminders restarted after reopening; the workspace log also records: reminders turned on or off, settings saved, settings restored, address suppressed, suppression cleared, customer exclusion switched on or off, operator stop started and released.
Observable: Pausing an invoice adds a Paused event naming the member, the time, the note and the resume date; an Admin turning reminders off adds one workspace event naming the Admin.
Source: implied: U-5, U-7, U-12, U-16 — "find what went wrong" needs the controls' effects on record.

### C-112: A billing email address on an invoice that is not syntactically valid is ignored when choosing recipients; if no valid address remains, the invoice has no recipient (C-20).
Observable: An invoice whose only billing email is "acme@" shows "Not scheduled — no recipient" and logs Skipped — no recipient for each due step.
Source: implied: C-18 — addresses are free text in the host product.

### C-113: A member can pause an invoice only while it is in Open or Partially paid; a resume date must be a date after today in the workspace timezone and at most 365 days ahead; pausing an already paused invoice replaces its resume date and note; without a resume date a pause lasts until a member resumes.
Observable: Pausing a Paid invoice, or entering a resume date of today or 366 days ahead, is refused with a message and changes nothing; pausing again with a new date changes the date shown and is not an error; a pause with no date is still in force a year later.
Source: choice: bounds for a control the request does not mention; 365 days.

### C-114: A reminder that the email provider accepted but whose acceptance was never confirmed to the system is not sent a second time on retry.
Observable: After a provider that processes a handover but whose answer is lost, the customer receives one email, and the entry ends Sent or Failed once.
Source: implied: C-17, C-92 — the retry after an unconfirmed handover is where duplicates come from.

### C-115: While a workspace is suspended or closed, no reminder is sent for it, its invoices show Off, queued reminders are cancelled, and on reactivation C-52 applies.
Observable: A workspace suspended on 1 March and reactivated on 15 March sends no reminder for moments between, and sends those after 15 March.
Source: implied: the host product has account states; a business that cannot use the product must not send mail in its name.

### C-116: At the scheduled moment of each step of an eligible invoice that has a recipient, the customer receives one reminder email for that step.
Observable: Invoice 1042, due 12 March, steps -3, 0, 7, send hour 9, UTC, balance outstanding, one billing address: emails arrive at about 09:00 UTC on 9 March, 12 March and 19 March, none on other days.
Source: request — "automatic reminders for unpaid invoices".

### C-117: The operations view and the stop controls are available to platform operators only; a workspace Admin or Member who tries to reach them is refused.
Observable: A workspace Admin opening the operations address, or pressing a stop through any interface, gets a "not permitted" message and nothing changes; their own workspace's log (C-42) stays available.
Source: implied: U-16 — the operations view spans all workspaces (C-60, C-106), so it must not be reachable by any one of them.
