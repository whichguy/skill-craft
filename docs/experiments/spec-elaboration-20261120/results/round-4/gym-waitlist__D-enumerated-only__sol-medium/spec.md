## Use cases

### U-1: Member joins the waitlist to keep a chance at a spot
Flow: Open a bookable occurrence whose seats are all taken, choose to join, and see that the request is waiting. The first member can join an empty queue. An existing member who tries again sees their current entry.
Source: request

### U-2: Member books an available spot to attend a class
Flow: Open an occurrence with an available seat and book it under the existing rules. If the seat is taken before booking completes, the member can choose to join the waitlist if still eligible.
Source: implied: a waitlist for full classes complements the existing booking flow

### U-3: Waitlisted member checks status to know whether they have a seat
Flow: Return to the app as the same member. See whether they are still waiting, have been booked, or have stopped waiting. An operator can also inspect the occurrence when investigating a report.
Source: implied: joining a waitlist makes a seat possible later

### U-4: Waitlisted member leaves to stop waiting
Flow: Open their waiting entry and withdraw. A repeated withdrawal leaves it withdrawn. If a seat was already assigned, the member sees the booking and uses the ordinary booking cancellation action if they want to give it up.
Source: implied: members can change plans while waiting

### U-5: Waitlisted member receives a released seat to attend the class
Flow: A cancellation or capacity increase makes a seat available while booking is open. Eligible queued members receive available seats in join order and can see their bookings in the app.
Source: implied: the waitlist gives people a way into full classes

### U-6: Member handles an invalid request to learn whether anything changed
Flow: Try to join a missing, inaccessible, canceled, closed, or already-booked occurrence, or try to withdraw somebody else's entry. See the applicable refusal or existing personal status. No new entry is created by a failed join.
Source: implied: U-1 and U-4 require valid targets and actors

### U-7: Member retries after a failure to confirm their status
Flow: If a join or withdrawal fails or its result is lost, return to the occurrence or retry. See the committed status once the app can read it again.
Source: implied: U-1 and U-4 can encounter outages

### U-8: Operator starts or pauses intake to manage waitlist availability
Flow: Use the waitlist intake control. Pausing blocks new joins and leaves existing waiting entries eligible for seats. Resume to accept joins for eligible full occurrences.
Source: implied: operating a waitlist requires a way to start and stop intake

### U-9: Operator changes class capacity to manage available seats
Flow: Use existing capacity controls. Added seats can go to waiting members while booking remains open. Reducing capacity does not itself cancel confirmed bookings.
Source: implied: capacity determines whether a class is full

### U-10: Operator closes or cancels an occurrence to end waiting for it
Flow: Use the existing booking close or class cancellation action. Members still waiting stop waiting. A later reopening allows new joins and does not restore prior waiting entries.
Source: implied: waiting needs an end when there is no longer a seat to assign

### U-11: Operator inspects waitlists to answer support questions
Flow: Open an occurrence the operator manages. See its intake availability, who is waiting, their order, and outcomes of earlier joins. An occurrence with no entries shows an empty list.
Source: implied: operator work includes observing waitlist activity

### U-12: Operator recovers from allocation interruptions to restore progress
Flow: When service returns, inspect the occurrence. Eligible waiting members receive seats still available under the same rules, including when a previous attempt committed before contact was lost.
Source: implied: U-5 has to survive interruptions

### U-13: Operator enables the feature to serve existing occurrences
Flow: After rollout, existing classes and bookings are visible. An existing eligible full occurrence can accept its first waitlist join once intake is enabled.
Source: implied: the class booking app already exists

### U-14: Operator rolls back the feature to restore ordinary booking
Flow: Pause intake and close outstanding waiting entries before withdrawing waitlist access. Existing confirmed bookings remain usable. Re-enabling starts with no restored waiting entries.
Source: implied: returning to the earlier version must account for waitlist-created state

### U-15: Member joins a long waitlist to keep a chance at attendance
Flow: Join even if others are already waiting. If service cannot accept a request, see failure or an unknown outcome and use the app to verify the result when service returns.
Source: implied: a full class can attract many waiting members

## Clauses

### C-1: A member can join a waitlist for a full class occurrence
Observable: A member otherwise eligible to book an open occurrence with no free seat can register interest for it.
Source: request

### C-2: Joining leaves the member without a confirmed seat while they are waiting
Observable: After a join that has not led to a seat assignment, the member sees a waiting status distinct from a confirmed booking.
Source: implied: U-1

### C-3: A waiting entry can lead to a confirmed seat
Observable: When a seat is released while booking remains open and the only waiting member is eligible, that member can obtain the seat through the waitlist.
Source: implied: U-5

### C-4: A member opts into the waitlist
Observable: A failed direct booking does not create a waiting entry without a separate affirmative join action.
Source: choice: a waitlist may result in a booking, so the member chooses whether to wait

### C-5: Eligible waiting members are booked automatically
Observable: A waiting member receives a confirmed booking when they become next for an available seat. No claim or response is required.
Source: choice: avoid leaving seats unused during an offer window

### C-6: Earlier joins have priority
Observable: When two eligible members are waiting for one seat, the member whose join was accepted first gets it.
Source: choice: accepting requests in order gives members predictable priority

### C-7: A member can check their current waitlist status in the app
Observable: Returning to the occurrence shows the member their status as waiting, booked through the waitlist, withdrawn, or ended without booking, when applicable.
Source: choice: the app itself provides the outcome without requiring an external delivery channel

### C-8: A waiting member can withdraw
Observable: A member can end their own active waitlist participation before it becomes a booking.
Source: choice: plans can change before a seat opens

