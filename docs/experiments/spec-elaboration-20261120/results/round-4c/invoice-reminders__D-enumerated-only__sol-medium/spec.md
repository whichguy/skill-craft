## Use cases

### U-1: A billing operator turns on automatic reminders to follow up on outstanding invoices
Flow: The operator sets up automatic reminders. When an unpaid invoice qualifies, a reminder is sent without the operator acting on that invoice.
Source: request

### U-2: A customer identifies the outstanding invoice from its reminder to arrange payment
Flow: The customer receives a reminder about a particular unpaid invoice. They can recognize which invoice requires attention and can use any payment route already available for it.
Source: implied: The request calls for reminding someone about a specific unpaid obligation.

### U-3: A billing operator checks first-time coverage to see which existing invoices enter reminders
Flow: The operator enables the feature with invoices already on file. Existing and newly issued eligible invoices are considered. Accounts with no eligible invoices send nothing. The operator can inspect what happened when the schedule was already overdue at activation.
Source: implied: The request applies to unpaid invoices without distinguishing by when they were created.

### U-4: A customer pays or receives an adjustment to stop or change future reminders
Flow: The invoice receives a full or partial payment, a credit, a write-off, a void, or an equivalent lifecycle update. Later reminder decisions use the current invoice state and outstanding amount.
Source: implied: The request limits reminders to unpaid invoices.

### U-5: A billing operator pauses or resumes reminders to control future sends
Flow: The operator disables reminders for their account and sees the disabled state. After re-enabling, the operator sees the enabled state and can inspect which reminders have already been sent. If a setting change cannot be confirmed, the operator can read the effective setting when it becomes available.
Source: implied: Setting up an automatic action calls for a way to manage its ongoing effect.

### U-6: A billing operator reviews reminder activity to answer a customer inquiry
Flow: The operator opens an invoice's reminder activity and checks when a reminder was due, what happened to it, and where an accepted reminder was addressed.
Source: implied: Automatic sends occur without an operator present to witness them.

### U-7: A billing operator corrects unusable invoice data to restore eligible reminders
Flow: An invoice lacks a usable billing email or due date. The operator sees the reason for the hold, corrects the underlying invoice, customer, or billing account record, and sees eligible work considered automatically.
Source: implied: An automatic reminder depends on being able to determine when it applies and who should receive it.

### U-8: A billing operator with insufficient access attempts a reminder action to learn whether it is permitted
Flow: A user without the required permission tries to inspect reminder activity or change the account setting. The action is refused.
Source: implied: Reminder controls and recipient information belong to the account responsible for the invoices.

### U-9: An operations owner restores processing after a failure to continue follow-up
Flow: A scheduling interruption or an email service failure stops progress. Operations can identify the interruption. After recovery, the service considers still-eligible work and exposes outcomes that require review.
Source: implied: An automatic process must cope with failures that happen without the billing operator present.

### U-10: An operations owner handles a large eligible population to keep reminders progressing
Flow: More invoices are eligible than delivery can accept at once. Operations can see a backlog while processing continues as capacity becomes available.
Source: implied: The request places no upper bound on the number of unpaid invoices.

### U-11: An operations owner rolls back a release to restore the previous invoicing experience
Flow: Operations stops new submissions before rollback and accounts for submissions that already started. Existing invoice workflows remain usable. If reminders are deployed again, prior send outcomes remain available for deciding whether a reminder is still owed.
Source: implied: Automatic external messages can outlive the release that initiated them.

### U-12: A billing operator edits an outstanding invoice to make later reminders reflect the correction
Flow: The operator changes the due date, billing destination, or balance of an issued invoice. A reminder still eligible for a later submission reflects the changed invoice. The operator can distinguish that submission from earlier activity.
Source: implied: U-4 and U-7 rely on current invoice data.

### U-13: An operations owner investigates an uncertain delivery to prevent a duplicate reminder
Flow: The email service stops responding during a submission. Operations sees an uncertain outcome and checks any conclusive evidence the email service provides. A restart or replay does not send the same reminder again merely because the result is unknown.
Source: implied: U-9 includes a failure after a message might have left the service.

### U-14: An operations owner prepares live dispatch to make reminders available to billing accounts
Flow: Operations verifies whether the deployment can run automatic processing and submit to customer destinations. A missing prerequisite prevents submission and is visible to operations. Once readiness is restored, enabled accounts can proceed under the ordinary reminder rules.
Source: implied: U-1 depends on an operational means of sending reminders.

## Clauses

### C-1: A scheduled reminder is initiated automatically
Observable: With reminders active, let a qualifying invoice reach a scheduled reminder time. Observe a reminder submission without anyone pressing send or having the app open.
Source: request

### C-2: A fully paid invoice is excluded from new reminder sends
Observable: Pay an invoice in full before its next reminder is initiated. The reminder is not sent.
Source: implied: The request restricts reminders to unpaid invoices.

