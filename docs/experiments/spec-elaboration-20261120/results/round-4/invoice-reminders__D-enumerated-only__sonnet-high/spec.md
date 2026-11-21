## Use cases

### U-1: An account Owner turns on automatic reminders for the first time, to get overdue money chased without doing it by hand
Flow: The Owner opens the account's reminder settings and sees reminders Off, the default schedule (3 days before the due date, on the due date, then 7, 14 and 30 days after it), the send time 09:00 and the account time zone. If a required setting is missing the page lists each one. The Owner fills them in and turns reminders On. The settings page then shows On, and each open invoice shows the date of its next reminder.
Source: request ("Set up automatic reminders")

### U-2: An Owner or Admin changes when reminders go out, to fit how their customers pay
Flow: The user edits the schedule (adds, removes or changes steps), the send time or the time zone, and saves. A schedule that breaks a limit is refused with the reason and the saved schedule is unchanged. A valid one is saved and every open invoice's next-reminder date updates.
Source: implied: "Set up" means the timing is configurable

### U-3: An Owner or Admin sends themselves a test reminder, to see what customers will receive before turning reminders on
Flow: The user chooses "send test reminder". They receive one email at their own login address showing a sample reminder clearly marked as a test. No customer is emailed and no invoice history changes.
Source: implied: a user cannot trust an automatic customer-facing email they have never seen

### U-4: A customer (invoice recipient) receives reminders before and after the due date and pays
Flow: The customer gets an email per schedule step stating the business, invoice number, outstanding balance, due date, how many days remain or overdue, how to pay, and how to contact the business. They pay by the means given. No further reminder arrives once the invoice is settled.
Source: request ("reminders for unpaid invoices")

### U-5: An invoice becomes settled while reminders are scheduled or being sent, so the customer is not chased for money already paid
Flow: A payment, credit note, void or write-off is recorded. No later step is sent. If it is recorded in the moments between a step becoming due and the message leaving, that message is not sent either and the history shows it skipped because the invoice was settled.
Source: implied: "unpaid" in the request

### U-6: A customer stops reminders for one invoice, to stop being emailed about it
Flow: The customer follows the "stop reminders for this invoice" link in a reminder, without logging in. They see a confirmation. No further automatic or manual reminders go out for that invoice, and the business sees the invoice marked "stopped by recipient".
Source: implied: customers who cannot stop unwanted email mark it as spam, which harms the business's sending reputation

### U-7: An Owner or Admin pauses and resumes reminders on a single invoice, e.g. while a dispute is settled
Flow: On the invoice the user chooses Pause. The invoice shows Paused and receives nothing. Later they choose Resume. The invoice shows its next scheduled reminder date and no reminder missed during the pause is sent late.
Source: implied: a business needs to hold back reminders for one customer without turning off the feature

### U-8: An Owner or Admin sends a reminder to one customer immediately, to chase now rather than at the next step
Flow: On an unsettled invoice the user chooses "send reminder now". The reminder goes out at once to the invoice's billing addresses and appears in the history as manual. If a reminder went out in the last 24 hours the user is refused and told when sending becomes possible.
Source: implied: automatic schedule alone cannot serve a customer the owner wants to chase today

### U-9: An Admin reviews what was sent and fixes delivery problems
Flow: On an invoice the Admin sees every reminder with its status and per-address outcome. On the account page they see a list of invoices whose reminders failed, bounced, had no recipient address, had an unknown outcome or were held back by a suppressed address. They correct the invoice's address or clear the suppression, and later reminders go to the corrected address.
Source: implied: an automatic sender nobody can observe is not trustworthy

### U-10: An Owner turns reminders off and later back on
Flow: The Owner turns reminders Off; within an hour nothing more goes to customers; history is kept. Later they turn them On; reminders resume only for steps dated after that day.
Source: implied: every automatic feature needs a stop

### U-11: The operator stops all reminder sending, and recovers after the reminder job was down
Flow: The operator flips a system-wide switch, and no reminder email leaves for any account. After switching it back on, or after the job was down for any reason, it sends only what is still timely and does not flood customers with a backlog or send any reminder twice.
Source: implied: operator's work (stop, recover, go back)

