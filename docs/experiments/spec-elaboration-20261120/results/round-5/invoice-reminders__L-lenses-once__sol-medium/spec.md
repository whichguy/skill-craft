## Use cases

### U-1: A billing operator enables automatic reminders to follow up on unpaid invoices
Flow: The operator opens billing controls for an account they manage, sees whether automatic reminders are enabled, enables them, then returns later and sees that the setting persisted. Enabling again leaves the feature enabled. A person without the account's billing-settings permission cannot enable or disable it.
Source: implied: “Set up automatic reminders” requires an authorized way to put the automation into effect.

### U-2: An invoice recipient receives a reminder so they can act on an overdue invoice
Flow: An issued invoice remains payable after its due date. The recipient receives an email without anyone initiating that send. They can identify the biller and invoice, see what is still due, and use the existing invoice payment instructions. A draft, a future-due invoice, and an invoice with no payable balance generate no reminder.
Source: request

### U-3: A billing operator relies on follow-ups while an invoice remains unpaid
Flow: The invoice remains unpaid past successive scheduled dates. The recipient receives later reminders within the policy's cap. A partial payment changes the amount shown in the next reminder. A payment or other change that removes the obligation stops new handoffs as soon as the change is recorded.
Source: implied: Continuing reminders for unpaid invoices requires distinguishing invoices that still need payment from invoices whose payment obligation has ended.

### U-4: A billing operator enables reminders for an account with existing invoices
Flow: Existing issued invoices are evaluated with newly issued invoices. An already overdue invoice can receive the most recent applicable reminder. An account with no eligible invoices generates no customer messages. An account with a large eligible backlog can observe progress without any invoices being silently omitted.
Source: implied: The request says “unpaid invoices” without limiting the population to invoices created after setup.

### U-5: A billing operator corrects incomplete invoice information so reminders can proceed
Flow: An overdue invoice has a missing due date, an unusable billing address, or incomplete payment information. The operator sees the reason it cannot be sent and corrects the invoice through existing billing controls. A later evaluation uses the corrected values if a reminder opportunity remains.
Source: implied: A reminder depends on knowing when it is due, who should receive it, and which obligation the recipient can pay.

### U-6: A billing operator pauses and resumes automatic reminders to control outgoing messages
Flow: The operator disables reminders while an invoice is pending or a delivery is retrying. No new handoff begins after the disable takes effect. On re-enable, invoices are evaluated against the current date and previous handoffs. An email already handed off before disable may still arrive.
Source: implied: Operating an automatic sender requires a way to stop outgoing work and resume safely.

### U-7: A billing operator investigates failed or uncertain delivery to understand what the recipient may have received
Flow: The operator opens the invoice's reminder information to see whether it is waiting, blocked, accepted, failed, or unresolved. A temporary failure known to precede acceptance may retry within the limit. An uncertain result remains visible while it is investigated. Late delivery information can resolve the uncertainty.
Source: implied: Sending a reminder requires an external delivery outcome that may fail or arrive after the send attempt.

### U-8: A billing operator changes an invoice while a reminder is pending so current billing facts govern the send
Flow: A due date, contact, amount, issue status, or payment status changes during processing. A change recorded before handoff governs the send. A change recorded after handoff governs later work. A repeated or overlapping evaluation does not send the same reminder twice.
Source: implied: Automatic processing can overlap invoice edits, payment events, or repeated processing.

### U-9: A service operator restores reminder processing after an interruption
Flow: Processing stops or a delivery dependency becomes unavailable. The operator sees the interruption and can restore ordinary processing. After recovery, due work is re-evaluated using current invoice facts and previous outcomes. Ambiguous past sends are not blindly repeated.
Source: implied: An automatic reminder service has to recover from interruptions without losing track of work it may already have performed.

### U-10: A service operator rolls back the reminder rollout so billing can continue
Flow: The operator stops new automatic handoffs and returns to the previous billing release or rollout state. Existing invoice and payment operations continue. If reminders return later, previously recorded reminder outcomes still govern duplicate prevention. Already handed-off mail can finish delivery.
Source: implied: Invoice operations must continue when the reminder feature is withdrawn.

