## Use cases

### U-1: A billing operator enables reminders to automate collection follow-up
Flow: The operator checks the account's reminder setting, enables it, and sees that reminders are enabled. A later review shows the saved state. A malformed update is refused and leaves that state in effect.
Source: implied: “Set up automatic reminders” requires a way to put the automation into service.

### U-2: A billing recipient receives a reminder to identify an unpaid invoice
Flow: An issued invoice with an outstanding balance passes its due date. A reminder arrives without a manual send. The recipient identifies the invoice, the amount outstanding, and how to pay or get help.
Source: request

### U-3: A billing recipient receives later reminders to follow up on a still-unpaid invoice
Flow: The first reminder arrives. If the invoice is still unpaid, later eligible occurrences can produce reminders. When the schedule is exhausted, the recipient receives no more automatic reminders for that schedule.
Source: implied: “automatic reminders” applies to repeated follow-up without an endless sequence.

### U-4: A payer settles an invoice to end reminder follow-up
Flow: The payer pays in full. Once billing records the payment, no new reminder submission starts for that invoice. If the payer makes a partial payment instead, the next eligible reminder reflects the remaining balance.
Source: implied: “unpaid invoices” requires a current outstanding balance.

### U-5: A billing operator corrects an invoice or recipient to make follow-up accurate
Flow: The operator corrects the due date or billing address through the existing billing workflow. A subsequent reminder follows the current invoice and recipient data. If the correction leaves required data unusable, the operator can see why the invoice was skipped.
Source: implied: U-2 requires a usable due date and a valid destination.

### U-6: A billing operator pauses and resumes reminders to control automatic sends
Flow: The operator disables reminders while invoices are outstanding and sees the disabled state. Automatic sends pause. The operator re-enables reminders and eligible follow-up resumes under the current schedule.
Source: implied: U-1 needs a reversible way to stop automatic sends.

### U-7: A billing operator brings existing invoices into scope to avoid reissuing them
Flow: The operator enables reminders for an account with existing invoices. Eligible existing invoices participate using their recorded due dates. The operator also enables an empty account and sees no send activity.
Source: implied: U-1 can occur after invoices already exist.

### U-8: A person without billing authority attempts to change reminders and is refused
Flow: The person attempts to enable or disable reminders or inspect send outcomes. The action is refused, and the account's saved setting and private records are protected.
Source: implied: U-1 and U-6 act on private account data and can cause external communication.

### U-9: A billing operator investigates a failed reminder to understand whether it was sent
Flow: The delivery service rejects, delays, or gives an uncertain response to an attempted send. The operator can distinguish confirmed acceptance from failure or uncertainty. Eligible follow-up recovers automatically when safe.
Source: implied: U-2 depends on an external delivery service.

### U-10: A billing operator processes a large invoice population without losing eligible work
Flow: The account has more eligible invoices than can be processed at once, or the delivery service throttles traffic. The operator can distinguish processed, deferred, and expired work. Work that still qualifies can proceed as capacity returns.
Source: implied: U-2 applies to an account with many unpaid invoices.

### U-11: A billing operator withdraws an invoice to stop its reminders
Flow: The operator voids or otherwise withdraws an invoice through the existing workflow. Subsequent automatic attempts for that invoice are suppressed. A draft or otherwise unissued invoice also receives no automatic reminders.
Source: implied: U-2 requires an outstanding invoice the recipient is expected to pay.

### U-12: A release operator rolls back reminders while keeping prior billing data usable
Flow: The release operator confirms automatic sending is stopped for all accounts affected by the rollback, then returns to the previous release when one exists. Invoice, payment, and manual billing workflows remain usable. When reminders are later restored, accepted occurrences are still recognized.
Source: implied: U-6 includes taking the automation out of service during a rollback.

### U-13: A billing operator reviews reminder activity to explain what a recipient received
Flow: The operator looks up an invoice's reminder occurrences and sees which were skipped, attempted, or accepted. The operator can tell whether an acceptance means delivery was confirmed.
Source: implied: U-2 sends on the operator's behalf and U-9 needs outcomes that can be checked.

### U-14: A billing recipient gets follow-up on the correct invoice when several invoices are open
Flow: The same recipient has two invoices with their own balances and due dates. Each qualifying invoice can produce its own reminder. Paying one invoice ends follow-up for that invoice.
Source: implied: “unpaid invoices” applies to individual obligations, including several owed by the same customer.

### U-15: A billing operator restores valid billing data to make future reminders possible
Flow: The operator finds an invoice skipped for a missing or unusable due date, amount or currency, reference, issuer identity, billing destination, or way to act. They correct it through the billing workflow. An occurrence that is still open can qualify again.
Source: implied: U-5 includes recovery from incomplete data.

### U-16: A release operator verifies reminders before live billing use
Flow: The operator exercises an eligible reminder with approved test delivery. The operator verifies that live customer addresses remain protected in test, and that production submission depends on the authorized sender and environment.
Source: implied: U-1 can initiate real billing email after deployment.

## Clauses

### C-1: The system initiates reminders for unpaid invoices without a person initiating each send
Observable: After reminders are set up, a qualifying unpaid invoice produces a reminder even when nobody opens the invoice or requests a send.
Source: request

### C-2: Reminder activity is scoped to the billing account that owns the invoice
Observable: Enabling reminders for Account A produces no reminder for otherwise identical invoices owned by Account B.
Source: implied: U-1 acts on one billing account.

### C-3: An authorized billing operator can enable reminders for their account
Observable: The operator enables reminders and subsequently reads the enabled setting.
Source: implied: U-1 requires putting the automation into service.

### C-4: An authorized billing operator can disable reminders for their account
Observable: The operator disables reminders and subsequently reads the disabled setting.
Source: implied: U-6 requires withdrawing authorization to send.

