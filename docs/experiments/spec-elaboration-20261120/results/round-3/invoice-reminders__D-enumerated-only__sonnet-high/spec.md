## Use cases

### U-1: An operator turns automatic reminders on for the first time, with invoices already in the system, to stop chasing late payers by hand
Flow: The operator (a signed-in user allowed to manage billing) opens the reminder settings, which show reminders as Off. The form is pre-filled with the default schedule (3 days before the due date, on the due date, and 3, 7 and 14 days after it), the default send time (09:00) and the business time zone. The operator fills in the reply-to address and the payment instructions if the form is missing them, sees a summary of how many unpaid invoices will be covered and when the first reminder will go out, and switches reminders On. Invoices that were already overdue before this moment are not sent a backlog of reminders; they receive only the steps that fall after the switch-on.
Source: request

### U-2: An operator changes how reminders behave (schedule, send time, time zone, sender details), including trying values that are not allowed
Flow: The operator edits the schedule offsets, the send time, the time zone, the reply-to address or the payment instructions and saves. A valid change is confirmed and applies to reminders not yet sent. An invalid change (for example 0 offsets, 11 offsets, an offset of 400, a repeated offset, a malformed reply-to address) is refused with a message that names the problem; the previous settings stay in force.
Source: implied: "automatic reminders" must be set up, and a set-up that cannot be configured or corrected cannot be maintained

### U-3: A customer receives a reminder before or on the due date and pays
Flow: The customer receives an email from the business before the due date (or on it) that names the invoice, the amount outstanding, the due date and how to pay. They pay (through the payment link, or by the payment instructions, after which the operator or the payment system records the payment). No further reminder arrives for that invoice.
Source: request

### U-4: A customer receives overdue reminders for an invoice they have partly paid
Flow: The customer has paid part of an invoice. The next reminder shows the amount still outstanding (not the original total), how many days overdue the invoice is, and how to pay the rest. The reminders carry on until the invoice is fully paid, or the last step of the schedule has been sent.
Source: implied: "unpaid invoices" includes invoices that are not wholly paid

### U-5: A customer opts out of reminders
Flow: The customer clicks the opt-out link in a reminder and sees a confirmation page that says automatic reminders from this business will no longer be sent to them. No more automatic reminders go to that customer, for any of their invoices. The invoice itself is unchanged and still owed.
Source: implied: automatic messages to people outside the business need a way for them to say stop

### U-6: A customer with several unpaid invoices receives one message, not one per invoice
Flow: When more than one of a customer's invoices has a reminder due for the same recipient in the same run, the recipient receives a single email that lists each of those invoices with its number, outstanding amount and due date.
Source: implied: automatic reminders for many invoices must not flood one inbox

### U-7: An operator pauses reminders for one invoice or one customer (for example during a dispute) and resumes them later
Flow: The operator opens an invoice (or a customer), chooses Pause reminders, and sees it marked Paused. No automatic reminder goes out while it is paused. The operator later chooses Resume; the invoice then receives only the steps whose time falls after the resume.
Source: implied: automatic chasing must be stoppable for an invoice that should not be chased

### U-8: An operator sends a reminder right now for one invoice
Flow: The operator opens an unpaid invoice and chooses Send reminder now. The reminder goes to the invoice's recipients immediately and appears in the invoice's reminder history marked as manual.
Source: implied: an operator whose schedule has already passed, or who has just fixed an address, needs to trigger a reminder by hand

### U-9: An operator sends themself a test reminder to check how it looks
Flow: The operator chooses Send test reminder in the settings. An email marked as a test, built from the current settings and sample data, arrives at the operator's own address only. Nothing is recorded against any invoice.
Source: implied: a message that customers will receive must be checkable before it goes live

### U-10: An operator finds out what reminders have been sent, what will be sent, and why an invoice is not being reminded
Flow: On an invoice the operator sees the next reminder (its date and time) or, when none is coming, the reason, and the history of every reminder (when, to whom, which step, outcome). In a reminders list the operator filters by outcome and by date range.
Source: implied: an automatic process the operator cannot observe cannot be trusted or debugged

### U-11: An operator deals with a reminder that did not arrive (failed, bounced, no recipient)
Flow: The operator sees the failed or bounced reminders in the attention list and on the invoice, with the reason. They correct the customer's email address (or clear a suppression), then use Send reminder now if they want to reach the customer immediately.
Source: implied: unhappy path of sending email

### U-12: An operator turns reminders off, and later back on
Flow: The operator switches reminders Off. No further automatic reminder is sent, including ones that were waiting to be sent. History stays visible. If the operator switches them On again later, reminders whose time passed while Off are not sent.
Source: implied: the operator's work includes stopping and going back to the way things were before

### U-13: The system sends reminders on schedule without anyone watching, including when it was down, ran twice, or the email provider failed
Flow: Without any user action, each reminder goes out at its scheduled send time (within the stated delay), each is sent once, and failures are retried or reported according to the rules below.
Source: request

