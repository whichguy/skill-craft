## Use cases

### U-1: A billing operator enables reminders so outstanding invoices can be followed up automatically
Flow: The operator learns when invoices are checked, enables reminders for the billing records they manage, and sees that reminders are active. The service checks for eligible invoices without further action from the operator.
Source: request

### U-2: A customer receives the first reminder so they know which invoice to pay
Flow: An issued invoice remains unpaid when it becomes eligible. The customer receives a reminder at the invoice's billing email address that identifies the invoice and asks for payment. A partial payment leaves the invoice eligible if a collectible balance remains.
Source: request

### U-3: A billing operator leaves reminders running so repeated checks cover newly eligible invoices
Flow: Checks continue after the first delivery. An invoice already sent its automatic reminder receives no second automatic reminder. A different invoice that becomes eligible later is considered on a subsequent check.
Source: implied: an automatic reminder service keeps working after its first delivery

### U-4: A billing operator runs reminders over an empty or ineligible set so customers receive only applicable reminders
Flow: On a check with no eligible invoices, the service sends nothing and remains available for later checks. This includes a set containing only fully paid, unissued, canceled, or not-yet-overdue invoices.
Source: implied: reminders are for unpaid invoices and some checks have nothing to send

### U-5: A customer pays or a billing operator cancels an invoice so a pending reminder is withheld
Flow: After an invoice becomes eligible, a payment that settles it or a cancellation is recorded before the next delivery handoff. The customer receives no reminder from that handoff.
Source: implied: an invoice can change between being considered for a reminder and being sent one

### U-6: A billing operator corrects incomplete invoice data so a skipped invoice can receive its reminder
Flow: An otherwise eligible invoice has no usable billing email, or the invoice has no usable due date. The operator can identify the affected invoice and reason for the skip. Other invoices continue through the check. After correction, the service considers the invoice under the current eligibility rules.
Source: implied: existing invoices may lack the information needed to time or address a reminder

### U-7: A billing operator reviews delivery failures so the next action matches the outcome
Flow: The service attempts a delivery. A temporary rejection is retried while the invoice remains eligible. A permanent rejection is visible to the operator and an unchanged delivery is not repeated. When acceptance is uncertain, the operator can distinguish it from a confirmed rejection, and the service avoids a second potentially accepted delivery. If an accepted email later bounces and the service learns of it, the operator can see that delivery failed.
Source: implied: an automatic delivery can fail or have an uncertain outcome

### U-8: A billing operator handles a backlog so eligible customers receive reminders across the supported invoice volume
Flow: The service checks a billing scope containing the largest volume of invoices supported by the existing product. If the eligible set exceeds the capacity of one check, work continues on later checks until it has been considered. Failed or skipped invoices do not hold up unrelated invoices.
Source: implied: automatic reminders must work when the eligible invoice set exceeds one check's capacity

### U-9: A billing operator disables reminders so further automatic deliveries stop
Flow: The operator turns reminders off and sees the inactive state. If a reminder is waiting to be handed off, it is withheld. The operator can later turn reminders on and the service evaluates the then-current invoices.
Source: implied: the operator needs to control when automatic customer contact is active

### U-10: An unauthorized caller attempts to change reminder settings and is refused
Flow: A caller without authority to manage reminders for the affected billing records attempts to enable or disable them. The caller sees that the change was refused and the effective setting stays as it was.
Source: implied: a settings change can cause customer contact and must respect billing access boundaries

### U-11: A billing operator submits an invalid reminder setting so they can correct it
Flow: The operator supplies a value that does not represent either available setting. The service indicates which setting is invalid and the last valid value remains in effect.
Source: implied: an operator can supply a wrong value when configuring reminders

### U-12: An operator starts or restarts the service so reminder work resumes safely
Flow: Starting the feature with no saved activation leaves it inactive. On restart, the saved setting still applies. When enabled, checks resume and consider eligible invoices from missed checks. Replayed or overlapping work does not send another reminder for an invoice whose reminder was already accepted.
Source: implied: automatic processing needs predictable startup and recovery behavior

### U-13: A billing operator enables reminders after an upgrade so existing invoices can use the feature
Flow: The operator activates reminders with invoices already present. Existing eligible invoices can be reminded without being reissued. Existing invoices with missing information follow the same skip and correction behavior as new invoices.
Source: implied: activation occurs in a billing system that may already contain invoice data

