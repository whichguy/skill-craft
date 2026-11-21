## Use cases

### U-1: A member joins the waitlist for a full class to get a chance at a seat
Flow: The member opens a specific class session and sees that it is full. They choose to join its waitlist and see whether they have a place in the queue. Their first successful join starts the queue when nobody is waiting. If the request fails, they see the refusal or learn that its outcome needs checking.
Source: request

### U-2: A member opens a class with an available seat to book it
Flow: The member opens a session with a seat available for direct booking and uses the booking action.
Source: implied: the request adds a path for full classes to an existing class booking app

### U-3: A waiting member checks their status to see whether they have a booking
Flow: The member returns to the session or their own waitlist activity. They can tell whether they are still waiting or have a booking.
Source: implied: joining a waitlist is useful only if the member can determine the outcome

### U-4: A booked member frees a seat so a waiting member can get it
Flow: A booked member cancels. If the class remains open for booking, a waiting member can get the seat and see the confirmed booking.
Source: implied: a waitlist for a full class must lead to a chance at a seat once one frees up

### U-5: A waiting member leaves the queue to stop waiting for a seat
Flow: The member withdraws from the session's waitlist and sees that they have left. If they already have a booking, they see the booking and can use the applicable cancellation action.
Source: implied: a request to wait can outlast a member's interest in a class

### U-6: A member retries a request to learn its outcome after a failed response
Flow: A join or withdrawal response is interrupted. The member checks their status and can retry without adding another active place or affecting a booking.
Source: implied: U-1 and U-5 can be attempted more than once or interrupted

### U-7: A caller submits an unavailable or invalid join to find out why it cannot proceed
Flow: The caller attempts a join without access, for an invalid or unavailable session, with a conflicting booking, or where new joins are disabled. The result distinguishes a rejected request from a successful join. An unauthorized caller receives no private session or member details.
Source: implied: U-1 depends on a valid session, access and permission to join

### U-8: Multiple members request the last available opportunities to learn who got them
Flow: Members request a final directly bookable seat or try to join a busy waitlist. Each sees their own outcome. The person who misses the last direct seat can see whether they may join. An otherwise eligible member can join even when many members already wait, subject to service limits. Existing waiters retain their applicable priority as seats open.
Source: implied: several members can seek the same limited class capacity

### U-9: A waiting member sees that a session can no longer admit them to understand their outcome
Flow: A session is cancelled, stops taking bookings, or begins while the member is still waiting. The member sees that waiting for this session has ended.
Source: implied: U-1 cannot produce attendance once the session can no longer admit bookings

### U-10: A booking operator enables the waitlist to verify that members can use it
Flow: The operator checks deployment readiness and the initial setting, enables waitlisting for the intended scope, and reads back its effective status. If readiness or the setting change cannot be verified, the operator sees that activation is unconfirmed. In a session in that scope, a full class offers a join to an eligible member.
Source: implied: U-1 requires waitlisting to be available where the operator intends

### U-11: A booking operator changes where the waitlist runs to control admission
Flow: The operator changes the app-wide setting or a setting for one session, then checks the effective result. Where waitlisting is turned off, outstanding waiting ends and ordinary booking uses available seats.
Source: implied: operating the waitlist requires control over its scope and a visible outcome

### U-12: A booking operator investigates a failed promotion to determine what happened
Flow: The operator locates the session, checks whether it has a seat and whether a promotion is outstanding, then finds the affected member's outcome or the failure. If the service recovers while booking is open, the operator can see whether the work resolved.
Source: implied: U-4 can fail after an available seat has been reported

### U-13: A returning member uses a booking created before the waitlist existed to manage their attendance
Flow: After rollout, the member opens their existing booking and uses its ordinary controls. Its seat still counts for capacity.
Source: implied: the request adds a feature to an existing booking app

### U-14: A booking operator corrects an erroneous waitlist action to restore the applicable booking state
Flow: The operator locates the affected session and member. They can remove a waiting place or use their existing authority to correct a confirmed booking. They see the correction's outcome or why it was refused.
Source: implied: an operator may need to correct a mistaken join or promotion

### U-15: A release operator rolls back the feature to keep ordinary booking available
Flow: The operator disables waitlisting and checks rollback readiness. Once the app confirms that active waitlisting has ended, the operator returns to the earlier version. Ordinary bookings remain usable. On reinstalling the waitlist version, the operator can inspect the retained outcomes before enabling it again.
Source: implied: the app must remain usable if the waitlist release is reversed

## Clauses

### C-1: A member can join a waitlist for a full class session
Observable: An eligible member opens a full session where waitlisting is offered, submits a join, and receives confirmation that their place was accepted. In the absence of a concurrent change, the place is still waiting when they receive that result.
Source: request

### C-2: Joining a waitlist does not confirm attendance
Observable: After a successful join that has not led to promotion, the member sees a waiting result with no confirmed booking for that session.
Source: implied: U-3 depends on distinguishing waiting from booking

### C-3: A seat that opens can be assigned to a waiting member
Observable: In an open full session with one eligible waiter, a cancellation frees one seat and the waiter can obtain a confirmed booking through the waitlist.
Source: implied: U-4 gives the queue a purpose

### C-4: A member can withdraw an active waitlist place
Observable: The member withdraws while still waiting and sees that the place is no longer active.
Source: choice: U-5 lets members stop expressing interest before a booking exists

### C-5: A member can have at most one active waitlist place per session
Observable: Repeating or overlapping a join for the same member and session leaves at most one active place.
Source: choice: one place per person prevents duplicate claims on a limited class

