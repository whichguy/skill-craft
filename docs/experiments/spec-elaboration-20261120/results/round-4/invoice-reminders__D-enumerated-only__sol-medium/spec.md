## Use cases

### U-1: A billing operator enables reminders to collect outstanding invoices
Flow: The operator enables reminders for their billing account, checks that the setting took effect, and leaves collection running unattended.  
Source: implied: “Set up automatic reminders” requires a way to put automation into service.

### U-2: An invoice recipient receives a reminder to identify what remains due
Flow: An issued invoice stays overdue with an outstanding amount. The current billing contact receives a reminder identifying the invoice and what is owed.  
Source: implied: “reminders for unpaid invoices” presumes someone can act on the reminder.

### U-3: An invoice recipient settles an invoice to stop future reminders
Flow: A partial payment changes the amount due. Once payment or another recorded settlement clears the outstanding amount, later reminders stop.  
Source: implied: “unpaid invoices” makes settlement relevant at send time.

### U-4: A billing operator reviews an empty account to confirm that no reminder is due
Flow: The operator enables reminders when there are no eligible invoices. No message is sent. The operator can leave reminders enabled for future invoices.  
Source: implied: the set of unpaid invoices can be empty.

### U-5: A billing operator handles many due invoices to keep collections moving
Flow: Many invoices qualify at the same time. The operator monitors submissions, including outcomes for reminders whose time window expires during a backlog.  
Source: implied: “invoices” can be plural and sending has finite throughput.

### U-6: A billing operator corrects invoice data to make future reminders possible
Flow: An issued invoice has a missing due date or unusable billing address. The operator finds the problem, corrects it through the billing workflow, and checks the next eligible attempt.  
Source: implied: sending relies on invoice terms and a reachable recipient.

### U-7: An account member attempts to manage reminders to learn whether they have access
Flow: A member without the required permission attempts to change settings or view invoice reminder history. Access is refused.  
Source: implied: sending and seeing customer information on behalf of a billing account require authorization.

### U-8: A billing operator pauses reminders to suspend collection messages
Flow: The operator pauses the account while reminders are due. The operator later resumes and checks which scheduled reminders can still be sent.  
Source: implied: operating an automatic sender requires a way to stop it.

### U-9: A billing operator inspects a failed reminder to understand what happened
Flow: The mail service rejects a submission, becomes unavailable, or returns no definitive acceptance. The operator checks the resulting outcome and whether automatic recovery is pending.  
Source: implied: reminders depend on an external delivery channel that can fail.

### U-10: A billing operator enables reminders for existing invoices to continue collections
Flow: The account has already-issued invoices at rollout. If enabled on 2026-11-23 for an unpaid invoice due 2026-11-20, the operator can see future windows opening at 09:00 UTC on 2026-11-27 and 2026-12-04. No reminder is sent for 2026-11-21.  
Source: implied: the request can apply to unpaid invoices that already exist.

### U-11: A release operator reverts the feature to stop automation during rollback
Flow: The release operator stops submissions for rollback, preserves the evidence needed for recovery, then explicitly restores automation if the feature is redeployed.  
Source: implied: the rollout must be reversible.

### U-12: A billing operator reviews pending reminders to reconcile an invoice
Flow: The operator checks the timing and outcome for an invoice they can view, including a reason when the service cannot send.  
Source: implied: U-5 and U-9 require enough information to act on the outcome.

### U-13: A billing operator changes an invoice during a reminder window to keep the message accurate
Flow: The operator records a payment or edits the due date or recipient while a window is open. Submissions use the billing state effective when they start. The operator can see a correction or suppression reflected in later activity.  
Source: implied: U-2, U-3, and U-6 can overlap during automatic operation.

### U-14: A release operator restores interrupted processing to continue service without duplicate mail
Flow: Processing resumes after a crash or an overlapping run. Open windows can progress. Outcomes for transmissions whose acceptance was uncertain are reconciled when reliable evidence arrives.  
Source: implied: U-5 and U-9 can overlap when processing resumes.

### U-15: A release operator activates a production integration to run reminders unattended
Flow: The operator confirms scheduled processing can run without an active user session, verifies the production sender can submit mail, and checks health while account sending remains disabled.  
Source: implied: U-1 and U-14 require a runtime capable of unattended operation.

### U-16: A billing operator continues normal billing while reminders run
Flow: The operator issues and manages invoices, records a settlement, and uses any pre-existing manual invoice communications under their existing rules. Reminder failures leave those actions usable.  
Source: implied: automatic reminders are an addition to the invoice lifecycle used in U-2, U-3, and U-6.

### U-17: A billing operator verifies a settings change after an interruption
Flow: The operator cannot tell whether an enable or pause request succeeded. They reread the setting and its effective time before retrying.  
Source: implied: U-1 and U-8 may be interrupted before the operator gets a confirmation.

## Clauses

### C-1: Unpaid invoices receive reminders automatically.
Observable: An invoice that meets the applicable reminder rules causes a reminder without a person initiating that individual send.  
Source: request