### C-3: An account starts with automatic reminders disabled
Observable: On first availability, the account shows reminders disabled until explicitly enabled.
Source: choice: An account-wide outbound action should start with operator consent.

### C-4: An authorized operator can enable reminders for one billing account
Observable: Enable reminders in an authorized account. The account reports enabled.
Source: choice: Account-wide activation gives operators a single setup action.

### C-5: An authorized operator can disable reminders for one billing account
Observable: Disable reminders in an authorized account. The account reports disabled.
Source: choice: An operator needs a single way to pause outbound reminders.

### C-6: A disabled account excludes new reminder sends
Observable: Leave the account disabled across an otherwise eligible reminder time. No new automatic reminder is submitted for the account.
Source: choice: Disabling is a pause on outbound activity.

### C-7: Reminders are addressed to the invoice customer
Observable: A reminder for a qualifying invoice is addressed to a destination authorized to receive that customer's invoice.
Source: implied: The reminder must reach the party responsible for the unpaid invoice.

### C-8: The reminder identifies the invoice
Observable: A customer with more than one invoice from the business can tell which invoice the reminder concerns.
Source: implied: U-2 requires the customer to identify the debt.

### C-9: An account with no qualifying invoices produces zero automatic reminders
Observable: Enable reminders in an empty account or one with only fully paid invoices. No reminder is sent.
Source: implied: The request calls for reminders only for unpaid invoices.

### C-10: Eligible pre-existing invoices are within the automatic reminder population
Observable: An invoice issued before activation can qualify for a reminder without reissuing it.
Source: choice: Existing outstanding work should benefit from activation subject to the same rules as new work.

### C-11: The operator can inspect the effective reminder policy
Observable: In a selected account the operator can inspect whether reminders are enabled, the delivery channel, the scheduled offsets, the scheduling time zone and time, the catch-up and spacing rules, and the retry wait and attempt budget.
Source: choice: Operators need to understand the effect of activating the feature.

### C-12: The operator can inspect reminder activity for an invoice
Observable: Open an invoice and see each recorded reminder outcome for that invoice.
Source: choice: Invoice-scoped activity supports customer inquiries.

### C-13: Reading reminder activity requires invoice read access
Observable: A user without permission to read a selected invoice cannot see its reminder activity.
Source: implied: U-8 applies invoice access restrictions to invoice-related data.

### C-14: Changing reminder activation requires account billing settings authority
Observable: A user without billing settings authority cannot enable or disable reminders for that account.
Source: choice: Account-wide sending is governed by account settings authority.

### C-15: An unusable destination prevents submission
Observable: Without a usable destination for the intended recipient, the invoice produces no reminder submission.
Source: implied: U-7 has no reachable intended recipient.

### C-16: A temporarily unavailable dependency does not permanently stop reminders for other scheduled work
Observable: After an interruption ends, new eligible invoices continue to be considered automatically.
Source: implied: U-9 restores the automatic service.

### C-17: Capacity pressure leaves still-eligible work available for later consideration
Observable: When some eligible invoices cannot be considered at once, those invoices can still be considered as capacity frees up.
Source: choice: Large accounts should not silently lose work because it exceeds one processing window.

### C-18: Operations can stop new automatic reminders before rollback
Observable: After the deployment-wide stop takes effect, new reminders cease across all accounts.
Source: choice: Rolling back a live sender needs one deployment-wide stop.

### C-19: Reminder eligibility uses the invoice's authoritative billing record
Observable: When a customer record or a reminder activity entry disagrees with the billing record about what is owed, the amount on the billing record governs eligibility.
Source: implied: U-4 requires the actual invoice to be unpaid.

### C-20: Reminder eligibility requires a positive collectible balance
Observable: In an otherwise qualifying issued invoice, a remaining balance of 25.00 USD qualifies after a partial payment or partial credit. A zero or negative collectible balance does not qualify.
Source: choice: A positive remaining obligation is the useful definition of unpaid for partial settlements and overpayments.

### C-21: Only issued invoices with an active collection obligation qualify
Observable: An issued invoice open for collection can qualify. A draft, voided or canceled invoice, fully paid or fully credited invoice, written-off invoice, archived or deleted invoice, or invoice on a collection hold cannot qualify while in that state. A disputed invoice is excluded while the dispute places it on a collection hold. An unrecognized disposition cannot qualify until billing can establish that the invoice is issued and open for collection.
Source: choice: Reminders follow collectible, customer-facing obligations. These are business dispositions, which can be represented as states, flags, or ledger outcomes.

### C-22: A valid due date is required for scheduling
Observable: An invoice with no due date or with an impossible calendar date such as February 30 has no scheduled submission.
Source: choice: An invoice without a calendar due date cannot use a due-date-relative schedule.

### C-23: Automatic reminders use email
Observable: A qualifying reminder is submitted as email.
Source: choice: Email supplies a single asynchronous channel with an invoice-specific recipient.

