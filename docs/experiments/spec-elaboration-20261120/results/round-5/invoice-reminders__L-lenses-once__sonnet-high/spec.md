## Use cases

### U-1: An account owner turns on automatic reminders for the first time, to get unpaid invoices chased without doing it by hand
Flow: The owner opens the invoice-reminder setting, which shows "off". They turn it on. The setting shows the default schedule of reminders at 3 days before the due date, on the due date, 7 days after and 14 days after, and shows that reminders go out at 09:00 in the account's time zone. They save. From then on, each unpaid invoice that is due gets its reminders on those days.
Source: request ("Set up automatic reminders for unpaid invoices")

### U-2: An account owner changes the schedule or turns reminders off, to control how and when customers are chased
Flow: The owner edits the list of day offsets (for example adds 30 days after, removes 3 days before), saves, and sees the new list. Or they turn the setting off and no further reminders go out for any invoice. Later they turn it back on.
Source: implied: "automatic reminders" are something a business must be able to tune and stop; sending email to customers is outward-facing

### U-3: A customer who owes money receives a reminder, to be prompted to pay before or after the due date
Flow: On a scheduled day at 09:00 account time the customer receives one email about one unpaid invoice. It tells them which invoice, how much is still owed, the due date, whether it is due in N days, due today or N days overdue, who it is from, how to pay or view the invoice, and who to reply to with questions.
Source: request

### U-4: A customer pays, and the reminders for that invoice stop, so they are not chased for something already paid
Flow: The customer pays in full (or the owner records a payment). No further reminder email is sent for that invoice, and the invoice's history shows the not-yet-sent reminders as cancelled because the invoice is settled. If they pay only part, reminders continue and show the smaller remaining balance. If they pay at nearly the same moment a reminder is due, the reminder is not sent when the payment was recorded before the email was handed to the email provider.
Source: implied: "unpaid invoices" — an invoice that stops being unpaid must stop being chased

### U-5: An account owner pauses reminders for one invoice, to hold off chasing a customer they are talking to, and resumes them later
Flow: On an invoice the owner chooses "pause reminders". The invoice shows reminders as paused and no reminder goes out for it. Later the owner chooses "resume reminders". Reminders whose day passed during the pause are not sent after resuming; later scheduled ones are.
Source: implied: an automatic process with no per-invoice stop would force the owner to turn it off for all customers

### U-6: An account owner reviews what was sent for an invoice, to know whether and when the customer was reminded
Flow: The owner opens an invoice and sees every reminder step with its day offset, the date it was scheduled for, and its outcome (upcoming, sent, skipped with the reason, cancelled with the reason, failed, unconfirmed, bounced) with the time that outcome happened.
Source: implied: automated outward-facing actions must be observable by the person responsible for them

### U-7: An account owner turns reminders on while invoices already exist, or issues an invoice late, without the customer being flooded
Flow: The owner turns reminders on while some invoices are already past due. Those invoices are not sent reminders for days that already passed; they get only the reminders still ahead of them. The same holds for an invoice issued on a day when some of its reminder days are already past. A customer is never sent several reminders about one invoice in one burst.
Source: implied: "carry on with data that already exists"; first use at the edge

### U-8: An invoice changes while reminders are pending, and the reminders follow the change
Flow: The owner moves an invoice's due date, changes the customer's billing email, voids the invoice, writes it off, or a previously recorded payment is reversed so it is unpaid again. Pending reminders follow the new facts: new dates, new recipient, or none; reminders already sent are never sent again.
Source: implied: a schedule depends on the invoice, and invoices change

### U-9: A reminder cannot be delivered, and the owner and the system cope
Flow: The customer has no billing email, the address is invalid, the address bounces, the email provider is down, or the provider is slow to answer. The reminder is retried or skipped by fixed rules, the history says what happened and why, and the customer is never sent the same reminder twice.
Source: implied: unhappy paths of sending email

