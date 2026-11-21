# Specification: automatic reminders for unpaid invoices

Terms used below. "Account" is the business that issues invoices. "Owner" is a person allowed to manage the account's
settings. "Customer" is the person an invoice is addressed to. "Outstanding balance" is the invoice total minus the
payments recorded against it. "Unpaid" means issued to the customer, not voided, and with an outstanding balance
above zero.

## Use cases

### U-1: Owner turns on automatic reminders, to get unpaid invoices chased without doing it by hand
Flow: The owner opens the account's reminder settings and sees reminders are off. They turn reminders on. The
settings show reminders are on, together with the current schedule values. From then on, customers with unpaid
invoices receive reminders on their own, and the owner takes no further action.
Source: request

### U-2: Owner sets the reminder schedule, to match how they want to chase customers
Flow: The owner changes how many days after (or before) the due date the first reminder goes, how many days pass
between reminders, and the most reminders one invoice may get. They save. A value outside the allowed range is
refused with a message that names the setting, and nothing is saved. A valid set is saved and shown back.
Source: implied: "set up" reminders needs some way to say when they go; the request gives no schedule

### U-3: Customer with an unpaid invoice receives reminders until they pay
Flow: An invoice becomes due. On the scheduled day the customer receives an email that identifies the invoice, the
amount still owed and the due date. If still unpaid, they receive further reminders at the set interval, up to the
maximum. When the customer pays, no more arrive.
Source: request

### U-4: Customer who has paid, partly paid, or had the invoice cancelled is not chased wrongly
Flow: A customer pays in full the morning of the day a reminder is due: no reminder arrives. A customer pays part:
reminders continue and state only the balance still owed. An invoice is voided, or is still a draft: no reminder
arrives.
Source: implied: "unpaid invoices" excludes every invoice that is not owed

### U-5: Owner stops reminders for one invoice, and starts them again
Flow: The owner opens an invoice, pauses its reminders, and sees it marked paused; none go out. Later they resume;
the invoice goes back into the schedule.
Source: implied: an owner who negotiated a payment plan or is in a dispute must be able to stop automatic chasing of
that invoice; "automatic" must not mean "uncontrollable"

### U-6: Owner checks what reminders went out for an invoice
Flow: The owner opens an invoice and sees every reminder attempt with its date and outcome (sent, failed, or not sent
with a reason), and either the date of the next reminder or the reason there is none.
Source: implied: without this the owner cannot know whether the automatic process worked

### U-7: First time: owner turns reminders on while many invoices are already overdue
Flow: The account has invoices that are 5, 40 and 200 days overdue. The owner turns reminders on. On the next run each
of those customers receives one reminder, not the whole sequence a late start would imply. Later reminders follow at
the interval.
Source: implied: "the first time" and "carry on with the data that exists today"; reminders must not flood customers

### U-8: Repeated: the reminder process runs again the same day, twice at once, or after a restart
Flow: The process runs at 09:00, again at 09:05, and a second copy runs alongside the first. The operator restarts it
at 09:10. Each customer still receives one reminder for each reminder that was due, in total.
Source: implied: anything automatic and periodic is rerun; a repeated reminder to a customer is a visible fault

### U-9: Empty and largest cases
Flow: With no unpaid invoices, a run sends nothing and finishes without an error. With 10,000 invoices that all fall
due on the same day, every one gets its reminder that day, and one bad address does not stop the others.
Source: implied: the empty case and the largest case

### U-10: Reminder cannot be delivered
Flow: An invoice's customer has no email address, or the email service refuses or is down. The owner sees the reminder
recorded as not sent, with the reason. The process tries again on later days up to a limit, then stops for that
invoice and marks it as needing attention. Other invoices are unaffected.
Source: implied: unhappy path; the request assumes delivery works

### U-11: Someone without permission tries to change reminder settings
Flow: A person who is not an owner tries to turn reminders on or off, change the schedule, or pause an invoice's
reminders. The action is refused and nothing changes.
Source: implied: reminders go out to the account's customers in its name

### U-12: Invoice changes after reminders began
Flow: The due date is moved later, an invoice is paid then reopened, the owner changes the schedule, or the owner turns
reminders off and later on again. Reminders already sent stay on record; later ones follow the new facts and at most
one per invoice goes out on any one day.
Source: implied: invoices and settings are edited during the life of an invoice

### U-13: Operator deploys, restarts, and rolls back
Flow: The operator releases the version with reminders: existing invoices and accounts are unchanged and no customer
is emailed until an owner turns reminders on. The operator starts the process; email delivery is or is not set up. The
process is down for two days and restarted: due reminders go out once each. The operator rolls back to the version
before and later upgrades again: invoices are intact and no reminder is sent twice.
Source: implied: "start, restart, configure, carry on with existing data, go back to the version before"

## Clauses