### C-24: A reminder uses one current billing email per invoice
Observable: The invoice's current billing email takes precedence. If it has no invoice-specific email, use the linked customer's current billing email for that account if there is exactly one designated address. An invoice-specific address that is present but invalid is held for correction. A missing or ambiguous customer fallback is held for correction. No reminder is copied to other recipients.
Source: choice: A single explicit billing destination avoids guessing who may see the invoice.

### C-25: The reminder email identifies the billing business
Observable: The recipient can see the billing account's customer-facing business name.
Source: choice: The customer-facing business name lets the recipient recognize who is requesting payment.

### C-26: The reminder email shows the outstanding amount in the invoice currency
Observable: For an invoice with 25.00 USD remaining on a 100.00 USD original total, the email identifies 25.00 USD as the amount currently due.
Source: choice: The current balance helps a customer who has already paid part of the invoice.

### C-27: The reminder email shows the current invoice due date
Observable: The recipient can read the due date that applied when the message was submitted.
Source: choice: The due date puts the payment request in context.

### C-28: The reminder email points the customer to the existing invoice payment route when one is available
Observable: If the original invoice has a customer-facing payment link or instructions, the reminder gives access to that same payment route. If the invoice has neither, the reminder can go out without a payment route.
Source: choice: Use the invoice's payment process without requiring a new checkout or withholding an otherwise useful reminder.

### C-29: Each due date creates reminder milestones 1, 7, and 14 calendar days later
Observable: For an invoice due November 20, 2026, the milestones are November 21, November 27, and December 4, 2026.
Source: choice: One, seven, and fourteen calendar days after the due date provide a finite overdue follow-up schedule.

### C-30: Each milestone opens at 09:00 UTC on its calendar day
Observable: A November 21 milestone cannot send before November 21 at 09:00 UTC and is due at that instant. Daylight saving changes and account locale do not shift that instant.
Source: choice: UTC gives a determinate schedule without an additional account setting.

### C-31: Activation is the reminder setting an account operator can change
Observable: The account offers enable and disable. Channel, cadence, time zone, time, catch-up, templates, and per-invoice overrides are not editable reminder settings.
Source: choice: One toggle is sufficient to set up the requested automatic behavior.

### C-32: Access to the effective account policy requires billing settings authority
Observable: An invoice reader who lacks billing settings authority cannot inspect the account's reminder settings.
Source: choice: Account-level policy follows the permission boundary of the control that changes it.

### C-33: An account uses its own activation setting
Observable: Enable account A while account B is disabled. Account B remains disabled even if both accounts use the same invoice reference or customer email.
Source: choice: Activation is consent for one billing business.

### C-34: Missing or invalid reminder inputs are visible on an otherwise eligible invoice
Observable: An issued invoice otherwise open for collection shows the categories that prevent scheduling or submission. These are missing or invalid due date, missing or invalid destination, ambiguous customer destination, unavailable or invalid collectible balance or currency, missing customer-facing reference, and missing customer-facing business name. Multiple applicable reasons may be displayed together.
Source: choice: Recoverable invoice data problems need a reason that an operator can act on.

### C-35: Corrected invoice data can restore automatic consideration
Observable: Correct the prerequisite that held an otherwise eligible invoice. The current invoice is considered automatically without reissuing it.
Source: implied: U-7 makes the correction effective in the automatic process.

### C-36: Catch-up considers only the latest milestone that has opened
Observable: First enable reminders for a qualifying invoice 10 days after its due date at noon UTC. Only day seven is considered for submission at activation, and day fourteen becomes the candidate when it opens. After day fourteen opens, an unavailable or closed day-fourteen milestone does not cause an older milestone to submit.
Source: choice: A delayed start calls for one current follow-up.

### C-37: A newer milestone starting submission permanently closes older ordinals to submission
Observable: Once a day-seven submission starts, day one cannot start a submission even if day seven is rejected, the due date is edited, or evidence resolves an uncertain day-one attempt in favor of retry. A day-seven milestone opening without starting submission does not permanently close day one.
Source: choice: Catch-up must not make the customer receive backlogged messages in a burst.

### C-38: A milestone keeps its identity across due-date edits
Observable: After a day-one reminder is accepted, edit the due date so day one falls in the future. Day one cannot send again when the new day-one time arrives. An unfinished day-seven or day-fourteen milestone is evaluated relative to the revised due date.
Source: choice: The account, invoice, and milestone ordinal identify the same follow-up through a due-date correction.

### C-39: A scheduled send uses the current submission eligibility at the point of starting submission
Observable: With a reminder ready to send, commit a change before its email submission begins. The feature uses the current account activation, deployment stop, invoice disposition, collectible balance, due date, latest open milestone, minimum spacing, retry eligibility, required message data, billing destination, and live readiness. If any required condition fails or the relevant record cannot be read authoritatively, submission does not start.
Source: choice: Checking all applicable gates at submission gives invoice edits, pauses, and stops a common effective boundary.