### C-6: A member with a confirmed booking for the session cannot join its waitlist
Observable: A booked member who attempts to join sees their existing booking as the outcome and gains no waiting place.
Source: choice: the member already has the seat the waitlist is meant to provide

### C-7: A seat available for direct booking is offered through ordinary booking
Observable: When a session can accept bookings and no waiting member has priority over a free seat, an eligible member can request that seat through the existing booking action.
Source: implied: U-2 follows from adding a waitlist to the existing booking app

### C-8: A rejected join reports failure
Observable: A caller whose join is rejected receives a refusal rather than confirmation of a waiting place.
Source: implied: U-7 distinguishes an accepted waitlist request from a refused one

### C-9: Waiting ends when the session can no longer take bookings
Observable: A place still waiting when the session is cancelled, removed from the schedule, reaches the applicable booking cutoff or scheduled start, or enters another existing state that closes ordinary booking for the whole session shows the applicable terminal outcome. The complete list of any additional session-wide closed states is unconfirmed.
Source: choice: attendance requires an active session that is still accepting bookings

### C-10: A positive waitlist result refers to one specific class session
Observable: Joining one occurrence of a recurring class yields a place only for the selected occurrence.
Source: implied: U-1 refers to the full class whose capacity is exhausted

### C-11: A join identifies exactly one session
Observable: The caller selects a single occurrence from the schedule or submits a reference that identifies that same occurrence. A missing, malformed, or ambiguous reference produces a refusal that lets the caller correct the selection.
Source: choice: waitlist admission needs an unambiguous destination

### C-12: Joining requires a signed-in member identity
Observable: A signed-out caller is asked to sign in before a waiting place is created.
Source: choice: the app needs a durable owner for the seat request

### C-13: Members act on their own waitlist places
Observable: A signed-in member attempting to join for, withdraw for, or read the waiting status of a different member is refused.
Source: choice: member self-service follows the ownership of the seat request

### C-14: A member needs access to the selected session
Observable: An unknown session reference or a valid reference to a session the caller cannot view produces the same unavailable result. That result reveals neither session details nor whether the session exists.
Source: choice: session lookup must preserve the app's existing visibility boundaries

### C-15: The same session availability governs both booking paths
Observable: A session is full for waitlisting when the existing booking rules report zero open places from its capacity, seat occupancy and existing seat restrictions, before applying waitlist priority. The definitions of occupancy and any additional seat restrictions are unconfirmed. A freed seat is a place those same rules now count as open.
Source: choice: the waitlist and ordinary booking share the class's capacity rules, whose app-specific seat restrictions were not supplied

### C-16: Joining uses the existing eligibility rules for booking the session, apart from seat availability
Observable: A visible session refuses a member whom ordinary booking would refuse for a reason independent of having a seat available. The full list of app-specific eligibility checks is unconfirmed because no booking rules were supplied. Any rule already applied by ordinary booking remains applicable here.
Source: choice: a waiting place represents interest in a booking the member could otherwise make

### C-17: Waitlist availability is visible before the member tries to join
Observable: A member can find the join action from the eligible full session's normal booking view.
Source: implied: U-1 needs a discoverable way to join

### C-18: A join checked against newly available direct capacity returns the booking option
Observable: A member submits a join from a full-session view after a place becomes available for direct booking. The app gives the member the option to book and the join creates no place.
Source: choice: the member's join consent was for the waitlist and the ordinary booking action is now available

### C-19: A disabled waitlist refuses new places
Observable: A member tries to join a session whose waitlist is disabled and receives an unavailable-for-waitlisting result.
Source: choice: the app must honor the applicable availability setting even from an outdated view

### C-20: A session that stops taking bookings refuses joins
Observable: For a visible session, a join is refused after cancellation, removal from the schedule if still visible, the existing booking cutoff if any, or the scheduled start, whichever applies first.
Source: choice: waiting is offered only while a booking could still result

### C-21: Waitlisting honors any existing booking opening time
Observable: If the session has an ordinary booking opening time, a join can take effect at that instant or later if the other admission conditions hold. A join before that instant is refused.
Source: choice: waiting should open alongside the session's established admission window

### C-22: Accepted joins are ordered by acceptance
Observable: For equally eligible members, the next place offered from the waitlist goes to the member whose active join was accepted first. Overlapping joins with no prior acceptance can be accepted in either order, with a single resulting order for that session.
Source: choice: first accepted, first served makes priority predictable without relying on device clocks or imposing a tie-break format

### C-23: The member consents to automatic booking before joining
Observable: A successful join authorizes a later automatic booking for the selected session only, under the booking commitment shown when joining.
Source: choice: automatic assignment is useful without a separate claim step if the commitment is clear up front

### C-24: Promotion creates the member's ordinary confirmed booking automatically
Observable: One eligible waiter in an open session gets a confirmed booking when a seat can be assigned through the waitlist without taking another action.
Source: choice: automatic booking fills the session without a claim period

### C-25: Promotion requires eligibility at the time the booking takes effect
Observable: A member who could join earlier but now fails an applicable ordinary booking rule receives no booking from that promotion attempt.
Source: choice: changing eligibility must affect both paths to a confirmed booking

### C-26: An ineligible waiter leaves the active queue when considered for promotion
Observable: A waiter skipped because an authoritative eligibility check refused the booking can see that the place has ended for ineligibility.
Source: choice: a definitive refusal must not strand the seat behind an entry that could not be booked

