## Use cases

### U-1: An eligible member joins the waitlist for a full class to get a chance at a seat
Flow: The member opens a full class, sees a way to wait, submits the request, then sees that they are waiting for that class. This works for the first person on an empty waitlist. If the last seat becomes available for ordinary booking before the request takes effect, the member is directed to booking.
Source: request

### U-2: A waiting member checks their status to know whether they have a seat
Flow: The member returns to the app to check that occurrence. They can distinguish waiting, having an offer, having a confirmed booking, or having none of those. If the status cannot be retrieved, the app shows that it is unavailable.
Source: implied: joining a waitlist creates a status the member relies on later

### U-3: A waiting member leaves to stop being considered for a seat
Flow: The member opens their waiting status, leaves, then checks that they are no longer waiting. If an offer was issued first, they can decline it. If they have already confirmed the booking, the leave action gives them the confirmed status and ordinary cancellation remains available under its existing rules.
Source: implied: a member's plans can change while they wait

### U-4: A waiting member gets an available seat to attend the class
Flow: A seat opens after a cancellation or capacity increase. The member checks their status, sees their offer deadline, and claims the seat through ordinary booking. If the offer has expired or the class has closed, the member sees that it is unavailable.
Source: implied: a waitlist for a full class must provide a way to obtain an opening

### U-5: A member books an available class to reserve a seat directly
Flow: The member opens a class with an available seat and uses the ordinary booking flow. If the last seat is taken before they confirm, they can return to the full occurrence to see whether they can join the waitlist.
Source: implied: the request adds a waitlist to an existing booking app

### U-6: A member handles a repeated or refused action to learn their actual status
Flow: The member submits a join twice, tries after the class stops accepting requests, submits an invalid class reference, or uses the app while signed out. The app shows the resulting status or a reason the action could not be completed.
Source: implied: waitlist requests can be repeated, invalid, or made after the displayed class status changes

### U-7: A member tries to join during heavy demand to find out whether they can still wait
Flow: Many eligible members join the same full class. A later member tries to join, then sees whether they are waiting or whether the request could not be accepted.
Source: implied: full classes can draw more than one waiting member

### U-8: A member recovers from an interrupted action to find out what happened
Flow: The member loses the response or encounters a service error, then checks their status or repeats the action after service returns.
Source: implied: a member may lose connectivity while changing their status

### U-9: An operator starts or pauses waitlist admissions to manage rollout
Flow: An authorized operator checks the current admission setting, enables or pauses admissions, then verifies the setting or sees that the change failed.
Source: implied: introducing a feature to an existing class booking app requires an operational start and stop

### U-10: An operator checks an occurrence to recover from a booking or waitlist incident
Flow: An authorized operator identifies the occurrence and checks the outstanding waiting and offer counts. If allocation is interrupted, the operator can see that recovery is pending and verify current counts when service returns.
Source: implied: a failed booking or waitlist operation can leave members uncertain about seats

### U-11: An operator changes or cancels a class to keep bookings and waitlists consistent with the schedule
Flow: An authorized operator changes an occurrence's capacity or schedule, or cancels the occurrence. Members see the resulting availability or closure. If the existing app refuses a proposed change, the attempted edit does not change the queue or its offers.
Source: implied: the existing app may change classes after some members have joined a waitlist

### U-12: An operator releases or rolls back the feature to keep existing booking data usable
Flow: The operator starts with existing classes and bookings, verifies their status after release, pauses admissions to prepare a rollback, and checks readiness. An active entry, offer, or unsettled claim keeps rollback from starting. After rollback, claimed bookings remain available through ordinary booking.
Source: implied: the feature is an addition to an app with existing booking data

## Clauses

### C-1: An eligible member can request to wait for a full class that is still accepting bookings
Observable: Open a full, bookable class as an eligible member while the waitlist is accepting new requests. Find a way to submit a waitlist request, including when nobody is waiting.
Source: request

### C-2: A successful join shows the member a waiting outcome for the requested class
Observable: Join a full class successfully while it stays full. The result confirms that the request to wait applies to that occurrence.
Source: implied: U-1

### C-3: Waiting is distinguishable from a confirmed booking
Observable: Compare the member's status while waiting with the status after a booking is confirmed. Each communicates a different entitlement to a seat.
Source: implied: U-2

### C-4: A member can stop waiting for a class
Observable: Leave while still waiting, then check the class and see that the member is no longer waiting.
Source: choice: give members a way to withdraw interest when their plans change

### C-5: A waiting member can get a seat that becomes available
Observable: With one eligible member waiting, cancel a confirmed booking while the class can still be booked and observe a route for that member to take the resulting opening.
Source: implied: U-4

### C-6: Ordinary booking remains available for bookable seats that are available to the caller
Observable: Open a bookable class with an open seat and no waiting members, then reserve it through the existing booking flow.
Source: implied: U-5

### C-7: Repeating a join while already waiting creates at most one active waiting entry for that member in that class
Observable: Submit two joins for the same member and occurrence while it remains full. After one booking fulfills the request, check the member's status. There is no second request still waiting for a seat.
Source: implied: U-6, a member has one request for the same opportunity

