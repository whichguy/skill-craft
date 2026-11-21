## Use cases

### U-1: A billing operator sets up automatic reminders to follow up on open invoices
Flow: The operator reviews the reminder policy, enables it for their billing account, and sees when it takes effect. An issued invoice with an outstanding balance reaches a reminder time without anyone sending it manually. The recipient sees an invoice-specific email. If the account cannot send mail, the operator sees why activation is refused.
Source: request

### U-2: An invoice recipient uses a reminder to identify what they owe
Flow: The recipient opens the email and identifies the issuer, invoice reference, payment due date, outstanding balance and currency. They follow the issuer's normal invoice instructions. If the invoice is paid before a later reminder can leave the system, that reminder is suppressed.
Source: implied: a reminder for an unpaid invoice must let its recipient identify the obligation

### U-3: A billing operator follows an invoice through repeated reminders to see when follow-up ends
Flow: The operator reviews the policy for an invoice still outstanding after its first reminder. At each remaining scheduled opportunity, the invoice is checked again. Once all opportunities are used or the invoice has no collectible balance, the operator sees no further reminder scheduled under the current facts.
Source: implied: automatic follow-up can run repeatedly while invoices remain unpaid

### U-4: A billing operator enables reminders on an empty or busy account to cover the whole account
Flow: On an account with no eligible invoices the operator can enable reminders and sees that none are due. On a busy account the operator checks individual invoices, including those near the end of the workload, and can distinguish completed, pending and missed opportunities.
Source: implied: automatic reminders must work with zero invoices and when many invoices fall due together

### U-5: A billing operator corrects unusable invoice information to allow future reminders
Flow: The operator sees a reason on an invoice that lacks a due date or usable billing email, corrects the source record using the ordinary invoice workflow, and checks which reminders remain available.
Source: implied: an unpaid invoice can lack information needed for automatic contact

### U-6: A billing operator investigates a delivery failure to understand whether further action is needed
Flow: The operator finds the invoice and reminder opportunity, distinguishes a refusal from an uncertain outcome, then verifies whether a retry is pending or the opportunity has ended.
Source: implied: outbound delivery can fail independently of invoice eligibility

### U-7: An unauthorized user tries to manage another account's reminders and is refused
Flow: The user attempts to view reminder activity or change settings. The action is refused without showing the other account's invoices, recipients or operational details.
Source: implied: invoices and their follow-up are private to the parties authorized to access them

### U-8: A billing operator changes the policy to adjust future follow-up
Flow: The operator saves a new set of offsets and sees the effective policy. Invalid input is refused with the prior policy intact. Existing invoices show the remaining opportunities under the new policy.
Source: implied: operating automatic reminders requires knowing which schedule will actually run

### U-9: A billing operator pauses an account or invoice to stop unwanted follow-up
Flow: The operator pauses the whole account or suppresses one invoice. They verify the control took effect, inspect any opportunity already released to email, and resume when appropriate. Past opportunities do not become a backlog.
Source: implied: an operator needs to stop or reverse mistaken automation

### U-10: A billing operator brings existing invoices into automatic follow-up
Flow: On first activation, pre-existing invoices use their current invoice data. The operator sees only future opportunities under the policy and can see why old or incomplete invoices have no upcoming reminder.
Source: implied: accounts already hold invoices before this feature is enabled

### U-11: A service operator checks automation health to find a fault
Flow: The service operator sees whether scheduled evaluation is progressing and whether delivery results are accumulating. An authorized billing operator can locate the affected invoice and read its individual outcome and reason.
Source: implied: managed automation needs both a service-level health check and individual diagnosis

### U-12: A service operator stops reminder dispatch to roll back a release safely
Flow: The service operator stops new reminder dispatches across all accounts and verifies the stop before rolling back. Already released messages may still arrive. After restoration, the operator can verify preserved account settings and invoice history before deliberately resuming.
Source: implied: the new automation must be reversible without losing billing records or repeating prior sends

### U-13: A billing operator changes an invoice during processing to keep the reminder accurate
Flow: A payment, credit or invoice edit commits while reminder processing is under way. The operator checks the current invoice and reminder history. A change committed before release governs that release. If a reminder already left, its original result stays visible and the change governs later decisions.
Source: implied: U-2 and U-3 depend on how ordinary invoice updates meet scheduled processing

### U-14: A service operator verifies recovery after an interruption to identify missed work
Flow: Scheduled processing stops before a run finishes. The operator checks stale progress, then sees completed evaluations resume. Billing operators can distinguish work recovered inside its original window from expired or unresolved opportunities.
Source: implied: U-4, U-6 and U-11 depend on what recovery does to each invoice's outstanding work

### U-15: A service operator verifies reminder delivery in a nonproduction environment
Flow: The operator enables reminders for a test account and follows an eligible test invoice to its designated test inbox. An attempted release to an address outside the designated test recipients is blocked.
Source: implied: production and nonproduction have different delivery permissions

