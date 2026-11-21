## Use cases

### U-1: A billing administrator enables reminders to follow up automatically
Flow: The administrator opens the account’s reminder controls. An account that has never had the feature starts disabled. The administrator enables reminders and sees the saved state. A user without billing administration permission is refused. A save that is refused or cannot commit leaves the prior setting in effect. If the response is lost, the administrator checks the committed value.
Source: request

### U-2: An invoice recipient receives a reminder to identify the amount still due
Flow: The account has reminders enabled and global handoffs are running. An issued open invoice with a positive balance reaches an eligible opportunity 1, 7 or 14 days after its due date. The service hands off one email for the designated billing recipient. On successful delivery the recipient sees the issuer, invoice reference, outstanding amount with currency, due date and request to pay. If the address is unusable the email is skipped, and if delivery fails after acceptance it may never reach the recipient.
Source: request

### U-3: A billing administrator handles ineligible or incomplete invoices to avoid inappropriate mail
Flow: The administrator reviews invoices that are unissued, settled, on collection hold, missing a due date or missing a usable billing address. Those invoices produce no reminder while ineligible. An account with no eligible invoice produces no recipient email.
Source: implied: “for unpaid invoices” requires identifying invoices eligible for follow-up

### U-4: A billing administrator opts out of future sends to pause automatic follow-up
Flow: The administrator disables account reminders and sees the saved state. After the pause, the administrator can enable reminders again. Previously handed-off mail may still arrive.
Source: implied: operating automatic outbound reminders requires a way to stop them

### U-5: A billing administrator reviews reminder outcomes to decide whether intervention is needed
Flow: The administrator looks up an invoice and sees its reminder history or that it has none. The administrator distinguishes an accepted email from a failed or uncertain handoff.
Source: implied: unattended reminders can fail without the administrator being present

### U-6: An operator recovers from an outage to resume automatic follow-up safely
Flow: Scheduling or email delivery fails. The operator sees which capability is unavailable, restores it and checks that eligible work resumes. Completed reminders stay completed.
Source: implied: automatic sending depends on a clock, invoice data and outbound delivery

### U-7: A billing administrator enables reminders for an account with existing invoices to cover eligible older records
Flow: After upgrade, the administrator enables reminders for an existing account. A complete existing invoice can qualify during an open opportunity under the same rules as a new invoice. Windows that already closed produce no catch-up mail. An incomplete older invoice remains ineligible until corrected.
Source: implied: the request does not restrict reminders to newly created invoices

### U-8: An operator rolls back the release to restore the prior application version
Flow: The operator pauses reminder handoffs before rollback and confirms the paused state. If the operator cannot confirm the paused state, the normal rollback remains pending. After confirming the stop, the operator restores the prior version. Existing invoice operations remain available. After re-upgrade, the operator checks readiness before resuming and authorized staff can inspect prior handoff history.
Source: implied: an automatic outbound feature needs a safe rollback path

### U-9: A billing administrator relies on reminders for a large account to follow up across its invoice portfolio
Flow: A large set of invoices can qualify for reminders at the same time. The service works through eligible invoices while capacity is available and their windows remain open. If capacity runs out, the administrator can look up an affected invoice and see that its window expired.
Source: implied: “invoices” includes portfolios with simultaneous work

### U-10: A billing clerk records a payment to keep the next reminder accurate
Flow: The clerk records a partial payment using the existing billing workflow. If the payment commits before handoff, the reminder uses the lower balance. A payment that clears the balance prevents a subsequent handoff. If the payment fails to record, the reminder continues to use the balance the billing system has committed.
Source: implied: “unpaid” is determined by the current outstanding balance

### U-11: A billing administrator corrects invoice details to keep future reminders accurate
Flow: The administrator updates the billing address or due date under existing invoice rules. Before handoff starts, the latest committed address and schedule take effect. An invalid address leaves the invoice ineligible. Editing or reopening an invoice does not reset a completed opportunity.
Source: implied: U-2 and U-3 rely on invoice facts that can change

### U-12: A billing administrator investigates a failed handoff to understand whether it will be tried again
Flow: The administrator sees a definite temporary rejection as eligible for at most two retries within its window. A permanent rejection closes the opportunity. When acceptance is unknown, no retry begins. A late authoritative result can update the displayed outcome.
Source: implied: U-5 and U-6 must account for unresolved and rejected delivery

### U-13: A deployment operator starts reminder processing to release automatic handoffs
Flow: The operator checks scheduling and delivery readiness on deployment and resumes from the initial paused state. If the delivery service can send only to sandbox destinations, production handoffs remain unavailable. Production customer addresses receive no reminders from nonproduction environments.
Source: implied: U-6 and U-8 require an operator to be able to start or resume processing safely

## Clauses

### C-1: An issued unpaid invoice is followed up automatically when reminders are enabled and the invoice is eligible for a scheduled reminder.
Observable: With dependencies ready and delivery capacity available, a reminder for an eligible invoice is submitted automatically during an open opportunity. An end-to-end delivery to a working test mailbox shows the recipient receives the reminder without a person issuing an invoice-level send action.
Source: request

### C-2: The billing administrator can change the account’s reminder enablement.
Observable: The administrator can save either enabled or disabled and read back the saved state.
Source: implied: U-1 and U-4

### C-3: Account reminders start disabled.
Observable: An account with no saved reminder setting shows disabled until an administrator enables it.
Source: choice: explicit enablement gives the account control over initiating outbound mail

### C-4: A caller without billing administration permission cannot change reminder enablement.
Observable: An unauthorized write is refused and an authorized read still shows the prior state.
Source: implied: U-1