### C-9: A repeated join preserves the existing active entry
Observable: Two join actions by the same member for the same occurrence while already waiting leave one active entry in its original place.
Source: choice: retries should preserve the member's place

### C-10: Ordinary booking remains available when a seat is free for direct booking
Observable: A member can confirm a seat through the existing booking flow when there is capacity available for direct booking and ordinary eligibility rules permit.
Source: implied: U-2

### C-11: Intake can be paused for the app
Observable: An authorized operator can pause new waitlist joins across all occurrences with one control.
Source: choice: one app-wide control covers rollout and rollback

### C-12: Intake can be enabled for the app
Observable: An authorized operator can open intake for all eligible occurrences with one control.
Source: choice: one app-wide control is sufficient to start or resume

### C-13: Pausing intake preserves eligibility for existing waiting entries
Observable: With intake paused, a release still books the next eligible member who joined before the pause.
Source: choice: pausing intake honors commitments already accepted

### C-14: No waitlist-specific length cap applies
Observable: An eligible join is accepted even with many members already waiting, subject to service availability. There is no configured maximum number of waiting members per occurrence.
Source: choice: the request aims to serve people after capacity is reached

### C-15: Waitlists can be inspected by authorized operators
Observable: An operator who can manage an occurrence can open that occurrence's waitlist view.
Source: choice: operators need to diagnose outcomes

### C-16: Allocation resumes after a recoverable outage
Observable: After a transient interruption ends, an eligible waiting member receives a seat that is still available for them, without rejoining.
Source: choice: accepting a waitlist join commits the service to continue processing it

### C-17: Existing occurrences can receive waitlist joins
Observable: After enablement, an otherwise eligible full occurrence created before rollout can accept a join.
Source: implied: U-13

### C-18: Outstanding waits end on feature rollback
Observable: Before withdrawing waitlist access during rollback, the operator ends remaining active waits with a feature withdrawal outcome.
Source: choice: rolling back should resolve existing waitlist commitments

### C-19: A confirmed booking survives feature rollback
Observable: A member booked through the waitlist keeps that booking when waitlist access is withdrawn.
Source: implied: U-14

### C-20: Each waitlist belongs to one scheduled occurrence
Observable: Joining one date or time of a recurring class leaves the status for its other occurrences unchanged.
Source: choice: a seat belongs to a scheduled occurrence

### C-21: A class occurrence needs a valid reference for a join
Observable: A join using a missing, malformed, or unknown occurrence reference produces no entry.
Source: implied: U-6

### C-22: A join requires the member's authenticated identity
Observable: A caller without an authenticated member account cannot create a waiting entry.
Source: choice: require an authenticated booking identity so the member can recover and manage a wait

### C-23: A withdrawal requires the member's authenticated identity
Observable: An unauthenticated request cannot withdraw an entry.
Source: choice: use the booking identity to verify ownership before withdrawing

### C-24: An operation on an inaccessible occurrence does not disclose its existence
Observable: The app does not distinguish an inaccessible occurrence from an unknown one to a caller who lacks view permission.
Source: choice: waitlist actions follow the existing visibility boundary

### C-25: A member can find the waitlist from the existing occurrence view
Observable: An eligible member looking at a full open occurrence can reach the join action from that occurrence when intake is enabled.
Source: choice: use the existing occurrence view to make waiting discoverable

### C-26: A class is full when zero seats are available for direct booking
Observable: Capacity available for direct booking is configured capacity minus confirmed seats, existing holds counted under C-27, and seats owed to the queue under C-71, with zero as the floor.
Source: choice: capacity may be reduced below the number already confirmed

### C-27: Existing seat holds count when the booking app treats held seats as unavailable
Observable: The waitlist uses the ordinary booking app’s treatment of existing holds, including their release or expiry. A seat is counted once if an existing hold becomes its confirmed booking.
Source: choice: preserve existing seat commitments while allowing demand to queue

### C-28: Joining checks ordinary booking eligibility apart from lack of capacity
Observable: A member who would be refused an available seat under a non-capacity booking rule also cannot join. The exact app-specific eligibility rules are unconfirmed because the booking app is absent from the workspace. The waitlist introduces no eligibility exemptions.
Source: choice: joining should not bypass booking rules

### C-29: A member with a confirmed booking for the occurrence cannot create a waiting entry for it
Observable: An already-booked member sees that they have a seat if they request to join.
Source: implied: U-1 and U-6

### C-30: A member can have at most one active waiting entry per occurrence
Observable: After any number of successful join requests by the same member for one occurrence, at most one entry is waiting at a time.
Source: choice: one member needs one place in line

### C-31: A canceled occurrence refuses joins
Observable: Attempting to join a canceled occurrence creates no entry.
Source: choice: a cancellation ends the opportunity to attend

### C-32: An occurrence outside its booking window refuses joins
Observable: Before ordinary booking opens or once it closes, no new waiting entry can be created. The opening and closing offsets are unconfirmed and follow the existing booking window for that occurrence.
Source: choice: waitlist admission follows the ordinary booking window

### C-33: Paused intake refuses new joins
Observable: An otherwise eligible member who is not waiting cannot start waiting while intake is paused.
Source: choice: the operator's intake control must take effect on admission

### C-34: A free uncommitted seat routes an eligible prospective joiner to ordinary booking
Observable: If the occurrence has a seat available for direct booking when the member attempts to join, the attempt does not create an entry and the member can use ordinary booking.
Source: choice: the waitlist addresses unavailable seats