## Clauses

### C-1: An enabled account sends reminders automatically for eligible unpaid invoices
Observable: Leave an eligible invoice outstanding through a configured reminder opportunity with mail service available. The recipient receives a reminder without anyone taking a per-invoice send action.
Source: request

### C-2: Automatic reminders use email
Observable: At a successful opportunity, the invoice's designated billing recipient receives an email. Automatic SMS, postal mail, push notifications and calls are outside this policy because email provides direct invoice follow-up through one channel.
Source: choice: the request leaves the channel open

### C-3: Enabling reminders succeeds for an eligible account with no invoices
Observable: Enable an account with a ready mail setup but zero invoices. It shows as enabled with zero due opportunities.
Source: implied: U-4

### C-4: The number of invoices due together imposes no feature-level cut-off on which invoices are considered
Observable: Make many invoices due together. Each can be found by its invoice reference with its own opportunity outcome, even when the sending window expires before all mail can be submitted. The supported concurrent workload of the eventual runtime is unconfirmed.
Source: implied: U-4

### C-5: An invoice without a schedulable due date cannot trigger an email
Observable: Clear the invoice's due date before a dispatch. The invoice has no reminder sent on the basis of its old due date.
Source: choice: the post-due schedule requires the invoice's own due date

### C-6: Each email identifies its invoice
Observable: A recipient can identify the issuing business and the invoice reference used in the ordinary billing workflow.
Source: implied: U-2

### C-7: Each email reports the outstanding balance
Observable: On a partially paid invoice the email gives the remaining amount in the invoice currency.
Source: choice: the balance is the amount the recipient can act on

### C-8: Each email states the invoice due date
Observable: The recipient can read the invoice's payment due date.
Source: choice: the due date explains why payment is being requested

### C-9: An invoice with no outstanding balance cannot trigger a reminder
Observable: Settle an invoice before a later opportunity. No reminder is issued at that opportunity.
Source: implied: the request limits reminders to unpaid invoices

### C-10: A delivery failure on one invoice is isolated from other invoices
Observable: Cause one recipient's message to be refused while other recipients are reachable. The other invoices can still progress to their own outcomes.
Source: implied: U-4 and U-6

### C-11: Reminder access requires authorization for the invoice or account being accessed
Observable: An unauthorized caller cannot view another account's reminder settings, invoice reminder status or recipient information, or change any of its controls.
Source: implied: U-7

### C-12: Reminders are evaluated against the invoice's owning billing account
Observable: Two accounts can each have an invoice with the same displayed reference. Enabling one account affects only its own invoice.
Source: implied: U-1 and U-7 require settings to resolve to the account that owns an invoice

### C-13: Each reminder opportunity belongs to one issued invoice identity
Observable: Two separate invoices for the same customer can each trigger a reminder, even if their dates and amounts match. Editing a displayed reference does not create a new invoice for reminder purposes.
Source: implied: U-1 and U-3 require an invoice to be found consistently across runs

### C-14: Only an issued invoice classified as open for collection can trigger a reminder
Observable: With an otherwise eligible positive balance, an issued open invoice can progress, including an overdue or partially paid invoice. Draft or otherwise unissued, paid, voided or cancelled, written-off or otherwise uncollectible, disputed or on collection hold, and missing or unmapped collection states are excluded. The list describes billing semantics so differently named legacy statuses can map to the same rule.
Source: choice: omit invoices for which automated collection would be premature, inappropriate or uncertain

### C-15: The billing system's current collectible balance determines whether an open invoice is unpaid
Observable: A partially applied payment or credit leaves the collectible remainder eligible when it is greater than zero. A zero, negative, unavailable or indeterminate balance does not qualify.
Source: implied: U-2 and U-3 require the amount still owed to control follow-up

### C-16: A reminder goes to the invoice's designated billing email at dispatch
Observable: An invoice with one usable designated address sends only to that address. An invoice with no usable designation or multiple unresolved designations sends to nobody. The system does not substitute a general customer contact, copy another recipient or reuse the address from a previous reminder.
Source: choice: an explicit invoice-level destination avoids guessing who should receive private billing information

### C-17: A usable billing email is a single address accepted by the ordinary billing address validation rules
Observable: A missing or blank address, display text with no address, or a value the billing system rejects as malformed prevents dispatch. A syntactically acceptable address can still fail during delivery.
Source: choice: use the billing system's definition of a valid address without making up a separate deliverability test

### C-18: A schedulable due date is a valid calendar date supplied by the invoice
Observable: A missing, impossible or unresolvable date prevents scheduling. The issue date and account activation date are never substituted.
Source: choice: use authoritative invoice terms as the basis of the post-due schedule

