## Use cases

### U-1: A member joins a full class to stay in consideration for a seat
Flow: The member opens a specific class session in the booking app. When capacity is the only obstacle and the waitlist is open, the member chooses to join and sees their waiting status. The first member can join an empty waitlist. A later member can join an existing waitlist. A class with no remaining seats and one with room are handled according to current availability.
Source: request

### U-2: A waiting member checks their status to know whether they have a seat
Flow: The member returns to the app or uses another signed-in device. They can find their current waitlist status for the session. If promoted, they see the ordinary confirmed booking. A member with no active entries can tell that they are waiting for no sessions.
Source: implied: the waitlist must remain useful after the member leaves the class page

### U-3: A waiting member withdraws to stop being considered for a seat
Flow: The member opens their waitlist entry and leaves. The app shows the resulting status. If the entry already became a booking, the member can use the existing booking cancellation action subject to its normal rules.
Source: implied: U-1 records intent that a member may withdraw

### U-4: A waiting member receives a seat when space opens
Flow: A booking cancellation or another change releases space before booking closes. The next eligible waiting member receives a confirmed booking automatically and can discover the result. If nobody eligible is waiting, the seat can be booked normally.
Source: request

### U-5: A member recovers from an unsuccessful or uncertain waitlist action
Flow: The member encounters an invalid session, insufficient permission, a booking restriction, a changed class, or an unavailable service. The app gives the applicable outcome or explains that the result is uncertain. The member can check their current status and repeat an action safely where it still applies.
Source: implied: joining or leaving can fail or be interrupted

### U-6: A member books an available session through the existing flow
Flow: The member selects a session with a seat available for ordinary booking and completes the existing steps. They receive the usual booking result. If the last seat has already gone, they can choose to join the waitlist when eligible.
Source: implied: the request adds a waitlist to an existing booking app

### U-7: Authorized staff change a scheduled session to manage availability
Flow: Using existing scheduling actions where supported, staff adjust capacity, cancel a session, or change its scheduled details. The affected waitlist follows that session's updated availability or closes when the queued commitment can no longer be honored. Rejected staff changes retain their existing effect.
Source: implied: U-4 depends on the session's bookable seats and lifecycle

### U-8: An operator enables or disables the waitlist to control rollout
Flow: The operator enables it for the app. Existing sessions and confirmed bookings carry over. The operator can see whether it is enabled. When disabling the feature or returning to the prior version, the operator resolves outstanding waitlist commitments before ordinary booking proceeds without waitlist priority.
Source: implied: the existing app already serves sessions and bookings before rollout

### U-9: An operator detects and recovers a waitlist interruption
Flow: The operator checks whether waiting members are blocked from receiving available seats. After restoring the required booking service, the operator sees eligible waiting members processed under current rules. A finished session receives no late promotion.
Source: implied: U-4 relies on the booking service and must survive interruptions

### U-10: A member checks how waiting ended when a session or eligibility changes
Flow: The member returns to the app after an unfulfilled entry ends. If the session remains visible, the outcome explains whether waiting ended because of a session change, the booking deadline, or an applicable booking restriction. If the session is no longer open, an older page cannot start a new waiting commitment for it.
Source: implied: U-2 and U-7 can end waiting without a booking

## Clauses

### C-1: A member can join a waitlist for an otherwise bookable full session
Observable: With capacity as the sole obstacle for the member, opening the full session in the booking flow offers an explicit join action while its waitlist is open.
Source: request

### C-2: A successful join is acknowledged as waiting
Observable: Join a full session that stays full through the action. The result identifies the session as one the member is waiting for.
Source: implied: U-1 needs an acknowledged result

### C-3: Waiting by itself confers no right to attend
Observable: While waiting, the member has no confirmed admission for that session in the normal booking view.
Source: implied: a waitlist exists because confirmed capacity is already occupied

### C-4: A member can retrieve their own active waitlist status after joining
Observable: Reopen the app under the same account after a successful join while the session remains full. The member can find that session as waiting.
Source: implied: U-2

### C-5: A member can end their active waitlist entry
Observable: Leave an entry that is still waiting. A subsequent current status check shows that the member is no longer waiting for that session.
Source: choice: self-service withdrawal lets a member give up interest without staff assistance

### C-6: Space in a bookable session triggers a path from waiting to obtaining a seat
Observable: With a member still eligible and waiting, free a seat before booking closes. The member can obtain a confirmed seat through the waitlist without starting over in ordinary booking.
Source: request

### C-7: Promotion confirms a booking without a separate claim step
Observable: Free capacity for a waiting member selected under the waitlist rules while booking remains open. The ordinary booking view shows a confirmed booking without the member accepting a later offer.
Source: choice: the explicit join authorizes a normal booking and removes the delay of a claim round

### C-8: An available seat with an empty waitlist remains bookable through the existing flow
Observable: For an open session with an available seat and an empty waitlist, an eligible member can complete the existing booking flow.
Source: implied: U-6

### C-9: A refused waitlist action communicates the obstacle when it can be disclosed
Observable: Attempt to join while the session is visible but booking has closed. The result explains unavailability in terms of the closed session.
Source: choice: actionable feedback prevents repeated futile attempts without exposing restricted details

### C-10: Existing confirmed bookings survive waitlist enablement
Observable: Enable the waitlist while a session has a confirmed booking. Its holder can still find the same confirmed reservation.
Source: implied: adding a waitlist shall preserve existing bookings

