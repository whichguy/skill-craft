## Use cases

### U-1: A billing administrator enables reminders so unpaid invoices are followed up automatically
Flow: The administrator finds reminders disabled on first availability, enables them for the billing account, then issues an invoice through the existing workflow. If it remains payable with an outstanding balance, its billing recipient gets a reminder on the first calendar day after its due date.
Source: request

### U-2: A billing recipient receives a reminder to identify the invoice they still owe
Flow: The recipient receives an email identifying the invoice and its current outstanding balance. If the invoice is still eligible, it is followed up every 7 calendar days. A partial payment reduces the balance shown in the next reminder. A settled invoice drops out of future reminders.
Source: implied: by asking for reminders about unpaid invoices

### U-3: A billing administrator checks an account with no eligible invoices to confirm no reminders are sent
Flow: The administrator enables reminders with no invoices, or with only invoices that are not due yet, have no outstanding balance, or are no longer payable. Nobody receives a reminder for those records.
Source: implied: by the unpaid-invoice scope and the empty case

### U-4: A caller attempts an unauthorized or invalid configuration change and sees it refused
Flow: A person without billing-settings permission tries to enable reminders and is refused. An authorized administrator submits an unsupported value and sees a rejection. Each refusal leaves the last saved setting in effect.
Source: implied: by offering an account-wide setting that can cause outbound messages

### U-5: A billing administrator corrects unusable invoice data so future reminders can be sent
Flow: An otherwise eligible invoice is missing a due date or a usable billing email address. The administrator can determine why no reminder went out, then corrects the source data using the existing billing workflow. The invoice can participate in automatic reminders once it is eligible.
Source: implied: by reliance on invoice dates and recipient information

### U-6: An operator handles a delivery failure to keep other reminders moving
Flow: A reminder attempt receives a temporary rejection, a permanent rejection, or an uncertain result. The operator can distinguish these from an accepted handoff. Temporary failures can be retried within the current opportunity. An unresolved handoff is not blindly repeated. Other invoices continue to be processed.
Source: implied: by automatic delivery depending on a delivery service

### U-7: An operator processes the largest supported invoice workload to reach every eligible recipient
Flow: At supported invoice capacity, some invoices become eligible together. The operator sees outcomes across the workload. Repeated or overlapping processing does not send a second copy for the same opportunity. Separate eligible invoices for one recipient can each be followed up.
Source: implied: by automatic processing at supported invoice volumes and the duplicate-delivery limit

### U-8: A billing administrator adopts reminders for invoices already on file
Flow: Before enabling reminders, the account has both historical and newer invoices. On first processing after enablement, an already-overdue eligible invoice can receive one current reminder without being reissued. Previous missed opportunities do not each produce a message.
Source: implied: by introducing automation into billing that already has unpaid invoices

### U-9: An operator restarts reminder processing to resume after an interruption
Flow: Processing stops with a mix of accepted, unfinished, and missed reminders. After restart the account retains its setting. Previously accepted reminders are not repeated for the same opportunity, and a still-eligible invoice can receive the current reminder without a backlog of old messages.
Source: implied: by automatic processing across restarts and downtime

### U-10: A billing administrator disables reminders to stop future messages
Flow: The administrator disables reminders even though some invoices remain overdue. Reminders awaiting handoff stop. The administrator can later enable the feature again, and eligible invoices return to the normal schedule.
Source: implied: by operating an automated outbound feature

### U-11: A billing administrator records a payment or closes an invoice before a pending reminder is sent
Flow: The administrator records a partial payment, records settlement, or closes the invoice using the existing workflow before reminder handoff. A remaining payable balance is reflected in a reminder. Settlement or closure prevents the pending reminder from being sent.
Source: implied: by the reminder reflecting whether an invoice is unpaid at the time of sending

### U-12: An operator rolls back the application to restore the previous billing version
Flow: The operator returns to the previous version. Automatic reminder handoffs stop. Existing billing workflows can still use invoices and posted payments from before or during the rollout. If the reminder-capable version is restored, it can resume from saved reminder state without repeating an already accepted opportunity.
Source: implied: by rolling back a feature that operates alongside existing billing

## Clauses

### C-1: Eligible unpaid invoices receive reminders automatically
Observable: An eligible unpaid invoice causes a reminder at a scheduled opportunity without a person having to initiate the individual send.
Source: request