### C-19: The default policy schedules reminders 1, 7 and 14 calendar days after the due date
Observable: Under the default policy, an invoice due June 1 has nominal opportunities on June 2, June 8 and June 15. There is no reminder on or before June 1.
Source: choice: three opportunities provide initial follow-up and two spaced follow-ups with a defined end

### C-20: Each opportunity becomes due at 09:00 UTC on its scheduled calendar date
Observable: An invoice due June 1 has its default first opportunity on June 2 at 09:00 UTC, regardless of the operator's, customer's or host's time zone. The operator sees the scheduling time zone when reviewing the policy.
Source: choice: one clock gives the same interpretation to a date-only invoice across accounts and environments

### C-21: A configured policy has one to three distinct offsets from 1 through 365 whole calendar days after the due date
Observable: A policy with offsets of 2 and 10 days is valid. Zero offsets, four offsets, duplicate offsets, fractional days and offsets outside 1 through 365 are refused. Valid offsets are interpreted from smallest to largest regardless of the order entered.
Source: choice: the operator can tune the timing while keeping each sequence finite and post-due

### C-22: Each invoice has at most three lifetime reminder opportunities that can be used
Observable: A position is consumed at the first release or when a release could have occurred but cannot be verified. After positions 1, 2 and 3 are consumed, the same invoice cannot acquire a new opportunity. An allowed retry belongs to its original opportunity.
Source: choice: cap repeated automated contact for the same obligation

### C-23: A reminder gives the recipient a way to find the invoice through the issuer's ordinary invoice process
Observable: The recipient has the invoice reference plus a route to use it, such as the existing invoice destination or instructions to obtain the invoice from the issuer. A payment link, attachment, exact subject, text template, branding and localization are left open because recognizing and finding the invoice is sufficient.
Source: choice: keep the reminder actionable without requiring a new payment or document-delivery channel

### C-24: Automatic reminders start disabled for each billing account
Observable: An existing or newly created account shows reminders disabled until an authorized operator enables them. Merely deploying the feature sends zero emails.
Source: choice: activating customer contact is an explicit decision

### C-25: A billing operator can inspect the effective reminder policy for their account
Observable: The operator sees the account's enabled or disabled state, effective offsets, scheduled time and time zone, and when the current policy took effect.
Source: implied: U-1 and U-8 require verification of the policy in use

### C-26: A billing operator can enable reminders for their account
Observable: Successful activation shows the account as enabled with its effective time.
Source: implied: U-1 and U-4

### C-27: Activation is refused when outbound email is not ready for that account
Observable: With outbound mail disabled in the current environment, the account's sending identity unapproved for that environment, or outbound delivery access missing or known invalid, an enable attempt reports the blocking condition and the account remains disabled. Invoice-specific data gaps affect those invoices only.
Source: choice: avoid reporting successful setup when customer delivery is known to be unavailable

### C-28: A billing operator can change the account's day offsets
Observable: Save a valid set of offsets and see the full effective set and its effective time. Subsequent opportunity evaluation uses the saved offsets subject to the opportunity history rules.
Source: implied: U-8

### C-29: A rejected policy change leaves the last effective policy intact
Observable: Submit invalid offsets and see the reason for refusal. Reading the policy afterwards returns the same offsets, enabled state and effective time as before the rejected change.
Source: implied: U-8

### C-30: A billing operator can disable automatic reminders for their whole account
Observable: Disable the account and see the effective disabled state. From that point the account has no new reminder dispatches until re-enabled.
Source: implied: U-9

### C-31: A billing operator can suppress automatic reminders on one invoice
Observable: Suppress one invoice and see its suppression state and effective time. No new reminder leaves for that invoice while suppressed. A different eligible invoice in the enabled account can still send.
Source: implied: U-9

### C-32: A billing operator can remove an invoice's reminder suppression
Observable: Remove suppression and see the invoice is no longer individually suppressed. The account and service controls and remaining opportunity rules determine whether it can send again.
Source: implied: U-9

### C-33: Existing invoices are evaluated when the account first enables reminders
Observable: An invoice issued before the feature existed can show a future reminder without being reissued or edited, if its existing data qualifies. The operator can see that a prior scheduled time has already passed or that prerequisite data is unavailable.
Source: implied: U-10

### C-34: Billing operators can locate reminder activity for an individual invoice
Observable: Using the existing invoice lookup or a reminder-specific lookup, the operator can find an invoice even after a high-volume run and see its eligibility and available outcomes. If displayed references collide, the operator can distinguish the matching invoices by their invoice identities.
Source: implied: U-6 and U-11

### C-35: The invoice's reminder view explains whether it has a future opportunity
Observable: The operator sees the next nominal time currently available, including a due time if evaluation is pending inside its window. If none is available, the operator can determine whether a dispatch gate in C-80 is unmet, all admitted times have elapsed, or every configured position is already used or closed at its nominal time. A scheduled time is a projection based on current facts.
Source: implied: U-3, U-5 and U-11 require an explanation even when zero messages are sent

