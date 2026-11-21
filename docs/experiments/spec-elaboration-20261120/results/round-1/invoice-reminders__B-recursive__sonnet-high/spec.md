## Use cases

### U-1: An account admin turns on automatic reminders for the first time, to get unpaid invoices chased without lifting a finger
Flow: The admin opens the reminder settings and sees reminders Off, the account's time zone, and the default schedule (3 days before the due date, on the due date, 7 days after, 14 days after). The settings also say that reminders whose date has already passed when they are turned on will not be sent. The admin switches reminders On and sees On with the same schedule. From then on customers with unpaid invoices receive reminder emails on those dates with no further action.
Source: request ("Set up automatic reminders for unpaid invoices")

### U-2: An account admin changes the schedule and sends themselves a sample, to be sure customers get what the admin intends
Flow: The admin edits the schedule (for example adds "5 days before" and removes "14 days after"), saves, and sees the new schedule. The admin asks for a sample reminder and receives an email at their own address that is marked as a sample. The admin tries values that are not allowed (for example "2.5 days", a repeated step, an empty schedule) and sees the save refused with the reason; the saved schedule is unchanged.
Source: implied: "Set up" means someone chooses when reminders go out and can check what they look like

### U-3: A customer receives a reminder for an unpaid invoice and pays it, to settle what they owe
Flow: On a scheduled date the customer finds an email in their inbox from the business, naming the invoice, the amount still owed, the due date and whether it is coming due, due today or overdue. They open the link in the email without logging in and see the invoice. They pay it by whatever means the invoice offers. Once the payment is recorded on the invoice, no further reminder arrives.
Source: request

### U-4: An account user records that an invoice is paid, voided, credited or reopened, so that reminders stop or resume accordingly
Flow: The user records a full payment, voids the invoice, or applies a credit that brings the balance to zero; the invoice's upcoming-reminders list becomes empty and no reminder reaches the customer afterwards. If the user later reverses the payment or credit so a balance is owed again, reminders resume for dates still in the future. A partial payment keeps reminders going, now for the smaller balance.
Source: implied: "unpaid invoices"

### U-5: An account user pauses reminders on one invoice (for example it is disputed) and later resumes them
Flow: On the invoice the user pauses reminders and sees it marked paused. They see it in the list of paused invoices. Reminders that fall due while paused are not sent. The user later resumes reminders and sees the invoice no longer marked paused; reminders whose dates are still in the future are then sent.
Source: implied: unpaid invoices include disputed ones that the business does not want to chase

### U-6: An account user reviews what was sent, what will be sent and what went wrong, to know where each invoice stands
Flow: On an invoice the user sees the history of reminders (which step, for which date, to which address, when, and the outcome with a reason where it was not sent) and the upcoming reminders with their dates. In a "reminder problems" view the user sees invoices whose reminders failed or could not be sent (no address, bounced address, provider failure). Admins receive at most one email a day summarising new problems.
Source: implied: automatic action on customers needs to be observable by the business that owns it

### U-7: A customer stops receiving reminders, to be left alone
Flow: The customer clicks the "stop reminders" link in a reminder email, lands on a page that asks them to confirm, presses the confirm button, and sees a confirmation. They receive no further reminders from that business at that address. The business sees that the customer opted out and can switch it back on if the customer asks.
Source: implied: recipients of automatic email expect a way to stop it, and mail providers require one

### U-8: An account user edits an invoice while reminders are scheduled, so reminders follow the invoice's current facts
Flow: The user changes the due date, the billing email address(es), or the amount. The invoice's upcoming reminders and the next email reflect the new facts; reminders already sent stay in the history.
Source: implied: invoices change after they are issued

### U-9: An account admin turns reminders off and later on again
Flow: The admin switches reminders Off; nothing further is sent to any customer of the account. Later the admin switches On again and sees the same schedule; only reminders whose dates are still ahead are sent, not a flood of the ones missed while off.
Source: implied: anything that emails customers automatically needs an off switch, and an off switch needs an on

### U-10: The operator of the system keeps reminders running, watches them, stops them, and recovers from trouble
Flow: The operator starts the system and sees reminders being processed (counts of sent, failed, skipped per day, without customer email addresses). The operator can stop all sending across every account at once and start it again. After the system was down for a day or the email provider failed for hours, reminders that were due are sent once on recovery if still within their allowed lateness, none twice, and the rest are recorded as missed.
Source: implied: "automatic" means something runs unattended; unattended things fail and must be stoppable and recoverable

### U-11: The operator runs the system in a development or test environment, without emailing real customers
Flow: In an environment not marked as production, the reminders run exactly as in production but every message goes to one configured test inbox rather than to the customers' addresses.
Source: implied: this sends email to real people from real data, so a copy of the data must not do that

### U-12: The operator rolls out this feature on an installation that already has invoices, and may go back
Flow: Existing invoices, customers and payments are unchanged after the feature is added. Reminders are off until each account turns them on. If the operator goes back to the version before the feature, invoices, customers and payments are still intact and no reminders are sent.
Source: implied: "carry on with data that already exists, go back to the version before"

