## Use cases

### U-1: A billing operator enables reminders to follow up automatically
Flow: An authorized billing operator enables reminders for their billing account and sees that the setting is active. When an eligible invoice remains unpaid, its billing recipient gets a reminder without anyone having to send it manually.
Source: request

### U-2: A billing recipient reads a first reminder to identify what they owe
Flow: A recipient with several invoices receives a reminder, recognizes the invoice it concerns, and sees the amount still due in the invoice currency. Where the invoice already offers a way to pay, the recipient can reach it from the reminder.
Source: implied: the recipient must be able to act on a reminder for an unpaid invoice

### U-3: A billing recipient gets another reminder when an invoice stays unpaid
Flow: The first reminder becomes eligible on the calendar day after the due date. If the invoice stays eligible, the next reminder becomes eligible 7 calendar days after the previous one was accepted for delivery.
Source: implied: automatic follow-up for invoices that remain unpaid after the initial reminder

### U-4: A billing operator starts reminders with no eligible invoices
Flow: The operator enables reminders for an empty account or one whose invoices are all ineligible. No reminder goes out. When a later invoice becomes eligible, the operator does not need to enable reminders again.
Source: implied: first use with an empty set of unpaid invoices

### U-5: A billing recipient pays an invoice to stop further collection reminders
Flow: The recipient makes a partial payment and a later reminder reflects the remaining balance. If the invoice is settled before a pending reminder is handed off, the recipient gets no further reminder for the settled invoice.
Source: implied: reminders are for invoices with an unpaid balance

### U-6: A billing operator updates an invoice to correct future follow-up
Flow: The operator moves the due date, changes the designated billing address, or withdraws the invoice through existing billing actions. Future reminders reflect the current invoice and recipient information.
Source: implied: invoice data can change between eligibility and sending

### U-7: A billing operator enables reminders for invoices already on file
Flow: After activation, an existing overdue invoice with usable billing information is considered on the next evaluation. Its recipient gets a current reminder without receiving one for each missed date.
Source: implied: first activation with invoices that predate the feature

### U-8: A billing operator corrects unusable invoice data to resume follow-up
Flow: An invoice with a missing or unusable due date or billing email produces no reminder. Other eligible invoices continue. The operator can identify which invoice needs attention and see the reason. After correction, the invoice is evaluated again.
Source: implied: existing invoice records can contain missing or invalid data

### U-9: An unauthorized person attempts to change reminders
Flow: Someone without permission for the billing account tries to enable or disable reminders. The change is refused and the account's effective setting stays as it was.
Source: implied: changing who receives automatic billing communications requires account authority

### U-10: A billing operator submits an invalid setting to learn whether it took effect
Flow: Where the configuration surface accepts submitted values, the operator submits a value that does not identify either supported state. The operator sees the rejection and the previous setting continues to apply.
Source: implied: configuration may receive invalid input

### U-11: A billing operator handles a delivery failure to restore follow-up
Flow: A delivery service can reject a reminder temporarily, permanently, or leave its acceptance unknown. The operator can distinguish those outcomes for the affected invoice. A temporary rejection can be tried again on a later calendar day. A permanent rejection for the address waits for correction, including when the delivery service reports the failure after accepting the message. An uncertain attempt is held for the same 7-calendar-day interval as an accepted one.
Source: implied: the automatic action depends on an external delivery outcome

### U-12: A billing operator runs reminders at the account's highest supported invoice volume
Flow: The account has as many eligible invoices as its invoice system supports. Reminders are handled within the delivery limits. Invoices deferred at a limit stay eligible for later evaluation if they still qualify.
Source: implied: automatic processing must handle the supported invoice population and delivery limits

### U-13: A service operator restarts reminders after an interruption
Flow: An interruption occurs around a scheduled evaluation or delivery handoff. After restart, eligible invoices resume evaluation. Recipients do not receive a burst for missed dates or copies of a reminder that was already accepted.
Source: implied: automatic operation must recover from interruptions

### U-14: A billing operator disables reminders to stop future sends
Flow: The operator disables reminders before a pending reminder is handed off. No new reminders are handed off while disabled. On re-enable, the operator can resume follow-up without replaying missed reminders.
Source: implied: the operator needs to stop or resume automatic billing communication

### U-15: A service operator rolls back to the preceding version to restore prior operation
Flow: Where there is a preceding version, the service operator rolls back while reminders are pending. New automatic handoffs stop. Invoice and payment records remain usable on the preceding version. If the feature returns, sent reminder history still prevents replay.
Source: implied: reminders must coexist with existing billing data through rollback