### C-36: Each recorded opportunity has an operator-visible disposition
Observable: The operator can distinguish waiting for its scheduled time, due and awaiting evaluation, waiting for a retry, released and awaiting a result, accepted by the email service, skipped before release, expired without release, failed with confirmed nonacceptance, and unresolved because acceptance is uncertain.
Source: implied: U-6 and U-11 require meaningful distinctions between failure, pending work and submission

### C-37: Each attempted or closed opportunity exposes its diagnostic facts
Observable: The operator sees the invoice reference, opportunity position, nominal time, last state-change time, disposition, applicable reason, count of releases including any possible but unverified release, next retry time if any, and the destination used for each released attempt if the operator is ordinarily allowed to view that invoice's billing email. Message bodies and raw provider responses are omitted because those contents are unnecessary for diagnosis.
Source: choice: preserve enough evidence to diagnose one invoice without storing or exposing extra message content

### C-38: Service operators can determine whether scheduled reminder processing is progressing
Observable: The service operator can see the latest completed evaluation time, whether service dispatch is stopped, and totals for accepted, awaiting retry, uncertain, confirmed failed, bounced and expired opportunities. For totals over a reporting interval the interval is visible. The interval selection and presentation are left open because the reported time coverage is what the operator relies on.
Source: implied: U-11

### C-39: Customer emails already released for dispatch cannot be recalled through reminder controls
Observable: After mistaken release, disable the account or suppress the invoice. The operator sees the existing attempt or outcome in history, and the control prevents later releases within its scope. Mail already handed off can still reach the recipient.
Source: choice: email does not offer a dependable product-level recall

### C-40: A service operator can stop new reminder dispatch across all accounts
Observable: Apply the service-wide stop and see its effective time. No new reminder is released across any account while the stop is in effect.
Source: implied: U-12

### C-41: A service operator can resume service-wide dispatch
Observable: Clear the service-wide stop and see its effective time. Accounts resume subject to their own enabled state and each invoice's suppression and remaining opportunities.
Source: implied: U-12

### C-42: Rolling back the reminder release preserves existing billing data
Observable: Stop dispatch and roll back. The prior billing version can still read the same invoices, payment balances and designated billing contacts through its ordinary billing functions.
Source: implied: U-12

### C-43: Restoring the reminder release preserves reminder decisions recorded before rollback
Observable: After restoration the operator can read the prior account policies, invoice suppression settings and recorded opportunity outcomes.
Source: implied: U-12

### C-44: Activation or resumption admits only opportunities scheduled strictly after the effective activation or resumption time
Observable: If the first slot was June 2 at 09:00 UTC and an account enables at 10:00 UTC that day, that slot is past even though its ordinary sending window is still open. The same rule applies when re-enabling the account, clearing invoice suppression or clearing the service-wide stop, each within its own scope.
Source: choice: enabling a control should govern future follow-up without producing a backlog

### C-45: Changing the offsets or due date recalculates the schedule only for unused positions
Observable: Positions are numbered 1 through 3 by ascending offset under each policy. Moving an unsent position to a new future instant moves its schedule. Removing a position removes its schedule. An opportunity counted as used at a given position, including an uncertain or confirmed failed release, permanently reserves that position for the same invoice even if offsets are replaced, removed or added back.
Source: choice: retain the lifetime contact limit while applying revised invoice terms and policies to remaining contact

### C-46: A moved or newly added nominal time must be strictly after the effective schedule change
Observable: At 10:00 UTC on June 2, changing the first position to 09:00 UTC on June 2 produces no release for that position. Correcting an absent or invalid due date uses the same rule. Maintaining an identical position and nominal time preserves its existing first-release eligibility.
Source: choice: applying a new schedule prospectively avoids retroactive contact

### C-47: An opportunity closes for its current nominal time when final evaluation finds the invoice ineligible
Observable: While a slot is due, a definitive exclusion at dispatch evaluation closes it as skipped with the applicable reason. Previewing upcoming opportunities or being unable to check authoritative facts is distinct from a definitive exclusion. Correcting the exclusion alone does not restart the same position at the same nominal time.
Source: choice: make each scheduled evaluation final for that nominal opportunity while permitting ordinary future follow-up

### C-48: Each nominal opportunity expires 24 hours after its scheduled time
Observable: A slot due June 2 at 09:00 UTC can release from that instant up to but excluding June 3 at 09:00 UTC. After a processing outage, slots still within their windows can proceed using current eligibility, subject to the activation and resumption rules. An admitted slot that is still pending at its deadline is shown as expired without release. The deadline does not replace a skipped disposition or an outcome from a release.
Source: choice: recover from brief delays without sending stale reminders