### C-5: A disabled account produces no new reminder send authorizations.
Observable: A due invoice in a disabled account produces no new authorized handoff.
Source: implied: U-4

### C-6: The reminder channel is email.
Observable: The designated billing recipient receives an email.
Source: choice: one familiar asynchronous billing channel is sufficient

### C-7: An account with no eligible invoices produces no reminder emails.
Observable: Evaluating an empty account or an account containing only ineligible invoices starts zero handoffs.
Source: implied: U-3

### C-8: The billing administrator can inspect reminder outcomes for an invoice.
Observable: An authorized administrator can see the outcomes for a known invoice and can identify an invoice with no outcome history.
Source: implied: U-5

### C-9: The operator can identify which reminder dependency is unavailable.
Observable: Operator health reports availability of scheduling, the clock used for reminder windows, authoritative invoice reads, account settings, global control, opportunity history and outbound delivery. For each, unavailable or unknown is distinguishable from available. An unavailable health source cannot make the dependency appear healthy.
Source: implied: U-6

### C-10: Restoring reminder dependencies allows future eligible work to proceed automatically.
Observable: After an outage clears while global processing remains running, eligible work resumes during open windows without an individual resend action.
Source: implied: U-6

### C-11: Previously created invoices use the same eligibility rules as newly created invoices.
Observable: An older eligible invoice in an enabled account can receive a reminder without being recreated.
Source: implied: U-7

### C-12: The operator can stop automatic reminder handoffs before rollback.
Observable: The operator stops handoffs and can verify that no further handoff is authorized.
Source: implied: U-8

### C-13: Rolling back preserves the invoice operations that were available before the feature.
Observable: After rollback, a previously supported invoice operation remains available to the same authorized caller.
Source: implied: U-8

### C-14: Simultaneous eligibility does not impose a reminder-specific cap on the number of invoices in an account.
Observable: If an account has 10,001 concurrently eligible invoices, invoice 10,001 can be processed while its window is open. Eligibility does not end at the first group or at a fixed per-account invoice count.
Source: choice: a portfolio can span multiple processing groups without losing eligibility

### C-15: Billing administration permission applies within the invoice’s own account.
Observable: An administrator of account A can operate reminders in A. The same identity is refused in account B unless it also has billing administration permission there.
Source: implied: U-1 and U-5 require account-scoped authority

### C-16: Account administrators can control only the enabled or disabled setting for their account’s reminders.
Observable: The account settings offer enable and disable. Manual send and resend controls are outside this feature because the requested follow-up is automatic. Cadence, send time, time zone, channel, recipient selection and retry policy follow the feature’s stated rules.
Source: choice: the account needs a switch and a predictable policy without additional configuration

### C-17: An invoice’s account and stable invoice identity determine which invoice is evaluated.
Observable: Two accounts can each have an invoice labeled INV-42. Enabling reminders in one account leaves the other account’s enablement and invoice delivery unaffected.
Source: implied: U-2 and U-7 require matching an invoice to its owner independently of its display label

### C-18: Only invoices whose canonical lifecycle state is issued and open can qualify for reminders.
Observable: An issued open invoice can qualify whether unpaid in full or partially paid. Draft, scheduled for issuance, paid, voided, canceled, written off, deleted and unknown lifecycle states produce zero handoffs. A past-due label on an otherwise issued open invoice is compatible with eligibility.
Source: implied: U-2 and U-3 require a collectible invoice already issued to the recipient

### C-19: An invoice qualifies only while its authoritative outstanding balance is strictly greater than zero.
Observable: At the same lifecycle state, balances of 0 and negative amounts yield no handoff. A positive balance after recorded payments, credits and adjustments can qualify. An unavailable or indeterminate balance cannot qualify.
Source: implied: “unpaid invoices” requires money to remain due

### C-20: A collection hold makes an otherwise eligible invoice ineligible.
Observable: An invoice marked disputed or marked as having collection activity paused yields no reminder. If neither mark is set, this restriction does not apply.
Source: choice: an automated follow-up should respect an explicit hold on collecting the invoice

### C-21: A reminder requires an authoritative calendar due date.
Observable: A missing, impossible or unreadable due date produces zero handoffs. An invoice corrected to a valid due date can qualify under that date’s schedule.
Source: choice: a due-date schedule needs a dependable stated date

### C-22: An invoice with a valid due date has three scheduled reminder opportunities.
Observable: For a due date of June 1, the scheduled opportunities are June 2, June 8 and June 15, corresponding to offsets of 1, 7 and 14 calendar days after the due date. No opportunity starts on the due date or at another offset.
Source: choice: three spaced follow-ups cover newly and persistently overdue invoices with a finite cadence

### C-23: Each opportunity opens at 09:00 UTC on its scheduled calendar date.
Observable: The June 2 opportunity opens at 09:00 UTC on June 2 for recipients in any time zone, including across daylight-saving changes.
Source: choice: one stable clock works without introducing account time-zone configuration

### C-24: Each opportunity is open for 24 hours from its scheduled time, with the opening instant included and the closing instant excluded.
Observable: A June 2 opportunity can authorize a handoff from June 2 at 09:00 UTC through any instant before June 3 at 09:00 UTC. It cannot authorize one at June 3 at 09:00 UTC or later.
Source: choice: a bounded catch-up period absorbs short outages while avoiding a burst of stale mail

### C-25: The invoice’s current designated billing address is the reminder’s sole destination.
Observable: With one designated address, the reminder goes only to that mailbox. Multiple competing designations, a missing address or an invalid address cause zero handoffs. Account owners, alternative contacts, CC and BCC receive no copies through this feature.
Source: choice: using the existing billing destination minimizes disclosure and requires no new recipient settings

