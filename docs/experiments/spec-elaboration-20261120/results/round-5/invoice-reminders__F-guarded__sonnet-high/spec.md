## Use cases

### U-1: A customer's billing contact is reminded of an unpaid invoice, to pay it
Flow: Invoice INV-1001 for 1,200.00 USD is issued, due 2026-12-01, unpaid. With reminders enabled and the default schedule, at the send time (09:00 in the business time zone) on 2026-12-01 the billing contact receives one email for INV-1001 stating the invoice number, the outstanding balance 1,200.00 USD, the due date 2026-12-01 and that it is due today, and how to pay. If it is still unpaid on 2026-12-08 (7 days after due) they receive a second email stating it is 7 days overdue; likewise on 2026-12-15 (14 days) and 2026-12-31 (30 days). After the 30-day reminder nothing more is sent automatically.
Source: request

### U-2: A customer pays and the reminders stop
Flow: The customer pays INV-1001 in full on 2026-12-05 and staff record the payment. The invoice becomes paid. On 2026-12-08, 2026-12-15 and 2026-12-31 no email is sent for it. The invoice's reminder history shows the later steps as not sent because the invoice was settled.
Source: implied: "unpaid invoices" — an invoice that is no longer unpaid must not be reminded

### U-3: A customer pays part of an invoice and keeps being reminded of the rest
Flow: INV-1002 total 1,000.00 USD, due 2026-12-01. On 2026-12-03 a payment of 400.00 USD is recorded; the invoice is partially paid with balance 600.00 USD. The reminder due 2026-12-08 is sent and states an outstanding balance of 600.00 USD.
Source: implied: "unpaid invoices" — a partially paid invoice is still unpaid for the amount outstanding

### U-4: An operator configures reminders and turns them on
Flow: An operator with permission to manage reminders opens the reminder settings, sees every setting with its current value (reminders initially off), enters the sender address and a payment-instructions text, optionally changes the schedule (default: 0, 7, 14, 30 days after the due date), send time (default 09:00) and business time zone (default UTC), and turns reminders on. An invalid value is refused with a message naming the setting and nothing is saved. From the next evaluation, reminders go out under the saved settings.
Source: implied: "Set up automatic reminders" — automatic behaviour needs someone to set it up and a sender identity

### U-5: An operator turns reminders off, and back on
Flow: The operator turns reminders off (for example because of a wrong template or an outage on the customer side). From that moment no reminder email is sent; invoices, payments and history are untouched. Later the operator turns reminders on again; steps whose window is still open are sent, older ones are not made up. This is also the way back to the behaviour before the feature was on.
Source: implied: operator stop/start and "go back to the version before"

### U-6: An operator pauses reminders for one invoice, then resumes them
Flow: A customer disputes INV-1003. The operator pauses reminders on INV-1003; the invoice shows "reminders paused", who paused it and when. No reminder is sent for it while paused. Later the operator resumes; the invoice shows reminders active and its next scheduled step.
Source: implied: staff need to stop reminders for an invoice that is unpaid but must not be chased

### U-7: An operator reviews what was and will be sent for an invoice
Flow: On the invoice, the operator sees a reminder history: each step with its offset in days, scheduled date, outcome (pending, sent, skipped, failed, outcome unknown) with the reason where it is not sent, the time, and for each recipient the address and result. They also see the next scheduled step with its date, or the reason there is none.
Source: implied: operator "observe"