### U-13: A team member without admin rights uses an account that has reminders
Flow: The member can see the reminder settings and an invoice's reminder history but cannot change the settings. A member who is allowed to edit invoices can pause and resume reminders on an invoice; a member who cannot edit invoices cannot.
Source: implied: settings that email customers on the business's behalf are not for everyone

### U-14: An account with a very large number of unpaid invoices turns reminders on, or has many reminders due on the same day
Flow: The admin turns reminders on for an account with 10,000 unpaid invoices due on the same day. Every reminder that is due ends up sent or with a recorded reason it was not, none twice, none sent at night.
Source: implied: the largest case of the ordinary use

## Clauses

### C-1: With reminders on, a customer with an unpaid invoice receives reminder emails automatically
Observable: With reminders turned On before 2026-12-01, time zone UTC, the default schedule, and an issued unpaid invoice due 2026-12-10 that was issued before 2026-12-01, the customer's billing address receives reminders on 2026-12-07, 2026-12-10, 2026-12-17 and 2026-12-24, without anyone doing anything on those days, provided the invoice is still unpaid on each.
Source: request

### C-2: An account that has never turned reminders on sends none
Observable: A new account with an issued unpaid invoice due today: no reminder email is sent for it on any day, and the reminder settings show Off.
Source: choice: reminders are email sent to a business's customers in its name; the business must opt in. The loosest rule that protects that is off until turned on.

### C-3: An account admin can turn reminders on
Observable: After the admin switches reminders On and saves, the settings show On, and reminders are then sent per C-1.
Source: implied: U-1

### C-4: Turning reminders off stops every reminder that has not yet been handed to the email provider
Observable: After an admin saves Off, the settings show Off; a reminder that would have been sent the next hour is not sent; a message already handed to the provider before the save may still arrive.
Source: implied: U-9

### C-5: The schedule a first-time admin sees is 3 days before the due date, on the due date, 7 days after, 14 days after
Observable: The settings of an account that never changed its schedule list exactly four steps: -3, 0, +7, +14 days relative to the due date.
Source: choice: the request does not say when to remind; this is a usual dunning cadence. A default is needed because turning reminders on must work without first designing a schedule.

### C-6: A schedule is a set of steps, each a whole number of days relative to an invoice's due date (negative before, zero on, positive after)
Observable: An admin saves steps -5, 0, 2 and the settings show exactly those three; an invoice due 2026-12-10 then shows upcoming reminders dated 2026-12-05, 2026-12-10 and 2026-12-12.
Source: implied: U-2

### C-7: A schedule with a step that is not a whole number, or two equal steps, is refused
Observable: Saving "2.5" or saving "3, 3" is refused with a message naming the problem; the previously saved schedule stays.
Source: implied: U-2; a step has to name one calendar date

### C-8: A schedule with more than 10 steps, or with a step below -30 or above +90, is refused
Observable: Saving 11 steps is refused with a message naming the problem; saving -31 or +91 is refused; saving 10 steps including -30 and +90 is accepted.
Source: choice: the request is silent on limits; these accept every realistic cadence while stopping a schedule that would email a customer daily for a year

### C-9: An empty schedule is refused
Observable: Saving a schedule with no steps is refused with a message saying to add a step or turn reminders off; the previous schedule stays.
Source: choice: an empty schedule on an "On" account would look active and do nothing; the off switch already exists for that

### C-10: A refused schedule save changes nothing
Observable: After any refused save the settings show the same schedule and the same On/Off state as before it, and reminders already pending are unaffected.
Source: implied: U-2

### C-11: A step's reminder is due on its target date, which is the invoice's due date plus the step's days counted as calendar days in the account's time zone
Observable: An invoice due 2026-01-31 with step +30 has target date 2026-03-02; an account in America/New_York with due date 2026-03-05 and step +14 has target date 2026-03-19 and the reminder is sent on 2026-03-19 New York time even though daylight saving began on 2026-03-08.
Source: implied: U-1; "days relative to a due date" has to mean something exact

### C-12: Reminder emails are only ever sent between 08:00 and 18:00 in the account's time zone
Observable: In a test with the clock set to 07:59 local, 18:01 local, or 03:00 local, no reminder email is sent however many are due; at 08:00 local sending may begin.
Source: choice: the request is silent; customers should not be emailed at night, and the loosest rule that guarantees it is a daytime window

### C-13: A reminder that can be sent is sent on its target date within the 08:00–18:00 window
Observable: With nothing blocking it (invoice unpaid, address valid, provider working and within its send-rate limit), a reminder with target date 2026-12-07 is handed to the email provider (and shown as sent) between 08:00 and 18:00 local on 2026-12-07; delivery to the customer's inbox after that is up to the mail system.
Source: implied: C-1, C-11

### C-14: An issued invoice with an outstanding balance above zero is reminded
Observable: An invoice that has been issued to the customer, is not void, and shows a balance of 250.00 is reminded per its schedule.
Source: implied: "unpaid invoices"

### C-15: An invoice that has not been issued (a draft) is never reminded
Observable: A draft invoice with a due date entered: no reminder is sent and its upcoming-reminders list is empty. When it is issued, reminders begin per C-39.
Source: implied: "unpaid invoice" means the customer has been billed