### C-35: Losing a direct booking race exposes the waitlist option
Observable: When a booking attempt fails because the last available seat was taken, the member can reach the join action if eligible and intake is open.
Source: implied: U-2

### C-36: A refused operation leaves unrelated entries unchanged
Observable: After a refused join or withdrawal, other members retain their existing waitlist entries.
Source: implied: U-6

### C-37: A previously withdrawn member can join again
Observable: A member who withdrew can join again if current admission rules permit.
Source: choice: members can change their plans without retaining a released place

### C-38: A member whose turn ended may join again if eligible
Observable: After a prior wait ended without a booking, the member may start a new wait if the target is again accepting their join under current rules.
Source: choice: ended waits do not bar a fresh request

### C-39: A waitlist booking that is later canceled permits a fresh join
Observable: A member whose promoted booking was canceled can join again if current admission rules permit.
Source: choice: eligibility follows the current booking rather than past attendance plans

### C-40: A fresh join supersedes prior waitlist outcomes in the member's current view
Observable: A member who joins again sees the latest entry's status in their current waitlist view.
Source: choice: the current screen should communicate the member's actionable state

### C-41: The member can distinguish an ordinary booking from waiting
Observable: The ordinary booking view shows a confirmed seat only when the member actually has a live booking for the occurrence.
Source: implied: U-2 and U-3

### C-42: A member with no entry has no personal waitlist status
Observable: On an occurrence for which the member never joined, the app does not present them as waiting, withdrawn, booked through the waitlist, or ended.
Source: implied: U-3

### C-43: A member's status identifies the occurrence
Observable: A member checking a status can associate it with the same occurrence shown in ordinary booking, even when there are several occurrences of the same class.
Source: implied: U-3

### C-44: A member can verify waiting status without relying on a numeric rank
Observable: A member can tell whether their entry is waiting from its status alone.
Source: choice: eligibility changes can affect the order in which seats are assigned

### C-45: The member view identifies what ended an unfulfilled wait
Observable: An ended entry shows whether the wait ended because booking closed, the occurrence was canceled, the member was no longer eligible at allocation, the member already had a seat from another path, or the feature was withdrawn.
Source: choice: the member should know why the wait ended without receiving other members' details

### C-46: Leaving an active wait reports withdrawal
Observable: After a successful withdrawal, reading the entry shows withdrawn.
Source: choice: make withdrawal observable without prescribing presentation

### C-47: A repeated withdrawal does not modify a withdrawn entry
Observable: Repeating withdrawal for the same entry leaves its outcome withdrawn.
Source: choice: repeated requests should be safe

### C-48: A withdrawal without a matching personal entry does not create one
Observable: A request to withdraw an unknown entry leaves the requester's occurrence without a new entry.
Source: implied: U-4 and U-6

### C-49: A withdrawal cannot target another member's entry
Observable: Attempting to withdraw another member's entry changes neither their place nor their outcome.
Source: implied: U-4

### C-50: Only an authorized operator can change app-wide intake
Observable: A caller without the app's authority to manage booking configuration cannot enable or pause intake.
Source: choice: the global control changes admission for every occurrence

### C-51: An operator can inspect effective intake for an occurrence
Observable: The operator sees whether the occurrence can accept new joins, with an applicable reason when it cannot: app intake paused, feature withdrawal in progress, booking not yet open, booking closed, occurrence canceled, or a free seat available for ordinary booking.
Source: choice: operators need to know which current condition governs admission

### C-52: An operator can identify the owner of an entry
Observable: The waitlist view identifies each entry's member using the identity already available to that operator for class bookings. Contact details are omitted from the waitlist view because inspecting a queue does not require them.
Source: choice: existing identity is sufficient to investigate waitlist outcomes

### C-53: An operator can see the order of waiting entries
Observable: For an occurrence with active entries, the operator can identify which members are ahead of which other active members.
Source: choice: support needs to explain allocation priority

### C-54: An operator can see completed entry outcomes
Observable: The occurrence's waitlist view can show withdrawn, booked through the waitlist, and ended without booking, with the reason from C-45 for an ended wait.
Source: choice: completed outcomes let operators investigate reported issues

### C-55: An operator sees an empty waitlist when there have been no joins
Observable: Opening the waitlist view of an occurrence with no entries shows that there are no entries.
Source: choice: distinguish an empty operator view from failure to retrieve entries

### C-56: The waitlist introduces no manual reordering control
Observable: Operators can inspect order but cannot use the waitlist to move an entry ahead of another.
Source: choice: join order should remain predictable

### C-57: The waitlist introduces no manual per-member enrollment control
Observable: The operator cannot add members to the waitlist on their behalf from the waitlist view.
Source: choice: automatic booking requires a member's affirmative join

### C-58: The waitlist introduces no manual per-member allocation control
Observable: Operators cannot force a promotion through the waitlist view.
Source: choice: ordinary lifecycle and intake controls cover the requested operations

### C-59: A member can obtain the waitlist outcome without an external notification
Observable: The app's member view shows the resulting status even if the member has no email address, push subscription, or SMS number.
Source: choice: status in the booking app is sufficient for the baseline feature

### C-60: Existing waitlist outcomes remain visible while their occurrence remains available to the viewer
Observable: While the feature remains installed and the viewer retains access to the occurrence's records, a completed outcome can still be inspected. Exact retention duration is unconfirmed and follows the existing occurrence record lifecycle.
Source: choice: outcome history should last as long as it remains useful in the occurrence context

### C-61: New deployments start with app-wide intake paused
Observable: Before an operator enables intake for the first time, an eligible full occurrence does not accept joins.
Source: choice: give the operator control over when the feature starts