### U-12: An invoice changes while reminders are in flight (due date moved, partial payment, address edited, becomes open again)
Flow: The user or customer causes the change. The next reminder reflects it: the current outstanding balance, the current billing addresses, and dates computed from the current due date. Reminders already sent are neither recalled nor repeated for the same dates.
Source: implied: invoices are edited and paid in part during their life

### U-13: A view-only member looks at reminder history but cannot change anything
Flow: A Member of the account opens the reminder settings and an invoice's history and sees them, but every control that changes reminders is absent or refused. Someone outside the account sees nothing.
Source: implied: who may see and who may change

### U-14: An account with existing unpaid and overdue invoices turns reminders on
Flow: The Owner turns reminders On while some invoices are already past due. Nothing goes out to customers on the day for steps dated that day or earlier; overdue invoices receive their next step that is dated after the day of enabling.
Source: implied: "carry on with data that already exists"; a surprise burst to every overdue customer is harmful

### U-15: An Owner tries to turn reminders on or save a schedule that cannot work
Flow: The Owner attempts it with a missing prerequisite, an empty schedule, a duplicate step, an out-of-range offset or too many steps. The save is refused, the message names every problem found, and what was saved before is unchanged.
Source: implied: unhappy paths of U-1 and U-2

## Clauses

### C-1: Reminders are off for an account until an Owner or Admin turns them on
Observable: An account that has never turned reminders on, including every account that existed before this feature, shows Off and no customer receives any reminder email from it.
Source: choice: sending email to a business's customers without that business's consent is harmful, so the default is off

### C-2: Turning reminders on is refused while any prerequisite is missing, and the refusal lists every missing one
Observable: Attempting to turn on while any of these is missing is refused and the message names all missing ones: sender business name; reply-to email address; time zone; at least one schedule step; account payment instructions text. The account stays Off.
Source: choice: a reminder without a sender, a place for replies, a way to pay, or a schedule cannot do its job

### C-3: A new account's schedule is pre-filled with five steps
Observable: A new account's schedule shows five steps at -3, 0, +7, +14 and +30 days relative to the due date.
Source: choice: the request gives no schedule and customers expect a notice before, on and after the date

### C-4: A schedule step is a whole-number day offset from the invoice's due date
Observable: Negative means before the due date, 0 means on it, positive means after it. A step of +7 on an invoice due 10 March is dated 17 March; a step of -3 is dated 7 March.
Source: implied: "reminders" for "unpaid invoices" need a time relationship to the invoice

### C-5: A step's date is a calendar date in the account's time zone, without shifting for weekends or holidays
Observable: A step whose date falls on a Saturday, Sunday or public holiday is sent on that date.
Source: choice: simplest rule that is predictable; the request does not mention business days

### C-6: The send time is a whole hour of the day in the account's time zone, defaulting to 09:00
Observable: The send time can be set to any of 00:00, 01:00 ... 23:00; a new account shows 09:00; any other value is refused.
Source: choice: the request gives no time; a morning default avoids night-time email

### C-7: A reminder for a step is sent no earlier than the send time on the step's date and, when the system is healthy and within the volume of C-73, within 60 minutes after it
Observable: With a send time of 09:00 in the account's time zone, the email is handed to the mail provider between 09:00 and 10:00 that day, never before 09:00 and never on a different date.
Source: choice: the request says "automatic" without a precision; an hourly granularity matches the whole-hour send time

### C-8: Reminders are considered only for invoices in the states Open and Partially paid
Observable: An invoice in state Open or Partially paid whose balance is above zero receives reminders. An invoice in state Draft, Paid, Void or Written off receives none.
Source: choice: these are the invoice states this specification assumes the invoicing system has; "unpaid" in the request means money still owed on a billed invoice

### C-9: An invoice is settled when its state is Paid, Void or Written off, or when its outstanding balance is zero or less
Observable: After a payment, credit note, void or write-off brings an invoice to any of those, no further reminder is sent for it, whether the step was scheduled, being retried or requested manually.
Source: implied: "unpaid" in the request