### C-16: An invoice with zero balance (paid in full, or credited to zero) is never reminded
Observable: An invoice recorded paid on 2026-12-06 has its 2026-12-07 reminder not sent and shows no upcoming reminders.
Source: implied: "unpaid"

### C-17: A void invoice is never reminded
Observable: An invoice voided on 2026-12-06 has its 2026-12-07 reminder not sent and shows no upcoming reminders.
Source: implied: "unpaid"; a void invoice is not owed

### C-18: A partly paid invoice is reminded for the amount still owed
Observable: An invoice of 1,000.00 with 400.00 recorded paid has reminders that state 600.00 outstanding.
Source: implied: U-4; "unpaid" includes what remains

### C-19: Each reminder identifies which invoice it is about and who it is from
Observable: The email shows the issuing business's name and invoice number INV-1042, and its subject line contains INV-1042.
Source: implied: U-3; the customer must know which invoice and from whom

### C-20: Each reminder states the amount outstanding at the time of sending, with its currency
Observable: For a EUR invoice with 600.00 outstanding at send time, the email states 600.00 and EUR (or the € symbol); if the balance changed after the reminder was scheduled the figure is the balance at sending.
Source: implied: U-3

### C-21: Each reminder states the due date so that its day and month cannot be confused
Observable: A due date of 2026-12-03 appears with its month as a word or otherwise unmistakable (for example "3 December 2026"), never only as "03/12/2026".
Source: choice: the request is silent on format; customers in different countries read numeric dates differently, so only ambiguity is excluded

### C-22: Each reminder says whether the invoice is due in some days, due today, or overdue by some days, with the number of days
Observable: The step -3 email says it is due in 3 days; the step 0 email says due today; the step +7 email says 7 days overdue. The count is taken on the day the email is sent: the -3 reminder sent a day late (after an outage) says due in 2 days.
Source: implied: U-3

### C-23: Each reminder contains a link that opens that invoice in a browser without logging in
Observable: Opening the link in a browser with no session shows the invoice for the reminder (number, amount, due date); it shows no other invoice and no link in it leads to another customer's data.
Source: implied: U-3; "how do I pay it" needs the invoice at hand

### C-24: The link in a reminder still works after the invoice is paid and then shows it as paid
Observable: A link from a reminder opened a week after the invoice was paid shows the invoice marked paid and offers no way to pay it again.
Source: implied: U-3; customers open old emails

### C-25: A reminder shows the business as the sender's name and replies go to the business
Observable: The From name shown is the business's name; pressing Reply addresses the business's contact address.
Source: choice: the request is silent; customers answer to the business, and the system's own address is not one they know

### C-26: Each billing email address on the invoice receives its own separate message
Observable: An invoice with billing addresses a@x.example and b@y.example causes two messages, one addressed only to each; if a@x.example bounces, b@y.example still has its message.
Source: choice: the request is silent; one message per address keeps opt-outs and failures per address

### C-27: The addresses a reminder goes to are the billing email addresses recorded on the invoice (the ones the invoice itself is sent to) as they are when sending is about to happen
Observable: An address added on the invoice the day before a reminder is due receives it; an address removed the day before does not.
Source: implied: U-8

### C-28: An invoice with no billing email address gets its due reminders skipped and recorded as "no email address"
Observable: An invoice with no billing address, due reminder on 2026-12-07: nothing is sent, the history shows an entry for 2026-12-07 saying skipped, no email address, and the invoice appears in the reminder problems view.
Source: implied: U-6; a thing it depends on is missing

### C-29: Every attempted, skipped or failed reminder is recorded on the invoice with its step, target date, address, time and outcome
Observable: The invoice's history shows one entry per address per reminder with: step (for example +7), target date, address, the time, and an outcome of sent, failed, skipped (with the reason), missed, superseded, bounced, or outcome unknown.
Source: implied: U-6

### C-30: An invoice shows its upcoming reminders with their dates
Observable: An invoice due 2026-12-10 with the default schedule viewed on 2026-12-08 lists upcoming reminders for 2026-12-10, 2026-12-17 and 2026-12-24; viewed on 2026-12-25 it lists none and says no further reminders are scheduled.
Source: implied: U-6

### C-31: An account user who may edit invoices can pause reminders on one invoice
Observable: After pausing, the invoice shows as paused and its reminders due while it is paused are not sent.
Source: implied: U-5

### C-32: A reminder that the system comes to send while its invoice is paused is skipped for good, recorded as "paused"
Observable: Pause on 2026-12-06, resume on 2026-12-08: the 2026-12-07 reminder is never sent, not even on 2026-12-08, and the history shows it skipped (paused).
Source: choice: the request is silent; sending a stale reminder on resume would surprise the person who paused it

### C-33: An account user who may edit invoices can resume reminders on a paused invoice
Observable: After resuming the invoice no longer shows paused and reminders still to be sent (such as one dated 2026-12-17 when resumed on 2026-12-08) are sent.
Source: implied: U-5