### C-62: Reopening an occurrence does not restore closed entries
Observable: Members whose waits ended on closure must join again if they want to wait after reopening.
Source: choice: someone who was told they stopped waiting should not be booked without a new opt-in

### C-63: A capacity increase can make a seat available for allocation
Observable: Increasing capacity above occupied seats while booking remains open lets an eligible waiting member receive a booking.
Source: implied: U-5 and U-9

### C-64: A confirmed booking cancellation frees only the seat released by that booking
Observable: Canceling a booking creates a new opportunity only if confirmed bookings and applicable holds now occupy fewer seats than capacity.
Source: choice: a cancellation may merely reduce an existing over-capacity count

### C-65: Releasing an existing hold can make a seat available for allocation
Observable: If an existing hold ends and its seat becomes available for ordinary booking, eligible waiting members can receive it.
Source: choice: allocation follows effective seat availability

### C-66: Lowering capacity does not revoke an existing booking
Observable: A confirmed member retains their booking after capacity is reduced, including when confirmed bookings exceed the new capacity.
Source: choice: changing capacity should not cancel attendance already confirmed

### C-67: Capacity reductions govern subsequent allocations
Observable: Once a lower capacity takes effect, outstanding allocations cannot create a new confirmed booking beyond it.
Source: choice: uncommitted work must respect current capacity

### C-68: One released seat confirms at most one additional booking
Observable: With several eligible people waiting and one available seat, at most one receives a booking from that release.
Source: implied: U-5 allocates actual seats

### C-69: Several released seats go to successive eligible waiting members
Observable: With three available seats and four eligible waiting members, the first three in acceptance order receive bookings and the fourth stays waiting.
Source: choice: allocate all available seats in queue order

### C-70: Unused seats return to ordinary booking when the active queue is exhausted
Observable: If two seats become available and the only waiting member receives one, the remaining seat is available to ordinary booking.
Source: choice: capacity beyond the queue belongs to ordinary booking

### C-71: A direct booking cannot take capacity owed to a waiting member
Observable: Once an eligible member is waiting, a later direct booking cannot take a newly available seat that the waiting member is entitled to receive, including while automatic allocation is pending.
Source: choice: delay should not let a new arrival jump the queue

### C-72: Every way to create a new confirmed booking respects outstanding waitlist priority
Observable: Member self-service, staff booking on behalf of a member, and any other existing booking entry point all honor C-71. Exact existing entry points are unconfirmed. An entry point that merely modifies attributes of an existing booking without freeing or consuming a seat does not allocate capacity.
Source: choice: allocation priority must hold regardless of the booking surface

### C-73: Simultaneous joins produce a single stable acceptance order
Observable: If two eligible members join when one is not observably accepted before the other, the operator sees a definite order that is retained for later allocation.
Source: choice: simultaneous joins still need an unambiguous priority

### C-74: An accepted join participates in the next seat decision
Observable: If a join takes effect before a seat opens, that member participates in allocation of that seat. If the seat is available for direct booking when the join takes effect, C-34 applies.
Source: choice: admission and release must agree on which happened first

### C-75: A withdrawal that takes effect first excludes that entry from assignment
Observable: If withdrawal completes before assignment takes effect, the withdrawn member does not receive the seat from that entry.
Source: implied: U-4

### C-76: An assignment that takes effect first leaves a booking to cancel
Observable: If assignment wins a race with withdrawal, the late withdrawal leaves the booking active and the member is shown the booking outcome.
Source: choice: a waitlist action and a booking cancellation represent different intents

### C-77: A withdrawal can release a pending opportunity to the next member
Observable: When the first waiting member withdraws while a seat is free and their booking has not taken effect, the next eligible waiting member can receive the seat.
Source: choice: withdrawal should not strand a free seat

### C-78: Allocation checks current booking eligibility before confirming a seat
Observable: A member who has become ineligible under ordinary non-capacity booking rules since joining does not receive the seat. The specifics of those rules remain unconfirmed under C-28.
Source: choice: admission is not a permanent entitlement to a booking

### C-79: A definitively ineligible entry ends at allocation
Observable: When the next waiting member is evaluated for a seat and current eligibility rules definitively refuse them, the entry ends with the ineligible outcome.
Source: choice: an ineligible member must not consume a turn indefinitely

### C-80: Allocation proceeds past an entry that already has a confirmed seat
Observable: If the next member gained a seat through an existing operation since joining, no second booking is made and their wait ends with the already-booked outcome.
Source: choice: an existing seat resolves that member's reason to wait

### C-81: Eligibility loss does not cancel a wait before it is considered for a seat
Observable: A member who temporarily loses eligibility and regains it before their entry is considered keeps the original priority, provided the occurrence remains open and the entry has not otherwise ended.
Source: choice: assess current eligibility at the point it matters

### C-82: An unresolved eligibility check preserves the entry
Observable: If the booking service cannot determine whether the next member qualifies, that member remains waiting in the same place.
Source: choice: a service failure is not a member refusal

### C-83: An unresolved earlier entry retains priority over later applicants
Observable: If an eligibility or booking dependency prevents deciding the first waiting member's turn, the service does not give that member's potentially assignable seat to a later waiting member or a direct booker.
Source: choice: temporary failure should not change queue order

### C-84: A seat assignment exposes a booking only after it takes effect
Observable: If booking creation fails before commitment, the member's wait cannot be shown as booked through the waitlist.
Source: implied: U-3 and U-7

### C-85: A committed assignment resolves exactly one waiting entry
Observable: After a seat assignment commits, the same entry is shown as booked through the waitlist and is no longer eligible for allocation.
Source: implied: U-5