### C-5: Reminders start disabled for each account
Observable: A newly created or upgraded account without a saved reminder setting shows disabled and produces zero automatic reminders until an authorized enable takes effect.
Source: choice: Explicit activation prevents an upgrade or account creation from initiating external messages.

### C-6: Automatic reminders use email
Observable: The qualifying reminder reaches the invoice's billing destination as email. The automation initiates zero SMS, push, postal, or phone reminders.
Source: choice: One billing channel suffices for routine invoice follow-up.

### C-7: A qualifying invoice has a positive outstanding balance
Observable: An invoice showing an outstanding balance of zero produces zero reminders. A partially paid invoice whose displayed amount still due is positive can qualify.
Source: implied: “unpaid invoices” requires an amount still owed.

### C-8: An invoice must be issued to qualify
Observable: A draft or other invoice awaiting issuance produces zero reminders even if it has a due date and positive total.
Source: implied: U-11 requires an invoice the recipient is expected to pay.

### C-9: The automatic schedule has three occurrences at 1, 7, and 14 calendar days after the due date
Observable: An invoice due April 10 has occurrences on April 11, April 17, and April 24, with zero occurrences on every other date for that due date. An invoice due February 28, 2028 has occurrences on February 29, March 6, and March 13, 2028.
Source: choice: Three overdue follow-ups provide a finite cadence with time to respond between messages.

### C-10: Existing invoices can qualify using their existing billing records
Observable: An eligible invoice created before activation can receive a reminder without being reissued or recreated.
Source: implied: U-7 uses invoices already on file.

### C-11: An empty account generates zero reminders
Observable: After enabling reminders on an account with no invoices, the recipient channel receives zero reminders attributable to the account.
Source: implied: “for unpaid invoices” gives the automation no subject in U-7.

### C-12: A reminder identifies the invoice
Observable: The recipient can match the reminder to the invoice using the invoice reference shown in the billing workflow.
Source: implied: U-2 requires the payer to know which invoice needs attention.

### C-13: A reminder states the current amount outstanding
Observable: An invoice issued for USD 100.00 with USD 60.00 still due shows USD 60.00 as the amount outstanding in the reminder.
Source: implied: U-4 requires follow-up for the amount still owed.

### C-14: A reminder tells the recipient how to act on the outstanding invoice
Observable: The recipient can identify at least one next step from the reminder: existing payment instructions, an authorized invoice or payment destination, or the issuer's established billing contact.
Source: implied: U-2 asks the recipient to address an unpaid invoice.

### C-15: Unauthorized people cannot change the reminder setting
Observable: A person who lacks billing administration authority receives a refusal when attempting to enable or disable reminders, and a billing operator observes the prior saved setting.
Source: implied: U-8 requires protection from unauthorized sends.

### C-16: A failed delivery attempt has a visible outcome
Observable: The billing operator can find the failed occurrence and distinguish its failure from a confirmed acceptance.
Source: implied: U-9 requires knowing whether an attempt was accepted.

### C-17: Capacity limits do not permanently omit invoices that remain eligible
Observable: A batch larger than available capacity can be processed across multiple opportunities while its invoices remain eligible.
Source: implied: U-10 requires work beyond one processing opportunity.

### C-18: Voided invoices are excluded
Observable: A previously issued invoice that is now voided produces zero new reminder submissions even if a positive historical balance remains visible.
Source: implied: U-11 removes the obligation to pay.

### C-19: An authorized operator can inspect reminder outcomes for their account
Observable: The operator locates an occurrence through its invoice and can see its outcome.
Source: implied: U-13 requires visibility into activity on the operator's account.

### C-20: The reminder feature permits return to the preceding billing release where one exists
Observable: After stopping reminders and returning to the preceding release, existing invoices and recorded payments remain available to the prior billing workflows.
Source: implied: U-12 requires a usable rollback.

### C-21: Reminder eligibility is assessed separately for each invoice
Observable: Two invoices for the same billing email qualify independently. Recording a payment against one invoice affects eligibility for that invoice only.
Source: implied: U-14 involves distinct outstanding obligations.

### C-22: Each automatic email concerns one invoice
Observable: Two eligible invoices for the same recipient produce distinct invoice-specific reminders. Each email gives the reference and amount for only its own invoice.
Source: choice: Per-invoice follow-up lets recipients match the message to the obligation it concerns.

### C-23: Current authoritative billing data governs eligibility
Observable: If a cached or previously observed record shows a positive balance but the current billing record shows it is fully paid, the current record suppresses the send.
Source: implied: U-4 requires reminders to reflect recorded payments.

### C-24: The reminder uses the invoice's current authorized billing email destination
Observable: With different billing and general contact addresses on file, the automation sends only to the email destination designated for that invoice by billing. For an invoice whose billing workflow designates a primary billing recipient and additional contacts, the automation uses the primary address only.
Source: choice: One designated destination provides follow-up while limiting exposure of invoice details.

### C-25: An invoice without a usable billing email is ineligible
Observable: An invoice with a blank, malformed, ambiguous, or unresolved billing email produces zero submissions.
Source: implied: U-2 and U-5 require a usable, authorized address.

### C-26: An invoice without a usable due date is ineligible
Observable: An invoice with a missing, unparseable, or noncalendar due date produces zero submissions.
Source: choice: The automation cannot safely infer that an invoice is overdue.

### C-27: An invoice without a reliable outstanding balance is ineligible
Observable: An invoice with a missing, unreadable, or otherwise unverified outstanding balance or currency produces zero submissions. The operator can distinguish unavailable balance data from a verified zero balance.
Source: implied: U-4 requires a reliable amount still owed.

### C-28: An invoice without its billing reference is ineligible
Observable: An invoice with a missing or unreadable reference produces zero submissions.
Source: implied: U-2 requires the recipient to identify the obligation.

