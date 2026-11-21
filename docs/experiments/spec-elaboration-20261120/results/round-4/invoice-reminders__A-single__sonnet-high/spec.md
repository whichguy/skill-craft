# Specification: automatic reminders for unpaid invoices

Terms used below. **Owner**: the business user who issues invoices and manages the reminder settings. **Customer**: the person an invoice is addressed to. **Operator**: the person who runs and maintains the system. **Step**: one reminder in the schedule, identified by its offset, the number of days after the invoice's due date on which it is sent. **Step date**: the calendar date of the due date plus the step's offset, in the configured time zone. **Overdue**: the current date is later than the due date.

The working directory holds no existing product, so there is no earlier reminder behaviour to preserve. The invoices, customer contact addresses and payment records are assumed to exist already, and the clauses protect them.

## Use cases

### U-1: Customer with an overdue unpaid invoice is reminded automatically, to be prompted to pay
Flow: The owner has reminders on with the default schedule. An invoice for a customer is due 2026-03-01 and stays unpaid. On 2026-03-02, 2026-03-08 and 2026-03-15, at the send time, the customer receives one message each time about that invoice. The message shows the invoice number, the outstanding amount with its currency and the due date. After the third message nothing more is sent for that invoice, though it is still unpaid.
Source: request

### U-2: Customer pays and stops being reminded
Flow: A customer has received the first reminder for an invoice. The invoice is then recorded as fully paid, including on the morning of a step date before the send time. No further reminder arrives for it.
Source: implied: "unpaid invoices" in the request; a reminder for a paid invoice would be wrong

### U-3: Customer who paid part of an invoice is reminded of what is left
Flow: An invoice for 1,000.00 USD has 400.00 USD paid against it and is overdue. The next reminder states an outstanding amount of 600.00 USD.
Source: implied: "unpaid" covers an invoice that is only partly paid

### U-4: Owner switches reminders on for the first time
Flow: After the feature is installed, the owner sees that reminders are off. No customer has been contacted. The owner turns reminders on and sees that they are on, with the default schedule (1, 7 and 14 days after the due date), the default send time (09:00) and the default time zone (UTC). From the next send time, overdue unpaid invoices are reminded.
Source: request ("set up"); implied: the owner must be able to start the feature

### U-5: Owner changes when reminders go out
Flow: The owner sets the schedule to 2 and 10 days after the due date, the send time to 08:30 and the time zone to Europe/London. The owner then sees those settings. An invoice due 2026-03-01 is reminded on 2026-03-03 and 2026-03-11 at 08:30 London time. The settings are still there after a restart.
Source: implied: "set up" means the owner can configure it; a fixed schedule would not suit every business

### U-6: Owner enters settings that cannot work
Flow: The owner tries a schedule with 11 steps, an offset of 0, 366 or 1.5, a repeated or descending offset, a send time of 25:00 or a time zone that does not exist. The change is refused with a message naming the faulty setting, and the earlier settings stay in force.
Source: implied: every configurable value has limits

### U-7: Owner pauses and resumes reminders
Flow: The owner turns reminders off. From that moment no reminder is sent, even one due later that day. Days later the owner turns them on again. Each overdue unpaid invoice receives at most one reminder at the next send time, not one for every step date missed.
Source: implied: anything that sends mail to customers must be stoppable; "carry on with the data that exists today"

### U-8: Owner stops reminders for one invoice, for example one in dispute, and resumes them later
Flow: The owner marks one invoice "no reminders" and sees that mark on the invoice. That invoice gets no reminders while the mark stands and other invoices are unaffected. The owner later removes the mark and the invoice is eligible again.
Source: implied: a customer who disputes an invoice should not be chased by an automatic message

### U-9: Owner reviews what was sent
Flow: The owner opens the reminder history for an invoice. For each reminder it lists when it was handled, the address used, and whether it was sent, failed or skipped, with the reason for a failure or skip. The owner uses it to answer "did the customer get chased?".
Source: implied: an automatic action that contacts customers must be auditable

### U-10: An invoice that cannot or must not be reminded
Flow: Invoices that are drafts, void or cancelled, with no due date, with nothing owing (zero or credit balance), or paid get no reminders. An unpaid overdue invoice whose customer has no usable email address gets none either, and the owner sees a skipped entry saying why.
Source: implied: the request's "unpaid invoices" leaves open which unpaid-looking invoices count