### C-8: An unsuccessful join reports an unsuccessful outcome
Observable: Cause a join to fail with a known refusal and see an explanation that the member did not join in that attempt.
Source: implied: U-6

### C-9: An otherwise valid join has no additional product-imposed queue-size cap
Observable: Given an eligible, bookable full class and healthy service, the number of existing waiting members alone never causes refusal. Any platform-imposed queue-size ceiling is unconfirmed.
Source: choice: avoid turning away eligible members solely because many others are waiting

### C-10: A member can retrieve their current waitlist status after reconnecting
Observable: Lose the response to a join, reconnect as the same member, and retrieve the current state for that class.
Source: implied: U-8

### C-11: An operator can set admissions to either enabled or paused
Observable: As an authorized operator, apply each of the two settings and verify which setting took effect.
Source: choice: give operators a reversible admission control for U-9

### C-12: An operator can see the number of waiting members for a class
Observable: As an authorized operator, inspect a class with 0 waiting members. One member joining changes the count to 1. Issuing that member an offer changes the waiting count to 0.
Source: choice: give operators a way to confirm queue activity during an incident

### C-13: Cancellation of a class closes its waitlist
Observable: Cancel a full class with a waiting member. The member can see that the class was cancelled and that their request will no longer be considered.
Source: implied: U-11, a cancelled class can no longer offer a seat

### C-14: Existing bookings retain their status when the waitlist feature is released
Observable: Check a previously booked class before and after the feature is released. The booking has the same status after release unless an ordinary booking change took effect.
Source: implied: U-12

### C-15: Rollback readiness requires zero active waiting entries
Observable: Compare rollback readiness with 1 active waiting member across the deployment and after the active waiting count reaches 0. Only the latter can meet the waiting-count condition.
Source: choice: protect outstanding waiting requests during rollback

### C-16: A waitlist applies to one scheduled occurrence
Observable: With two sessions of the same class, join the full session. The other session's waiting status for the same member is unaffected.
Source: implied: U-1, the seat being sought belongs to the class session the member intends to attend

### C-17: Waitlist status identifies the occurrence it applies to
Observable: Open your own status for one of two same-title sessions. The member can tell which session their status refers to even when the sessions share a start time. The display fields are left to the host app's existing convention, which is unconfirmed.
Source: implied: U-1 and U-2, members must be able to identify the class they are waiting for

### C-18: A member can find the waitlist from the existing class details
Observable: Reach a full, joinable occurrence as an eligible member using the existing class discovery flow. Find the waitlist action in that occurrence's booking context.
Source: choice: provide the alternative at the point where the member encounters a full class

### C-19: A member's waitlist actions require a signed-in member identity
Observable: Attempt to join, leave, claim, or decline while signed out or with an expired session. The app requires a valid member sign-in before performing the requested action.
Source: implied: U-2 and U-6, the app must identify whose waiting status or seat entitlement would change

### C-20: Existing booking eligibility governs entry to the waitlist
Observable: For a full occurrence, compare the join outcome for a member who can ordinarily book that occurrence with a member denied by an existing member or class eligibility rule. Only the former is eligible to wait. Existing eligibility rules and their numeric thresholds are unconfirmed. Seat availability and any steps the existing booking flow performs at confirmation are excluded from the join check.
Source: choice: offer openings to members who could take them while leaving booking confirmation steps in the existing flow

### C-21: Waitlist activity closes when the occurrence stops accepting bookings or reaches its scheduled start, whichever comes first
Observable: On either boundary, attempts to create a new waitlist entry no longer qualify. With no earlier booking cutoff, the boundary is the scheduled start. Any earlier booking cutoff and its offset from start are unconfirmed.
Source: choice: tie waiting to a usable opportunity to book, with the class start as the latest possible boundary

### C-22: A member without a booking or active waitlist entry uses direct booking when an unallocated seat is available
Observable: Attempt to join without an existing booking or active entry when a seat is available for ordinary booking. The app directs the member to ordinary booking without entering them on the waitlist.
Source: choice: use the shortest route to a seat that is currently available

### C-23: A confirmed booking excludes the same member from the same occurrence's waitlist
Observable: Open the waitlist or submit a join for an occurrence you have already booked. The result is the current confirmed booking with 0 active waitlist entries for that member.
Source: implied: U-1 and U-2, a member with a seat has no outstanding request to obtain one

### C-24: The member-facing state for an accessible occurrence distinguishes every current booking or waitlist outcome
Observable: Check the occurrence in each case and distinguish these outcomes: confirmed booking, active offer with a seat held, waiting without an offer, or none of those three. An accessible cancelled or closed occurrence also shows its applicable class status. Past waitlist actions and the member's exact position in the queue are outside this required display because the member needs their current entitlement to decide whether to act.
Source: choice: let the member decide whether to wait, act, or attend using current status

### C-25: A waitlist opening is offered in order of successful join
Observable: Have eligible members A and B join in that order while a class is full. When one seat becomes allocatable while the class accepts bookings, A receives the first offer. Simultaneous joins and ineligible entries are covered by C-41 and C-47.
Source: choice: use the order in which the app accepted each request as the priority members can rely on