### C-29: An invoice without an available billing action is ineligible
Observable: If the invoice has no existing payment instructions, authorized invoice or payment destination, or established billing contact, it produces zero submissions.
Source: choice: A reminder should give the recipient a usable next step without inventing payment details.

### C-30: Only currently issued, collectible obligations qualify
Observable: Draft or unissued, fully paid, zero- or negative-balance, voided, canceled, fully credited, written-off, explicitly collection-blocked, and deleted or otherwise withdrawn invoices produce zero submissions. A disputed, archived, refunded, or reopened invoice qualifies only if the billing workflow treats it as issued, payable now, and free of a collection block, with a verified positive balance. Unrecognized states with unconfirmed collectibility produce zero submissions.
Source: choice: The named categories define reminder eligibility by the billing outcome and leave product-specific state labels to the host.

### C-31: The invoice's billing calendar governs reminder dates
Observable: With a due date recorded as a date, the reminder calendar uses that date directly. If the host records a due instant instead, it uses the date containing that instant in the invoice's established billing zone. This is the zone the host uses for that invoice, inherited from the account when applicable. The calendar uses UTC if no established zone is available.
Source: choice: A billing calendar preserves the meaning of the due date, with a deterministic fallback when no calendar zone is recorded.

### C-32: Each occurrence is open for its scheduled civil date only
Observable: For an April 11 occurrence, a submission can start only at instants whose local calendar date in the billing zone is April 11. The first such instant is included and the first instant of April 12 is excluded. A 23- or 25-hour date constitutes one window. A skipped civil date has no eligible instants.
Source: choice: A calendar-day window allows recovery during that date while preventing stale catch-up.

### C-33: Overdue invoices are eligible only in open or future occurrences
Observable: Enabling on April 18 for an invoice due April 10 produces no catch-up for April 11 or 17. The April 24 occurrence can still send. Enabling April 25 produces zero reminders for that due date.
Source: choice: Activation does not trigger a backlog of stale reminders.

### C-34: The reminder shows the identity of the invoice issuer
Observable: The recipient can identify the billing party shown on the invoice from the sender identity or email content.
Source: implied: U-2 requires the recipient to recognize who is requesting payment.

### C-35: A reminder states the due date that made it eligible
Observable: A reminder for an invoice due April 10 communicates April 10 as the invoice due date, using a presentation that lets the recipient identify the date.
Source: choice: Including the deadline helps the recipient recognize the cause of follow-up.

### C-36: Reminder configuration consists of a single account-level on or off setting
Observable: An operator can read and change enabled or disabled. The feature provides no controls for offsets, templates, channels, arbitrary recipients, customer overrides, per-invoice scheduling, or sending an automatic occurrence on demand.
Source: choice: A reversible account switch suffices for the requested automation.

### C-37: Repeating the existing setting does not restart follow-up
Observable: Setting an already enabled account to enabled leaves it enabled without producing an extra send or clearing the invoice's accepted occurrences. Repeating disabled leaves the account disabled.
Source: implied: U-1 and U-6 change account authorization rather than initiating a send.

### C-38: A malformed setting change leaves the prior value intact
Observable: A change request that supplies neither enabled nor disabled, including a missing or unsupported value, is refused. The authorized operator can still read the prior value.
Source: choice: The available control has exactly two meaningful values.

### C-39: Reminder activity is private to authorized account users
Observable: A person with no permission to view the account's billing activity receives no reminder records, settings, destination data, or confirmation that another account's invoice exists when querying with its reference.
Source: implied: U-8 concerns private billing information.

### C-40: Reminder permissions follow the account's billing authority
Observable: Rights equivalent to managing account billing allow changing reminder settings. Rights that allow inspecting an invoice's billing activity allow inspecting that invoice's reminder activity. A read-only billing user with no billing administration authority cannot change the setting.
Source: choice: Reuse the host's account permissions where present. In a host without delegated billing roles, the account operator holds both permissions.

### C-41: An open occurrence can qualify once its invoice data is corrected
Observable: Correcting a missing billing email during an open occurrence allows that occurrence to be considered again. A correction after expiry does not revive it.
Source: choice: Allow safe recovery while the originally scheduled follow-up is still timely.

### C-42: The feature does not infer scope from a customer's other invoices or contact records
Observable: A reminder for invoice A includes no data from other invoices, no payment method credentials, and no unrelated customer data, even when the issuer and recipient are shared.
Source: implied: U-14 exposes only the billing information needed for the individual obligation.

### C-43: The first handoff begins only while the invoice is eligible
Observable: If a full payment, withdrawal, collection block, account disable, window expiry, or loss of required invoice data takes effect before the email submission starts, the email service receives zero submissions for that occurrence while that condition holds. Preparing an email earlier does not authorize a later handoff.
Source: implied: U-4, U-5, U-6, and U-11 can occur while a send is pending.

### C-44: Each handoff uses the invoice data current when submission starts
Observable: If a partial payment, due date correction, destination change, reference correction, payment instruction change, or billing calendar change takes effect before submission starts, the attempt reflects the change or is suppressed if the changed invoice no longer qualifies.
Source: implied: U-4 and U-5 can occur between evaluation and submission.

### C-45: A change after submission starts applies to future handoffs
Observable: A provider can accept or deliver an email whose submission began before a payment, withdrawal, correction, disable, or expiry. The existing attempt retains the outcome reported by the provider. The change governs every submission that starts afterward.
Source: implied: U-9 observes outcomes that can arrive after U-4, U-5, U-6, or U-11.

### C-46: Every retry is subject to the same submission eligibility as an initial attempt
Observable: A retry waits after a temporary rejection. If the invoice is paid or withdrawn, the account is disabled, the window expires, or required data becomes unusable before the retry starts, the service receives zero further submissions while that condition holds.
Source: implied: U-4, U-6, U-9, and U-11 apply to every automatic send.