### C-26: The reminder identifies the invoice issuer.
Observable: The recipient can tell which billing account issued the invoice from the issuer’s billing display name.
Source: implied: U-2 requires knowing who is requesting payment

### C-27: The reminder identifies the invoice.
Observable: The recipient can match the email’s invoice reference to the reference shown on their invoice.
Source: implied: U-2 requires matching the follow-up to the bill

### C-28: The reminder states the invoice’s current outstanding amount inclusive of its currency.
Observable: For a USD 100 invoice with USD 40 recorded as paid, the email identifies USD 60 as outstanding. A later opportunity uses the balance current at its own authorization.
Source: implied: U-2 requires the amount still due to be intelligible

### C-29: The reminder states the invoice’s current due date.
Observable: For an invoice with a June 1 due date, the recipient can identify June 1 as the due date in the email.
Source: choice: the stated due date explains why the recipient is receiving a follow-up

### C-30: The reminder asks the recipient to pay the outstanding balance.
Observable: The recipient can identify the requested action as payment of the named invoice’s balance.
Source: implied: U-2 is a follow-up for unpaid invoices

### C-31: The reminder requires only the issuer’s billing display name, invoice reference, outstanding amount with currency, due date and request to pay as billing content.
Observable: A reminder containing those five elements is complete without an attachment, a line-item list, payment instructions or a payment link. Those four additions are outside this feature’s contract because the requester supplied no invoice document or payment interface.
Source: choice: identify the debt with the minimum information needed for follow-up

### C-32: Missing authoritative reminder content prevents handoff.
Observable: An invoice with a missing issuer display name, invoice reference, currency, balance or due date causes no handoff. A correction can make a still-open opportunity eligible.
Source: choice: skip an incomplete invoice instead of sending a payment request whose required facts cannot be verified

### C-33: A rejected reminder-setting write leaves the saved state unchanged.
Observable: A write with an absent value or a value other than enabled or disabled is refused. A subsequent authorized read returns the prior setting.
Source: choice: rejected settings cannot silently start or stop outbound mail

### C-34: An administrator can determine why an invoice is currently ineligible.
Observable: For an invoice in the administrator’s account, the available reasons are account disabled or absent, globally paused, lifecycle state ineligible, balance unavailable or nonpositive, collection hold, due date missing or invalid, billing address missing or unusable, existing billing email block, required billing content missing, no open opportunity, opportunity already closed by outcome or superseded, attempt still in progress, retry waiting until its next permitted instant, and required dependency unavailable. Multiple applicable reasons can be shown together. A deleted or unknown invoice follows the existing invoice lookup boundary.
Source: choice: these reasons distinguish conditions staff can correct from conditions governed by time or prior outcomes

### C-35: Saving the setting repeatedly to its existing value has no extra reminder effect.
Observable: Saving enabled twice without any intervening change leaves the account enabled without creating extra opportunities. Saving disabled twice leaves it disabled.
Source: implied: U-1 and U-4 describe a saved state

### C-36: Account enablement does not release opportunities whose windows already closed.
Observable: Enabling an account on June 9 at 09:00 UTC for an invoice due June 1 does not release the closed June 2 or June 8 opportunities. Its June 15 opportunity is available if the invoice is eligible then.
Source: choice: enabling reminders applies to current and future chances rather than accumulating a mailing backlog

### C-37: The operator can pause or resume automatic handoffs across accounts.
Observable: An authorized deployment operator can set the global state to paused or running and can read back that state. Billing administrators have no global pause control unless separately granted deployment operator authority.
Source: choice: a deployment-wide control is needed for outages and rollback across multiple accounts

### C-38: The global reminder state starts paused on first deployment.
Observable: The first deployment reports paused until a deployment operator sets it to running, including if a billing administrator has already enabled an account.
Source: choice: the operator can verify dependencies before releasing real email

### C-39: A reminder requires the global state to be running at authorization.
Observable: An enabled account with an otherwise eligible invoice starts no external handoff while the global state is paused.
Source: implied: U-8 requires a deployment-wide stop that applies to enabled accounts

### C-40: The operator can observe whether the automatic evaluator is making progress.
Observable: The operator can see the global running or paused state and the time of the last completed evaluation tick, or that none has completed.
Source: choice: a liveness signal makes a failed timer distinguishable from an empty portfolio

### C-41: Reminder eligibility is evaluated against committed invoice and control values at the start of the external handoff.
Observable: If payment in full, a credit to zero, a state change out of issued and open, a collection hold, deletion, account disablement or a global pause commits first, a previously selected invoice produces no handoff. Selection alone gives no authority to send.
Source: implied: U-3 and U-4 must apply to invoice and settings changes during evaluation

### C-42: A committed change to reminder inputs supersedes any earlier preparation for a handoff that has yet to start.
Observable: A due-date change before handoff uses the new window. An address, invoice reference, issuer name, currency or partial balance change before handoff uses the latest valid value for the outgoing email or prevents handoff if it no longer qualifies.
Source: implied: U-2 and U-3 require a reminder for the current invoice

### C-43: Each retry is subject to the same current eligibility rules as an initial handoff.
Observable: After a temporary delivery rejection, recording payment in full or disabling the account before the retry prevents that retry.
Source: implied: U-3 and U-4 apply even when an earlier attempt failed

### C-44: A handoff already begun is outside the feature’s ability to recall.
Observable: If payment or pause commits after handoff begins, the recipient may still receive the email based on the invoice values at the handoff boundary.
Source: implied: U-4 requires distinguishing future action from mail already released to an external system