### C-2: A fully paid invoice is ineligible for a new reminder.
Observable: After payment clears the invoice, no further submission is initiated for it.  
Source: implied: U-3 and “unpaid invoices”

### C-3: An account with no eligible invoices produces no reminders.
Observable: With zero eligible invoices, the account produces zero reminder submissions.  
Source: implied: U-4

### C-4: An authorized billing operator can enable reminders for their billing account.
Observable: The operator enables the feature and can see that the account is enabled.  
Source: choice: U-1 can start automation at the billing-account boundary.

### C-5: An authorized billing operator can pause reminders for their billing account.
Observable: The operator pauses the feature and can see that the account is paused.  
Source: choice: U-8 needs a reversible stop.

### C-6: Reminders use email.
Observable: The intended billing contact receives the reminder in their email mailbox when delivery succeeds.  
Source: choice: email requires no dedicated recipient app.

### C-7: Each reminder is addressed to the invoice’s intended recipient.
Observable: For two invoices with different intended recipients, each reminder is addressed to the recipient for the invoice it concerns.  
Source: implied: U-2

### C-8: An account member without reminder-management permission cannot change reminder settings.
Observable: The member attempts a settings change and receives an access refusal.  
Source: implied: U-7 requires authority to send on behalf of the account.

### C-9: Existing invoices can qualify for reminders.
Observable: A previously issued invoice that meets the same applicable rules as a new invoice can produce a reminder.  
Source: implied: U-10 and the request cover unpaid invoices regardless of when the feature was added.

### C-10: The operator can inspect the outcome of a reminder for an invoice they manage.
Observable: The operator opens the record for an attempted or blocked reminder and sees its outcome.  
Source: choice: U-5, U-6, and U-9 require evidence to distinguish sending from failure.

### C-11: A temporary delivery outage permits automatic retry.
Observable: When a temporary error allows recovery under the retry rules, the reminder is retried without an operator initiating it.  
Source: choice: U-9 keeps ordinary recovery automatic.

### C-12: Rollback suspends initiation of reminder submissions.
Observable: After the rollback stop takes effect, the release operator observes zero newly initiated reminder submissions from the reverted deployment.  
Source: choice: U-11 needs a safe operational stop.

### C-13: Automatic reminders start disabled for each billing account.
Observable: An account with no saved reminder setting shows disabled and produces zero submissions before enablement, including after initial rollout.  
Source: choice: outward communication begins after the account authorizes it.

### C-14: Reminder-management permission is scoped to one billing account.
Observable: A caller with permission to manage reminders for account A can read or alter A’s reminder setting. The same permission confers no access to B’s setting.  
Source: choice: U-1 and U-7 use the billing account as the authorization boundary.

### C-15: Viewing invoice reminder history requires authority to view that invoice.
Observable: A caller who cannot view an invoice cannot obtain its reminder history by any account or invoice identifier.  
Source: implied: U-7 and U-12 keep reminder evidence within existing invoice access.

### C-16: A reminder refers to one invoice within one billing account.
Observable: Two invoices with the same displayed number in different accounts are evaluated as separate invoices.  
Source: implied: U-2 requires the right invoice to be found even if display numbers coincide.

### C-17: An invoice must have been issued to qualify.
Observable: A draft or other unissued invoice with a positive displayed amount produces zero submissions.  
Source: choice: a recipient can act on an issued invoice.

### C-18: A reminder requires a positive collectible balance.
Observable: An invoice qualifies on the balance dimension only when the current billing record shows a collectible amount strictly greater than zero in its invoice currency. Zero balances, credit balances, and unavailable or indeterminate balances fail this check.  
Source: choice: the remaining collectible amount gives “unpaid” an operational meaning.

### C-19: Terminal invoice states block reminders.
Observable: Paid or otherwise fully settled, voided or canceled, written-off, deleted, and superseded invoices produce zero new submissions even if an old snapshot shows a positive balance.  
Source: choice: these invoice dispositions end collection for that record regardless of residual accounting entries.

### C-20: An explicit collection hold blocks reminders.
Observable: An invoice with a billing-record collection hold or an unresolved dispute produces zero submissions while that state applies.  
Source: choice: U-3 collects only amounts the billing account currently treats as eligible for ordinary collection.

### C-21: A reminder requires a valid due date.
Observable: An invoice with a missing or invalid due date produces zero submissions. A valid date is a real Gregorian calendar date recorded by the billing account for the invoice, including a valid leap day.  
Source: choice: an overdue schedule requires an unambiguous calendar date.

### C-22: Reminders have three scheduled offsets from the due date.
Observable: For an invoice due 2026-11-20, its scheduled offsets fall on 2026-11-21, 2026-11-27, and 2026-12-04. The offsets are 1, 7, and 14 calendar days after the due date, including weekends and holidays.  
Source: choice: three spaced contacts serve collections with a finite sequence.

### C-23: Each scheduled reminder window opens at 09:00 UTC.
Observable: For an invoice due 2026-11-20, the first window opens at 09:00 UTC on 2026-11-21 regardless of daylight saving changes or viewer location.  
Source: choice: one fixed clock makes the cutoff independent of local clock changes.