### U-14: An invoice changes while its reminder sequence is under way (payment, partial payment, due date change, void, reopened after a refund)
Flow: Whatever happens to the invoice, the next reminder reflects its state at that time: a settled invoice gets nothing more, a changed due date moves the remaining steps, a changed outstanding amount appears in the next message.
Source: implied: invoices are live records and reminders run over days or weeks

### U-15: A customer opens the invoice link in a reminder, or a link that is wrong or old
Flow: The customer opens the link without logging in and sees that one invoice (its details and how to pay). A link that is altered or unknown shows a neutral "link not valid" page that shows no invoice or customer data.
Source: implied: the message must give the customer a way to see and pay the invoice

### U-16: A user who is not allowed to manage reminders tries to
Flow: A user without permission to manage billing opens the reminder settings and may see them (read-only) but every attempt to change a setting, pause, resume, send now, send a test, or clear an opt-out or suppression is refused with a message that they do not have permission, and nothing changes.
Source: implied: reminders send email in the business's name and need access control

## Clauses

### C-1: An invoice is a candidate for reminders only while its status is Open or Partially paid and its outstanding balance is greater than 0
Observable: An invoice with status Open or Partially paid and a balance above 0.00 shows a next reminder (or a stated reason it has none, per C-70); an invoice whose balance is 0.00 or less, in any status, shows "No reminder: nothing owed" and never receives one. "Overdue" is not a separate status: it means Open or Partially paid with a due date earlier than today in the business time zone.
Source: request

### C-2: No automatic reminder is sent for an invoice in any of these states: Draft (never issued), Paid, Void (cancelled) or Deleted; together with Uncollectible (C-88) these are all the invoice states that stop reminders
Observable: For an invoice in each of the four states, the invoice shows a no-reminder reason naming that state (a Deleted invoice is no longer listed) and no reminder email is sent for it. Open and Partially paid are the only states that do not stop reminders.
Source: implied: "unpaid invoices" excludes invoices that are settled, never issued or cancelled

### C-3: Apart from invoice status, reminders for an invoice are held back by exactly these conditions: reminders switched Off, the invoice paused, the customer paused, the customer opted out, the customer archived, and no deliverable recipient
Observable: For each of the six conditions, an otherwise eligible invoice receives no automatic reminder and shows the matching reason (C-70). No other setting or state holds back automatic reminders.
Source: implied: use cases U-5, U-7, U-11, U-12

### C-4: An invoice with no due date is treated as being due on its issue date for the purposes of reminders
Observable: An invoice with issue date 2026-03-10 and no due date has its steps computed from 2026-03-10 (so with the default schedule its "on the due date" reminder is at 09:00 on 2026-03-10 and its "+7" reminder on 2026-03-17), and the reminder message states 2026-03-10 as the due date.
Source: choice: the request assumes a due date; the loosest rule that still lets such invoices be reminded is to use the only date they have

### C-5: The default schedule has exactly five steps at offsets -3, 0, +3, +7 and +14 calendar days from the due date
Observable: With nothing customised, an invoice due 2026-06-20 gets reminders on 2026-06-17, 2026-06-20, 2026-06-23, 2026-06-27 and 2026-07-04 (each at the send time), and no others.
Source: choice: the request names no schedule; a pre-due nudge, a due-date notice and three widening overdue chasers is the loosest common pattern that serves the user

### C-6: A schedule is a list of 1 to 10 offsets, each a whole number of days from -60 to +365 inclusive, with no offset repeated
Observable: Saving a schedule of 1 offset, of 10 offsets, an offset of -60 and an offset of +365 succeeds; saving 0 offsets, 11 offsets, an offset of -61, +366, a fraction (2.5) or text, or a repeated offset (3, 3) is refused. A negative offset is before the due date, 0 is the due date and a positive offset is after it. The offsets may be entered in any order and are shown and applied in ascending order.
Source: choice: the request gives no bounds; these bounds keep the sequence finite and sane (at most 10 messages per invoice) while leaving room for any ordinary dunning plan

### C-7: A refused schedule or settings change leaves the previous settings in force and names the first problem
Observable: After a refused save the settings screen shows the error text identifying the offending field and value (e.g. "Offset 400 is above the maximum of 365"), and re-opening the settings shows the values from before the attempt.
Source: implied: U-2 unhappy path

### C-8: The send time is a time of day from 00:00 to 23:59 in the business time zone, default 09:00
Observable: With the default, a reminder step falling on 2026-06-20 is handed to the email provider no earlier than 09:00 on 2026-06-20 in the business time zone. Setting the send time to 14:30 moves unsent steps to 14:30. A value of 24:00 or 25:61 is refused.
Source: choice: the request does not say when in the day to send; a business-hours default that the operator can change is the loosest rule that serves the user

### C-9: The business time zone is any valid IANA time-zone name; it defaults to the account's own time zone, or UTC where the account has none
Observable: Setting "America/New_York" makes every date and time rule in this specification (step dates, send time, "today", "calendar day") use New York local time; an unknown name (e.g. "Mars/Base") is refused. A due date is a calendar date and is not shifted by the time zone.
Source: choice: dates need one reference time zone; the business's own is the one the operator reasons in

