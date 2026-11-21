## Use cases

### U-1: A billing operator enables reminders to follow up automatically on unpaid invoices
Flow: The operator reviews the reminder policy, enables it for their billing workspace, then sees whether automatic reminders are active. A user without billing-management permission is refused. If live prerequisites are unavailable, the operator sees why enabling failed.
Source: implied: “Set up automatic reminders” requires a way to activate the feature.

### U-2: A customer receives a reminder to identify an overdue invoice they still owe
Flow: An issued invoice passes its due date with a positive balance. Automatic processing checks the invoice and sends an email to its billing recipient. The recipient can identify the invoice and see the outstanding amount. A subsequent evaluation of the same invoice leaves the accepted reminder alone.
Source: request

### U-3: A customer pays an invoice to clear the amount owed
Flow: The billing system records payment through its existing flow. At the next reminder evaluation, a fully paid invoice is skipped. A partially paid invoice can still receive a reminder for its remaining balance.
Source: implied: “unpaid invoices” requires distinguishing a remaining debt from a settled invoice.

### U-4: A billing operator checks a quiet workspace to see whether automatic processing is working
Flow: The operator checks reminder status after an evaluation with zero eligible invoices. No customer receives a reminder, and the operator can see that the evaluation finished.
Source: implied: U-1 can be enabled before any invoice is eligible.

### U-5: A billing operator handles a large set of overdue invoices to keep follow-up moving
Flow: Automatic processing takes up invoices across a backlog, including invoices created before activation. If time or a service limit interrupts processing, outstanding work stays visible and resumes through later evaluations.
Source: implied: “unpaid invoices” can refer to more invoices than can be handled at once.

### U-6: A billing operator corrects invoice data to let eligible reminders proceed
Flow: When a required due date or billing address is missing or invalid, the operator sees the affected invoice and the reason. The operator corrects the record through the existing billing flow and automatic processing reevaluates it.
Source: implied: U-2 depends on a due date and a usable destination.

### U-7: A billing operator investigates delivery trouble to recover outstanding reminders
Flow: The operator sees whether an attempt was rejected, deferred, accepted, or left uncertain. Confirmed temporary failures are retried automatically while eligible. An uncertain attempt stays on hold until its outcome can be established. The operator can see which attempt needs investigation. A bounce after acceptance is visible when reported.
Source: implied: U-2 depends on a delivery service that can fail.

### U-8: A billing operator pauses reminders to stop new email submissions
Flow: The operator disables automatic reminders and sees the new state. A submission already in progress can still complete. An authorized operator can enable reminders again, at which point eligible unsent invoices reenter automatic processing.
Source: implied: U-1 is a continuing action that may need to be stopped.

### U-9: A billing operator inspects a reminder to answer a customer question
Flow: The operator opens the invoice’s reminder history, sees the recorded outcome and time, and can distinguish delivery-service acceptance from confirmed delivery where the latter is reported. A user without access to the invoice is refused.
Source: implied: U-2 creates customer-facing activity that operators may need to investigate.

### U-10: A release operator rolls back the feature to restore the prior billing version
Flow: The operator stops new reminder submissions before returning to the prior version. Existing invoices remain usable. If the feature returns later, previous accepted reminders still suppress repeats.
Source: implied: U-1 introduces an automated side effect that may outlive a deployment.

### U-11: A release operator verifies production readiness to launch live reminders
Flow: The operator checks whether background evaluations can run without a user session and whether the configured sender can submit live email. A sandbox sender or unavailable schedule leaves the deployment visibly unready. The operator can exercise a nonproduction copy without contacting its live customers.
Source: implied: U-1 requires background processing and U-2 requires live delivery for the feature to work in production.

### U-12: A billing operator continues ordinary billing work while reminders run
Flow: The operator issues an invoice, records a correction or accesses any existing manual send action using the billing product's existing permissions. Reminder activity is visible separately from those business events. An operator from another workspace cannot view or act on that invoice's reminder.
Source: implied: The requested follow-up extends the existing invoice lifecycle.

## Clauses

### C-1: After activation, eligible unpaid invoices trigger reminders automatically
Observable: An eligible invoice exists while reminders are active. Its reminder is submitted without an operator initiating the individual send.
Source: request

### C-2: Eligibility requires a positive outstanding balance
Observable: An invoice with an outstanding balance of zero or less generates no automatic reminder.
Source: implied: “unpaid invoices” excludes settled invoices.

### C-3: An authorized billing operator can enable automatic reminders for their workspace
Observable: The operator enables reminders for a workspace they manage and sees an active state there.
Source: choice: Workspace-level activation gives the billing team control at the level at which it manages invoices.

### C-4: Automatic reminders start disabled
Observable: A workspace without a saved reminder setting shows reminders disabled and submits no automatic reminder.
Source: choice: Customer-facing email begins after the billing team opts in.

### C-5: Changing activation requires billing-management permission
Observable: A user without that permission attempts to enable or disable reminders and receives a refusal.
Source: implied: U-1 and U-8 place control of customer-facing email with the billing operator.

### C-6: Activation with unavailable live email is refused
Observable: In a disabled workspace, the operator attempts activation while live email is known unavailable. Reminders stay disabled.
Source: choice: Activation should indicate readiness to submit real reminders.