### U-14: An operator rolls back the release so billing can continue on the previous version
Flow: The operator stops reminders and returns to the prior billing release. Invoices and payments remain usable there. If the feature is later restored, a reminder accepted before rollback is still accounted for.
Source: implied: rollback must preserve invoice operation and a later return must avoid duplicate contact

### U-15: A billing operator or customer uses existing billing workflows so reminder activity does not change their invoice transactions
Flow: Billing staff continue issuing and editing invoices and recording adjustments, while customers use the existing payment flow. Existing manual communications remain available. Reminder processing leaves normal invoice and payment rules in effect.
Source: implied: automatic reminders add follow-up to an existing billing workflow

### U-16: A billing operator checks reminder activity so they can tell what happened to an invoice
Flow: The operator inspects an invoice that was accepted for delivery, skipped, or failed. The operator can associate the outcome with that invoice and retrieve the reason for a skip or failure. Billing operators see only the records they are entitled to access.
Source: implied: automatic processing needs an observable outcome when intervention or verification is needed

## Clauses

### C-1: The service sends reminders for eligible unpaid invoices automatically
Observable: With reminders active, an eligible unpaid invoice is sent a reminder without a person initiating its delivery.
Source: request

### C-2: A reminder identifies the invoice it concerns
Observable: The recipient can use the reminder to distinguish the invoiced obligation from their other invoices.
Source: implied: U-2 requires the customer to know which invoice to pay

### C-3: A reminder asks the recipient to pay the outstanding invoice
Observable: The recipient sees that payment of the identified invoice is being requested.
Source: implied: the request is to remind customers about unpaid invoices

### C-4: A fully settled invoice is ineligible for reminders
Observable: An invoice with zero outstanding balance after a recorded settlement produces no automatic reminder.
Source: request

### C-5: A partial payment leaves an otherwise eligible invoice eligible while a collectible balance remains
Observable: An otherwise eligible invoice with a positive collectible balance after partial payment can receive an automatic reminder.
Source: implied: U-2 concerns an obligation that is still unpaid in part

### C-6: An invoice must have been issued to qualify for a reminder
Observable: A draft with a positive balance produces no automatic reminder.
Source: implied: U-4 requires a customer obligation that has already been presented to the customer

### C-7: An invoice withdrawn from collection is ineligible for reminders
Observable: A canceled or voided invoice produces no automatic reminder even if its original amount remains visible.
Source: implied: U-4 distinguishes money owed from amounts on invoices no longer collectible

### C-8: Reminders begin only after the invoice payment deadline has passed
Observable: An otherwise eligible invoice receives no automatic reminder while its payment window is still open. It can receive one once that window has ended.
Source: choice: following up after payment is due avoids contacting customers who still have time to pay

### C-9: A date-only due date without existing deadline semantics includes the full due date
Observable: With a date-only due date and no existing deadline rule, the invoice is not overdue at any time on that date in the billing time zone. It first becomes overdue at the start of the following calendar day in that zone.
Source: choice: customers should have the whole stated day to pay when the invoice gives no time of day

### C-10: UTC governs a date-only due date when billing has no applicable time zone or deadline rule
Observable: In that case, a date-only deadline has passed starting at 00:00 UTC on the calendar day after the due date.
Source: choice: a shared fallback prevents the cutoff from shifting with the operator's or service's location

### C-11: An invoice with no determinable payment deadline is skipped
Observable: An invoice with a missing or unusable due date that has no other valid deadline produces no automatic reminder.
Source: choice: withholding delivery avoids guessing when the customer agreed to pay

### C-12: Automatic reminders are delivered by email
Observable: A recipient gets the automatic reminder in their email inbox after successful delivery.
Source: choice: a single asynchronous channel suffices for routine invoice follow-up

### C-13: A reminder is addressed to the current billing email applicable to the invoice
Observable: If the authorized billing destination for an invoice is corrected before handoff, the reminder is addressed to the corrected destination.
Source: choice: the designated billing contact is the least surprising recipient for invoice correspondence

### C-14: An invoice with no usable billing email is skipped
Observable: An invoice whose billing address is blank or malformed produces no automatic delivery attempt until it has a usable destination.
Source: implied: U-6 requires a valid destination for the selected delivery channel

### C-15: Current invoice eligibility governs whether a pending reminder may be handed off
Observable: When an eligibility-changing update takes effect before handoff, a pending reminder for the now-ineligible invoice is withheld.
Source: implied: U-5 requires honoring payment or cancellation recorded before contact is made