### C-47: One occurrence can have at most one accepted email submission
Observable: Overlapping processing, repeated triggers, late completion reports, and restarts cannot produce two accepted submissions for the same account, invoice, and schedule offset.
Source: choice: A scheduled follow-up represents one intended recipient message.

### C-48: The invoice's current due date controls every unconsumed offset
Observable: If the due date changes from April 10 to April 20 before any acceptance, the active occurrence dates become April 21, April 27, and May 4. Submissions for the former dates cease when the new due date takes effect.
Source: choice: Follow-up should track the corrected deadline.

### C-49: An accepted offset stays consumed for the lifetime of the invoice
Observable: After the 1-day reminder is accepted, editing the due date or billing zone, disabling then re-enabling, correcting the recipient, reopening, refunding, or restoring the same invoice produces zero additional 1-day reminders for that invoice.
Source: choice: A billing edit or temporary stop should not generate duplicate follow-up.

### C-50: Reopening an invoice permits only genuinely outstanding follow-up
Observable: If a payment is reversed or a credit is removed, the same invoice can qualify again once it is issued, collectible, and positive. It can use an open or future offset that has no accepted or unresolved submission, subject to its attempt limit.
Source: choice: A debt can become payable again while earlier follow-up remains part of its history.

### C-51: Concurrent setting changes have one effective order
Observable: When authorized enable and disable changes overlap, the effective setting is the value from the last committed change.
Source: choice: Overlapping administrative changes require one authoritative outcome.

### C-52: A failed setting update leaves the prior setting effective
Observable: When the service confirms it rejected the update, reading the setting shows the previous value unless an independent authorized change has taken effect.
Source: implied: U-1 and U-6 require knowing whether a setting took effect.

### C-53: A temporary failure confirmed to have occurred before acceptance is retryable
Observable: A confirmed temporary failure that rules out acceptance is retried automatically if the occurrence remains eligible after its required wait, has an attempt left, and has enough open time and capacity for another submission. Examples are a temporary rejection, a throttling refusal, and a temporary connectivity failure known to have prevented provider acceptance.
Source: choice: Automatic recovery is appropriate when there is evidence the previous attempt could not deliver.

### C-54: A temporary rejection imposes a minimum retry delay of 15 minutes
Observable: If a failure becomes known to be temporary and pre-acceptance at 10:00, no retry begins before 10:15, measured in elapsed time. For a delayed report, the wait is measured from when the result becomes known.
Source: choice: A 15-minute floor gives a transient failure time to clear and defers to a longer delivery-service wait.

### C-55: An invoice offset permits at most three submission attempts
Observable: Repeated retryable failures produce at most one initial submission attempt and two retries per invoice offset. Restarts, toggles, and invoice data changes do not clear the count. Eligibility checks that stop before an attempt do not consume the limit.
Source: choice: A finite retry budget prevents an ongoing failure from producing unbounded traffic.

### C-56: A permanent rejection terminates attempts for that occurrence under the rejected delivery facts
Observable: A definitive permanent rejection for an unusable destination or unpermitted sender produces zero retries for the same destination or sender respectively. If the rejected destination or sender is corrected before expiry, a remaining attempt can be used. Any other definitive permanent rejection closes attempts for the offset.
Source: choice: Retrying an unchanged permanent error cannot deliver the reminder, while a correction can remove an identified cause.

### C-57: An unresolved delivery result blocks further submissions for the same occurrence
Observable: If a timeout, interrupted response, or restart leaves acceptance unknown, subsequent processing sends zero further submissions for the same invoice offset until evidence confirms that the prior attempt was not accepted.
Source: choice: An extra copy is avoidable when acceptance cannot be ruled out.

### C-58: Acceptance evidence updates the original occurrence
Observable: A delayed delivery-service confirmation after expiry, restart, due date change, or disable changes the original occurrence’s observed result to accepted without a new send.
Source: implied: U-9 and U-13 require accurate accounting for the same action despite late or duplicate reports.

### C-59: An unresolved attempt is reported as unconfirmed after its occurrence expires
Observable: If there is still no authoritative result when its window closes, the operator sees that acceptance remains unconfirmed after expiry. If evidence later arrives, the record shows the confirmed outcome. Expiry alone releases no retry for that attempt.
Source: choice: The operator needs a closed scheduling window to be distinguishable from a proven failure.

### C-60: A later offset can proceed while a different expired offset remains unconfirmed
Observable: An attempt started April 11 remains unconfirmed on April 17. If the invoice is still eligible, the April 17 occurrence can be submitted within its own window.
Source: choice: An unresolved earlier outcome does not prevent later scheduled follow-up for a debt that remains unpaid.

### C-61: A delivery bounce does not reissue an accepted occurrence
Observable: If a provider accepts a reminder and later reports a bounce, the automation initiates zero replacement submissions for that offset.
Source: choice: Provider acceptance consumed the scheduled occurrence and a bounce needs billing or delivery correction.

### C-62: Delivery outcomes distinguish submission acceptance from delivery confirmation
Observable: An accepted submission without a delivery report is shown as accepted with delivery unconfirmed. When authoritative confirmation of delivery or a bounce is available, the operator can tell which occurred. No view asserts that a person opened or read the email.
Source: implied: U-13 asks what was sent and what evidence exists that it reached its destination.

### C-63: Reminder observation exposes the invoice occurrence and its disposition
Observable: For an occurrence the account may inspect, the operator can see its invoice reference, schedule offset, due date used, billing zone, scheduled date, disposition, and reason when applicable. The operator can also see the number of submission attempts and each attempt’s start time, submitted destination, submitted amount and currency, and known submission and delivery outcomes. Fields for a submission that never occurred have no value.
Source: choice: These facts let billing explain a send or a failure without exposing email bodies or provider internals.