### C-45: A correction or reopening can restore eligibility only for an open opportunity that remains available.
Observable: Fixing an address, ending a hold, recording a payment reversal that restores issued-open status and a positive balance, or resuming reminders can make an open opportunity eligible again. Such a change cannot extend a closed calendar window or clear an outcome that closed the opportunity.
Source: choice: corrections should take effect without retroactive sends or repeats

### C-46: Opportunity identity is stable across invoice edits for the life of the invoice.
Observable: The 1-, 7- and 14-day opportunities retain their respective identities when an invoice’s due date, reference, address, balance or lifecycle state changes. A due-date edit recalculates the window of each opportunity without creating a new set of identities.
Source: choice: an edit must not reset the follow-up sequence

### C-47: An earlier opportunity cannot start a handoff once a later opportunity has started its handoff.
Observable: After a 7-day handoff begins, editing the due date so the 1-day window would open produces no 1-day handoff. The 14-day opportunity can still qualify.
Source: choice: revised dates should not move a recipient backward through an active follow-up sequence

### C-48: Only one unresolved handoff attempt per invoice can begin at a time.
Observable: Two evaluations finding the same invoice eligible concurrently result in one outbound attempt while that attempt’s result is unresolved. That restriction still holds if a date edit moves the invoice into another opportunity.
Source: implied: U-2 requires repeat evaluation to avoid concurrent duplicate handoffs

### C-49: An accepted handoff permanently closes its opportunity.
Observable: After acceptance, restarts, duplicate evaluations, repeated enablement, changes to recipient or due date, payment reversals and rollback followed by re-upgrade yield no further attempt of that same opportunity.
Source: implied: U-2 calls for scheduled follow-up, with a single send per opportunity

### C-50: A definitely temporary rejection can be retried at most twice per opportunity.
Observable: Following a definite temporary first rejection, at most two more attempts can begin for that identity. With three temporary rejections the opportunity is exhausted. Edits, restarts and pause followed by resume do not reset the count.
Source: choice: two retries allow recovery from transient failures while bounding repeated work

### C-51: A retry after a definite temporary rejection cannot begin until at least 15 minutes after that rejection.
Observable: A definite temporary rejection recorded at 09:05 UTC allows a retry no earlier than 09:20 UTC, subject to the open window and any later binding delivery-service retry time.
Source: choice: a short minimum interval allows temporary failures to clear

### C-52: A definitely permanent rejection closes its opportunity.
Observable: After a definite permanent rejection, correcting the address or restoring the delivery service cannot initiate another attempt for that opportunity. A later opportunity uses current data and can still qualify.
Source: choice: terminal failures need bounded behavior without a manual resend path

### C-53: A handoff with unknown acceptance closes its opportunity to new attempts.
Observable: If the connection ends after mail could have been accepted but no authoritative result is received, later evaluations initiate no further attempt for that opportunity. The administrator can see that acceptance is unknown.
Source: choice: after ambiguity, avoiding duplicate mail takes priority over retrying the same opportunity

### C-54: An unresolved attempt becomes acceptance unknown five minutes after it begins.
Observable: If a handoff starts at 09:00 UTC, a definitive result observed by 09:05 UTC controls its outcome. If none is observed by that instant, the attempt becomes acceptance unknown. A lost or interrupted sender is subject to the same deadline.
Source: choice: bound the time an unresolved attempt can block later work for the same invoice

### C-55: Definitive late evidence refines an unknown outcome without reopening its opportunity.
Observable: A definitive confirmation observed for the same attempt replaces acceptance unknown with accepted, definitely temporarily rejected or definitely permanently rejected. A late temporary rejection cannot authorize a retry of an opportunity previously closed as unknown.
Source: choice: outcome reporting should reflect authoritative evidence without reopening a duplicate-send risk

### C-56: An outcome notification affects only the attempt it identifies.
Observable: A late result from the first attempt cannot update the displayed result of a subsequent attempt. A duplicate result yields no additional history event. A result that cannot be matched to an attempt changes no invoice’s reminder history.
Source: implied: U-5 must report the outcome of the correct outbound action

### C-57: A delivery failure after acceptance does not reopen the opportunity.
Observable: A bounce observed after an accepted handoff is visible as a subsequent delivery outcome for that handoff. No fresh attempt is made for the same opportunity because of the bounce.
Source: choice: a post-acceptance failure is separate from rejection of the original handoff

### C-58: A dependency failure prevents any handoff whose eligibility or send readiness cannot be established.
Observable: While the clock, invoice data, account settings, global control, opportunity history or outbound service readiness is unavailable, an affected invoice cannot produce a new handoff based on cached guesses. If the outbound service fails after handoff begins, that attempt follows the ordinary outcome rules.
Source: implied: U-6 cannot safely continue without the facts required to determine eligibility

### C-59: A pause or dependency outage does not extend the schedule.
Observable: After an outage spanning June 2 at 09:00 UTC through June 3 at 09:00 UTC or later, the June 2 window for a June 1 invoice yields no catch-up attempt. Eligible work in an open window can resume.
Source: choice: recovery uses the same closing boundary as normal operation

### C-60: Reminder history exposes the evidence needed to locate an outbound attempt.
Observable: For an invoice the administrator can look up, each attempt shows the 1-, 7- or 14-day opportunity identity, window opening time applicable when the attempt began, attempt number 1 through 3, handoff start time, current handoff outcome, and the time of that outcome if known. A recorded service acceptance reference is included when the service issues one. An observed bounce is accompanied by its observation time.
Source: choice: those fields support reconciliation without retaining the raw message as part of the history view