### C-7: A refused activation exposes its reason to the operator
Observable: After activation is refused, the operator can identify which launch prerequisite prevented activation.
Source: implied: U-1 requires the operator to tell whether activation succeeded and resolve a refusal.

### C-8: Reminders are sent by email
Observable: An eligible invoice produces a reminder submitted to its billing email destination.
Source: choice: Email gives the customer an asynchronous reminder using billing contact information.

### C-9: An invoice becomes eligible for timing purposes after its due date ends
Observable: An invoice due June 10 fails the timing check through the end of June 10 and passes it starting June 11 in the effective billing time zone.
Source: choice: An overdue-only policy allows the full due date for payment.

### C-10: A reminder identifies its invoice
Observable: The customer can match the reminder to the invoice using a customer-visible invoice reference.
Source: implied: U-2 requires the customer to identify what they owe.

### C-11: A reminder states the outstanding amount
Observable: An invoice originally for 100 USD with 25 USD paid yields a reminder stating 75 USD outstanding when the remainder is still owed at submission.
Source: choice: The current amount gives the customer enough information to act on the reminder.

### C-12: Automatic reminders are limited to one accepted reminder per invoice
Observable: After a reminder for an invoice is accepted by the delivery service, subsequent evaluations produce zero additional automatic submissions for that invoice.
Source: choice: A single automatic follow-up meets the request without introducing a repeated-contact cadence.

### C-13: A completed evaluation with no eligible invoices is visible to the operator
Observable: The operator can identify the latest completed evaluation even when it found zero eligible invoices.
Source: choice: Operators need to distinguish a quiet cycle from stalled processing.

### C-14: Preexisting invoices can qualify after activation
Observable: An invoice issued before activation that satisfies the current eligibility rules can receive its automatic reminder after activation.
Source: implied: “unpaid invoices” includes qualifying invoices already outstanding.

### C-15: Interrupted backlog processing preserves outstanding work
Observable: Processing stops at an operational limit. After capacity returns, eligible unsent invoices remain available for automatic processing.
Source: implied: U-5 includes unpaid invoices beyond the first set that fits.

### C-16: A missing or invalid due date prevents automatic submission for that invoice
Observable: An invoice without a usable due date generates zero automatic submissions.
Source: choice: Automatic processing needs a reliable deadline for applying the overdue policy.

### C-17: A missing or invalid billing email prevents automatic submission for that invoice
Observable: An invoice without a usable billing recipient generates zero automatic submissions.
Source: implied: U-2 requires a destination belonging to the invoice.

### C-18: An operator can see the blocking reason for an invoice with missing or invalid reminder inputs
Observable: A billing operator views an affected invoice and can tell which reminder input needs correction.
Source: choice: The operator needs a way to distinguish and repair a block.

### C-19: Automatic processing reevaluates invoices after their blocking data is corrected
Observable: Correct the missing due date or billing email on a still-unpaid invoice. It can qualify at a later evaluation without a manual reminder send.
Source: implied: U-6 repairs the invoice so automatic processing can continue.

### C-20: A confirmed temporary failure remains eligible for automatic retry
Observable: The email service definitively refuses a submission for a temporary reason. A later attempt occurs automatically if the invoice still qualifies.
Source: choice: Recover from temporary outages without requiring operator intervention.

### C-21: An uncertain submission outcome suspends automatic retries for that invoice
Observable: The connection fails after submission may have been accepted. Evaluations submit no additional attempt while the outcome remains uncertain.
Source: choice: A hold avoids sending a duplicate when the original may already have gone out.

### C-22: An authorized billing operator can disable automatic reminders for their workspace
Observable: The operator disables the feature and sees the disabled state.
Source: choice: Operators need a way to stop future automated customer contact.

### C-23: A disabled workspace makes no new automatic reminder submissions
Observable: An eligible unpaid invoice remains in a disabled workspace across evaluations. Zero new reminders are submitted for it while disabled.
Source: implied: U-8 stops new email submissions.

### C-24: Billing operators can inspect reminder outcomes for invoices they may view
Observable: An operator opens an accessible invoice’s reminder history and can identify the outcome and time of recorded attempts.
Source: choice: Receipt questions and recovery require an invoice-level account of what occurred.

### C-25: Rolling back preserves existing invoice records
Observable: An invoice with a recorded payment remains available with that payment in the prior version after rollback.
Source: implied: U-10 restores the prior billing version with its data intact.

### C-26: An accepted reminder still counts after restoring the feature from rollback
Observable: A still-eligible invoice received an accepted reminder before rollback. Restoring and enabling the feature produces zero further automatic submissions for it.
Source: implied: U-10 preserves the one-reminder policy across deployment changes.

### C-27: Reminder eligibility uses the authoritative billing record
Observable: An older view shows a positive balance after a settled payment has been recorded in billing. Evaluating the invoice uses the recorded settled balance.
Source: implied: U-3 depends on the current amount owed.

### C-28: An invoice must be issued before it can receive a reminder
Observable: A draft with a positive amount and a past due date generates zero automatic submissions.
Source: implied: An unpaid invoice in U-2 is an issued obligation.

