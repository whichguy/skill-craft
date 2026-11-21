## Use cases

### U-1: A member finds a full class and joins its waitlist to get a chance at a spot
Flow: The member finds a class they could otherwise book, sees that no spots are available, joins the waitlist, and sees that they are waiting for this class.
Source: request

### U-2: A member returns to a class to check their status or retry a join
Flow: The member opens the class again or repeats the join after an uncertain response. They can tell whether they are waiting or booked, and a retry does not add a second entry.
Source: implied: a member needs to know whether their request took effect

### U-3: A waitlisted member leaves to give up their chance at a spot
Flow: The member leaves before receiving a spot and sees that they are no longer waiting. If they change their mind while the class is full, they can join again.
Source: implied: a member's plans can change before a spot opens

### U-4: A member gets a booking when someone gives up a spot
Flow: A booked member cancels through the normal booking flow. An eligible waiting member receives the freed spot and can verify that they are booked. The cancelling member sees the usual cancellation result.
Source: implied: a waitlist must give members a way into the class when a spot opens

### U-5: A member books an available class through the existing flow
Flow: The member books a class with available capacity and no waiting members. If someone later cancels while nobody is waiting, another member can book the freed spot normally.
Source: implied: adding a waitlist for full classes touches ordinary booking and cancellation

### U-6: Members contend for the last available spot
Flow: Several members act while the last spot is being taken or released. Each gets a result reflecting whether they booked or can wait. The class never gains an extra booking as a result of the competing requests.
Source: implied: several members can act on the same class at the same time

### U-7: A member encounters a refused waitlist action
Flow: The member tries to join for an invalid or unavailable class, acts without the required access, attempts to join when ineligible, or uses a full-class view after a spot has opened. They see the applicable outcome without an invalid waitlist entry being created.
Source: implied: waitlist actions can be attempted with stale information, invalid input or insufficient permission

### U-8: An operator changes a class that has people waiting
Flow: Where the app already supports it, the operator raises or lowers capacity, cancels the class or removes it. People waiting see the consequences for that class and its available spots.
Source: implied: the existing class controls can affect whether a spot can be offered

### U-9: A waiting member reaches the end of the booking window
Flow: The class stops accepting bookings with people still waiting. A member returning to the class can tell that they are no longer waiting for a spot.
Source: implied: a waitlist needs an end when a member can no longer book the class

### U-10: Members use a waitlist at the largest supported class capacity
Flow: Every spot in a class at the app's existing maximum capacity is taken. Eligible members continue to join the waitlist. When spots open, each available spot can go to an eligible waiting member. An entry that cannot receive a booking does not hold up the others.
Source: implied: the feature must handle full classes across the existing capacity range and continue when a member's eligibility changes

### U-11: An operator enables the release for existing members
Flow: The operator starts the release with the current class and booking data. Members keep their existing bookings and can join the waitlist of an already-full class. Any existing booking settings still apply.
Source: implied: adding the feature must support the app's current data and configuration

### U-12: An operator restarts the app after normal operation or an interruption
Flow: The operator restarts with bookings and waiting entries already present, possibly while a spot was being freed. Members recover their recorded status, and pending allocation can proceed without granting the same spot twice.
Source: implied: members rely on their place even if the app stops or restarts

### U-13: An operator returns to the previous version to continue ordinary booking
Flow: The operator rolls back after waitlist activity. The previous version can continue handling classes and confirmed bookings. Pending entries are unavailable during rollback and become usable again on re-upgrade if the class still accepts bookings.
Source: implied: the operator needs a way back to the previous release without losing confirmed bookings

## Clauses

### C-1: An eligible member can join the waitlist of a full class that is open for booking
Observable: A member who meets the class's booking requirements other than seat availability can join when the class has zero bookable spots remaining.
Source: request

### C-2: An otherwise visible class remains discoverable when it becomes full
Observable: A member can still find the class through the app's ordinary class discovery flow once the last spot is booked.
Source: implied: U-1 requires members to find the full class before joining

### C-3: A member can identify a class as full before trying to join its waitlist
Observable: The class view communicates that zero spots are available when it offers the waitlist action.
Source: implied: U-1 requires a member to understand why the waitlist is available

### C-4: A successful join is visible to the member
Observable: After joining succeeds, the member can see that they are waiting for that class.
Source: implied: U-1 requires the member to know the outcome of joining

### C-5: An entry applies to a single bookable class occurrence
Observable: Joining one occurrence leaves the member's waitlist status for all other occurrences unchanged, including another occurrence of the same class.
Source: implied: U-1 concerns a spot in the class the member selected