### U-16: A billing recipient uses the ordinary invoice process alongside reminders
Flow: The recipient still receives the original invoice under the existing delivery rules, uses the existing payment process, and receives any existing payment confirmation. Existing recipient restrictions still apply to reminders.
Source: implied: automatic reminders extend the existing invoice process

## Clauses

### C-1: Eligible unpaid invoices receive reminders automatically.
Observable: With automatic reminders active, leave an eligible invoice unpaid through an eligible sending opportunity and observe a reminder without taking a send action.
Source: request

### C-2: An authorized billing operator can enable reminders for their billing account.
Observable: Enable reminders with the account's billing authority and observe the active setting for that account.
Source: implied: U-1

### C-3: An authorized billing operator can disable reminders for their billing account.
Observable: Disable active reminders with the account's billing authority and observe the inactive setting for that account.
Source: implied: U-14

### C-4: Reminders start disabled for an account that has never configured them.
Observable: Inspect the setting on an account before its first configuration and observe that it is disabled.
Source: choice: initial activation should be deliberate when customers could receive new billing messages

### C-5: An unauthorized reminder setting change is refused.
Observable: Attempt to change an account's reminder setting without the account's billing authority and observe a refusal.
Source: implied: U-9

### C-6: A refused change leaves the effective reminder setting intact.
Observable: Read the setting before and after a refused change and observe the same value.
Source: implied: U-9

### C-7: A configuration surface that accepts submitted setting values rejects values outside its supported states.
Observable: Where values can be submitted directly, submit a value representing neither enabled nor disabled and observe that it is rejected.
Source: choice: explicit validation prevents an incorrect value from activating billing messages

### C-8: A rejected setting value leaves the effective reminder setting intact.
Observable: Where values can be submitted directly, compare the setting before and after an invalid submission and observe the same value.
Source: implied: U-10

### C-9: An account's reminder setting applies only to its own invoices.
Observable: Enable reminders in one account and observe no resulting reminder activity for invoices owned by another account.
Source: implied: U-1

### C-10: A reminder is sent to the invoice's designated billing recipient.
Observable: Give an invoice a designated billing recipient and observe that the reminder is addressed to that recipient.
Source: implied: U-2

### C-11: Reminders use email.
Observable: For an eligible invoice with a valid designated billing email, observe the reminder through email.
Source: choice: email provides one channel for reaching the billing recipient

### C-12: A reminder identifies the invoice it concerns.
Observable: Give a recipient multiple invoices and observe identifying information in the reminder that distinguishes the invoice being followed up.
Source: implied: U-2

### C-13: A reminder shows the invoice's remaining balance in its currency.
Observable: Apply a partial payment before sending and observe the remaining amount shown in the invoice currency.
Source: choice: showing the outstanding amount lets the recipient see what is due from the reminder itself

### C-14: A reminder provides access to the invoice's existing way to pay where one exists.
Observable: Receive a reminder for an invoice with an existing way to pay and use the reminder to reach that payment option for the same invoice.
Source: choice: the recipient can act without a new payment method

### C-15: A first reminder becomes eligible on the calendar day after the invoice due date.
Observable: Observe no first reminder on the due date or earlier, then observe eligibility on the next calendar day for an otherwise eligible invoice.
Source: choice: give the recipient the entire due date to pay before beginning follow-up

### C-16: An accepted reminder makes the next reminder eligible 7 calendar days after its acceptance date.
Observable: Keep an otherwise eligible invoice unpaid after a reminder is accepted. Observe no repeat in the following 6 calendar days and eligibility on calendar day 7.
Source: choice: a weekly repeat keeps follow-up predictable without daily messages

### C-17: Reminder calendar dates use the account's billing time zone when one is set.
Observable: Use an account whose billing date differs from the service's local date and observe that reminder eligibility follows the account's billing date.
Source: choice: reminder dates should match the billing account's calendar

### C-18: Reminder calendar dates use UTC when the account has no billing time zone.
Observable: With no billing time zone, observe that a change of reminder calendar date occurs at 00:00 UTC.
Source: choice: an account without a time zone still needs a single predictable date boundary

### C-19: Enabled accounts are evaluated at least once per calendar day during normal operation.
Observable: With reminders enabled and services available for a full calendar day, observe an evaluation of that day's eligible invoices.
Source: choice: daily evaluation supports date-based follow-up without imposing an exact send time