### C-1: An owner can turn automatic reminders on and off for the account
Observable: In the reminder settings the owner switches reminders on, and the settings then show "on"; they switch
them off, and the settings show "off". The state is the same after the owner leaves and returns.
Source: request

### C-2: Reminders are off for every account until an owner turns them on
Observable: Immediately after the feature is released, or for a new account, the settings show reminders off and no
customer receives any reminder, even for invoices long overdue.
Source: choice: emailing customers on behalf of the business without the owner's say-so is the riskier default

### C-3: Once on, reminders go out without anyone taking a manual step
Observable: With reminders on, an unpaid invoice that reaches its reminder date results in an email to the customer
that day without anyone pressing a button or running a command.
Source: request

### C-4: The owner can set three schedule values: first-reminder offset, interval, and maximum count
Observable: The settings accept and show back (a) the offset in whole days from the due date at which the first
reminder is due, where a negative number means before the due date, (b) the interval in whole days between reminders,
and (c) the maximum number of reminders per invoice.
Source: implied: U-2; the request does not say when reminders go

### C-5: Until the owner changes them, the schedule values are offset 1, interval 7, maximum 3
Observable: An account that has never saved a schedule shows offset 1, interval 7, maximum 3.
Source: choice: a first nudge the day after the due date and a weekly repeat are customary and not pushy

### C-6: The offset is accepted from -30 to 90 days and refused outside that range
Observable: Offsets -30, 0 and 90 are accepted. Offsets -31 and 91 are refused. A non-whole number such as 1.5 is
refused.
Source: choice: the request gives no limit; a bounded range keeps the schedule meaningful

### C-7: The interval is accepted from 1 to 90 days and refused outside that range
Observable: Intervals 1 and 90 are accepted. Intervals 0, -1 and 91 are refused. A non-whole number is refused.
Source: choice: a minimum of 1 day matches the rule that an invoice gets at most one reminder a day

### C-8: The maximum count is accepted from 1 to 12 and refused outside that range
Observable: Maximums 1 and 12 are accepted. Maximums 0 and 13 are refused. A non-whole number is refused.
Source: choice: the request gives no limit; at least one reminder must be possible and the count must be bounded

### C-9: A refused schedule value is refused with a message that names the setting
Observable: Submitting an interval of 0 returns a message that identifies the interval as the problem. The same holds
for the offset and the maximum. A missing value is refused the same way.
Source: implied: U-2, a refused action must say what to fix

### C-10: A refused schedule save leaves every saved schedule value unchanged
Observable: With offset 1, interval 7, maximum 3 saved, submitting offset 2, interval 0, maximum 5 is refused, and the
settings still show 1, 7, 3.
Source: implied: U-2

### C-11: A reminder becomes due on the later of the due date plus the offset, and the interval after the previous reminder was sent
Observable: With offset 1 and interval 7, an invoice due 1 March whose first reminder was sent on 2 March becomes due
for its second reminder on 9 March. For the first reminder, only the due-date-plus-offset part applies. For an invoice
due 1 March with offset -3, the first reminder is due on 26 February (2026 is not a leap year).
Source: choice: the stated rule gives a regular rhythm and keeps late starts and delays from bunching reminders

### C-12: A reminder is never sent before the date on which it becomes due
Observable: With offset 1, an invoice due 1 March receives nothing on 1 March and nothing before it.
Source: request: reminders are scheduled; implied: the schedule values are meaningful

### C-13: A due reminder is sent the day it becomes due
Observable: With reminders on, offset 1 and an invoice due 1 March still unpaid, the customer has received the first
reminder by the end of 2 March.
Source: request

### C-14: An invoice gets at most one reminder on any one calendar day
Observable: However many times the process runs and however many reminders are overdue, a customer receives no more than
one reminder for the same invoice in a calendar day.
Source: choice: protects customers from bursts; a day is the finest unit the schedule uses

### C-15: An invoice that missed its reminders (reminders off, process down, or paused) gets one reminder when it is next processed, not the missed set
Observable: An invoice 200 days overdue with offset 1, interval 7, maximum 3 and no reminders sent yet, when reminders
are first turned on receives exactly one reminder on the first run, none on the next 6 days, and a second reminder 7
days after the first.
Source: implied: U-7 and U-13; the first-time and carry-on-with-existing-data cases

### C-16: The number of reminders an invoice receives never exceeds the maximum count
Observable: With maximum 3, an invoice that stays unpaid indefinitely receives exactly 3 reminders and nothing after.
Lowering the maximum to 2 after 2 have been sent means no more are sent.
Source: request: setting up reminders must not mean endless reminders; implied: C-8

### C-17: Only reminders that were sent count toward the maximum
Observable: A reminder that failed or was not sent (see the delivery clauses) is not counted. With maximum 3, an invoice
that had 2 failed attempts and then 3 successful sends has received 3 reminders.
Source: implied: U-10; the maximum limits what customers get