### C-6: A waiting entry does not confer a confirmed spot
Observable: A member who has joined but has yet to receive a spot does not appear as booked for that class.
Source: implied: U-1 distinguishes waiting from holding a place in a full class

### C-7: Joining alone does not use any booking entitlement
Observable: The member's credits or applicable booking allowance remain unchanged when the member joins.
Source: choice: waitlist entry is reversible interest in a spot

### C-8: Joining alone does not create a booking charge
Observable: A member who joins is not charged for the class at the time of joining.
Source: choice: a charge is appropriate only under the existing rules for a confirmed spot

### C-9: A member can check whether they are waiting after returning to the app
Observable: A member with an active entry can see that status on a later visit.
Source: implied: U-2 requires status to be available beyond the join response

### C-10: A member can hold at most one active waiting entry for a class
Observable: Repeating a join, including submitting multiple joins together, leaves at most one active entry for the member in the class.
Source: choice: each member needs only one chance at one spot

### C-11: Repeating a successful join preserves the member's place
Observable: A member who retries while still waiting keeps the same priority relative to other members.
Source: choice: retrying after an uncertain response should be safe

### C-12: A member can withdraw their active waiting entry
Observable: With a pending entry, the member can leave the waitlist and see that they are no longer waiting.
Source: choice: members need a way to change their plans before receiving a booking

### C-13: Repeating a withdrawal cannot create an active entry
Observable: If a member retries leaving after their withdrawal took effect, they remain off the waitlist.
Source: implied: U-3 requires a withdrawal to remain effective after a retry

### C-14: A withdrawal request is never a booking cancellation
Observable: A member who submits a withdrawal after receiving a confirmed booking still holds that booking after the request.
Source: implied: U-3 gives up waiting for a spot, while U-4 uses ordinary cancellation for a confirmed spot

### C-15: A withdrawn entry is ineligible for allocation
Observable: Once withdrawal takes effect, a later available spot is not booked on the basis of that entry.
Source: implied: U-3 requires leaving to give up the chance at a spot

### C-16: A member who left may join again while eligible
Observable: A member who has left can join again if the class is still full and the usual join conditions are met.
Source: choice: leaving does not permanently bar a member from the class

### C-17: A rejoin uses the priority of the new entry
Observable: A rejoining member has the priority of a member joining at that time.
Source: choice: withdrawal ends the member's claim to their previous place

### C-18: A withdrawal racing an allocation has an outcome consistent with which action took effect first
Observable: If withdrawal takes effect first the member receives no booking from that entry. If allocation takes effect first the member sees the confirmed booking and can use the existing booking cancellation action.
Source: implied: U-3 and U-6 require a successful withdrawal and a confirmed booking to have clear, distinct effects

### C-19: A freed spot can go to a member waiting for that class
Observable: When a spot opens during the booking window and at least one waiting member qualifies, an eligible waiting member receives the spot.
Source: implied: U-4 fulfills the request to give people a way into a class that was full

### C-20: An eligible waiting member receives an available spot automatically
Observable: In a class with a waiting member eligible for a spot, the member receives a confirmed booking without submitting another request.
Source: choice: automatic booking fills a vacancy without a claim step or timer

### C-21: The member is told before joining that an available spot can be booked on their behalf
Observable: Before submitting the join, the member can see that joining authorizes a confirmed booking for the selected class if they receive a spot.
Source: implied: U-1 involves opting into the booking outcome in U-4

### C-22: Earlier active entries have priority over later entries
Observable: If two otherwise eligible members join one after the other for the same class and only one spot opens, the earlier entrant receives it.
Source: choice: arrival order is a predictable way to allocate scarce spots

### C-23: Eligible waiting members have priority over new direct bookings for freed spots
Observable: If a new direct booking request competes with an eligible waiting member for the only freed spot, that spot goes to the waiting member.
Source: choice: membership on the waitlist must give a meaningful chance at a spot

### C-24: One newly available spot can produce at most one booking
Observable: With multiple waiting members competing for one released spot, at most one of them receives a booking for that spot.
Source: implied: U-6 preserves the existing class capacity limit

### C-25: Multiple vacancies can be filled from the waitlist
Observable: When multiple spots open during the booking window, each can be allocated to a different eligible waiting member until the available spots or eligible members run out.
Source: implied: U-10 extends the ordinary waitlist outcome to more than one vacancy

### C-26: An empty waitlist leaves a vacancy usable by ordinary booking
Observable: When a spot opens for a class with zero waiting entries, an eligible member can book it through the usual path.
Source: implied: U-5 requires ordinary booking to continue without waiting members