### U-11: A reminder cannot be delivered
Flow: The mail service refuses or is unreachable at the send time. The system tries again later that day, up to 3 attempts in all. If every attempt fails the history shows "failed" and the owner can see it. Meanwhile the owner creates invoices, edits them and records payments as usual.
Source: implied: sending can fail; the invoicing work around it must not suffer

### U-12: Operator restarts the system or it is down for days
Flow: The operator restarts the system, possibly several times in a day, or the system is down across several step dates. After the restart no customer gets a copy of a reminder already delivered. Reminders due and not yet sent still go out. After a multi-day outage each overdue unpaid invoice gets at most one reminder, not a flood of missed ones. If two copies of the system run at the same time, each reminder still arrives once.
Source: implied: "automatic" reminders must survive restarts

### U-13: Operator introduces the feature on a system that already has invoices
Flow: The system holds invoices created before the feature existed, some overdue by months. Reminders are off until the owner turns them on. Once on, each overdue unpaid invoice that has a step date already behind it gets exactly one reminder at the first send time, and invoices not yet overdue get none.
Source: implied: "carry on with the data that exists today"

### U-14: Operator runs a large day
Flow: 10,000 invoices have a step date on the same day. Every one of them is handled that day: each gets exactly one history entry for the step and no customer gets a duplicate.
Source: implied: the largest case

### U-15: Operator goes back to the version before this feature
Flow: The operator reverts to the earlier version. All invoices, payments and customer data show correctly and are unchanged, and no reminders go out. If the operator later installs this version again, reminders already sent are not sent again.
Source: implied: "go back to the version before"

### U-16: An invoice changes while reminders are running
Flow: An invoice's due date is moved, or the invoice is voided, after some reminders have been sent. Later reminders follow the new due date, and a voided invoice gets none. Reminders already sent are never repeated.
Source: implied: invoices are edited after they are issued

## Clauses

### C-1: An unpaid, overdue invoice is sent one reminder on each of its step dates
Observable: With the default schedule, an unpaid invoice due 2026-03-01 gets one message to its customer on each of 2026-03-02, 2026-03-08 and 2026-03-15, if the system is running and reminders are on.
Source: request

### C-2: The default schedule has three steps, at 1, 7 and 14 days after the due date
Observable: On a fresh setup the owner sees the schedule 1, 7, 14.
Source: choice: the request gives no schedule and a default is needed so that "set up" works at once; a short escalating one is the usual need

### C-3: No reminder is sent before the first step date
Observable: With the default schedule, an invoice due 2026-03-01 gets nothing on any date up to and including 2026-03-01, even though it is unpaid.
Source: choice: the request says "unpaid", which also covers invoices not yet due; reminders start only once an invoice is late so that customers are not chased before they owe

### C-4: An invoice gets no reminder beyond the steps of the schedule
Observable: With the default schedule an unpaid invoice has received 3 reminders by 2026-03-15 and receives none on any later date, such as 2026-04-15.
Source: choice: the request does not say when to stop; a bounded count keeps the system from nagging forever

### C-5: Each step is sent at most once per invoice
Observable: However often the system runs in a day, however often it restarts, the customer gets one message for each step of an invoice and never two for the same step.
Source: implied: U-1 and U-12; a repeated reminder is noise to the customer

### C-6: A reminder shows the invoice number, the outstanding amount with its currency, and the due date
Observable: A reminder for invoice INV-1042, with 600.00 USD outstanding and due 2026-03-01, contains the text INV-1042, 600.00, USD and 2026-03-01 (or the same date in another clear form).
Source: implied: U-1; the customer cannot act without knowing which invoice and how much

### C-7: A reminder names the business that issued the invoice
Observable: The message contains the issuing business's name.
Source: implied: U-1; the customer must recognise who is asking for payment

### C-8: A reminder carries the payment instructions or payment link the invoice has, when it has one
Observable: For an invoice with a payment link the message contains that link. For one with none no placeholder or empty link appears.
Source: implied: U-1; the point of a reminder is that the customer can pay

### C-9: A reminder is sent only to the contact address of the invoice's own customer
Observable: The recipient is the invoice's customer contact address. No other customer's address and no address outside the invoice receives it.
Source: implied: U-1; invoice details are private to the customer

### C-10: Each reminder concerns one invoice
Observable: A customer with 3 unpaid invoices that share a step date receives 3 separate messages, each naming one invoice.
Source: choice: one message per invoice keeps the amount, number and payment details unambiguous