### C-10: A step's scheduled moment is the send time on the calendar date obtained by adding its offset in calendar days to the due date, in the business time zone
Observable: Due date 2026-06-20, offset +3, send time 09:00, zone America/New_York: the moment is 2026-06-23 09:00 New York time. Offsets count calendar days, not 24-hour blocks, so a step is never shifted by a daylight-saving change, and a due date of 2028-02-29 with offset +1 is 2028-03-01.
Source: implied: "reminders" at offsets from a due date

### C-11: Under normal operation a step's reminder is handed to the email provider within 60 minutes after its scheduled moment, never before it
Observable: For a step with moment 09:00, the history timestamp for the send is between 09:00:00 and 10:00:00 the same day when the system, the provider and its quota are healthy.
Source: choice: the request says "automatic"; a bounded delay is the loosest figure a user can rely on. The 60-minute figure is decided, not given

### C-12: When the send time does not exist on a date because the clock skips it (daylight-saving spring-forward), the step's moment is the first instant after the gap on that date
Observable: With zone America/New_York and send time 02:30, a step on 2027-03-14 is handed over at or after 03:00 on 2027-03-14 (and within 60 minutes of it), exactly once.
Source: implied: Pass 4, time-zone rules of the platform

### C-13: When the send time occurs twice on a date because the clock repeats it (daylight-saving fall-back), the step's moment is the first occurrence
Observable: With zone America/New_York and send time 01:30, a step on 2026-11-01 is sent at the first 01:30 and no second message is sent at the repeated 01:30.
Source: implied: Pass 4, time-zone rules of the platform

### C-14: A step is sent only if its scheduled moment is not earlier than the "start of eligibility"; a step whose moment is earlier is skipped, with outcome Skipped and reason "before eligibility"
Observable: The start of eligibility of an invoice is the latest of these events: reminders were switched On; the invoice entered Open or Partially paid from any other state (including being issued or reopened); the invoice was resumed after being paused; its customer was resumed after being paused; the operator cleared the customer's opt-out; its customer was unarchived; its due date was changed (or first set). For a single recipient address the start of eligibility is also no earlier than the moment that address was added to the invoice or its customer. Example: an invoice due 2026-06-10 with default steps dated 06-07, 06-10, 06-13, 06-17 and 06-24, when reminders are switched On at 2026-06-20 10:00, has its first four steps shown as Skipped "before eligibility" and receives the 06-24 step. The list of events is complete: other changes (a partial payment, a changed amount, a changed schedule) do not move the start of eligibility.
Source: implied: U-1, U-7, U-12 (carry on with data that already exists; no backlog flood)

### C-15: When a run finds several unsent steps of one invoice whose moments have all passed and are not earlier than the start of eligibility, it sends only the one with the latest moment and records each earlier one as Skipped with reason "superseded"
Observable: After the system was down from 2026-06-19 to 2026-06-24, an invoice due 2026-06-20 (step 06-17 sent earlier, steps 06-20 and 06-23 unsent) receives one reminder on recovery, worded for the +3 step; the 06-20 step shows Skipped "superseded".
Source: implied: U-13, recovering after a stop without flooding customers

### C-16: Each step is identified by its invoice, its offset and its recipient address, and once it has a final outcome it is never attempted again
Observable: The final outcomes are Sent, Failed, Bounced, Skipped and Cancelled (C-68). After any of them, no later run, restart, retry or schedule edit produces a second message for that invoice, offset and recipient; the recipient's mailbox shows one message for it.
Source: implied: "reminders" sent "automatically" must not repeat; Pass 3, duplication

### C-17: When the operator saves a changed schedule, offsets that already have a final outcome for an invoice are not sent again, offsets not yet finalised follow the new list, and an offset added by the change whose moment has already passed is skipped with reason "before eligibility"
Observable: An invoice has had its -3 and 0 steps sent. The operator changes the schedule from (-3, 0, 3, 7, 14) to (-3, 0, 5, 10) the day after the due date: neither -3 nor 0 is sent again, the +5 and +10 steps are sent on their dates, and +3 / +7 / +14 are no longer sent. If the operator instead adds +1 on the day after the due date at 12:00, the +1 step (09:00 that day) shows Skipped "before eligibility".
Source: implied: Pass 3, editing the schedule while sequences are in flight

### C-18: When an invoice's due date changes, its steps already finalised are not repeated and its remaining steps are recalculated from the new due date
Observable: Invoice due 2026-06-20 has had its -3 step sent on 06-17; the due date is moved to 2026-07-20 on 06-18. On 06-20 no reminder is sent; on 07-20 the 0 step is sent; the -3 step is not sent again; steps with moments before the change are Skipped "before eligibility" (C-14).
Source: implied: U-14

### C-19: When the business time zone or send time is changed, steps not yet finalised use the new values from then on
Observable: Changing the send time from 09:00 to 14:30 at 08:00 makes a step dated today go out at 14:30, not at 09:00. Steps already finalised are unaffected.
Source: implied: U-2, Pass 3