### C-27: The member can read the outcome of their own waitlist attempt
Observable: Subject to applicable access and retention rules, the member can distinguish no retained attempt, waiting, promoted, withdrawn by the member, ended by session cancellation or removal, ended when the booking window closed or the session started, ended when ordinary booking was otherwise closed, ended by disabling waitlisting, ended for ineligibility, ended because a booking was obtained separately, ended because the member account closed, and removed by an operator. The app reports only the applicable outcome for the attempt being viewed.
Source: choice: a member needs a durable way to distinguish why waiting stopped

### C-28: The member can identify which session a waitlist outcome concerns
Observable: The member's waitlist outcome shows the class name and scheduled start with the app's usual time context, sufficient to distinguish recurring occurrences. For a removed session it shows the last class name and scheduled start the member was allowed to see.
Source: choice: the user needs to match an outcome to a specific visit

### C-29: The app makes the promotion outcome available in the member's own booking view
Observable: After promotion, the member can open the same confirmed booking details as for a direct booking, with that session's ordinary booking status and controls available.
Source: implied: U-3 and U-4 require the member to find the booking they received

### C-30: An empty queue places no claim on an open seat
Observable: With no active waiters, an open seat can be booked directly without a waitlist action.
Source: implied: U-2 and U-4 distinguish ordinary booking from serving active waiters

### C-31: Rejoining after a withdrawal creates a fresh place at the back
Observable: An eligible member who withdrew, then makes a new join while the join conditions hold, is ordered after every place already active in that session.
Source: choice: an ended request no longer carries priority

### C-32: Waitlisting adds no separate product maximum for queue length
Observable: A member who otherwise qualifies can join a full session regardless of how many members already wait. Any hard ceiling imposed by the deployed service is unconfirmed.
Source: choice: the request gives no business reason to turn away the next eligible member at a fixed queue length

### C-33: Success requires a recorded outcome
Observable: If a join or withdrawal cannot take effect because its required service is unavailable, the caller does not receive a successful result for that action.
Source: implied: U-6 depends on truthful confirmation

### C-34: An uncertain response gives the member a way to check their current status
Observable: If the app cannot tell whether a change completed, it reports that uncertainty. Once the service is reachable, the member can read the current state before deciding whether to try again.
Source: choice: an interrupted response can follow a completed change

### C-35: Waitlist controls require booking-operator authority
Observable: A member without the applicable operator permission cannot read or change operator settings, inspect another member's operational history, or remove another member's place.
Source: choice: the new controls need the same scope boundaries as booking administration, whose role names and scopes are unconfirmed

### C-36: The waitlist starts disabled app-wide on first rollout
Observable: Before an authorized operator enables it, the app-wide setting shows disabled and sessions accept no joins.
Source: choice: first rollout lets operators choose when automatic booking becomes available

### C-37: A booking operator can enable or disable waitlisting app-wide
Observable: An operator with app-wide authority can set the global control to enabled or disabled and read back the applied value.
Source: choice: operators need one control covering all sessions

### C-38: A booking operator can opt an individual session out of waitlisting
Observable: For a session in their scope, an operator can set its control to follow the app-wide setting or to remain disabled. The control affects only the selected occurrence.
Source: choice: a single-session exception covers cases where waitlisting is unsuitable without a new recurring-class policy

### C-39: The effective waitlist setting requires both applicable controls to permit it
Observable: The operator sees effective enabled only when the app-wide setting is enabled and the session follows it. They can distinguish app-wide disabled, session opted out, or both as causes of effective disabled.
Source: choice: a local setting must honor an app-wide stop

### C-40: A newly created or pre-existing session follows the app-wide setting by default
Observable: A session without an explicit opt-out shows the follow setting whether it existed before rollout or was added later.
Source: choice: operators can switch on the feature without editing every class

### C-41: Successfully applying a setting makes the effective result visible to its operator
Observable: After a successful save, the operator can read the resulting effective setting for affected sessions.
Source: choice: the operator needs to verify a change before relying on it

### C-42: Disabling waitlisting ends affected active places
Observable: An operator disables waitlisting for a session, directly or app-wide. Affected waiters can see the ended-by-disablement outcome and the ended places can no longer receive a booking.
Source: choice: disabling removes the expectation of an automatic booking and returns open seats to ordinary booking

### C-43: Re-enabling waitlisting starts with no places from an earlier disablement
Observable: Members whose places ended on disablement can make fresh joins when eligible. Their old places provide no priority.
Source: choice: an ended request cannot authorize a later booking

### C-44: Changing a waitlist setting leaves confirmed bookings in place
Observable: A member already confirmed at the time of the setting change still has their booking, regardless of whether it originated on the waitlist.
Source: implied: U-11 changes waiting scope and U-3 distinguishes promotion from waiting

### C-45: Operators can inspect an individual session's waitlist
Observable: An authorized operator can find a session by its class and occurrence, see its effective setting, see the number of open seats under booking rules, and view its active queue in service order.
Source: choice: session-level inspection lets the operator verify activation and diagnose whether a seat should go to a waiter

### C-46: Operators can identify an active waitlist place
Observable: For each active place in the session view, an authorized operator can identify the member using the app's existing member references and see the join time. Display format and identifiers follow the existing operator context, whose conventions are unconfirmed.
Source: choice: investigation and correction require selecting the intended member