### C-10: A reminder contains the following parts, all of them
Observable: sender business name; invoice number; outstanding balance with its currency; due date; a statement of how many days remain, that it is due today, or how many days overdue; the account's payment instructions; the customer-facing link to view the invoice when the invoice has one; the business's reply-to contact; the "stop reminders for this invoice" link; and a subject that contains the invoice number and the business name.
Source: implied: the customer must know who is asking, for what, how much, by when, how to pay and how to reach someone

### C-11: The amount in a reminder is the outstanding balance at the moment of sending, not the invoice's original total
Observable: An invoice of 1,000.00 USD with 400.00 USD paid shows 600.00 USD in the reminder.
Source: implied: a customer must not be asked for money they have paid

### C-12: A reminder goes to every billing address on the invoice, as a separate message to each address
Observable: An invoice with two billing addresses yields two emails per step, one addressed to each.
Source: choice: keeps per-address outcomes independent

### C-13: A test reminder goes only to the requesting user's own login address and touches no invoice
Observable: After the test request exactly one email arrives at the requester's login address, with its subject and body marked as a test and filled with sample invoice values; no customer receives anything; no invoice's history changes.
Source: implied: U-3

### C-14: An Owner or Admin can pause and resume reminders on a single invoice
Observable: The Pause control is offered on invoices in state Open or Partially paid. A paused invoice shows Paused and no automatic or manual reminder is sent for it until it is resumed; Resume returns it to the schedule.
Source: implied: U-7

### C-15: An Owner or Admin can send a reminder now for any invoice that is unsettled
Observable: The reminder reaches the invoice's billing addresses within 5 minutes; the history lists it as manual.
Source: implied: U-8

### C-16: Each reminder the system tries to send for an invoice is recorded in that invoice's history
Observable: After any attempt, automatic or manual, the invoice's history shows a new entry for it (fields in C-70).
Source: implied: U-9

### C-17: A transient delivery failure is retried up to 3 times, at least 15 minutes apart, and only on the same calendar day
Observable: Every failure not reported as permanent (timeouts, temporary refusals, provider errors) counts as transient. Up to 3 further attempts are made at least 15 minutes after the previous one. If all fail, or the account-time-zone day ends first, the entry shows Failed and no further attempt is made for that step.
Source: choice: bounded effort so a long provider outage does not delay a reminder into a later step's day

### C-18: Turning reminders off stops all automatic sending for the account within 60 minutes
Observable: After the Owner or Admin turns reminders Off, no automatic reminder for that account is sent more than 60 minutes later, including attempts that were being retried.
Source: implied: U-10

### C-19: The "stop reminders for this invoice" link stops reminders for that invoice, without login
Observable: Following the link shows a confirmation, and afterwards the invoice shows "stopped by recipient".
Source: choice: a way for customers to opt out protects sender reputation

### C-20: A schedule has at most 10 steps
Observable: Saving a schedule with 10 steps works; adding an 11th is refused with a message naming the limit, and the saved schedule is unchanged.
Source: choice: the request gives no bound; 10 prevents harassment

### C-21: The operator can stop all reminder sending system-wide
Observable: While the switch is off no reminder email leaves for any account within 5 minutes of flipping it; flipping it back resumes by the rules for catching up.
Source: implied: U-11

### C-22: Each invoice shows its reminder state
Observable: One of: Scheduled with the date of the next reminder; Paused; Stopped by recipient; Settled; Complete (no further steps); Off (account reminders are off). Where several apply the first in this order is shown: Settled, Stopped by recipient, Paused, Off, Complete, Scheduled. An invoice in Draft shows no reminder state.
Source: implied: U-1, U-7, U-9

### C-23: Reminders are delivered by email only
Observable: Every reminder is an email; no SMS, push or in-app message is sent as a reminder.
Source: choice: the request names no channel and invoices already carry email addresses

### C-24: An account has exactly one reminder schedule, shared by all its invoices and customers
Observable: The settings page shows one schedule; there is no way to give a different schedule to one customer or one invoice.
Source: choice: the request says "reminders" without per-customer variation