### C-24: Each reminder window is open for 24 hours.
Observable: The first window for a due date of 2026-11-20 permits submission starting at 09:00 UTC on 2026-11-21 up to but excluding 09:00 UTC on 2026-11-22.  
Source: choice: bounded recovery tolerates a brief delay without delivering stale reminders.

### C-25: An invoice must be issued by a window’s opening to use that window.
Observable: An invoice backdated on 2026-11-21 at 10:00 UTC with a due date of 2026-11-20 can next qualify at 09:00 UTC on 2026-11-27.  
Source: choice: the earlier reminder time was scheduled before the recipient had the invoice.

### C-26: A reminder uses one designated invoice billing address.
Observable: A submission has exactly one recipient, the address currently designated by the billing record for this invoice. There are zero CC or BCC recipients and zero fallback recipients.  
Source: choice: a single explicitly designated destination avoids guessing among customer contacts.

### C-27: An invalid billing destination blocks sending.
Observable: Missing, malformed, ambiguous, suppressed following a known permanent delivery failure, and explicitly opted-out destinations each produce zero new submissions. An address is ambiguous when the billing record designates more than one mailbox for the invoice and establishes no priority.  
Source: choice: U-6 requires a single usable destination and respect for known delivery restrictions.

### C-28: A reminder identifies the bill it concerns.
Observable: The email provides the issuing business identity, the displayed invoice reference, the current due date, the amount still collectible, and its currency. Presentation can vary.  
Source: choice: these details let a recipient reconcile a partially paid or overdue invoice.

### C-29: A reminder states that payment is requested.
Observable: The email makes clear that an outstanding amount is due for the identified invoice.  
Source: implied: U-2 and “reminders for unpaid invoices”

### C-30: A reminder uses a sender authorized for the issuing billing account.
Observable: An account without an approved sending identity produces zero submissions. With an approved identity, the submitted email uses that identity.  
Source: choice: the recipient must be able to attribute the request to the right issuer.

### C-31: Account controls support enable and pause.
Observable: The operator can change only whether automatic reminders are enabled at the account boundary. Reminders have no operator-adjustable cadence, time zone, channel, message template, or recipient selector in this feature.  
Source: choice: a fixed policy and a single operational control satisfy setup without requiring configuration expertise.

### C-32: Reminder activity identifies individual scheduled windows.
Observable: For an invoice, the operator can identify each window represented in reminder activity by the scheduled instant and its offset of 1, 7, or 14 calendar days.  
Source: choice: U-12 needs to distinguish occurrences across dates and due-date changes.

### C-33: Reminder activity shows the fields needed to explain a window’s outcome.
Observable: Each visible window shows the invoice reference, scheduled instant, offset, current outcome, time of that outcome, and submission attempt count. It shows a reason for a non-success outcome when one applies.  
Source: choice: U-5 and U-9 can diagnose individual outcomes without reading messages or provider logs.

### C-34: Enablement starts a new eligible schedule interval.
Observable: When enablement or resumption takes effect at instant T, only windows whose opening is at or after T qualify during that enabled interval. A window that opened before T is skipped even if its 24 hours have yet to elapse.  
Source: choice: enabling never causes an immediate backlog of earlier scheduled contacts.

### C-35: Repeating the currently effective setting leaves its start instant intact.
Observable: If an already-enabled account receives enable again, the operator sees the original effective time and the current window remains usable. A repeated pause likewise preserves the time the account became paused.  
Source: choice: repeating a setting change after a lost response must not move the schedule.

### C-36: Concurrent account setting changes resolve in effective order.
Observable: For competing enable and pause requests, the account status after both succeed is the one from the last effective change. The displayed effective time describes that change.  
Source: choice: operators can determine which account control is in force.

### C-37: Eligibility is checked at submission initiation.
Observable: For each attempt, a payment, state change, account pause, due-date edit, suppression or opt-out change, or recipient correction effective before submission initiation is reflected in the eligibility check. Submission initiation is when a specific outbound attempt is committed to handoff as described in C-93.  
Source: choice: applies the current billing decision equally to first attempts and retries.

### C-38: Content reflects the billing state at submission initiation.
Observable: If a partial payment reduces the outstanding amount from 100 USD to 40 USD before initiation, the attempted message states 40 USD. The same rule uses the effective recipient and due date for an eligible changed invoice.  
Source: choice: U-13 keeps eligible messages accurate after edits.

### C-39: A new submission cannot be initiated using stale or unavailable authoritative data.
Observable: An attempt waits or expires if the service cannot establish the effective setting, issuance, invoice status, collection hold or dispute, due date, collectible balance and currency, billing destination and restrictions, or authorized sender at initiation.  
Source: choice: waiting is safer than sending collection mail based on uncertain facts.

### C-40: A submission already initiated can complete after eligibility changes.
Observable: If the account is paused, the invoice settles, the destination changes, or the rollback stop takes effect after submission initiation, the operator may still see acceptance or delivery for that specific attempt.  
Source: choice: an external handoff can already be in progress when a billing or control change becomes effective.