### C-18: A fully paid invoice receives no further reminders
Observable: After the invoice is recorded as paid, no reminder arrives on any later day, including days on which one
would otherwise have been due.
Source: request: "unpaid invoices"

### C-19: Payment status is checked at the moment of sending
Observable: If the invoice is recorded as paid at 09:00 and a reminder was due that day, no reminder is sent at 09:01
or later, even if the process had already selected the invoice before 09:00.
Source: implied: U-4

### C-20: An invoice with an outstanding balance of zero or less is treated as paid
Observable: An invoice whose recorded payments equal or exceed its total receives no reminder.
Source: implied: "unpaid" is defined by what is still owed

### C-21: A partly paid invoice continues to receive reminders
Observable: An invoice of 100.00 with 40.00 paid still receives its reminders on schedule.
Source: implied: U-4; it is still unpaid in part

### C-22: A voided invoice receives no reminders
Observable: After an invoice is voided, no reminder arrives for it on any later day.
Source: implied: U-4; a voided invoice is not owed

### C-23: An invoice that has not been issued to the customer (a draft) receives no reminders
Observable: A draft invoice with a past due date receives nothing. Once it is issued and is unpaid, it follows the
schedule.
Source: implied: U-4; the customer has not been told of the invoice

### C-24: An invoice with no due date receives no reminders, and the reason is shown
Observable: The invoice's reminder view states that there is no due date and no reminder has been sent. Once a due date
is added, it follows the schedule.
Source: choice: the schedule is based on the due date; an invoice with none cannot be scheduled

### C-25: The reminder is emailed to the customer's address on the invoice
Observable: The message arrives at the customer email address recorded for that invoice.
Source: choice: email is the channel for reaching an invoice's customer; the request does not name one

### C-26: The reminder identifies the invoice and its due date
Observable: The message contains the invoice number and the due date.
Source: implied: U-3; the customer needs to know which invoice is being raised

### C-27: The reminder states the amount still owed, with its currency
Observable: For an invoice of 100.00 USD with 40.00 USD paid, the message states 60.00 USD as the amount owed, not
100.00.
Source: implied: U-3 and U-4; a reminder with the wrong amount causes disputes

### C-28: The reminder names the account that issued the invoice
Observable: The message names the business that issued the invoice.
Source: implied: U-3; the customer needs to know who is asking for payment

### C-29: A customer with no email address is not sent a reminder and the reason is recorded
Observable: The invoice's reminder view shows the reminder as not sent because there is no email address for the
customer. The invoice is processed again on the next run, and a reminder goes out then if an address has been added.
Source: implied: U-10

### C-30: A failed delivery is recorded as failed, with its date
Observable: When the email service refuses or fails to deliver, the invoice's reminder view shows an attempt dated that
day with the outcome "failed". It is never shown as sent.
Source: implied: U-10

### C-31: A failed reminder is retried on later days, up to 3 attempts in a row
Observable: If delivery fails on 2 March, one new attempt is made on 3 March, and one on 4 March; there are no more
than 3 attempts in a row without a success.
Source: choice: bounds the effort on an address that does not work, while allowing for a brief outage

### C-32: After 3 failed attempts in a row, automatic reminders stop for that invoice and the invoice is marked as needing attention
Observable: After the third consecutive failure, no more reminders are attempted for the invoice, and the invoice's
reminder view shows that delivery failed and needs attention. Resuming the invoice's reminders (C-36) starts attempts
again.
Source: choice: avoids retrying a dead address forever and tells the owner something is wrong

### C-33: A failure for one invoice does not prevent reminders for others
Observable: With 100 invoices due on the same day and the customer of one having an address that the email service
refuses, the other 99 customers receive their reminders that day.
Source: implied: U-9, U-10

### C-34: When email delivery has not been set up, no attempt is made, nothing is recorded as sent, and the settings say so
Observable: With reminders on and no email delivery set up, the reminder settings show a notice that reminders cannot
be delivered. No invoice shows a sent reminder. After delivery is set up, due reminders go out under the normal rules.
Source: implied: U-13; the operator may start the process before configuring delivery

### C-35: The owner can pause the reminders of one invoice
Observable: After pausing, the invoice is shown as paused and receives no reminders on days when one would otherwise
be due. Other invoices are unaffected.
Source: implied: U-5

### C-36: The owner can resume the reminders of a paused invoice
Observable: After resuming, the invoice is no longer shown as paused and is processed under the normal schedule rules,
which for an invoice already past due means at most one reminder on the next run.
Source: implied: U-5

### C-37: An invoice's reminder view lists every attempt with its date and outcome
Observable: Opening an invoice shows each reminder attempt in date order with its date and one outcome: sent, failed,
or not sent with a reason. An invoice with no attempts shows an empty list, not an error.
Source: implied: U-6