### C-86: Retrying allocation after an uncertain result does not create a second booking
Observable: If a booking committed before the service lost the result, the recovered view shows one booking from that entry after retry.
Source: choice: recovery must respect an assignment that already took effect

### C-87: Closing booking ends active waits
Observable: When ordinary booking closes, every still-waiting entry for the occurrence ends with booking closed as the reason.
Source: choice: waiting uses the same closing boundary as ordinary booking

### C-88: Canceling an occurrence ends active waits
Observable: When the occurrence is canceled, every still-waiting entry ends with occurrence canceled as the reason.
Source: implied: U-10

### C-89: Closure before assignment prevents that assignment
Observable: If ordinary booking closes before an allocation takes effect, the requester cannot receive a booking from that allocation.
Source: choice: ordinary booking closure applies equally to uncommitted assignments

### C-90: Class cancellation before assignment prevents that assignment
Observable: If class cancellation takes effect first, a pending allocation cannot confirm a new booking for that occurrence.
Source: implied: U-10

### C-91: An assignment before class cancellation follows existing class-cancellation behavior
Observable: If promotion commits before the class is canceled, the resulting booking receives the same subsequent treatment as an ordinary confirmed booking.
Source: choice: a waitlist booking has the same standing as an ordinary booking

### C-92: Closure preserves completed entry outcomes
Observable: Closing or canceling the occurrence leaves already withdrawn, booked through the waitlist, and ended entries' historical outcomes intact while they are available under C-60.
Source: choice: history describes events that already happened

### C-93: Paused intake governs joins as soon as it takes effect
Observable: A new join accepted before a pause remains active. A new join evaluated while that pause remains in effect is refused.
Source: choice: there is one clear boundary for intake changes

### C-94: Duplicate joins remain safe while intake is paused
Observable: A member retrying a join that already left them waiting can confirm the existing entry while intake is paused.
Source: choice: pausing intake should not turn confirmation of an earlier action into a refusal

### C-95: A duplicate join for a live promoted booking returns the existing booking outcome
Observable: If a member repeats a join that produced a booking that is still confirmed, the app reports that they have a seat.
Source: choice: a retry after promotion should confirm the successful outcome

### C-96: A distinct fresh join after a resolved entry is evaluated under current rules
Observable: After withdrawal, an ended wait, or cancellation of a promoted booking, an affirmative new join request can create a new entry if eligible.
Source: choice: a new decision is separate from retrying an old action

### C-97: A delayed copy of an old join cannot start a new wait
Observable: If the same join action is replayed after its entry already became withdrawn, booked through the waitlist, or ended, that replay does not create a fresh waiting entry.
Source: choice: an old request is not new consent

### C-98: A delayed withdrawal cannot remove a newer entry
Observable: If a withdrawn member rejoins and the original withdrawal arrives again, the new entry remains active.
Source: choice: withdrawal is directed at the wait the member selected

### C-99: An unconfirmed write is distinguishable from a successful action
Observable: If the service cannot tell whether a join or withdrawal took effect, any response shown identifies the outcome as unknown and lets the member verify current status when service returns.
Source: choice: a dropped result is not proof of success or failure

### C-100: A failed join before commitment leaves no waiting entry
Observable: If service rejects or interrupts a join before it takes effect, a later successful read shows no entry from that attempt unless a retry subsequently took effect.
Source: implied: U-7

### C-101: A failed withdrawal before commitment leaves the wait intact
Observable: If a withdrawal fails before it takes effect and no other action changes the entry, a later successful read shows it still waiting.
Source: implied: U-7

### C-102: An unavailable status read is distinguishable from absence of an entry
Observable: During a status lookup failure, the app does not report that the member has no entry simply because it cannot retrieve it.
Source: choice: failure to read should not be confused with an empty result

### C-103: An unavailable operator read is distinguishable from an empty queue
Observable: When the operator view cannot read an occurrence's waitlist, it reports unavailability rather than an empty list.
Source: choice: the operator must be able to tell whether recovery is needed

### C-104: A failed intake change has no effect before it takes effect
Observable: When an intake change fails before commitment, the previous effective intake setting still governs admission.
Source: implied: U-8

### C-105: An uncertain intake change can be verified by reading effective intake
Observable: After an interrupted intake change, the operator can check whether app-wide intake is enabled or paused once service returns.
Source: choice: operators need to distinguish a failed update from a lost confirmation

### C-106: The operator can repeat an intake setting safely
Observable: Repeated requests to set intake enabled leave it enabled, and repeated requests to set it paused leave it paused.
Source: choice: recovery should set a known state

### C-107: Rollback termination prevents pending assignments from booking ended entries
Observable: Once an entry is ended during rollback, a delayed allocation cannot book that entry.
Source: choice: feature withdrawal is final for the outstanding wait

### C-108: Waitlist entries from before rollback do not resume on re-enable
Observable: After the feature returns, members with pre-rollback entries ended without a seat must opt in again to wait.
Source: choice: no member should receive a booking after being released from waiting

### C-109: Waitlist access follows the booking app's supported environments
Observable: A member can use the waitlist from the environments that expose the existing class booking flow. The host runtime, minimum supported client versions, and supported environment list are unconfirmed because no app or deployment details were supplied.
Source: choice: waitlist access belongs alongside booking, with host compatibility rules unconfirmed

### C-110: A runtime deadline cannot turn an unconfirmed action into a success
Observable: If a runtime request deadline interrupts a join, withdrawal, or intake change, the app only confirms it when commitment is known. The runtime deadline and exact duration are unconfirmed.
Source: choice: the outcome must remain truthful under any host request deadline