### C-41: A due-date change supersedes open windows calculated from the previous date.
Observable: After a due-date edit, the operator sees the superseded window canceled if it was still pending, blocked, or queued for retry. Any already initiated attempt remains visible with its original scheduled instant.  
Source: choice: U-13 must not make a submission against the old invoice terms.

### C-42: A revised due date determines future eligibility for unsent offsets.
Observable: After recalculation, an eligible invoice can use an offset with no prior accepted or unresolved submission if its recalculated window is open or in the future under the ordinary issuance and enablement rules. At 10:00 UTC on 2026-11-28, changing the due date to 2026-11-27 can make that day’s 09:00 UTC first window usable.  
Source: choice: collections follow revised terms while avoiding a repeated accepted contact at the same offset.

### C-43: A corrected invoice can qualify during a still-open window.
Observable: If a missing address, unusable balance, collection hold, dispute, or other temporary eligibility blocker is resolved before the window closes, the invoice can use that window if it still meets all eligibility, attempt, and duplication rules.  
Source: choice: U-6 recovers promptly after a billing correction.

### C-44: Resumed collectibility never restarts a completed reminder offset.
Observable: When a payment is reversed, an invoice is reopened, a hold is released, or a recipient is replaced, an offset already accepted remains consumed for that invoice.  
Source: choice: U-3 and U-13 preserve the three-contact bound even when billing state reverses.

### C-45: Each invoice offset permits at most one accepted submission.
Observable: Overlapping runs, repeated triggers, redeployment, account toggles, due-date edits, retries, and recipient changes cannot produce a second accepted submission for the same billing account, invoice, and offset.  
Source: choice: one contact per offset prevents duplicate collection reminders.

### C-46: Unresolved acceptance blocks any additional submission for the same invoice offset.
Observable: If an attempt may already have been accepted, a restarted or concurrent process does not initiate an additional submission at that offset, including with a new address or a revised date.  
Source: choice: U-14 gives duplicate prevention priority when the service cannot prove what happened.

### C-47: A qualifying window is serviced without manual intervention.
Observable: If eligibility and required dependencies stay available and capacity can service the window, the first attempt starts within 15 minutes of opening or within 15 minutes of becoming eligible during the window, whichever is later, subject to closure.  
Source: choice: the operator needs a measurable healthy-service timing expectation.

### C-48: Overloaded processing gives earlier scheduled windows priority.
Observable: When processing capacity is constrained, among eligible windows ready for an attempt and still open, windows with earlier scheduled instants are taken before later ones. No ordering is prescribed among windows with equal start times.  
Source: choice: the earliest expiry faces the greatest risk during backlog.

### C-49: Reminder scheduling has no feature-imposed invoice count cap.
Observable: Creating a further invoice does not remove another invoice from consideration. When throughput cannot serve every eligible window before closure, each unserved eligible window has its own observable expiry.  
Source: choice: the workspace provides no product volume cap, and capacity may vary by host.

### C-50: Window closure prevents late submissions.
Observable: An attempt cannot start at or after the window’s exclusive end. A pending, blocked, or retry-scheduled window that remains relevant when time runs out shows expired.  
Source: choice: U-5 and U-9 need a predictable cutoff and an observable missed reminder.

### C-51: A definitively rejected attempt can be retried only if the rejection is temporary.
Observable: After explicit temporary nonacceptance, the service retries automatically when the window is open and otherwise eligible, the retry delay has elapsed, and an attempt remains. After permanent rejection, the same window shows permanent rejection without an automatic retry.  
Source: choice: U-9 recovers temporary errors without repeating permanent ones.

### C-52: The earliest automatic retry starts 15 minutes after temporary nonacceptance.
Observable: If the mail service definitively rejects an attempt as temporary at 09:05 UTC, another attempt cannot start before 09:20 UTC. A later service-imposed retry time takes precedence.  
Source: choice: a fixed minimum delay avoids immediate retry loops.

### C-53: A scheduled window permits a maximum of three submission attempts.
Observable: The operator sees an attempt count of at most three for a window, including the initial attempt.  
Source: choice: two automatic retries bound recovery work and external contact attempts.

### C-54: An attempt with no definitive result after 60 seconds is shown as unconfirmed.
Observable: If 60 seconds have elapsed since initiation without authoritative acceptance or nonacceptance, the operator can see an unconfirmed outcome even if processing restarted in the meantime.  
Source: choice: an outstanding request needs a clear point at which its acceptance is treated as uncertain.

### C-55: Definitive external evidence can resolve an unconfirmed attempt.
Observable: The operator can see qualifying evidence resolve an unconfirmed attempt to accepted for delivery, bounced, or permanently rejected. Definitive temporary nonacceptance that rules out later acceptance resolves the window according to the ordinary rules for retry scheduled, blocked, retry exhausted, canceled, or expired. If the window became closed while acceptance was uncertain, its first closure event determines canceled or expired for this result.  
Source: choice: U-14 can recover when the outside service resolves ambiguity.

### C-56: Provider acknowledgement means accepted for delivery.
Observable: When the mail service acknowledges acceptance, the operator sees accepted for delivery. This status represents handoff to the service.  
Source: choice: acceptance is independently observable and mailbox receipt depends on the mail service.