### C-34: Paused invoices can be listed
Observable: A list of the account's paused invoices shows exactly the invoices currently paused.
Source: implied: U-5; a pause with nowhere to see it gets forgotten

### C-35: Every reminder email contains a link to stop further reminders
Observable: Each reminder email contains a "stop reminders" link.
Source: implied: U-7

### C-36: Opening the stop link changes nothing until the customer presses a confirm button
Observable: Requesting the stop link's URL (as a mail scanner or link preview would) leaves reminders going; the page shows a confirm button; pressing it records the opt-out.
Source: implied: U-7; mail security software opens links in emails automatically

### C-37: After a customer confirms, no reminder is sent to that address for any invoice of that business
Observable: After a@x.example confirms for business B, reminders due the next day for any of B's invoices to a@x.example are skipped and recorded as "customer opted out"; the same address still receives reminders from business C.
Source: implied: U-7

### C-38: The business can see which addresses opted out and can clear an opt-out
Observable: The account shows the list of opted-out addresses with the date; after clearing one, reminders with a target date on or after that day are sent to that address again.
Source: implied: U-7; a state needs an end

### C-39: A reminder whose target date is on or before the date the invoice was issued is never sent
Observable: An invoice issued on 2026-12-08 with due date 2026-12-10 and the default schedule: the -3 reminder (2026-12-07) is never sent; the 0, +7 and +14 ones are. An invoice issued 2026-12-10 due 2026-12-10 gets no step-0 reminder on 2026-12-10.
Source: implied: U-1; a "3 days before" reminder for an invoice that did not exist then makes no sense, and a reminder on the day the invoice itself is sent is noise

### C-40: An admin can send themselves a sample reminder, at any hour
Observable: Asking for a sample at 03:00 local delivers one email within 5 minutes to the admin's own address, clearly marked as a sample and showing the account's business name, with example invoice values.
Source: choice: the request is silent; a sample lets the admin check what customers will see before turning on

### C-41: Only an account admin can change the reminder settings
Observable: A member who is not an admin sees the settings but saving a change is refused; an admin's save succeeds.
Source: implied: U-13

### C-42: Only a member who can edit invoices can pause or resume reminders on an invoice, and any member who can view an invoice can see its reminder history
Observable: A view-only member sees the history and upcoming list but the pause control is absent or refused; an invoice editor can pause.
Source: implied: U-13

### C-43: A reminder problems view lists each invoice that has a reminder with a problem outcome, with the reason, until a later reminder for it is sent, it stops being unpaid, or it is deleted
Observable: A problem outcome is failed, bounced, outcome unknown, missed, or skipped for no email address, invalid address or address bounced (not paused, not opted out, not superseded). After such an outcome the invoice appears in the view with the reason; once the business fixes the invoice's address and the next reminder is sent, or the invoice is recorded paid, the view no longer lists it.
Source: implied: U-6

### C-44: An invoice with no due date is treated as due on the date it was issued
Observable: An invoice issued 2026-12-01 with no due date and the default schedule gets reminders on 2026-12-08 and 2026-12-15 only (the -3 and 0 steps fall on or before the issue date, per C-39).
Source: choice: the request is silent; chasing it on a recognisable date serves the business better than never chasing it

### C-45: A reminder whose target date is earlier than the date reminders were last turned on for the account is never sent
Observable: Reminders turned on at 10:00 on 2026-12-10 for an invoice due 2026-11-30 with the default schedule: the -3, 0 and +7 reminders (dates 2026-11-27, 2026-11-30, 2026-12-07) are never sent, and the +14 reminder is sent on 2026-12-14. Turned Off at 22:00 on 2026-12-11 and On on 2026-12-20, no reminder dated 2026-12-12 to 2026-12-19 is sent.
Source: implied: U-1, U-9; existing unpaid invoices are found when reminders are turned on, and chasing them for dates already past would flood customers

### C-46: Reminders stop only when the system's record says the invoice is paid; a payment the business has not recorded does not stop them
Observable: A customer pays by bank transfer but the invoice is not marked paid: the next reminder is still sent; after the payment is recorded the next scheduled one is not.
Source: implied: "unpaid" can only mean unpaid as far as the system's records say

### C-47: Each unpaid invoice of a customer has its own reminders and its own email
Observable: A customer with three unpaid invoices all due 2026-12-10 receives three separate emails on 2026-12-10, each naming only its own invoice.
Source: choice: the request is silent; separate messages keep history, pause and amounts per invoice

### C-48: One account's settings, pauses, opt-outs, and reminder history never affect or appear in another account's
Observable: Account A turns reminders Off and Account B has them On: B's customers still get reminders. An address that opted out of A still receives B's reminders. A member of A cannot see B's history.
Source: implied: accounts are separate businesses; "who is allowed to see it"

### C-49: Dates for an account are computed in the account's time zone, UTC if the account has none set
Observable: An account with no time zone set, due date 2026-12-10, step 0: the reminder goes between 08:00 and 18:00 UTC on 2026-12-10. For an account set to Asia/Tokyo it goes between 08:00 and 18:00 Japan time on 2026-12-10.
Source: choice: the request is silent; a fixed fallback makes the behaviour defined for every account