### C-61: Reminder history exposes a finite set of handoff outcomes.
Observable: An attempt shows one of in progress, accepted, definitely temporarily rejected, definitely permanently rejected or acceptance unknown. A recorded post-acceptance bounce appears as an additional fact. Acceptance indicates service acceptance for delivery.
Source: choice: staff need to distinguish acceptance, rejection, uncertainty and bounce without assuming inbox receipt

### C-62: The administrator can see the disposition of every opportunity for an invoice with a valid due date.
Observable: For each of the 1-, 7- and 14-day identities, the administrator can distinguish scheduled, open, waiting to retry, handoff in progress, closed by acceptance, closed by permanent rejection, closed by exhausted retries, closed by uncertainty, superseded by a later handoff and window expired without acceptance. A bounce is visible through the accepted attempt. An expired window without an attempt is still visible after a backlog or outage. Calendar dispositions reflect the current due date.
Source: choice: showing dispositions makes skipped and missed opportunities discoverable without searching delivery logs

### C-63: A reminder address must fit the supported Internet email mailbox limits.
Observable: An address is unusable if its SMTP local part exceeds 64 octets, its transport domain exceeds 255 octets or its full SMTP forward path exceeds 256 octets including delimiters. For an ordinary bracketed path this leaves at most 254 octets for the mailbox including its @ separator.
Source: implied: U-2 uses Internet email, whose interoperable path limits are stated in [SMTP RFC 5321 §4.5.3.1.1–3](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.1.1)