### C-57: A known permanent post-acceptance delivery failure changes the outcome to bounced.
Observable: When definitive bounce evidence for an accepted attempt arrives, the operator sees bounced for that window.  
Source: choice: U-9 needs to distinguish later failure from successful handoff.

### C-58: A bounced reminder still consumes its invoice offset.
Observable: After a permanent bounce from an accepted submission, correcting the address does not cause the same offset to be submitted again.  
Source: choice: bounce is an outcome of a prior accepted submission.

### C-59: A confirmed permanent destination failure suppresses subsequent sends to that destination.
Observable: A permanent failure attributed to the mailbox blocks submissions to that destination for the same billing account until the restriction is cleared through the authorized billing workflow. Changing to a different usable designated address permits future eligible offsets.  
Source: choice: recovery can proceed without repeatedly attempting an address known to fail.

### C-60: Reminder outcomes have a defined set of values.
Observable: The possible current outcomes are pending, blocked, submitting, retry scheduled, accepted for delivery, bounced, permanently rejected, retry exhausted, unconfirmed, expired, and canceled.  
Source: choice: U-12 needs to distinguish work in progress, completed handoff, failed attempts, and skipped work.

### C-61: Reminder processing runs without a foreground billing session.
Observable: After all billing users sign out or close their clients, an enabled account can still process a due window. Production requires an unattended scheduler that can invoke reminder processing while those clients are absent. The scheduler product is unconfirmed.  
Source: implied: “automatic” requires background execution because a client cannot initiate work while it is absent.

### C-62: Production stays stopped when unattended scheduling is unavailable.
Observable: If recurring invocation is absent or fails verification, the release operator sees an unavailable scheduler and outgoing reminders remain stopped for that deployment until scheduling is verified.  
Source: choice: the production prerequisite follows the unattended scheduler rule in C-61.

### C-63: The release operator can see whether background processing is progressing.
Observable: For an enabled account the operator can find the time of the last successful account eligibility evaluation, or see that none has completed. A healthy empty evaluation also updates that time.  
Source: choice: scheduled workers run outside the operator’s client session so successful empty runs need observable evidence.

### C-64: Reminder evaluation resumes after a background run is interrupted.
Observable: If the scheduler stops or preempts a run, a later invocation can continue evaluating still-open windows. The selected runtime’s invocation timeout, minimum recurrence interval, and concurrent-run limit are unconfirmed.  
Source: choice: the scheduler’s execution lifetime can end independently of a reminder window, so eligible work must outlive a single invocation.

### C-65: Mail submission respects the selected service’s capacity restrictions.
Observable: When the external service reports throttling, the operator sees delayed or expired work under the normal window policy. A provider-specified retry time is honored. The selected service and its per-second limit, rolling or daily quota, and submission concurrency limit are unconfirmed.  
Source: choice: the mail service can refuse requests over its enforced capacity.

### C-66: An external mail response deadline does not prove nonacceptance.
Observable: If the mail request ends with a timeout or disconnect without a definitive result, the operator eventually sees unconfirmed under the 60-second policy. The selected service’s response deadline and reconciliation evidence availability are unconfirmed.  
Source: choice: the external service can receive a request even when the caller never receives a response.

### C-67: Production sending requires usable authorization for the external mail service.
Observable: The release operator can see whether production mail access is ready. Before the deployment starts submissions, the selected service must accept the deployment’s authentication and authorize its sending identity and intended recipient scope. The exact credential, sender-verification, and sandbox-exit requirements are unconfirmed.  
Source: choice: an external delivery service can restrict who sends and whom a deployment can reach.

### C-68: Non-production activity cannot submit mail to live invoice recipients.
Observable: A staging or development run that uses copied invoice data or production-shaped settings produces zero submissions to live invoice recipient addresses.  
Source: choice: sender access or a sandbox exception in the chosen environment must not trigger live collection activity from a test run.

### C-69: Production release requires the runtime to satisfy the healthy processing budget.
Observable: If unavoidable scheduler frequency or host duration prevents a healthy eligible window from receiving its first attempt within 15 minutes when dependencies and capacity permit, the deployment cannot activate production sending. The runtime’s minimum interval and duration cap are unconfirmed.  
Source: choice: the hosting runtime’s enforced schedule and duration must allow the chosen user-visible service budget.

### C-70: Over-limit message submissions produce an observable failure.
Observable: An outbound message that exceeds a selected service’s enforced payload or address limit is shown as permanently rejected if the service definitively refuses that submission for the violation. The selected service’s payload and address limits are unconfirmed.  
Source: choice: the email service can refuse an oversized or unsupported message, so that window must expose its outcome.

### C-71: Automatic reminders leave invoice issuance independent.
Observable: The host still permits issue and initial invoice delivery under its existing rules, including while reminders are paused or the reminder mail integration is failing.  
Source: implied: U-16 preserves the operation that makes an invoice available to the recipient.

### C-72: Automatic reminders leave invoice edits independent.
Observable: The host still permits due-date and billing-destination changes under its existing rules while reminders are enabled, paused, or failing.  
Source: implied: U-6 and U-13 depend on the existing paths for fixing invoice data.