### C-26: A member accepts an offered seat through the ordinary booking confirmation flow
Observable: Open an active offer as its owner and complete the ordinary booking requirements before its deadline. The resulting seat is a confirmed class booking.
Source: choice: let members decide whether they can still attend and keep the existing confirmation requirements

### C-27: The app makes an active offer discoverable from the member's own booking or waitlist status
Observable: Return as the offered member and find the occurrence's offer, its deadline, and the available actions to claim or decline. External delivery through email, SMS, or push is outside the required notification surface because the request supplies no channel or contact preference.
Source: choice: provide a reliable place to retrieve an offer in the app

### C-28: The standard claim window is 15 elapsed minutes when the closing time permits
Observable: Observe an offer made 20 minutes before the waitlist closes. Its deadline is 15 elapsed minutes after it becomes available to view and claim. It is valid strictly before that deadline.
Source: choice: give the member time to respond while letting an unused seat reach the next person

### C-29: An offer's deadline cannot exceed the waitlist closing time
Observable: Observe an offer that becomes available 5 minutes before the waitlist closes. Its deadline is the closing time, 5 minutes after it becomes available.
Source: choice: prevent an offer from outliving the booking opportunity

### C-30: A member can decline their active offer
Observable: Decline your active offer. The offer ends and your own status shows no active waitlist entry.
Source: choice: let the member release a held seat as soon as their plans change

### C-31: A member can join again after their previous waitlist entry ends if the ordinary join conditions are met
Observable: Leave, decline, or let an offer expire. While the occurrence remains full and joinable, submit a fresh join and see a new waiting outcome.
Source: choice: let members change plans without restoring previously surrendered priority

### C-32: New admissions can be paused without interrupting outstanding waitlist requests
Observable: Pause admissions while a member is waiting or has an active offer. Existing entries continue to support status checks, withdrawal, sequential offers, claims, declines, expiry, and class closure.
Source: choice: allow a rollout to stop admitting members while honoring commitments already made

### C-33: The admission setting is deployment-wide
Observable: Pause admissions and attempt fresh joins for two different otherwise joinable occurrences. Both are paused.
Source: choice: provide one rollout control because no per-location or per-class segmentation was requested

### C-34: Admission is initially paused at rollout
Observable: Release the feature to an existing deployment. Before enabling admissions, fresh joins are unavailable.
Source: choice: let the operator choose when customers start taking on new waitlist commitments

### C-35: An operator can see the current admission setting
Observable: As an authorized operator, inspect the setting and distinguish enabled from paused without submitting a change.
Source: choice: let an operator verify rollout state without changing it

### C-36: An operator can see the number of outstanding offers for an occurrence
Observable: Inspect an occurrence before its first offer, then after one offer is issued but before its deadline. The active offer count changes from 0 to 1.
Source: choice: let an operator tell whether an apparent vacancy is held for a member

### C-37: Joining requires a currently identifiable occurrence
Observable: Submit a join with a missing, malformed, or unknown occurrence reference. The action reports that no valid occurrence was selected. Exact reference format and length are unconfirmed because the existing app contract is unavailable.
Source: implied: U-1 and U-6, a waitlist request must belong to an occurrence

### C-38: A first join is refused whenever a required condition is absent
Observable: Try a fresh join in each case: member identity missing or expired, occurrence reference missing or malformed, occurrence unknown or inaccessible, occurrence cancelled, waitlist closing time reached, existing eligibility check failed, member already booked, an ordinary seat available to that member, a request for more than the joining member's own seat, admissions paused, or service unable to establish or save the outcome. Each case yields the applicable sign-in, invalid or unavailable occurrence, ineligible, booked, direct-booking, unsupported seat request, paused, or service failure or unknown outcome. If multiple reasons apply, any applicable outcome is acceptable under the privacy rule in C-83. A repeat with an active entry is covered by C-45.
Source: choice: enumerate the refusals so each failed admission has a usable outcome

### C-39: An active offer holds one seat for its owner
Observable: With only one seat newly open, give member A an active offer. Member B cannot use ordinary booking to take that seat before A's offer ends.
Source: choice: make an offer a usable opportunity throughout its stated window

### C-40: The number of issued offers is limited by the seats currently allocatable
Observable: With 3 booking vacancies, 1 seat already held by an active offer, and 4 eligible members waiting, observe 2 additional offers. A booking vacancy is a seat within the occurrence's current effective booking capacity that is unoccupied by a confirmed booking. Existing capacity values are occurrence-specific and unconfirmed.
Source: choice: fill openings without promising any seat twice

### C-41: Concurrent joins have a stable relative priority for the duration of those entries
Observable: Have two eligible members join at the same time. Open 1 seat and observe who gets the offer. Revoke that offer by reducing capacity under C-63. After retries or a service restart, restore the seat. The same member gets the new offer. Which member wins an exact tie is left open because either arrived concurrently.
Source: choice: give simultaneous joins a consistent result without prescribing a tiebreaker