### C-40: A scheduled message uses the current invoice content at the point of starting submission
Observable: Edit the customer-facing invoice reference, billing business name, outstanding amount, currency, due date, billing destination, or available payment route before the submission begins. The submission reflects the latest committed values required for that message.
Source: choice: Using one current invoice view at submission gives the customer a coherent account of what is owed.

### C-41: An in-flight submission can finish after a qualifying condition changes
Observable: Disable reminders, settle the invoice, edit it, or stop processing after the email service submission has started. The result of that already-started submission can still be recorded.
Source: choice: Changes govern submissions the feature can still prevent.

### C-42: A reminder milestone has at most one submission in progress
Observable: Trigger overlapping evaluations or replay the same scheduled work for an account's invoice and milestone. The email service observes at most one submission in progress for that milestone.
Source: choice: One in-flight submission avoids duplicates while the result is pending.

### C-43: A retry after definitive temporary non-acceptance waits at least 1 hour
Observable: When the email service conclusively reports temporary non-acceptance, the earliest a still-eligible retry can start is 1 hour after non-acceptance is established.
Source: choice: Spaced retries recover intermittent failures without an immediate repeat to the same destination.

### C-44: Exhaustion of the retry budget closes the milestone
Observable: After the third submission returns conclusive temporary non-acceptance, the milestone is closed to automatic retry.
Source: choice: A failed milestone must eventually stop trying.

### C-45: Definitive permanent non-acceptance closes the milestone
Observable: After a permanent rejection, another automatic submission cannot start for that milestone.
Source: choice: A conclusive permanent failure requires correction for future reminders.

### C-46: An unconfirmed submission outcome prevents automatic resubmission of that milestone
Observable: If the service may have accepted a submission before communication was lost, including a timeout or interruption during submission, the result is marked uncertain and automatic reevaluation does not resubmit it while uncertain.
Source: choice: Missing confirmation is insufficient evidence that another email is safe.

### C-47: Conclusive evidence can resolve an uncertain outcome
Observable: When authoritative evidence tied to the original submission arrives, the attempt moves from uncertain to the established result: accepted, temporary non-acceptance, or permanent non-acceptance. The ordinary rules for that result apply to any remaining action.
Source: choice: Recovery can use verifiable evidence without guessing.

### C-48: An already accepted milestone is closed to further submissions
Observable: Replay scheduled work after acceptance. The same account, invoice, and milestone ordinal produce no further submission after a restart, pause, re-enable, recipient edit, due-date edit, payment reversal, or re-deployment.
Source: choice: Successful outcomes must survive changes that do not create a different invoice.

### C-49: A pause does not open a new reminder sequence
Observable: Disable and re-enable reminders. Previously accepted, permanently failed, exhausted, superseded, and uncertain milestones retain their outcomes. An unfinished milestone can submit only if it meets the ordinary catch-up, eligibility, and retry rules.
Source: choice: Resuming is continuation of the same follow-up.

### C-50: A reopened obligation uses its original reminder sequence
Observable: Reverse a payment, release a collection hold, or otherwise return the same invoice to collectible status. It can submit only for a still-available milestone under the current schedule.
Source: choice: A reopened invoice is the same debt for reminder history purposes.

### C-51: A failure for one invoice does not block eligible work on other invoices
Observable: One invoice has invalid data, a pending retry, a permanent failure, or an uncertain outcome. Other eligible invoices can continue while destination-specific delivery is available.
Source: choice: A problem with one obligation should not suspend unrelated work.

### C-52: Repeated outcome reports do not multiply reminder activity
Observable: Deliver the same acceptance or rejection report twice for a submission. The activity still shows one submission with its outcome.
Source: choice: Operators need to distinguish repeat reports from new send attempts.

### C-53: Late outcome evidence is associated with its original submission
Observable: An outcome for an older attempt arrives after a later milestone opens or sends. Only the original attempt's outcome is updated, subject to evidence reconciliation.
Source: choice: Arrival order does not determine which reminder a report describes.

### C-54: Accepted activity survives a processing interruption
Observable: Interrupt processing before, during, or after activity becomes visible. A submission with confirmed acceptance that is recoverable from authoritative evidence is shown as accepted after recovery. If acceptance cannot be established and the submission may have begun, the outcome is uncertain.
Source: choice: Restart recovery must preserve evidence without guessing whether to send again.

### C-55: The deployment-wide stop takes precedence over account activation
Observable: While operations has stopped dispatch, an account operator can still change activation but an enabled account cannot start submissions. Releasing the stop makes enabled accounts eligible under the ordinary rules.
Source: choice: Operations must be able to stop sending even when accounts have opted in.

### C-56: A rollout preserves enough prior reminder activity to resume safely
Observable: Stop dispatch, roll back, then redeploy with the same invoice data. Past accepted, failed, superseded and uncertain milestones retain their disposition, as do attempts counted against any remaining retry budget.
Source: choice: Rollback and redeployment must not turn previous messages into new sends.