## Clauses

### C-1: Enabled automatic reminders require no per-invoice send action
Observable: With the account enabled, a qualifying invoice reaches a reminder opportunity and the system initiates the reminder without an operator opening the invoice, pressing Send, or keeping a session open.
Source: request

### C-2: Each billing account has an independent reminder setting
Observable: Enabling reminders for one account leaves the setting for a second account as it was, including when the same person administers both.
Source: choice: The account is the narrowest shared operating scope that avoids invoice-by-invoice setup.

### C-3: Automatic reminders initially start disabled
Observable: A new or pre-existing account with no saved reminder setting shows reminders disabled and initiates zero automatic reminder handoffs.
Source: choice: The billing operator controls when customer communication begins.

### C-4: The billing-settings permission controls reminder configuration
Observable: An operator with the account's billing-settings permission can enable or disable reminders. A person without it receives an access refusal when attempting either action through any exposed entry point.
Source: implied: U-1 requires an authorized operator for outgoing billing communications.

### C-5: A saved enable or disable decision persists
Observable: After a successful setting change, an authorized operator returning in a new session or after a service restart sees the saved value.
Source: implied: U-1 requires an enduring setup decision.

### C-6: Repeating the same setting decision has no additional sending effect
Observable: Submitting enable twice leaves one enabled account and does not add reminder opportunities. Submitting disable twice leaves the account disabled.
Source: implied: U-1 includes repeating setup without creating extra sends.

### C-7: A refused setting change leaves the effective value intact
Observable: An unauthorized or invalid update is refused. An update known to have failed to save reports failure. Reading the setting again shows its last successfully saved value. If the save outcome cannot be determined, the caller is told it is unknown and can read the current value.
Source: implied: U-1 depends on knowing whether reminders were put into effect.

### C-8: An enabled account uses one automatic reminder policy
Observable: The operator's reminder-specific controls are enable and disable. The operator can inspect reminder timing, status and failure reasons. Per-invoice switches, schedule editing, template editing, additional channels and a manual reminder replay control are outside this policy.
Source: choice: A shared policy provides automatic follow-up without requiring configuration beyond activation.

### C-9: An invoice must have been issued to qualify
Observable: A customer-payable issued invoice may qualify. A draft, a quote and an invoice awaiting issuance generate zero automatic reminder handoffs.
Source: implied: U-2 concerns a bill the recipient already owes.

### C-10: A reminder requires a positive collectible outstanding balance
Observable: A payable invoice with a remaining balance of 1 minor currency unit may qualify. An invoice with a zero or negative collectible balance generates zero handoffs, including when credits or payments fully cover it.
Source: implied: “Unpaid invoices” requires an amount that remains due.

### C-11: A partial payment leaves the collectible remainder eligible
Observable: An otherwise eligible invoice for 100.00 with a recorded payment of 40.00 can receive a reminder for 60.00 in the invoice currency.
Source: implied: U-3 covers invoices that remain unpaid in part.

### C-12: A closed payment obligation prevents a reminder
Observable: An invoice recorded as paid or fully settled, voided, canceled, written off, or otherwise explicitly marked no longer collectible through existing billing rules produces zero new handoffs, even if a displayed historical balance is positive. A deleted invoice also produces zero new handoffs. Archiving, a dispute, or a pending payment alone affects eligibility only if billing already treats it as closing or suspending collection.
Source: implied: U-3 requires the reminder scope to follow the current obligation to pay.

### C-13: An existing collection hold prevents handoff while effective
Observable: If existing billing rules suspend collection on an otherwise eligible invoice, the recipient receives zero new handoffs while the hold is effective. The feature uses any hold that actually exists in billing and establishes no new hold types.
Source: implied: U-3 requires a reminder to respect the invoice's current collectibility.

### C-14: A reminder requires a usable due date
Observable: An invoice whose due date is absent, invalid or cannot be interpreted as a billing calendar date has a visible due-date blocker and zero handoffs until billing supplies a usable date.
Source: implied: U-2 and U-5 need a date against which lateness can be determined.