### U-8: An operator finds and fixes a reminder that was not delivered
Flow: INV-1004 has no billing email. On its step date the step stays pending with the reason "no recipient". The operator lists reminder steps that are failed or pending-with-problem, finds INV-1004, adds an email address to the invoice, and at the next evaluation (within the step's window) the reminder is sent. If the window closes first, the step is recorded as failed with reason "no recipient". Other problems (address rejected, delivery provider error, bounce) are shown with their reason in the same list.
Source: implied: unhappy path — a reminder that cannot be delivered must be visible and recoverable

### U-9: A business turns reminders on while many overdue invoices already exist
Flow: On the day reminders are first turned on, 300 invoices are unpaid and overdue by various amounts. Only invoices that have a step whose date is within the last 3 days (or today) receive a reminder, one email per invoice. An invoice 20 days overdue receives nothing that day and will next receive its 30-day reminder on its date.
Source: implied: "carry on with data that already exists" — switching on must not mail a backlog

### U-10: Staff change an invoice while its reminder sequence is under way
Flow: INV-1001's due date is moved from 2026-12-01 to 2026-12-20 after the 0-day and 7-day reminders were sent. The steps already sent are not sent again; the remaining steps (14, 30 days) now fall on 2027-01-03 and 2027-01-19. Changing the amount changes the balance quoted in the next reminder.
Source: implied: invoices change; sent reminders must not repeat

### U-11: A customer with several contacts or several unpaid invoices
Flow: INV-1005 lists two billing emails; each receives its own copy of the reminder. A customer with three unpaid invoices whose steps fall on the same day receives three separate emails, one per invoice.
Source: implied: more than one of a thing

### U-12: A person without permission tries to change reminder settings
Flow: A user who lacks permission to manage reminders opens or tries to change settings, pause an invoice or turn reminders on or off. The action is refused with a message saying they lack permission; nothing changes.
Source: implied: settings that send email to customers need access control

### U-13: The reminder run is late, interrupted or fires twice
Flow: The scheduler fires an evaluation an hour late, runs it twice at once, or the system is down for a day. After recovery each due step is sent at most once per recipient; steps missed by 3 or fewer days are sent late, older ones are recorded as skipped.
Source: implied: unhappy path / operator recovery

### U-14: A developer or tester runs the system outside production
Flow: In a non-production environment, reminders for invoices never reach real customer addresses; the operator can see what would have been sent.
Source: implied: a development environment must not email real customers

### U-15: An operator checks what an evaluation did
Flow: The operator opens the evaluation log and sees, for each evaluation, when it started and ended and how many steps it sent, skipped, failed, left pending for retry, and recorded as outcome unknown; an evaluation on a day with nothing due shows zeros. An evaluation that could not read the invoices says so.
Source: implied: operator "observe"

### U-16: A paid invoice is reopened
Flow: A payment on INV-1001 is reversed (bounced cheque); the invoice goes back to open with balance 1,200.00 USD. Steps already sent stay sent; steps not yet sent whose window is open are sent at the next evaluation; later steps follow their dates.
Source: implied: an invoice's state can go back to unpaid

### U-17: The delivery service fails or an address bounces
Flow: The delivery provider is unreachable for three hours on a send day. Nothing is lost: when it returns, the pending steps in their window go out. A message accepted by the provider later bounces; the history shows that recipient as bounced and no further reminders for that invoice go to that address.
Source: implied: unhappy path — a thing it depends on failing

### U-18: A customer replies to a reminder
Flow: The customer replies "we paid on Friday". The reply reaches the reply-to address (or the sender address). The reminder system does not read it, does not stop the sequence and changes no invoice; staff act on it.
Source: implied: a reminder email invites a reply

## Clauses

### C-1: Reminders are only for issued invoices with an outstanding balance
Observable: An invoice that is issued (not a draft) and whose outstanding balance is greater than 0.00 is eligible for reminders; any other invoice never receives one.
Source: request ("unpaid invoices")

### C-2: Invoice states that receive reminders
Observable: The invoicing states considered are draft, open, partially paid, paid, void and written off. Only open and partially paid invoices receive reminders. Any further state the invoicing system has is treated as not receiving reminders until listed here.
Source: choice: the invoicing system's states are not given; deny by default is the safe reading

### C-3: Settled or withdrawn invoices stop reminders
Observable: Once an invoice is paid in full, void, written off, or has a balance of 0.00 or less (fully paid, credited or refunded), no further reminder is sent for it; unsent steps are shown in its history as skipped with the reason "invoice no longer unpaid" for as long as it stays so (C-55 covers its return).
Source: implied: U-2

### C-4: Partially paid invoices are reminded for the remaining balance only
Observable: For a partially paid invoice the reminder states the outstanding balance (total minus payments and credits), not the original total. In U-3 the email states 600.00 USD.
Source: implied: U-3

### C-5: Default schedule is relative to the due date
Observable: Each reminder step is an integer number of days relative to the invoice's due date (negative = before, 0 = on, positive = after). The default schedule is 0, 7, 14 and 30. For due date 2026-12-01 the steps fall on 2026-12-01, 2026-12-08, 2026-12-15 and 2026-12-31.
Source: choice: the request gives no timing; reminders begin on the due date, so customers are not nagged before payment is late

### C-6: Schedule limits
Observable: The schedule holds 1 to 10 offsets; each an integer from -30 to 365; offsets are distinct. Anything else is refused with a message naming the schedule and nothing is saved. The offsets may be entered in any order and are shown ascending.
Source: choice: bounds the cost of a bad entry; the request names none

### C-7: Sequence ends after the last step
Observable: After the step with the largest offset has been handled (sent, skipped or failed), no further automatic reminder is sent for that invoice, however long it stays unpaid. The invoice's view says the sequence is finished.
Source: implied: "reminders" must end; an endless loop of emails to a customer is not wanted

### C-8: Step dates are calendar dates in the business time zone
Observable: The due date is a calendar date without a time. A step's date is the due date plus the offset, counted in calendar days in the business time zone. Month ends, year ends and 29 February are counted as calendar days (due 2026-12-31 and offset 7 is 2027-01-07; due 2028-02-28 and offset 1 is 2028-02-29).
Source: implied: "days" in a schedule need a calendar

### C-9: Send time and time zone
Observable: A step is sent at the first evaluation at or after the send time (default 09:00) on the step's date in the business time zone (default UTC). Send time is HH:MM from 00:00 to 23:59. The time zone must be a valid IANA zone name. On a day when the local send time does not exist or occurs twice due to a daylight-saving change, the step is still sent once on that date.
Source: choice: the request gives no time; business hours morning is a safe default

### C-10: Every day of the week counts
Observable: A step is sent on its date even if it is a Saturday, Sunday or public holiday; dates are not moved.
Source: choice: skipping days adds a rule the request does not ask for

### C-11: Catch-up window
Observable: A step whose date is today or up to 3 calendar days earlier (business time zone) is still sent. A step more than 3 days past is not sent and is recorded as skipped with the reason "window expired"; the record is made at the first evaluation after the window closes, or, if reminders were off, at the first evaluation after they are turned on. Until then it is shown as pending (C-51).
Source: choice: lets short outages and late runs recover without mailing old backlog

### C-12: Only the latest due step is sent
Observable: If at one evaluation more than one step of the same invoice is sendable, only the one with the largest offset is sent; the others are recorded as skipped with the reason "superseded". An invoice never receives more than one reminder per evaluation.
Source: choice: never two reminders to the same customer for the same invoice at once

### C-13: Steps before the invoice was issued are not sent
Observable: A step whose date is earlier than the date the invoice was issued (the date in the business time zone) is recorded as skipped with the reason "before issue date" and is not sent.
Source: choice: a pre-due reminder must not appear right after an invoice is issued late

### C-14: No due date, no reminders
Observable: An issued unpaid invoice without a due date gets no reminders; its view says "no due date".
Source: implied: the schedule is relative to the due date

### C-15: Reminders are off until an operator turns them on
Observable: Before an operator has turned reminders on, no reminder is sent. The setting shows "off".
Source: choice: a sender identity must exist first

### C-16: Turning reminders on is refused without a sender
Observable: An attempt to turn reminders on while the sender address is empty or invalid is refused with a message naming the sender address, and reminders stay off.
Source: choice

### C-17: Turning reminders off stops sending at once
Observable: After the operator turns reminders off no further reminder email is sent, including by an evaluation already under way for invoices it has not yet sent to. History and settings are kept.
Source: implied: U-5

### C-18: Turning reminders on does not mail a backlog
Observable: After turning on (or after a period off or paused), only steps within the catch-up window of C-11 are sent; nothing older is sent.
Source: implied: U-9

### C-19: Settings
Observable: The settings are: on/off; schedule (C-6); send time (C-9); business time zone (C-9); sender display name (up to 100 characters, may be empty); sender email address (required, valid address up to 254 characters); reply-to email address (optional, valid address up to 254 characters; where empty replies go to the sender address); payment-instructions text (optional, up to 1,000 characters).
Source: choice: the settings needed by the request's behaviour

### C-20: Settings changes apply to later evaluations and are recorded
Observable: A saved change applies from the next evaluation (turning reminders off applies at once, C-17); each change is listed in a settings log with who, when, the setting, old value and new value. The log is kept at least 24 months.
Source: implied: U-4, operator observe

### C-21: Only permitted users change settings or invoice controls
Observable: Turning on/off, editing settings and pausing/resuming an invoice are refused for users without the permission to manage reminders; the message says they lack permission; nothing changes.
Source: implied: U-12

### C-22: Pausing an invoice
Observable: While reminders are paused for an invoice, no reminder is sent for it. The invoice shows "reminders paused", by whom, and since when.
Source: implied: U-6

### C-23: Resuming an invoice
Observable: After resume, steps still within their window at the next evaluation are sent; steps whose window closed while paused were recorded as skipped with the reason "window expired".
Source: choice: consistent with C-11; no make-up mail

### C-24: Who receives the reminder
Observable: Recipients are the billing email addresses listed on the invoice. If it lists none, the customer's default billing email; if neither, there is no recipient. At most 5 recipients, taken in the order the invoice lists them after addresses repeated (ignoring upper/lower case) are counted once, are used; the history notes how many listed addresses were not used.
Source: choice: the request does not say who

### C-25: Each recipient gets their own message
Observable: Every recipient receives a separate email; one recipient's address is not visible to the others.
Source: choice

### C-26: One email per invoice per step
Observable: Each reminder email concerns exactly one invoice; unpaid invoices of one customer are not combined.
Source: choice: keeps each email and history entry simple

### C-27: No recipient
Observable: If an eligible step has no recipient, it stays pending with the reason "no recipient", and is re-checked at each evaluation while its window is open. If it gains a recipient, it is sent. If the window closes first it is recorded as failed with the reason "no recipient".
Source: implied: U-8

### C-28: Message content
Observable: Each reminder contains: the sender display name or address; the invoice number; the outstanding balance with its currency code; the due date; the timing line of C-29; the invoice's payment link where it has one, otherwise the payment-instructions text where one is set; a way to ask questions (reply goes to the reply-to address); a line saying to disregard the reminder if already paid. Where the invoice has no payment link and no payment-instructions text is set, the payment item is omitted. The subject contains the invoice number.
Source: implied: "reminders for unpaid invoices" must say which invoice, how much, by when

### C-29: Timing line
Observable: The message states the position of the send date (business time zone) against the due date: when they are the same day "due today"; when the send date is earlier "due in N days", N being the number of calendar days from the send date to the due date; when later "N days overdue", N being the number of calendar days from the due date to the send date. A step sent late (C-11) states the figure for the day it is actually sent, not its nominal offset.
Source: implied: customer needs the urgency

### C-30: Reminder language
Observable: The message is in English.
Source: choice: the request names no language

### C-31: Reminder history per invoice
Observable: For every step the invoice shows: offset, scheduled date, outcome (pending, sent, skipped, failed, outcome unknown), the reason for skipped/failed, the time of the last attempt, and per recipient address and result (accepted, rejected, bounced where the delivery provider reports it, suppressed, error). It also shows the next scheduled step and its date.
Source: implied: U-7

### C-32: A step is sent at most once per recipient
Observable: Whatever happens — two evaluations at the same time, an evaluation run twice, a restart, a retry — no recipient receives more than one email for the same invoice and offset.
Source: implied: "a thing done twice that should happen once"

### C-33: An already sent offset is not sent again
Observable: Steps are identified by their offset in days. An offset that was already sent for an invoice is not sent again even if the due date or the schedule changes (U-10).
Source: choice

### C-34: Due date changes recompute dates
Observable: When the due date changes, the dates of steps not yet sent are recomputed from the new due date.
Source: implied: U-10

### C-35: Schedule changes
Observable: A saved schedule change applies to steps not yet sent; offsets removed are not sent, added offsets are sent on their dates if still within the window and not excluded by C-78.
Source: implied: schedule is configurable, so it can change

### C-36: Payment right before sending
Observable: The invoice state is checked immediately before each email is handed to the delivery provider; a payment, void, pause or turning off recorded before that check prevents the send; one recorded after the check does not recall an email already handed over.
Source: implied: race between payment and sending

### C-37: Delivery failure and retry
Observable: If the delivery provider answers with a temporary failure, the attempt is retried to that recipient at an evaluation at least 60 minutes later, up to 3 attempts in total per recipient and step; after the third failure the recipient's result is "error" and no further attempt is made.
Source: choice

### C-38: Step outcome from per-recipient results
Observable: A step is "sent" once at least one recipient's email was accepted. Otherwise, once no attempt remains or its window has closed, it is "outcome unknown" if any recipient's result is "outcome unknown", and "failed" if not.
Source: choice

### C-39: Evaluation frequency
Observable: While reminders are on, an evaluation begins at least once every 60 minutes, so a step is first attempted no later than 60 minutes after its send time.
Source: choice: needed for C-9 and C-37

### C-40: Large volume
Observable: When 50,000 reminder emails are due on one day, every one is handed to the delivery provider or has its result recorded within 2 hours of the send time. The figure is a decided target, unconfirmed against the delivery provider.
Source: choice

### C-41: Reminders never change invoice data
Observable: Reminders do not modify an invoice's status, amounts, due date or payments.
Source: implied: what must not change

### C-42: Reminder failures never block invoicing
Observable: Creating invoices, recording payments and voiding work as without the feature, even if reminders are off, failing or running.
Source: implied: what must not change

### C-43: Non-production safety
Observable: In an environment not marked production, no reminder is delivered to a customer address; the history shows each step with each recipient's result "not delivered (non-production)" and the content that would have been sent.
Source: implied: U-14

### C-44: History retention
Observable: Reminder history is kept at least 24 months after each step.
Source: choice

### C-45: Reminders need no per-invoice action
Observable: Every eligible invoice, including one issued before reminders existed or were turned on, is reminded under the schedule with no action by anyone on that invoice and with no change to its data.
Source: request ("automatic")

### C-46: A refused settings change saves nothing
Observable: When any value in a settings change is invalid, the whole change is refused with a message naming each invalid setting; the settings keep their previous values and nothing is added to the settings log.
Source: implied: U-4 unhappy path

### C-47: No line breaks or control characters in sender fields
Observable: A sender display name, sender address or reply-to address containing a line break or another control character is refused as in C-46.
Source: implied: these values become email header fields; a line break would let a value add headers

### C-48: Payment instructions are plain text
Observable: The payment-instructions text appears in the email as the characters entered; markup in it (such as `<b>`) is shown as typed, not interpreted.
Source: implied: operator-entered text placed in customer email

### C-49: Amount format
Observable: The outstanding balance is shown with its ISO currency code and with the currency's standard number of decimal places (2 for USD and EUR, 0 for JPY): "1,200.00 USD". Separators and where the code sits are not fixed.
Source: implied: money in a customer message must be unambiguous

### C-50: Outcome unknown
Observable: If an attempt was started but no result was recorded within 15 minutes (for example because the system stopped), that recipient's result is shown as "outcome unknown" and that attempt is never repeated automatically.
Source: choice: protects C-32 (never twice) at the price of possibly one missed reminder, shown to the operator

### C-51: Pending steps
Observable: A step not yet sent and still possible is shown "pending" with its computed date, including steps in the future and steps that were due but waiting for a retry or a recipient.
Source: implied: U-7

### C-52: Later bounce
Observable: When the delivery provider reports that an accepted message bounced, that recipient's result changes to "bounced" with the time; the step stays "sent". Where the provider reports no bounces, no recipient is shown as bounced.
Source: implied: U-17

### C-53: No more reminders to a bounced or rejected address on that invoice
Observable: After a permanent bounce or a rejection the delivery provider attributes to the recipient's address (no such mailbox, invalid address) for an invoice, later steps of that invoice show that address as "suppressed" and no email is sent to it. If every recipient is suppressed the step is failed with the reason "no deliverable recipient".
Source: choice: repeated mail to dead addresses harms the sender's standing; scoped to the invoice so the address is retried on other invoices

### C-54: Recipients added after a step is sent
Observable: An address added to the invoice after a step reached sent is not sent that step; it receives later steps.
Source: choice

### C-55: A reopened invoice
Observable: An invoice that returns to open or partially paid with balance above 0.00 is eligible again; offsets already sent are not repeated (C-33), and unsent steps follow C-11.
Source: implied: U-16

### C-56: An invoice that no longer exists
Observable: An invoice deleted from the invoicing system gets no reminder; sent history for it stays for the retention in C-44.
Source: implied: depends on the invoice existing

### C-57: Stop conditions apply to every send path
Observable: Off, pause, invoice no longer unpaid, and the other refusals of this specification apply identically to a first attempt, a retry and a step delayed by a recipient being added later.
Source: implied: "a rule enforced in one path and not another"

### C-58: No retry after the window closes
Observable: No attempt is started for a step after its window (C-11) has closed; a step with no accepted recipient then takes the outcome C-38 gives it, with the reason "delivery error" where it is failed.
Source: choice: bounds late mail

### C-59: Evaluation log
Observable: Every evaluation made while reminders are on is recorded with start time, end time and counts of steps sent, skipped, failed, left pending and recorded as outcome unknown; an evaluation with nothing due is recorded with zeros. Records are kept at least 24 months.
Source: implied: U-15

### C-60: Finding problem steps
Observable: An operator can list reminder steps across all invoices filtered by step outcome (pending, sent, skipped, failed, outcome unknown), by recipient result (accepted, rejected, bounced, suppressed, error, outcome unknown) and by a range of step dates; each row shows invoice number, customer, step offset, outcome and reason.
Source: implied: U-8

### C-61: Who can see history and addresses
Observable: Reminder history, recipient addresses and the evaluation log are visible only to users who may view that invoice (or, for the evaluation log and settings log, who may manage reminders); anyone else gets no data and a message saying access is refused.
Source: implied: someone seeing what they may not see

### C-62: Send rate
Observable: Emails are handed to the delivery provider at no more than 10 per second by default (a decided value, unconfirmed against the provider); when the rate is exceeded or the provider says it is throttling or its quota is spent, the remaining sends are delayed, not dropped, and a quota answer counts as a temporary failure (C-37).
Source: choice: the provider's real limit is unknown

### C-63: A long evaluation continues, it does not drop invoices
Observable: If an evaluation cannot finish all due steps before it must stop (the platform's execution time limit; its figure is unconfirmed), the next evaluation continues with the steps not yet handled; no eligible step is left unhandled only because an evaluation ended early.
Source: implied: scheduled jobs on a platform have a maximum run time

### C-64: Sending domain must be verified before production use
Observable: In production, turning reminders on is refused, with a message naming the domain, when the sender address's domain is not one verified for sending with the delivery provider. The check is not applied outside production.
Source: implied: mail from an unverified domain is rejected or filed as spam, so reminders would silently not arrive

### C-65: Credentials are never shown
Observable: Delivery provider credentials do not appear in settings views, histories, logs or emails.
Source: implied: secrets

### C-66: Plain-text version
Observable: Each email has a plain-text version carrying all content listed in C-28.
Source: choice: readable in every mail client

### C-67: Results appear promptly
Observable: A send result recorded by the system appears in the invoice history and the evaluation log within 1 minute.
Source: choice

### C-68: Operator controls and what is left out
Observable: The operator's controls are exactly: turn reminders on/off, edit the settings listed in C-19, pause/resume reminders for one invoice, view history and the lists of C-60, C-59 and C-20. Deliberately not provided: sending a reminder on demand, pausing per customer, a per-customer or per-invoice schedule, a customer-facing unsubscribe link, combined emails, other channels (SMS, post), attachments, escalation to collections, late fees, a minimum balance below which no reminder is sent (any balance above 0.00 is reminded), and editing the message wording.
Source: choice: the request asks only for automatic reminders

### C-69: Replies do not drive the system
Observable: A customer's reply to a reminder does not change any invoice or stop reminders; replies go to the reply-to address, or to the sender address where there is none.
Source: implied: U-18

### C-70: Pause history
Observable: Every pause and resume is listed with who and when for the invoice, kept at least 24 months.
Source: implied: U-6

### C-71: Skipped and failed reasons
Observable: The reasons shown are exactly: for skipped — "window expired", "superseded", "before issue date", "invoice no longer unpaid"; for failed — "no recipient", "no deliverable recipient", "delivery error". Pending steps may carry "no recipient".
Source: implied: C-3, C-11, C-12, C-13, C-27, C-53, C-58

### C-72: Invoices cannot be read
Observable: If an evaluation cannot read the invoices, it sends nothing, records that it could not read them in the evaluation log, and the next evaluation tries again.
Source: implied: a thing it depends on failing

### C-73: Atomic recording of settings
Observable: A settings change and its log entry are saved together or not at all.
Source: implied: U-4

### C-74: Time-zone and send-time changes
Observable: Changing the business time zone or send time takes effect at the next evaluation; it never causes an offset already sent for an invoice to be sent again.
Source: implied: settings can change while sequences are under way

### C-75: Repeated addresses
Observable: An address listed more than once on an invoice (ignoring upper/lower case) is sent one email per step, not several.
Source: implied: C-32 (a recipient gets one email per step)

### C-76: Invalid listed addresses
Observable: A listed address that is not a syntactically valid email address is never sent to; its result in the history is "rejected" with the reason "invalid address". It counts toward the 5 of C-24.
Source: implied: a thing the request takes for granted (that addresses are usable) can be false

### C-77: Rejections that are not about the recipient
Observable: A rejection the delivery provider attributes to the sender (for example sender not authorised) or to the message is handled as a temporary failure under C-37 and suppresses no address.
Source: implied: C-53 must not turn a sender fault into dead recipients for every invoice

### C-78: Steps are never sent out of order
Observable: An offset smaller than the largest offset already sent for that invoice is never sent; if its date has come it is recorded as skipped with the reason "superseded".
Source: choice: adding an offset to the schedule must not send a "7 days overdue" email after a "14 days overdue" one

### C-79: Default holder of the permission
Observable: Until granted otherwise, only administrators of the account hold the permission to manage reminders; users with permission to view an invoice but not to manage reminders can see its reminder history and cannot change anything.
Source: choice: the permission mechanism of the invoicing system is not given

### C-80: Existing emails are unchanged
Observable: Invoice-delivery, receipt and other emails the invoicing system already sends are neither changed nor suppressed by reminders being on, off or failing.
Source: implied: what must not change

### C-81: One business's settings only
Observable: Where the system serves more than one business, each business has its own settings, evaluation log and settings log, and a reminder is sent only under the settings of the business that issued the invoice, to that invoice's recipients; nobody sees another business's reminders.
Source: implied: someone seeing what they may not see / the wrong sender identity on a customer's mail

### C-82: An unreachable delivery provider
Observable: When the delivery provider cannot be reached at all, no attempt is counted against C-37's limit of 3; the step stays pending and is tried again at later evaluations until its window closes (C-58).
Source: implied: U-17 (a thing it depends on failing for hours must not burn the retries)

### C-83: Permanent rejections are not retried
Observable: A recipient the delivery provider permanently rejects (for example no such mailbox) is not tried again for that step.
Source: implied: C-37 retries only temporary failures

### C-84: Reasons for there being no next step
Observable: Where an invoice has no next scheduled step its view says why, one of: "sequence finished", "invoice no longer unpaid", "no due date", "draft, not issued". While reminders are off or the invoice is paused the next step is still shown with the note "reminders off" or "reminders paused".
Source: implied: U-7

### C-85: Two operators editing settings at once
Observable: If the settings were changed by someone else after the operator opened them, the operator's save is refused with a message saying the settings changed and must be reloaded; nothing is overwritten.
Source: choice: no silent loss of another operator's change

### C-86: Content of other invoices never appears
Observable: A reminder email contains no figure, number, name or address belonging to any other invoice or any other customer.
Source: implied: someone seeing what they may not see