### C-57: An invoice's reminder activity distinguishes its milestone outcomes
Observable: The activity distinguishes upcoming, due, held for invoice data, ineligible for collection, skipped while a later milestone is open, submitting, retry scheduled, accepted, failed, uncertain, superseded, and blocked by conflicting outcome evidence.
Source: choice: Operators need to distinguish due work from work that finished or needs intervention.

### C-58: An invoice's reminder activity identifies the milestone and its schedule
Observable: For a displayed milestone the operator can identify day one, seven, or fourteen, its current scheduled timestamp if it has one, and its outcome or hold. For an attempt the operator can identify the originally planned timestamp even if the due date is edited later.
Source: choice: The operator needs to distinguish a reschedule from a submission.

### C-59: A recorded submission exposes its audit facts to an authorized invoice reader
Observable: Each attempt exposes its start timestamp, destination, result, and result timestamp when known. The result is pending, accepted, definitively declined as temporary or permanent, or uncertain.
Source: choice: Operators need what was sent where and when, or why it could not be confirmed.

### C-60: Reminder delivery depends on a separately authorized live email submission service
Observable: An enabled account cannot send while the deployment lacks a valid sender identity, authorization to submit from that identity, authorization to reach live recipients, or a working automatic processing service.
Source: choice: No production host or vendor is identified. A live email service must permit the sender and destination before taking responsibility for delivery.

### C-61: Non-production processing cannot send to live invoice recipients
Observable: With production-like invoice data in a development, test, or staging deployment, automatic reminders produce zero submissions addressed to live invoice recipients.
Source: choice: Environment-level isolation allows validation without contacting real customers.

### C-62: Email-service acceptance means the service has taken responsibility for the message
Observable: A positive submission acknowledgement shows acceptance in reminder activity. For ordinary SMTP submission, the final 250 completion reply after the message data is the acknowledgement. Acceptance alone does not appear as confirmation that the recipient received or read the email.
Source: implied: U-6 distinguishes the known outcome from receipt. SMTP separates acceptance from delivery under [RFC 5321 §§4.2.5 and 6.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5).

### C-63: A conclusive negative email-service response is classified by whether the service permits retry
Observable: For an SMTP submission, a definitive 4xx reply rejecting the submission is temporary non-acceptance. A definitive 5xx reply rejecting it is permanent non-acceptance.
Source: implied: U-9 and U-13 must honor the submission service's acknowledgement rules. For SMTP these are [RFC 5321 §§4.2.1 and 4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.1).

### C-64: An SMTP address outside the applicable envelope limits is unusable for reminder submission
Observable: With ordinary SMTP submission, an address with a local part exceeding 64 octets, a domain exceeding 255 octets, or a full envelope path exceeding 256 octets including punctuation is held as an invalid destination.
Source: implied: U-7 needs a destination the service can accept within the SMTP envelope limits in [RFC 5321 §§4.5.3.1.1–3](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.1).

### C-65: Hosted delivery limits can delay otherwise eligible reminder work
Observable: If the live email service restricts throughput or concurrent submissions, work above its admitted capacity waits for later consideration. The exact per-second, per-day, and concurrency figures are unconfirmed because no live email deployment is specified.
Source: implied: U-10 must honor the selected email service's admission limits if it imposes them.

### C-66: Operations can inspect the deployment limits that affect reminders
Observable: Before live dispatch, operations can determine the deployed host's scheduling and execution limits and the email service's send rate, quota, maximum message size, and submission timeout, or determine that a particular limit does not apply. Exact figures are unconfirmed for the unspecified production host and email provider.
Source: choice: Operations needs effective limits to distinguish a feature failure from a host or provider restriction.

### C-67: Enabling reminders does not wait for email delivery
Observable: The account's enable action reports the effective setting even if the email service is slow or unavailable.
Source: choice: The account control confirms the setting without requiring an asynchronous service to finish delivery.

### C-68: Sustained healthy processing starts ready submissions within 1 hour
Observable: If one milestone stays continuously ready and service capacity is available for all ready work throughout, its submission starts within 1 hour of becoming ready. This applies to milestones, newly corrected or resumed work, and retries when their wait ends. Under interruption or saturation this time bound does not apply.
Source: choice: A one-hour processing window makes automatic follow-up observable without promising provider delivery times.

### C-69: An attempt cannot appear to be actively submitting indefinitely
Observable: If an attempt still has no conclusive result 15 minutes after it started, it is shown as uncertain by that point when reminder processing is available, or upon recovery if it was unavailable. A conclusive result received afterward follows the uncertainty-resolution rule.
Source: choice: A 15-minute reporting bound exposes stalls without assuming the external attempt failed or can be canceled.