### C-11: The operator can switch on waitlisting across the app
Observable: An authorized operator enables the feature. An otherwise eligible member can then see the join action on an eligible full session.
Source: choice: one app-wide control is enough for rollout

### C-12: The operator can close waitlisting across the app
Observable: An authorized operator disables the feature. A fresh attempt to join any session is refused as unavailable.
Source: choice: the same rollout control gives operators a way to stop taking commitments

### C-13: Cancelling a session ends its active waitlist entries
Observable: Cancel a future session with a waiting member. The member's current result for that session is no longer waiting.
Source: implied: U-7 removes the possibility of a seat in that session

### C-14: Acknowledged waiting survives a temporary service interruption
Observable: Join successfully before a restart or temporary outage. After recovery, the member is still waiting if no valid intervening outcome ended the entry.
Source: implied: the waitlist must retain the member's place until it is resolved

### C-15: The operator can detect that waitlist processing needs attention
Observable: Leave a bookable session with available capacity and active demand that the app cannot process due to an ongoing booking failure. The operator can distinguish that condition from a healthy full session.
Source: choice: make unresolved demand visible to the people who can restore booking

### C-16: Each waitlist applies to one bookable occurrence of a class
Observable: Join one of two sessions with the same class name. Only the selected occurrence appears as waiting.
Source: implied: U-1 asks for a place in a specific session

### C-17: Members can identify the occurrence associated with a waitlist result
Observable: Open a waitlist result for one of two same-named sessions. The app provides enough session details to distinguish the intended occurrence.
Source: implied: C-16 must be usable for recurring or similarly named classes

### C-18: An otherwise open session is full when it has no seats available for ordinary booking
Observable: Compare an open, empty-waitlist session with 0 remaining seats to a similar session with 1 remaining seat. The booking app treats the first as full.
Source: implied: the request triggers the waitlist when a class is full

### C-19: The waitlist uses the app’s existing session visibility restrictions
Observable: Try to open the waitlist for a session that the account cannot view through ordinary booking. The response reveals no restricted session details.
Source: implied: U-1 adds an action within the existing booking app

### C-20: Only an authenticated member can create a waitlist entry for their account
Observable: Try joining while signed out or after the member session expires. The action requires sign-in before creating an entry.
Source: choice: reuse the booking account so the app can associate any resulting booking with its owner

### C-21: An unrecognized session reference cannot create a waitlist entry
Observable: Submit a request for a malformed, unknown, or deleted session reference. The action is refused for the supplied reference.
Source: implied: C-16 requires a real occurrence

### C-22: Joining requires meeting the non-capacity conditions for ordinary booking
Observable: Try joining a full session with a known disqualifying restriction such as missing membership access, where the app enforces it. The action does not create a waiting entry.
Source: choice: waitlisting removes the capacity obstacle only

### C-23: Promotion requires meeting the current non-capacity conditions for ordinary booking
Observable: Join while qualified, then become ineligible under an existing booking rule before a seat opens. The app creates no booking for that member while the rule prevents booking.
Source: choice: apply the same booking rules at fulfillment as at entry

### C-24: Joining makes the possibility of automatic confirmation clear before consent
Observable: Before choosing to wait, the member can see that a seat may become an ordinary confirmed booking without a further claim step.
Source: choice: the member needs to know the commitment made by joining

### C-25: The member can review applicable booking obligations before joining
Observable: For a session with a charge, credit use, or cancellation terms in normal booking, the member can review the applicable obligations before choosing to wait.
Source: choice: advance consent must cover the obligations of the resulting booking

### C-26: A waitlist join consumes no booking payment or credit
Observable: Compare the member’s booking charges or credits before and after joining a session that stays full. The join itself produces no booking charge or credit use.
Source: choice: defer any booking obligation until a seat is confirmed

### C-27: Automatic confirmation requires prior authorization for all steps the ordinary booking requires
Observable: Attempt to join where a mandatory approval or payment step cannot be authorized in advance through the existing app. The app explains that automatic booking is unavailable for that member or session.
Source: choice: preserve existing requirements without introducing a separate offer or payment workflow

### C-28: A member has at most one active entry for an occurrence
Observable: Join the same session twice while remaining eligible and while it remains full. The member has one active entry after both attempts.
Source: choice: one queue place per account per occurrence prevents duplicate demand

### C-29: An existing confirmed booking makes the same member ineligible to wait for that occurrence
Observable: With a confirmed booking already held by the member, request to join the full session. The member gains no active queue place.
Source: choice: this waitlist accepts one request for the member’s own seat per occurrence

### C-30: The active waitlist view has a distinguishable empty state
Observable: With no active entries, open the member’s waitlist status. The result makes clear there are 0 sessions currently waiting.
Source: implied: U-2 must distinguish no entries from a failed lookup

### C-31: The waitlist adds no product-level maximum number of entries per session
Observable: With a full session accepting joins, another distinct eligible account can join despite the number already waiting, subject to the app’s actual operating limits.
Source: choice: no business cap is needed to distribute confirmed seats

### C-32: Promotion order follows acceptance order among eligible active waiters for the same occurrence
Observable: Join as A and then as B, wait for both acknowledgments, then free one seat while both remain eligible. A is selected before B.
Source: choice: first in, first out gives members predictable priority without a ranking policy

### C-33: A promoted member can discover the confirmed seat in the app
Observable: After promotion, the member can find the confirmed seat through their ordinary booking view even if the client that joined is closed.
Source: implied: U-2 needs a reliable way to learn that waiting produced a seat