### C-47: Operators can find waitlist outcomes by occurrence and affected member
Observable: Within their scope an operator can locate accepted joins, member withdrawals, promotions, class cancellation or removal, closures at the booking window or start or in another existing session-wide closed state, disablement closures, eligibility refusals on promotion, endings because a booking was obtained separately or the account closed, operator removals, and promotion failures and recoveries.
Source: choice: these are the events that account for why a waitlist place changed or why an open seat was left unfilled

### C-48: Operators can tell who or what produced a recorded waitlist outcome
Observable: A recorded outcome exposes the session, affected member for member-specific events, time, action, result or failure reason, and responsible member, operator, or automatic action. Where a promotion succeeded, it also identifies the associated booking.
Source: choice: an operator needs to connect a state change to its cause and resulting seat assignment

### C-49: An operator can determine who changed a waitlist setting
Observable: The operator history for either setting shows the scope selected, previous value, resulting value, time, and acting operator for each applied change.
Source: choice: changes affecting many members must be traceable

### C-50: A booking operator can remove an active place as a correction
Observable: After selecting the active place for a member in the session, an authorized operator can end it and see confirmation.
Source: choice: operators need to remove erroneous entries without assigning a seat

### C-51: A promoted booking is corrected through existing booking controls
Observable: An operator with the app's existing booking correction permissions can act on a promoted booking with the same applicable controls as a direct booking. The control names and the complete list of supported booking corrections are unconfirmed.
Source: choice: correcting a confirmed booking must apply existing authority and consequences

### C-52: Correcting a booking does not restore its consumed waitlist place
Observable: After an operator cancels a mistaken promoted booking, the original attempt still shows that it was promoted. The booking displays its resulting status separately.
Source: choice: restoring the old priority would revive consent after the original request already produced a booking

### C-53: Booking records that predate waitlisting continue to occupy seats under existing rules
Observable: A class full of bookings from before rollout is full after rollout unless an ordinary event changes the available capacity.
Source: implied: U-13 preserves existing attendance commitments

### C-54: Old booking records do not generate waitlist places
Observable: On first rollout, an existing member or session shows no prior waitlist activity solely because it has booking history.
Source: choice: an ordinary booking provides no evidence that a member asked to wait

### C-55: A release operator can determine whether rollback has ended active waitlisting
Observable: For rollback, the release operator can verify global disablement and that there are zero active places and zero promotions still able to take effect before switching versions.
Source: choice: the earlier version cannot be relied on to honor an active queue

### C-56: Rollback preserves confirmed bookings
Observable: In the earlier release, members can find and use their confirmed bookings, including waitlist promotions completed before rollback.
Source: implied: U-15 must preserve attendance commitments while restoring ordinary booking

### C-57: Reinstalling after rollback preserves retained waitlist outcomes
Observable: Once the waitlist release is restored, the operator can inspect the outcomes recorded before rollback that remain within the app's applicable retention policy.
Source: choice: correction and investigation need the prior record without reviving withdrawn commitments

### C-58: Waitlist outcome history follows the applicable retention rules
Observable: Member and operator waitlist history remains available under the app's applicable access and retention rules. The duration and any record-specific exceptions are unconfirmed because no retention policy was supplied.
Source: choice: make completed outcomes reviewable subject to the app's data policy

### C-59: An active queue has priority over ordinary booking for an open seat
Observable: While waitlisting is effective and a session is still taking bookings, an ordinary booking cannot claim newly free capacity while the session has an active waiter. The app can offer any remaining free capacity for ordinary booking once the active queue is empty.
Source: choice: the same ordering must hold even if a direct booking arrives before promotion completes

### C-60: An open seat awaiting promotion has a distinct join outcome
Observable: An eligible member without a booking or waiting place who tries to join while existing capacity rules report an open seat held for the active queue sees that direct availability is pending. That submission creates no waiting place. If the session returns to full, the member can submit a fresh join.
Source: choice: joins are for full sessions and a pending allocation can change whether the visitor needs to wait

### C-61: Any ordinary change that opens seats can lead to promotion
Observable: The active queue is considered when a cancellation releases a seat or, if the app supports them, a capacity increase, a released reservation or hold, a correction, or another ordinary availability change makes a place bookable. The complete catalog of app-specific availability changes is unconfirmed.
Source: choice: how a seat became free should not change who gets priority

### C-62: An opening of several seats can serve several waiters
Observable: With two open seats and three active, eligible waiters, the first two in service order receive bookings and the third stays waiting if the session remains full.
Source: choice: a single event can create more than one opportunity to fill the class

### C-63: Promotion honors capacity as it exists when the booking takes effect
Observable: If a reported open seat is no longer available when promotion would confirm the booking, no promotion consumes that seat and the affected member keeps their place unless another ending condition applies.
Source: choice: capacity and queue membership can change after an opening is reported

### C-64: A waitlist place can be consumed only with a confirmed booking
Observable: The member first sees the attempt marked promoted only once the corresponding booking has been confirmed. If confirming fails, the place remains active unless a separate valid end to waiting applies.
Source: choice: the member must not lose their turn to an incomplete promotion

### C-65: A promotion produces at most one booking for its place
Observable: Repeated or concurrent processing of the same waitlist place results in at most one confirmed booking created from that place.
Source: choice: duplicate availability signals and retries must not duplicate a booking

### C-66: Booking does not exceed the seats then available
Observable: When a session has one remaining bookable seat, competing direct booking or promotion attempts can result in at most one new booking against that seat.
Source: implied: U-8 depends on full retaining its meaning when the last seat is contested