### C-20: After the last step of the schedule has been finalised, no further automatic reminder is sent for that invoice, however long it remains unpaid
Observable: With the default schedule, the +14 reminder is the last; the invoice then shows "No reminder: all steps completed" and, 60 days later, still no new reminder has arrived.
Source: implied: a schedule is a finite list of steps (C-6)

### C-21: An automatic step for a recipient is skipped, with reason "already reminded today", when a reminder of any kind (automatic or manual) about the same invoice went to that recipient earlier on the same calendar day in the business time zone
Observable: The operator uses Send reminder now at 08:00; the step due at 09:00 the same day shows Skipped "already reminded today" and the recipient gets one message that day about that invoice.
Source: implied: Pass 3, manual and automatic paths meeting

### C-22: Reminders are sent on any day of the week, including Saturdays, Sundays and public holidays
Observable: A step whose date is a Sunday is sent on that Sunday at the send time.
Source: choice: the request does not mention working days; no skipping rule is the loosest rule that does not silently delay a reminder

### C-23: Immediately before a reminder is handed to the email provider, the system re-reads the invoice and its customer, and sends only if the invoice is still a candidate (C-1, C-2, C-88, C-3), the step is still scheduled for that moment, and the recipient is still deliverable and not opted out; the message shows the values read at that moment
Observable: An invoice paid at 09:04 whose reminder was due at 09:00 and is handed over at 09:05 produces no email; its step shows Cancelled with reason "invoice settled". The same holds for a pause, an opt-out, an Off switch, a due-date change that moves the step, and a suppressed address made between selection and send. An outstanding amount that changed from 600.00 to 450.00 in that interval is shown as 450.00.
Source: implied: Pass 3, a payment or change arriving while a reminder is waiting

### C-24: Every Skipped and Cancelled step shows its reason on the invoice's history
Observable: The reason is one of: "before eligibility", "superseded", "already reminded today", "invoice settled", "invoice paused", "customer paused", "customer opted out", "customer archived", "reminders off", "no recipient", "address suppressed", "invoice status: <status>" (Draft, Paid, Void or Uncollectible), "due date changed", "over recipient limit". The list is complete.
Source: implied: U-10

### C-25: A partial payment does not stop reminders; the next reminder shows the balance still outstanding
Observable: An invoice of USD 1,000.00 with USD 400.00 paid gets its next step with an outstanding amount of USD 600.00 and also states the original total USD 1,000.00.
Source: implied: U-4

### C-26: Once an invoice's balance reaches 0.00 or it enters Paid, no further reminder is created for it
Observable: After payment, the invoice shows "No reminder: paid" (or "nothing owed") and its unsent steps never send.
Source: request

### C-27: An invoice that returns to Open or Partially paid (for example after a refund or a reversed payment) is a candidate again, receives only steps not yet finalised whose moments are after the return, and never repeats a finalised step
Observable: An invoice paid after its 0 step and later reopened receives the next not-yet-finalised step whose moment is after the reopening; its already sent 0 step is not repeated.
Source: implied: Pass 3, payment undone

### C-28: The recipients of a reminder are the billing email addresses currently recorded for the invoice (the invoice's own list where it has one, otherwise its customer's billing addresses), read at send time, up to 5 addresses
Observable: A customer whose billing email was changed from a@x.com to b@x.com yesterday gets today's reminder at b@x.com only.
Source: implied: Pass 2, "reminders" need an addressee

### C-29: If more than 5 billing addresses apply, the first 5 in the order the operator entered them receive the reminder and each extra address shows Skipped "over recipient limit"
Observable: With 7 addresses, 5 messages are sent and 2 history rows show "over recipient limit".
Source: choice: the request is silent; a cap bounds how many third parties one invoice can mail

### C-30: Each recipient gets a separate message; no recipient can see the other recipients' addresses
Observable: Two billing contacts each receive a message addressed only to themselves, with no other address in To, Cc or Bcc.
Source: choice: protects the privacy of each contact

### C-31: When an invoice has no deliverable recipient address at its step's moment, the step is Skipped with reason "no recipient" and appears in the attention list (C-77)
Observable: A deliverable address has exactly one "@", non-empty text before it, a domain after it that contains a dot, no spaces, and is not Suppressed. An invoice whose customer has no email, or only addresses failing that test, shows Skipped "no recipient" for that step and appears in the attention list.
Source: implied: Pass 2, the addressee exists

### C-32: A hard bounce, or a permanent rejection of an address by the email provider, marks that address Suppressed; a Suppressed address receives no further reminder
Observable: After the provider reports "mailbox does not exist" for a@x.com, the history row shows Bounced (on every invoice row that was in the same message), a@x.com shows Suppressed on the customer, and the next step for that customer skips a@x.com with "address suppressed" while still sending to other addresses. A soft bounce (mailbox full, temporary) does not suppress the address.
Source: implied: U-11; protects the sender's reputation