### C-42: A first join uses the occurrence's current availability when the outcome takes effect
Observable: Open a full class, then let the only confirmed member cancel before your fresh join takes effect. With no other claim on the opening, the join returns the direct-booking outcome. In the reverse race, a join already accepted for a full class is considered for the resulting opening.
Source: choice: handle stale class details without creating a waitlist entry for an immediately bookable seat

### C-43: A direct booking can use only seats left after eligible waiting members have been considered for newly allocatable seats
Observable: With A waiting, submit a direct booking as B when the sole occupied seat is released. If A remains eligible, the seat is held for A. With 2 newly vacant seats and A the only waiting member, B can book the other seat even if A's eligibility is still being checked.
Source: choice: let the waitlist honor its priority without blocking genuinely spare capacity

### C-44: A withdrawn entry cannot receive a later offer
Observable: Race a leave against allocation of the first opening. If the leave takes effect first, the withdrawn entry receives no offer. If allocation takes effect first, the leave returns the active offer so the member can decide whether to decline it. If the offer was already claimed, the leave returns the current confirmed booking.
Source: choice: respect committed withdrawals while keeping an already issued offer actionable

### C-45: A repeat join returns the current outcome of an already active entry
Observable: Retry the join while waiting or while offered a seat, including while new admissions are paused. The result is the existing waiting status or the existing offer with its current deadline. The retry itself cannot reset the deadline.
Source: choice: let members recover lost responses without changing their priority or claim window

### C-46: A fresh join following an ended entry takes a new place in the queue
Observable: Have A join ahead of B. Have A leave and rejoin while the class is still full. B gets the next opening.
Source: choice: make a rejoin a new commitment

### C-47: A member who definitively fails the current waitlist eligibility check is removed before that member can receive a new offer
Observable: Make the first waiting member ineligible by an existing member or class eligibility rule. When a seat opens, their waiting status ends and the next eligible member can be offered the seat.
Source: choice: keep an ineligible member from preventing other members from using the opening

### C-48: A temporary eligibility-check failure preserves the affected entry's priority
Observable: While checking the first waiting member, make the eligibility service unavailable. The entry stays waiting and the only vacant seat is withheld from competing bookings or offers until eligibility can be established. When service returns, the first member is considered using current eligibility.
Source: choice: treat an unavailable eligibility result as unresolved rather than as a disqualification

### C-49: A claim can confirm a booking only while its particular offer is active
Observable: Attempt to claim an offer after its deadline, after decline or revocation, after class cancellation or closure, or after the offer was used to book. The old claim cannot create a new booking, even if the member has another active offer.
Source: choice: keep stale or repeated actions from consuming a seat intended for a later opportunity

### C-50: The time a claim confirms determines whether it met the offer deadline
Observable: Start the confirmation flow just before the deadline. A booking confirmed before the deadline succeeds. A submission whose confirmation would take effect exactly at or after the deadline cannot use that offer.
Source: choice: give the claim boundary one meaning across devices and slow requests

### C-51: A definitively ineligible claimant loses their offer
Observable: Make the offered member fail an existing member or class eligibility rule before their claim confirms. The claim reports ineligibility, the offer ends, and the seat can reach the next eligible member.
Source: choice: apply current entitlement to the final booking without leaving a seat held for a member who cannot use it

### C-52: An uncompleted ordinary confirmation step does not consume the offer
Observable: While an offer is active, abandon the ordinary booking flow or encounter a recoverable failure in one of its confirmation steps. The member can retry on the same offer while it remains active.
Source: choice: allow recovery within the promised offer window

### C-53: Expiry ends an offer without requiring a member action
Observable: Leave an active offer unanswered until its deadline. At or after the deadline the status no longer shows an active offer, even if neither the owner nor an operator has interacted with it.
Source: choice: free a held seat when the response window ends

### C-54: A seat released from an offer is considered for allocation again while the class accepts bookings
Observable: With A offered a seat and B waiting, let A's offer expire, decline it, or invalidate A's eligibility during claim. B gets the opportunity if still eligible. With no waiting members, the released seat is available for ordinary booking.
Source: choice: make a vacated hold usable without depending on another cancellation

### C-55: A capacity increase creates waitlist opportunities while the class remains open for bookings
Observable: With capacity fully booked and 2 eligible members waiting, increase effective capacity by 1. Observe 1 offer to the first member.
Source: choice: use added seats the same way as seats freed by cancellations

### C-56: Restored service re-evaluates open occurrences for outstanding waitlist opportunities
Observable: Interrupt processing during a confirmed cancellation, a capacity increase, a decline, an expiry, or a revocation so that a new offer is not issued. Restore processing while the occurrence remains open and verify that current vacancies are considered for eligible waiting members without the original action being repeated by a member.
Source: choice: recover allocation from the current class and waitlist state after interruption

### C-57: A replayed or late availability change cannot create an offer for capacity that is no longer allocatable
Observable: Replay a cancellation or capacity increase after the resulting seat is already held or booked, or after the class ceased accepting bookings. No additional offer for that seat is created.
Source: choice: base allocation on current capacity and claimability