### C-70: An operations owner can inspect reminder service health
Observable: Operations can inspect the deployment stop state, readiness blockers, last successful evaluation time, ready work count, time elapsed since the oldest ready milestone became continuously ready, and counts of retained attempts with definitive failure or uncertain outcomes. If no evaluation has succeeded, there is no success timestamp. If no work is ready, the count is zero and there is no oldest ready age. A measure that cannot be determined is shown as unknown.
Source: choice: U-9 and U-10 require visible signals for stalled, saturated, and ambiguous work.

### C-71: Sustained capacity eventually serves every continuously eligible invoice in a finite ready population
Observable: With a backlog and continuing positive capacity to start reminders, each invoice that remains ready gets an opportunity. Adding new ready invoices does not cause an older still-ready invoice to wait indefinitely.
Source: choice: U-10 requires progress at scale without assuming a host-specific batch size or throughput.

### C-72: Automatic reminders preserve normal invoice lifecycle actions
Observable: With reminders enabled or disabled, existing authorized actions to create, issue, edit, cancel or void, and delete an invoice remain available under their existing rules where those actions are already supported.
Source: implied: The request adds follow-up to an invoice lifecycle without replacing that lifecycle.

### C-73: Automatic reminders preserve normal settlement actions
Observable: Existing recording of full and partial payments, recording of credits, write-offs, and reversals remains available under its existing rules where supported, even if reminder processing is unavailable.
Source: implied: The request changes follow-up on a debt while the existing billing workflow manages the debt.

### C-74: Reminder processing does not change the billing terms or settlement of an invoice
Observable: A reminder becoming due, held, submitted, accepted, failed, uncertain, or superseded creates no charge, payment, credit, write-off, or reversal. The amount, currency, balance, due date, and invoice lifecycle status remain as set by billing.
Source: implied: The request is for a reminder about an obligation.

### C-75: Automatic reminder controls preserve existing invoice communications
Observable: Where invoices can already be issued or resent to customers, or manual reminders can already be sent, these communications continue under their existing rules while automatic reminders are enabled, disabled, or deployment-stopped.
Source: implied: U-5 controls automatic reminders only.

### C-76: A reminder preserves customer authorization for the invoice and payment route
Observable: Following a route from a reminder grants only the access the ordinary customer-facing invoice or payment route grants. A recipient gains no operator access, cross-account access, or access to unrelated invoices by following it.
Source: implied: U-2 uses the authority of the existing customer payment route.

### C-77: Reminder data is scoped to the account that owns the invoice
Observable: With invoice references or customer emails shared by accounts A and B, inspecting or sending a reminder for account A uses only account A's invoice, billing identity, destination authorization, payment route, setting, and reminder activity. A user with access only to A cannot retrieve B's reminder data by supplying B's identifiers.
Source: implied: U-8 restricts each account's reminder information to its authorized audience.

### C-78: Reminder authorization applies through every exposed entry point
Observable: An unauthorized user is refused the same reminder read or control action from an interface, a direct link, or a callable interface if offered. Refusal exposes no requested reminder data and makes no setting change.
Source: implied: U-8 concerns the action and its data regardless of how it is reached.

### C-79: Deployment-level reminder controls require operations authority
Observable: An account billing operator without operations authority cannot see deployment-wide service health or change the deployment-wide stop.
Source: choice: Deployment-wide operations affect all accounts.

### C-80: Operations health views do not expose customer reminder details by default
Observable: An operations owner without separate invoice read access sees service readiness, activity aggregates, and attempt outcomes needed for reconciliation without the invoice's recipient address, amount, or rendered message.
Source: choice: Deployment health can be diagnosed without access to invoice contents.

### C-81: Reminder emails include only information meant for the invoice customer
Observable: The invoice-specific content is limited to the customer-facing reference, balance and currency, due date, and any existing customer-facing payment route. The message omits internal notes, operational failure details, other invoices, other recipients' addresses, and private account credentials.
Source: choice: Limiting invoice data to customer-facing details for one obligation reduces disclosure.

### C-82: Post-acceptance delivery failures do not reopen the submitted milestone
Observable: After the email service reports a bounce or other final delivery failure, the previously accepted milestone stays closed to new submissions.
Source: choice: A delegated delivery failure is different from original submission rejection.

### C-83: Reminder history remains associated with an invoice across changes to its human-facing reference
Observable: Two distinct invoices sharing the same visible reference have separate reminder activity. Renaming an invoice reference does not transfer or reset its milestones.
Source: implied: U-2 and U-6 concern the same underlying invoice, even when references are edited or reused.

### C-84: Reminder rollout preserves the existing attributes of prior-version invoices
Observable: After deployment, prior-version invoice records keep their existing status, balance, currency, due date, customer relationship, billing destination, customer-facing reference, and payment route where those values exist.
Source: implied: U-3 changes follow-up for existing invoices while those invoices remain the same billing obligations.

### C-85: Rolling back reminders leaves billing and customer access usable
Observable: After reminder dispatch is stopped and the prior invoicing version is restored, invoice records, outstanding balances, settlements, and existing customer invoice and payment access remain available under that version's rules.
Source: choice: Rollback disables the added sending behavior while preserving the billing data customers still need.