### C-2: Each reminder identifies its invoice
Observable: The recipient can tell which invoice the reminder concerns from the reminder itself.
Source: implied: by U-2, since a recipient must know what remains unpaid

### C-3: A reminder goes to the invoice's billing recipient
Observable: Where the invoice names a payer distinct from the billing administrator, its reminder is addressed to the payer contact designated for that invoice.
Source: implied: by U-2, since the reminder needs to reach the party expected to pay

### C-4: Automatic reminders use email
Observable: A billing recipient with a usable billing email can receive the reminder by email.
Source: choice: email gives the payer a direct reminder using billing contact information

### C-5: Each reminder shows the invoice's outstanding balance
Observable: For a 100-unit invoice with 40 units of posted payment before handoff, the reminder shows 60 due in the invoice currency.
Source: choice: showing what remains to be paid makes a partially paid invoice actionable

### C-6: An invoice with no outstanding balance receives no reminder
Observable: An invoice that already has a zero balance when evaluated produces no reminder.
Source: implied: by the request limiting reminders to unpaid invoices

### C-7: A partially paid invoice can qualify as unpaid
Observable: A payable invoice with a posted partial payment remains eligible when it has a positive outstanding balance and otherwise qualifies.
Source: implied: by U-2, since paying part of an invoice leaves a balance unpaid

### C-8: A nonpayable invoice receives no reminder
Observable: When the existing invoice rules mark an invoice as no longer payable before handoff, any reminder awaiting handoff is suppressed.
Source: implied: by U-11, since a closed obligation cannot be collected as an unpaid invoice

### C-9: An unissued invoice receives no reminder
Observable: A draft with a balance produces no reminder while it remains unissued.
Source: implied: by U-3, since a draft has yet to establish a payment obligation for its recipient

### C-10: Reminder eligibility uses the invoice's current payable state
Observable: When full payment is posted before a previously prepared reminder is handed off, no reminder is handed off.
Source: implied: by U-11, since preparing a reminder does not establish that payment is still owed

### C-11: The first scheduled reminder opportunity opens on the first calendar day after the due date
Observable: With uninterrupted operation, a qualifying invoice due June 10 has its first automatic handoff attempt on June 11, with no attempt through June 10.
Source: choice: waiting until the due date passes gives the payer the full agreed payment period

### C-12: Subsequent scheduled reminder opportunities occur every 7 calendar days
Observable: While an invoice remains eligible under normal operation, the next scheduled attempt is 7 calendar days after the preceding scheduled date.
Source: choice: weekly recurrence follows up persistent unpaid balances without daily contact

### C-13: A reminder opportunity remains current until the next scheduled date begins
Observable: When processing resumes after its opening date but before the next scheduled date, an unfulfilled opportunity is still available.
Source: choice: a late run within the current interval can complete the follow-up

### C-14: Reminder dates use the existing billing time zone when one is defined
Observable: A billing account with a time zone for invoice dates sees reminder calendar dates evaluated in that zone.
Source: choice: using the billing time zone keeps the due date and reminder schedule on the same calendar

### C-15: Reminder dates use UTC when billing defines no time zone
Observable: For a billing account without a defined billing time zone, the reminder calendar date changes at 00:00 UTC.
Source: choice: a fixed fallback makes dates independent of where reminder processing runs

### C-16: A billing administrator can enable reminders for the account
Observable: An administrator who can manage the account's billing settings can save the enabled state.
Source: choice: account-level enablement gives the billing owner control over outbound automation

### C-17: Reminders start disabled before the first enablement
Observable: On feature introduction, a billing account with overdue invoices produces no automatic reminders until the setting is enabled.
Source: choice: enabling outbound contact is an explicit billing decision

### C-18: A billing administrator can disable reminders for the account
Observable: An administrator who can manage the account's billing settings can save the disabled state.
Source: implied: by U-10, since billing needs to be able to stop outbound automation

### C-19: Disabling reminders prevents new handoffs for the account
Observable: A reminder awaiting handoff when disablement takes effect is not handed off while the setting is disabled.
Source: implied: by U-10, since stopping automation applies to pending work