### C-64: A reminder preserves the case of the destination mailbox’s local part.
Observable: For a designated address of Billing@example.com, the transport presents Billing as the local part. Domain letter case does not change the destination.
Source: implied: U-2 must use the designated mailbox, and [SMTP RFC 5321 §2.4](https://www.rfc-editor.org/rfc/rfc5321.html#section-2.4) requires preserving local-part case

### C-65: Reminder content remains readable within Internet email line limits.
Observable: A long valid invoice reference or issuer name can wrap or be encoded in the email, retaining its content. A baseline SMTP transport line stays within 1,000 octets including its line ending and excluding an SMTP transparency dot. An Internet Message Format line stays within 998 characters excluding its line ending.
Source: implied: U-2 requires readable content within [SMTP RFC 5321 §4.5.3.1.6](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.1.6) and [RFC 5322 §2.1.1](https://www.rfc-editor.org/rfc/rfc5322.html#section-2.1.1)

### C-66: A delivery service’s message-size refusal is visible as a permanent rejection when the service definitively refuses acceptance on that basis.
Observable: If the relay permanently refuses a reminder above its fixed supported size, the attempt shows definitely permanently rejected. The selected relay’s exact maximum size in octets is unconfirmed.
Source: implied: U-5 must reflect the delivery service’s fixed-size restriction, described for SMTP in [RFC 1870 §6.1](https://www.rfc-editor.org/rfc/rfc1870.html#section-6.1)

### C-67: Acceptance requires authoritative confirmation that the outbound delivery service took responsibility for the full reminder.
Observable: An SMTP positive completion reply of class 2xx after the entire message is transmitted is accepted. A successful connection or acceptance of the address by itself is still in progress until a definitive result or the uncertainty deadline. If the service exposes a different interface, its documented confirmation of message acceptance is equivalent.
Source: implied: U-5 follows the boundary at which SMTP transfers responsibility under [RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5)

### C-68: A definitive temporary refusal by the delivery service is recorded as a temporary rejection.
Observable: An SMTP class 4xx refusal that establishes nonacceptance of this submission is shown as definitely temporarily rejected. An equivalent definitive temporary response from the selected service has the same outcome.
Source: implied: U-5 follows the temporary failure semantics of [SMTP RFC 5321 §4.2.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.1)

### C-69: A definitive permanent refusal by the delivery service is recorded as a permanent rejection.
Observable: An SMTP class 5xx permanent refusal of this submission or a documented equivalent is shown as definitely permanently rejected. A pre-submission service outage without a definitive permanent refusal is not classified as a permanent rejection.
Source: implied: U-5 follows the permanent failure semantics of [SMTP RFC 5321 §4.2.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.1)

### C-70: Reminder handoffs respect the outbound service’s enforced sending capacity.
Observable: If the service enforces a per-time-period send quota, send rate or simultaneous-submission limit, eligible work can wait for available capacity until its window closes. The quotas, applicable time periods, rates and concurrency caps are unconfirmed because the service and plan are unidentified.
Source: implied: U-6 and U-9 are constrained by the deployed delivery service’s capacity rules

### C-71: A binding service retry restriction can delay another attempt beyond the product’s minimum interval.
Observable: After a definite temporary rejection with a service-provided retry time of 10:00 UTC, a retry cannot begin before 10:00 UTC even if the 15-minute minimum ends sooner. If the permitted retry time falls on or beyond the window close, that window yields no retry. The chosen service’s retry restrictions are unconfirmed.
Source: implied: U-6 must respect any binding throttling rule of the chosen delivery service

### C-72: A delivery service that cannot submit to production recipients is unavailable for production reminders.
Observable: With missing service authentication, a sender identity not authorized by the service, or sandbox-only permission, the operator sees production delivery unavailable and customer handoffs cannot begin. The provider’s concrete production authorization requirements are unconfirmed.
Source: implied: U-1 and U-6 depend on the outbound service allowing authenticated production submissions

### C-73: Work interrupted by the application host is subject to normal reminder recovery rules.
Observable: With a scheduler or execution timeout, a reminder with no begun handoff can still qualify in its open window. An interrupted handoff with unconfirmed acceptance follows the unknown-outcome rule. The application host and scheduler are unspecified. Their runtime timeout, minimum trigger interval, concurrent execution cap, trigger delivery guarantees and production scheduling prerequisites are unconfirmed.
Source: implied: U-6 must remain correct when the eventual execution platform interrupts or repeats work

### C-74: An invoice can still be created through any pre-existing creation workflow.
Observable: A creation action available before reminders remains available with the same required inputs and permissions, even when the new invoice lacks a reminder prerequisite.
Source: implied: U-7 adds follow-up to existing billing

### C-75: An invoice can still be issued through any pre-existing issuance workflow.
Observable: A caller previously able to issue an invoice can still do so when reminders are paused or the delivery service is unavailable.
Source: implied: U-7 preserves the existing issuance operation

### C-76: An invoice can still be edited under the pre-existing edit rules.
Observable: A previously permitted change to a due date, recipient, invoice reference or other invoice field still succeeds under the same permissions and validation even after a reminder attempt.
Source: implied: U-7 preserves invoice editing

### C-77: Payment recording remains independent of reminder state.
Observable: A payment or payment reversal that the existing billing workflow would accept still records with its usual effect on the balance and lifecycle, even during a reminder handoff or outage.
Source: implied: U-3 relies on existing payment recording

### C-78: Credits and balance adjustments retain their existing billing effect.
Observable: An authorized credit or adjustment updates the displayed balance under pre-existing billing rules even if a reminder opportunity is open.
Source: implied: U-3 relies on the existing balance calculation

### C-79: Invoice closure retains its existing billing behavior.
Observable: Where previously supported, authorized payment settlement, voiding, cancellation, write-off or deletion keeps its existing result even if a reminder is in progress.
Source: implied: U-3 preserves existing ways to close or remove an invoice

### C-80: Existing invoice delivery remains available independently of reminders.
Observable: Where issuance notices or manual invoice sends already exist, their normal triggers, destinations and permissions are the same with reminders enabled or disabled.
Source: implied: U-2 adds an automatic follow-up to existing invoice handling

### C-81: Existing invoice lookup permissions continue to govern invoice access.
Observable: Enabling reminders does not change which invoice details a customer, staff member or account administrator could already retrieve through that person's existing invoice access.
Source: implied: U-5 adds authorized access to reminder history without changing access to invoices

### C-82: Reminder records are visible only to authorized billing administrators in the invoice’s account.
Observable: A recipient, a caller without account billing administration permission or an operator without separate account billing administration permission cannot retrieve reminder settings, eligibility or invoice-level history through reminder surfaces. Supplying another account’s identifiers reveals neither the record nor its existence.
Source: implied: U-1 and U-5 give account reminder visibility only to authorized account staff

### C-83: Automatic reminder activity leaves the invoice’s billing facts intact.
Observable: Even after acceptance, rejection, timeout, bounce and retry, the invoice shows the same lifecycle, original amount, outstanding balance, currency, due date, payment records, credit records, invoice reference and designated billing address unless changed by the existing billing system.
Source: implied: “reminders for unpaid invoices” requests communication about invoices while preserving billing data

### C-84: A reminder contains no billing data belonging to another invoice or account.
Observable: Running simultaneously for two invoices, including invoices with identical references or addresses, yields messages with billing facts drawn only from the matching invoice and its own issuer.
Source: implied: U-2 requires each recipient to get the right invoice’s reminder

### C-85: Untrusted invoice text cannot add recipients or message headers.
Observable: An issuer name or invoice reference containing line breaks or header-like text remains message content. It cannot change the destination, add recipients or introduce a mail header.
Source: implied: U-2 requires delivery only to the intended billing recipient

### C-86: Production customer reminders cannot be sent by a nonproduction environment.
Observable: Copying production data into a development, preview or staging environment results in zero handoffs to production customer destinations. A nonproduction environment may use designated synthetic invoices with controlled test destinations.
Source: choice: exercising the feature outside production must not contact real customers

### C-87: Reminder history needed to prevent repeats survives rollback and re-upgrade.
Observable: After the operator pauses globally, rolls back and later re-upgrades, the authorized administrator can see prior attempt identities and outcomes. Accepted, permanently rejected, exhausted and uncertainty-closed opportunities remain closed.
Source: implied: U-8 requires recovery of the same history across release changes

### C-88: Re-upgrading after a rollback leaves global handoffs paused.
Observable: After restoring the reminder-enabled version, no new handoff begins until the authorized operator confirms the global state is running by resuming it.
Source: choice: re-upgrade must not release mail before the operator verifies readiness again

### C-89: Account enablement survives rollback and re-upgrade.
Observable: Each account recovers the enabled or disabled setting saved before a rollback.
Source: choice: the account’s saved intent remains available when the feature returns

### C-90: Reminder history has the same lifetime as the associated invoice.
Observable: The authorized administrator can read prior attempts while the invoice exists and can be looked up. If a deleted invoice can be restored, its attempts return with it. Permanent invoice removal ends retention of its reminder history.
Source: choice: keep the trace for as long as the invoice could be eligible without requiring permanent retention after removal

### C-91: A permanently removed invoice’s identity cannot authorize reminders again.
Observable: An old timer or result replayed after permanent removal causes zero handoffs for that identity. A new invoice with the same display reference has its own identity.
Source: implied: U-3 excludes removed invoices and U-7 can encounter reused display references

### C-92: Invoice-level reminder history omits the raw email and its destination.
Observable: Staff viewing reminder history see attempt and outcome fields without the raw body, original email address, delivery credentials or raw service response.
Source: choice: the operational history needs a minimal status trace rather than another copy of billing correspondence

### C-93: Automatic handoffs can begin without a signed-in billing user.
Observable: With an enabled account, global processing running and delivery available, a continuously eligible invoice shows an outbound attempt begun while no billing user had an active session.
Source: implied: “automatic” applies even when nobody is using the billing application

### C-94: A continuously eligible reminder starts a handoff within five minutes of becoming eligible under healthy conditions with available capacity and no backlog.
Observable: In those conditions an eligible invoice whose window opens at 09:00 UTC shows an attempt beginning by 09:05 UTC. The same upper bound applies when a saved enablement, data correction, dependency recovery or retry wait ending makes an open opportunity eligible. If eligibility ends first, the start must still meet the eligibility and window rules.
Source: choice: an explicit normal handoff bound makes automatic operation verifiable while allowing periodic work

### C-95: Healthy automatic processing continues admitting eligible work while there is backlog and available delivery capacity.
Observable: When capacity frees up during a large run, processing continues for eligible invoices before their windows close. If capacity suffices to process the eligible set within its windows, each eligible invoice is processed. The resulting sequence has no required delivery order because U-9 requires portfolio coverage without ordering invoices against one another.
Source: choice: temporary backlog can delay a handoff without turning into a pause

### C-96: An operator can recognize stalled automatic evaluation while global processing is running.
Observable: The scheduling capability shows unavailable if no evaluation tick has completed within 10 minutes of entering running or within 10 minutes after the last completed tick, whichever starting point is later. A completed tick confirms that automatic evaluation ran. It can complete with zero candidates or while handoffs from earlier evaluations are still pending.
Source: choice: two normal evaluation intervals separate scheduler failure from an empty account

### C-97: A submitted account setting takes effect only when that write commits.
Observable: Two successful writes to the same account take effect in commit order. A failed write that never commits leaves the prior value in effect. If the result of a write is lost, an authorized read shows the value currently committed.
Source: implied: U-1 and U-4 depend on a single authoritative account setting

### C-98: A global control write takes effect only when that write commits.
Observable: Concurrent successful pause and resume requests take effect in commit order. A missing or invalid requested state is refused. If the caller loses the response, the saved global state lets the operator verify whether handoffs are paused.
Source: implied: U-8 depends on confirming the effective stop

### C-99: A begun external handoff counts as one attempt across interruptions.
Observable: If processing stops after an external handoff could have begun and before its result is recorded, recovery preserves that attempt identity and resolves it using the in-progress or acceptance-unknown rules. It cannot start another service submission under the same attempt identity. Work known to have stopped before any handoff begins does not count as an attempt.
Source: implied: U-6 depends on distinguishing internal preparation from possible external submission

### C-100: An earlier opportunity retains its terminal disposition after a later handoff begins.
Observable: An accepted, permanently rejected, exhausted or uncertainty-closed 1-day opportunity keeps its terminal disposition when the 7-day opportunity starts. Earlier opportunities without terminal outcomes become superseded.
Source: choice: showing the recorded outcome preserves the explanation of what happened to each opportunity

### C-101: A late temporary rejection leaves the opportunity visibly closed by uncertainty when uncertainty already barred retries.
Observable: The history shows the late temporary rejection on its attempt while the opportunity still shows closed by uncertainty, even if it was the third attempt. A late acceptance or permanent rejection shows the corresponding terminal disposition.
Source: choice: the current attempt evidence and the reason that no retry was made must both be intelligible

### C-102: A retry date uses the last definitive temporary rejection for the same opportunity.
Observable: If the first and second attempts are temporarily rejected at 09:05 UTC and 09:25 UTC, the second retry cannot begin before 09:40 UTC. The opportunity’s start and close dates after a due-date edit still come from the current due date.
Source: choice: each retry gets its own minimum recovery interval

### C-103: An invoice’s attempt history remains readable when its due date becomes invalid or missing.
Observable: Removing an invoice’s due date leaves its recorded attempts visible. The administrator sees that there is no current schedule until an authoritative due date is available again.
Source: implied: U-5 and U-11 require prior delivery to stay traceable across invoice edits

### C-104: An unverifiable delivery result leaves reminder history unchanged.
Observable: A fabricated result claiming acceptance for a real attempt leaves its recorded outcome as it was.
Source: implied: U-5 relies on the integrity of the reported outcome

### C-105: An accepted reminder’s downstream delivery remains the responsibility of the delivery service.
Observable: If the delivery service defers or tries downstream delivery again after acceptance, the reminder feature records no second application handoff for that opportunity. Actual inbox-delivery timing is unconfirmed.
Source: implied: U-2 is subject to the responsibility transfer in [SMTP RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5)

### C-106: The previous application version cannot originate automatic reminder handoffs.
Observable: After rollback to the version preceding this feature, enabled accounts with open opportunities produce no new feature handoffs while that version is active.
Source: implied: U-8 returns to the version without automatic reminders

### C-107: A reminder window uses the date shown as the invoice’s due date in billing.
Observable: If billing shows December 31 as the due date, the first opportunity opens January 1 of the following year at 09:00 UTC. For a due date of February 28 in a leap year, it opens February 29 at 09:00 UTC. Changing the viewer’s locale or time zone does not change the invoice date used for this calculation.
Source: choice: calendar arithmetic starts from the authoritative invoice date as the recipient understands it

### C-108: An opportunity’s visible disposition follows its current controlling condition.
Observable: Acceptance and permanent rejection take precedence over exhausted retries or closure by uncertainty. Any of these terminal dispositions takes precedence over supersession. Supersession takes precedence over an in-progress attempt, which can be shown through the window close. With none of those conditions, the opportunity is scheduled before its window, expired at or after its close, or open within it. Within the window, an outstanding retry delay shows waiting to retry instead of open. An open window can coexist with an invoice-level blocker.
Source: choice: a single precedence rule keeps the history intelligible through calendar changes, blocking conditions and delayed results

### C-109: A handoff that begins inside its window can resolve after the window closes.
Observable: A handoff that begins just before 09:00 UTC at the end of its 24-hour window is recorded as accepted when authoritative acceptance arrives just after 09:00 UTC. A rejection at that time creates no further attempt in that closed window.
Source: implied: U-5 records the actual outcome of a submission that was eligible when it began

### C-110: A live account is required for reminder handoff.
Observable: If an invoice record remains available for billing history after its owning account is deleted, the record produces no new handoff. A newly created account using the same display name has its own disabled setting.
Source: implied: U-1 grants reminder permission to the invoice’s own account

### C-111: The operator can view global reminder health without account billing details.
Observable: Health and control views show the global state, last completed evaluation time or absence of one, and dependency availability. Invoice references, recipient addresses, balances, message contents and account settings require separate account billing access and are outside these global views.
Source: choice: operating the global switch does not require seeing customer billing data

### C-112: A reminder requiring an unsupported internationalized mailbox is ineligible.
Observable: The feature accepts a valid single baseline SMTP mailbox with an ASCII local part and a valid transport domain within the stated length bounds. A mailbox that requires SMTPUTF8 is unusable if the delivery service lacks that capability. Support for SMTPUTF8 by the eventual service is unconfirmed and optional because baseline Internet email provides the minimum delivery path.
Source: choice: baseline Internet email is sufficient. [SMTPUTF8 RFC 6531 §3.2](https://www.rfc-editor.org/rfc/rfc6531.html#section-3.2) requires an advertising server for SMTPUTF8 submissions.

### C-113: A deliverable reminder uses a sender identity permitted by the outbound service.
Observable: On an accepted production message the sender identity is one the delivery service authorizes for reminders. The identity need not be the issuer’s own mailbox. The minimum billing content identifies the issuer independently.
Source: implied: U-2 depends on a valid sender under the service’s production submission rules

### C-114: An authoritative post-acceptance bounce establishes acceptance for the matching unknown attempt.
Observable: If an attempt is acceptance unknown and the delivery service supplies evidence tying an actual post-acceptance bounce to that attempt, the attempt shows accepted with a bounce. The opportunity remains closed.
Source: choice: verified downstream failure is evidence of acceptance and also records why the recipient did not receive the email

### C-115: A reminder-setting or history read reports unavailability when its authoritative data cannot be obtained.
Observable: If the data source is unavailable, an authorized caller sees that the requested setting, eligibility or history is unavailable. This is distinguishable from disabled, ineligible or a successful lookup with no attempts.
Source: implied: U-1 and U-5 rely on committed information to interpret what the service will do or has done

### C-116: A handoff starts when the outbound delivery service is first asked to submit the individual reminder.
Observable: Opening a connection, preparing a message or scheduling future work causes no attempt by itself. The attempt starts with the first request to the service to submit that reminder for its intended recipient. The cutoff for current eligibility, pause and the send window is this start.
Source: implied: U-4 and U-6 require a single observable boundary between preparation and possible external delivery

### C-117: An expired calendar window alone does not permanently consume its opportunity.
Observable: An invoice due June 1 misses its 1-day window. The administrator changes its due date to June 10 before any later handoff begins. Its 1-day identity can now qualify during the June 11 window if it has no terminal outcome and remains within its attempt allowance.
Source: choice: a corrected due date reschedules an unsent opportunity while keeping acceptance, rejection and retry history intact

### C-118: The five-minute unknown deadline governs reporting rather than the underlying email transport timeout.
Observable: Where direct SMTP reaches the final message reply, a response can still arrive and update the attempt after the five-minute product deadline. SMTP’s recommended allowance for this final reply is 10 minutes from the end of message data. The eventual outbound service’s transport timeout is unconfirmed.
Source: implied: U-5 uses the late response allowed by [SMTP RFC 5321 §4.5.3.2.6](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.6)

### C-119: The first definitive authoritative handoff outcome survives conflicting later handoff reports.
Observable: A definitive acceptance or rejection for the same attempt remains recorded when a conflicting response arrives later. A verified post-acceptance bounce remains a separate outcome of downstream delivery.
Source: choice: the first definitive result controls retry safety and the handoff’s recorded outcome

### C-120: A reminder email has a single message origination date field.
Observable: A received reminder includes one email Date field showing message origination time, independently of the invoice due date stated as billing content.
Source: implied: U-2’s email follows the mandatory origination date in [Internet Message Format RFC 5322 §3.6](https://www.rfc-editor.org/rfc/rfc5322.html#section-3.6)

### C-121: Existing restrictions on sending billing email apply to automatic reminders.
Observable: Where the existing billing system blocks outbound billing email for the account, invoice or designated address, a reminder is skipped under the same block. These are the applicable scopes. The feature does not introduce a separate customer preference or override.
Source: implied: U-2 adds a billing email path subject to any existing billing email restrictions

### C-122: An existing billing email block is visible in the invoice’s reminder eligibility.
Observable: A billing administrator viewing an invoice blocked by a pre-existing email restriction sees that the restriction prevents a reminder. This is distinct from missing or invalid address data.
Source: choice: staff need to distinguish an intentional sending restriction from data they can correct

### C-123: A confirmed pause is required before the normal rollback can proceed.
Observable: The operator sees rollback readiness only after the global state is confirmed paused. A failed pause write or an unavailable state read leaves normal rollback pending while the operator re-establishes the stopped state.
Source: choice: an unconfirmed stop can leave the running version able to initiate customer email during rollback