### C-111: A runtime workload limit cannot silently discard accepted waits
Observable: If a runtime work or batch ceiling interrupts processing of a long queue, outstanding entries retain their current outcomes and any unfinished allocations remain eligible for recovery. The applicable workload rules and exact ceilings are unconfirmed.
Source: choice: host processing limits cannot negate an accepted join

### C-112: Automatic allocation does not depend on a member keeping the app open
Observable: After the waiting member closes the app, an eligible release can still result in a confirmed booking. The runtime's background execution rules, scheduling cadence and execution deadline are unconfirmed. No fixed waitlist-specific turnaround time is promised for this background work.
Source: choice: automatic allocation must serve a member who is away from the app

### C-113: A runtime input limit produces no partial enrollment
Observable: If a host rejects the member's join request for exceeding a request size limit, the rejected request creates no wait. The applicable input-size rule and exact limit are unconfirmed.
Source: choice: a rejected input must not enroll a member

### C-114: Waitlist controls are usable in the app's existing authenticated session
Observable: A member signed in to the booking app can use the waitlist without creating a second account. The host's authentication prerequisites and session lifetime are unconfirmed.
Source: choice: the same membership governs both operations

### C-115: Production waitlist availability follows the host app's release requirements
Observable: The waitlist is available in production only after any requirements that govern release of this change to the booking app are met. Such release rules, prerequisites, and any numeric limits are unconfirmed because no deployment context was supplied.
Source: choice: the waitlist ships with the booking app under its actual release rules

### C-116: Existing class discovery continues to show the same occurrences
Observable: Enabling the waitlist does not remove full or open occurrences a member was already permitted to see.
Source: implied: the request adds a path for full classes within the existing app

### C-117: Existing bookings keep their confirmed status on rollout
Observable: After the feature is deployed, previously confirmed seats still appear in the member's bookings with the same active status unless an ordinary change also took effect.
Source: implied: U-13

### C-118: Rollout creates no waiting entries from past activity
Observable: A member who previously viewed a full class, tried and failed to book it, or canceled a booking is not added to a waitlist by deployment.
Source: choice: historical activity is not an affirmative join

### C-119: Existing account identity continues to identify the member
Observable: Existing users book and wait using the same account and can still see the bookings associated with that account.
Source: implied: the request adds a waitlist to an existing class booking app

### C-120: Waiting does not itself consume a class seat
Observable: An occurrence's count of confirmed bookings does not increase when an entry becomes waiting.
Source: implied: U-1 records interest in a future seat

### C-121: A promoted booking follows the ordinary confirmation communication policy
Observable: If an equivalent ordinary confirmation would send a booking message, a promotion triggers the same confirmation policy. Existing channels, recipients, contents, and delivery rules are unconfirmed.
Source: choice: a promoted seat is an ordinary seat with the same commitments

### C-122: A promoted booking uses the ordinary cancellation path
Observable: A promoted booking can be canceled under the same eligibility rules as an equivalent ordinary booking. Existing cancellation cutoffs and restrictions are unconfirmed.
Source: choice: the way a member received the booking should not affect cancellation

### C-123: Ordinary cancellations retain their existing rules
Observable: After the feature is enabled, the same ordinary confirmed booking remains cancellable under the same conditions as before. Existing cancellation windows and restrictions are unconfirmed.
Source: implied: U-5 relies on ordinary cancellations continuing to work

### C-124: Declining to wait creates no booking or waitlist commitment
Observable: If the member leaves the full class view without confirming a join, they have neither a wait from that visit nor a booking from it.
Source: choice: commitment requires affirmative action

### C-125: Joining does not trigger an ordinary confirmed-booking message
Observable: The member does not receive an ordinary booking confirmation message for a join that leaves them waiting.
Source: choice: those effects belong to confirmation

### C-126: A member can see only their own waitlist records in the member view
Observable: A member cannot see other entries, identities, order, or outcomes through member-facing views or requests.
Source: choice: each member needs only their own status

### C-127: Operator inspection cannot bypass existing occurrence permissions
Observable: An operator permitted to manage one occurrence cannot see another occurrence's queue without existing permission to manage that other occurrence.
Source: choice: the new view inherits the booking administration boundary

### C-128: Changing intake does not edit class capacity
Observable: After enabling or pausing the waitlist, the occurrence retains its previous capacity unless an ordinary capacity edit also took effect.
Source: implied: U-8 controls waitlist admission

### C-129: Allocation never adds a seat beyond current sellable capacity
Observable: When a promotion takes effect, confirmed seats plus any existing holds counted against the new booking do not exceed current capacity because of that promotion.
Source: implied: U-5 assigns genuinely available seats

### C-130: An occurrence cannot have more than one live confirmed booking for the same member through waitlist allocation
Observable: If an ordinary booking and a promotion for the same member race, no second live confirmed booking is added for the member on that occurrence.
Source: implied: U-5 gives the member a seat

### C-131: A successful join remains visible after a refresh or service restart
Observable: After confirmed admission, a later successful read shows the accepted wait or its actual later outcome.
Source: implied: U-7

### C-132: A join on one occurrence cannot consume capacity on another
Observable: Waiting or being promoted for one occurrence changes no seating allocation for another occurrence.
Source: implied: U-1 and U-5 concern the selected class occurrence

### C-133: Operator capacity changes keep their existing authority requirements
Observable: The waitlist introduces no way for a caller previously unable to edit capacity to change an occurrence's capacity.
Source: implied: U-9 uses the existing capacity controls