### C-27: A booking awarded from the waitlist is visible in the member's existing booking view
Observable: The member can find the confirmed booking where they ordinarily find their confirmed classes.
Source: implied: U-4 requires the member to be able to tell that they have received a spot

### C-28: A successful allocation ends the member's active waitlist entry
Observable: A member who gets a booking through the waitlist is no longer shown as waiting for that class.
Source: implied: U-2 requires status to distinguish waiting from being booked

### C-29: A booking awarded from the waitlist counts toward class capacity
Observable: A single confirmed booking awarded from the waitlist occupies one spot in the class.
Source: implied: U-4 grants a spot in the existing class

### C-30: A booking awarded from the waitlist follows the existing confirmation behavior
Observable: If an ordinary confirmed booking for this member and class gives a receipt or confirmation through the app's existing channels, a confirmed booking from the waitlist does too.
Source: choice: reuse the existing confirmation experience so members can learn when they get a spot

### C-31: A member already booked for a class cannot join its waitlist
Observable: A member with a confirmed booking who tries to join the waitlist for that occurrence cannot acquire an active entry.
Source: implied: U-1 seeks a spot for a member who does not already hold one

### C-32: A member who already holds a confirmed booking does not receive another booking from the waitlist
Observable: If a waiting member acquires a confirmed booking for the same class through an existing booking path, the waitlist does not allocate another spot to that member.
Source: implied: U-4 satisfies the waiting member's request for a spot in the class

### C-33: A confirmed booking for the same class ends a pending entry regardless of how it was obtained
Observable: If a member already on the waitlist becomes booked for that class through another existing booking path, the member is no longer shown as waiting.
Source: implied: U-2 requires the member's status to reflect that they have a spot

### C-34: Class capacity remains the ceiling for newly confirmed bookings
Observable: Competing joins, allocations and direct booking requests cannot cause a new booking to take confirmed attendance beyond the configured capacity, including when requests arrive together.
Source: implied: U-6 requires the waitlist to work within the existing limit

### C-35: Ordinary booking is still offered when a spot is open to direct booking
Observable: An eligible member viewing an available class can still use the existing booking flow.
Source: implied: U-5 preserves the request's distinction between available and full classes

### C-36: When a class fills during a booking attempt, an eligible member can proceed to its waitlist
Observable: If the final spot is taken before the member's booking succeeds, the member can use the full-class waitlist flow without gaining an extra confirmed booking.
Source: implied: U-6 covers a class that becomes full while a member is trying to book it

### C-37: A join only takes effect while the class is full
Observable: If a class has an available spot when a join from a stale full-class view is processed, the member receives no waiting entry from that request.
Source: choice: members should use direct booking for classes with available spots

### C-38: A join never silently becomes a direct booking
Observable: When a stale join encounters an available spot, the member can proceed to ordinary booking without a booking having been created by the join.
Source: choice: the action the member selected should determine whether they booked directly

### C-39: An unknown or invalid class reference is refused
Observable: Attempting to join for a class the app cannot identify produces an unsuccessful result and creates no waitlist entry.
Source: implied: U-7 requires entries to refer to actual classes

### C-40: Waitlist actions respect existing booking access requirements
Observable: A caller without permission to act for the member cannot join or withdraw on that member's behalf.
Source: implied: U-7 preserves the authority required for member booking actions

### C-41: Member waitlist status respects existing booking privacy
Observable: A caller who cannot see another member's booking status cannot obtain their individual waitlist status through the waitlist feature.
Source: implied: U-2 exposes member-specific information similar to booking status

### C-42: Joining respects the existing rules that determine whether a member may book the class
Observable: A member refused an ordinary booking for a reason other than seat availability is refused waitlist entry while that reason applies.
Source: choice: a place should be held in the waitlist only by someone who could accept an available spot

### C-43: Eligibility is checked when a waitlisted member would receive a spot
Observable: A member whose booking eligibility changed after joining cannot receive a booking if the existing rules would refuse it at the time of allocation.
Source: implied: U-10 preserves the existing booking rules at the time a booking is made

### C-44: An entry that cannot receive an available booking because of member ineligibility ends
Observable: A member reached for allocation who fails the applicable booking eligibility check no longer has an active entry for that class.
Source: choice: an ineligible entry should stop claiming places in the queue

### C-45: An ineligible entry cannot hold an available spot away from eligible waiting members
Observable: If a member cannot receive the booking and another active waiting member qualifies, the qualifying member can receive the spot.
Source: implied: U-10 requires the waitlist to keep filling available spots when eligibility changes