### C-49: Each release reflects the authoritative billing facts at the point it leaves product control
Observable: Pause processing just before the outgoing request is released to the email service. Any applicable dispatch gate that fails before release blocks it, including one changed after the work was scheduled. A change to the eligible invoice data committed before release is reflected in the email. A change committed after release applies to later releases.
Source: implied: U-2, U-5 and U-9 require the current facts to govern dispatch

### C-50: Overlapping processing cannot create multiple accepted emails for the same opportunity through product dispatch
Observable: Process the same invoice position concurrently or replay a completed run. One release is in progress at a time for that position. Another release is permitted only after affirmative evidence that all previous releases of that position were never accepted. A downstream duplicate outside product control is distinguishable from a second release by the product where the email service reports it.
Source: implied: U-3 assumes one successful reminder per opportunity

### C-51: Confirmed temporary nonacceptance triggers a bounded automatic retry of the same opportunity
Observable: After a temporary refusal explicitly confirms nonacceptance, the retry proceeds on the first available evaluation at or after 15 minutes from receipt of the definitive result, subject to provider delay, current gates and cancellation. At most 3 total releases are permitted per position, including the initial release. If the budget is exhausted or the retry cannot proceed before the original window expires, the disposition becomes failed with confirmed nonacceptance.
Source: choice: allow brief delivery interruption to recover without sending stale reminders or retrying indefinitely

### C-52: A later policy or due-date change cancels retries for an earlier schedule
Observable: After confirmed nonacceptance, change the account offsets to a different effective set or change the invoice due date before the retry. That retry is cancelled with a recorded reason. The released position stays used, and another available position follows the new schedule.
Source: choice: an operator's schedule change supersedes retries decided under earlier terms

### C-53: A confirmed permanent refusal ends the opportunity
Observable: If the email service explicitly declines acceptance for a permanent reason, the operator sees confirmed failure and the reported reason category. That position has no further automatic attempt even after the recipient address is corrected.
Source: choice: allow correction for a later slot without repeatedly trying an already failed slot

### C-54: A release of uncertain acceptance is never retried while uncertainty remains
Observable: If the connection times out after release, acknowledgement is lost, or processing stops after release could have occurred, the operator sees an unresolved outcome instead of a second dispatch. A later authoritative result can resolve it. Other positions remain subject to their own rules.
Source: choice: protect recipients from duplicate contact when delivery cannot be determined

### C-55: Delivery results update only the original release they describe
Observable: A delayed result for an earlier slot resolves that slot even when a later slot has run, with no new dispatch except a still-allowed retry after confirmed temporary nonacceptance. Replayed copies of the same result give the same history and do not increase the release count. An acceptance already confirmed is not reset by a late temporary response.
Source: implied: U-6 requires reliable outcomes when external results arrive late or more than once

### C-56: A pause after a release cancels any outstanding retries within its scope
Observable: Stop at service level, disable the account or suppress the invoice while a prior release could still be retried. The affected slot closes to further releases even if the control is later cleared before a result or the retry time arrives.
Source: choice: a pause must remain effective for work that was already under way

### C-57: A repeated request that saves identical reminder settings leaves their effective time intact
Observable: Save the current offsets in a different entry order, or apply an already active on, off, stop or suppress control again. It has the same effective state and time as before, so duplicate operator requests do not invalidate opportunities or alter eligibility.
Source: choice: an unchanged policy should not shift a schedule

### C-58: An interrupted run accounts for each invoice independently
Observable: If a run stops after some invoice emails were accepted, the completed positions retain their outcomes. Remaining invoices can still progress within their windows. Positions whose release cannot be verified are handled as uncertain instead of being sent again.
Source: implied: U-4 and U-6 require a recovery path after partial completion

### C-59: Automatic evaluation runs independently of an operator session
Observable: With the account enabled, the billing application active, scheduled execution available and outbound email ready, sign out every user. Eligible opportunities still progress. If scheduled execution is unavailable, the operator can see stale evaluation progress.
Source: implied: U-1, U-11 and U-14 require a background scheduling runtime with a clock and the ability to run without an interactive request. The hosting platform and its scheduling granularity are unconfirmed.

### C-60: Hitting the scheduled execution runtime's invocation cap preserves outstanding work
Observable: When a scheduled execution is interrupted by its maximum run duration, the next evaluation can account for previously completed, uncertain and untouched opportunities under their original windows. The runtime's hard duration cap is unconfirmed.
Source: implied: U-4 and U-11 depend on recovery across the scheduled execution runtime's invocation lifetime limit

### C-61: The product treats a mail service quota refusal as a delivery refusal
Observable: When the outbound email service explicitly confirms that a message was rejected due to a rate or sending-volume quota, its slot is eligible for the temporary-failure policy. If the service directs a longer minimum delay than 15 minutes, the retry respects that delay within the 24-hour window. The provider's rate and volume quotas are unconfirmed.
Source: implied: U-6 must respect the outbound email service's quota and retry constraints