### C-58: Declining an offer affects only the specific offer the member acted on
Observable: Send a decline for a former offer after the same member gets another offer or completes the former claim. The newer offer or confirmed booking remains in place.
Source: choice: make a delayed decline safe to replay

### C-59: Closing time ends all unfulfilled entries for the occurrence
Observable: Reach the closing time with one member waiting and another holding an offer. Neither has an active waitlist entry at the boundary.
Source: choice: clear obligations that can no longer yield a booking

### C-60: A same-occurrence reschedule retains existing waiting priority while the occurrence is open continuously
Observable: Move the time of an open occurrence that remains open after the change. Its waiting members keep their relative priority under the newly displayed class time.
Source: choice: preserve the members' existing requests for the same occurrence

### C-61: A reschedule can shorten an existing offer only as needed to meet the new closing time
Observable: Reschedule an open occurrence so the new closing time falls before an offer's published deadline. The offer now ends at the new closing time. If the closing time moves later, the published deadline stays the same.
Source: choice: honor the issued window as far as the new class time permits

### C-62: A capacity reduction retains only the offers that still fit ahead of lower-priority offers
Observable: With 1 confirmed booking and 2 active offers, lower effective capacity to 2 if the existing app accepts that change. The higher-priority offer remains active for its original deadline, and the other ceases to hold a seat. If no vacancy remains, no active offer remains.
Source: choice: protect the earliest accepted requests when advertised capacity goes down

### C-63: A member whose offer is revoked solely by a capacity reduction returns to waiting at their previous priority
Observable: Revoke a member's offer through a capacity decrease. While the occurrence remains open, that member waits ahead of later joins. A later offer is a new offer with a new deadline.
Source: choice: preserve the member's priority when the reduction was outside their control

### C-64: A successful claim consumes the associated waitlist entry
Observable: Claim an active offer. In the outcome that confirms the booking, the member no longer has an active waiting entry or an active offer for that occurrence.
Source: choice: end the member's request the moment the obtained booking fulfills it

### C-65: A concurrent claim and decline resolve to a single outcome
Observable: Claim and decline the same active offer concurrently. If the claim confirms first, the booking remains. If decline ends the offer first, the claim cannot use it.
Source: choice: honor the first completed change to the seat opportunity

### C-66: Class cancellation takes precedence over an unconfirmed claim
Observable: Cancel the class before a pending claim would confirm. The pending claim yields no booking for the cancelled occurrence.
Source: implied: U-11, a cancelled class cannot offer a seat

### C-67: Reopening booking never reactivates entries previously ended by closure
Observable: Reschedule a previously closed occurrence so it accepts bookings again. Waiting requests and offers ended by the earlier closure stay ended.
Source: choice: avoid restoring lapsed commitments without members' involvement

### C-68: Waitlist actions honor the host app's session validity boundary
Observable: Use a session the host app classifies as expired or revoked. The waitlist rejects it the same way a protected booking action does. The session mechanism, timeout, and any grace period are unconfirmed.
Source: implied: U-6, the host app's existing session validity rule governs protected booking actions

### C-69: Claims use the host app's booking confirmation boundary for external steps
Observable: Where ordinary booking depends on a third party before confirmation, a waitlist claim stays unconfirmed until that ordinary confirmation condition is met. Whether such a dependency exists, its response timeout, and any synchronous completion limits are unconfirmed.
Source: implied: U-4, the host app's existing confirmation rule determines whether a booking exists

### C-70: A platform refusal to accept a request cannot appear as a successful waitlist action
Observable: If the deployment rejects a waitlist request before it can take effect, that request produces no success confirmation. The deployment platform, request-size limit, rate limit, connection concurrency limit, and request timeout are unconfirmed.
Source: implied: U-8, the platform request-acceptance rule bounds which actions reach the app

### C-71: An offer window starts only when its owner can view the issued offer and start a claim
Observable: Delay the work that makes an offer available. The claim window starts at the point when the offer becomes available to its owner, even if the owner checks later. The runtime's allocation scheduling limit, minimum timer granularity, and maximum outage duration are unconfirmed.
Source: choice: keep delivery delays from shortening the response window under C-28

### C-72: Production admission requires the host app's applicable production prerequisites
Observable: Attempt to start production admissions without a prerequisite the deployment requires for ordinary class booking. Fresh waitlist joins cannot become available until that prerequisite is met. The app's platform, production credentials, required approvals, configuration requirements, and any production capacity quotas are unconfirmed.
Source: implied: U-9 and U-12, the host deployment's production readiness rules also apply to the booking feature it hosts

### C-73: Existing class discovery continues to show the same scheduled occurrences
Observable: Compare the class listings and class details before and after rollout for an unchanged schedule. The same occurrences remain discoverable to the same members.
Source: implied: U-12, the request adds a way to handle full classes to the existing app

### C-74: Existing booking confirmation rules continue to govern direct booking
Observable: For an open occurrence with a seat available for direct booking, compare the same inputs before and after rollout. The app applies the same confirmation rules. The exact existing rules and their thresholds are unconfirmed.
Source: implied: U-5, the request adds an alternative to an existing booking flow