### C-15: The invoice is due throughout its due date
Observable: An unpaid invoice due October 10 cannot receive a reminder at any time on or before October 10 in its billing calendar. Its first reminder may become due on October 11.
Source: choice: Use overdue reminders so recipients have the entire due date to pay.

### C-16: The reminder calendar follows billing's interpretation of the due date
Observable: A billing date is taken as the date shown on the invoice. Where its time zone is needed, the applicable zone is the one billing associates with that invoice, else the account billing zone, else UTC. The recipient's browser zone and the processing host's zone do not move reminder boundaries.
Source: choice: Use the date the payer was given and supply a deterministic fallback when billing has no zone.

### C-17: Reminder dates use local calendar days
Observable: Dates are counted from the due date in the applicable billing zone, even when an intervening day is shorter or longer than 24 hours. A reminder opportunity begins at the first valid instant of its scheduled local date, or at the first valid instant afterward if the date is skipped.
Source: choice: Keep scheduled dates consistent with the invoice calendar across clock changes.

### C-18: The first reminder opportunity begins 1 calendar day after the due date
Observable: For a due date of October 10, opportunity 1 begins at the start of October 11 in the applicable billing zone.
Source: choice: Follow up after the recipient has had the full due date to pay.

### C-19: The second reminder opportunity begins 7 calendar days after the due date
Observable: For a due date of October 10, opportunity 2 begins at the start of October 17 in the applicable billing zone.
Source: choice: Leave time for the recipient to respond before repeating the reminder.

### C-20: The third reminder opportunity begins 14 calendar days after the due date
Observable: For a due date of October 10, opportunity 3 begins at the start of October 24 in the applicable billing zone.
Source: choice: Provide a final automatic follow-up on the same overdue obligation.

### C-21: An invoice has at most 3 automatic reminder opportunities
Observable: After opportunities 1, 2 and 3, no fourth opportunity appears, even if the invoice is still payable, the account is re-enabled, or the invoice is edited or reopened. A separately issued invoice has its own opportunities.
Source: choice: Bound repeated customer contact over the lifetime of the invoice.

### C-22: Only the latest reached opportunity is considered for a new handoff
Observable: For an invoice due October 10 with no previous attempts, evaluation on October 18 can use opportunity 2 only. Evaluation on October 24 or any later day can use opportunity 3 only. Opportunity 3 has no age cutoff while otherwise eligible.
Source: choice: A late start, downtime or an old invoice can warrant a reminder without replaying missed messages.

### C-23: A later reached opportunity supersedes older unsent work
Observable: When opportunity 2 opens, a pending attempt or retry for opportunity 1 cannot begin. When opportunity 3 opens, the same rule applies to opportunities 1 and 2. A handoff already begun may still report an outcome.
Source: choice: Send the reminder for the current stage of delinquency after a delay.

### C-24: Separate reminder opportunities are spaced by at least 24 elapsed hours between handoffs
Observable: If one opportunity begins a handoff at 20:00 UTC on October 16, no different opportunity for that invoice begins a handoff before 20:00 UTC on October 17, even if the next calendar boundary arrives earlier.
Source: choice: Avoid near back-to-back messages after recovery or a late retry.

### C-25: Evaluation uses the currently effective due date and billing zone
Observable: If a date or zone correction recorded before handoff moves the invoice back within its due period, no handoff begins. If the change moves it farther overdue, evaluation applies the corrected dates and selects the latest applicable opportunity.
Source: implied: U-8 requires sending based on the corrected invoice.

### C-26: A schedule correction cannot move sending backward through previously attempted opportunities
Observable: After a handoff begins for opportunity 2, moving the due date so that only opportunity 1 has been reached cannot cause an opportunity 1 handoff. Returning to opportunity 2 retains its existing outcome and any remaining retry allowance. Opportunity 3 may still become eligible.
Source: choice: Preserve the contact history of the same invoice through schedule edits.

### C-27: The first healthy evaluation begins eligible handoffs within 1 elapsed hour
Observable: With processing capacity available, continuously enabled settings, stable eligible invoice data, an available delivery service and no retry or spacing delay, the first handoff begins within 1 elapsed hour of eligibility. This is a handoff timing target under those conditions. Recipient inbox arrival has no guaranteed deadline.
Source: choice: Give operators a concrete timing expectation while allowing work to run in the background.