### C-16: Enabled reminders consider invoices as they become eligible over time
Observable: An invoice that becomes eligible after earlier reminder activity is considered without another activation.
Source: implied: U-3 requires the feature to keep working over time

### C-17: Normal reminder timing is available to the billing operator
Observable: Before enabling reminders, the operator can determine when an eligible invoice would normally be considered.
Source: choice: an operator needs a timing expectation without requiring a particular cadence

### C-18: Each invoice can have at most one accepted automatic reminder delivery
Observable: Once a delivery service accepts an invoice's automatic reminder, later checks, overlapping checks, or replayed work do not cause another accepted automatic reminder for that invoice.
Source: choice: one automatic follow-up serves the request without setting up a recurring collection sequence

### C-19: A check with no eligible invoice completes without a delivery
Observable: A check over zero eligible invoices completes normally and emits zero automatic reminders.
Source: implied: U-4 covers both an empty billing scope and a check where all invoices are ineligible

### C-20: Correcting a skipped invoice makes it available to later eligibility checks
Observable: After correcting the reason for a skip, an operator sees the invoice considered on a later check without recreating it.
Source: implied: U-6 requires normal processing to recover once the invoice information is usable

### C-21: A definitively rejected temporary delivery is retried while its invoice remains eligible
Observable: If the delivery service confirms a temporary rejection and the invoice remains eligible, the service makes a later delivery attempt without a manual send.
Source: choice: automatic recovery covers temporary outages without choosing a fixed retry delay or count

### C-22: A definitively rejected permanent delivery is withheld while its cause remains unchanged
Observable: Later checks do not repeat the same delivery after a confirmed permanent rejection while the cause of rejection remains in effect.
Source: choice: repeating a delivery known to be unreceivable does not improve collection

### C-23: An uncertain delivery is withheld from automatic retry unless the prior attempt is confirmed unaccepted
Observable: After a timeout or interruption with an unknown delivery result, subsequent checks issue no second potentially accepted delivery while the first outcome remains unknown.
Source: choice: withholding uncertain retries prioritizes preventing duplicate customer contact

### C-24: A problem with one invoice leaves other invoices available for processing
Observable: An eligible invoice with a healthy delivery path can be reminded even when another invoice in the same check is skipped or rejected.
Source: implied: U-6, U-7, and U-8 require independent invoices to keep progressing

### C-25: Reaching per-check capacity leaves excess work eligible for later checks
Observable: When more invoices qualify than a check can process, the remaining invoices are considered over subsequent checks while they remain eligible, including when more invoices arrive.
Source: implied: U-8 requires the supported invoice volume to be covered without silently abandoning work at a processing limit

### C-26: A billing operator can enable automatic reminders for their billing scope
Observable: An authorized operator enables reminders for the records they manage and can see that the setting is active.
Source: implied: U-1 requires an operator to put the automatic feature into service

### C-27: A billing operator can disable automatic reminders for their billing scope
Observable: An authorized operator disables reminders for the records they manage and can see that the setting is inactive.
Source: implied: U-9 requires an operator to stop automatic contact

### C-28: Inactive reminders prevent new automatic delivery handoffs
Observable: After disabling takes effect, a reminder that has yet to be handed off is not handed off while reminders are inactive.
Source: implied: U-9 requires disabling to cover pending reminders

### C-29: Reminder settings respect billing authority
Observable: A caller without permission to manage reminders for the affected billing scope receives a refusal when they try to change its setting. The effective setting is unchanged.
Source: implied: U-10 requires an unauthorized change to have no effect

### C-30: Invalid activation settings are rejected
Observable: A value outside the enabled or disabled states produces an error that identifies the setting at fault. The last valid setting stays in effect.
Source: implied: U-11 requires predictable behavior when configuration input is wrong

### C-31: Reminders are initially inactive in a billing scope without an activation setting
Observable: Starting a new or upgraded billing scope with no saved activation results in zero automatic reminder handoffs until an authorized operator enables them.
Source: choice: initial activation should be deliberate because it can contact customers about existing invoices

### C-32: A restart preserves the effective activation setting
Observable: After restarting, a previously enabled scope remains enabled and a previously disabled scope remains disabled.
Source: implied: U-12 requires a restart to preserve the operator's saved configuration

### C-33: An enabled service considers still-eligible work after an interruption
Observable: If a check was missed while the service was stopped, an invoice that became eligible during the interruption can be reminded after service resumes.
Source: implied: U-12 requires an interruption to be recoverable for outstanding work