### C-25: Only an Owner or Admin of the account can use these controls: turn reminders On or Off, edit the schedule, send time, time zone, sender business name, reply-to address and payment instructions, send a test, pause or resume an invoice, send a reminder now, clear an address suppression
Observable: A Member of the account, or a user of another account, who attempts any of them is refused and nothing changes.
Source: implied: U-13; "Set up" is an administrative act

### C-26: Any user of the account (Owner, Admin or Member) can view the reminder settings, every invoice's reminder history, the failed-reminders list and the suppression list; no one outside the account can
Observable: A Member sees them; a user of another account, or a visitor who is not logged in, is refused.
Source: implied: U-13

### C-27: Every change to reminder settings is recorded with who made it, when, which setting, and the old and new values
Observable: Owners and Admins can view a list of changes covering: On/Off, schedule steps, send time, time zone, reply-to address, sender business name, payment instructions, and suppression clears. Each row shows user, timestamp, setting, old value and new value.
Source: implied: an automatic sender to customers needs accountability for who configured it

### C-28: An invoice with no due date is treated as due on its issue date
Observable: An invoice issued 10 March with no due date and a step of +7 gets a reminder dated 17 March.
Source: choice: the request assumes invoices have due dates; "due on receipt" is the usual meaning of none

### C-29: An invoice with no usable billing address gets no email, and the history says so
Observable: When an invoice has zero billing addresses, or an address that is not a syntactically valid email address, no email is sent to that address and the history shows Skipped with the reason "no recipient address".
Source: implied: "a thing it depends on" (an address) may be absent

### C-30: The time zone must be a valid time-zone name; anything else is refused
Observable: Saving "Europe/London" or "America/New_York" works; saving "Mars/Olympus" or an empty value is refused and the saved zone is unchanged.
Source: implied: C-5 and C-7 depend on a zone existing

### C-31: Changing the send time or the time zone applies to all steps not yet sent
Observable: After the change, each unsent step's send moment is computed from the new values.
Source: implied: two settings meeting reminders already in flight

### C-32: Dates in a reminder cannot be misread as day/month swapped
Observable: Every date shown is written with the month spelled out (for example "17 March 2027") or in ISO 8601 form (2027-03-17), never as an all-numeric day/month/year such as 03/04/2027.
Source: choice: customers span locales; the exact format is left open

### C-33: Reminder text is in English and users cannot edit it in this version
Observable: The settings page offers no control to edit subject or body; every reminder is in English.
Source: choice: the request does not ask for templates; limiting scope keeps the behaviour verifiable

### C-34: Amounts are shown in the invoice's own currency with that currency's standard number of decimal places
Observable: 600 US dollars shows as 600.00 with "USD" or "$"; 600 Japanese yen shows as 600 with "JPY" or "¥", no decimals.
Source: implied: an amount in a reminder must be unambiguous

### C-35: The invoice number, balance, due date, customer name and billing addresses used in a reminder are those at the moment it is sent
Observable: If the due date or an address is edited at 08:00 and a reminder is sent at 09:00, the reminder shows and uses the edited values.
Source: implied: U-12

### C-36: Each reminder is about one invoice; reminders for several invoices of the same customer are separate emails
Observable: A customer with three unsettled invoices due the same day receives three emails, none mentioning the other two.
Source: choice: simplest rule that leaks nothing between invoices

### C-37: No automatic reminder is sent after the last step of the invoice's schedule
Observable: For the default schedule and an invoice due 10 March, no automatic reminder is sent after 9 April (+30), and the invoice shows Complete.
Source: implied: the schedule is finite, and the request does not ask for indefinite chasing

### C-38: A schedule step's offset is between -60 and +365 days inclusive
Observable: Saving -60 or +365 works; saving -61 or +366 is refused with a message naming the step, and the saved schedule is unchanged.
Source: choice: the request gives no bound; these cover two months' notice and a year overdue