### C-33: An operator can clear a Suppressed mark on an address, and an address that is edited to a different value is not Suppressed
Observable: After clearing (or correcting a@x.com to b@x.com), the next step is sent to the address.
Source: implied: U-11

### C-34: When a customer uses the opt-out link, automatic reminders stop for every invoice of that customer from that moment, including reminders already waiting to be sent
Observable: After the opt-out is confirmed, a reminder that was waiting shows Cancelled "customer opted out", and all of the customer's invoices show "No reminder: customer opted out".
Source: implied: U-5

### C-35: The opt-out link works without logging in, applies to that customer only, shows a confirmation, and clicking it again shows the same confirmation without error
Observable: The page says automatic reminders from the business will no longer be sent to this customer; a second click shows the same page; a link with a changed character shows the neutral "link not valid" page (C-50).
Source: implied: U-5

### C-36: An opt-out affects automatic reminders only: it does not change any invoice and does not stop the operator from seeing the invoice as owed
Observable: After opt-out the invoice is still Open, still counted as outstanding in the business's own reports, and unchanged.
Source: implied: U-5

### C-37: An operator can clear a customer's opt-out; the clearing is recorded and begins a new start of eligibility (C-14)
Observable: After clearing, the customer shows reminders as active and receives only steps whose moments are after the clearing.
Source: implied: Pass 3, undo of opt-out

### C-38: Every reminder email contains these parts: the business name as sender, the invoice number, the outstanding balance with its currency, the due date, a timing statement, a way to pay, a link to the invoice, the business's reply-to contact, and an opt-out link
Observable: A reminder for invoice INV-1042, USD 600.00 outstanding, due 2026-06-20, shows each of the nine parts. When the invoice is partially paid, the original total is also shown. No part is omitted for any step.
Source: implied: Pass 2, a reminder must say what is owed, by when, and how to settle it

### C-39: The timing statement states one of three things, computed in the business time zone at the moment of sending: "due in N days" (N from 1 up), "due today", or "N days overdue" (N from 1 up)
Observable: For an invoice due 2026-06-20: sent 2026-06-17 states 3 days until due; sent 2026-06-20 states due today; sent 2026-06-23 states 3 days overdue; sent 2026-06-24 after a one-day delay states 4 days overdue.
Source: implied: Pass 2, the customer must know the urgency

### C-40: The way to pay is the invoice's payment link where the system has one for the invoice, otherwise the business's payment instructions text (up to 1,000 characters)
Observable: An invoice with a payment link shows the link; an invoice without one shows the instructions text exactly as the operator saved it. Saving instructions of 1,000 characters succeeds and of 1,001 is refused.
Source: implied: Pass 2, "unpaid" is resolved by paying

### C-41: Amounts are shown in the invoice's own currency using that currency's standard number of decimal places
Observable: An outstanding amount of 1250 USD is shown with two decimals (1,250.00) and the code USD; 1250 JPY is shown with no decimals and the code JPY.
Source: implied: Pass 2, an amount without a currency is ambiguous

### C-42: The subject line of a single-invoice reminder contains the invoice number and the business name
Observable: The subject includes "INV-1042" and the business name.
Source: choice: customers find the right invoice in their inbox; the rest of the wording is open

### C-43: Reminders are written in English
Observable: Every label and sentence in the reminder is English regardless of the customer's country.
Source: choice: the request names no languages; one language is the loosest scope

### C-44: Reminders are sent from an address on the business's verified sending domain, with the business name as sender name and the business's reply-to address as Reply-To
Observable: In the recipient's mail client the sender shows the business name and replying addresses the reply-to value.
Source: implied: U-3; Pass 4 (mail providers require authenticated senders)

### C-45: Reminders carry no attachments
Observable: The message has no attached file; the invoice is reached only through the link.
Source: choice: avoids mail size limits and spam filtering of attachments

### C-46: When one run sends a recipient reminders for more than one invoice, the recipient receives one combined message listing every such invoice with its number, outstanding balance with currency, due date and timing statement, together with the way to pay for each, the business contact and the opt-out link
Observable: A recipient with invoices INV-1 and INV-2 both due a reminder at 09:00 and picked up by the same run receives one email listing both. A second recipient on only INV-1 receives an email about INV-1 alone. Each invoice's step shows Sent with the same message time. Steps picked up by different runs are not combined.
Source: implied: U-6

### C-47: A combined message lists at most 20 invoices; further due invoices for that recipient are sent in additional messages in the same run, each also listing up to 20
Observable: 45 due invoices for one recipient produce 3 messages (20, 20, 5).
Source: choice: bounds message length; 20 is decided

### C-48: A combined message shows no total across invoices
Observable: A recipient with an invoice in USD and one in EUR sees each amount on its own line and no summed figure.
Source: choice: invoices may be in different currencies, so a sum can be wrong

### C-49: The subject of a combined message contains the business name and the number of invoices listed
Observable: A 3-invoice message subject includes the business name and "3".
Source: choice: wording otherwise open