### C-50: If the account has no contact address, replies go to the account owner's email address
Observable: With no contact address set, pressing Reply on a reminder addresses the account owner's login email address.
Source: choice: C-25 needs a reply address; this is the one that always exists

### C-51: The stop-reminders link works without logging in
Observable: Opening the link in a browser with no session shows the confirm page for that customer's address and that business only.
Source: implied: U-7; customers have no account

### C-52: The stop-reminders link keeps working however old the email is
Observable: A stop link from a reminder sent 400 days ago still shows the confirm page and, on confirming, records the opt-out.
Source: implied: U-7; people act on old email

### C-53: A billing address that is not a syntactically valid email address is skipped and recorded as "invalid address"
Observable: A billing address "john@" with a reminder due: no send is attempted, the history shows skipped, invalid address, and the invoice is in the reminder problems view.
Source: implied: U-6; a thing it depends on is malformed

### C-54: After the last step of the schedule no further automatic reminder is sent
Observable: With the default schedule an invoice due 2026-12-10 and still unpaid on 2027-06-01 receives nothing that day or later after the 2026-12-24 reminder.
Source: implied: "reminders" at fixed steps are finite; an endless nag would be a different request

### C-55: An account with no unpaid invoices causes no emails, no history, no problems and no error
Observable: Reminders On on an account whose invoices are all paid: after a day of operation nothing was sent, the problems view is empty, the operator sees no error for the account.
Source: implied: the empty case of U-1

### C-56: An account that is suspended or closed sends no reminders, and on reactivation behaves as if reminders were turned on that day
Observable: Account closed at 22:00 on 2026-12-11 and reactivated on 2026-12-20: no reminder is sent while closed; reminders dated 2026-12-12 to 2026-12-19 are never sent; reminders dated 2026-12-20 or later are.
Source: implied: an account that no longer exists as a customer of the product should not send mail in its name

### C-57: A reminder that could not be sent on its target date can still be sent up to the end of the third calendar day after its target date, and never later
Observable: Reminder with target date 2026-12-07 and the system down all of 2026-12-07 and restored at 09:00 on 2026-12-08: it is sent on 2026-12-08 between 09:00 and 18:00 local. Restored on 2026-12-10: it is sent. Restored on 2026-12-11 instead: it is not sent, and the history shows it missed. Reminders turned on at 19:00 on 2026-12-10 for a reminder dated 2026-12-10 are sent at or after 08:00 on 2026-12-11.
Source: choice: the request is silent on outages; a short grace keeps customers from being missed after a brief outage, and a limit stops a very late "3 days before due" notice

### C-58: When several reminders for the same invoice and address are due and unsent at the same moment, only the one with the latest target date is sent and the others are recorded as "superseded"
Observable: Due 2026-12-10, default schedule, system down 2026-12-07 to 2026-12-09 and restored at 09:00 on 2026-12-10: the customer receives one email (the due-today one) and the history shows the 2026-12-07 reminder as superseded.
Source: choice: the request is silent; a customer must not receive a burst of emails after an outage

### C-59: Immediately before a message is handed to the email provider the invoice and address are checked again, and nothing is sent if the invoice is paid, void, at zero balance, paused, or the address opted out, or the account has reminders Off
Observable: An invoice paid at 10:00:00 whose reminder was due at 09:00 but not yet handed to the provider at 10:00:00 is not sent; one handed to the provider at 09:59:59 is sent.
Source: implied: U-4, U-5, U-7; time passes between deciding and sending, and the world changes in between

### C-60: At most one message is sent per invoice, step, due date and address, however many times the system runs or restarts
Observable: Two copies of the sending process running at the same time over the same due reminders, or a restart in the middle of a run, result in each address having exactly one message per reminder.
Source: implied: never a thing done twice that should happen once

### C-61: If the system dies after a message may have been handed to the provider but before the outcome is recorded, the reminder is shown as "outcome unknown" and is not sent again automatically
Observable: The system is killed after the provider has accepted a message and before the system recorded it; after it restarts, within 1 hour that reminder's history entry says outcome unknown and the customer has received exactly one email.
Source: choice: the request is silent; a missed reminder is cheaper than a duplicate to a customer, and the business can see the unknown outcome

### C-62: A temporary failure to send is retried, up to 3 attempts in all, at least 1 hour apart, only within the 08:00–18:00 window and within the allowed lateness; if all fail the reminder is recorded as "failed"
Observable: The provider answers "try later" at 09:00, 10:00 and 11:00: the history shows 3 attempts and failed, and no 4th attempt. The provider answers "try later" at 09:00 and succeeds at 10:00: the history shows sent.
Source: choice: the request is silent; the provider can fail briefly, and bounded retries recover from that without hammering it or the customer

### C-63: A permanent rejection of a message by the provider (such as address does not exist) is recorded as "failed" and is not retried
Observable: The provider answers that the mailbox does not exist: the history shows failed with that reason after one attempt, the invoice appears in the reminder problems view, and the next hour brings no second attempt.
Source: implied: U-6; retrying a permanent failure only repeats it