### U-10: An operator runs the reminders through restarts, overload and rollback
Flow: The operator releases the feature, finds it off everywhere, lets accounts enable it, watches attempts in the logs, survives the scheduler being down for hours or two workers running at once, and rolls back to the previous version without damaging any invoice.
Source: implied: the operator's work (start, stop, observe, recover, go back)

### U-11: A person who is not allowed, or an account that is not ready, tries to turn reminders on and is refused
Flow: A user without permission to manage billing settings tries to change the schedule and is refused. An owner whose sending domain is not authenticated tries to turn reminders on and is told why it cannot be done yet. An owner enters an invalid schedule and is told which rule it broke; the saved schedule is unchanged.
Source: implied: unhappy paths of configuration

## Clauses

### C-1: Reminders are off by default for every account
Observable: After release, every account that has not turned the setting on shows the setting as "off" and no reminder email is sent for any of its invoices, including accounts that existed before release and accounts created after it.
Source: choice: emailing a business's customers without the business choosing it is outward-facing and cannot be taken back

### C-2: The owner can turn reminders on and off for the whole account
Observable: A single account-level setting shows "on" or "off" and changes when saved; the new state is shown on the next view of the setting.
Source: request

### C-3: The schedule is a list of whole-day offsets from the due date
Observable: Each entry is a whole number of days relative to the invoice's due date: a negative number is days before, 0 is the due date, a positive number is days after. One reminder per entry per invoice.
Source: choice: the request gives no schedule; offsets from the due date are the smallest way to express "before, on and after"

### C-4: The default schedule is -3, 0, 7 and 14
Observable: The first time an owner turns reminders on, the schedule shown and saved is: 3 days before the due date, on the due date, 7 days after, 14 days after, until the owner edits it.
Source: choice: the request gives no schedule; this covers a heads-up, the due date, and two overdue nudges

### C-5: Each schedule offset must be a whole number from -30 to 365 inclusive
Observable: Saving a schedule containing an offset below -30, above 365, or not a whole number is refused with a message naming the offending value.
Source: choice: bounds keep a typo from creating a reminder a year before or a decade after the due date

### C-6: A schedule has between 1 and 10 offsets inclusive
Observable: Saving a schedule with 0 entries, or with 11 or more entries, is refused with a message stating the limit of 10; a schedule with exactly 1 or exactly 10 entries is accepted.
Source: choice: the request gives no limit; 10 caps how often one customer can be emailed about one invoice

### C-7: A schedule may not contain the same offset twice
Observable: Saving a schedule with a repeated offset is refused with a message naming the repeated value.
Source: choice: a duplicate offset would mean two reminders on the same day

### C-8: A refused schedule leaves the saved settings unchanged
Observable: After any refusal under C-5, C-6 or C-7, viewing the setting shows exactly the schedule and on/off state that were saved before the attempt.
Source: implied: U-11

### C-9: Only users permitted to manage billing settings can change reminder settings or pause and resume an invoice's reminders
Observable: A user without that permission who tries to change the on/off state, the schedule, or an invoice's pause state, through the screen or through any programmatic interface, is refused with a permission-denied message and nothing changes. The same user can still see the settings and the invoice history if they may view invoices.
Source: implied: U-11; a rule enforced in one path must be enforced in every path

### C-10: Every change to the reminder settings is recorded with who and when
Observable: For each change to the on/off state or the schedule, the account shows a record of the user, the time, and the old and new values.
Source: choice: outward-facing automation needs an answer to "who turned this on"

### C-11: Reminders cannot be turned on until the account's sending domain is authenticated
Observable: Turning reminders on while the account's email-sending domain has not passed the email provider's sender-authentication check (SPF and DKIM) is refused with a message saying the domain must be verified first; the setting stays "off". Whether the provider's exact check names are SPF and DKIM is unconfirmed for the chosen provider.
Source: implied: runtime rule — mail providers and major mailbox services reject or junk unauthenticated sender domains, so this cannot ship beyond development without it