### C-134: Ordinary booking availability returns after rollback
Observable: When the waitlist is withdrawn, an available seat can again be booked through the preceding booking flow subject to that flow's ordinary rules.
Source: implied: U-14

### C-135: A member cancellation does not cancel somebody else's confirmed seat
Observable: Canceling a member's booking after promotion leaves every other member's confirmed booking active unless a separate ordinary cancellation applies.
Source: implied: U-5 releases and assigns individual seats

### C-136: Excess capacity is available for ordinary booking while allocation is pending
Observable: With one unresolved wait and two otherwise free seats, one seat can be booked directly by another eligible member. Direct booking can use any seats beyond a maximum of one per unresolved or eligible unassigned waiting member, after applying existing holds.
Source: choice: protect queue priority without holding seats the queue cannot use

### C-137: A fresh join takes priority from its own acceptance
Observable: After withdrawal, an ended wait, or cancellation of a promoted booking, a new accepted join starts behind all then-waiting entries.
Source: choice: an earlier place is released when the wait ends

### C-138: A member who gains a seat through another path stops waiting
Observable: When an existing action confirms a seat for a waiting member, the entry ends with the already-booked reason even if no vacant seat remains for an allocation attempt.
Source: choice: a member with a seat no longer needs a place in line

### C-139: New joins disclose automatic assignment before commitment
Observable: Before confirming a join, the member sees that an eligible turn for a seat creates a confirmed booking without further acceptance.
Source: choice: members need to know the consequence of joining

### C-140: Automatic booking stays within the member's accepted commitments
Observable: If an ordinary booking would require consent to a charge or other booking commitment that the member did not accept at join time or through existing standing permissions, allocation refuses the entry under C-79.
Source: choice: consent to wait does not authorize new obligations

### C-141: A promoted booking follows ordinary payment rules
Observable: A promoted booking has the same payment treatment as an equivalent ordinary booking, subject to C-140. Applicable charges, credits, amounts, currency, and payment timing are unconfirmed.
Source: choice: a seat should cost the same regardless of the booking path

### C-142: A promoted booking follows ordinary entitlement rules
Observable: A promoted booking uses the same entitlement as an equivalent ordinary booking, once per confirmed seat. Existing booking entitlement types and quantities are unconfirmed.
Source: choice: automatic assignment uses the same eligibility resources as ordinary booking

### C-143: Canceling a promoted booking has ordinary cancellation effects
Observable: The member gets the same cancellation effects as for an equivalent ordinary booking, including any applicable refunds, charges, and entitlement restoration. Existing rules and amounts are unconfirmed.
Source: choice: a promoted booking carries the same cancellation consequences

### C-144: Waiting alone creates no booking charge
Observable: The member incurs no booking charge for a join that leaves them waiting.
Source: choice: waiting does not purchase a seat

### C-145: Waiting alone uses no booking entitlement
Observable: A member who only joins retains their existing booking entitlements.
Source: choice: entitlements are used at confirmation

### C-146: An allocation that fails without a booking leaves no net booking charge
Observable: If an attempt ends without a seat after payment processing began, the member has no net charge for the failed attempt once recovery is complete.
Source: choice: payment should match the booking outcome

### C-147: An allocation that fails without a booking leaves no entitlement consumed
Observable: If an attempt ends without a seat after an entitlement was applied, the member retains the entitlement once recovery is complete.
Source: choice: entitlement use should match the booking outcome

### C-148: A refused join gives the authorized member a reason
Observable: For an accessible occurrence, the app identifies an applicable refusal: canceled, booking not yet open, booking closed, intake paused, feature withdrawal in progress, free seat for direct booking, a seat already confirmed for the member, or other ordinary eligibility refusal. If several apply, one accurate reason suffices.
Source: choice: a member needs enough information to decide what to do next

### C-149: Withdrawal after an ended wait preserves its outcome
Observable: A late withdrawal leaves an ended entry's recorded reason intact and shows the existing outcome when visible under C-60.
Source: choice: a late action should reflect the outcome already reached

### C-150: A past assignment is distinguishable from a current seat
Observable: After a promoted booking is canceled, the app does not show it as an active booking. An outcome still visible under C-60 can show that it was assigned before cancellation.
Source: choice: history should not suggest the member can still attend

### C-151: The waitlist offers operators no manual per-member withdrawal control
Observable: An operator cannot use the waitlist view to withdraw one member's entry.
Source: choice: members control individual withdrawals

### C-152: An authorized operator can end outstanding waits for rollback
Observable: An operator with authority to manage app-wide booking configuration can initiate feature withdrawal across all occurrences. Callers without that authority cannot initiate it.
Source: choice: an app-wide action gives the operator a defined way to retire the feature

### C-153: Feature withdrawal requires paused intake
Observable: An attempt to initiate feature withdrawal while intake is enabled leaves the existing waits active and tells the operator to pause intake.
Source: choice: closing admission makes the set of outstanding waits finite

### C-154: A failed rollback termination can be retried
Observable: After an interruption, an authorized operator can repeat feature withdrawal to end waits that still need to be resolved. Previously committed outcomes stand.
Source: choice: rollback must be recoverable

### C-155: Cancellation supplies the reason when it also closes booking
Observable: If one operation cancels an occurrence and closes its booking window, entries it ends show occurrence canceled as the reason.
Source: choice: cancellation best explains what happened

### C-156: An active wait has no separate age limit
Observable: An entry remains waiting until withdrawal, booking through the waitlist, booking closure, occurrence cancellation, allocation-time eligibility refusal, another path confirming a seat for that member, or feature withdrawal. No extra number of minutes or days ends the wait.
Source: choice: the booking lifecycle already defines the end of a wait