### C-39: Two steps in a schedule cannot have the same offset
Observable: Saving a schedule with two steps of +7 is refused with a message naming the duplicate, and the saved schedule is unchanged.
Source: implied: two identical steps would send the same reminder twice

### C-40: These fields have these limits, and a value outside them is refused with a message naming the field: sender business name 1 to 100 characters; reply-to address a syntactically valid email address; payment instructions 1 to 2,000 characters
Observable: A 101-character business name, an empty payment-instructions text or "not-an-email" as reply-to is refused and the saved value is unchanged.
Source: choice: a bounded message keeps reminders readable; figures are decided values

### C-41: A reminder is fully readable in a mail client that shows only plain text
Observable: In a plain-text-only view every part listed in C-10 is present, including both links as full addresses.
Source: implied: some mail clients and filters show only plain text

### C-42: A given step is sent for a given invoice and billing address at most once within one cycle
Observable: Within a cycle the step +7 yields at most one Sent row per billing address; removing the step from the schedule and adding it back does not make it send again.
Source: implied: "a thing done twice that should happen once"

### C-43: A new cycle begins for an invoice at exactly these events: the invoice becomes Open from Draft; the invoice returns to Open or Partially paid after having been settled; the invoice's due date changes
Observable: An invoice due 10 March whose +7 step was sent on 17 March has its due date moved to 20 April on 18 March: its +7 step is sent again on 27 April. A partial payment or an address edit does not begin a new cycle.
Source: implied: U-12

### C-44: Steps dated on or before the day of any of these events are not sent for that invoice, the day being a calendar date in the account's time zone: a new cycle beginning (C-43); a step added to the schedule or an existing step's offset changed; the account's reminders turned On
Observable: Turning reminders On on 20 November for an invoice due 1 November sends nothing for steps dated 20 November or earlier; an invoice opened on 10 March gets nothing for a step dated 10 March; a step of +7 added on 17 March for an invoice due 10 March sends nothing for it on that invoice; a step dated one day after the event is sent.
Source: choice: prevents bursts of stale or duplicate-looking reminders when existing data meets a new rule; U-14

### C-45: Editing the schedule applies to the future steps of every unsettled invoice at once
Observable: A removed step is not sent for any invoice afterwards; an added step is dated relative to each invoice's due date; steps already sent stay in the history.
Source: implied: U-2

### C-46: If several steps for an invoice are due and unsent at once, only the latest is sent
Observable: After an outage covering the +7 and +14 send moments, only the +14 reminder is sent; the +7 row shows Skipped with the reason "superseded".
Source: choice: avoids flooding a customer after downtime

### C-47: A due step that is more than 3 calendar days past its date in the account's time zone is not sent
Observable: A step dated 10 March that has not been sent by the end of 13 March is never sent; its row shows Skipped with the reason "expired". A step dated 10 March sent on 13 March is within the window.
Source: choice: a stale reminder is worse than none; 3 days is the decided value

### C-48: Immediately before every attempt, including retries and manual sends, the system re-checks these conditions and sends nothing if any holds: the invoice is settled; the invoice is paused; the invoice is stopped by the recipient; the account's reminders are Off or operator-disabled (automatic attempts only); the operator's system-wide switch is off; the invoice or account no longer exists
Observable: A payment recorded at 09:00:10 for a reminder due at 09:00:00 results in no email and a Skipped row with the matching reason from C-72. When the invoice or account no longer exists there is no row to show and nothing is sent.
Source: implied: U-5

### C-49: When two sending runs overlap or the same step is processed twice, the customer still receives it once
Observable: Running two sending processes at the same moment for a due step yields exactly one email per billing address and one Sent row.
Source: implied: "a thing done twice that should happen once"

### C-50: When the outcome of an attempt is unknown (for example the system stopped after handing the message to the provider and before recording the result), the row shows Unknown and the step is not sent again automatically
Observable: After such an interruption no second email goes to the customer for that step; the row shows Unknown and appears in the failed-reminders list.
Source: choice: a missed reminder is less harmful than a duplicate