### C-34: The app makes a promotion apparent to the member without requiring them to inspect their former entry
Observable: Promote a waiting member while their app is closed. On returning, the member can find an in-app indication of the promotion tied to the session.
Source: choice: show the change in the app without requiring a new delivery channel

### C-35: The waitlist deadline is the earlier of the session’s ordinary booking cutoff and its scheduled start
Observable: For a session with a booking cutoff earlier than its start, that cutoff is the boundary before which joining is still possible. For a session with no earlier cutoff, the scheduled start is that boundary.
Source: choice: use the existing booking cutoff with the session start as the latest possible boundary

### C-36: Active waitlisting begins only during the session’s ordinary booking window
Observable: Open a full visible session before its booking window opens. The member cannot yet join.
Source: choice: avoid new reservation rights before ordinary bookings open

### C-37: A session that reaches its waitlist deadline has no active waiters
Observable: Let an occurrence reach its waitlist deadline with an unpromoted member. The member’s current outcome is closed without a seat when they check the visible session after the deadline.
Source: choice: expiry resolves an intent that can no longer produce a booking

### C-38: Rejoining after withdrawal is a new entry
Observable: Have A join, B join, A leave, then A join again while the session is full. When one seat opens with both eligible, B receives priority.
Source: choice: preserve uninterrupted waiting ahead of renewed interest

### C-39: The member’s waitlist status distinguishes a concluded entry from an unavailable status lookup
Observable: End a previously acknowledged entry and reopen the app while the associated session is still visible and upcoming. The member can determine that the prior request is no longer waiting.
Source: choice: allow a member to resolve what happened without prescribing indefinite history

### C-40: Opening capacity through an existing capacity increase triggers promotion
Observable: Increase a full session’s capacity by one while an eligible member is waiting during the booking window. The waiter is promoted.
Source: choice: treat newly added capacity like a released booking

### C-41: Promotion fills multiple newly available seats up to eligible waiting demand
Observable: Release 2 seats in one change with 3 eligible members waiting. Exactly 2 become booked through the waitlist.
Source: choice: use all the seats released to the queue

### C-42: An ordinary booking cannot take a seat owed to an eligible earlier waiter
Observable: With an eligible waiter and 1 newly available seat, race an ordinary booking attempt against promotion. The new caller cannot obtain that seat ahead of the waiter.
Source: choice: enforce queue priority across booking paths

### C-43: An available seat in excess of unresolved waiting demand can be booked normally
Observable: With 2 bookable seats and 1 unresolved waiting entry, an otherwise eligible ordinary booker can take 1 seat during the booking window.
Source: choice: preserve access to seats the queue cannot fill

### C-44: A stale join action with a free ordinary booking seat returns the member to ordinary booking
Observable: Load a join action when the class is full. Free an ordinary booking seat before the member submits. The action directs the member to ordinary booking.
Source: choice: joining a queue does not substitute for the ordinary booking flow when queueing is unnecessary

### C-45: A booking attempt that loses the last seat offers a separate waitlist join
Observable: Two members contend for the only seat with no active waiters. The eligible member who loses the seat can choose the join action if waitlisting is open.
Source: choice: offer the same opt-in at a point where stale availability would otherwise turn the member away

### C-46: An ordinary booking attempt never joins a waitlist by itself
Observable: Submit an ordinary booking attempt for a session whose last seat has just been taken. The member has no active entry unless they separately accept the waitlist commitment.
Source: choice: automatic promotion requires an explicit opt-in

### C-47: Simultaneous joins for the same account share one active entry
Observable: Submit join from two devices under one account while the session stays full. Subsequent status for that occurrence shows exactly 1 active entry.
Source: implied: C-28 must hold across devices and overlapping actions

### C-48: Ties between distinct accepted joins have a stable resolution
Observable: Accept two concurrent joins, free one seat, then interrupt the first member’s confirmation at a booking dependency that can distinguish the member being processed. Restore that dependency. The member whose confirmation was interrupted retains first priority.
Source: choice: resolve concurrent joins once without imposing a member-facing tie-break formula

### C-49: Repeating a join while its original entry is active retains the original priority
Observable: Have A join, then B join, then A repeat the join while the session stays full. When one seat opens with both eligible, A is selected first.
Source: choice: a repeated join is a status recovery path

### C-50: A completed withdrawal prevents subsequent promotion of that entry
Observable: Have a member successfully withdraw immediately before another booking releases capacity. The withdrawn member receives no booking from that entry.
Source: implied: U-3 ends the member’s consent to be promoted

### C-51: A withdrawal that arrives after confirmation reports the booking outcome
Observable: Submit a leave request from a stale waiting view after promotion has won the race. The result identifies the confirmed booking as the member’s current state.
Source: choice: resolve the race in terms of the state the member must now act on

### C-52: Withdrawing a stale entry never cancels a confirmed booking
Observable: Send a leave action for an entry that has already become a booking. The booking stays confirmed until acted on through ordinary cancellation.
Source: choice: booking cancellation may carry different terms and requires its own action

### C-53: Retransmission of a completed withdrawal has no further effect
Observable: Complete a leave then submit the same leave again. The member remains withdrawn when there has been no new join.
Source: implied: U-3 should tolerate repeated attempts to stop waiting

### C-54: An action for an earlier entry cannot withdraw a later entry
Observable: Leave an entry, rejoin while the session is full, then deliver an old leave for the first entry. The new entry remains active.
Source: implied: C-38 creates a different commitment