### C-64: If the provider reports after acceptance that a message bounced permanently, its history entry becomes "bounced" and the address is marked as bounced for that account
Observable: A bounce report for a message sent at 09:00 arrives at 15:00; at 15:01 the history entry says bounced, and the invoice is in the reminder problems view with the bounced address named.
Source: implied: U-6; acceptance by the provider is not delivery

### C-65: A reminder due to an address marked bounced is skipped and recorded as "address bounced"
Observable: The next reminder to a bounced address is not sent, the history shows skipped, address bounced, and the invoice is in the problems view.
Source: implied: C-64; sending to an address known to bounce harms the sender's reputation

### C-66: The business can clear a bounced mark on an address
Observable: After the business clears the mark in the problems view, reminders still to be sent to that address are sent again.
Source: implied: C-64; a state needs an end

### C-67: When an invoice's due date is changed, its upcoming reminders are recomputed from the new due date and no reminder planned for the old date is sent
Observable: Default schedule, due date moved from 2026-12-10 to 2026-12-20 on 2026-12-08: the invoice then lists upcoming reminders for 2026-12-17, 2026-12-20, 2026-12-27 and 2027-01-03, and nothing arrives on 2026-12-10.
Source: implied: U-8

### C-68: After a due date change, a reminder whose target date is earlier than the date of the change is not sent
Observable: Due date moved on 2026-12-08 from 2026-12-20 to 2026-12-09: the -3 step (2026-12-06) is not sent; the 0 step (2026-12-09) is sent.
Source: implied: U-8; same reasoning as C-39 and C-45

### C-69: A reminder already sent for the old due date does not prevent the same step being sent for the new due date
Observable: The -3 reminder was sent on 2026-12-07 for due date 2026-12-10; the due date moves to 2026-12-20 and the invoice is still unpaid: a -3 reminder is sent on 2026-12-17.
Source: choice: the request is silent; a customer given a new due date should again be warned before it

### C-70: When an invoice becomes unpaid again (a payment or credit reversed), reminders resume with target dates on or after the day it became unpaid
Observable: Invoice recorded paid 2026-12-08, payment reversed 2026-12-12, default schedule due 2026-12-10: the +7 (2026-12-17) and +14 (2026-12-24) reminders are sent; the 2026-12-10 one is not.
Source: implied: U-4

### C-71: When a step is removed from the schedule, its reminders not yet sent are not sent, and ones already sent remain in the history
Observable: Admin removes +14 on 2026-12-12: the invoice's upcoming list no longer has 2026-12-24 and nothing arrives that day.
Source: implied: U-2

### C-72: When a step is added to the schedule, its reminder is sent only if its target date is on or after the day it was added
Observable: Admin adds step +5 on 2026-12-12 to an invoice due 2026-12-10 (target 2026-12-15): it is sent on 2026-12-15. Added on 2026-12-20 instead (invoice due 2026-12-10, +5 = 2026-12-15, in the past): it is not sent.
Source: implied: U-2; same reasoning as C-45

### C-73: A stop-reminders confirmation applies to the address regardless of upper or lower case
Observable: A reminder went to Jane@Example.com; she confirms; a later reminder due to jane@example.com for the same business is skipped as opted out.
Source: implied: U-7; email addresses are typed in different cases

### C-74: Confirming the stop-reminders page a second time changes nothing and shows that reminders are already stopped
Observable: Pressing confirm twice, or opening the link again after confirming, shows the stopped state and records one opt-out with its first date.
Source: implied: U-7; people double-click and revisit

### C-75: Changing the account's time zone never causes a reminder to be sent that was already sent for that invoice, step, due date and address
Observable: A reminder was sent 2026-12-07 at 09:00 Tokyo time; the time zone is changed to America/New_York at 10:00 Tokyo time the same day: no second copy arrives when 2026-12-07 begins in New York.
Source: implied: never a thing done twice that should happen once

### C-76: Reminders pending for an invoice that is deleted are not sent
Observable: A reminder due 2026-12-07 for an invoice deleted on 2026-12-06 is not sent and the invoice's reminders no longer appear anywhere.
Source: implied: "carry on with data that already exists": what is gone cannot be chased

### C-77: Every admin of an account receives a summary email listing each reminder that reached a final problem outcome (as defined for the problems view in C-43) since the previous summary, once each, and none when there are none
Observable: Two invoices have reminders end failed on 2026-12-07; every admin receives one summary the next day that lists both, and the following day's summary, if any, does not list them again. Three attempts and a final "failed" at 11:00 produce one line, not three. A day with no new problems sends no summary.
Source: choice: the request is silent; a business that never opens the problems view should still learn that customers are not getting reminders

### C-78: An account receives at most one summary email per local day
Observable: With problems arising at 09:00, 13:00 and 17:00 on the same local day, the admins receive one summary email for that day, not three.
Source: choice: the request is silent; the loosest rule that prevents a flood is once a day

### C-79: An admin can send a sample reminder whether reminders are On or Off
Observable: With reminders Off, asking for a sample still delivers the sample email to the admin's own address.
Source: implied: U-2; the sample is how the admin checks before switching On