### C-50: The invoice link in a reminder opens that one invoice without logging in, and cannot be altered or guessed to open any other invoice or customer
Observable: Opening the link shows the invoice number, items, amount outstanding and the way to pay. Changing, removing or adding any character to the link shows the neutral "link not valid" page, with no invoice or customer data on it.
Source: implied: Pass 2, a customer has no account; Pass 5, never expose another customer's data

### C-51: A reminder's invoice link stays valid for at least 90 days after the message is sent
Observable: A link from a message sent 89 days ago opens the invoice; the invoice page shows the invoice's present state.
Source: choice: customers may act on an old message; 90 is decided

### C-52: The invoice page opened from a link for a Paid or Void invoice shows its status and offers no way to pay
Observable: Opening the link after payment shows "Paid" and no payment button or instructions.
Source: implied: Pass 3, the link arriving after the invoice changed

### C-53: Every reminder carries a one-click unsubscribe indication in its message headers (List-Unsubscribe and List-Unsubscribe-Post) pointing at the customer's opt-out
Observable: Mail clients that support it show an "Unsubscribe" control, and using it has the effect of C-34. Whether this is mandatory for this volume of mail is unconfirmed; the behaviour is provided regardless.
Source: implied: Pass 4, large mailbox providers require one-click unsubscribe from bulk senders (thresholds unconfirmed)

### C-54: Only users with permission to manage billing can change reminder settings, pause, resume, send now, send a test, clear an opt-out or clear a suppression; every other signed-in user of the business can view
Observable: A user without the permission sees the settings read-only; each change attempt shows "You do not have permission" and changes nothing. A signed-out visitor sees the sign-in page.
Source: implied: U-16

### C-55: An operator controls exactly these things: reminders On/Off, the schedule (C-6), the send time (C-8), the business time zone, the reply-to address, the payment instructions text, pause and resume per invoice, pause and resume per customer, send reminder now per invoice, send test reminder, clear opt-out, and clear suppression
Observable: The settings and invoice screens offer these and no others. Nothing else (such as per-invoice schedules or weekend rules) is configurable.
Source: choice: bounds the operator's controls to what the request needs

### C-56: Reminders cannot be switched On unless all of these are present: a valid schedule, a valid reply-to email address (shaped as in C-31), non-empty payment instructions, and a verified sending domain (C-90)
Observable: Switching On with any missing shows a message listing each missing item and leaves reminders Off.
Source: implied: Pass 2 and Pass 4: the message needs these to be correct and deliverable

### C-57: Before switching On, the operator sees how many invoices are candidates and the date and time of the first reminder that would be sent
Observable: The summary reads, for example, "37 unpaid invoices are covered; the first reminder will go out 2026-06-21 09:00." If none is scheduled it says "No reminders are scheduled yet."
Source: implied: U-1, carry on with existing data

### C-58: Switching Off takes effect for every reminder not yet handed to the email provider, including those waiting to be retried, which show Cancelled "reminders off"
Observable: After switching Off, no email goes out from that moment; a message already handed to the provider before the switch is not recalled. Steps whose moments fall while Off are not sent.
Source: implied: U-12

### C-59: Switching Off and On again keeps all history and settings, and reminders whose moments passed while Off are Skipped "before eligibility" (C-14)
Observable: After Off for 5 days and On again, no backlog is sent, the skipped steps show in the history, and the history from before is still visible.
Source: implied: U-12

### C-60: Pausing an invoice stops automatic reminders for that invoice only; pausing a customer stops them for every invoice of that customer
Observable: Paused invoice shows "No reminder: invoice paused"; customer paused shows "No reminder: customer paused" on every one of the customer's invoices. Other invoices are unaffected.
Source: implied: U-7

### C-61: Resuming starts a new start of eligibility (C-14) and does not repeat finalised steps
Observable: After resume, steps whose moments passed while paused are Skipped "before eligibility"; the next future step is sent.
Source: implied: U-7

### C-62: Send reminder now sends one reminder for the chosen invoice to its current recipients immediately, records it as manual, and does not use up or finalise any scheduled step; it has the parts of C-38 and the timing statement of C-39
Observable: The history shows a row of type Manual and the scheduled steps are unchanged; the message shows the balance at that moment.
Source: implied: U-8

### C-63: Send reminder now is refused, with a message naming the reason, when the invoice is not Open or Partially paid with a balance above 0, when the customer opted out, or when no deliverable recipient exists
Observable: Each refusal shows the reason ("Invoice is Paid", "Customer has opted out", "No deliverable recipient") and no email is sent. Suppressed addresses are skipped.
Source: implied: Pass 5, a rule enforced on the automatic path must be enforced on the manual one (settled invoice, opt-out, no recipient)

### C-64: Send test reminder delivers one email, marked as a test in the subject and body, only to the signed-in operator's own email address, and records nothing against any invoice
Observable: The email arrives at the operator's address with a test marker and shows the current settings; no invoice history row appears.
Source: implied: U-9