### C-29: An invoice must remain collectible in billing to receive a reminder
Observable: A voided, canceled or fully written-off invoice generates zero automatic submissions even if its original face amount remains visible.
Source: implied: U-2 concerns amounts the customer still owes.

### C-30: A positive remainder after a posted partial payment counts as unpaid
Observable: An issued invoice with a posted partial payment still passes the balance check when its outstanding balance remains positive.
Source: implied: U-3 depends on whether any balance remains owed.

### C-31: The existing billing balance determines whether a credit or adjustment has settled an invoice
Observable: A posted credit reduces an invoice’s recorded outstanding balance to zero. The invoice generates no automatic reminder.
Source: implied: U-2 relies on amounts still owed, regardless of how billing records settlement.

### C-32: The billing system determines when a payment changes the outstanding balance
Observable: A pending payment that leaves the authoritative invoice balance unchanged also leaves the reminder balance check unchanged.
Source: implied: U-3 relies on payment as recorded by billing.

### C-33: Reminder timing uses the workspace’s existing billing time zone when available
Observable: An invoice due June 10 in a workspace using America/Los_Angeles still fails the timing check at June 11 00:00 UTC, when the workspace is on June 10.
Source: choice: The date the billing workspace uses governs the full payment day.

### C-34: A workspace without a billing time zone uses UTC for reminder timing
Observable: An invoice due June 10 in a workspace without a billing time zone passes the timing check starting June 11 00:00 UTC.
Source: choice: A common fallback makes date-only invoice deadlines unambiguous.

### C-35: Active workspaces are evaluated automatically every billing calendar day in normal operation
Observable: With the scheduler, billing and delivery available, a workspace active throughout a billing calendar day completes at least one evaluation that day when demand is within supported capacity.
Source: choice: Daily evaluation follows the date-based due policy without fixing an hour.

### C-36: Normal processing submits a ready invoice by the end of its first full eligible billing day
Observable: An invoice due June 10 remains fully eligible from the start of June 11 through submission in a healthy, active workspace within supported capacity. The first reminder is submitted before June 12 in the billing time zone.
Source: choice: Daily evaluation must produce a timely customer action when the invoice is ready throughout the day.

### C-37: Automatic email uses the invoice’s designated billing recipient
Observable: A customer has distinct general and billing email addresses. The invoice reminder is addressed to the designated billing recipient.
Source: implied: U-2 follows up with the recipient responsible for that invoice.

### C-38: An ambiguous billing recipient blocks automatic submission
Observable: Billing data offers competing recipients without a designated destination. No automatic reminder is submitted for the invoice.
Source: choice: A follow-up needs an authoritative destination to avoid misdirected disclosure.

### C-39: Distinct invoices are evaluated independently
Observable: Two distinct eligible invoices for the same customer each qualify for their own reminder even when they share a billing email address.
Source: choice: Invoice-level follow-up keeps one invoice’s prior reminder from suppressing a different obligation.

### C-40: The outstanding amount is identified in the invoice currency
Observable: A reminder for 75 CAD outstanding identifies the amount as Canadian dollars unambiguously.
Source: implied: U-2 requires the customer to identify the amount owed.

### C-41: An authorized operator can inspect the effective reminder policy before enabling it
Observable: With reminders disabled, the billing operator can determine that the policy uses email, starts after the due date, and allows one accepted automatic reminder per invoice.
Source: choice: An operator should be able to assess the customer contact policy before opting in.

### C-42: Activation remains effective across ordinary restarts
Observable: An active workspace undergoes an ordinary service restart. Its saved reminder setting still shows active without another opt-in.
Source: implied: U-1 sets up continuing automatic behavior.

### C-43: A definite permanent destination rejection blocks further automatic attempts to the unchanged destination
Observable: The service definitively rejects a mailbox as nonexistent. Later evaluations of the still-eligible invoice make zero submissions to that unchanged mailbox.
Source: choice: Repeating a known permanent failure does not advance delivery.

### C-44: Correcting a permanently rejected destination restores retry eligibility
Observable: Before any acceptance, the operator replaces the permanently rejected billing address with a valid designated address. The eligible invoice can then be submitted to the corrected address.
Source: choice: Repairing the cause of a definite rejection should let automated follow-up proceed.

### C-45: Payment recorded before submission starts suppresses a pending reminder for a settled invoice
Observable: An invoice qualifies when evaluated. Billing records full payment before submission to the delivery service begins. The service receives zero submissions for that invoice.
Source: implied: U-3 can happen after evaluation but before customer contact starts.

### C-46: A partial payment recorded before submission starts changes the amount in the pending reminder
Observable: Evaluation finds 100 USD outstanding. Billing records a 25 USD payment before submission begins. The submitted reminder identifies 75 USD outstanding.
Source: implied: U-2 and U-3 can overlap while an invoice still has a balance.

### C-47: A due date change effective before submission starts can make a pending reminder ineligible
Observable: Evaluation finds an invoice overdue. Before submission begins, billing moves the due date to a future billing day. There is no submission while the new date fails the timing check.
Source: implied: U-6 can change the basis for eligibility after evaluation.