### C-11: A fully paid invoice gets no reminder from the moment the payment is recorded
Observable: If payment is recorded at 08:59 and the send time is 09:00, no reminder for that invoice arrives that day or later.
Source: implied: U-2

### C-12: A part-paid invoice keeps being reminded, and the amount shown is the outstanding balance
Observable: An invoice of 1,000.00 USD with 400.00 USD paid, once overdue, gets reminders showing 600.00 USD and not 1,000.00 USD.
Source: implied: U-3

### C-13: A void or cancelled invoice gets no reminder
Observable: After an invoice is voided, nothing arrives for it on later step dates.
Source: implied: U-10, U-16; the debt no longer exists

### C-14: A draft invoice, one not yet issued, gets no reminder
Observable: A draft with a due date in the past gets no message.
Source: implied: U-10; the customer has not received that invoice

### C-15: An invoice with nothing owing gets no reminder
Observable: An invoice whose outstanding balance is zero, or negative because of a credit, gets no message.
Source: implied: U-10; there is nothing to ask for

### C-16: An invoice without a due date gets no reminder
Observable: An unpaid invoice with no due date gets no message at any time.
Source: implied: U-10; step dates are counted from the due date, so none can be worked out

### C-17: An overdue unpaid invoice whose customer has no usable email address is skipped, and the owner can see why
Observable: Nothing is sent. The reminder history for the invoice shows a skipped entry for that step with a reason that the address is missing or invalid.
Source: implied: U-10

### C-18: When several step dates have passed without being handled, only the latest one is sent
Observable: With the default schedule and an invoice due 2026-03-01, if the system is down, off or not yet enabled from 2026-03-02 and returns on 2026-03-16, the customer receives one reminder, the 14-day step, at the next send time. The 1-day and 7-day steps are shown in the history as skipped.
Source: choice: a customer must not get a burst of late reminders after downtime, a pause or a first start; one is enough to prompt payment

### C-19: A step dated on or before the date of the invoice's most recent sent reminder is not sent
Observable: An invoice has had its 1-day and 7-day reminders. The schedule is then changed to 2 and 10. The 2-day step is not sent. The 10-day step is sent on its date.
Source: choice: after a schedule change, the customer should not receive a reminder that falls behind one already sent

### C-20: If an invoice's due date changes, the steps not yet sent follow the new due date
Observable: An invoice due 2026-03-01 is sent its 1-day reminder on 2026-03-02. Its due date is moved to 2026-03-20. The next reminder, the 7-day step, arrives on 2026-03-27. The 1-day step is not sent again.
Source: implied: U-16; step dates are counted from the due date

### C-21: Reminders are sent at a configured send time of day, 09:00 by default, and never before it on the step date
Observable: With the default send time, a reminder for a step date is not sent before 09:00 on that date.
Source: choice: the request gives no time of day; a business-hours default avoids mail in the middle of the night

### C-22: A reminder that is due is sent within 1 hour of its send time, if the system is running
Observable: With the send time 09:00 and the system running, a reminder due that day is delivered to the mail service by 10:00 that day.
Source: choice: "automatic" needs a stated promptness; one hour is loose enough for a batch job

### C-23: Step dates and the send time are counted in a configured time zone, UTC by default
Observable: With the time zone set to Europe/London and the send time 08:30, a reminder is sent at 08:30 London time on the step date. With no zone set, it is 09:00 UTC.
Source: choice: a due date is a calendar date, so a zone is needed to decide when a day starts

### C-24: The owner can set the schedule, and a change applies to sends after it is made
Observable: After the schedule is set to 2 and 10, an invoice due 2026-03-01 is reminded on 2026-03-03 and 2026-03-11. A reminder already delivered is not withdrawn.
Source: implied: U-5

### C-25: A schedule has from 1 to 10 steps
Observable: A schedule of 1 step is accepted. A schedule of 10 steps is accepted. A schedule of 0 or 11 steps is refused.
Source: choice: at least one step is needed for the feature to do anything, and 10 is plenty before it becomes harassment

### C-26: Each step offset is a whole number of days from 1 to 365
Observable: 1 and 365 are accepted. 0, 366, -1 and 1.5 are refused.
Source: choice: only overdue reminders exist (C-3), and a year is a sensible upper bound