### C-73: Automatic reminders leave settlement independent.
Observable: An authorized payment, credit, write-off, reversal, void, or other disposition available in the host continues to take effect under its existing rules regardless of reminder processing.  
Source: implied: U-3 and U-16 rely on the authoritative billing workflow.

### C-74: Automatic reminders leave pre-existing manual invoice communications independent.
Observable: Where the host permits a user to send a manual invoice message, that action retains its existing recipients, validation, permissions, and availability regardless of reminder settings or automatic reminder outcomes.  
Source: choice: U-16 adds unattended messages alongside any independently initiated communications.

### C-75: An automatic reminder leaves the invoice’s accounting facts unchanged.
Observable: Submitting, skipping, failing, or retrying a reminder leaves the invoice’s identity, lifecycle state, issue date, due date, customer, currency, collectible balance, and payment records unchanged.  
Source: implied: “reminders for unpaid invoices” communicates about existing debt.

### C-76: Reminder processing remains within the invoice’s billing account.
Observable: An invoice from account A can yield only a reminder under A’s eligibility, billing data, and sender authority, even if account B uses the same displayed invoice number or shares a recipient mailbox.  
Source: implied: U-2 and U-7 require the designated invoice and issuer.

### C-77: Reminder access refusal does not disclose protected invoice facts.
Observable: A caller without invoice access cannot use a reminder history lookup to establish whether the invoice exists or learn its recipient, amount, schedule, or outcomes.  
Source: implied: U-7 protects invoice data across access paths.

### C-78: A reminder discloses billing data for one invoice only.
Observable: A recipient receiving a reminder for invoice A sees zero identifiers, amounts, balances, or attachments belonging to other invoices, even when the recipient is the billing contact on several invoices.  
Source: choice: U-2 gives the recipient only the billing context needed for that contact.

### C-79: Any invoice link in a reminder preserves invoice access rules.
Observable: If a reminder includes a link, opening it grants at most the access the host grants to an ordinary link for that same invoice. A link cannot expose other invoice records or grant account-management access.  
Source: choice: any optional link must preserve the invoice’s ordinary access boundary.

### C-80: External outcome evidence must belong to the original attempt.
Observable: A duplicate, unrelated, unauthenticated, or mismatched provider event cannot create a submission or change the outcome of another attempt. An authenticated event with the same meaning as a processed event leaves the same visible outcome.  
Source: choice: U-9 and U-14 need outcome evidence that can be reconciled safely after retries or restarts.

### C-81: A late event cannot undo a definitive acceptance.
Observable: After acceptance or a confirmed permanent bounce, an older pending or failure signal about the same attempt cannot replace it with a retry, expiry, or nonacceptance outcome.  
Source: choice: acceptance stays authoritative for both operator history and duplicate prevention.

### C-82: Rolling back preserves billing records.
Observable: Comparing billing records before and after rollback shows the same invoice and payment data except for changes from ordinary billing operations.  
Source: implied: U-11 withdraws the reminder feature from the existing billing workflow.

### C-83: Rolling back preserves reminder evidence needed for restoration.
Observable: After restoration, the operator can recover the saved account setting, attempt counts, definitive outcomes, and unresolved acceptance for the invoice windows that existed before rollback, subject to existing invoice-record access.  
Source: choice: U-11 and U-14 depend on retaining the record of work across versions.

### C-84: Rollback recovery requires explicit release activation.
Observable: Following a rollback stop, merely restoring the newer version produces zero new submissions until a release operator activates production sending again.  
Source: choice: restored code alone is insufficient authority to resume external messages.

### C-85: Rollback recovery only uses windows opened at or after release activation.
Observable: When sending is activated after rollback at instant R, the new deployment can use only windows opening at or after R, subject to the account’s own enablement time and the remaining eligibility rules.  
Source: choice: recovery resumes ongoing collections without replaying the rollback interval.

### C-86: A settings lookup reports the effective account setting.
Observable: An authorized operator sees enabled or disabled and the effective time of the last change. A new account with no saved change shows disabled with no effective change time.  
Source: choice: U-17 needs a way to distinguish an effective pause from a lost response.

### C-87: The settings control rejects requests that do not specify a supported state.
Observable: An authorized caller requests an absent or unsupported state. The caller receives a validation failure and the previously effective setting remains in force.  
Source: choice: the only requested states supported by C-31 are enable and pause.

### C-88: A settings change that cannot take effect is never confirmed as successful.
Observable: If the host cannot make a settings change effective, the operator receives an error or an explicitly uncertain result. A later authorized read shows the authoritative setting regardless of what happened to the earlier response.  
Source: choice: U-17 needs a reliable way to recover from an interrupted write.

### C-89: Pausing cancels still-open unsent work for the current enabled interval.
Observable: After pause takes effect, pending, blocked, and retry-scheduled work in windows already open for that interval shows canceled. An already initiated attempt remains subject to reconciliation. A future window can qualify on resumption under C-34.  
Source: choice: U-8 terminates work that cannot be sent after resumption.