### C-20: Reminder settings changes require access to manage the account's billing settings
Observable: A caller who lacks that access sees their attempted change refused.
Source: implied: by U-4, since account-wide outbound communication requires authorization

### C-21: A refused settings change preserves the previous setting
Observable: After a caller's attempted change is refused, the previously saved state remains in effect.
Source: implied: by U-4, since refusal must have no settings effect

### C-22: An unsupported setting value is rejected
Observable: An authorized caller who submits an unsupported value through a reminder configuration operation receives a validation failure.
Source: implied: by U-4, since an unsupported value cannot configure a valid state

### C-23: A reminder setting applies only to its billing account
Observable: Changing one account's setting leaves the reminder setting of another account unchanged.
Source: implied: by U-4, since account-level authorization applies within the account

### C-24: Empty reminder processing produces no reminder
Observable: An enabled account with zero eligible invoices produces zero outbound reminders when evaluated.
Source: implied: by U-3, since each reminder requires an eligible invoice

### C-25: An invoice without a due date is skipped
Observable: No reminder is handed off for an invoice with no due date.
Source: choice: the schedule needs a known due date before it can tell whether the invoice qualifies

### C-26: An invoice without a usable delivery destination is skipped
Observable: An otherwise eligible invoice with a missing or invalid delivery destination produces no handoff.
Source: implied: by U-5, since there is no usable address for delivery

### C-27: The next handoff attempt uses the current destination for the billing recipient
Observable: If the billing recipient's delivery destination is corrected before the next attempt, the attempt uses the corrected destination.
Source: implied: by U-5, since correcting the address must affect future reminders

### C-28: Correcting invoice data can restore eligibility
Observable: After the missing information is corrected through the normal billing workflow, an otherwise eligible invoice can receive a reminder through automatic processing.
Source: implied: by U-5, since correcting the cause of a skip should allow follow-up

### C-29: A billing operator can determine why an otherwise actionable invoice was skipped
Observable: The operator can identify the prerequisite that prevented a reminder handoff for an invoice that would otherwise qualify.
Source: implied: by U-5, since the operator needs to know which invoice information to correct

### C-30: A temporary delivery rejection is retried automatically if another processing run is available in the current opportunity
Observable: When the delivery service definitively rejects an attempt as temporary, a later processing run in the same opportunity attempts handoff again if the invoice still qualifies.
Source: choice: a recoverable failure can be handled before the next scheduled date

### C-31: A permanent delivery rejection is not retried within the same opportunity for the same address
Observable: After the delivery service permanently rejects a handoff to an address, repeated processing of that opportunity produces zero further attempts to that address.
Source: choice: repeating the same permanently rejected handoff would not help the recipient

### C-32: An uncertain delivery result is resolved before another handoff for the same opportunity
Observable: After an attempt with an unknown result, there is no second handoff for that opportunity unless the earlier attempt is established to have been unaccepted.
Source: choice: preserving the recipient's duplicate limit takes priority after an ambiguous handoff

### C-33: An operator can distinguish the outcome of a handoff attempt
Observable: For a given invoice attempt, the operator can tell whether the delivery service accepted it, rejected it temporarily, rejected it permanently, or returned an uncertain result.
Source: implied: by U-6, since the operator needs to distinguish accepted sends from delivery problems

### C-34: One invoice's delivery failure does not prevent other eligible invoices from being processed
Observable: When one invoice's attempt fails, another invoice eligible in the same workload can still have its handoff attempted.
Source: implied: by U-6, since a recipient's delivery failure should not halt the rest of the workload

### C-35: Each invoice has at most 1 accepted reminder per scheduled opportunity
Observable: Repeated or overlapping processing, including after restart or rollback followed by restoration, results in at most 1 accepted handoff for the same invoice in the same opportunity.
Source: choice: each scheduled follow-up needs a single copy even if processing repeats

### C-36: Separate invoices are evaluated independently for the same recipient
Observable: A recipient who owes two separate eligible invoices can receive follow-up for both invoice obligations.
Source: implied: by U-7, since one invoice's reminder does not cover another debt

### C-37: The reminder feature imposes no additional invoice-count ceiling
Observable: At the billing system's supported invoice capacity, every eligible invoice can receive a reminder without a feature-specific count limit causing it to be skipped.
Source: choice: the existing invoice capacity is sufficient as the scope of the feature