### C-28: An account with no eligible invoice sends zero reminders
Observable: Enabling or evaluating an account with zero invoices, or with invoices that all fail eligibility, produces zero reminder messages.
Source: implied: U-4 requires a meaningful empty case.

### C-29: Pre-existing invoices enter evaluation without recreation
Observable: An invoice issued before deployment or activation qualifies under the same eligibility rules as an invoice issued afterward. An invoice fully settled before activation generates zero reminders.
Source: implied: U-4 covers the existing invoice population.

### C-30: The policy imposes no product cap on the number of invoices considered per account
Observable: A backlog larger than one processing cycle continues through subsequent cycles. An invoice can cease waiting because it was processed, lost eligibility, or was superseded by a later opportunity. Crossing an invoice count alone does not discard it. The supported throughput, maximum backlog completion time and deployment capacity are unconfirmed.
Source: choice: Follow up on the whole eligible population without inventing a processing capacity for an unknown host.

### C-31: Re-enabling evaluates invoices against the current policy state
Observable: After disabling before October 11 and re-enabling on October 18 for an invoice due October 10, evaluation can use opportunity 2. Previously accepted attempts, unresolved handoffs and exhausted allowances stay recorded.
Source: implied: U-6 requires safe resumption after a pause.

### C-32: A recorded disabled state blocks new handoffs
Observable: After disable succeeds, zero handoffs begin for that account until enable takes effect, including attempts previously queued for retry.
Source: implied: U-6 requires an effective stop control.

### C-33: Each handoff uses billing facts effective at the point the handoff begins
Observable: If a payment, closure, hold, account disable, invoice edit or recipient change becomes effective in billing before a handoff begins, that handoff uses the new facts or is suppressed. Processing that started earlier cannot authorize a handoff using an older snapshot.
Source: implied: U-8 requires current billing facts to govern a pending send.

### C-34: A handoff already begun may finish after eligibility changes
Observable: A handoff begun while eligible may later be accepted, delivered or reported failed after a payment, closure, edit, hold or disable. The status remains visible against that handoff. The changed facts govern every later handoff.
Source: implied: U-6 and U-8 meet at the external handoff boundary, after which delivery may already be committed.

### C-35: Reopening preserves the invoice's previous reminder outcomes
Observable: If billing reopens a payable obligation on the same invoice, including after a reversed payment or credit, the system considers only the currently applicable opportunity. A consumed opportunity stays consumed and a prior attempt still counts against its allowance.
Source: choice: Treat a reopened invoice as the same recipient obligation for reminder history.

### C-36: Billing events govern reminders once recorded in billing
Observable: A payment that occurred externally but has yet to be recorded can race with a reminder. Once billing records its effect, evaluation uses the resulting balance and collection status. A repeated or late event changes reminder eligibility only insofar as billing changes the effective invoice.
Source: implied: U-8 requires reminders to follow recorded billing facts, including where external events arrive late or twice.

### C-37: Reminders are sent by email
Observable: A handoff submits an email to the invoice recipient. It triggers no SMS, push notification, paper mailing or new recipient portal.
Source: choice: Email is a single direct channel for billing follow-up.

### C-38: A reminder has exactly one designated billing address
Observable: The email goes to the primary billing address designated for that invoice by the existing invoice delivery rules. If the invoice has no override, those rules may supply its customer's primary billing address. Unrelated contacts, internal users, and automatic CC or BCC recipients receive zero copies.
Source: choice: One designated recipient minimizes disclosures and duplicate notices.

### C-39: An ambiguous or unusable address blocks handoff
Observable: Zero, multiple equally designated, syntactically unusable, or billing-suppressed destination addresses result in a visible recipient blocker. Exactly 1 usable, unsuppressed primary address is required.
Source: implied: U-5 requires a known authorized destination before sending invoice information.