### C-55: A duplicate of an earlier join cannot create a new entry after that entry ends
Observable: Delay a duplicate of an accepted join until after the member leaves. The old action does not place the member back in the queue.
Source: implied: U-3 revokes the earlier intent

### C-56: An uncertain response is distinguishable from confirmed success
Observable: Interrupt the response to a join or leave after submitting it. If the current outcome cannot be obtained, the result indicates that completion is unconfirmed.
Source: choice: a dropped response is insufficient evidence of either success or definitive refusal

### C-57: A recovered status lookup resolves an uncertain earlier action
Observable: Lose the response to a submitted action. After service returns and the action settles, open the normal waitlist status and see the resulting current state.
Source: implied: U-5 needs a way to recover from an uncertain response

### C-58: A definitively failed join leaves no new active entry
Observable: Force rejection before join can succeed, then restore service and check the member’s status. The failed attempt created 0 active entries.
Source: implied: U-5 distinguishes a definite rejection from an uncertain result

### C-59: A definitively failed withdrawal leaves the pending intent in force
Observable: Force a leave to fail definitively while the session stays full. On recovery the member is still waiting.
Source: implied: U-3 requires an effective withdrawal before it ends intent

### C-60: A member found ineligible for a released seat stops waiting
Observable: Make the first waiter ineligible under a current ordinary booking restriction, then release a seat before the deadline. The ineligible member’s active entry ends when evaluated for that seat.
Source: choice: a confirmed eligibility failure resolves the request and allows the queue to progress

### C-61: A member can learn that an entry ended for a known booking restriction
Observable: After an entry ends for a restriction that can be disclosed to its owner, check its outcome while the session remains visible. The result distinguishes ineligibility from voluntary withdrawal.
Source: choice: the member needs to know whether correcting eligibility could help before a fresh join

### C-62: A definite rejection of the first waiter allows the next eligible waiter to use the seat
Observable: With A ahead of B, make A definitively ineligible then free a seat. B can be promoted without A taking any seat.
Source: choice: one member’s ineligibility must not waste capacity

### C-63: An indeterminate booking dependency failure retains the affected active entry
Observable: Break the dependency used to complete the first waiter’s booking without a definitive rejection. During the interruption that entry remains waiting unless another valid event ends it.
Source: choice: temporary unavailability should not take away an accepted queue place

### C-64: A temporarily blocked earlier waiter retains priority over later waiters
Observable: With A ahead of B and 1 seat available, temporarily prevent verification or completion for A. B does not receive that seat while A’s higher-priority result remains unresolved.
Source: choice: a dependency failure should not silently reorder waiting commitments

### C-65: A recovered booking dependency resumes promotion without a fresh member action
Observable: Restore the failed dependency with an open session, a free seat, and an eligible waiting member. That member can be promoted without rejoining or relying on a second cancellation.
Source: choice: an accepted queue commitment survives transient processing failures

### C-66: Promotion uses only booking obligations the member authorized at join
Observable: Change the charge, credit cost, or cancellation terms to require a new authorization before opening a seat. The previously waiting member receives no automatic booking on the changed terms.
Source: choice: promotion cannot substitute for acceptance of materially changed obligations

### C-67: An entry ends when the released seat requires new authorization from its member
Observable: After an obligation changes in a way that needs renewed consent, release a seat and evaluate the prior entry. The member can see that the old entry ended because its consent no longer applies.
Source: choice: do not hold up released capacity while waiting for renewed consent

### C-68: An unsuccessful promotion leaves no unreconciled charge or consumed credit
Observable: Interrupt a promotion that ultimately produces no booking. After recovery the member has no net booking charge or consumed credit attributable to that attempt.
Source: implied: C-26 defers payment or credit use to confirmed booking

### C-69: An unresolved payment outcome cannot produce a repeated booking charge
Observable: Interrupt promotion after a payment may have succeeded, then recover and retry processing. The member incurs at most the ordinary charge for one confirmed booking.
Source: implied: C-7 produces one ordinary booking

### C-70: Promotion cannot consume more seats than the session makes available
Observable: Free 1 seat while concurrent promotion or booking attempts target it. At most 1 net additional confirmed booking fills the vacancy.
Source: implied: the waitlist uses existing limited capacity

### C-71: A promotion is reflected as a booking instead of active waiting
Observable: Once the booking is confirmed, retrieve current waitlist status for the same member and occurrence. The entry no longer appears as active, including when follow-up work is interrupted.
Source: implied: C-29 applies once a confirmed reservation exists

### C-72: Repeat processing of the same opening does not allocate an additional seat
Observable: Process the same 1-seat opening again after promotion while there have been no other availability changes. No additional waiter is confirmed.
Source: implied: C-70 enforces actual capacity on repeated triggers

### C-73: An ordinary booking cancellation after promotion does not restore the member’s queue place
Observable: Cancel an allowed confirmed booking received through promotion. The former waiter has no active waiting entry unless they explicitly join again.
Source: choice: booking cancellation does not renew consent to wait

### C-74: A capacity decrease affects promotions using the resulting availability
Observable: Reduce capacity before a pending promotion is confirmed so that the seat is no longer available. No waiter is confirmed against the removed seat.
Source: implied: C-18 depends on current capacity

### C-75: A capacity edit alone creates no new authority to revoke confirmed reservations
Observable: Reduce capacity through an existing staff action. Holders of confirmed bookings receive the same treatment as they would under that capacity change before waitlisting existed.
Source: implied: the waitlist adds a path to obtain a seat within existing booking rules