### C-64: Reminder history distinguishes the occurrence's disposition
Observable: The operator can tell the applicable disposition among awaiting evaluation, eligible but deferred, skipped for ineligibility, awaiting submission result, pending retry, submission result unknown, expired with no acceptance, expired with acceptance unconfirmed, superseded, permanently rejected, confirmed failure with retryability unknown, retry budget exhausted, and accepted.
Source: choice: Billing needs to distinguish work that can still run, work that cannot run, and work whose result remains unknown.

### C-65: An occurrence that could not be processed before its deadline is observable as expired
Observable: Capacity or dependency failure prevents work on April 11 until April 12. The operator can determine that the April 11 occurrence expired without a submission. No April 11 submission starts on April 12.
Source: implied: U-10 requires an explanation of eligible work missed during an outage or at capacity.

### C-66: Temporary inability to evaluate an invoice does not authorize a send
Observable: If the billing record or effective account setting cannot be read when a submission is about to start, zero submissions start on the strength of stale data.
Source: implied: U-4, U-6, and U-9 require current eligibility even during a failure.

### C-67: An outage does not require a new operator action when service recovers
Observable: After scheduling, billing, or delivery service recovers, eligible work resumes while reminders remain enabled. Closed windows stay closed and previous acceptance, uncertainty, and attempts still count.
Source: implied: U-9 requires eligible automatic recovery.

### C-68: Clearing a scheduling backlog does not indefinitely bypass otherwise eligible invoices
Observable: If capacity becomes available repeatedly while several invoices remain eligible, repeatedly encountering the same invoice cannot prevent the others from getting an opportunity while there is sufficient capacity for all of them. This applies across invoices within an account and across enabled accounts.
Source: choice: The user relies on eligible invoices getting a chance, without requiring a fixed processing order.

### C-69: An earlier unsent occurrence may expire without blocking later occurrences
Observable: If the April 11 occurrence was skipped, deferred, definitively rejected, or otherwise left without acceptance, the April 17 occurrence can still send if the invoice then qualifies.
Source: choice: Later scheduled follow-up is useful even if an earlier scheduled email did not go out.

### C-70: A pre-expiry disable does not forfeit an otherwise open occurrence
Observable: Disabling reminders before an outstanding occurrence has sent blocks attempts while disabled. Re-enabling on the same scheduled date allows an otherwise eligible occurrence to proceed within its remaining attempt budget.
Source: choice: A reversible pause respects availability within the already authorized window.

### C-71: Repeated or out-of-order delivery reports do not erase known outcomes
Observable: After a confirmed delivery or bounce, an older pending report does not regress delivery status. A repeated copy of an acceptance continues to show one acceptance and adds zero attempts.
Source: implied: U-9 and U-13 require a record that tracks provider facts even when notifications arrive out of order.

### C-72: Reminder submission waits for an authorized production delivery environment
Observable: An enabled account sends zero customer emails when the release lacks a production-authorized email service or sender identity. The service, exact sender validation rules, and credential lifetime are unconfirmed.
Source: choice: The email service's production access and sender authorization bind which messages it will accept once selected.

### C-73: A nonproduction deployment sends reminders only to approved test destinations
Observable: Running the schedule in a testing or sandbox deployment with a live customer address produces zero email to that address. A permitted test destination can exercise the flow when the environment permits delivery. The provider's sandbox destination and volume limits are unconfirmed.
Source: choice: Nonproduction exercises should avoid external billing contact. Any sandbox restrictions imposed by the selected email service further restrict test delivery.

### C-74: Automatic sends stay within the delivery service's enforced capacity
Observable: If the service reports a rate, concurrency, or daily volume limit, the automation defers eligible work when capacity is unavailable. No particular throughput, daily quota, or concurrency count is promised. Exact rate, volume, and concurrency limits are unconfirmed.
Source: choice: The selected email service's throttling and quota rules bound processing capacity.

### C-75: An oversized reminder is never submitted as a truncated billing notice
Observable: If a message cannot fit within the email service's address or message-size restrictions while retaining its required information, the operator sees a validation or delivery error. The recipient receives zero truncated reminders. Exact provider address-length and message-size limits are unconfirmed.
Source: choice: The selected email service's address and payload limits constrain what it can accept.

### C-76: Automatic reminders survive the end of an interactive billing session
Observable: The operator can close their browser and sign out after enabling. A qualifying reminder still runs when background execution is available. The scheduling platform, maximum execution duration, minimum activation interval, trigger precision, and concurrency limits are unconfirmed.
Source: implied: U-1 and U-2 require unattended execution. No execution platform has been supplied.

### C-77: A platform deadline without a definitive submission result leaves acceptance unknown
Observable: If execution is cut off after submission may have started, the observable outcome is unknown until verified, even when the runtime reports a timeout. Exact execution and delivery response timeout figures are unconfirmed.
Source: choice: A runtime termination deadline and an email service response deadline both limit how long the system can wait for a synchronous result. Neither establishes whether the service accepted an in-flight submission.

### C-78: A provider's delivery observability bounds what the operator can verify
Observable: If the delivery service supplies no delivery or bounce evidence, the operator sees the acceptance result and the absence of delivery confirmation. Exact confirmation availability, reporting delay, and provider history retention are unconfirmed.
Source: choice: The selected email service's outcome reporting determines which delivery facts the application can verify.

### C-79: Confirmed deployment policy restrictions block reminder activation
Observable: If production billing email is barred for the account or deployment by a confirmed host policy, the operator can see that activation is unavailable and no reminder is sent there. The deployment jurisdiction, release approval rules, and provider terms are unconfirmed.
Source: choice: Any confirmed production authorization rule governs whether the release can send.

### C-80: The automation imposes no additional invoice-count cutoff
Observable: An invoice qualifies by the same rules whether it is 1st or 10,001st in the account's billing records. The host's maximum invoice count and per-run capacity are unconfirmed.
Source: choice: Scale may change throughput without changing which invoices qualify.