### C-40: A reminder identifies itself as a request to pay an outstanding invoice
Observable: The email communicates that payment is still due. The subject and body wording, layout and branding are flexible.
Source: implied: U-2 requires a reminder that the recipient can recognize and act on.

### C-41: A reminder identifies the issuing biller
Observable: The recipient can identify which business issued the invoice from the email.
Source: implied: U-2 requires the recipient to recognize the obligation.

### C-42: A reminder provides the customer-facing invoice identifier
Observable: The email shows the invoice identifier the recipient would use with the biller. Two invoices for the same customer can be distinguished by their identifiers.
Source: implied: U-2 requires the recipient to identify the unpaid invoice.

### C-43: A reminder provides the outstanding amount in the invoice currency
Observable: An invoice with USD 60.00 still payable shows an outstanding USD amount of 60.00, regardless of the original invoice total. Currency presentation can follow existing billing conventions.
Source: implied: U-2 and U-3 require the recipient to know the remaining obligation.

### C-44: A reminder provides the invoice due date
Observable: An invoice due October 10 shows that date as the due date, including when the reminder is sent on October 17.
Source: choice: Give the recipient the date for the obligation without prescribing date formatting.

### C-45: A reminder directs the recipient to the existing payment path
Observable: The email includes the invoice's existing customer-facing payment link or its actionable payment instructions. It introduces no new checkout, payment method or payment terms.
Source: implied: U-2 requires a way to act on the reminder.

### C-46: A handoff requires the customer-facing details needed to compose the reminder
Observable: Missing biller identity, invoice identifier, valid balance or currency, usable due date, designated recipient, or usable payment instructions is visible as a blocker. Evaluation resumes from current details if the blocker is corrected and an opportunity remains.
Source: implied: U-5 requires a complete, actionable email directed to the right recipient.

### C-47: Reminder content is limited to the intended invoice and its payment context
Observable: The email can contain sender identification, the reason for contact, invoice identifier, remaining amount with currency, due date and payment directions. Other invoices, internal notes, internal identifiers, personal data unrelated to the payment, full payment credentials and invoice attachments are excluded because they are unnecessary to follow up.
Source: choice: Include the information needed to pay the named invoice with minimal disclosure.

### C-48: Each invoice receives its own reminder
Observable: Two eligible invoices sharing a recipient address can produce two separately identifiable reminders, each governed by its own schedule and outcomes.
Source: choice: Keep recipient action and stopping conditions specific to the invoice.

### C-49: A reminder preserves the existing access rules for linked invoice and payment pages
Observable: A link from a reminder grants only the access the established customer-facing payment path grants for that invoice. It provides no access to another invoice, an operator page or a different account.
Source: implied: U-2 uses the existing payment path without changing who can see billing information.

### C-50: Repeated or concurrent processing cannot produce two accepted sends for the same opportunity
Observable: Re-evaluating the same account and invoice at the same opportunity, including with overlapping workers or after a restart, results in at most 1 delivery-service acceptance of that opportunity. Sharing an email address or invoice display number does not join separate invoices or accounts.
Source: implied: U-8 distinguishes one intended reminder from repeated execution of the same work.

### C-51: A delivery-service acceptance consumes the opportunity
Observable: Once the service accepts a reminder, repeating evaluation initiates zero further handoffs for that opportunity, including when the service gives no final delivery report or reports a later bounce.
Source: choice: Treat acceptance as the point after which resending can duplicate customer contact.

### C-52: An uncertain handoff prevents retry while its outcome is unresolved
Observable: If a request times out after the message may have reached the sender, or processing stops after starting a handoff, the opportunity shows an unresolved outcome. Repeated evaluation, service recovery and re-enabling produce zero additional handoffs for it while acceptance remains possible.
Source: implied: U-7 and U-9 require safe handling when external acceptance cannot be ruled out.

### C-53: Authoritative late evidence resolves an uncertain outcome
Observable: Evidence of acceptance for the same handoff records acceptance. Evidence establishing that no acceptance occurred records the corresponding temporary or permanent failure. In the absence of either, the state remains unresolved and is visible even after that opportunity stops being current.
Source: implied: U-7 requires a visible outcome grounded in the sender's actual response.