### C-51: Sending a reminder manually does not consume, move or cancel any schedule step
Observable: A manual reminder sent at 17:00 on 17 March does not stop the +7 step due on 17 March from being sent on its own schedule.
Source: choice: keeps the schedule predictable; the manual send is an extra

### C-52: A manual reminder is refused when any reminder for that invoice reached the Sent status in the preceding 24 hours
Observable: The refusal states the earliest time sending is allowed again. The 24 hours are counted from the most recent Sent row of any origin.
Source: choice: prevents repeated clicks from spamming a customer

### C-53: A manual reminder is refused when any of these holds, and the refusal names the reason: the invoice is settled; the invoice is in Draft; the invoice is paused; the invoice is stopped by the recipient; a prerequisite listed in C-2 is missing; C-52 applies; the user lacks the Owner or Admin role; every billing address of the invoice is absent, invalid or suppressed
Observable: In each case no email is sent and the invoice's history is unchanged.
Source: implied: U-8 unhappy paths

### C-54: A manual reminder does not require the account's reminders to be On
Observable: An account whose reminders are Off, with all C-2 prerequisites met, can send a manual reminder.
Source: choice: manual sending is an explicit human decision

### C-55: Steps whose send moments pass while an invoice is paused are not sent after it is resumed
Observable: Paused from 8 March to 20 March on an invoice due 10 March, its 10 March (0) and 17 March (+7) rows show Skipped with the reason "invoice paused"; on resuming on 20 March nothing is sent for them.
Source: choice: a late flood after a dispute would defeat the pause

### C-56: A pause stays in force across invoice changes until a user resumes it
Observable: A paused invoice that is edited (due date, amount, address) or partially paid is still Paused and sends nothing.
Source: implied: pause meeting edits

### C-57: A customer's stop is permanent for that invoice and cannot be undone by the business
Observable: There is no Resume control on an invoice stopped by the recipient.
Source: choice: undoing a customer's stated wish risks complaints

### C-58: Following the stop link of an invoice that is already settled shows that the invoice is settled and changes nothing
Observable: The page says the invoice is already settled and the invoice's state is not changed to "stopped by recipient".
Source: implied: a link in an old email is followed later

### C-59: Following a stop link with an unrecognised or malformed token shows a neutral not-found page and changes nothing
Observable: The page reveals no invoice, business or customer information and no invoice changes.
Source: implied: links can be mistyped, truncated or forged

### C-60: A stop link's token is specific to one invoice, cannot be derived from other invoices' tokens, and carries at least 128 bits of randomness
Observable: Changing any character of a valid token yields the not-found page of C-59; one invoice's token never stops another invoice.
Source: implied: someone must not be able to stop reminders on invoices they were not sent

### C-61: After the operator's system-wide switch is turned back on, steps missed while it was off are handled by the rules of C-46 and C-47
Observable: Off from 10 March 08:00 to 11 March 12:00, the steps due on 10 and 11 March for an invoice are not sent while off; after the switch is on, only the latest (the 11 March one) is sent, within the window.
Source: implied: U-11

### C-62: An invoice or account that no longer exists receives no reminders
Observable: After an account is deleted or an invoice removed, no further email is sent for it, including pending retries.
Source: implied: "a thing it depends on" disappearing

### C-63: A sending run uses one version of the schedule, never a mixture of before and after a save
Observable: A schedule save made while a run is in progress is reflected completely in the next run and not partly in the current one.
Source: implied: two parts meeting at once

### C-64: A permanent delivery failure for an address is recorded as Bounced and not retried
Observable: When the provider reports a permanent failure for an address, that row shows Bounced and no more attempts are made for that step and address.
Source: implied: a dependency failing

### C-65: A permanent delivery failure for an address adds the address to the account's suppression list
Observable: After a Bounced row, the address appears on the suppression list.
Source: implied: repeat bounces harm sender reputation

### C-66: A spam complaint about a reminder adds that address to the suppression list
Observable: After the provider reports a complaint, the address is on the suppression list within 60 minutes of the report.
Source: implied: protects sender reputation

### C-67: A suppressed address receives no reminders from any invoice in the account, automatic or manual
Observable: Reminders to that address are Skipped with the reason "address suppressed"; the invoice's other billing addresses are unaffected.
Source: implied: a repeat bounce or complaint harms sender reputation