### C-62: A mail request timeout cannot be reported as confirmed nonacceptance by itself
Observable: When the email service fails to acknowledge a released request within its effective response deadline, the operator sees uncertainty unless authoritative evidence resolves it. The outbound email request deadline is unconfirmed.
Source: implied: U-6 must account for the outbound email service being able to accept a request before its response reaches the caller

### C-63: The product reports service acceptance separately from recipient delivery
Observable: An accepted email has an acceptance outcome even when delivery is not reported. If the email service later reports a bounce for that email, the operator sees the bounce. Delivery confirmation and bounce reporting capabilities of the eventual provider are unconfirmed.
Source: implied: U-6 depends on the outbound email service's distinction between handoff acknowledgement and mailbox delivery

### C-64: A permanent sender or delivery authorization refusal blocks that release
Observable: If the outbound email service rejects a release because its sending identity or authorization is invalid, the operator sees a mail configuration failure. A provider restriction affecting trial environments, allowed destinations or sending identities is surfaced as a refusal within its scope. The provider's exact onboarding conditions and trial limits are unconfirmed.
Source: implied: U-1 and U-6 depend on the outbound email service's sender authorization and environment restrictions

### C-65: Development and test environments restrict delivery to designated test recipients
Observable: Try to exercise automatic reminders in a nonproduction environment with a real customer address outside the designated test recipients. No mail is released to that address. A designated test recipient can exercise the flow once test sending is ready.
Source: choice: U-15 needs to exercise scheduled email before production activation without contacting customers during development

### C-66: The billing operator can distinguish saved policy from stalled or blocked dispatch
Observable: With a policy enabled, interrupt scheduled execution, revoke mail authorization or apply the service-wide stop. The view preserves the saved enabled setting and indicates the execution issue, mail readiness issue or service stop as applicable. Provider recovery time and the platform's maximum detection delay are unconfirmed.
Source: implied: U-1 and U-11 depend on distinct readiness of billing, scheduling and outbound email services

### C-67: Reminder processing leaves invoice lifecycle operations available under their existing rules
Observable: Create a draft, issue an invoice, edit permitted fields, or cancel or void it through the billing system where those operations exist. Their ordinary validation, authorization and effects still apply with reminders enabled, disabled or unavailable.
Source: implied: the request adds invoice follow-up to U-1 and U-5

### C-68: Reminder processing leaves money movement and balance calculation under the existing billing rules
Observable: An ordinary payment, partial payment, credit, refund, reversal or write-off, where supported, is recorded and applied as before. A reminder success, refusal or timeout has no effect on the invoice balance or currency.
Source: implied: U-2 and U-3 use existing billing state as the input to follow-up

### C-69: Reminder processing does not replace existing invoice communications
Observable: If invoice issuance messages, receipts or manual invoice resends already exist, they still follow their own rules regardless of the automatic reminder controls. Sending one of those communications does not consume an automatic reminder position.
Source: implied: U-1 adds an automated action on top of the existing invoice workflow

### C-70: Only billing-account managers can change account reminder controls
Observable: A caller with the account's billing-management permission can enable, disable and change offsets. An invoice recipient, unrelated user or invoice reader without that permission is refused even if they can open a shared invoice.
Source: choice: customer-facing or read-only invoice access does not grant authority to automate contact

### C-71: Changing invoice suppression requires billing-management permission for that invoice's account
Observable: A manager can suppress or restore an invoice they manage. A recipient, invoice reader without billing-management permission, or manager of another account cannot change its suppression.
Source: choice: one authority governs automatic contact for both the account and the invoice

### C-72: Viewing invoice reminder activity requires the account's internal permission to read that invoice
Observable: An internal reader with permission for that invoice can view its reminder disposition. A public invoice viewer, a recipient using a shared link or an internal user without that permission cannot view reminder history. Visibility of addresses follows the ordinary billing contact permission.
Source: choice: existing internal invoice visibility determines access to invoice-specific automation status

### C-73: Viewing account reminder settings requires internal billing access to that account
Observable: An internal user authorized to view the account's billing settings can see the reminder policy. A recipient or user without that access cannot inspect it.
Source: choice: apply the account's existing billing-settings visibility to reminder policy

### C-74: Service-wide reminder controls require service-operator authorization
Observable: An authorized service operator can view service health and stop or resume dispatch across accounts. A billing-account manager acting only with account permission cannot read service-wide health or change service-wide dispatch.
Source: choice: keep service-wide powers separate from account billing powers

### C-75: Every route applies the same authorization requirements
Observable: Direct requests, bookmarked views, search results and ordinary interface actions enforce the same access checks for settings, invoice reminder history, invoice suppression and service-wide controls. Refused access reveals no invoice, address, policy or delivery facts about data outside the caller's permissions.
Source: implied: U-7 requires enforceable access independent of how the request reaches the product