### C-76: A session start-time change ends existing waiting commitments
Observable: Change the scheduled start instant while there are active waiters. Those entries end even if the occurrence identity stays the same.
Source: choice: a member’s consent to wait is for the original start time

### C-77: A venue change ends existing waiting commitments
Observable: Change the advertised venue while there are active waiters. Those entries end even if the occurrence identity stays the same.
Source: choice: a member’s consent to wait is for the original venue

### C-78: An edit that leaves session timing, venue, and bookability intact preserves waiting priority
Observable: Correct a title typo without otherwise changing the occurrence or its terms. The queued members retain their relative priority.
Source: choice: a cosmetic edit creates no new commitment

### C-79: A withdrawn or closed entry is never revived by reopening a session
Observable: After an entry ends because the session closed, reopen booking for the session if the existing app allows it. The earlier entry stays ended.
Source: choice: ended commitments require a fresh join

### C-80: A deleted session cannot receive a promotion
Observable: Delete a waitlisted session using the existing app, where deletion is supported, then process a delayed signal that a seat had opened. No booking is created.
Source: implied: C-16 requires an existing occurrence

### C-81: Promotion uses the session’s current deadline at confirmation
Observable: Delay an opening that occurred before the deadline until processing would confirm at or after the deadline. The waiting member receives no new booking from that opening.
Source: choice: members need the existing booking time boundary to hold during delayed processing

### C-82: Session cancellation prevents in-flight promotion work from confirming a booking
Observable: Cancel the session before an in-progress promotion creates a confirmation. The member gains no confirmed seat.
Source: implied: U-7 removes the bookable occurrence

### C-83: A promotion completed before session cancellation follows the existing cancellation policy
Observable: Confirm a promotion before staff cancel that session. The already-confirmed member receives the same treatment as any other confirmed attendee.
Source: implied: C-7 produces an ordinary booking

### C-84: A runtime capacity rejection is reported as a waitlist availability failure
Observable: Reach a runtime limit on accepting another active entry, if the deployed app has one. The attempted join reports that waitlisting is unavailable for that attempt. The runtime and its exact supported volume are unconfirmed.
Source: choice: no product runtime was supplied to establish a numeric limit

### C-85: A platform deadline cannot be treated as confirmation of an unobserved result
Observable: Let a deployed request or processing deadline elapse before its result is known. The caller receives or can recover an uncertain outcome. The platform and applicable timeout figures are unconfirmed.
Source: choice: the app must handle its platform’s deadlines without guessing the booking outcome

### C-86: Waitlisting can be enabled only when the deployed app can honor accepted entries across interruptions
Observable: Attempt production enablement in an environment that cannot recover acknowledged entries. The operator sees that enablement is blocked.
Source: choice: the product runtime is unconfirmed and durable acceptance is a release prerequisite regardless of platform

### C-87: Waitlisting can be enabled only when ordinary booking can enforce waitlist priority in that environment
Observable: Attempt production enablement while an active booking entry point can allocate seats without honoring priority. The operator sees that enablement is blocked.
Source: choice: production rollout must protect accepted queue places on every ordinary seat allocation path

### C-88: Interrupted promotion work can be completed after its original request ends
Observable: End the cancellation or capacity-change request after its change has succeeded but before the eligible waiter can be booked. The waiter is still processed when the required service is available before the deadline.
Source: choice: the host’s synchronous execution window is unconfirmed and seat fulfillment must survive it

### C-89: Promotion works with the waiting member’s client closed
Observable: Close the waiting member’s client before the vacancy opens. The confirmed booking is created even if that member does not return until later.
Source: choice: the client may be suspended or offline while the class is filling

### C-90: A signed-in member can read only their own waitlist status through member access
Observable: From another member’s account, request an entry known to belong to someone else. The result reveals no information about that entry.
Source: implied: U-2 concerns the requesting member’s own status

### C-91: Member-facing waitlist information reveals no other waiters’ identities
Observable: As a member, inspect all visible waitlist information about a class. No other waiter’s identity or contact details are disclosed.
Source: choice: member access requires personal status only

### C-92: A member cannot withdraw another member’s entry
Observable: Submit a leave action under a different member account from the owner. The owner’s waiting state is unaffected.
Source: implied: U-3 withdraws the requesting member’s commitment

### C-93: Waitlist configuration changes require authorized operator access
Observable: As an ordinary member, attempt to enable or disable the feature. The app’s waitlist setting stays as it was.
Source: implied: U-8 is an operator action

### C-94: The current rollout setting is observable to an authorized operator
Observable: Read the rollout setting after an enable or disable action succeeds. The operator can tell whether the app is accepting new waitlist joins.
Source: choice: operators need to verify the effective setting

### C-95: Waitlist service health is restricted to authorized operational access
Observable: From an ordinary member account, attempt to read operational waitlist health. No privileged operational details are returned.
Source: choice: recovery visibility belongs to the people responsible for service operation

### C-96: Existing ordinary booking restrictions still apply when there is capacity
Observable: Try to book an available seat while violating a restriction previously enforced by the booking app. The same restriction still prevents booking.
Source: implied: U-6

### C-97: A waiting entry occupies zero confirmed seats
Observable: Compare confirmed attendance and capacity usage immediately before and after a successful join to a full session. The new entry adds 0 occupied seats.
Source: implied: waiting represents interest in a future seat

### C-98: Ordinary cancellation rules also govern a promoted booking
Observable: Try to cancel a promoted booking under a timing or fee rule that applies to ordinary bookings. The response follows the same cutoff or fee rule.
Source: implied: C-7 produces an ordinary booking