### C-48: A recipient change effective before submission starts supersedes the evaluated recipient
Observable: Evaluation finds billing address A. The invoice designates valid address B before submission begins. The submission goes to B.
Source: implied: U-6 can change the proper destination after evaluation.

### C-49: A collectibility change effective before submission starts suppresses a pending reminder for a closed obligation
Observable: An overdue invoice is voided after evaluation but before submission begins. There is no submission.
Source: implied: U-2 concerns invoices still owed when the reminder is sent.

### C-50: Disablement takes effect for pending work as soon as the operator sees it confirmed
Observable: An invoice is ready to send but submission has yet to begin. Once the disable action is confirmed, it cannot start while the workspace remains disabled.
Source: implied: U-8 places the stop boundary before any new submission.

### C-51: A submission already in progress can finish after a stop condition takes effect
Observable: A submission begins before the workspace is disabled or the invoice ceases to qualify. A later response can record acceptance for that submission.
Source: choice: Once submission starts, later billing or activation changes cannot guarantee withdrawal.

### C-52: Reactivation resumes evaluation of currently eligible unsent invoices
Observable: An invoice becomes overdue while reminders are disabled. After reactivation it can qualify for submission during automatic processing.
Source: choice: The one-reminder policy applies to the current obligation after a pause.

### C-53: A missed evaluation does not consume an invoice’s reminder opportunity
Observable: The evaluator is unavailable on an invoice’s first eligible day. Once it recovers, the still-eligible invoice can be submitted automatically.
Source: implied: U-5 requires automatic follow-up to carry on after interruptions.

### C-54: Overlapping evaluations cannot start concurrent submissions for the same invoice
Observable: Two evaluations find the same eligible invoice before either submits. At most one submission to the delivery service is in progress for that invoice at a time.
Source: implied: U-5 and U-7 operate under the one-accepted-reminder policy.

### C-55: Retries use current invoice eligibility
Observable: A temporary rejection is followed by full settlement before the next attempt. No retry is submitted.
Source: implied: U-3 and U-7 can occur between attempts.

### C-56: Evidence of acceptance clears an uncertain attempt as accepted
Observable: An attempt enters an uncertain state. Later the delivery service confirms acceptance of that same submission. The invoice history shows acceptance for the original attempt.
Source: choice: An authoritative acceptance resolves uncertainty without risking another customer message.

### C-57: Evidence of non-acceptance clears an uncertain attempt for the applicable rejection policy
Observable: An attempt enters an uncertain state. Later evidence establishes that the service did not accept it because of a temporary failure. The attempt becomes eligible for retry under C-20.
Source: choice: Definite non-acceptance lets automatic processing resume safely.

### C-58: Repeated evidence of one attempt’s outcome has one effect
Observable: The same acceptance evidence is presented twice for the same attempt. History records one accepted attempt.
Source: implied: U-7 can receive repeated evidence about one submission.

### C-59: Late failure evidence about an earlier attempt cannot reopen an accepted reminder
Observable: After a later attempt is accepted, evidence of an earlier attempt’s rejection arrives. The invoice remains counted as having an accepted reminder.
Source: implied: U-7 and U-9 must agree about which attempt an outcome describes.

### C-60: An interrupted attempt with unresolved acceptance remains on hold after restart
Observable: Processing stops after a submission may have reached the delivery service but before acceptance is known in billing. After restart, that invoice generates no new submission while the previous outcome is unresolved.
Source: implied: U-7 must apply its uncertainty rule across interruption.

### C-61: A failure on one invoice cannot permanently block unrelated eligible invoices
Observable: One invoice has a bad address or uncertain outcome. Other eligible invoices remain able to progress through evaluations.
Source: implied: U-5 and U-6 encompass multiple independent invoices.

### C-62: Backlog processing cannot indefinitely bypass a continuously ready invoice while usable capacity keeps returning
Observable: New eligible invoices arrive during recovery. An older continuously ready invoice eventually receives an attempt as processing capacity becomes available over successive evaluations.
Source: choice: Backlog recovery should work under continuing arrivals without prescribing an order.

### C-63: The latest successful evaluation remains distinguishable from a later failed evaluation
Observable: A successful empty cycle is followed by a failed cycle. The operator can still tell when the last successful cycle finished.
Source: implied: U-4 and U-7 must distinguish a quiet cycle from a processing failure.

### C-64: A reminder submitted through SMTP is accepted only after the service positively completes the message transfer
Observable: The SMTP service acknowledges the recipient with 250 but has yet to return a positive completion reply after the message data. The attempt is not yet recorded as accepted.
Source: choice: Where email is submitted via SMTP, [RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5) assigns delivery responsibility only after the final positive reply.

### C-65: An SMTP temporary refusal is recorded as definite non-acceptance
Observable: The SMTP service returns 451 after the message data. The operator can distinguish this definite temporary refusal from an unresolved outcome.
Source: choice: [RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5) defines a final 4yz reply as a temporary rejection for which the receiving server will make no delivery attempt.

### C-66: A permanent SMTP refusal before acceptance is recorded as a definite rejection
Observable: The SMTP service returns 550 after the message data. The operator sees a permanent rejection rather than acceptance or an unresolved outcome.
Source: choice: [RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5) defines a final 5yz reply as a permanent rejection for which the receiving server will make no delivery attempt.