### C-54: A verified temporary pre-acceptance failure can retry
Observable: A sender response confirming temporary rejection before acceptance, such as throttling or temporary unavailability, permits another attempt for the same opportunity if it is still current, eligible and below the attempt cap. A reported outage before any handoff begins leaves the opportunity pending with zero attempts consumed.
Source: choice: Recover from transient errors only when another attempt can safely be made.

### C-55: One opportunity allows at most 3 handoff attempts
Observable: After the first attempt plus 2 retries for an opportunity, evaluation shows that the allowance is exhausted if none were accepted. A fourth handoff never begins, including following re-enable or restart. Each begun handoff counts, including an uncertain one.
Source: choice: Bound repeat traffic during a delivery failure.

### C-56: The first retry waits at least 1 elapsed hour after temporary failure is confirmed
Observable: A first failed handoff confirmed at 10:00 UTC is ineligible for its first retry until 11:00 UTC.
Source: choice: Give a transient delivery problem time to clear.

### C-57: The second retry waits at least 4 elapsed hours after the second temporary failure is confirmed
Observable: A second failed handoff confirmed at 11:00 UTC is ineligible for its final retry until 15:00 UTC.
Source: choice: Reduce repeated pressure on a dependency still failing after the first retry.

### C-58: A sender's mandatory retry delay takes precedence over an earlier retry time
Observable: If a sender confirms nonacceptance and requires a wait longer than the policy minimum, no retry starts before the sender permits it. The selected sender's required delay limits are unconfirmed.
Source: implied: U-7 must honor the delivery service's rate-limit and retry rules when those rules apply.

### C-59: A permanent pre-acceptance rejection ends attempts for that opportunity
Observable: A sender-confirmed permanent rejection, such as an invalid destination or prohibited message, shows a failed outcome. Correcting the data can allow a later opportunity if one remains. It does not reopen the permanently rejected opportunity.
Source: choice: Keep recovery bounded when the sender has rejected the message permanently.

### C-60: Every retry rechecks the conditions for a fresh handoff
Observable: A retry can begin only while the account is enabled, the invoice is issued and collectible with a positive balance and no hold, the date selects that opportunity, required message details are usable, the spacing rule allows it, prior acceptance has been ruled out, the attempt cap allows it, and the retry time has arrived. A corrected billing address or amount is used if a retry qualifies.
Source: implied: U-6 through U-8 require pending retries to follow the same current facts as initial attempts.

### C-61: An unresolved older opportunity leaves a later opportunity available
Observable: A timeout on opportunity 1 blocks another attempt for opportunity 1. Opportunity 2 may still begin when it is current and eligible, after the minimum spacing from the last handoff for opportunity 1.
Source: choice: Preserve the later scheduled opportunity without replaying the uncertain one.

### C-62: Delivery evidence is applied only to its corresponding handoff
Observable: A repeated report does not create another send or another counted attempt. An unmatched report cannot alter an invoice. A late report for an earlier send cannot erase or advance another opportunity. Reports of later delivery failure may update delivery status while preserving the fact of earlier acceptance.
Source: implied: U-7 and U-8 require outcomes to remain correct when external reports arrive twice or out of order.

### C-63: An accepted message is distinguishable from confirmed delivery
Observable: After sender acceptance, history shows the acceptance. If the sender supplies correlated delivery or bounce evidence, history can show delivered or bounced respectively. Without that evidence, final delivery is shown as unconfirmed.
Source: implied: U-7 requires operators to distinguish what was handed off from what reached the destination.

### C-64: A blocked invoice can return to evaluation after correction
Observable: Correcting invoice data or clearing a billing or delivery block before any handoff allows the currently applicable opportunity to proceed if otherwise eligible. Waiting on a blocker alone does not consume a handoff attempt.
Source: implied: U-5 requires a way to recover an invoice with incomplete or unusable information.

### C-65: An operator can see the current reminder position for an invoice
Observable: An authorized operator can distinguish disabled, ineligible or blocked, waiting for a scheduled opportunity, ready or delayed awaiting handoff, handoff in progress, waiting to retry, unresolved, accepted, failed, and no further opportunities. The view shows the relevant reason, applicable opportunity and next eligible attempt time where known. Historical outcomes remain separately identifiable from current eligibility.
Source: implied: U-5 through U-7 require enough visibility to correct a problem or understand what will happen next.