### C-65: A user may send at most 20 test reminders per hour; the 21st in an hour is refused with a message saying to try later
Observable: The 21st test within 60 minutes shows the refusal; an hour later it works again.
Source: choice: prevents using the test as a mail cannon; 20 is decided

### C-66: Every change to reminder settings, pause, resume, opt-out clearing and suppression clearing is recorded with who made it, what changed (old and new value) and when
Observable: A change-history list shows these entries in time order.
Source: implied: Pass 5, accountability for an automatic process

### C-67: Each invoice shows, for every reminder attempt, these fields: time, step offset (or Manual), recipient address, outcome, and reason (for Skipped, Cancelled, Failed, Bounced)
Observable: A history row reads, for example, "2026-06-23 09:02, +3, a@x.com, Sent".
Source: implied: U-10

### C-68: The outcomes a reminder step can show are exactly: Scheduled, Sending, Sent, Failed, Bounced, Skipped and Cancelled
Observable: Scheduled is shown for a step not yet due; Sending while it is being handed over or retried; Sent when the provider accepted it; Failed when it was refused or not accepted after the retries; Bounced when the provider reported a permanent non-delivery; Skipped and Cancelled with a reason (C-24).
Source: implied: U-10

### C-69: "Sent" means the email provider accepted the message; it is not a promise of delivery or of being read
Observable: A row shows Sent even though the recipient's mailbox may later bounce, in which case the row changes to Bounced.
Source: implied: Pass 4, what an email system can know

### C-70: Each invoice shows its next reminder (date and time and offset) or, where there is none, exactly one reason chosen from: nothing owed, invoice status (naming it), reminders off, invoice paused, customer paused, customer opted out, customer archived, no deliverable recipient, all steps completed
Observable: An invoice with the next step 2026-06-23 09:00 shows "Next reminder: 2026-06-23 09:00 (+3 days)"; a Paid invoice shows "No reminder: paid".
Source: implied: U-10

### C-71: The reminders list can be filtered by outcome (any of the seven in C-68) and by a date range, and shows the number of rows matching
Observable: Choosing outcome Failed and 2026-06-01 to 2026-06-30 lists only failed reminder rows in that period with a count.
Source: implied: U-10

### C-72: Reminder history and the settings change history (C-66) are kept for at least 24 months
Observable: A reminder sent 23 months ago is still visible in its invoice's history, and a settings change made 23 months ago is still in the change list.
Source: choice: the request is silent on retention; 24 months is decided and the legal minimum for this business is unconfirmed

### C-73: When the email provider refuses a message with a temporary error before accepting it, the system retries up to 3 times, at 15 minutes, 1 hour and 4 hours after the previous attempt, and each retry repeats the checks of C-23
Observable: With attempts at 09:00, 09:15, 10:15 and 14:15, an outage lasting 30 minutes from 09:00 results in the message being accepted at the 10:15 attempt and one Sent row in the history. If the 14:15 attempt also fails the row shows Failed with the provider's reason.
Source: implied: U-13, a thing it depends on failing; the intervals are decided

### C-74: When the email provider refuses a message permanently (for example an invalid address), the step is Bounced, not retried, and the address is Suppressed (C-32)
Observable: One attempt only in the history; the row shows Bounced.
Source: implied: U-11

### C-75: When the result of handing a message to the provider is unknown (a timeout or a lost connection after the request was sent), the step shows Failed with reason "outcome unknown" and is not retried automatically
Observable: One history row Failed "outcome unknown"; no second email can arrive from the system for that step; the operator may use Send reminder now.
Source: choice: a missed reminder can be recovered by hand, a duplicated one cannot be unsent

### C-76: The system hands messages to the provider no faster than 10 per second, and when the provider limits it by rate or by a daily quota, the remaining steps are deferred to the next run and sent oldest moment first
Observable: 5,000 messages due at 09:00 take at least 500 seconds to hand over; if the provider's daily quota ends, the unsent steps show Scheduled, and go out in the next run after the quota resets, oldest first, never dropped and never duplicated; where the invoice's next step has come due by then, C-15 applies. The provider's actual limits are unconfirmed; 10 per second is decided.
Source: implied: Pass 4, platform limits

### C-77: The operator can see a list of reminders needing attention, containing every step with outcome Failed or Bounced and every Skipped "no recipient", with a count of them shown on the reminder settings screen
Observable: Three failed steps and one "no recipient" step show "4 need attention" and appear in the list with their invoices; fixing the address and sending now does not remove old rows.
Source: implied: U-11

### C-78: A failure on one invoice or recipient does not stop the other reminders of the same run
Observable: When one address bounces among 100 reminders in a run, the other 99 are sent.
Source: implied: Pass 3, partial completion

### C-79: The system checks for due reminders at least every 30 minutes
Observable: At any time of day, the interval between two runs does not exceed 30 minutes; with C-11's 60-minute allowance this lets a step's message go out in the hour after its moment.
Source: choice: the figure is decided so C-11 can be met

### C-80: When two runs overlap, or one run is repeated, a step results in at most one message per recipient
Observable: Running two copies simultaneously at 09:00 still produces exactly one email for each step and recipient.
Source: implied: Pass 3, two at once; the platform may run scheduled work more than once