### C-76: A reminder cannot expand access to invoice records
Observable: A destination included for viewing or paying an invoice follows the same access rules as the existing destination. A reminder for one invoice grants no access to another invoice, customer details or account controls.
Source: implied: U-2 and U-7 require invoice-specific contact without broadening access to billing records

### C-77: An automatic reminder cannot change invoice records
Observable: After an accepted, refused or unresolved reminder, the invoice identity, reference, issue date, due date, collection state, balance, currency, customer and designated billing email read the same as before, except for changes made through ordinary billing operations.
Source: implied: U-2 and U-12 require follow-up to preserve the underlying obligation

### C-78: Invoice removal ends reminder eligibility for the removed identity
Observable: If the billing system permits deletion, deleting an invoice before release prevents its reminder. A new invoice with the same displayed reference does not inherit the old identity's suppression or outcomes.
Source: implied: U-2 and U-9 apply controls and contact only to the invoice they concern

### C-79: Reminder amounts require an authoritative invoice currency
Observable: If the invoice currency is missing or invalid under the billing system's currency rules, the invoice is skipped. A supported currency uses the billing system's amount and precision as of dispatch, without substitutions or conversion.
Source: choice: never communicate an amount whose currency cannot be determined reliably

### C-80: A dispatch is allowed only while all dispatch gates are satisfied
Observable: A release requires all of the following at dispatch: service dispatch is not stopped; the account still owns the invoice with reminders enabled; the invoice is unsuppressed, issued and open for collection; the collectible balance is known and positive in a valid invoice currency; the due date is valid; exactly one usable billing recipient is designated; the issuer and invoice are identifiable; the delivery environment permits this sender and destination; and the opportunity is admitted under the current schedule and remains open for the contemplated release. Each unmet gate blocks release.
Source: implied: U-2, U-5 and U-9 require one consistent eligibility decision

### C-81: An invoice issued after an opportunity's nominal time cannot enter that opportunity
Observable: Issue a backdated invoice at 10:00 UTC on June 2. Its June 2 09:00 UTC slot is past. A later eligible slot can send. Ordinary refunds, reversals and collection-hold removal follow current eligibility without resetting any closed position at its old nominal time.
Source: choice: reserve the window for delays in processing issued invoices

### C-82: Temporary inability to verify billing facts defers evaluation within the original window
Observable: Interrupt access to authoritative invoice data before dispatch evaluation. The product sends nothing from stale data. If access returns within the window, evaluation can proceed for an open opportunity. If the window expires first, the opportunity is shown as expired once the product can account for it.
Source: choice: a billing service interruption is distinct from a verified ineligible invoice

### C-83: Every retry must satisfy the current dispatch gates
Observable: After a temporary refusal, the retry uses current invoice facts under the same gates as an initial release. If there is a definitive exclusion at retry evaluation, the opportunity ends with the exclusion as the cancellation reason and confirmed nonacceptance as the outcome.
Source: implied: U-2 and U-9 require that failure recovery respect the same billing and operator decisions

### C-84: Late outcomes cannot reopen an opportunity for which retries were cancelled
Observable: If a service stop, account disable, invoice suppression, due-date change or effective offset change occurred after a release, a later temporary refusal updates its outcome but cannot schedule a retry, even if the original window is still open and the controls and schedule have since been restored.
Source: choice: an outcome that arrives late must respect an intervening decision to stop an earlier schedule

### C-85: An unverified or uncorrelated result cannot change reminder history
Observable: A result that the product cannot attribute to the email service and match uniquely to a released attempt cannot change an invoice's disposition or cause a retry.
Source: implied: U-6 depends on outcomes being attributable to one actual release

### C-86: Each unsuccessful opportunity explains why it ended or is unresolved
Observable: The reason is identifiable as applicable from these categories: failed dispatch gate, nominal time already past when admitted or changed, schedule superseded, position removed from the policy, sending window elapsed, retry cancelled, retry budget exhausted, temporary refusal, permanent refusal, provider quota, provider authorization, provider bounce, or acceptance unknown. A failed gate or cancelled retry identifies the triggering condition. Provider-specific wording is left open because only the cause category is required.
Source: implied: U-5 and U-6 require the operator to distinguish corrective action from an ended opportunity

### C-87: Opportunity history remains available while the associated invoice is retained and accessible
Observable: Open a retained invoice after its schedule has changed or after its last opportunity. Recorded outcomes remain visible with their original position and nominal times. When invoice or account removal makes the original unavailable, access to any retained reminder history follows the ordinary billing deletion and access rules. Those rules and any post-removal retention period are unconfirmed.
Source: choice: retain diagnostic history for as long as the ordinary billing view can use it

### C-88: The service-wide stop remains effective after restoration from rollback
Observable: Stop dispatch, roll back and then restore the release. Until a service operator clears the stop, restoring the release sends zero new reminders.
Source: implied: U-12 requires restoration to preserve the explicit stop