### C-99: Successful ordinary cancellation still releases its seat under the existing booking rules
Observable: Cancel a confirmed reservation with no active waiters. The seat becomes available to ordinary bookings at the same lifecycle point as before waitlisting.
Source: implied: U-6 and U-7 build on existing seat release

### C-100: Existing attendance access applies to promotions once confirmed
Observable: Have authorized staff consult the ordinary roster or attendance view if one exists. A promoted participant appears there as an ordinary confirmed attendee.
Source: implied: C-7 produces an ordinary booking

### C-101: Waitlisting does not change who may administer a scheduled session
Observable: Attempt an existing schedule edit without the permission required before waitlisting. The action is still refused.
Source: implied: U-7 uses existing scheduling actions

### C-102: A session without prior waitlist data starts with zero waiting entries
Observable: Enable the feature for a pre-existing session with bookings but no prior waitlist entries. A waitlist check finds 0 members waiting.
Source: implied: U-8 adds waitlisting without inferring consent from existing records

### C-103: Ordinary booking history remains accessible under the same rules after enablement
Observable: Enable waitlisting and revisit an existing past booking. Its visibility follows the same history rules as before enablement.
Source: implied: U-8 adds a feature to the existing booking app

### C-104: An ordinary booking cancellation remains effective if promotion cannot proceed
Observable: Successfully cancel a booking during a promotion dependency failure that does not prevent cancellation itself. The booking stays cancelled despite the failed promotion.
Source: implied: waitlist processing follows a released seat from ordinary cancellation

### C-105: Disabling waitlisting ends outstanding waiting entries
Observable: Disable the feature with active waiters. Affected entries stop waiting because the feature closed.
Source: choice: disablement resolves commitments before restoring ordinary access to released seats

### C-106: Disablement prevents in-progress promotions from confirming after it takes effect
Observable: Race a promotion with disablement. If disablement takes effect before a booking is confirmed, that promotion never confirms a booking.
Source: choice: operators must be able to stop new commitments and fulfillment at the same boundary

### C-107: Disabling waitlisting preserves already-confirmed promoted bookings
Observable: Disable the feature after a member’s promotion was confirmed. The member still holds that booking under its ordinary rules.
Source: implied: C-7 produces an ordinary booking

### C-108: Re-enabling waitlisting does not reactivate entries closed by disablement
Observable: Disable waitlisting with active entries and enable it again. The former waiters must choose to join again to become active.
Source: choice: feature closure ends each original commitment

### C-109: Rollback resolves accepted waiting entries before the old booking version serves seat allocations
Observable: With active entries present, take the operator’s rollback path. The prior version cannot admit ordinary bookers ahead of unresolved waiting commitments.
Source: choice: resolve the queue before returning to a version that cannot honor its priority

### C-110: Rollback preserves confirmed bookings created through promotion
Observable: After a promotion, roll back to the prior app version. The member still has their confirmed seat in ordinary booking.
Source: implied: U-8 returns to the existing app with ordinary reservations intact

### C-111: A waitlist closure remains discoverable to affected members after rollback
Observable: After rollback, an affected member who had not checked their status before the version change can obtain the closure outcome through the app or an existing account or support channel under ordinary access and account data rules.
Source: choice: operators should not leave people believing they are still waiting after a feature withdrawal

### C-112: A failed waitlist status lookup is reported as unavailable
Observable: Interrupt status access while the member has an accepted entry. The result signals that status could not be obtained.
Source: choice: an outage must be distinguishable from the empty state

### C-113: A waitlist promotion cannot duplicate an ordinary booking confirmed through any supported booking surface
Observable: If the app offers multiple booking surfaces, submit conflicting ordinary booking and promotion actions for the same account and occurrence. The waitlist creates no duplicate booking.
Source: implied: C-7 produces a single booking regardless of surface

### C-114: Waitlist outcomes follow the existing account data removal rules
Observable: Use an existing account deletion or data removal action where supported. The resulting waitlist data visibility and any required retention follow the app’s existing rules for that account.
Source: choice: waitlisting needs no separate retention promise

### C-115: A temporary waitlist outage does not silently surrender queue priority
Observable: Make existing waitlist demand impossible to verify with the waitlist enabled. Ordinary booking cannot allocate a seat for which accepted priority cannot be ruled out.
Source: choice: fail closed for potentially owed seats until current priority is known

### C-116: Each active entry can fulfill at most one seat for its owner
Observable: Free 2 seats with only one eligible entry for the same occurrence. Its owner receives exactly 1 confirmed seat from that entry.
Source: choice: waitlisting covers one person’s own reservation without introducing group booking

### C-117: A newly submitted join with a seat available for ordinary booking creates no waitlist entry
Observable: Submit a stale join after a seat becomes available for ordinary booking with no earlier demand. The member has 0 new active entries.
Source: choice: a queue entry is unnecessary while the member can book normally

### C-118: A stale join response pointing to ordinary booking creates no confirmed booking
Observable: Submit the class’s old join action after a seat becomes available for ordinary booking. No booking appears until the member completes ordinary booking.
Source: choice: a stale queue action does not replace direct booking confirmation

### C-119: The priority of earlier accepted demand counts against seats available to new callers
Observable: With 1 physically vacant seat owed to an existing unresolved waiter, open the same eligible session as a new member. The result indicates no seat is available to book immediately.
Source: choice: availability shown to new callers must account for the queue’s existing claims