### C-75: Existing member cancellation rules continue to govern confirmed bookings
Observable: Compare cancelling the same kind of confirmed booking before and after rollout. Members retain the same cancellation permissions, deadlines, and outcomes for that booking. Existing cutoff values and any financial terms are unconfirmed.
Source: implied: U-11 and U-12, the waitlist reacts to released capacity while existing bookings keep their terms

### C-76: Existing class cancellation rules continue to govern confirmed bookings
Observable: Cancel a class with pre-existing confirmed bookings. Their statuses follow the same class-cancellation rules as before rollout. Existing cancellation status names and any financial terms are unconfirmed.
Source: implied: U-11 and U-12, pre-existing booking obligations still apply when the class is cancelled

### C-77: Existing capacity-edit rules continue to govern whether a class capacity change takes effect
Observable: Try an edit the existing app accepts and one it refuses. The same acceptance rules govern the edits after rollout. Existing permitted capacity ranges and overbooking rules are unconfirmed.
Source: implied: U-11, the waitlist responds to changes the existing booking app allows

### C-78: Waitlist rollout does not enroll members from existing data
Observable: Release the feature with future full classes, existing confirmed bookings, and past cancelled bookings. Every occurrence begins with 0 active waiting entries and 0 active offers.
Source: choice: create waitlist commitments only after a member acts

### C-79: A waitlist request never transfers between occurrences automatically
Observable: Cancel one occurrence and create a replacement with the same title and start time. The replacement has 0 inherited entries or offers.
Source: choice: a replacement is a separate booking opportunity that members can choose to join

### C-80: Direct booking and offer claims cannot increase confirmed bookings above effective capacity
Observable: Race multiple confirmations for the last seat, whether through simultaneous direct bookings, simultaneous claims, or one of each. At most one additional booking confirms. If the existing app allows a capacity reduction below the confirmed count, further confirmations wait for room within effective capacity.
Source: implied: U-1 and U-4, a full class has no further confirmed capacity

### C-81: A member can read only their own member-specific waitlist status
Observable: As one member, request the waitlist status for another member using either regular navigation or a changed action reference. The other member's identity, queue entry, order, offer, and deadline are not disclosed.
Source: implied: U-2, the status belongs to the signed-in member

### C-82: A member can affect only their own waitlist entry or offer
Observable: As one member, use a reference belonging to another member in a join, leave, claim, or decline. The other member's state is unaffected.
Source: implied: U-2 and U-3, the right to act belongs to the member whose request or seat is affected

### C-83: Inaccessible occurrences do not disclose waitlist details
Observable: Request details or actions against an occurrence the host app does not let the caller access. Compare with a request against an unknown occurrence. The outcomes reveal no private class title, schedule, membership, queue count, or offer details.
Source: implied: U-6, class access rules still apply through the waitlist

### C-84: Waitlist operator controls require authorized operator access
Observable: Attempt to inspect the admission setting, change it, view aggregate counts, view allocation recovery status, or check rollback readiness as an ordinary member. Operator-only information and actions remain unavailable. The host app's role names and exact authorization mechanism are unconfirmed.
Source: implied: U-9, U-10, and U-12, operator capabilities require operator authorization

### C-85: Waitlist actions cannot create extra financial obligations
Observable: Join, wait, receive an offer, leave, decline, or let an offer expire. None of those actions adds a charge, fee, or payment hold. Claiming follows the app's ordinary confirmation terms, whose amounts and payment rules are unconfirmed.
Source: choice: keep financial commitments within the booking action members already use

### C-86: A replayed claim cannot confirm a second booking
Observable: Submit the same claim twice or submit it concurrently from two devices. Observe at most 1 confirmed booking attributable to that offer.
Source: implied: U-4 and U-8, the opportunity is for one seat

### C-87: A replayed claim cannot incur an additional booking charge
Observable: If the existing confirmation flow charges for a booking, lose the response to a successful claim and retry it. The charge attributable to that claim is no greater than for one ordinary booking under the existing terms. The amount is unconfirmed.
Source: implied: U-4 and U-8, a booking made once incurs its ordinary terms once

### C-88: Rolling back preserves confirmed bookings made by waitlist claim
Observable: Claim a seat successfully, reach rollback readiness, and return to the previous app version. View the confirmed booking through the ordinary booking flow.
Source: implied: U-12, fulfilling a waitlist request creates a booking the older app must still honor

### C-89: Availability-changing actions preserve existing confirmed bookings unless the action ordinarily changes them
Observable: Run waitlist joins, leaves, offers, declines, expiries, or revocations against an occurrence with confirmed bookings. The confirmed bookings remain intact. Ordinary booking cancellation or class cancellation can still change them under existing rules.
Source: implied: U-1 and U-12, the waitlist covers openings rather than already assigned seats

### C-90: An acknowledged waitlist change survives ordinary service interruption
Observable: Receive confirmation of a join, leave, offer, decline, or claim, then reconnect after interruption. The resulting status reflects the acknowledged change unless a subsequent valid transition occurred.
Source: implied: U-8, a successful status change must remain meaningful after reconnecting