### C-46: A refused waitlist action has an observable unsuccessful outcome
Observable: The caller attempting a refused join or withdrawal can tell that the requested change did not take effect.
Source: implied: U-7 requires the caller to distinguish success from refusal

### C-47: A refused waitlist action does not alter another member's entry
Observable: An unsuccessful attempt to act on another member's entry leaves that entry's status and priority unchanged.
Source: implied: U-7 requires a refused action to leave other members' places intact

### C-48: A refused waitlist action leaves the member's confirmed booking unchanged
Observable: After a refused join or withdrawal, any confirmed booking already held by the member for that class is still in the same state.
Source: implied: U-7 requires waitlist action errors to leave existing bookings intact

### C-49: An existing confirmed booking retains its normal cancellation rules
Observable: A booked member can cancel under the same conditions, including the applicable cutoff, regardless of waitlist status.
Source: implied: U-4 continues to use ordinary cancellation

### C-50: A normal cancellation refusal does not release the member's spot
Observable: If the app refuses to cancel a confirmed booking, that booking still occupies its spot and the waitlist cannot allocate that spot.
Source: implied: U-4 opens a spot only when the ordinary cancellation takes effect

### C-51: An existing confirmed booking retains its normal cancellation consequences
Observable: The member cancelling a booking receives the same applicable credit return, refund or penalty regardless of whether the freed spot is filled from the waitlist.
Source: implied: U-4 preserves the result of the original booking cancellation

### C-52: A booking from the waitlist uses the app's existing booking price rules
Observable: For the same member, class and time of confirmation, any price charged follows the rules for an ordinary booking.
Source: implied: U-4 creates a booking in the existing app

### C-53: A booking from the waitlist uses the app's existing booking entitlement rules
Observable: Confirmation from the waitlist uses the same applicable credits or booking allowance as an ordinary booking under the same conditions.
Source: implied: U-4 grants the same kind of confirmed spot as ordinary booking

### C-54: A booking from the waitlist can be cancelled under the ordinary cancellation rules
Observable: A member booked from the waitlist can cancel in the same situations as a comparable directly booked member.
Source: implied: U-4 gives the member an ordinary confirmed booking

### C-55: A booking obtained from the waitlist retains ordinary cancellation consequences
Observable: Cancelling a confirmed booking obtained from the waitlist has the same applicable credit return, refund or penalty as cancelling a comparable direct booking.
Source: implied: U-4 grants an ordinary confirmed booking

### C-56: An operator can still use existing class capacity controls
Observable: Where capacity edits are already supported, the operator can apply the same range and validation of capacity values to a class with a waitlist.
Source: implied: U-8 preserves the operator's current class controls

### C-57: A capacity increase makes newly bookable spots available for allocation
Observable: Where capacity edits are supported, raising capacity enough to add a bookable spot while waitlist allocation is open allows that spot to be filled from the waitlist.
Source: implied: U-8 can free spots by increasing capacity

### C-58: A capacity decrease does not trigger waitlist allocations while there are zero bookable spots
Observable: After a supported capacity decrease leaves no spots available, no waiting member gets a spot unless capacity becomes available again.
Source: implied: U-8 cannot grant a spot that a capacity reduction did not free

### C-59: A class cancellation or removal ends the class's active waitlist
Observable: Once the operator cancels or removes a class using a supported action, its entries cease to be active.
Source: implied: U-8 leaves no class to book after cancellation or removal

### C-60: A cancelled or removed class does not accept new waitlist entries
Observable: A member using an earlier class view after the operator cancels or removes the class cannot create an active entry.
Source: implied: U-8 leaves no class to book after cancellation or removal

### C-61: An operator's class cancellation retains its normal effects on confirmed bookings
Observable: Where class cancellation is supported, it has the existing consequences for confirmed members even when the class also has waiting members.
Source: implied: U-8 preserves the class cancellation behavior

### C-62: A class stops accepting joins at the existing booking cutoff
Observable: As soon as the class reaches its existing booking cutoff, a join cannot create a waiting entry.
Source: implied: U-9 requires the waitlist to follow the class's existing booking cutoff

### C-63: Waitlist allocations stop at the existing booking cutoff
Observable: A spot that becomes available at or after the point when the class stops accepting ordinary bookings does not produce a waitlist booking.
Source: implied: U-9 requires an allocation to take effect within the booking window

### C-64: The scheduled start is the waitlist cutoff if the app has no booking cutoff
Observable: For a class without an existing booking cutoff, waitlist access closes at the scheduled start time.
Source: choice: waiting is useful only before the class begins when no existing cutoff applies