### C-67: A withdrawal that takes effect first prevents promotion of that place
Observable: Once the withdrawal is effective, even a promotion already under consideration cannot confirm a booking from the withdrawn place.
Source: choice: removing consent must take effect before later seat assignment

### C-68: A withdrawal that follows promotion leaves the booking untouched
Observable: If promotion takes effect before withdrawal, the withdrawal returns the booked outcome and the member can use the ordinary booking cancellation control.
Source: choice: leaving a queue and cancelling attendance have different effects

### C-69: Closure prevents a later promotion of an affected place
Observable: If disablement, operator removal, account closure, session cancellation or removal, departure from the booking window, scheduled start, or another existing session-wide closed state takes effect before promotion, the member receives no booking from that place. Any additional app-specific session-wide closed states are unconfirmed.
Source: choice: the outcome must respect the first action or time boundary that ends consent

### C-70: Session closure after promotion leaves the booking to ordinary booking rules
Observable: A promotion confirmed before a session is cancelled, removed, or rescheduled is handled by the existing confirmed-booking behavior for that change.
Source: implied: U-4 says the member receives a confirmed booking in the existing app

### C-71: A departure from the queue releases only that place's priority
Observable: If the head withdraws, is removed, or ends for ineligibility while a seat is open, the next still-active waiter gains priority. If no place remains active, the seat is available for ordinary booking.
Source: choice: the loss of one claim must not strand an open seat

### C-72: A withdrawal retry cannot withdraw a later place
Observable: Repeating a withdrawal for an ended place leaves any new place for the same member and session active. The caller sees the outcome of the original withdrawal or the current booking if promotion won the race.
Source: choice: a retry must apply to the originally selected place

### C-73: Retrying a prior join cannot create a new place
Observable: Retrying the same submission leaves its accepted place and order unchanged, even if that place since ended. The result exposes that submission's outcome if available. If it cannot be identified, a retry is refused and the member can check status before making a fresh join.
Source: choice: delayed retries must not renew consent or priority

### C-74: A late seat-opening report cannot promote against obsolete session state
Observable: Processing an old availability report after a seat was filled or the session stopped taking bookings does not create a booking against that report.
Source: choice: a seat-opening report may be delayed or duplicated

### C-75: An unavailable eligibility check is treated as a temporary promotion failure
Observable: If the app cannot obtain an authoritative eligibility result, the affected place remains active in order while the session remains open. The member is not classified as ineligible.
Source: choice: a service failure supplies no evidence about the member's eligibility

### C-76: Pending promotion resumes after a temporary failure
Observable: If the failure clears while the session is still open and a seat is still available, promotion resumes from the current head without the waiter requesting it again.
Source: choice: a transient failure should not force the operator or member to recreate the original event

### C-77: Promotion is attempted within 60 seconds while ordinary booking dependencies are available
Observable: If waitlisting stays effective, the session remains open, an open seat and an active queue persist, and services needed to book remain available, the operator sees a new attempt result within 60 seconds of those conditions first holding or the previous attempt resolving. Attempt results are confirmation, definitive eligibility refusal, or recorded temporary failure. The same bound applies when those conditions first hold after recovery.
Source: choice: a member waiting on an open seat needs eventual service with a concrete first-attempt bound

### C-78: Time boundaries are evaluated when a waitlist action takes effect
Observable: With a cutoff or scheduled start at 18:00 in the session's usual time context, a join or promotion taking effect at 18:00 or later is refused even if the request began before 18:00. No new place or promoted booking is produced by that attempt.
Source: choice: the applicable closing instant is exclusive and slow or delayed requests do not extend it

### C-79: Closing a waitlist place is final for that attempt
Observable: If an active place has ended because its session stopped taking bookings, reopening the session or moving its start later does not reactivate the old place.
Source: choice: a past request that already ended does not carry forward to a reopened booking window

### C-80: A still-open schedule edit preserves waiting priority for the same occurrence
Observable: If a schedule edit keeps the same occurrence open for booking, an active place keeps its priority. Promotion still uses current eligibility and the member's existing authorization.
Source: choice: keep queue continuity for the same bookable occurrence while respecting the app's existing session identity

### C-81: One effective end determines the recorded outcome of a waitlist place
Observable: A place ended by promotion, member withdrawal, operator removal, ineligibility, disablement, cancellation or removal, closure of the booking window or start, another existing session-wide closed state, a separate booking, or account closure keeps that recorded outcome when a later ending action is attempted. If two endings overlap, the app reports one consistent result to the member and operator.
Source: choice: overlapping endings must not create competing histories for the same place

### C-82: A confirmed booking obtained through another permitted path ends an active place for the same session
Observable: If an existing privileged booking path can legitimately confirm a seat for a member with an active place, their attempt ends as already booked and they lose queue priority. The member can find their booking through ordinary booking.
Source: choice: the queue must never consider a member who already received the requested seat

### C-83: An unavailable queue is distinguishable from an empty queue
Observable: If current queue data is unavailable, the operator sees that the queue could not be verified.
Source: choice: treating unavailable state as empty could bypass accepted places

### C-84: An operator can verify whether the deployed booking environment is ready for waitlisting
Observable: Before activation, the release operator can identify the actual booking platform and whether member identity and access checks, session and capacity reads, durable waitlist updates, ordinary booking confirmation, and automatic processing while no member is online are all available. The platform, its prerequisite permissions and configuration, and any restrictions on synchronous processing are unconfirmed.
Source: choice: the incoming request names a class booking app but supplies no application runtime, service inventory, or deployment configuration