### C-38: Existing invoices can qualify without reissue
Observable: An invoice issued before feature introduction receives a reminder if it qualifies after enablement using the information already on file.
Source: implied: by U-8, since unpaid invoices already on file are within the request

### C-39: Expired reminder opportunities are skipped
Observable: After a pause spanning multiple opportunities, an eligible invoice can receive a reminder for the current opportunity, with zero handoffs for expired opportunities.
Source: choice: a current follow-up serves the outstanding debt without replaying a backlog

### C-40: The saved enablement setting survives an ordinary restart
Observable: After restart, the account's reminder setting is the same as immediately before restart.
Source: implied: by U-9, since restarting processing should not change a billing decision

### C-41: Automatic processing resumes after an ordinary restart
Observable: When reminder processing is restored for an enabled account, eligible work resumes without requiring the administrator to enable the feature again.
Source: implied: by U-9, since unattended operation must survive interruptions

### C-42: Enabling the feature again resumes evaluation of existing invoices
Observable: After disablement followed by enablement, an overdue invoice still on file is evaluated without needing a new invoice event.
Source: implied: by U-10, since enablement applies to the account's current invoices

### C-43: Sending reminders leaves invoice due dates unchanged
Observable: The invoice shows the same due date before and after a reminder handoff when no other billing action changes it.
Source: implied: by U-11, since a reminder does not renegotiate payment terms

### C-44: Sending reminders leaves outstanding balances unchanged
Observable: The amount the payer owes is identical before and after a reminder handoff when no other billing action changes it.
Source: implied: by U-11, since a reminder does not post a charge or payment

### C-45: Sending reminders leaves invoice status unchanged
Observable: A reminder handoff alone leaves the invoice in its existing billing status.
Source: implied: by U-11, since sending a reminder does not settle or close an invoice

### C-46: Existing payment acceptance rules apply with reminders enabled
Observable: The existing payment workflow accepts or refuses a submitted payment under the same rules as before feature introduction.
Source: implied: by U-11, since reminders consume invoice payment information without changing payment handling

### C-47: Existing restrictions on invoice communication still apply
Observable: Where an existing billing rule forbids invoice communication to a recipient, an automatic reminder that falls under that rule is suppressed.
Source: implied: by U-2, since automation must respect existing recipient restrictions

### C-48: Existing manual invoice communication remains available under its existing rules
Observable: Where billing already offers manual invoice communication, the same authorized user can perform it with the same eligibility rules after reminders are introduced.
Source: implied: by U-12, since adding automatic follow-up does not replace existing billing workflows

### C-49: Rollback stops new automatic reminder handoffs
Observable: Once rollback to the previous version takes effect, zero new automatic reminders are handed off by this feature.
Source: implied: by U-12, since the previous version operates without the added automation

### C-50: Rollback preserves access to invoice records
Observable: In the previous version, invoices issued before or during the rollout still appear through its ordinary invoice workflow.
Source: implied: by U-12, since reverting reminder behavior must preserve the invoices billing acts on

### C-51: Rollback preserves posted payments
Observable: In the previous version, payment amounts posted before or during the rollout are still reflected in the corresponding invoices' balances.
Source: implied: by U-12, since reverting reminder behavior must preserve money already posted

### C-52: The saved reminder setting is available when the reminder-capable version is restored
Observable: After rollback followed by restoration, the account shows its last saved reminder setting.
Source: choice: restoring the last billing decision allows the operator to resume without configuring the account again

### C-53: Existing payments change invoice balances under the same rules with reminders enabled
Observable: An accepted payment updates the invoice balance by the amount the existing billing workflow would have applied before feature introduction.
Source: implied: by U-11, since reminder eligibility uses balances maintained by the existing payment workflow

### C-54: Invoice issuance retains its existing eligibility rules
Observable: An invoice that met the existing issuance rules before feature introduction can still be issued by the same authorized caller with reminders enabled.
Source: implied: by U-1, since an automatic reminder must not change which invoices can be issued

### C-55: Existing initial invoice delivery remains available under its existing rules
Observable: Where billing already sends an invoice at issuance, it still sends the invoice under the same conditions with reminders enabled.
Source: implied: by U-1, since a follow-up should preserve the original delivery of the invoice