### C-157: An occurrence removed permanently is treated as canceled for active waits
Observable: If an existing operator action permanently removes an occurrence, the outstanding waits end as occurrence canceled. Visibility of their outcomes follows C-60.
Source: choice: a removed occurrence can never supply a seat

### C-158: Changing an occurrence's schedule does not move the entry to a different occurrence
Observable: An existing edit that changes the time of the same occurrence retains its active queue while booking remains open. An existing operation that cancels it and creates another occurrence ends the old waits under C-88, with no carryover to the replacement.
Source: choice: waitlist participation follows occurrence identity

### C-159: Feature withdrawal blocks promotion once its cutoff takes effect
Observable: After app-wide withdrawal takes effect, no new promotion can confirm, even if individual terminal outcomes are still being processed. A previously confirmed booking is governed by C-19.
Source: choice: a rollback can stop allocation even when outcome processing takes time

### C-160: Intake cannot reopen during feature withdrawal
Observable: An enable action after the withdrawal cutoff cannot resume intake until the waitlist is available again after rollback.
Source: choice: reopening must not create waits while retirement is still in progress

### C-161: The operator can distinguish incomplete rollback from completed withdrawal
Observable: Before removing waitlist access, the operator can tell whether every outstanding entry has ended. An unavailable read reports unavailability under C-103.
Source: choice: rollback requires assurance that obligations have been resolved

### C-162: Replaying an old join reports its recorded outcome when available
Observable: A member retrying the same join action after its entry ended or was withdrawn can receive that prior outcome while authorized to see it. A retry does not substitute a new entry for that action.
Source: choice: a lost action result can be recovered without new consent

### C-163: A rejected or unavailable operation has distinguishable feedback
Observable: For an operation with a known outcome, the app distinguishes invalid or unavailable target, lack of authentication, refusal under current rules, and service failure before change, as applicable. An unknown write outcome follows C-99. Existing visibility protections under C-24 still apply.
Source: choice: the member must know whether to correct input, sign in, change plans, or verify the result later

### C-164: Retrying a committed allocation does not repeat a booking charge
Observable: When an allocation is retried after a lost result, the member incurs the ordinary payment for one confirmed booking only, if required.
Source: choice: retries cannot multiply the cost of one seat

### C-165: Retrying a committed allocation does not trigger a second ordinary confirmation
Observable: A retry after a promotion already committed does not initiate an additional ordinary confirmation for that same booking. Existing message delivery behavior is unconfirmed.
Source: choice: a retried assignment is the same booking event

### C-166: A blocked allocation is visible to the operator
Observable: When the service knows a potentially assignable seat is waiting on an unresolved eligibility or booking dependency, the authorized operator can distinguish the blocked allocation from the ordinary case of every seat being occupied or held.
Source: choice: an operator needs to tell a service interruption from a full occurrence

### C-167: An occurrence with zero capacity can accept waits if booking is otherwise open
Observable: A zero-seat occurrence accepts a join when intake is enabled and the member otherwise qualifies. If the existing app treats zero capacity as booking closed or canceled, that existing state governs instead. The host app's permitted capacity range is unconfirmed.
Source: choice: a class that can gain seats can benefit from a waitlist even when it starts with none

### C-168: An edit that takes an open occurrence outside its booking window ends active waits
Observable: If an existing schedule or booking-window edit moves an open occurrence to a time when ordinary booking is unavailable, its active waits end with booking closed unless the occurrence was canceled.
Source: choice: existing waits should resolve when booking is taken out of service

### C-169: Only a definitive booking refusal ends a wait for ineligibility
Observable: A known ordinary booking refusal ends the entry under C-79 when based on current non-capacity eligibility, required consent, or another applicable ordinary prerequisite. A dependency timeout, unavailable service, or uncertain result leaves the entry pending reconciliation under C-82 and C-86. Existing application-specific refusal rules are unconfirmed.
Source: choice: distinguish a decision about the member from lack of a reliable result

### C-170: Retries do not assign a seat after the booking opportunity has ended
Observable: If allocation becomes possible again only after booking closed, cancellation took effect, or feature withdrawal took effect, a wait that never obtained a booking cannot be promoted by retry.
Source: choice: recovery resolves interrupted work under the same lifecycle limits

### C-171: Rollback completion remains verifiable after an interrupted attempt
Observable: When service returns after a lost withdrawal result, the authorized operator can determine whether feature withdrawal has taken effect and whether any waiting outcomes still need to be finalized.
Source: choice: operators must know whether to retry the cutoff or wait for completion

### C-172: Intake starts paused when the waitlist returns after rollback
Observable: When waitlist access is restored after rollback, full occurrences accept no new waits until the operator enables intake again.
Source: choice: the operator chooses when to resume enrollment

### C-173: The first event that ends a wait supplies its terminal outcome
Observable: Once withdrawal, assignment, closure, cancellation, definitive ineligibility, a seat from another path, or feature withdrawal takes effect for an entry, a later event does not replace that entry's outcome. C-155 governs the single action that both cancels and closes an occurrence. Feature withdrawal takes effect at the cutoff under C-159 even if its outcome is still being finalized.
Source: choice: a delayed event must not overwrite the actual resolution

### C-174: An unresolved turn defers later promotions for the occurrence
Observable: If the earliest remaining entry has a turn for a seat but its eligibility or booking result is unresolved, no later waiting member is promoted until that turn is resolved. Direct booking can still use excess capacity under C-136.
Source: choice: retain an observable confirmation order without withholding seats that no waiting entry can use