### C-85: A platform timeout cannot produce a false mutation confirmation
Observable: If the deployed platform times out or interrupts a join, withdrawal, or promotion, a known recorded outcome can be retrieved after recovery. A response whose outcome cannot yet be verified reports uncertainty. The applicable request and background execution time limits are unconfirmed.
Source: choice: the actual platform is unidentified, so its timeout rule and bound cannot be stated as facts

### C-86: Platform admission limits are distinguishable from class capacity
Observable: If the platform refuses an operation because it exceeds a request size, queue or storage ceiling, or request rate, the caller sees a service-limit or temporary-unavailability result without a fabricated waiting place. The applicable categories and exact ceilings, rate windows and retry delays are unconfirmed.
Source: choice: an unidentified platform may impose hard limits even though the product sets no separate queue maximum

### C-87: Live activation requires the release's existing deployment prerequisites
Observable: The release operator can verify that the target environment satisfies its applicable production deployment prerequisites before waitlisting becomes available to its members. Target environments, required approvals, platform account or service permissions, and any distribution review are unconfirmed.
Source: choice: no existing production release rules or platform requirements were supplied

### C-88: The ordinary session schedule remains browsable under existing access rules
Observable: A caller can still find the class occurrences they were allowed to view before waitlisting was added.
Source: implied: the request adds a full-session action to the existing booking app

### C-89: Direct booking retains its ordinary confirmation behavior
Observable: For a session with a place available for ordinary booking, direct booking still produces the app's usual result and confirmation for that booking. The existing confirmation channels and details are unconfirmed.
Source: implied: U-2 uses the existing direct booking path

### C-90: Waitlisting does not change the applicable cancellation behavior for a confirmed booking
Observable: Members can use the existing cancellation path for direct or promoted bookings under the existing cutoff, fee or refund, and seat release rules where applicable. The actual deadlines, amounts and supported rules are unconfirmed.
Source: implied: U-4 starts with ordinary cancellation and U-3 ends with an ordinary confirmed booking

### C-91: Waiting does not count as attendance
Observable: An active waiter is absent from the confirmed attendance list and cannot check in using only a waitlist place, if the app supports attendance lists or check-in.
Source: implied: U-3 distinguishes waiting from a booking

### C-92: Waiting does not occupy a seat
Observable: A seat's occupied count does not increase when the waitlist accepts a join. It increases when an ordinary booking takes effect, including by promotion.
Source: implied: U-1 gives access to a queue while U-4 supplies a seat later

### C-93: Member waitlist responses reveal no identifiable information about other members
Observable: In the member waitlist view and member-facing responses, the caller sees no other waiter's identity, contact details, status, or identifiable booking details.
Source: choice: members need their own outcome to manage attendance

### C-94: A waiting member retains their place through an ordinary service restart
Observable: After the booking app becomes reachable again, an accepted place is still visible unless it legitimately changed or ended while the service was unavailable.
Source: implied: U-6 requires the caller to be able to recover an accepted outcome

### C-95: A waitlist retry cannot cause duplicate ordinary booking consequences
Observable: Retrying a promotion already confirmed creates no additional charge, entitlement consumption, or initial booking confirmation for that same booking, where the existing app performs those effects. The ordinary confirmation channels and entitlement or billing rules are unconfirmed.
Source: choice: duplicate processing must not double the member's cost or report an extra booking

### C-96: Joining a waitlist incurs no booking charge or entitlement consumption
Observable: An active waiter has no booking charge or redeemed class credit from the join itself. Ordinary applicable booking charges or credits can arise when a promotion confirms a booking under the authorized terms.
Source: choice: a member should incur booking consequences only for an actual booking

### C-97: Waitlisting does not bypass any member action indispensable to confirm a booking
Observable: If the existing booking terms require a new payment approval, a new waiver, or another interaction that cannot be authorized by the waitlist join, the app refuses the join where that requirement is known. The app-specific list of such requirements is unconfirmed.
Source: choice: automatic booking needs valid authority for the same consequences as an ordinary booking

### C-98: The system rechecks material booking terms before promotion
Observable: If terms requiring member consent have changed since the join, the app promotes only if the current terms fall within the member's existing authorization. Otherwise the place ends for ineligibility without an unauthorized charge or commitment. The app-specific terms requiring consent are unconfirmed.
Source: choice: waiting gives permission to act under authorized booking terms

### C-99: A member can learn the outcome without an added outbound channel
Observable: The member can read waiting, promotion, or closure information in the app. Waitlisting adds no email, SMS, or push requirement.
Source: choice: an in-app outcome satisfies the status need without requiring new contact permissions or delivery services

### C-100: Signing out or closing the app leaves a waiting place active
Observable: A member can join, close the app, and later find the current waitlist outcome after signing in again. A promotion can occur while the member is offline.
Source: choice: automatic promotion should not depend on the member keeping a session or device open

### C-101: Retained outcomes do not reveal later details of a session the member can no longer view
Observable: If permission changes, an outcome the member can still read contains their own join time and result plus the last session name and start they were authorized to see. It reveals no newer detail from the restricted session.
Source: choice: members need their own history while the app retains control of session visibility

### C-102: An ineffective waitlist imposes no additional seat priority
Observable: Where waitlisting is disabled, ordinary booking allocates available seats according to its original rules.
Source: implied: U-11 ends waitlisting for the affected scope