### C-81: A run that is stopped partway (restart, time limit of the platform, crash) leaves no step half done: steps not yet handed over remain Scheduled and are sent by the next run, and steps handed over are Sent
Observable: After a restart mid-run, the totals across both runs are one message per step and recipient. The execution time limit of the platform is unconfirmed; no behaviour depends on a run finishing.
Source: implied: Pass 4, runtime's own rules

### C-82: When up to 10,000 reminders become due at the same send time, all are handed to the provider within 6 hours, subject to the provider's quota
Observable: With 10,000 due at 09:00, the last is handed over before 15:00 the same day when the provider's quota allows. Above 10,000 the time is not promised.
Source: choice: the request implies no volume limit; the figure is decided

### C-83: Outside the production environment, no reminder is delivered to any address that is not on a configured allowlist
Observable: In development or testing, a reminder for a customer a@x.com is not delivered to a@x.com; it is captured or rerouted to an allowlisted address.
Source: implied: Pass 4, what it demands before it could ship beyond a development environment; Pass 5, never mail real customers from a test setup

### C-84: Reminders, history, settings, opt-outs and links of one business are never visible to or sent on behalf of another business
Observable: A user of business A sees no invoice, history row or setting of business B; a reminder for A's invoice never shows B's name, reply-to or payment instructions.
Source: implied: Pass 5

### C-85: Sending a reminder does not change any invoice's status, amount, due date or recipients
Observable: Comparing an invoice before and after reminders show the same status, amount and due date; only reminder history differs.
Source: implied: Pass 5, data must not be altered on the way

### C-86: When a customer is erased at the customer's request, that customer's email addresses are removed from the reminder history within 30 days and the rows remain with the address replaced by "removed"
Observable: After erasure, history rows for those invoices show "removed" in place of the address and no further reminder is sent.
Source: choice: personal data rule, the exact legal deadline is unconfirmed; 30 days is decided

### C-87: Reminders can be rolled back to the behaviour before the feature existed by switching Off, which leaves every invoice and customer record as it was
Observable: With reminders Off, no reminder email is sent by the system and the invoice pages work as before, apart from showing "No reminder: reminders off".
Source: implied: operator work, go back to the version before

### C-88: No automatic reminder is sent for an invoice that has been marked Uncollectible (written off)
Observable: An Uncollectible invoice shows "No reminder: invoice status Uncollectible" and no reminder email is sent for it.
Source: choice: chasing a debt the business has itself written off confuses and annoys the customer and the request is silent

### C-89: Reminders are sent by email only
Observable: No text message, phone call, letter or in-app notice is produced by this feature.
Source: choice: the request does not name a channel; email is the one every invoice customer has

### C-90: A sending domain counts as verified only when the email provider confirms that SPF and DKIM are set up for the domain reminders are sent from; the operator sees the domain's status as Verified or Not verified
Observable: With the domain Not verified the settings show "Not verified" and reminders cannot be switched On (C-56); once the provider confirms SPF and DKIM the status shows Verified. A DMARC policy on the domain is recommended and its presence is not required. The mail providers' exact requirements are unconfirmed.
Source: implied: Pass 4, mail providers reject or spam-box unauthenticated bulk mail

### C-91: The due date in a reminder is written so that the month cannot be misread (the month spelled out, or the form 2026-06-20)
Observable: A due date of 3 April 2026 never appears as 03/04/2026.
Source: choice: customers are in different countries; only the unambiguity is fixed, not the layout

### C-92: Times and dates the operator sees for reminders (next reminder, history, summary) are in the business time zone and labelled with the zone's name or offset
Observable: A history time reads, for example, "2026-06-23 09:02 America/New_York".
Source: choice: one reference zone avoids confusion; the label's form is open

### C-93: Every reminder says that it may be disregarded if the invoice has already been paid
Observable: The message contains a sentence to that effect; a customer who paid minutes before the reminder was sent sees it.
Source: choice: payment can arrive while the message is in transit and the re-check of C-23 cannot close that window

### C-94: When more than one no-reminder reason applies to an invoice, the one shown is the first in this order: invoice status (C-2, C-88), nothing owed, customer archived, customer opted out, customer paused, invoice paused, reminders off, no deliverable recipient, all steps completed
Observable: A Paid invoice whose customer has also opted out shows "No reminder: paid"; an Open invoice that is paused and whose customer has opted out shows "No reminder: customer opted out".
Source: choice: the request is silent on which reason to show; any one fixed order serves the operator, so this one is decided

### C-95: Send reminder now is allowed while reminders are Off and while the invoice or its customer is paused
Observable: With reminders Off, or on a paused invoice, Send reminder now delivers the reminder to the invoice's recipients and records a Manual row; a paused or Off state does not appear as a refusal reason.
Source: choice: Off and pause are the operator's own switches, and a deliberate manual action by the same operator overrides them; an opt-out is the customer's wish and is not overridden (C-63)