### C-12: A reminder is scheduled for a calendar day, counted in the account's time zone
Observable: The reminder for offset N goes out on the calendar day (in the account's time zone) that is the invoice's due date plus N days.
Source: implied: due dates are calendar days, and "3 days before" has to mean one specific day

### C-13: Reminders go out at 09:00 in the account's time zone, or in UTC if the account has no time zone
Observable: A reminder scheduled for a day is not sent before 09:00 local time on that day. If 09:00 does not exist that day because of a clock change, it is sent at the first moment after that time that does exist.
Source: choice: the request gives no time; morning in the customer-paying business's own time is the loosest sensible default

### C-14: A reminder is never sent before its scheduled time
Observable: No reminder email has a send time earlier than the 09:00 of its scheduled day in the account's time zone.
Source: implied: C-12 and C-13

### C-15: Under normal load a reminder is sent within 15 minutes after its scheduled time
Observable: When the system is running and the provider is answering, 15 minutes after the scheduled time the step shows as sent.
Source: choice: bounds the scheduler's granularity so "09:00" means roughly 09:00

### C-16: When up to 10,000 reminders are due at the same moment, all are sent within 60 minutes after it
Observable: With 10,000 steps due at 09:00 and the provider answering, none is still unsent at 10:00. The figure 10,000 is a chosen sizing, not a confirmed requirement.
Source: choice: the largest case; many accounts share 09:00 in the same time zone

### C-17: An invoice is reminded only while it is issued and has a balance due greater than zero
Observable: Reminders are sent for an invoice that has been issued and whose remaining balance is above zero. No reminder is sent for an invoice that is in any of these states: draft (not yet issued), paid in full, void or cancelled, written off or marked uncollectible, or reduced to a zero balance by credits or refunds.
Source: implied: "unpaid invoices"; the states are chosen because the request does not list them and this is every state in which nothing is owed or nothing has been demanded

### C-18: A partly paid invoice is still reminded, and shows the remaining balance
Observable: After a partial payment, later reminders for that invoice are sent and state the remaining balance, not the original total.
Source: implied: "unpaid" includes partly paid; U-4

### C-19: A payment that has been started but not yet cleared stops reminders while it is in progress
Observable: While an invoice has a payment recorded as processing or pending, no reminder is sent for it. If that payment fails, reminders resume with the next scheduled step; steps whose time passed meanwhile are skipped under C-30.
Source: choice: reminding someone who has just paid is worse than a short delay

### C-20: An invoice with no due date gets no reminders
Observable: The invoice's history shows no steps scheduled and states that reminders need a due date. When a due date is later set, steps are scheduled under C-31.
Source: choice: all offsets are measured from the due date, and the request gives no other anchor

### C-21: The invoice's state is checked immediately before each send attempt
Observable: If the invoice stopped being eligible (C-17, C-19), was paused (C-33), or the account setting was turned off after the step became due but before the email was handed to the email provider, no email is sent for that attempt. A payment recorded after the hand-off cannot recall the email, and the email is delivered.
Source: implied: U-4, where two events race

### C-22: When an invoice becomes settled, its pending reminders are cancelled
Observable: The history shows each not-yet-sent step with the outcome "cancelled" and the reason (paid, void, written off, credited) and no email is sent for it.
Source: implied: U-4

### C-23: If a settled invoice becomes unpaid again, reminders resume for steps still ahead and never repeat steps already sent
Observable: After a payment reversal on a previously paid invoice, steps whose scheduled time is still in the future are sent as scheduled; steps whose time passed are skipped under C-30; steps previously sent are not sent again.
Source: implied: U-8

### C-24: Each step of an invoice is delivered at most once
Observable: For any one invoice and offset, the customer receives at most one email in total, including when two workers evaluate the same step simultaneously, when a worker restarts partway through, and when the scheduler runs twice. A step is identified by the invoice and its offset.
Source: implied: "a thing done twice that should happen once"; parts that meet

### C-25: A definite failure to hand off an email is retried up to 3 more times, 1 hour apart
Observable: When the provider refuses or rejects the email, or is unreachable, the attempt is retried 1 hour later, up to 3 retries (4 attempts in all); if the fourth also fails the step shows "failed". If any attempt succeeds, the remaining retries are not made.
Source: choice: the request is silent; bounded retries cover short provider outages without chasing forever

### C-26: A provider rate-limit answer counts as a definite failure
Observable: When the provider answers that the account is being rate-limited, the step is retried under C-25 and not marked failed on the first answer.
Source: implied: runtime rule — email providers cap sending rate and answer with a throttle response

### C-27: An attempt whose outcome is unknown is not retried
Observable: When the provider does not answer in time and it cannot be known whether the email was accepted, the step shows "unconfirmed", no second email is sent for it, and no automatic retry is made.
Source: choice: for a customer-facing payment demand, a possible silent miss is better than a possible duplicate

### C-28: A step more than 24 hours past its scheduled time is skipped as missed
Observable: When the system first handles a due step and its scheduled time is more than 24 hours ago (for example after the scheduler was down), no email is sent and the step shows "skipped: missed". A step due 24 hours ago or less is sent.
Source: choice: a "3 days before" reminder arriving after the due date is misleading

### C-29: When more than one step of an invoice is due at the same time, only the latest is sent
Observable: The latest-due step is sent; each earlier one shows "skipped: superseded" and sends nothing. The customer gets one email for that invoice in that run.
Source: implied: U-7, U-10; catch-up after an outage must not produce a burst

### C-30: Steps whose time has already passed when reminders begin or are rescheduled are skipped
Observable: When a trigger below happens, every unsent step of an affected invoice whose scheduled time is already past at that moment shows "skipped: before start" and is never sent later, however recent it is. The triggers are: the owner turns reminders on; the owner saves a changed schedule; the account's time zone changes; the invoice is issued; the invoice's due date is set or changed; the invoice's pause is ended; the invoice's payment in progress fails; the invoice is reopened (C-23). Steps still in the future are scheduled as normal.
Source: choice: nothing should be sent for a day that was missed before the owner or invoice reached the state that makes reminders apply, so no customer is flooded

### C-31: Changing an invoice's due date recomputes its unsent steps
Observable: Unsent steps move to the new scheduled days; the history shows the new dates; steps already sent keep their record and are not sent again for the same offset.
Source: implied: U-8

### C-32: Changing the schedule applies to unsent steps on all invoices, and an offset already sent is not sent again
Observable: After saving, an offset removed from the schedule shows as "cancelled" on invoices where it was unsent; an offset added is scheduled for invoices still ahead of it under C-30; an offset that was already sent on an invoice is not sent again even if it stays in the list. Because a step is identified by its offset, changing 7 to 8 adds a new step and does not undo the sent 7.
Source: implied: U-2

### C-33: The owner can pause and resume reminders on a single invoice
Observable: A paused invoice shows "reminders paused", sends nothing while paused, and resumes on request. Steps whose time passes during the pause show "skipped: paused" and are not sent on resuming; steps still in the future are sent as scheduled.
Source: implied: U-5

### C-34: Turning reminders off stops all pending reminders, and turning on again follows C-30
Observable: After turning off, no further reminder is handed to the provider for any invoice of the account; unsent steps are shown as "cancelled: reminders turned off". An email already handed to the provider before the change is still delivered.
Source: implied: U-2; the operator's stop

### C-35: A reminder goes to the billing email address recorded on the invoice, and only to it
Observable: The email's recipient is exactly the invoice's billing contact email address as it stands when the attempt is made, so a changed address takes effect for all later steps. No other person is copied or blind-copied.
Source: implied: "reminders for invoices" go to whoever the invoice is billed to; never disclose a customer's debt to anyone else

### C-36: A step with no usable billing email is skipped
Observable: When the invoice has no billing email address, or the address is not a syntactically valid email address, the step shows "skipped: no recipient" and no email is sent. Once a valid address is set, later steps are sent; skipped steps are not sent late.
Source: implied: U-9

### C-37: After an address bounces permanently, no more reminders go to it for that invoice
Observable: When the provider reports a permanent delivery failure (hard bounce), the step shows "bounced", the invoice's remaining steps show "skipped: bounced", and sending resumes only after the invoice's billing email address is changed.
Source: choice: repeated sends to a dead address damage the sender's standing with mail providers

### C-38: Each reminder email is about exactly one invoice
Observable: A customer with several unpaid invoices receives a separate email per invoice, not one combined email.
Source: choice: simplest unit that keeps each invoice's state, retries and history independent

### C-39: A reminder email contains the invoice number, the amount still owed, the due date, how the due date relates to today, the sender's name, a way to pay or view the invoice, and a contact for replies
Observable: All seven parts appear in the received email. The amount is the remaining balance at the time of sending (C-18), with its currency, to the currency's usual number of decimal places. The due date is shown in a form that cannot be misread in another country's convention.
Source: implied: U-3

### C-40: The email states whether the invoice is due in N days, due today, or N days overdue
Observable: For an offset below 0 it says it is due in that many days; for 0 it says it is due today; for above 0 it says it is that many days overdue; where N is counted in calendar days in the account's time zone on the send day.
Source: implied: U-3; the three situations of the schedule

### C-41: The way to pay in the email works for that invoice only and stays valid while the invoice is unpaid
Observable: Following the link from a reminder opens that one invoice, and does not give access to the customer's or the account's other invoices. The link still works on the day of the last scheduled reminder and any day the invoice remains unpaid.
Source: implied: a reminder with a dead link defeats its purpose; a link that exposes more than one invoice shows what may not be shown

### C-42: Replies to a reminder go to the account's billing contact address
Observable: Replying to the email addresses the account's billing contact address, not a no-reply address.
Source: implied: a customer who disputes or has a question must be able to reach the business

### C-43: Reminder emails are in English
Observable: All fixed text in the email is in English.
Source: choice: the request names no language

### C-44: Each invoice shows a reminder history
Observable: For each step of the schedule the owner sees its offset, scheduled date, and one outcome: upcoming, sent, skipped (with reason), cancelled (with reason), failed, unconfirmed, or bounced, and the time the outcome was recorded when it is not upcoming. Skip reasons are: missed, superseded, before start, paused, no recipient, bounced. Cancel reasons are: paid, void, written off, credited, reminders turned off, offset removed.
Source: implied: U-6

### C-45: Failed and unconfirmed steps are visibly set apart from sent ones
Observable: In the invoice history a step in the states failed, unconfirmed or bounced is marked differently from a sent step so it can be found at a glance.
Source: implied: U-9; the owner must be able to act, for example by contacting the customer

### C-46: Reminder history is visible only within its own account and only to users who may view that invoice
Observable: A user of another account, or a user without permission to view invoices, cannot see or retrieve an invoice's reminder history or any reminder email content.
Source: implied: "someone seeing what they may not see"

### C-47: Reminder history is kept as long as the invoice exists
Observable: Sent and skipped steps stay visible on the invoice after it is paid, voided or written off, and are removed only when the invoice itself is removed.
Source: choice: the request gives no retention; keeping it for the life of the invoice answers any later "did we remind them"

### C-48: Every send attempt is logged for the operator
Observable: Each attempt writes a log entry with the time, account, invoice, offset, attempt number and outcome. The entry contains no pay-link and no full email body.
Source: implied: U-10, the operator observes; choice: payment links in logs would give access to anyone who reads logs

### C-49: Sending a reminder does not change the invoice
Observable: After a reminder is sent, skipped or failed, the invoice's status, amounts, due date, payments and the customer's record are the same as before.
Source: implied: what must not change

### C-50: Existing invoice behaviour and other emails are unchanged
Observable: Issuing, editing, paying, voiding and writing off invoices, and the emails the system already sends about invoices, behave and look exactly as before the release, whether reminders are on or off.
Source: implied: every existing rule this must keep

### C-51: Rolling back to the version before reminders loses no invoice data and sends no reminders
Observable: After rollback, all invoices and payments are as they were, no reminder email is sent, and re-releasing finds the earlier history intact; steps that became past-due while rolled back are skipped under C-28 and C-30, not sent.
Source: implied: the operator going back to the version before