### C-86: A reminder email shows the invoice's customer-facing reference
Observable: The email about invoice INV-42 includes the value INV-42 as the customer-facing invoice reference.
Source: choice: Use the identifier the customer can match to their invoice.

### C-87: A reminder requires the billing facts necessary to identify the debt
Observable: Even with a usable date and destination, there is no submission if the customer-facing invoice reference or business name is missing, or if the collectible balance or its currency is unavailable or invalid.
Source: choice: A payment request must identify the obligation without inventing financial data.

### C-88: The schedule uses the invoice's authoritative customer-facing calendar due date
Observable: Where the invoice displays January 31 as its due date, the day-one milestone opens February 1 at 09:00 UTC regardless of the operator's time zone. Weekends, holidays, and month or year boundaries do not move a milestone to another day.
Source: choice: Calendar offsets should follow the due date understood by the customer.

### C-89: Invoice age alone does not expire the final milestone
Observable: First enable reminders for a 90-day overdue invoice that remains collectible. Day fourteen can submit if it is otherwise eligible and unfinished.
Source: choice: An outstanding debt can warrant one catch-up reminder even after a long gap.

### C-90: Potentially delivered reminders for the same invoice are spaced at least 24 hours apart at submission
Observable: A day-one attempt starts at 08:30 UTC on day seven, 30 minutes before the day-seven milestone opens. While that attempt is submitting, accepted, or uncertain, day seven cannot start before 08:30 UTC the next day. Conclusive non-acceptance of the earlier attempt removes this spacing restriction. The spacing is per invoice even when two invoices use the same destination.
Source: choice: A late submission should not be immediately followed by a different milestone for the same invoice.

### C-91: A reminder milestone allows at most 3 submissions
Observable: For one invoice and milestone across recovery, policy changes, and edits, the delivery service sees at most 3 submissions including the initial one. Pre-submission delays and holds do not count. An attempt that may have reached the service counts while its result is uncertain.
Source: choice: Keep the retry budget finite despite restarts and changes to the invoice.

### C-92: Invoice activity exposes the earliest retry time for a temporary failure
Observable: For a retry that is still available, the operator can find its earliest permissible retry time, even if a pause or capacity deferral will delay it further.
Source: choice: An operator can distinguish a scheduled retry from a silently stalled attempt.

### C-93: Definitively closed failures are visible as failed milestones
Observable: Activity distinguishes a failure closed by permanent non-acceptance from one closed by exhaustion of the submission budget.
Source: choice: The billing operator needs to know whether an automatic retry remains available.

### C-94: Invoice activity exposes reported post-acceptance delivery failures
Observable: If the email service reports a bounce or other final delivery failure, the affected attempt displays that failure alongside its original acceptance. If the service offers no downstream outcome, the activity can show acceptance alone.
Source: choice: Acknowledgement and later delivery failure are separate facts an operator may need.

### C-95: Repeating an account activation command is idempotent
Observable: Enable an enabled account or disable a disabled account again. The setting stays in the requested state without restarting the schedule or clearing activity.
Source: choice: A repeated command after a lost response should be safe.

### C-96: A settings change confirms success only after it takes effect
Observable: If changing account activation or the deployment stop fails, the caller gets a failure or unconfirmed result.
Source: choice: A failed or ambiguous settings request must not display a false confirmation.

### C-97: Overlapping successful account setting changes have one effective order
Observable: If opposing changes overlap, a read after both have completed shows the last effective change. A non-overlapping later successful change takes precedence over an earlier one.
Source: choice: Concurrent control requests must leave a determinate setting without imposing an order on overlapping requests.

### C-98: A pre-submission interruption leaves work available under the ordinary eligibility rules
Observable: Processing stops before contact with the email service can have begun. If that fact is conclusive, recovery considers current work without counting an attempt for the interrupted preparation. If contact may have begun, recovery applies the submission outcome rules.
Source: choice: Recovery should distinguish work that never reached the external boundary from work that might have.

### C-99: An outcome report must verifiably apply to the original attempt
Observable: A report with no trustworthy association to an existing submission does not change reminder activity or make a retry available.
Source: choice: A guessed or unauthenticated report must not cause an erroneous replay.

### C-100: Recording a conflict in conclusive outcome evidence stops further submissions for the affected milestone
Observable: If apparently authoritative reports conflict about acceptance of the same attempt, no further submission for that milestone starts after the conflict becomes known.
Source: choice: Conflicting evidence is unsafe grounds to continue retries.

### C-101: Reminder history is retained for as long as the invoice can be resumed
Observable: Deactivate, archive, or temporarily delete a restorable invoice under an existing billing workflow. Restoring it brings back the same reminder history and attempt counts.
Source: choice: A reversible business action must not erase the history used to suppress duplicates. The duration is tied to invoice retention, whose exact period is unconfirmed.