### C-120: An accepted join reports confirmation if the member is already promoted when the result is determined
Observable: Accept a join while the session is full, then promote the member before the app determines the action’s result. The result identifies the confirmed booking.
Source: choice: a fast promotion must not require the app to present outdated waiting status

### C-121: A later promotion indication cannot present a cancelled booking as current
Observable: Promote a member, cancel the resulting booking, then open the app. Any remaining promotion indication does not represent that booking as currently confirmed.
Source: implied: U-2 needs the member’s current status

### C-122: An unfulfilled terminal outcome remains discoverable while the member can access the occurrence under ordinary booking rules
Observable: End an entry before or at the deadline. While the session remains accessible under the app’s ordinary visibility and account data rules, a current status check can retrieve the ended outcome.
Source: choice: keep closure outcomes accessible for as long as their session is relevant under existing app rules

### C-123: An early session cancellation is distinguishable from a voluntary withdrawal
Observable: Cancel a session before its deadline with outstanding entries. Where the member retains access to its outcome, it identifies session cancellation as the reason waiting ended.
Source: choice: members should know the occurrence itself is unavailable

### C-124: A schedule change that ends an entry is distinguishable from a voluntary withdrawal
Observable: Move the session to a different venue. Where the member retains access to the outcome, it identifies the schedule change as the reason waiting ended.
Source: choice: members need to know that any new session commitment requires a fresh decision

### C-125: Promotion uses the app’s session time rather than the waiting member’s device clock
Observable: Put the member’s device clock behind the app’s authoritative session time. Once the app’s time reaches the deadline, that device cannot secure promotion for the occurrence.
Source: choice: the class uses one cutoff instant for every member

### C-126: Extending the cutoff before it passes keeps pending entries eligible under the new cutoff
Observable: Before the current deadline, extend ordinary booking to a later instant that is still before the scheduled start. A member waiting across the original deadline can be promoted during the extension.
Source: choice: current booking availability governs pending entries that have not already ended

### C-127: Temporarily unavailable status leaves established waiting priority intact
Observable: Make the member’s status view unavailable between two accepted joins and the release of one seat. After service recovery, the earlier entry still has priority if both are eligible.
Source: implied: C-14 preserves the accepted commitment rather than a particular display

### C-128: Production waitlisting begins disabled until initial enablement succeeds
Observable: Deploy the feature for the first time without enabling it. Existing ordinary booking remains in effect without an active join action.
Source: choice: operators control when the live app starts accepting new obligations

### C-129: A definitively failed configuration change preserves the effective setting
Observable: Fail an authorized disable attempt before it takes effect. A subsequent authorized check still reports enabled.
Source: choice: an attempted switch does not change the operator’s effective setting

### C-130: An operator blocked from completing rollback can identify the unresolved waitlist commitment
Observable: Attempt rollback while waiting entries cannot be reconciled because the required booking service is unavailable. The operator can tell the transition is blocked by outstanding waitlist state.
Source: choice: unresolved commitments must remain actionable during a failed rollback

### C-131: A runtime limit refusal leaves existing accepted entries intact
Observable: Reach an actual platform limit on accepting another waiter and trigger a refused join. Previously accepted entries retain their priority.
Source: implied: C-14 protects an acknowledged commitment during an interruption

### C-132: A stale join cannot authorize automatic booking for a changed start time
Observable: Open the join action, then reschedule the start before submitting it. No waiting entry for the new time is created until the member chooses to join after seeing the new time.
Source: choice: queue consent applies to the schedule presented to the member

### C-133: A stale join cannot authorize automatic booking for a changed venue
Observable: Open the join action, then change the venue before submitting it. No waiting entry for the new venue is created until the member chooses to join after seeing the new venue.
Source: choice: queue consent applies to the location presented to the member

### C-134: A stale join cannot authorize newly applicable booking obligations
Observable: Open the join action, then change the obligations in a way that requires new consent before submission. The member must review the new obligations before the new join can succeed.
Source: choice: use the obligations the member actually accepted

### C-135: Booking restrictions shared across sessions hold for concurrent promotions
Observable: With an ordinary booking rule that permits only one of two reservations, release seats concurrently in the two sessions for which the same member waits. The member ends with at most 1 confirmed booking across those sessions.
Source: implied: C-23 applies ordinary booking rules at confirmation

### C-136: A temporarily suspended booking window prevents promotion while suspended
Observable: Suspend booking through an existing temporary hold, where supported. Release a seat during that hold. No waiter receives a confirmed booking while ordinary bookings are suspended.
Source: choice: temporary closure blocks fulfillment on the same terms as ordinary booking

### C-137: A temporary booking suspension preserves existing waiting priority
Observable: Temporarily suspend booking without cancelling the session or reaching the deadline, then resume it. Active members retain their relative priority if no intervening event ended their entries.
Source: choice: a temporary suspension does not withdraw either side's commitment

### C-138: Resuming an open booking window makes already vacant seats available for promotion
Observable: Lift a temporary booking hold before the deadline while an eligible member is still waiting and space is already available. The member can be promoted without another seat-release action.
Source: choice: restoration of bookability is itself an opportunity to fulfill accepted entries

### C-139: An elapsed deadline is distinguishable from voluntary withdrawal in a visible ended outcome
Observable: Allow an entry to expire at the current deadline. Where its ended outcome is accessible, it identifies the booking deadline as the reason waiting ended.
Source: choice: the member needs to know why the earlier commitment produced no seat