### C-65: Entries still waiting when the waitlist closes cease to be active
Observable: A member who was waiting when the waitlist closed can no longer see an active waiting entry for the class.
Source: implied: U-9 requires the waiting status to reflect that a spot is no longer possible

### C-66: Waitlisting works at every class capacity the app already supports
Observable: An eligible member can join any supported class once it is full, including at the smallest and largest existing capacity values that allow a bookable class.
Source: implied: U-10 extends the feature across the existing supported classes

### C-67: There is no waitlist-specific length limit
Observable: An otherwise valid join is not refused solely because of the number of members already waiting.
Source: choice: the request gives no queue size at which to start turning eligible members away

### C-68: An existing class is usable with the new release without being recreated
Observable: On first start with existing data, a previously created class retains its details and can accept waiting members when eligible.
Source: implied: U-11 requires carryover of the existing class schedule

### C-69: An existing confirmed booking remains confirmed on first start
Observable: A member can see and use a booking made before the waitlist release in the same way after startup.
Source: implied: U-11 requires carryover of the existing confirmed bookings

### C-70: Existing classes start with no waiting entries on first upgrade
Observable: A pre-existing class starts with zero waiting entries until a member joins it.
Source: implied: U-11 adds a new action that no member could have previously taken

### C-71: The waitlist uses the existing booking configuration without a separate required setup step
Observable: After starting the new release with the existing booking settings, an operator can accept waitlist joins for eligible full classes without setting additional options.
Source: choice: waitlisting should work for current classes as part of ordinary class booking

### C-72: Restart preserves a recorded active waiting entry
Observable: After restarting with the same app data, the member's previously acknowledged entry continues to participate if it would otherwise still be active.
Source: implied: U-12 requires members to retain their recorded place after restart

### C-73: Restart preserves the relative priority of surviving entries
Observable: If the same entries remain active after a restart, their priority relative to each other remains the same.
Source: implied: U-12 requires retaining the members' existing places

### C-74: Restart can recover an allocation interrupted after a vacancy opened
Observable: If a vacancy was recorded and the app stops before filling it, an eligible waiting member can receive the spot after restart if the class still accepts bookings.
Source: implied: U-12 requires service interruption to leave the waitlist capable of filling a vacancy

### C-75: An interrupted allocation remains eligible for recovery when the booking could not be recorded
Observable: If completing a booking is temporarily unavailable, an otherwise eligible member's entry remains active until the booking takes effect, the member withdraws, or the entry would otherwise end.
Source: implied: U-12 requires an interruption to leave an unfulfilled recorded entry usable

### C-76: Recovering an interrupted allocation does not duplicate a confirmed booking
Observable: If the booking already took effect before the interruption, recovery leaves the member with one confirmed booking for that allocation.
Source: implied: U-12 requires recovery to preserve the booking already recorded

### C-77: Recovering an interrupted allocation does not charge the member twice
Observable: If the booking charge already took effect before the interruption, recovery does not add a second charge for that booking.
Source: implied: U-12 requires recovery to preserve existing booking charges

### C-78: Recovering an interrupted allocation does not consume the member's booking entitlement twice
Observable: If the booking already used a credit or booking allowance before the interruption, recovery does not use it again for the same booking.
Source: implied: U-12 requires recovery to preserve existing entitlement use

### C-79: The previous version can resume ordinary class booking after rollback
Observable: After rollback, the operator can use the previous version with the existing class data and its ordinary booking controls.
Source: implied: U-13 requires a usable previous version

### C-80: Rollback preserves confirmed bookings made before rollback
Observable: After rollback, members can view and manage their confirmed bookings, including those obtained from the waitlist, through the previous version's ordinary booking flow.
Source: implied: U-13 requires continued use of confirmed spots

### C-81: Waitlist operation is suspended while running the previous version
Observable: Pending entries cannot award spots while the previous version is serving ordinary bookings.
Source: choice: the previous version can continue to use its own booking behavior during rollback

### C-82: Re-upgrade restores pending entries for classes that still accept waitlist allocations
Observable: After rollback followed by re-upgrade, a previously pending entry is available to participate with its prior priority if the class still exists and its waitlist is still open.
Source: choice: a reversible deployment should preserve a member's place when it can still be used

### C-83: Re-upgrade applies waitlist allocation only to spots currently available
Observable: If the previous version filled a spot during rollback, re-upgrade leaves that confirmed booking in place and cannot grant the same spot to a waiting member.
Source: implied: U-13 must preserve bookings made while the old version was serving members