### C-102: A newly issued invoice has its own reminder history
Observable: Permanently remove an invoice and issue a different invoice using the same customer-facing reference. The new invoice can start its own schedule under the ordinary rules.
Source: implied: U-3 and U-6 concern individual invoices.

### C-103: Account settings remain effective through routine service restarts
Observable: Restart reminder processing with an account enabled or disabled. The account reports the same setting after recovery.
Source: choice: An automatic feature should continue under the operator's existing decision.

### C-104: Eligibility has no product-imposed invoice-count cap
Observable: A qualifying invoice is not excluded merely because it is beyond a particular count of invoices in an account or deployment. Delivery capacity may delay it. There is no fixed product dispatch deadline during saturation.
Source: choice: U-10 calls for continued coverage while accommodating host and provider limits.

### C-105: A ready reminder is distinct from a reminder that is merely due
Observable: Operations counts one ready reminder for an invoice when its latest open milestone can start a submission immediately under the applicable gates, ignoring capacity pressure. Future milestones, data holds, closed gates, active submissions, unelapsed retry or spacing waits, and terminal or uncertain milestones do not count as ready.
Source: choice: U-10 needs a backlog count of actionable work.

### C-106: Redeployment preserves account activation choices unless an authorized operator changes them
Observable: Stop dispatch and roll back, then redeploy with the same accounts. Each account has its previous activation setting.
Source: choice: Restoring the release should retain operator intent without silently reopening live sending.

### C-107: An automatic reminder asks the customer to address the outstanding payment
Observable: From the reminder the customer can tell that they are being asked to pay the identified invoice.
Source: implied: The request is for a reminder about unpaid invoices.

### C-108: Reminder activity preserves previous attempts when a milestone is superseded
Observable: After day seven starts and closes day one to further submission, the invoice still shows any day-one attempts and their known outcomes. An unresolved earlier attempt can still be reconciled even though it cannot result in another submission.
Source: choice: Supersession closes future work while preserving the evidence of what happened.

### C-109: The deployment-wide stop remains effective across rollback and redeployment
Observable: Set the stop, roll back, then redeploy. No new automatic submission starts before an authorized operations owner explicitly releases the stop.
Source: choice: Redeployment should not act as authorization to restart live dispatch.

### C-110: Unresolved submissions remain identifiable through rollback
Observable: Stop dispatch while an attempt is pending and roll back before a result is known. After redeployment the attempt is identifiable as accepted or definitively declined if evidence has established the result, or uncertain otherwise. It is never presented as an untouched milestone.
Source: choice: Recovery after rollback must account for each submission that could have left the product.

### C-111: Operations reconciliation provides a reference for the original submission
Observable: For an attempt with an uncertain or conflicting outcome, an authorized operations owner can obtain a reference that links it to available email-service evidence without needing the rendered message or customer email.
Source: choice: U-13 requires a way to investigate a particular submission without opening unrelated invoice data.

### C-112: A successful empty evaluation is visible as normal operation
Observable: With working processing and no eligible invoices, operations sees the last successful evaluation time advance even though the ready count stays at zero.
Source: choice: An empty workload needs to be distinguishable from a stalled scheduler.

### C-113: Permanent deletion makes the invoice’s reminder activity unavailable
Observable: After permanent deletion, callers cannot retrieve invoice-specific reminder activity for the deleted invoice.
Source: choice: Reminder access and dispatch follow the existence of the billing record.

### C-114: A billing email is usable only if it identifies one mailbox supported by the submission service
Observable: A designated value that is only a display name, is a group or list of addresses, is malformed under the chosen service's mailbox syntax, or exceeds its address limits produces a destination hold. A valid single-mailbox address can qualify without evidence that the mailbox has ever received a message.
Source: choice: Detect invalid input before sending while leaving mailbox deliverability to the delivery service.

### C-115: Current eligibility and historical attempt outcomes can be inspected independently
Observable: An invoice with a previously accepted reminder is later paid, held, archived where still readable, or paused at account level. Its historical attempt still shows acceptance while any future milestone remains subject to the current invoice and account conditions.
Source: choice: A later eligibility change should not be mistaken for a change in what was sent.

### C-116: Existing manual communications do not consume automatic reminder milestones
Observable: If manual reminders or invoice resends are already supported, using one does not count as an automatic reminder attempt or reopen a closed automatic milestone.
Source: choice: The requested automation adds its own cadence without repurposing the existing communications.

### C-117: A permanently deleted invoice cannot start another automatic submission
Observable: Permanently delete an invoice before its next submission begins. Later evaluation produces no submission for that invoice even if its old work is replayed.
Source: implied: U-4 requires an obligation that still exists when reminders begin.

### C-118: A displayed acceptance remains part of the attempt history after recovery
Observable: Once acceptance is shown for an attempt, restarting processing preserves that recorded acceptance for as long as the invoice history is retained. A later conflicting report can be recorded alongside it but cannot erase it.
Source: choice: Recovery must retain a confirmed outcome already visible to the operator.