### C-20: An evaluation with zero eligible invoices sends zero reminders.
Observable: Evaluate an account with an empty invoice list and observe zero reminders.
Source: implied: U-4

### C-21: An invoice with a zero or negative balance is ineligible at delivery handoff.
Observable: Settle the invoice or apply a credit covering the amount owed before a pending reminder is handed off and observe no handoff for that invoice.
Source: implied: U-5

### C-22: An invoice that is not collectible under existing billing rules is ineligible.
Observable: Where the billing system supports draft, void, or cancelled invoices, give one a positive balance and observe no reminder while its state prevents collection.
Source: implied: U-6 and U-16

### C-23: A pending reminder uses the invoice's current due date to determine eligibility.
Observable: Edit the due date before handoff and observe eligibility evaluated using the revised date.
Source: implied: U-6

### C-24: A pending reminder uses the invoice's current designated billing address.
Observable: Correct the designated billing address after eligibility is first checked but before handoff and observe that the handoff targets the corrected address.
Source: implied: U-6

### C-25: Eligible invoices that predate activation enter normal reminder evaluation.
Observable: Enable reminders with an existing otherwise eligible overdue invoice and observe that it is considered on the next evaluation.
Source: implied: U-7

### C-26: Missed reminder dates do not accumulate separate catch-up sends.
Observable: Resume evaluation for an invoice that remained eligible through multiple missed dates and observe at most 1 reminder for that invoice on resumption.
Source: choice: a current reminder serves the purpose of elapsed reminder opportunities

### C-27: An invoice with a missing or unusable due date is skipped.
Observable: Evaluate an otherwise eligible invoice whose due date cannot be determined and observe no reminder for that invoice.
Source: choice: follow-up should not guess when payment was due

### C-28: An invoice with a missing or unusable billing email is skipped.
Observable: Evaluate an otherwise eligible invoice with no designated billing email or an invalid address and observe no reminder for that invoice.
Source: choice: follow-up should not guess where to send billing information

### C-29: An invoice-level problem leaves other eligible invoices available for processing.
Observable: Evaluate an account containing an invoice with bad data alongside another eligible invoice and observe normal processing for the other invoice.
Source: implied: U-8

### C-30: An authorized billing operator can determine why an invoice was skipped for unusable data.
Observable: Inspect a skipped invoice as its billing operator and see which required information was unusable.
Source: choice: the account needs enough information to correct the invoice

### C-31: Corrected invoice data is considered in subsequent evaluation.
Observable: Fix the unusable field of an otherwise eligible skipped invoice and observe that it can qualify without recreating the invoice.
Source: implied: U-8

### C-32: An authorized billing operator can distinguish delivery outcomes for an affected invoice.
Observable: Inspect reminders with accepted, temporarily rejected, permanently rejected, and uncertain handoffs and observe which outcome applies to each.
Source: choice: distinguishing outcomes tells the operator when the invoice or address may need attention

### C-33: A temporarily rejected reminder is retried if the invoice remains eligible.
Observable: Resolve a temporary rejection while the invoice still qualifies and observe a later delivery attempt.
Source: implied: U-11

### C-34: A retry after a temporary rejection is eligible no earlier than the next calendar day.
Observable: Trigger a temporary rejection and observe zero retries for that invoice for the rest of that calendar day.
Source: choice: a next-day retry avoids repeated handoffs during a temporary failure

### C-35: A known permanent delivery failure for an address suppresses further reminders for the affected invoice to that address.
Observable: Have the delivery service report a permanent address failure, either at handoff or after acceptance. Keep the address on the invoice and observe no later handoffs to that address for that invoice.
Source: choice: retrying a known permanently rejected destination cannot complete delivery

### C-36: An unresolved handoff makes the next attempt eligible no earlier than 7 calendar days after the uncertain attempt.
Observable: Leave acceptance unresolved and observe zero new attempts for that invoice before calendar day 7.
Source: choice: an uncertain attempt may already have reached the recipient, so follow-up waits a full interval

### C-37: Repeated or concurrent evaluations do not duplicate a delivery handoff for the same reminder opportunity.
Observable: Trigger overlapping evaluations for one eligible invoice and observe at most 1 handoff for that opportunity.
Source: implied: U-3 and U-13