### C-90: The release operator can distinguish stopped production from an unhealthy running schedule.
Observable: Release status exposes the applicable conditions from this set: deliberately stopped, scheduler unavailable, mail authorization unavailable, active with no successful evaluation yet, active with a last successful evaluation at most 30 minutes ago, and active with a last successful evaluation more than 30 minutes ago.  
Source: choice: a 30-minute cutoff allows one late evaluation before indicating a possible stall.

### C-91: A missed background tick does not extend an active window.
Observable: If processing returns after a scheduler or service outage, it can act only during the window’s original 24 hours. At recovery, a known missed window in the enabled interval whose deadline passed is shown as expired if it was pending, blocked, or retry scheduled. A terminal or unresolved submission outcome is preserved.  
Source: choice: U-14 resumes within the original collection timetable.

### C-92: A healthy retry is serviced within 15 minutes of becoming ready.
Observable: When dependencies and capacity permit, the next retry starts no more than 15 minutes after the latest of the retry-delay cutoff, any later provider retry time, and restoration of eligibility. It cannot start after the submission window closes.  
Source: choice: U-9 needs retries to make progress under the same ordinary processing budget as first attempts.

### C-93: A submission attempt is counted once it is committed to external handoff.
Observable: When an outbound attempt is admitted for immediate transmission, it consumes one attempt even if a crash prevents proving that the request reached the mail service. Evaluating a window without admitting an outbound attempt consumes zero attempts.  
Source: choice: the count must survive uncertainty at the handoff boundary.

### C-94: History records the reason for a blocked, canceled, rejected, exhausted, unconfirmed, or expired window.
Observable: The operator sees an applicable reason from these groups: account pause or release stop, changed due date, invoice missing or unissued, terminal invoice state, hold or dispute, missing or invalid due date, unavailable or nonpositive balance, missing or invalid currency, missing invoice reference or issuer identity, missing or malformed or ambiguous address, destination suppression or opt-out, unavailable billing data, unavailable scheduled processing, unavailable mail service or sender authorization, provider refusal or throttling, permanent mailbox failure, attempt budget exhausted, acceptance uncertain, attempt already accepted at that offset, unresolved attempt at that offset in another window, and window closed before a possible submission. When several apply, any applicable reason suffices.  
Source: choice: U-6 and U-9 need actionable explanations without exposing raw external errors.

### C-95: The operator can diagnose an invalid invoice prerequisite even when no window can be computed.
Observable: For an issued invoice during an enabled interval, the operator can observe a missing or invalid due date, an unavailable balance or currency, or a missing, invalid, or unavailable destination without a scheduled instant being fabricated.  
Source: choice: U-6 needs an explanation even when required data prevents a window from existing.

### C-96: Reminder activity distinguishes a planned window from an attempt.
Observable: Before an eligible upcoming window opens, its pending outcome has an attempt count of zero. After it opens, the status reflects blocked, submitting, retry scheduled, or its eventual outcome as work progresses.  
Source: choice: U-12 can distinguish a scheduled reminder from one ever sent to the mail service.

### C-97: Returning to the same due date preserves the original window’s attempt budget.
Observable: If an invoice changes away from a due date and later changes back, the account, invoice, offset, and scheduled instant identify the same window. Its original end time and attempt count still apply. A window canceled solely by the intervening date change can become active if all current rules permit it.  
Source: choice: toggling due dates cannot create a fresh budget for an identical reminder window.

### C-98: A previously terminal rejection remains terminal for its scheduled window.
Observable: If the same window becomes eligible again after an edit, hold, or restart, its existing permanently rejected or retry exhausted outcome cannot return to a sendable status.  
Source: choice: an interrupted eligibility interval does not bypass the retry decision for that scheduled instant.

### C-99: Reminder evidence persists while the invoice can still be viewed or restored.
Observable: An operator with ordinary access can see the related outcomes for as long as the host keeps the invoice viewable. If the host temporarily hides a restorable invoice, its old attempts still govern eligibility when the invoice is restored. Evidence for an irreversibly removed invoice follows the host’s authorized removal policy, whose retention figure is unconfirmed.  
Source: choice: U-3 and U-14 need a stable record for invoices that can still return to collections.

### C-100: An invoice restored under the same identity retains previous reminder outcomes.
Observable: If a settled or removed invoice returns with the same account and invoice identity, an earlier accepted offset remains consumed and unresolved acceptance still blocks that offset.  
Source: choice: reopening or restoration does not create new authority to repeat the same reminder.

### C-101: Vendor error details shown to billing users omit confidential diagnostics.
Observable: An authorized operator can see the applicable user-facing reason without receiving raw provider responses, credentials, message bodies, or unrelated recipient data in the reminder history.  
Source: choice: the status evidence in U-12 needs only invoice-scoped information.

### C-102: The feature exposes no manual override of automatic eligibility.
Observable: A user cannot use the reminder feature to dispatch an extra message, force a retry, or reopen an expired window. Any separately existing manual invoice communication remains governed by its ordinary rules.  
Source: choice: the automated schedule has a consistent cutoff and attempt budget.