### C-34: Existing invoices participate under the same eligibility rules as new invoices
Observable: After activation, an invoice issued before the feature was installed can receive a reminder under the same conditions as a later invoice without being reissued.
Source: implied: U-13 requires the feature to work with the invoice data already present

### C-35: The previous billing version can continue using existing invoice records after a rollback
Observable: After stopping reminders and reverting, operators can access and use invoice records created before or during feature operation through the prior version's normal billing workflows.
Source: implied: U-14 requires a return to the prior release with usable invoices

### C-36: Rollback preserves recorded payments
Observable: A payment recorded before rollback, including during feature operation, remains reflected on the invoice in the previous version.
Source: implied: U-14 requires rollback to preserve payment records

### C-37: A rollback followed by restoration preserves prior accepted reminder outcomes
Observable: After restoring the feature, the operator can still see that a delivery accepted before rollback was accepted for its invoice.
Source: implied: U-14 requires prior reminder outcomes to be accounted for on restoration

### C-38: Reminder processing leaves existing invoice issuance rules in effect
Observable: The same invoice creation inputs are accepted or refused under the same existing rules with reminders active or inactive.
Source: implied: U-15 adds follow-up to already-issued invoices without changing invoice issuance

### C-39: Reminder processing leaves existing invoice update rules in effect
Observable: Existing edits, adjustments, or cancellations remain available under the same conditions after reminder activation.
Source: implied: U-15 requires the existing invoice lifecycle to continue

### C-40: Reminder processing leaves existing payment workflows in effect
Observable: Customers or billing staff can make or record payments under the same existing rules with reminders active or inactive.
Source: implied: U-15 requires normal payment operation alongside reminders

### C-41: Automatic reminder activity does not change the outstanding amount of an invoice
Observable: With no intervening billing or payment action, the outstanding balance immediately after reminder processing is the same as before it.
Source: implied: U-15 requires reminders to leave payment obligations intact

### C-42: Existing manual invoice communications remain available under their existing rules
Observable: A manual communication previously available for an invoice can still be sent in the same circumstances after reminder activation, including after an automatic reminder for that invoice.
Source: implied: U-15 adds automatic follow-up alongside existing communications

### C-43: An operator can associate a recorded reminder outcome with its invoice
Observable: The operator can look up whether a reminder was accepted for delivery, skipped, rejected, or has an uncertain result for a particular invoice that was processed.
Source: implied: U-16 requires distinguishing operational outcomes when following up on an invoice

### C-44: A skip or delivery rejection has an operator-visible reason
Observable: For a skipped or rejected reminder, the operator can determine the cause known to the service, such as a missing billing address or a temporary provider outage.
Source: implied: U-6, U-7, and U-16 require the operator to know what can be corrected

### C-45: Reminder outcome visibility follows existing billing-record access boundaries
Observable: A caller without access to an invoice cannot retrieve its reminder activity through the feature.
Source: implied: U-16 requires reminder information to follow the invoice's access rules

### C-46: Reminder delivery uses the billing information belonging to the invoice's own scope
Observable: Two billing scopes with similar invoice or customer identifiers each see their own invoice information routed only to the billing recipient for that invoice.
Source: implied: U-2 requires contact with the correct customer, including when several billing scopes operate together

### C-47: Existing invoice deadline rules govern reminder eligibility where they apply
Observable: For an invoice with an established deadline rule, the reminder uses the same payment cutoff that billing already applies to that invoice.
Source: implied: U-13 and U-15 require consistency with the invoice terms already in use

### C-48: An invoice becomes eligible for consideration again when a permanent rejection is corrected
Observable: When a cause such as a rejected billing address is corrected, a later check considers the otherwise eligible invoice using its updated information.
Source: implied: U-6 and U-7 require recoverable delivery problems to clear when their cause is fixed

### C-49: A known failure after acceptance is visible to the billing operator
Observable: If a delivery service reports a bounce after accepting a reminder, the invoice's reminder outcome shows the reported delivery failure.
Source: implied: U-7 and U-16 require an operator to distinguish a known delivery failure from an accepted handoff

### C-50: Reminder processing preserves the invoice's payment terms
Observable: With no intervening billing action, an invoice has the same payment terms after reminder processing as it had before processing.
Source: implied: U-15 treats the reminder as follow-up on the obligation already agreed with the customer

### C-51: Reminder processing preserves the invoice's billing status
Observable: With no intervening billing or payment action, processing an automatic reminder does not change the invoice's status in existing billing workflows.
Source: implied: U-15 requires sending a reminder to leave the invoice lifecycle intact