### C-81: Enabling reminders does not change how an invoice is issued
Observable: Given an existing billing workflow that issues invoices, its normal issuance action still creates the same issued invoice with reminders enabled or disabled. Enabling reminders alone issues zero invoices.
Source: implied: U-1 automates follow-up for invoices established by the billing workflow.

### C-82: Reminder activity does not alter an invoice's billing dates
Observable: Comparing the recorded issue and due dates before and after an automatic reminder shows the same values unless an authorized billing action changed them.
Source: implied: U-5 changes invoice dates through billing, while U-2 uses those dates.

### C-83: Reminder activity does not alter invoice lifecycle status
Observable: An invoice retains its billing status when a reminder is scheduled, submitted, accepted, or bounced. Issuance, payment, collection holds, cancellation, voiding, and other lifecycle transitions remain under the host billing workflow where supported.
Source: implied: U-2 and U-11 make reminder eligibility depend on the invoice state.

### C-84: Reminder activity does not alter invoice amounts
Observable: A reminder leaves the invoice's recorded total, currency, outstanding amount, and any existing fees or credits the same unless the billing workflow independently changes them.
Source: implied: U-4 makes the reminder report the balance under the existing billing rules.

### C-85: Payment recording continues independently of reminder availability
Observable: The same valid full or partial payment is recorded and applied by the billing workflow whether reminders are enabled, disabled, processing, or experiencing a delivery failure.
Source: implied: U-4 depends on billing remaining able to record payments.

### C-86: Existing invoice-recipient maintenance keeps its billing effect
Observable: Changing an invoice's billing destination through an authorized existing billing action still changes the recorded designation with reminders enabled or disabled. A scheduled reminder changes zero address records.
Source: implied: U-5 uses the billing workflow to correct recipients.

### C-87: Existing billing communications remain under their existing triggers
Observable: Where the host sends original invoices, receipts, or manual messages, those communications retain their trigger and destination policy with reminders enabled or disabled.
Source: implied: U-1 requests a new automatic trigger for reminders without replacing existing billing communication.

### C-88: Reminder delivery respects the host's existing billing contact restrictions
Observable: If the host already blocks billing email to a destination or for an account, a reminder generates zero submissions there while the restriction is active. Applicable host restrictions and their values are unconfirmed.
Source: implied: U-8 and U-2 require authorization to communicate the invoice.

### C-89: A reminder provides no additional permission to read the invoice or change payment data
Observable: Opening a reminder link grants only the access allowed by the host's existing invoice-view or payment flow. Someone who lacks the access required by that flow receives no additional invoice details or payment privileges.
Source: implied: U-8 requires the invoice's existing access protections to hold through reminders.

### C-90: Scheduled work running under an earlier release cannot send after the stop takes effect
Observable: A rollback operator stops reminders before switching releases. Previously scheduled or prepared work starts zero new handoffs after the stop while it remains effective, including work encountered by an older release.
Source: implied: U-12 requires the rollback to take reminders out of service.

### C-91: Rollback preserves the account's disabled setting
Observable: An account whose setting was disabled before rollback still shows disabled when the reminder feature is restored.
Source: choice: Restoring the release should preserve the operator's last send authorization.

### C-92: Rollback preserves the occurrence facts that prevent duplicate follow-up
Observable: After restoration and explicit re-enabling, accepted offsets remain consumed, unresolved submissions remain blocked, and the recorded attempt count still applies to each offset.
Source: implied: U-12 requires safe restoration without forgetting prior sends.

### C-93: Reminder history follows the invoice's existing visibility lifetime
Observable: Invoice activity remains available through the authorized billing history while the invoice remains inspectable under the host's existing retention and access policy. After an invoice is permanently deleted under that policy, its private reminder details are no longer obtainable through reminder activity. The host's exact invoice retention period is unconfirmed.
Source: choice: Reminder history should have the same visibility lifetime as its source obligation.

### C-94: An unrecordable send outcome does not cause a second submission
Observable: When the provider accepts a submission but the application cannot immediately make that outcome visible, the same offset produces zero new submissions while its outcome is unresolved. Recovery records acceptance against the original attempt when confirmed.
Source: implied: U-9 must avoid a duplicate if only the observation step failed.

### C-95: An untrustworthy delivery report cannot change an occurrence
Observable: A report for another account, invoice, offset, or attempt, or a report that the selected provider cannot authenticate, does not change the target occurrence. A verifiable report changes only the corresponding attempt.
Source: implied: U-8 and U-13 require accurate account-scoped outcomes.

### C-96: An automatic reminder does not take a payment or start any collection action
Observable: Sending, skipping, or exhausting reminders triggers zero charges, late fees, write-offs, transfers to collections, or other automatic changes to the invoice obligation.
Source: implied: The request asks to remind the payer about unpaid invoices.

### C-97: Reminder activity does not expose unnecessary delivery content
Observable: The authorized activity view exposes the occurrence and outcome facts without returning full email bodies, credentials, raw provider responses, or unrelated customer data. An error shown to the operator contains only account-appropriate information.
Source: choice: The facts in the activity record suffice for diagnosing the send.

### C-98: A billing operator can observe reminder ineligibility even without a calculable occurrence
Observable: An existing invoice with no usable due date shows the invoice-level reason no reminder can be scheduled even though it has no scheduled date to look up. Correcting the due date removes that current reason.
Source: choice: Billing should be able to diagnose unschedulable invoices without inventing occurrence dates.

### C-99: An invoice without a usable issuer identity is ineligible
Observable: An invoice whose billing data cannot provide an identifiable issuer produces zero reminder submissions.
Source: implied: U-2 requires the recipient to recognize who is requesting payment.