### C-140: A promoted booking is eligible for the app’s ordinary confirmation messages
Observable: Promote a waiter whose ordinary booking would trigger a confirmation message under the existing settings. The confirmation for the promoted seat follows the same notification policy and preferences.
Source: choice: use the app’s established notification behavior rather than requiring a new channel

### C-141: A confirmation messaging failure leaves the promoted booking effective
Observable: If the app uses confirmation messaging, interrupt message delivery after the booking is confirmed. Current booking status still shows the confirmed seat.
Source: choice: attendance depends on booking confirmation rather than message delivery

### C-142: A waitlist retry cannot create a second logical confirmation notice for the same booking
Observable: Where ordinary confirmation messaging exists, retry the completed promotion. The app does not initiate a new confirmation notice for that booking beyond the existing delivery policy.
Source: choice: a promotion retry should not appear to create another reservation

### C-143: Temporary suspension of ordinary booking prevents new active waitlist entries
Observable: Attempt a new join while the existing app has temporarily suspended booking for that occurrence. The action creates 0 entries.
Source: choice: pause new commitments while the session is out of ordinary booking

### C-144: Permanent closure of ordinary booking ends outstanding entries for the session
Observable: Use an existing permanent booking closure before the deadline, if the app supports one. Active entries end without a booking even if the class is still scheduled to run.
Source: choice: unlike a temporary hold, permanent closure leaves no future booking opportunity for the original commitment

### C-145: Deleting a session ends its active waiting commitments
Observable: Delete a session with an active entry if the app allows deletion. The deleted session disappears from the member’s active waitlist.
Source: implied: C-16 requires an occurrence to exist

### C-146: A member cannot retrieve waitlist status after authentication expires
Observable: Expire the member's account session then seek current waitlist status. The app requires normal sign-in before returning private status.
Source: choice: protect the same account boundary used to join

### C-147: A member cannot withdraw an entry after authentication expires
Observable: Expire the member's account session before submitting leave. The old client cannot change the entry before satisfying normal sign-in.
Source: choice: apply account authorization to withdrawal as well as joining

### C-148: A join from before disablement cannot establish a commitment after re-enablement
Observable: Open a full session’s join action while enabled. Disable and re-enable waitlisting before submitting the old action. A new active entry requires a fresh choice made after re-enablement.
Source: choice: an action from before operator closure cannot revive a former acceptance window

### C-149: All seat allocation paths using ordinary bookable capacity honor waitlist priority
Observable: Where supported, try to assign the last ordinary bookable seat through a staff-assisted or alternate booking surface while it is owed to an eligible waiter. That surface cannot allocate the seat ahead of the waiter.
Source: choice: eligibility for an ordinary seat cannot depend on which surface is used to allocate it

### C-150: Separately reserved capacity follows the app’s existing availability rules
Observable: If the app already reserves some seats outside ordinary booking, free one of those seats while the ordinary allocation remains full. The waitlist does not receive it unless the app releases it into ordinary booking.
Source: choice: waitlisting follows the same seat pool as ordinary booking

### C-151: Fully resolved ineligible demand does not hold a seat from ordinary booking
Observable: Free one seat with only definitively ineligible waiters. After their entries end, an eligible member can book the open seat through ordinary booking.
Source: choice: priority applies only while there is a waiting commitment that could use the seat

### C-152: A current status lookup reflects the member’s latest completed action across devices
Observable: Join or withdraw on one signed-in device, then request current waitlist status on another under the same account. The result reflects the completed action unless a newer outcome has superseded it.
Source: implied: U-2 requires current account status across visits

### C-153: A full session with an available waitlist can be joined while an earlier waiter’s promotion is pending
Observable: With all remaining seats owed to earlier waiting members, an otherwise eligible newcomer can join behind existing entries when the waitlist remains open.
Source: choice: a seat reserved for prior waiting demand leaves the session full for new bookings

### C-154: A fresh join at the deadline cannot create an active entry
Observable: Load a full session before the cutoff and submit its join at the cutoff instant according to the app. The member acquires 0 active entries from that action.
Source: choice: the deadline is exclusive for new waiting commitments

### C-155: An ordinary booking for a waiting member ends their active entry for that occurrence
Observable: If the existing app permits a member to obtain a confirmed booking from a separate allocation or an unreserved seat while waiting, check their current status after that confirmation. They no longer hold an active waitlist entry for the session.
Source: choice: any confirmed seat for the member fulfills the waiting intent

### C-156: Cancelling a booking obtained outside the waitlist does not restore the closed waiting entry
Observable: Have a waiting member obtain an ordinary booking through a supported allocation outside the queue, then cancel the booking. The member has no active entry unless they choose to join again.
Source: choice: a completed waiting commitment does not return after the member gives up the seat

### C-157: A join from an ended booking window cannot authorize waitlisting in a reopened window
Observable: Load the join action before the deadline, let that window end, then reopen booking if supported. An action from before the window ended cannot create a new waiting entry.
Source: choice: reopening does not carry earlier unaccepted consent across a terminal cutoff

### C-158: A known member-specific booking restriction is disclosed before accepting a waitlist commitment
Observable: Try to join a full visible session while subject to an ordinary booking restriction that can be disclosed to that member. The refusal explains that restriction as the obstacle.
Source: choice: a member should be able to distinguish a correctable eligibility problem from a full session

### C-159: A refused session change has no effect on active waitlist commitments
Observable: Attempt a time or venue change that the existing scheduling app rejects. Members waiting for the unchanged occurrence keep their places.
Source: implied: U-7 depends on effective session changes