### C-68: An Owner or Admin can clear a suppression
Observable: After clearing, the next reminder to that address is attempted; the clearing is recorded in the change list of C-27.
Source: implied: addresses are corrected or mistaken

### C-69: A bounce reported after a reminder was Sent changes that row to Bounced
Observable: A row shown as Sent at 09:05 reads Bounced after the provider reports a permanent failure at 09:40.
Source: implied: delivery results arrive late

### C-70: The history has one row per attempted step and billing address, with its own status
Observable: A step on an invoice with two billing addresses yields two rows. A manual send yields one row per address with origin "manual". Each row shows origin (the step's offset or manual), the date it was scheduled for, the time of each attempt and its status.
Source: implied: U-9; keeps per-address outcomes independent

### C-71: A history row has exactly one of these statuses: Sent (the mail provider accepted the message), Bounced, Failed, Unknown, Skipped
Observable: Each row shows one of the five. Sent means accepted by the mail provider, not read by the customer.
Source: implied: C-17, C-50, C-64

### C-72: A Skipped row shows exactly one of these reasons: invoice settled; invoice paused; stopped by recipient; account reminders off; system switch off; superseded; expired; no recipient address; address suppressed; environment not permitted
Observable: Each Skipped row displays one reason from this list.
Source: implied: U-9; the reasons derive from C-29, C-46, C-47, C-48, C-55, C-67, C-83

### C-73: When more than 1,000 reminders are due for one account at one send time, all are handed to the mail provider as fast as the provider's rate allows, and the 60-minute bound of C-7 does not apply to them
Observable: 1,000 or fewer due reminders are handed over within 60 minutes after the send time; with more, the rest follow, and any not sent within the window of C-47 show Skipped with the reason "expired". The provider's rate limit figure is unconfirmed.
Source: choice: the provider's rate caps what the design can do; 1,000 is the decided figure

### C-74: A reminder passes sender authentication when received
Observable: The headers of a reminder received at a major mailbox provider show SPF pass, DKIM pass and DMARC pass for the From domain.
Source: implied: mail providers reject or junk unauthenticated mail; needed before shipping beyond a development environment

### C-75: Reminders cannot be turned on in production until the sending domain is verified with the mail provider
Observable: In production, turning On is refused with a message that the sending domain is not verified, until the operator marks it verified.
Source: implied: what the platform demands before this ships beyond development

### C-76: The From name of a reminder is the account's sender business name, and replying to it reaches the account's reply-to address
Observable: The recipient's mail client shows the business name as sender; a reply is addressed to the reply-to address.
Source: implied: C-10

### C-77: Bounce and complaint reports from the mail provider are applied within 60 minutes of the provider sending them
Observable: A bounce reported at 09:40 shows on the row by 10:40.
Source: implied: C-64, C-66, C-69

### C-78: The reminder job runs at least every 15 minutes, and the operator is alerted when it has not run for 30 minutes
Observable: The operator's view shows the time of the last completed run, which is never more than 15 minutes old in normal operation; after 30 minutes without a run an alert reaches the operator.
Source: choice: C-7's 60-minute bound needs a regular trigger

### C-79: When a send time falls in a daylight-saving gap that does not exist locally, the reminder is sent at the first moment after the gap
Observable: With a send time of 02:00 in America/New_York on the spring-forward day, the reminder is sent at 03:00 that day, once.
Source: implied: the runtime's calendar rules

### C-80: When a send time occurs twice because clocks are set back, the reminder is sent once, at the first occurrence
Observable: With a send time of 01:00 in America/New_York on the fall-back day, one email is sent for the step, not two.
Source: implied: the runtime's calendar rules

### C-81: A sending run cut short by a platform time limit, crash or restart loses no due reminder and duplicates none
Observable: After stopping a run mid-way and letting later runs proceed, every due reminder is sent exactly once, except any past the window of C-47 and any Unknown of C-50. The platform's time limit is unconfirmed.
Source: implied: hosted jobs have execution limits

### C-82: Reminders carry no attachments
Observable: A received reminder has no attached file.
Source: choice: small messages with links are least likely to be filtered as spam

### C-83: In a non-production environment reminders go only to addresses on an allow-list
Observable: A reminder to an address not on the allow-list is not sent and the row shows Skipped with the reason "environment not permitted".
Source: implied: what is demanded before this could ship; testing must not email real customers

### C-84: Times in the history and settings are shown with the account's time zone
Observable: A row sent at 09:05 in America/New_York displays 09:05 and the zone, not the viewer's or the server's.
Source: implied: C-5, C-7

### C-85: History rows and change-list rows are kept for at least 24 months
Observable: A row created now is still viewable 24 months later.
Source: choice: covers a normal dispute and audit period

### C-86: Users cannot edit or delete history rows or change-list rows
Observable: No control to edit or delete them exists, for any role.
Source: implied: accountability

### C-87: Reminder activity never changes an invoice's state, balance, due date, addresses or any other invoice data
Observable: The invoice's fields before and after any reminder, pause, stop or failure are identical, except for its reminder state and history.
Source: implied: what must never happen

### C-88: A reminder is always sent under the identity (name, reply-to, payment instructions) of the account that owns the invoice
Observable: With two accounts, A's invoices never carry B's business name, reply-to address or payment instructions.
Source: implied: what must never happen

### C-89: A reminder, a stop page and a history view reveal nothing about any other invoice, customer, billing address or account
Observable: A reminder lists one invoice only and shows no other recipient's address; a stop page shows only a confirmation; a user sees only their account's history.
Source: implied: what must never happen

### C-90: Suppression, customer stop, pause and settled checks apply identically to automatic, retried and manual sending
Observable: For each of these four conditions, an automatic step, a retry and a manual send are all blocked.
Source: implied: "a rule enforced in one path and not another"

### C-91: With reminders Off or the operator's switch off, invoice creation, delivery of invoices, payment and every other existing invoice function work as before
Observable: An invoice can be created, issued and paid with reminders Off exactly as before the feature existed.
Source: implied: what must not change; going back to the version before

### C-92: Invoices existing before this feature have an empty reminder history and show Off until reminders are turned on
Observable: An invoice created before the feature shows no history; its state reads Off.
Source: implied: carrying on with existing data

### C-93: The operator can see, per day and system-wide, the counts of reminders by status and by Skipped reason, and the time of the last completed run
Observable: A page or query shows, for a chosen day, a number for each status of C-71 and each reason of C-72.
Source: implied: operator's work (observe)

### C-94: The operator can disable reminders for a single account, and the account's users cannot turn them back on
Observable: An operator-disabled account shows Off with the note that the operator disabled it; turning On is refused with that reason. Reminders resume only when the operator re-enables and a user turns On.
Source: choice: a single misbehaving account must be stoppable without stopping everyone

### C-95: The failed-reminders list shows invoices having a row in the last 90 days with status Failed, Bounced or Unknown, or Skipped with the reason "no recipient address" or "address suppressed"
Observable: Such an invoice appears in the list with its latest such row; an invoice with none of them does not appear.
Source: implied: U-9; 90 days is a choice

### C-96: Reminders that are On cannot be left with an empty schedule
Observable: Saving a schedule with 0 steps while the account is On is refused with a message and the saved schedule is unchanged; with the account Off it can be saved.
Source: implied: C-2 requires a step to turn On, and an edit must not undo that afterwards

### C-97: No more than 10 test reminders can be sent per account in any 60 minutes
Observable: The 11th request within an hour is refused with a message saying when it is allowed again; no email is sent.
Source: choice: bounds the cost and abuse of the test control; 10 is the decided value

### C-98: Reminders go to at most the first 5 billing addresses of an invoice, in the order the invoice lists them
Observable: An invoice listing 7 billing addresses yields 5 emails per step, to the first 5; the 6th and 7th receive nothing.
Source: choice: bounds fan-out per invoice; 5 is the decided value, and the request does not say how many addresses an invoice holds