### C-100: An operator authorized to view account billing can read its reminder setting
Observable: An authorized read-only billing operator can see whether reminders are enabled. An otherwise identical account user with no billing-view permission cannot obtain that setting.
Source: choice: Billing readers need to explain reminder activity without being able to authorize sends.

### C-101: Authorization is evaluated when the settings action takes effect
Observable: If an operator loses billing administration authority before an outstanding setting update takes effect, that update is refused and does not change the setting.
Source: implied: U-8 applies at the time an external send authorization would be changed.

### C-102: An operator can read the effective setting after an ambiguous update response
Observable: After an update times out with an unknown result, a successful settings read returns the effective value, whether the update took effect or the prior value still applies.
Source: implied: U-1 and U-6 require knowing the current authorization after a lost response.

### C-103: A nonexistent or unavailable account cannot authorize a submission
Observable: Removing or closing an account, or blocking its authority to send billing email, suppresses subsequent reminder submissions for its invoices even if the last saved setting was enabled.
Source: implied: U-1 authorizes sending on behalf of an active billing account.

### C-104: An invoice message submitted to the delivery service targets exactly one authorized address
Observable: The submitted message has one billing destination, zero CC recipients, and zero BCC recipients. If billing supplies multiple candidate addresses with no single designated primary, the invoice is skipped for an ambiguous destination.
Source: choice: The recipient limit avoids disclosing an invoice to additional recipients without a clear billing designation.

### C-105: A required provider retry time governs subsequent attempts
Observable: A temporary rejection with a provider-imposed retry time of 10:30 results in zero retry submissions before 10:30, even if the 15-minute product delay ends at 10:15.
Source: choice: The delivery service's rate or availability restriction can require a longer wait than the automatic retry schedule.

### C-106: Confirmed nonacceptance resolves an unknown submission
Observable: An unknown attempt becomes a confirmed failure when the delivery service verifies that it did not accept the submission. A verified temporary failure can allow another attempt only if the offset is open, the invoice remains eligible, the wait has elapsed, and its attempt budget has not been spent.
Source: choice: A verified result can safely release the uncertainty block.

### C-107: Different offsets cannot begin recipient follow-up less than 24 elapsed hours apart while the earlier attempt might have delivered
Observable: Following a 1-day attempt at 10:00 that was accepted or remains unresolved, a due date edit that makes the 7-day offset open cannot cause its submission before 10:00 plus 24 elapsed hours. If authoritative evidence establishes the 1-day attempt was never accepted, this spacing rule no longer applies to that attempt.
Source: choice: A deadline correction should not place successive scheduled emails in the same 24-hour period.

### C-108: Superseded schedule dates with activity remain explainable
Observable: If a due date or billing zone change moves an offset after an evaluation or an attempt was recorded, the earlier schedule date remains visible with its known disposition or superseded reason. The current schedule shows the new date for an unconsumed offset.
Source: choice: An operator should be able to explain activity tied to prior invoice dates without treating those dates as active work.

### C-109: An invoice receives at most three accepted automatic reminders in its lifetime
Observable: Even after changes to the due date, destination, account setting, or collectible state, the number of accepted automatic reminders for the same invoice does not exceed three.
Source: choice: Each of the three scheduled offsets can be accepted at most once per invoice.

### C-110: Manual billing emails do not consume automatic reminder occurrences
Observable: A manually sent billing email for an outstanding invoice leaves its automatic occurrence available to qualify under the automatic schedule.
Source: choice: Existing mail actions remain independent of automatic follow-up.

### C-111: The operator can distinguish unobserved outage conditions from confirmed ineligibility
Observable: When activity service returns after an outage, an occurrence whose window elapsed with zero submissions and whose invoice and schedule can be identified is visible as expired. If the system cannot establish whether it was eligible during the outage, the operator sees that eligibility at the time is unknown.
Source: choice: Recovery should explain missing activity using only available evidence.

### C-112: Temporary contact-data correction cannot bypass an existing billing contact restriction
Observable: Correcting a destination just before a retry or later occurrence still yields zero submissions if the corrected destination is restricted by the account's existing billing policy.
Source: implied: U-5 and U-8 apply to all automatic submissions for a corrected invoice.

### C-113: Reminder activity uses the current permissions of the viewer
Observable: An operator permitted to see an occurrence yesterday but barred from the invoice today cannot obtain that occurrence today, even by using a previously saved reference.
Source: implied: U-8 requires ongoing privacy for account and invoice activity.

### C-114: Authoritative contradictory delivery evidence is visible as uncertain until resolved
Observable: When authenticated reports for the same attempt make incompatible claims and the provider gives no way to establish which is authoritative, the operator sees a conflicting outcome for the affected fact. If the conflict concerns delivery, the submission result remains separately visible.
Source: choice: A conflict is insufficient evidence that another email would be safe.

### C-115: The attempt count begins at submission
Observable: When billing facts or sending capacity were unavailable before a submission attempt began, recovering them leaves the attempt count unchanged. Once an attempt to submit begins, its count remains even if the service confirms that it accepted nothing.
Source: choice: The attempt budget counts actual submissions initiated toward delivery.

### C-116: An invoice's restored identity keeps its history
Observable: Restoring a withdrawn or recoverably deleted invoice restores its accepted offsets, attempt counts, and unresolved submission facts. Creating a distinct invoice gives it independent offsets even if the recipient, reference displayed to the payer, balance, and due date all match another invoice.
Source: choice: Follow-up history belongs to the obligation's existing billing identity.

### C-117: A delivery-service outage does not turn off the saved setting
Observable: An enabled account remains enabled after a delivery outage. Once the outage ends, that saved setting still governs automatic work.
Source: implied: U-9 requires recovery without a new enable action.

### C-118: A continuously eligible occurrence receives a submission attempt during its scheduled date
Observable: With the invoice eligible for the entire scheduled date, the background service available throughout that date, the necessary delivery authorization in place, and no capacity restriction, the email service receives a submission attempt on that date without any manual action.
Source: choice: A scheduled calendar date is the observable timing promise under normal operating conditions.