### C-27: The offsets in a schedule are strictly increasing
Observable: 3, 7, 14 is accepted. 7, 3, 14 and 3, 3, 14 are refused.
Source: choice: a repeated or out-of-order step would give two reminders for one date or a confusing order

### C-28: The owner can set the send time and the time zone
Observable: The send time is accepted as a time of day from 00:00 to 23:59 and the time zone as a standard time-zone name such as Europe/London. 25:00 and "Mars/Base" are refused.
Source: implied: U-5

### C-29: A refused settings change tells the owner which setting is wrong
Observable: Each refusal in C-25 to C-28 comes with a message that names the faulty setting (for example the schedule or the send time).
Source: implied: U-6

### C-30: A refused settings change leaves the earlier settings unchanged
Observable: After a refused change the owner sees exactly the settings that held before it, and sends follow them.
Source: implied: U-6

### C-31: The settings and the on/off state persist across restarts, and the owner can see them
Observable: After the system is restarted, the schedule, send time, time zone and on/off state are as the owner left them. The owner can display all four at any time.
Source: implied: U-5, U-12

### C-32: Reminders are off until the owner turns them on
Observable: On a system where the feature has just been introduced, no customer receives a reminder until the owner has turned reminders on, even with overdue unpaid invoices present.
Source: choice: the request says "set up", and mail to customers cannot be recalled; so the owner starts it deliberately

### C-33: The owner can turn reminders on
Observable: After the owner turns them on, the owner sees the state "on" and overdue unpaid invoices begin to be reminded at the next send time.
Source: request ("set up automatic reminders")

### C-34: Turning reminders off stops all sending from that moment
Observable: After the owner turns reminders off at 08:00, no reminder is sent that day, including those due at 09:00 and retries of earlier failures.
Source: implied: U-7

### C-35: The owner can mark one invoice "no reminders", and it gets none while the mark stands
Observable: The invoice shows the mark. On its step dates nothing is sent for it. Other invoices of the same customer are still reminded.
Source: implied: U-8

### C-36: The owner can remove the "no reminders" mark from an invoice
Observable: After the mark is removed the invoice no longer shows it and is reminded again, as C-1 and C-18 describe.
Source: implied: U-8

### C-37: The owner can see a reminder history per invoice
Observable: For each reminder handled, the history shows the time, the address used, the step and the outcome (sent, failed or skipped), and for a failure or skip the reason. An invoice that has been handled by none shows an empty history.
Source: implied: U-9

### C-38: A failed delivery is tried again, for 3 attempts in all, at least 1 hour apart, within the step date
Observable: With a mail service that always refuses, the history shows 3 attempts for the step, none less than 1 hour after the one before, and all on the step date.
Source: choice: a temporary mail failure should not lose a reminder, but retrying without limit would pile up

### C-39: When the attempts in C-38 are used up, or the step date ends first, the step is recorded as failed and is not sent later
Observable: The history shows "failed" with a reason. The customer gets nothing for that step on a later day.
Source: choice: a late copy of an old step would be out of date by then, and the next step follows anyway

### C-40: A failure to send reminders does not affect the invoicing work
Observable: While the mail service is down, creating and editing invoices and recording payments all work and give the same results as they would with the service up.
Source: implied: U-11

### C-41: Reminders never change an invoice's data
Observable: An invoice's status, amounts, due date and payments are the same after a reminder is sent as before it.
Source: implied: this touches existing invoice data and must not alter it

### C-42: A restart loses no reminder and repeats none
Observable: Reminders delivered before a restart are not sent again after it. A reminder due and not yet sent before the restart is sent after it, within the time in C-22 of the restart or its send time, whichever is later.
Source: implied: U-12

### C-43: Two copies of the system running at once send each reminder once
Observable: With two copies running over the same data, a customer receives one message per step.
Source: implied: U-12

### C-44: A day with 10,000 invoices due for a step is handled in full, each exactly once
Observable: With 10,000 eligible invoices on one step date, by the end of that date the history has exactly one entry with an outcome for each, and no customer received two messages for the same step.
Source: implied: U-14

### C-45: Going back to the version before this feature leaves invoice, payment and customer data intact and sends no reminder
Observable: After the revert, every invoice, payment and customer record shows the same values as before and the earlier version works on them as it did. No reminder is sent.
Source: implied: U-15

### C-46: Installing the feature again after a revert does not send reminders already sent
Observable: The reminder history from before the revert is still there, and steps recorded as sent are not sent again.
Source: implied: U-15