### C-66: An operator can see the reminder outcomes recorded for an invoice
Observable: Each begun handoff can be identified by its opportunity number, attempt number, destination address, handoff time, current outcome, last outcome update time and failure reason when applicable. Outcomes are in progress, unresolved, temporarily rejected before acceptance, permanently rejected before acceptance, accepted with delivery unconfirmed, delivered, or bounced. An email body copy, full payment credentials and provider secrets are omitted because they are unnecessary to diagnose delivery.
Source: choice: Keep the invoice's delivery history sufficient for diagnosis and duplicate prevention.

### C-67: Invoice access controls reminder visibility
Observable: A person authorized to view the account's billing details for an invoice can inspect its reminder information. A person without that invoice access sees neither its reminder details nor confirmation that a guessed invoice identifier exists, including via direct requests.
Source: implied: U-5 and U-7 expose invoice and contact information only to authorized billing operators.

### C-68: A service operator can identify a processing interruption
Observable: The service operator can see the time of the last successful evaluation, whether there is due work waiting, and whether processing or the sender is unavailable. When a continuously ready invoice remains waiting more than 1 elapsed hour, the operator can distinguish a backlog or interruption from a future schedule, retry delay or eligibility block.
Source: implied: U-9 requires a way to detect a stalled automatic process.

### C-69: Restoring service resumes outstanding evaluation
Observable: After a scheduler or sender outage clears, enabled accounts resume evaluation without requiring an operator to enable each account again. Queued work follows current eligibility and the opportunity-selection rules. Completed, failed and unresolved outcomes retain their effect.
Source: implied: U-9 requires safe recovery from a processing interruption.

### C-70: A failure for one invoice does not exclude other eligible invoices from evaluation
Observable: With an available sender, a missing address, invalid invoice data, permanent rejection or unresolved response for one invoice does not prevent another eligible invoice from being processed, including within the same account.
Source: implied: U-4 and U-7 cover accounts containing both sendable and blocked invoices.

### C-71: Reminder bookkeeping and diagnostics stay associated with the originating account
Observable: An operator acting in one account cannot see another account's settings, waiting invoices, destinations or outcomes. Service-wide diagnostics require service-operator access and ordinary recipient access reveals no operator history.
Source: implied: U-1 and U-7 involve account-specific controls and private billing information.

### C-72: Ambiguous setting updates cannot create conflicting effective values
Observable: If enable and disable overlap, the setting read afterward reflects the last successfully applied change. Any handoff that begins after that change uses the effective value at its own boundary. A failed update does not take precedence over an applied one.
Source: implied: U-1 and U-6 may be carried out by different authorized operators at the same time.

### C-73: A reminder does not create or issue an invoice
Observable: An evaluation, retry, handoff or delivery callback leaves the set of existing invoices and their issue states as they were unless a separate billing action changes them.
Source: implied: U-2 adds follow-up to the existing invoice lifecycle.

### C-74: A reminder does not post a payment or change the amount owed
Observable: Evaluation, sending and delivery outcomes have no effect on the ledger or collectible amount. Existing payments, credits, refunds and write-offs retain their billing effects.
Source: implied: U-2 and U-3 ask for reminders about an obligation.

### C-75: A reminder does not change the terms of an invoice
Observable: Following evaluation or delivery, the invoice retains its existing due date, payment methods and terms. A reminder cannot add a fee or interest.
Source: implied: U-2 asks to communicate the existing obligation.

### C-76: Original invoice delivery remains independent of reminder delivery
Observable: Existing invoice sends and resends keep their usual permissions, content and trigger behavior. A reminder failure does not prevent an original invoice from being sent. Original issue or resend activity does not count as an automatic reminder handoff.
Source: implied: U-2 adds an automatic follow-up to billing's previous delivery behavior.