### C-89: Concurrent control changes take effect in commit order
Observable: Two authorized operators save different policies or toggles at the same time. The last successfully committed change governs that control. Each acknowledgement identifies the value and effective time of its own change. If a change is refused or fails before commitment, it has no scheduling effect.
Source: choice: resolve concurrent operations by the same ordering used to decide dispatch eligibility

### C-90: Reminder health identifies a stalled evaluation interval
Observable: Once scheduled evaluation is active, show it as stalled when 30 minutes have elapsed since the last completed evaluation, or since it first became active if none has completed. Show the last completed time when one exists. A completed evaluation can have zero due invoices.
Source: choice: an explicit threshold distinguishes a quiet installation from an automation failure

### C-91: Healthy scheduled evaluation considers a newly due opportunity within 15 minutes
Observable: With the billing and mail services available and workload within supported capacity, a newly due opportunity is considered within 15 minutes of its nominal time. This bound governs evaluation rather than mailbox delivery. Platform capacity remains unconfirmed.
Source: choice: make the healthy schedule observable with enough margin for retries inside the 24-hour window

### C-92: An invoice is unsuppressed until an authorized operator suppresses it
Observable: A new or pre-existing invoice with no explicit suppression record is shown as unsuppressed. Account activation needs no individual opt-in for such invoices.
Source: choice: account-level activation covers eligible invoices by default

### C-93: Saving offsets while dispatch is off does not start dispatch
Observable: Save valid offsets while the account is disabled or while service dispatch is stopped. The offsets take effect for schedule calculation, with dispatch still blocked by the existing stop. Later enablement or resumption uses those saved offsets.
Source: choice: operators can prepare the policy without contacting customers

### C-94: An unidentifiable obligation cannot trigger an email
Observable: A legacy invoice without an identifiable issuer or an invoice reference usable in the ordinary invoice process is blocked with a missing issuer or missing invoice reference reason. If the ordinary process already recognizes an invoice identifier when its display reference is missing, that identifier is usable.
Source: implied: U-2 requires every sent reminder to identify the obligation

### C-95: A bounce cannot reopen a position
Observable: After a verified bounce, the operator sees downstream failure for the original release, even if the bounce is the first evidence the service accepted it. No retry of that position follows. A later position uses the then-current recipient.
Source: choice: a downstream failure is not evidence that the service refused the release

### C-96: Removal of an account ends reminder dispatch for that account
Observable: If an account is deleted, invoices associated only with that account cannot release reminders after the removal takes effect. The automated policy does not depend on the continued session or employment of the original enabling operator while the billing account and policy remain active.
Source: implied: U-1 and U-7 bind automation to the billing account

### C-97: A confirmed failure reason distinguishes a closed slot from a retry awaiting release
Observable: If the provider specifies a retry time at or beyond expiration, or the normal 15-minute minimum already puts the retry there, the operator sees a closed confirmed failure with the window as the reason. If the third release is definitively refused, the operator sees no fourth attempt. A reported retry time exists only while a further release remains possible under C-51, C-52, C-56, C-61 and C-83.
Source: implied: U-6 requires an operator to tell whether recovery can still happen

### C-98: Ambiguous provider responses are classified as uncertain acceptance
Observable: If the service reports a transport error, generic failure or conflicting result that does not establish nonacceptance for that release, no additional release follows on the strength of that result. For services lacking definitive negative results, automatic retries after release are unavailable for those responses.
Source: implied: U-6 depends on the outbound email provider's ability to confirm whether a message was accepted. The provider's result guarantees are unconfirmed.

### C-99: An invoice moved between accounts is evaluated prospectively under the new owner's policy
Observable: If invoice ownership can change while preserving the invoice identity, moving an invoice ends evaluation under the former account and cancels its pending retries. Only times strictly after the transfer can be admitted by the new account. Used positions remain used for that invoice identity.
Source: choice: keep the lifetime contact cap across an ownership change while preventing old work from being released

### C-100: Ownership changes do not disclose the former account's reminder history to the new account
Observable: The new account's operator can distinguish a used position from an available one. Details recorded under the former account, including policy, recipient and delivery facts, require permission to read that history in its original account scope.
Source: implied: U-7 applies to historical as well as current reminder records

### C-101: Healthy evaluation reports progress during idle periods
Observable: With scheduled evaluation configured and its dependencies available, its last completed time advances at least once every 15 minutes even when no invoices are due or dispatch is stopped. Before scheduled evaluation is configured, health shows that evaluation is inactive.
Source: choice: zero work and intentional suspension of sending should be distinguishable from a stalled scheduler

### C-102: The service-wide dispatch stop starts cleared on first installation
Observable: On the first installation, the service operator sees the service-wide stop cleared. Each account still starts with reminders disabled and must pass its activation gates. Restoring a prior installation follows C-88 instead.
Source: choice: let account operators enable a ready service without a separate service-wide activation