### C-91: Rollback readiness requires paused admissions
Observable: With 0 active waiting entries and 0 active offers, check rollback readiness with admissions enabled, then with admissions paused. Only the paused setting meets the admission condition.
Source: choice: prevent new commitments from racing an operator's rollback

### C-92: Rollback readiness requires zero active offers
Observable: With paused admissions and 0 waiting members, check readiness while 1 offer is active. That offer prevents readiness until it ends or the claim confirms.
Source: choice: treat a held seat as an outstanding obligation

### C-93: Rollback readiness requires zero unresolved booking confirmations started through an offer
Observable: After the last offer expires, check readiness while a claim's ordinary confirmation outcome is still unresolved. Readiness stays false until the outcome is settled. A claim is settled once it is confirmed or has failed with any provisional booking or financial effects cleared.
Source: choice: protect claims that began before the waitlist drained

### C-94: Rollback readiness is evaluated using the combined current conditions
Observable: An authorized operator sees ready only when admissions are paused, active waiting entries total 0, active offers total 0, and unresolved offer confirmations total 0. If the app cannot establish any of these conditions, readiness is unavailable.
Source: choice: give operators a definitive readiness result without forcing an active class to clear its queue

### C-95: A failed admission setting change leaves the previous effective setting in force
Observable: Interrupt a pause or enable request before it takes effect. A subsequent read shows the prior setting.
Source: choice: keep the effective state predictable when a setting change cannot be completed

### C-96: A join takes effect only if the deployment was accepting new admissions at that point
Observable: Race a fresh eligible join with a pause. A join accepted before the pause remains in effect. A fresh join reaching the admission decision at or after the pause is refused until admissions resume.
Source: choice: make pause effective for new commitments at a definite boundary

### C-97: The operator can distinguish a current allocation result from one awaiting recovery
Observable: For an occurrence the operator can inspect, observe each of these states: no unresolved allocation, allocation pending or awaiting recovery, or allocation status unavailable. Pending includes an unresolved eligibility or availability change that stands between waiting members and an opening.
Source: choice: let an operator distinguish a drained or full occurrence from one with unresolved work

### C-98: An unverified action result is distinguishable from a definitive refusal
Observable: Lose the result after submitting a join, leave, claim, or decline. If the app can respond but cannot establish the final outcome, it communicates that the result is unknown. Once the app returns, the member can check their current status.
Source: choice: avoid leading members to act on a false assumption that their change failed

### C-99: Unavailable member status is distinguishable from having no waitlist entry
Observable: Make the service for retrieving a member's current status unavailable. The app reports that it cannot retrieve status instead of presenting an empty status as current.
Source: choice: keep a status outage from making a member believe their seat opportunity disappeared

### C-100: A leave applies only to the waiting entry the member acted on
Observable: Have a leave succeed for entry A. Rejoin to create entry B, then deliver a delayed repeat of the leave for A. Entry B remains active.
Source: choice: a late request must not withdraw a newer commitment

### C-101: A replay of a previously accepted join cannot create a later waitlist entry
Observable: Deliver the same accepted join after its entry ended by withdrawal, decline, expiry, ineligibility, confirmed claim, or closure. No new entry is created by that replay. A deliberate new join can create a new entry under C-31. The rule applies whenever the host accepts the replay for processing. The host's replay or retry limits are unconfirmed.
Source: choice: require fresh intent after the previous request ended

### C-102: A replay of a successful claim returns the previously confirmed booking while that booking remains confirmed
Observable: Lose the response to a successful claim. Retry the claim while the booking is still confirmed and see that booking as its outcome.
Source: choice: let the member recover a successful claim result without booking again

### C-103: A failed claim leaves the member with no booking-related financial commitment from that attempt
Observable: Where ordinary booking can take payment during confirmation, force a claim to fail after a provisional payment step. Once the app reports the outcome as settled, any provisional charge or hold has been cleared under the ordinary failed-booking terms. The applicable terms and settlement timing are unconfirmed.
Source: choice: preserve ordinary failed-booking financial treatment when an offer cannot confirm

### C-104: A claim uses the app's authoritative occurrence time at its confirmation boundary
Observable: Set one member device ahead of the offer deadline and another behind it. Identical claims evaluated at the same authoritative time have the same time eligibility independent of device clocks. Time precision finer than the app's authoritative clock is unconfirmed.
Source: choice: apply the same deadline to members in different device time settings

### C-105: An expired or otherwise unavailable offer has a visible unavailable outcome on access
Observable: Open the old offer directly after it expires, is declined, is revoked, or closes with the class. The result identifies the offer as unavailable to claim. The app can also show the member's current class status under C-24.
Source: choice: give a member returning to an old offer a definite result without requiring a history view

### C-106: Waitlist policy adds no separate member-wide quota
Observable: Join a second full occurrence while waiting for an unrelated first occurrence. The first waitlist entry alone does not prevent the second join. Existing rules for eligibility across multiple classes still apply, and their numeric thresholds are unconfirmed.
Source: choice: preserve independent opportunities for different sessions