### C-77: Existing invoice edits retain their billing behavior
Observable: Authorized changes to contact, due date, amount, and status continue to follow existing billing permissions and validation. The reminder feature reads the effective facts without requiring extra reminder-specific fields to save an invoice.
Source: implied: U-5 and U-8 use the ordinary invoice correction flow.

### C-78: Existing recipient payment behavior stays available during a reminder failure
Observable: A recipient can use the original invoice payment surface when automatic reminders are disabled or the reminder scheduler or sender is unavailable, subject to the existing payment surface's own availability and rules.
Source: implied: U-9 concerns recovery of reminder processing while billing can continue.

### C-79: Existing invoice visibility and retention rules still govern the invoice
Observable: Enabling, disabling or removing the feature does not extend access to an invoice or cause earlier deletion of billing data. The billing system's existing invoice access and retention behavior remains in effect.
Source: implied: U-10 requires the existing billing records to survive reminder rollout and rollback according to their normal rules.

### C-80: Reminder history remains available for the invoice's allowed retention period
Observable: An operator with invoice access can inspect its reminder history after pause or restart. History follows the applicable invoice retention or erasure rule. If personal details must be erased while the invoice can still be evaluated, any legally retainable reminder outcome needed for duplicate prevention survives without those details. No separate numeric retention duration is established because the billing retention policy is unconfirmed.
Source: choice: Preserve the history needed to resume safely while honoring existing billing data retention.

### C-81: Rolling back stops new automatic handoffs
Observable: After the operator stops the rollout, zero new automatic handoffs begin, including from earlier pending work. Mail already handed off may still complete.
Source: implied: U-10 requires effective withdrawal of the automatic sender.

### C-82: Returning to a release with reminders preserves previously recorded sending outcomes
Observable: After rollback and later restoration, accepted opportunities stay consumed, unresolved ones stay protected against retry, and existing attempt counts still apply. An account resumes only when its effective setting enables it.
Source: implied: U-10 requires rollback and restoration to avoid duplicate follow-ups.

### C-83: A blocked sender configuration prevents live handoffs
Observable: Before a delivery service is usable with the authorization, sender identity and sending permissions it requires, no live handoff begins. The service operator can identify this as a setup blocker. The service-specific authorization lifetime and sender verification requirements are unconfirmed.
Source: implied: U-9 depends on the delivery service permitting a production send.

### C-84: Background processing must be active before automatic handoffs can occur
Observable: With the deployment's background execution disabled or unavailable, no new handoffs occur even if accounts are enabled. Once background execution is available, eligible work resumes with its existing history. The host's allowed trigger granularity, invocation duration, concurrency and retry limits are unconfirmed.
Source: implied: U-1 and U-9 require an execution host that can initiate work independently of a user session. No runtime or scheduler is identified in the workspace.

### C-85: A runtime interruption leaves unfinished work recoverable within the sending rules
Observable: When the execution host interrupts work before handoff begins, eligible work can be evaluated again. If interruption occurs after handoff begins and before an outcome is known, the outcome is unresolved. The host timeout and interruption thresholds are unconfirmed.
Source: implied: U-9 must respect the execution host's ability to interrupt work without a synchronous outcome.

### C-86: The sender's enforced volume limits throttle delivery
Observable: If available delivery capacity is exhausted, due work stays visible for reevaluation and the system obeys the sender's restrictions on additional handoffs. Sender rate, burst, daily volume and destination limits are unconfirmed.
Source: implied: U-4 and U-7 must honor the delivery service's enforced rate and volume limits. No delivery service is identified in the workspace.

### C-87: The sender's enforced message limits can block a reminder
Observable: If a required reminder cannot be submitted within the selected sender's permitted message size, address length or format, the operator sees a failure or blocker and no incomplete reminder is sent. Exact service-specific limits are unconfirmed.
Source: implied: U-5 and U-7 must honor the delivery service's message acceptance rules.

### C-88: Nonproduction evaluation sends zero reminders to live billing contacts
Observable: Running evaluation in a development or test environment using a production invoice or contact does not submit an email to that contact. Live handoffs require the production delivery context and an enabled billing account.
Source: choice: Let operators exercise the automation without contacting real customers from a nonproduction environment.