### C-103: A full-session booking refusal exposes the applicable waitlist action
Observable: If the last direct seat is taken before a member's booking succeeds, the response shows the join action when that member qualifies to join.
Source: choice: a member who arrives through an outdated availability view still needs the full-class option

### C-104: A repeated join while waiting returns the current place
Observable: A member submits a fresh join for the same occurrence while their earlier place is active. They see that they are already waiting with the existing priority, even if an open seat is being assigned.
Source: choice: a duplicate intent should help members find their existing place

### C-105: The member can reach their waitlist outcomes without reopening the session
Observable: A signed-in member can find their own retained waitlist attempts through an account-linked view after the session leaves the upcoming schedule. If they joined more than once, they can distinguish each attempt by when they joined and see its outcome.
Source: choice: closure and past results need to remain discoverable independently of the schedule

### C-106: Waitlist changes are scoped to the selected attempt
Observable: A member or operator attempting to remove a specific active place from an old view sees that attempt's recorded outcome if it already ended. A newer place for the same member and session is unaffected.
Source: choice: an old view must not be able to end consent given in a different attempt

### C-107: Permission refusals precede disclosure of waitlist status
Observable: An unauthorized caller receives the same refusal whether the named place is active, ended, or unknown.
Source: choice: a refusal must not reveal a place to someone who lacks permission to see it

### C-108: A closed member account cannot receive a promotion
Observable: Where the app supports permanent account closure, an active place ends when closure takes effect and can no longer produce a booking. Any retained outcome is subject to the app's existing account closure and retention rules.
Source: choice: a closed account no longer provides a bookable member identity

### C-109: Loss of session eligibility prevents promotion
Observable: A waiter who loses session visibility or another required booking permission before the booking takes effect is refused at promotion. If the refusal is authoritative, the place ends for ineligibility.
Source: choice: access is a booking condition at the point of admission

### C-110: Moving a session outside its booking window ends outstanding waiting
Observable: If an edit moves the opening time into the future or the cutoff or scheduled start to the present or earlier, the active place ends when the edit makes the session unavailable. It does not revive when booking opens again.
Source: choice: going from open to closed ends existing waiting, even when caused by a schedule edit

### C-111: An in-flight join cannot survive an intervening disablement
Observable: A join submitted before disablement that has yet to take effect is refused if its processing spans that disablement, even if the feature was re-enabled in the meantime. A member can submit a fresh join after re-enablement.
Source: choice: disabling waitlisting cancels outstanding consent to enter the queue in the affected scope

### C-112: Retrying a setting change does not undo a later successful setting change
Observable: A repeat of the original operator submission returns its applied outcome if available. If it cannot verify the submission, it reports uncertainty. A repeat does not overwrite a different setting value applied later.
Source: choice: a lost response must not turn a stale operator instruction into a new change

### C-113: An operator can distinguish outstanding seat allocation from a resolved outcome
Observable: For a seat allocation that began with an open seat and applicable queue priority, the operator can see either that assignment is pending, that it is blocked by a temporary failure, or its resolved outcome. Resolutions are booking confirmed, queue emptied with the seat still open, and opportunity ended because the seat stopped being open or the session stopped serving its queue.
Source: choice: the operator needs to tell a failure still blocking the seat from a completed or obsolete attempt

### C-114: A promotion needs no separate manual assignment to finish after recovery
Observable: If a booking already took effect before processing was interrupted, after recovery the member sees that same booking linked to the promoted outcome. The app does not reallocate that place to a different member based on the interruption.
Source: choice: recovery must reconcile a completed booking before making another allocation

### C-115: A capacity reduction cannot add a waitlist booking above the new capacity
Observable: If a capacity change puts existing occupancy at or beyond the new limit, the waitlist confirms zero additional bookings until existing booking rules report an open seat. Existing over-capacity bookings are handled by the app's ordinary capacity-edit behavior, which is unconfirmed.
Source: choice: waitlisting must honor the edited capacity without adding a new policy for confirmed bookings

### C-116: Session timing for promotion follows the app's session clock
Observable: Two members in different device time zones reach the same booking cutoff for the same occurrence. The app's existing interpretation of dates, offsets, and daylight saving changes applies, and its exact time conventions are unconfirmed.
Source: choice: a device clock or display setting cannot extend admission

### C-117: The app makes any applicable booking commitment visible before an automatic booking is authorized
Observable: Before joining, the member can see the applicable session, automatic booking behavior, and any price, class-credit use, cancellation deadline, fee, or refund terms the ordinary booking path requires them to accept. The complete app-specific list of commitments is unconfirmed.
Source: choice: the same consent needs to cover a direct booking or a later automatic booking

### C-118: An ended place can be replaced only by a fresh eligible join
Observable: After any outcome that ends the original place, a later join for that same occurrence starts at the back if all current join conditions are met. This includes having no confirmed booking for that occurrence.
Source: choice: all new attempts use current admission conditions and fresh priority

### C-119: A waitlist places no extra cap on the number of sessions a member may wait for
Observable: An eligible member can hold active places in different sessions at the same time. Existing restrictions on which bookings the member can hold still apply at promotion, including when multiple sessions offer seats concurrently.
Source: choice: class-specific requests need no new account-wide cap

### C-120: Restoring the waitlist release does not enable it automatically
Observable: After a rollback followed by reinstalling the waitlist release, the restored feature is disabled app-wide until an authorized operator enables it.
Source: choice: reinstalling should not silently reverse the explicit stop used to roll back