### C-107: Allocation can recover without an original participant returning to the class
Observable: Release a seat for an eligible waiting member while nobody has the class open. On the next successful status read, the member sees the offer if an eligible opportunity remains. The allocation interval imposed by a deployment runtime is unconfirmed.
Source: choice: make allocation depend on openings rather than repeat member requests

### C-108: Seats held by active offers count as unavailable to a fresh joiner's ordinary booking
Observable: In a class with one confirmed vacancy, give A the corresponding offer. Eligible member B, who has no offer, sees the class as full for their own booking and can join if the other join conditions hold.
Source: choice: keep the waitlist available to people who cannot directly book the held seat

### C-109: An offered member can use the held seat when they start booking from ordinary class details
Observable: As the offer owner, start booking from the occurrence's ordinary class details. The app recognizes the current offer and gives the member a route to claim it before its deadline.
Source: choice: honor the current offer across the existing booking entry point

### C-110: Each waitlist entry seeks one seat for the joining member
Observable: Submit a join requesting seats for multiple people. The waitlist does not accept the group as one entry or create offers for other people. Existing group or guest booking terms, if any, keep their ordinary direct-booking scope and their numerical limits are unconfirmed.
Source: choice: keep each offer attributable to the member who requested it

### C-111: A failed schedule or capacity edit does not change the waitlist
Observable: Attempt an edit rejected by the existing booking app. Confirm that the attempted edit did not change an active offer's deadline, a waiting member's priority, or which seats are held.
Source: choice: apply waitlist effects only to class edits that take effect

### C-112: An occurrence permanently removed from booking ends its active waitlist entries
Observable: If the host supports removal separate from cancellation, remove an occurrence with a waiting member and an outstanding offer. Neither entry can later receive or claim a seat. What past details remain visible follows the host's existing class-access rule.
Source: choice: end obligations for a class that can no longer provide any seat

### C-113: Rollback starts only while the deployment meets its rollback readiness conditions
Observable: Request a rollback after a ready check, but resume admissions before rollback takes effect. The rollback cannot start while admissions are enabled. If rollback starts first, admissions cannot reopen on that deployment during the rollback.
Source: choice: prevent an outdated ready check from stranding new entries

### C-114: An ordinary restart preserves the effective admission setting
Observable: Restart a deployment after enabling admissions, then repeat while admissions are paused. Each restart retains the setting already in force.
Source: choice: keep rollout intent through ordinary service recovery

### C-115: A live offer ends once even if several end conditions occur together
Observable: Deliver expiry, decline, and capacity revocation for the same offer concurrently. The offer has one effective end. A revocation that takes effect while the offer is active can restore the entry under C-63. Expiry or decline that takes effect first leaves the entry ended.
Source: choice: avoid both resurrecting a departed member and releasing one seat several times

### C-116: The app uses the existing class access policy for member waitlist actions
Observable: Change a member's ordinary access to an occurrence while they have an entry. Once that access is lost, a saved waitlist action cannot let the member claim a seat or read its protected details. The host's access categories and qualification thresholds are unconfirmed.
Source: implied: U-2 and U-6, the waitlist remains within the occurrence's existing access boundary

### C-117: An unresolved eligibility check withholds at most the openings the waiting entries could use
Observable: With 3 vacancies, no active offers, and 2 waiting members, make the earlier member's eligibility temporarily unavailable. The app issues no newer offer ahead of that member and withholds 2 vacancies for the waiting members. The third remains available for direct booking.
Source: choice: preserve the waiting members' places without keeping spare seats out of ordinary booking

### C-118: A definitive loss of access counts as ineligibility when the app checks an outstanding entry
Observable: Revoke a waiting member's class access before an opening appears. Once the app establishes the loss of access, the entry ends rather than blocking the opening. If the loss is established during an offer claim, the offer ends under C-51 without disclosing protected class details.
Source: choice: make current class access part of the eligibility check for existing requests

### C-119: An unsuccessful claim identifies an applicable reason without exposing another member's seat entitlement
Observable: Try a claim in each case: invalid session, missing or malformed offer reference, unknown offer, another member's offer, expired or otherwise ended offer, occurrence no longer accessible or bookable, definitive ineligibility, incomplete ordinary confirmation, unavailable confirmation service, or a settled unsuccessful booking response. The app returns the applicable sign-in, unavailable, ineligible, incomplete, or failure or unknown outcome. Unknown offers and unauthorized access to another member's offer disclose the same information. Offer reference format and length are unconfirmed.
Source: choice: give the member the outcome they can act on without revealing private offers

### C-120: An unavailable operator count is distinguishable from zero
Observable: Compare an occurrence with zero entries or offers to an occurrence whose entry or offer count cannot be retrieved. For an unavailable count, the operator sees that it is unavailable.
Source: choice: prevent unavailable data from making the operator conclude that commitments have cleared

### C-121: An admission setting request reports whether its effect is known
Observable: As an authorized operator, submit an enable or pause request. Distinguish three response outcomes: applied, definitively rejected, or unable to establish whether it applied. After service recovers, the current setting can be checked under C-35.
Source: choice: let operators resolve a setting change interrupted after submission