### C-80: A run of the reminder process that is cut short (by a platform execution-time limit, a restart or a crash) loses and duplicates nothing: reminders it did not reach are sent by the next run
Observable: A run is stopped after 1,000 of 10,000 due reminders; the next run completes; afterwards 10,000 reminders have an outcome and no address received a second copy. (The platform's own time limit is not named by the request and is unconfirmed; the behaviour holds whatever it is.)
Source: implied: unattended work runs on a platform that caps how long one execution may take, and "automatic" must survive that

### C-81: Sending is paced to stay within the email provider's sending rate
Observable: With the provider limited to N messages per second (N unconfirmed and set by the operator), 100,000 due reminders at 08:00 are handed to the provider no faster than N per second, and the provider never answers that the limit was exceeded because of this system's pacing. Whatever is still unsent at 18:00 waits for the next window under C-12 and C-57.
Source: implied: U-14; providers cap send rate and daily volume and reject or suspend senders who exceed it

### C-82: A throttling response from the provider delays a reminder and does not count as one of its 3 attempts
Observable: The provider answers "too many requests" three times in a row at 09:00 and then accepts at 09:05: the history shows sent, not failed.
Source: choice: the request is silent; throttling says nothing about the message itself

### C-83: Reminders that were due while the provider was not configured or its credentials were rejected are sent once it is fixed, if still within their lateness limit
Observable: Starting with no provider credentials, then supplying them at 10:00 on 2026-12-07: the 2026-12-07 reminders are sent that day, and no history entry says sent before 10:00.
Source: implied: U-10; a thing it depends on is missing (what it requires before it will run at all)

### C-84: Reminder emails are sent from a domain the operator has authenticated (SPF and DKIM passing and DMARC aligned), with the business's name only as the display name
Observable: The headers of a received reminder show SPF pass, DKIM pass and DMARC pass for the From domain, and the From domain is the operator's, not the business's. (Major mailbox providers have required this of bulk senders since 2024; their exact thresholds are unconfirmed.)
Source: implied: U-10; without it mail from a shared product lands in spam or is rejected, and the system cannot authenticate a domain it does not own

### C-85: A POST to the one-click unsubscribe address in a reminder's headers records the same opt-out as C-37
Observable: A reminder's headers include List-Unsubscribe and List-Unsubscribe-Post; sending the POST to the address in List-Unsubscribe records the opt-out for that address and business with no confirm page, while a GET to it records nothing. (The sender volume above which providers require this is unconfirmed; it is stated for every message.)
Source: implied: U-7; required of bulk senders by major mailbox providers

### C-86: If the business has a postal address on its account, it is shown in the footer of each reminder
Observable: An account with postal address "1 Main St, Springfield" shows it in the footer of its reminders; an account without one shows no empty footer line.
Source: choice: some jurisdictions require a sender's postal address on commercial email, and whether reminders count as commercial is unconfirmed; showing it when known is harmless

### C-87: In an environment not marked as production, every reminder goes only to a configured test inbox and never to a customer's address
Observable: In a staging environment with test inbox test@sandbox.example and a customer address c@x.example with a reminder due: test@sandbox.example receives the message and c@x.example receives nothing; with no test inbox configured, nothing is sent.
Source: implied: U-11

### C-88: The operator can stop all reminder sending across every account, and it stops within 5 minutes
Observable: After the operator sets the stop, no message begins sending more than 5 minutes later and nothing is shown as sent after that; when the operator lifts it, reminders still within the lateness limit of C-57 are sent.
Source: choice: U-10 needs a stop that works; the request gives no time, and 5 minutes is the loosest that still serves someone stopping a mistake

### C-89: The operator can see, per day, the number of reminders sent, failed, skipped, missed, superseded, bounced and of unknown outcome
Observable: After a day with 40 sent, 2 failed and 1 skipped the operator's view shows 40, 2, 1 for that day, and 0 for the others.
Source: implied: U-10

### C-90: Logs and metrics the operator sees never contain a customer's email address or an invoice amount
Observable: After a day's operation, searching the operator's logs and metrics for any customer's address or invoice amount finds nothing.
Source: choice: the request is silent; the operator needs to observe the system, not the customers' data

### C-91: An invoice's reminder history is kept as long as the invoice exists and is deleted with it
Observable: History entries from 3 years ago are still shown on an invoice that still exists; after the invoice is deleted none of its history can be found.
Source: choice: the request is silent; history only has meaning with its invoice, and keeping personal data after its subject is gone is not needed

### C-92: Turning reminders on returns within 5 seconds however many unpaid invoices the account has
Observable: An account with 10,000 unpaid invoices: the admin saves On and sees On within 5 seconds; the reminders then go out when due.
Source: choice: U-14 needs turning on to stay interactive on a large account (a web request cannot wait for thousands of invoices to be examined); the request gives no time and 5 seconds is the loosest that still feels immediate

### C-93: Reminders never change an invoice's status, amounts, due date, customer, billing addresses or payments
Observable: Comparing every invoice before and after a day of reminders, the only differences are reminder history and the upcoming list.
Source: implied: what must not change

### C-94: A failure or outage of the email provider never prevents or noticeably slows issuing, editing, viewing or recording a payment on an invoice
Observable: With the provider refusing every connection, recording a payment on an invoice succeeds and responds as quickly as with the provider working.
Source: implied: what must not change

### C-95: Emails that already go out for invoices today (such as the invoice itself and receipts) are unchanged and are not counted as reminders
Observable: Issuing an invoice sends the same email as before the feature; it does not appear in the reminder history and is not counted in the operator's reminder counts.
Source: implied: what must not change

### C-96: After the feature is added, every existing invoice, customer, payment, user and permission is unchanged
Observable: Row counts and field values of existing invoices, customers, payments and users are identical before and after; every account shows reminders Off.
Source: implied: U-12

### C-97: After going back to the version before the feature, invoices, customers and payments are intact and no reminder is sent
Observable: Roll back, then check existing invoices (unchanged) and observe no reminders sent on a due day.
Source: implied: U-12

### C-98: Every reminder that was due for an invoice that stayed unpaid, unvoided and unpaused, on an account with reminders On, ends as exactly one of sent, failed, skipped (with reason), missed, superseded, bounced or outcome unknown, and none stays pending past its lateness limit or vanishes
Observable: 10,000 due reminders, each to one address, at the end of the lateness limit: 10,000 history entries, each with one final outcome from that list.
Source: implied: never data lost on the way

### C-99: No message reveals any address other than its own recipient's
Observable: An invoice with billing addresses a@x.example and b@y.example: the message to a@x.example shows no b@y.example in any recipient field or the body, and the other way round.
Source: implied: U-3; never someone seeing what they may not see

### C-100: The same rules (paid, void, paused, opted out, bounced, Off, closed) apply to a first attempt, a retry and a catch-up send
Observable: An invoice paid between a failed first attempt at 09:00 and its retry at 10:00 receives no retry; an invoice paused between the two likewise.
Source: implied: never a rule enforced in one path and not another

### C-101: A reminder is shown as sent only if the provider accepted the message
Observable: When the provider rejects the message, or does not answer within its time limit, the history never says sent for it.
Source: implied: never data lost on the way; an untrue "sent" hides a missed reminder

### C-102: A link in a reminder cannot be used to reach any invoice or opt-out other than the one it was made for
Observable: Changing any single character of the invoice link or the stop link in a reminder shows no invoice and records no opt-out; a link from invoice 1042 cannot be turned into invoice 1043's by changing the number.
Source: implied: C-23; never someone seeing what they may not see

### C-103: A provider that is not configured, or whose credentials are rejected, is reported to the operator as a configuration error naming the provider
Observable: Starting with no provider credentials, the operator's view shows an error naming the email provider within 5 minutes, and keeps showing it until the credentials work.
Source: implied: U-10; a thing it depends on is missing (what the runtime requires before it will run at all)

### C-104: After moving forward again to the version with the feature, the reminder settings and history from before going back are still there
Observable: Roll back, then roll forward: each account shows the same On/Off state, schedule, pauses, opt-outs and invoice histories as before the roll back.
Source: implied: U-12

### C-105: A sample reminder is not recorded against any invoice and goes to no customer
Observable: After a sample is sent, no invoice's history has a new entry, the operator's counts are unchanged, and no customer's inbox received anything.
Source: choice: the request is silent; a trial must not look like a real reminder or reach a real customer

### C-106: An invoice's upcoming-reminders list is empty, with the reason shown, while reminders are Off for its account, the invoice is paused, or the account is suspended or closed
Observable: With the account Off, an unpaid invoice due 2026-12-10 shows no upcoming reminders and says reminders are off; with the invoice paused it shows none and says paused.
Source: implied: C-30; the list must tell the truth about what will be sent

### C-107: The reminder settings show the account's time zone and an admin can change it
Observable: The settings show "America/New_York"; the admin changes it to "Asia/Tokyo", saves, and the settings and the upcoming dates on invoices use Japan time from then on.
Source: implied: U-1, C-49; the time zone decides which day a reminder goes out on

### C-108: Saving a schedule applies the whole schedule or none of it; when two admins save at the same time, the account ends with exactly one of the two schedules
Observable: One admin saves steps -3 and 0 while another saves 1 and 2: the settings then show exactly "-3, 0" or exactly "1, 2", never a mixture.
Source: implied: two admins can use the same settings; one rule of the schedule must hold at any time

### C-109: Text entered by users (such as a business name or an invoice number) appears in a reminder as plain text and can never change who the message is addressed to or how it is laid out
Observable: A business named `Acme "Sales", <x@evil.example>` sends a reminder whose From name shows that text literally, whose recipients are only the invoice's billing addresses, and no message is sent to x@evil.example; a name containing `<b>` or a line break shows as characters, not as formatting or a new header.
Source: implied: U-3; user-supplied text goes into message headers and body, and what a stranger can type must not be able to turn the system into a way of mailing other people

### C-110: Every link in a reminder uses https
Observable: Every URL in the body of a reminder starts with "https://".
Source: implied: U-3; the links open invoices and record opt-outs, and mail providers and mail scanners treat plain links as suspect