### C-103: An invoice must have the billing fields required for a truthful reminder.
Observable: An otherwise eligible invoice is blocked if the authorized issuer identity, invoice reference, or invoice currency is missing or unusable. A currency is usable when the host can denominate the current balance in that currency.  
Source: choice: a recipient must be able to identify the invoice and interpret the amount requested.

### C-104: Each committed attempt may be transmitted at most once.
Observable: Following overlapping runs, a crash, or an ambiguous send response, the feature does not initiate another transmission of the same committed attempt. For the same window, a further attempt is permitted only after definitive temporary nonacceptance under C-51 through C-55.  
Source: choice: U-14 must prevent duplication even when the provider cannot recover the result of a request.

### C-105: A permanent bounce can establish that the original submission was accepted.
Observable: If an authenticated permanent bounce tied to the attempt arrives before its acknowledgement, the operator sees bounced and the invoice offset is consumed.  
Source: choice: a delivery failure for an actual message is evidence of an earlier handoff.

### C-106: A transient post-acceptance delivery event does not cause another submission.
Observable: After acceptance, a delayed-delivery notice or another nonfinal delivery event leaves the outcome accepted for delivery and initiates zero new attempts.  
Source: choice: only the mail service controls delivery after acceptance.

### C-107: Late mail evidence applies to the destination used for the original attempt.
Observable: If the recipient changes from address A to address B before a definitive permanent mailbox failure arrives for A, the failure suppresses A for future submissions. That event does not suppress B.  
Source: choice: a provider result bears on the mailbox actually used.

### C-108: Release controls require deployment-level authorization.
Observable: A caller authorized only to manage settings for a billing account cannot stop or activate production sending for the deployment.  
Source: choice: U-11 and U-15 operate across accounts and require separate authority.

### C-109: Initial production activation excludes windows that opened before the release was active.
Observable: When production sending first becomes active at instant R, an otherwise enabled account produces zero submissions for windows that opened before R.  
Source: choice: initial release follows the same non-replay rule as rollback recovery.

### C-110: A deliberate release stop cancels open unsent work.
Observable: After a deliberate deployment stop takes effect, open pending, blocked, and retry-scheduled windows show canceled. An attempt already committed still follows its existing outcome reconciliation.  
Source: choice: rollback must leave a visible end for work the restoration policy will not replay.

### C-111: Work with uncertain acceptance remains visible after its scheduled window closes.
Observable: If no definitive evidence ever arrives for an attempt, its status remains unconfirmed while the invoice history is accessible. Later eligible offsets remain available.  
Source: choice: an expired schedule cannot prove the attempt was not accepted, while uncertainty at one offset does not end the whole sequence.

### C-112: An evaluated elapsed window is visible even if it had no attempt.
Observable: If the release and account were enabled for the whole window, the due date effective at window closure can be established from authoritative billing data, and issuance met C-25, the operator sees an expired outcome for a wholly missed window when no earlier outcome exists. Recovery does not claim which balance or destination was effective during the outage.  
Source: choice: U-5 and U-14 need evidence of a scheduling miss even when nobody evaluated the invoice during that window.

### C-113: A blocked window reports whether a retry is actually scheduled.
Observable: When a retryable attempt is waiting for an eligibility correction, the window shows blocked until the prerequisite is restored or the window ends. A retry-scheduled window shows the earliest currently allowed retry instant.  
Source: choice: U-9 needs to distinguish time-based waiting from a prerequisite the operator may need to correct.

### C-114: Reminder history does not reconstruct an unverifiable missed window.
Observable: After an outage, if no window was previously known and the effective due date or the enabled interval cannot be established for an elapsed window, the service shows no retrospective per-window outcome for it. The release operator can still see the last successful evaluation under C-63.  
Source: choice: current invoice terms cannot prove that an earlier reminder window existed.

### C-115: Display invoice numbers are not reminder identities.
Observable: If the host permits two separate invoices to display the same number within one account, they retain separate schedules and acceptance histories.  
Source: implied: U-2 and U-12 concern individual invoices, even if human-readable references are reused.

### C-116: The first reminder can never start before its computed opening.
Observable: Changing the recipient, balance, hold, due date, or account setting cannot trigger a submission before the applicable scheduled opening. An invoice due today with unchanged terms produces zero reminders today on the schedule’s UTC date.  
Source: choice: collection activity follows the scheduled offsets rather than acting as an immediate response to edits.

### C-117: The window reports exhausted retries after the last allowed temporary rejection.
Observable: If the third temporary nonacceptance becomes definitive while the window is still open and current, the window shows retry exhausted. If the window first closed while that attempt was unresolved, C-55 determines its outcome.  
Source: choice: the operator needs to distinguish a completed retry budget from work that first ran out of time or was canceled.

### C-118: A healthy active account receives a background evaluation at least every 15 minutes.
Observable: If the deployment and account are enabled and dependencies and capacity permit, the age of the last successful account eligibility evaluation stays at or below 15 minutes, including for an empty account. The first successful evaluation occurs within 15 minutes of both being enabled under those conditions.  
Source: choice: U-4 and U-15 need a way to verify that automation is running even when there is nothing to send.