### C-38: An invoice's reminder view shows the date of the next reminder, or the reason there is none
Observable: An unpaid invoice that is due for a reminder on 9 March shows 9 March. A paid invoice, a paused invoice, an
invoice that has reached the maximum count, and an invoice needing attention each show the matching reason in place
of a date.
Source: implied: U-6

### C-39: Reminder history is kept for as long as the invoice exists
Observable: Attempts made months earlier are still listed in the invoice's reminder view.
Source: implied: U-6, U-13; history is what prevents repeats after a rollback

### C-40: Changing the schedule affects only reminders not yet sent
Observable: With 2 reminders already sent, changing the interval from 7 to 14 leaves the 2 sent reminders in the
history and the count, and the third becomes due 14 days after the second was sent.
Source: implied: U-12

### C-41: Changing an invoice's due date moves the first reminder that has not yet been sent
Observable: With offset 1 and no reminders sent, moving the due date from 1 March to 15 March means the first
reminder becomes due on 16 March, and nothing is sent on 2 March.
Source: implied: U-12; the schedule is based on the due date

### C-42: Reopening a paid invoice that has an outstanding balance again brings it back into the schedule with its earlier count kept
Observable: An invoice with 1 reminder sent that is paid and then reopened with the balance outstanding is eligible
for up to (maximum - 1) further reminders.
Source: implied: U-12

### C-43: Turning reminders off stops all reminders, including those due the same day
Observable: After the owner turns reminders off at 09:00, no customer receives a reminder from that moment, including
for reminders that were due that day. The history is kept.
Source: request: setting up reminders implies they can be undone; implied: U-1

### C-44: Turning reminders on again does not resend earlier reminders
Observable: Reminders sent before the switch-off remain in the history and count toward the maximum. An invoice that
had 3 of 3 sent receives nothing further after switching back on.
Source: implied: U-12

### C-45: Each due reminder is sent exactly once however many times, or in how many copies, the process runs
Observable: Running the process 5 times in a row, or running two copies at the same moment, produces one email per
due reminder per invoice, and one history entry.
Source: implied: U-8

### C-46: A restart or a period of downtime loses no due reminder and repeats none
Observable: After the process is down on 2 March and 3 March and restarted on 4 March, each invoice that was due a
reminder receives one on 4 March (per C-15) and no invoice receives one it had already received.
Source: implied: U-8, U-13

### C-47: With nothing to remind about, a run sends nothing and does not fail
Observable: With no unpaid invoices, or with reminders on and no invoice due, no email is sent and no error is shown.
Source: implied: U-9, the empty case

### C-48: At least 10,000 invoices that fall due on the same day all get their reminders that day
Observable: With 10,000 unpaid invoices, all with a first reminder due on 2 March, and valid addresses, all 10,000
customers receive one reminder by the end of 2 March.
Source: choice: a concrete load target for the largest case; the request gives no size

### C-49: Dates are judged in the account's time zone, and in UTC when the account has none
Observable: For an account in a zone eight hours behind UTC, an invoice due 1 March with offset 1 is not sent a reminder
at 23:00 on 1 March local time even though it is already 2 March in UTC. For an account with no zone, the date
is the UTC date.
Source: choice: due dates are calendar dates; a rule is needed for which calendar

### C-50: Only owners can turn reminders on or off or change the schedule
Observable: A person who is not an owner who tries any of these is refused with a message saying they lack permission,
and the settings are unchanged.
Source: implied: U-11

### C-51: Only owners can pause or resume an invoice's reminders
Observable: A person who is not an owner who tries is refused with a message saying they lack permission, and the
invoice's state is unchanged.
Source: implied: U-11

### C-52: Sending a reminder does not change the invoice's status, amount or due date
Observable: Before and after a reminder is sent, the invoice shows the same status, total, payments and due date.
Source: implied: existing invoices must keep their behaviour

### C-53: Invoices created before the feature existed work with reminders with no conversion step
Observable: An invoice created before the release, with a due date and unpaid, receives reminders under the normal rules
once reminders are on, without anyone editing it.
Source: implied: U-13, carry on with the data that exists today

### C-54: Releasing the feature changes no existing invoice, payment or account data
Observable: Every existing invoice shows the same status, amounts, payments and due date after the release as before.
Source: implied: U-13

### C-55: Rolling back to the version before leaves all invoices usable
Observable: After rollback, existing invoices can be opened, edited, paid and voided as before, and no error refers to
reminders.
Source: implied: U-13, go back to the version before

### C-56: After rollback and a later upgrade, reminders already sent are not sent again
Observable: An invoice that had 2 reminders sent before rollback shows those 2 in its history after the second
upgrade, and neither is resent.
Source: implied: U-13; C-39