### C-67: SMTP acceptance alone is reported as acceptance for delivery
Observable: The SMTP service returns a final positive reply without downstream confirmation. The operator sees only acceptance for delivery.
Source: choice: [RFC 5321 §4.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.5) permits downstream delivery or later failure after the positive reply.

### C-68: SMTP submission requires authorization from the live submission service
Observable: The SMTP submission service refuses authorization. It accepts zero reminders from that unauthorized session.
Source: choice: [RFC 6409 §4.3](https://www.rfc-editor.org/rfc/rfc6409.html#section-4.3) requires refusal by default unless authentication or authorization has been established.

### C-69: An SMTP destination requiring SMTPUTF8 cannot be submitted through a service lacking that capability
Observable: A billing address has a non-ASCII mailbox local part. The SMTP service does not advertise SMTPUTF8. No submission is made to that destination through that service.
Source: choice: [RFC 6531 §3.2](https://www.rfc-editor.org/rfc/rfc6531.html#section-3.2) forbids transmission of internationalized addresses in this case.

### C-70: Base SMTP reminder lines fit the protocol’s line limit
Observable: For a submission over base SMTP without a relevant extension, every message line fits within 1,000 octets including the line terminator, excluding the extra dot used for SMTP transparency.
Source: choice: [RFC 5321 §4.5.3.1.6](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.1.6) sets the base SMTP text-line limit. The limit does not dictate customer-facing wording.

### C-71: An SMTP server that stops responding leaves a bounded submission attempt
Observable: During SMTP submission the service stops responding. The attempt leaves its in-progress state when the applicable operation timeout expires. The exact deployed timeout is unconfirmed.
Source: choice: [RFC 5321 §4.5.3.2](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2) requires SMTP client timeouts per operation. A deployment-wide task timeout is a separate hosting limit.

### C-72: A production deployment takes up evaluations without an active user session
Observable: All users sign out before the next billing day. With the production scheduler running and dependencies available, the active workspace is still evaluated.
Source: implied: The automatic operation in U-1 cannot depend on the operator keeping a session open.

### C-73: A forced end to a production evaluation leaves eligible unsubmitted work recoverable
Observable: The hosting service terminates an evaluation at its permitted execution limit. A later evaluation can take up invoices whose submission never began. The host’s exact execution limit is unconfirmed.
Source: choice: A selected host may end work at its own execution boundary. U-5 requires continuation after such a boundary.

### C-74: A delivery-service throughput limit defers work the service cannot accept yet
Observable: The live email service reports that its sending rate or quota is exhausted before it accepts a reminder. The unaccepted reminder remains eligible for reconsideration when there is capacity. The service’s exact rate and quota are unconfirmed.
Source: choice: The selected provider enforces its own sending limits. Capacity exhaustion should preserve the opportunity to send under U-5.

### C-75: Production readiness requires a functioning background schedule
Observable: A release operator verifies whether production can execute a reminder evaluation without an active interactive session. A deployment without a functioning background schedule cannot be reported as ready for live reminders.
Source: choice: An enabled setting alone cannot implement U-1 in production.

### C-76: Production readiness requires a permitted live sender
Observable: A release operator checks the production sender against the configured service. A sender limited to sandbox or test recipients cannot be reported as ready for live customer reminders. Exact provider approval requirements are unconfirmed.
Source: choice: A delivery service can constrain who may send to live destinations. Live readiness must reflect the actual deployment permissions.

### C-77: Nonproduction evaluation cannot contact live billing recipients
Observable: A nonproduction deployment evaluates a copy of an eligible live invoice. It submits zero emails to the live billing recipient.
Source: choice: A test deployment should be safe to exercise on copied data.

### C-78: Existing invoice creation retains its prior behavior
Observable: Where invoice creation already exists, a caller uses its existing input and permissions and observes the same invoice creation result with reminders present.
Source: implied: The request adds follow-up to existing billing in U-12.

### C-79: Existing invoice editing retains its prior behavior
Observable: Where invoice editing already exists, a caller can apply the same permitted changes under the same validation rules while reminders are enabled.
Source: implied: U-6 and U-12 depend on ordinary billing edits.

### C-80: Existing invoice issuance retains its prior behavior
Observable: Where issuance already exists, an authorized operator issues an invoice during a delivery outage and sees the usual issuance result.
Source: implied: U-12 conducts ordinary billing independently of the new delivery dependency.

### C-81: Existing payment posting retains its prior behavior
Observable: A payment is posted during a reminder delivery outage. The billing record reflects the payment under the existing billing rules.
Source: implied: U-3 uses the existing payment flow.

### C-82: Existing manual invoice or reminder sends retain their prior behavior
Observable: Where the billing product already offers a manual send, the same authorized action remains available before and after an automatic reminder is accepted.
Source: implied: U-12 preserves existing manual actions.

### C-83: An automatic reminder leaves the financial record for its invoice intact
Observable: Compare the invoice’s amount, balance, currency, due date and payment history immediately before and after an accepted reminder with no other billing activity. All financial values are identical.
Source: implied: U-2 communicates the financial state rather than changing it.

### C-84: Acceptance of an automatic reminder is identified separately from ordinary invoice issuance
Observable: After an automatic reminder is accepted, the operator can distinguish that event from when the invoice was originally issued.
Source: implied: U-9 investigates a follow-up to the existing obligation.

### C-85: Changing one workspace’s reminder setting has no effect on another workspace’s setting
Observable: An operator with access to workspaces A and B enables reminders in A. B retains its prior setting.
Source: implied: U-1 establishes workspace-level control.

### C-86: A workspace’s reminder status is visible only under its applicable access permissions
Observable: A caller with access to workspace A only requests workspace B’s reminder settings or evaluation status. No reminder settings or evaluation status for B is disclosed.
Source: implied: U-1 and U-4 operate on the workspace the operator is allowed to see.

### C-87: Attempt history follows current invoice access
Observable: A billing operator loses permission to view an invoice. A later request reveals none of that invoice’s reminder history.
Source: implied: U-9 only permits history for an invoice the operator may view.

### C-88: A reminder discloses no information from unrelated invoices
Observable: Two customers have invoices with the same display number in separate workspaces. A reminder to either customer contains zero details from the other customer’s invoice.
Source: implied: U-2 refers to the recipient’s obligation.

### C-89: A reminder uses no recipients outside the invoice’s designated billing destination
Observable: A submitted reminder has no recipient outside the designated destination in the submitted envelope or visible recipient fields.
Source: implied: U-2 sends invoice information to the responsible billing recipient.

### C-90: Customer-supplied data cannot add an email recipient
Observable: An invoice or contact field contains text resembling an extra email header. The service sees no extra recipient created from that text.
Source: implied: U-2 relies on the authoritative billing destination for disclosure.

### C-91: Reminder failure details expose no delivery credentials
Observable: A billing operator inspects the outcome of a failed authentication attempt. No delivery credential is disclosed.
Source: implied: U-7 needs a failure reason within the operator’s access, without granting access to the service secret.

### C-92: An unresolved submission still prevents retry after feature restoration
Observable: An attempt may have been accepted before rollback. After the feature is restored and enabled, the operator still sees an uncertainty hold on that invoice unless reliable evidence has resolved it.
Source: implied: U-10 must preserve the duplicate protection in U-7.

### C-93: A failed stop operation cannot report disablement
Observable: The service fails to apply a disable request. The operator sees no confirmation that the workspace is disabled.
Source: implied: U-8 depends on confirmation as the stop boundary.

### C-94: An outage in authoritative invoice lookup permits no submission based solely on older invoice data
Observable: A previously evaluated invoice may be ready, but the billing system cannot confirm its current state. The delivery service receives no new submission for it until current eligibility can be verified.
Source: implied: U-2 and U-3 require customer contact to use current billing facts.

### C-95: An automatic reminder cannot charge the customer
Observable: An automatic reminder is submitted while the invoice is unpaid. The customer incurs zero payment transactions caused by that reminder.
Source: implied: The request asks for follow-up on money owed, with payment in the existing U-3 flow.

### C-96: Activation is refused when the production schedule is known unavailable
Observable: The live sender is ready, but background evaluation cannot run. An activation attempt leaves reminders disabled.
Source: choice: Activation is meaningful only when the automatic operation can run.

### C-97: A dependency outage after activation is visible without erasing the saved opt-in
Observable: The live email service stops accepting submissions after activation. The operator can distinguish the temporarily impaired service from deliberate disablement.
Source: choice: Continuing user intent and current operational readiness answer different questions for recovery.

### C-98: An affected operator can identify the attempt that needs reconciliation
Observable: An invoice has multiple attempts including one with unknown acceptance. Its history provides a reference that distinguishes the uncertain attempt from the other attempts.
Source: choice: U-7 requires evidence to be checked against the correct submission.

### C-99: Unresolved acceptance does not become a definite rejection merely with time
Observable: The delivery service provides no conclusive outcome. Subsequent evaluations continue to show the uncertainty hold after ordinary retry time has elapsed.
Source: choice: Time alone cannot tell whether a customer message already went out.

### C-100: An authorized operator can reconcile a held attempt using conclusive evidence
Observable: An authorized operator who has authoritative evidence can have the corresponding acceptance or non-acceptance reflected in the held attempt’s outcome.
Source: choice: Recovery must remain possible when evidence is available outside the automated delivery response.

### C-101: Reconciliation requires billing-management permission for the invoice’s workspace
Observable: A caller without billing-management permission attempts to resolve an uncertain attempt. The recorded outcome does not change.
Source: choice: Resolving uncertainty can enable further customer contact.

### C-102: Unverified outcome evidence cannot release an uncertainty hold
Observable: A caller supplies outcome evidence for a different attempt. The held attempt remains uncertain.
Source: implied: U-7 depends on establishing the outcome of the submission actually in doubt.

### C-103: A post-acceptance bounce does not restore automatic submission eligibility
Observable: The provider accepts a reminder and later reports a bounce. A subsequent billing address change yields zero new automatic submissions for the same invoice.
Source: choice: Acceptance consumes the invoice’s one automatic follow-up. Existing manual contact remains available where supported.

### C-104: A reported downstream bounce is visible on the accepted attempt
Observable: The provider reports non-delivery for an accepted submission. The operator can tell that downstream delivery failed after acceptance.
Source: choice: U-9 needs to explain why a customer reports no receipt despite acceptance.

### C-105: Delivery confirmation is recorded only when evidence confirms delivery
Observable: The delivery service reports delivery for a known submission. The operator can distinguish that confirmed delivery from mere service acceptance.
Source: choice: U-9 needs an accurate account of what the service actually confirms.

### C-106: An invoice reopened after a settled balance is reconsidered if no reminder was accepted
Observable: Full payment suppresses an invoice’s reminder. A reversal restores an overdue collectible balance. With no acceptance or other active block, the invoice can qualify again.
Source: implied: U-3 applies the current remaining balance each time.

### C-107: Reopening an invoice does not reset its prior acceptance
Observable: A reminder for an invoice is accepted. The invoice is then paid and later reopened with a positive balance. The same invoice receives zero further automatic submissions.
Source: choice: Settlement history does not change the identity used by the one-reminder policy.

### C-108: A deleted invoice cannot receive a new automatic reminder
Observable: An eligible invoice is removed from the authoritative billing record before submission begins. No new reminder is submitted for it.
Source: implied: U-2 requires a current invoice to follow up on.

### C-109: Reusing a visible invoice number does not inherit another invoice’s reminder history
Observable: Billing replaces a removed invoice with a distinct issued invoice that reuses its display number. The old invoice’s accepted reminder does not suppress the new one.
Source: choice: The one-reminder policy follows invoice identity rather than displayed numbering.

### C-110: The passage of the local billing date controls eligibility on daylight saving transitions
Observable: In a billing time zone with a 23-hour calendar day, an invoice due on that day passes the timing check at the start of the following local date.
Source: choice: The overdue policy preserves the full local due date regardless of its elapsed duration.

### C-111: A catch-up evaluation applies the current billing date
Observable: A workspace misses multiple evaluation days. When it recovers, an unsent invoice is evaluated for current eligibility without a separate submission for each missed day.
Source: choice: A missed evaluation is an interruption to follow-up, not a new customer messaging occasion.

### C-112: Temporary retries respect the delivery service’s communicated retry restriction
Observable: A service refuses a submission temporarily and specifies when it will next permit an attempt. No retry is submitted before that boundary.
Source: choice: The selected service can impose a retry delay or reset time. The exact delay is unconfirmed until the provider is selected or supplies it for the attempt.

### C-113: A temporary rejection is retried by the end of the first full healthy billing day when retry is permitted
Observable: The service definitively rejects a submission temporarily on June 11. If the restriction has expired by the start of June 12, or none was given, a retry is submitted by the end of June 12 provided the invoice remains eligible throughout that day with dependencies available and demand within supported capacity.
Source: choice: A later daily cycle provides a bounded recovery path under the same healthy conditions as the initial attempt.

### C-114: An operator can distinguish capacity deferral from a completed evaluation with no work
Observable: An evaluation has eligible work that cannot be attempted because the email quota is exhausted. The operator can tell that the cycle had deferred work.
Source: choice: U-4 and U-5 require distinguishing quiet processing from an unfinished backlog.

### C-115: Production operators can determine the deployment’s operating limits
Observable: Before live activation, a release operator can learn the supported processing capacity and any host or service limits that bound it, including a reset window when a quota has one.
Source: choice: U-5 and U-11 depend on recognizing when normal daily behavior gives way to catch-up. The deployed figures are unconfirmed.

### C-116: A reminder exceeding the delivery service’s message-size allowance remains visibly unaccepted
Observable: The live email service rejects a reminder because the message exceeds its accepted size. The operator sees a size-related rejection. The provider’s maximum message size is unconfirmed.
Source: choice: The provider can cap accepted message size. [RFC 5321 §4.5.3.1.7](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.1.7) requires a base SMTP server’s message limit to be at least 64 KiB without establishing its actual maximum.

### C-117: A known loss of access to the live sender defers affected submissions until access returns
Observable: Authorization for the configured sender is revoked. After the authorization problem is established, the application stops making further submissions with that sender until authorization is restored.
Source: choice: The runtime can reject unauthorized submissions regardless of invoice eligibility. Recovery should follow repair of the shared dependency rather than treating all destinations as permanently bad.

### C-118: Disabling reminders creates no submission outcome for unsent work
Observable: Disable reminders while an invoice is waiting for a future attempt. History contains no new provider acceptance or rejection for that unsent attempt.
Source: implied: U-9 describes actual submission outcomes.

### C-119: Repeating an already-applied activation request leaves reminders active
Observable: An authorized operator requests enablement twice, including a repeat after losing the first response. The saved state stays active.
Source: choice: Operators must be able to recover from an uncertain response to the configuration action.

### C-120: Repeating an already-applied disable request leaves reminders disabled
Observable: An authorized operator requests disablement twice, including a repeat after losing the first response. The saved state stays disabled.
Source: choice: Operators must be able to retry stopping automated contact.

### C-121: Production rollback stops automatic submissions before the older version takes over
Observable: While rolling back, the release operator can confirm that new reminder submissions are stopped before returning billing traffic to the prior version.
Source: choice: U-10 needs an observable rollback boundary even if previously started submissions can still complete.

### C-122: A reminder identifies the billing sender to the customer
Observable: The recipient can tell which billing organization issued the reminder.
Source: choice: An identifiable sender makes an unsolicited-looking reminder actionable without dictating its wording.

### C-123: Reminder content identifies how to reach the existing invoice or billing flow
Observable: A customer can discover where to view or deal with the invoice from the reminder. The route can be an existing invoice link or an existing billing contact or access instruction.
Source: choice: A reminder should let a customer act without requiring a new payment feature.

### C-124: A workspace with no invoices can enable reminders
Observable: A billing operator enables reminders in an otherwise ready workspace with zero invoices. The workspace becomes active.
Source: choice: Opt-in can precede the first invoice.

### C-125: Eligibility can be recovered after a failure before the submission has started
Observable: An evaluation prepares an invoice for submission and then stops before it contacts the provider. When processing returns, a ready invoice is eligible for a new attempt without the operator needing to clear an uncertainty hold.
Source: implied: The hold in U-7 applies only when acceptance is possible.

### C-126: Evidence for a different workspace cannot resolve a held attempt
Observable: Matching-looking invoice numbers from two workspaces are present in a reconciliation request. Evidence belonging to the other workspace leaves the held attempt unchanged.
Source: implied: U-7 must resolve the correct invoice without crossing the access boundary in U-12.

### C-127: A permanent destination block survives an ordinary restart
Observable: The provider rejects a destination permanently before acceptance. The application restarts while the invoice and cause of rejection are unchanged. The invoice is still blocked from sending to that destination.
Source: implied: The recovery in U-7 depends on correcting the cause of a definite permanent rejection.

### C-128: The operator can distinguish a workspace awaiting its first evaluation from one that has completed an empty evaluation
Observable: Immediately after activation and before the first completed evaluation, the operator can tell that no evaluation has completed yet.
Source: choice: Newly enabled operation should be distinguishable from a proven quiet cycle.

### C-129: A change in the effective billing time zone applies to future submission eligibility
Observable: An invoice was evaluated as overdue. Before submission begins, billing records a time-zone change under which the due date is still today. There is no submission while the invoice fails the timing check.
Source: choice: The effective billing date at submission governs the overdue policy.

### C-130: Existing invoice access rules also apply when opening an invoice from a reminder
Observable: If a reminder offers a link to an existing restricted invoice, a caller without the required entitlement is denied invoice access through that link.
Source: implied: U-2 introduces a way to identify the obligation while U-12 preserves invoice access boundaries.

### C-131: Suppression for accepted reminders lasts as long as the same invoice can qualify again
Observable: A prior accepted reminder is no longer displayed in the regular activity history. Reevaluating the same invoice still produces zero further submissions.
Source: choice: Visible history retention must not shorten the one-reminder policy.

### C-132: A permanent destination failure is visible without requiring a retry
Observable: An attempted reminder is permanently refused for an invalid mailbox. The invoice history identifies the destination-related problem on that attempt.
Source: implied: U-6 and U-7 require the operator to know what can be corrected.

### C-133: A temporary submission refusal cannot trigger repeated attempts in the same billing day
Observable: The provider definitely rejects a reminder temporarily early on June 11. The application makes zero further automatic submissions for that invoice on June 11.
Source: choice: The daily policy lets a temporary problem clear and prevents concentrated repeated attempts. A later provider-imposed retry boundary still applies.

### C-134: A definite permanent rejection for a reason other than the destination blocks retries while that reason remains
Observable: The provider rejects a reminder permanently because its size exceeds the allowed maximum. With the size and the limit unchanged, later evaluations make zero further automatic submissions for that invoice.
Source: choice: Permanent failures require correction of their cause, which can be outside the recipient’s address.

### C-135: Correcting a permanent submission failure restores eligibility to attempt an otherwise ready unsent reminder
Observable: A permanent size rejection is followed by a change that puts the reminder within the provider’s limit. While the invoice remains otherwise eligible, automatic processing can attempt it again.
Source: choice: A permanent rejection describes the failed submission conditions and should cease blocking after correction.

### C-136: Handing off a reminder for later provider delivery counts as starting submission
Observable: The delivery service receives a reminder for asynchronous processing. A later disablement does not treat that handoff as an unsent item, even if the service is still processing it.
Source: choice: U-8 can stop future handoffs but a provider’s asynchronous handling begins after the submission boundary.

### C-137: An operator can identify when a ready invoice is deferred by provider capacity
Observable: A provider-wide limit is reached before an otherwise ready invoice can be attempted. The operator can tell that the invoice is awaiting capacity.
Source: choice: U-5 and U-7 require deferral to be distinguishable from an invoice data or delivery failure.

### C-138: A recorded acceptance is not revoked by conflicting non-acceptance evidence for the same attempt
Observable: An acceptance is recorded. Conflicting evidence later claims that the same submission was rejected before acceptance. Zero new submissions result from the contradiction.
Source: choice: Conflicting evidence cannot safely establish that no customer contact occurred.