### C-38: Reminder evaluation covers the full invoice population supported by the billing account.
Observable: Populate an account up to its supported invoice limit and observe that eligible invoices throughout that population can receive reminders.
Source: implied: U-12

### C-39: Reminder handoffs honor the delivery service's applicable sending limit.
Observable: Evaluate more eligible invoices than the delivery service permits in one limit window and observe that handoffs stay within that limit.
Source: implied: U-12, where the configured delivery service governs acceptance

### C-40: Invoices deferred at a delivery limit are reconsidered once capacity returns.
Observable: Reach the applicable sending limit, restore sending capacity, and observe reconsideration of still-eligible invoices deferred by the limit.
Source: implied: U-12

### C-41: An account's reminder setting survives a restart.
Observable: Restart after changing an account's setting and observe the same effective setting afterward.
Source: implied: U-13

### C-42: An interrupted evaluation resumes automatically after restart.
Observable: Interrupt processing before an eligible invoice is considered, restore service, and observe a subsequent evaluation without reconfiguring the account.
Source: implied: U-13

### C-43: Restart preserves accepted reminder history for determining repeat eligibility.
Observable: Restart after an accepted handoff and observe that the next reminder is still timed from the recorded acceptance date.
Source: implied: U-13

### C-44: Disabling reminders blocks any subsequent handoff while the account is disabled.
Observable: Disable the account after a reminder becomes pending but before handoff and observe that it is not handed off while disabled.
Source: implied: U-14

### C-45: Re-enabling reminders restores evaluation for eligible invoices.
Observable: Re-enable the account while an invoice is eligible and observe that it is considered on a subsequent evaluation.
Source: implied: U-14

### C-46: A completed rollback to the preceding version stops new automatic reminder handoffs.
Observable: Where a preceding version exists, roll back with a reminder pending and observe zero automatic handoffs after rollback completes.
Source: implied: U-15

### C-47: Invoices in use during the reminder feature remain usable on rollback.
Observable: Open an invoice that existed or was created while reminders were available after restoring the preceding version and observe that the prior invoice workflow can still use it.
Source: implied: U-15

### C-48: Payments recorded during the reminder feature remain reflected on rollback.
Observable: Record a payment while reminders are available, restore the preceding version, and observe the payment reflected in the invoice balance.
Source: implied: U-15

### C-49: Restoring the reminder feature after rollback preserves prior accepted handoffs for repeat eligibility.
Observable: Roll back after an accepted reminder, restore the feature before its next opportunity, and observe that the previous acceptance still governs repeat eligibility.
Source: implied: U-15

### C-50: A reminder leaves the underlying invoice terms unchanged.
Observable: Inspect an invoice before and after sending a reminder without any separate invoice update and observe the same invoice terms.
Source: implied: U-16

### C-51: A reminder leaves the invoice's balance unchanged.
Observable: Send a reminder with no intervening billing event and observe the same balance on the invoice afterward.
Source: implied: U-16

### C-52: Original invoice delivery follows its existing rules.
Observable: Issue an invoice that qualifies for the existing original delivery workflow and observe the same delivery behavior regardless of the reminders setting.
Source: implied: U-16

### C-53: Invoice payments follow their existing rules.
Observable: Pay an invoice using its existing payment process and observe that the usual payment rules apply regardless of the reminders setting.
Source: implied: U-16

### C-54: Existing payment confirmations continue under their existing rules.
Observable: Where payment confirmations exist, complete a qualifying payment and observe the usual confirmation regardless of the reminders setting.
Source: implied: U-16

### C-55: Existing recipient restrictions for billing communications apply to reminders.
Observable: Use a designated recipient whom existing billing rules prohibit contacting for this kind of follow-up and observe no reminder handoff to that recipient.
Source: implied: U-16

### C-56: Existing invoice access controls apply to invoice access from reminders.
Observable: Where a reminder provides access to an invoice, attempt to open it without the access required by the existing invoice workflow and observe that access is denied.
Source: implied: U-2 and U-16

### C-57: Existing manual invoice follow-up remains available under its existing rules.
Observable: Where a manual follow-up action exists, perform it with the usual permissions and observe the existing behavior regardless of the automatic reminders setting.
Source: implied: U-16

### C-58: Disabling reminders preserves accepted reminder history for repeat eligibility after re-enable.
Observable: Disable reminders after an accepted handoff and re-enable them before the next opportunity. Observe that the previous acceptance still governs repeat eligibility.
Source: implied: U-14