### C-121: Unverified queue priority temporarily blocks direct seat allocation
Observable: When waitlisting is effective and the app cannot determine whether an open seat has waitlist priority, an ordinary booking attempt for that seat reports temporary unavailability. Once priority can be determined, the usual seat allocation rule applies.
Source: choice: existing claims need protection during a queue read failure

### C-122: A failed promotion does not reverse a successful cancellation
Observable: A booking cancellation that frees a seat remains in effect if promotion fails afterward. The cancelling member can still see the cancellation in the ordinary booking view.
Source: implied: U-4 starts with ordinary cancellation, whose result is independent of another member taking the seat

### C-123: Promotion follows the app's ordinary booking confirmation channels
Observable: If the app normally sends an email, SMS, push, or other confirmation for an ordinary booking under the applicable member settings, it uses the same applicable channel and settings for a promoted booking. The supported channel list and delivery behavior are unconfirmed.
Source: choice: a promoted booking should reach the member through the established booking confirmation behavior

### C-124: A confirmation delivery failure does not undo a promoted booking
Observable: If ordinary confirmation cannot be delivered after a booking takes effect, the member can still see the confirmed booking and the promoted outcome in the app.
Source: choice: delivery and the seat commitment have different outcomes

### C-125: A booking dependency failure cannot let a later waiter take the head's place
Observable: While the app cannot determine or complete the current head's booking for a temporary reason, a later waiter cannot receive the same open seat ahead of that member. A definitive eligibility refusal or another legitimate end releases that priority.
Source: choice: an outage should not alter the order members earned

### C-126: An unconfirmed settings save gives the operator a way to check what applied
Observable: If a settings save cannot be confirmed, the operator sees a known failure or an uncertain result. Once the settings view is reachable, they can read the applied value before retrying.
Source: choice: an interrupted save may have applied before its response was lost

### C-127: Rollback readiness cannot be reported when it is unverified
Observable: If the release operator cannot verify global disablement, zero active places, or zero promotions still able to take effect, the app reports rollback readiness as unconfirmed.
Source: choice: switching to the previous release can otherwise bypass an active commitment

### C-128: A completed operator correction is visible in waitlist history
Observable: An operator who corrected a promoted booking can follow the promoted attempt to the booking's resulting ordinary status while that history remains available.
Source: choice: a correction must be traceable without changing whether a promotion originally happened

### C-129: A newly required member action prevents an automatic booking
Observable: If a new payment approval, new waiver, or other indispensable member action becomes necessary after the join and has not been satisfied, promotion handles that result as an eligibility refusal. The app-specific interaction list is unconfirmed.
Source: choice: a prior join cannot replace consent or action newly required for a booking

### C-130: Booking a session cannot silently enroll the caller in its waitlist
Observable: An ordinary booking attempt that misses a seat leaves the caller with no new waitlist place until they submit a join.
Source: choice: waitlist enrollment authorizes a future booking and needs a separate decision

### C-131: Waitlist availability is checked on every supported booking path
Observable: Every ordinary path to book a session gives the same effective queue priority. A pre-existing operator-only exception, if any, remains limited to its existing authority and does not gain a new waitlist bypass.
Source: choice: members must receive the same seat allocation regardless of entry point, with existing privileged exceptions unconfirmed

### C-132: A disabled or closed session cannot show an actionable join after a successful refresh
Observable: A refresh that successfully reads the current session state omits the join action if the session fails any applicable opening condition: effective waitlist enablement, opening time, cutoff, start, cancellation, schedule removal, or another existing session-wide booking closure, whose complete list is unconfirmed.
Source: choice: an actionable control should reflect the current session's ability to admit waiters

### C-133: Other existing session-wide closures block new waitlist places
Observable: If the app offers a session-wide booking closure distinct from cancellation, removal, the booking window and scheduled start, a join during that closure is refused. The complete list of additional app-specific closed states is unconfirmed.
Source: choice: an operator's existing way to close a class to booking must also stop new waiting

### C-134: A refreshed waitlist outcome reflects visible edits to the occurrence
Observable: After a successful refresh, an outcome for a session the member can still view displays its current class name and scheduled start.
Source: choice: a waiting member needs the current occurrence details under the same visibility rules

### C-135: A failed status read is distinguishable from having no waitlist place
Observable: When the app cannot retrieve the member's waitlist outcome, the member sees temporary unavailability. A previously shown outcome may remain visible if identified as unverified.
Source: choice: a member checking an interrupted action should be able to distinguish an unreadable result from an absent place

### C-136: An interrupted operator removal reports its outcome as uncertain until verified
Observable: If the operator cannot tell whether removal took effect, the app shows that uncertainty for the selected place. On recovery the operator can check that place's outcome before retrying.
Source: choice: correction must target the original request even if a member rejoins before the operator receives a result

### C-137: An uncertain booking commit prevents reassignment of the same potential seat
Observable: If the app cannot verify whether a promotion confirmed, a competing request for the affected seat cannot consume it while the result is uncertain. Once verified, the seat counts as taken by that booking or returns to the applicable seat allocation path.
Source: choice: an unknown response can conceal a successful commitment and must not allow a second claim

### C-138: A failed promotion cannot leave a booking charge or entitlement consumption in place
Observable: If the ordinary booking service initiates a charge or class-credit redemption but promotion ultimately fails without a booking, the member sees it voided, released, or restored under the existing booking failure rules. The applicable compensation methods and their completion times are unconfirmed.
Source: choice: automated confirmation must leave the member with the same financial outcome as a failed direct booking