### C-119: A release operator verifies that sending has stopped for the rollback scope
Observable: Before returning to a previous release that has no reminder control, an authorized release operator can verify that new reminder submissions are disabled for every account served by the affected deployment. Accounts outside the rollback scope remain under their own effective authorization.
Source: implied: U-12 applies to every account served by the release being rolled back.

### C-120: The provider's accepted submission is the event counted toward the occurrence
Observable: When the service confirms that it accepted an email for delivery, the operator sees the offset as consumed even if the recipient has received zero email so far.
Source: choice: Acceptance is the first confirmed point at which repeating the submission can produce a duplicate.

### C-121: A recorded acceptance remains consumed during a conflicting report
Observable: If a subsequent authenticated report contradicts a confirmed acceptance for the same attempt, the conflict is visible and new attempts for that offset remain blocked. A conflicting or older message does not count as evidence of nonacceptance for retry.
Source: choice: A later contradiction is insufficient to safely undo a confirmed handoff.

### C-122: A definitive permanent failure for an invoice destination suppresses later reminders to that same destination
Observable: After a provider confirms that an address is permanently undeliverable, that invoice makes zero later submissions to the same address unless the provider establishes that the destination can accept delivery again. This result applies only to the affected invoice and address.
Source: choice: Reusing an address known to be undeliverable cannot provide useful follow-up.

### C-123: A production delivery block leaves the billing invoice usable
Observable: If sender or delivery authorization is unavailable, issuing, viewing, amending, and paying an invoice continue through the existing billing workflow wherever those actions are supported.
Source: implied: U-9 concerns email failure, while U-4, U-5, and U-11 still use billing independently.

### C-124: The account setting and current operational availability can be distinguished
Observable: An authorized billing operator can distinguish disabled from enabled with sending unavailable because execution is paused, a required service is unavailable, or the environment or sender lacks delivery authorization. When availability cannot be established, the operator can see that it is unknown.
Source: choice: Saved authorization and current ability to send answer different operator questions.

### C-125: Stopping a deployment for rollback is independent of changing account preferences
Observable: If an authorized release operator stops the deployment's reminder execution without editing the account setting, sending stops while the release is stopped. Reading an enabled account still shows enabled with sending unavailable during that stop.
Source: choice: A release stop can protect accounts without changing their billing preferences.

### C-126: Restoring a release preserves its operational stop until sending is explicitly resumed
Observable: After restoring a release that was stopped for rollback, new submissions stay blocked for that deployment, including for enabled accounts, until an authorized release operator explicitly resumes sending.
Source: choice: Software restoration alone should not restart external communication.

### C-127: Reminder history explains the known reason for a disposition
Observable: Reason details cover an account disabled, unavailable, or barred from billing email, an unissued or noncollectible invoice, a verified nonpositive balance, unusable due date, amount or currency, reference, issuer identity, destination or billing action, a host contact restriction, a destination known to be undeliverable, capacity or throttling, spacing from an earlier offset, execution paused, dependency or authorized sender unavailable, superseded schedule dates, prior unknown acceptance, failure classification, unsupported calendar range, or a closed window. When a reason is unavailable, the operator sees that it is unknown.
Source: choice: A disposition needs an explanation when it alone does not tell billing why the occurrence changed.

### C-128: An unrecognized failure does not count as confirmed retryable
Observable: If the service confirms nonacceptance but cannot indicate whether the error is temporary or permanent, the operator sees a confirmed failure with retryability unknown. No retry starts until the failure has a confirmed temporary or correctable classification.
Source: choice: A failed submission should be retried only under a defined recovery rule.

### C-129: Definitive nonacceptance for one attempt never clears an unresolved result for another
Observable: If a report for the first attempt arrives while a later attempt for the same offset has an unknown result, the later attempt remains unresolved. It cannot be retried on the strength of the older attempt's result.
Source: choice: Proof that one attempt failed gives no evidence about another attempt.

### C-130: Nonproduction reminder delivery uses test invoice data
Observable: An approved test destination can receive a reminder generated from a test invoice. Running the rehearsal against a live customer invoice produces zero test emails containing that invoice's private billing data.
Source: choice: Testing can verify the delivery path without disclosing live invoice data.

### C-131: An occurrence exists only for a calculable date within the host calendar's supported range
Observable: If adding a schedule offset to a due date would exceed the host calendar's supported date range, that offset cannot send and the operator sees the calendar-range reason. The exact host date range is unconfirmed.
Source: choice: An offset outside the host calendar's domain cannot define a real submission window.

### C-132: At most one submission per invoice offset can await an initial provider result at a time
Observable: While the first submission call is still awaiting a result, simultaneous processing of the same offset starts zero other submission calls. During that interval the operator can distinguish the pending call from an outcome already classified as accepted, rejected, or unknown.
Source: choice: Parallel calls for the same follow-up can create two accepted emails before either result is known.

### C-133: The attempt history distinguishes the full lifecycle of submission and delivery
Observable: An attempt's submission result is awaiting response, accepted, confirmed temporary failure, confirmed permanent rejection, confirmed failure with retryability unknown, acceptance unknown, or conflicting. For an accepted attempt the delivery outcome is unconfirmed, confirmed delivered, bounced with the provider's known temporary or permanent classification, or conflicting. If the provider gives no bounce classification, the bounce is visible with its classification unknown.
Source: choice: Submission and post-acceptance delivery have different effects on eligibility and are independently observable.

### C-134: The submission attempt limit for one invoice is nine
Observable: After three attempts against each of the three offsets, the invoice can produce zero further automatic submission attempts, including after a due date edit or restored release.
Source: choice: Three offsets with at most three attempts each bound both expected and failed follow-up for the invoice.
